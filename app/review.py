import uuid
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import and_, func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import auth, model
from app.db import get_db


router = APIRouter(prefix="/reviews", tags=["Reviews"])


class ReviewCreate(BaseModel):
    target_user_id: str | None = Field(default=None, min_length=1, max_length=64)
    target_listing_id: str | None = Field(default=None, min_length=1, max_length=64)
    rating_score: float = Field(..., ge=1, le=5, multiple_of=0.01, examples=[5.0])
    qualitative_review: str | None = Field(default=None, max_length=5000)

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "target_user_id": "U-123456",
                "rating_score": 5.0,
                "qualitative_review": "Responsive owner and a smooth rental experience.",
            }
        },
    )

    @model_validator(mode="after")
    def require_exactly_one_target(self):
        has_user_target = self.target_user_id is not None
        has_listing_target = self.target_listing_id is not None
        if has_user_target == has_listing_target:
            raise ValueError("Provide exactly one of target_user_id or target_listing_id")
        return self


class ReviewResponse(BaseModel):
    review_id: str
    reviewer_id: str
    target_user_id: str | None = None
    target_listing_id: str | None = None
    rating_score: float | None = Field(default=None, ge=0, le=5)
    qualitative_review: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ReviewUpdate(BaseModel):
    rating_score: float | None = Field(
        default=None,
        ge=1,
        le=5,
        multiple_of=0.01,
        examples=[4.5],
    )
    qualitative_review: str | None = Field(default=None, max_length=5000)

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "rating_score": 4.5,
                "qualitative_review": "Updated review text.",
            }
        },
    )

    @model_validator(mode="after")
    def require_an_update(self):
        if not self.model_fields_set:
            raise ValueError("Provide rating_score or qualitative_review")
        if "rating_score" in self.model_fields_set and self.rating_score is None:
            raise ValueError("rating_score cannot be null")
        return self


class ReviewCollectionResponse(BaseModel):
    average_rating: float | None
    review_count: int
    reviews: list[ReviewResponse]


def _completed_booking_count(
    db: Session,
    reviewer_id: str,
    target_user_id: str | None,
    target_listing_id: str | None,
) -> int:
    """Return how many completed rentals authorize this reviewer/target pair."""
    if target_listing_id is not None:
        listing = (
            db.query(model.Listing)
            .filter(model.Listing.listing_id == target_listing_id)
            .first()
        )
        if listing is None:
            raise HTTPException(status_code=404, detail="Listing not found")
        if listing.lessor_id == reviewer_id:
            raise HTTPException(status_code=400, detail="You cannot review your own listing")

        completed_bookings = (
            db.query(model.Booking)
            .filter(
                model.Booking.listing_id == target_listing_id,
                model.Booking.lessee_id == reviewer_id,
                func.lower(model.Booking.booking_status) == "completed",
            )
            .with_for_update(of=model.Booking)
            .all()
        )
    else:
        target_user = (
            db.query(model.User)
            .filter(model.User.user_id == target_user_id)
            .first()
        )
        if target_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        if target_user_id == reviewer_id:
            raise HTTPException(status_code=400, detail="You cannot review yourself")

        completed_bookings = (
            db.query(model.Booking)
            .join(model.Listing, model.Booking.listing_id == model.Listing.listing_id)
            .filter(
                func.lower(model.Booking.booking_status) == "completed",
                or_(
                    and_(
                        model.Booking.lessee_id == reviewer_id,
                        model.Listing.lessor_id == target_user_id,
                    ),
                    and_(
                        model.Listing.lessor_id == reviewer_id,
                        model.Booking.lessee_id == target_user_id,
                    ),
                ),
            )
            .with_for_update(of=model.Booking)
            .all()
        )

    if not completed_bookings:
        raise HTTPException(
            status_code=403,
            detail="A completed rental with this target is required before reviewing",
        )
    return len(completed_bookings)


def _existing_review_count(
    db: Session,
    reviewer_id: str,
    target_user_id: str | None,
    target_listing_id: str | None,
) -> int:
    query = db.query(func.count(model.Review.review_id)).filter(
        model.Review.reviewer_id == reviewer_id
    )
    if target_listing_id is not None:
        query = query.filter(model.Review.target_listing_id == target_listing_id)
    else:
        query = query.filter(model.Review.target_user_id == target_user_id)
    return query.scalar() or 0


def _get_review_or_404(db: Session, review_id: str) -> model.Review:
    review = (
        db.query(model.Review)
        .filter(model.Review.review_id == review_id)
        .first()
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


def _review_collection(db: Session, filters, offset: int, limit: int):
    review_count, average_rating = (
        db.query(
            func.count(model.Review.review_id),
            func.avg(model.Review.rating_score),
        )
        .filter(*filters)
        .one()
    )
    reviews = (
        db.query(model.Review)
        .filter(*filters)
        .order_by(
            model.Review.created_at.desc().nullslast(),
            model.Review.review_id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    rounded_average = None
    if average_rating is not None:
        rounded_average = float(
            Decimal(str(average_rating)).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
        )

    return ReviewCollectionResponse(
        average_rating=rounded_average,
        review_count=review_count,
        reviews=reviews,
    )


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    data: ReviewCreate,
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    completed_booking_count = _completed_booking_count(
        db,
        current_user.user_id,
        data.target_user_id,
        data.target_listing_id,
    )
    existing_review_count = _existing_review_count(
        db,
        current_user.user_id,
        data.target_user_id,
        data.target_listing_id,
    )
    if existing_review_count >= completed_booking_count:
        raise HTTPException(
            status_code=409,
            detail="Review limit reached for completed rentals with this target",
        )

    review = model.Review(
        review_id=f"REV-{uuid.uuid4().hex.upper()}",
        reviewer_id=current_user.user_id,
        target_user_id=data.target_user_id,
        target_listing_id=data.target_listing_id,
        rating_score=Decimal(str(data.rating_score)),
        qualitative_review=data.qualitative_review,
    )

    try:
        db.add(review)
        db.commit()
        db.refresh(review)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not create review") from exc

    return review


@router.get("/mine", response_model=list[ReviewResponse])
def get_my_reviews(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(model.Review)
        .filter(model.Review.reviewer_id == current_user.user_id)
        .order_by(
            model.Review.created_at.desc().nullslast(),
            model.Review.review_id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/listings/{listing_id}", response_model=ReviewCollectionResponse)
def get_listing_reviews(
    listing_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    listing_exists = (
        db.query(model.Listing.listing_id)
        .filter(model.Listing.listing_id == listing_id)
        .first()
    )
    if listing_exists is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    return _review_collection(
        db,
        [model.Review.target_listing_id == listing_id],
        offset,
        limit,
    )


@router.get("/users/{user_id}", response_model=ReviewCollectionResponse)
def get_user_reviews(
    user_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    user_exists = (
        db.query(model.User.user_id)
        .filter(model.User.user_id == user_id)
        .first()
    )
    if user_exists is None:
        raise HTTPException(status_code=404, detail="User not found")

    return _review_collection(
        db,
        [model.Review.target_user_id == user_id],
        offset,
        limit,
    )


@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(review_id: str, db: Session = Depends(get_db)):
    return _get_review_or_404(db, review_id)


@router.patch("/{review_id}", response_model=ReviewResponse)
def update_review(
    review_id: str,
    data: ReviewUpdate,
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    review = _get_review_or_404(db, review_id)
    if review.reviewer_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You can only edit your own reviews")

    update_data = data.model_dump(exclude_unset=True)
    if "rating_score" in update_data:
        update_data["rating_score"] = Decimal(str(update_data["rating_score"]))

    for field, value in update_data.items():
        setattr(review, field, value)

    try:
        db.commit()
        db.refresh(review)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update review") from exc

    return review


@router.delete("/{review_id}")
def delete_review(
    review_id: str,
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    review = _get_review_or_404(db, review_id)
    if review.reviewer_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own reviews")

    try:
        db.delete(review)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not delete review") from exc

    return {"message": "Review deleted successfully"}
