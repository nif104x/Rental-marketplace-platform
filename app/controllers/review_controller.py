from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.controllers.deps import get_current_user
from app.core.database import get_db
from app.models.booking import Booking, BookingStatus
from app.models.review import Review
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewResponse

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    review_in: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a review for a completed booking.
    """
    # 1. Check if the booking exists
    booking = db.query(Booking).filter(Booking.id == review_in.booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # 2. Check if booking is completed
    if booking.status != BookingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can only leave a review for a completed rental.",
        )

    # 3. Determine if the reviewer is the Lessee or the Lessor
    listing = booking.listing
    is_lessee = booking.lessee_id == current_user.id
    is_lessor = listing.lessor_id == current_user.id

    if not (is_lessee or is_lessor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to review this booking.",
        )

    # 4. Target of the review: if reviewer is lessee -> reviewee is lessor, and vice versa
    reviewee_id = listing.lessor_id if is_lessee else booking.lessee_id

    # 5. Prevent double reviews for the same booking by the same user
    existing_review = db.query(Review).filter(
        Review.booking_id == booking.id,
        Review.reviewer_id == current_user.id,
    ).first()

    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted a review for this booking.",
        )

    review = Review(
        booking_id=booking.id,
        reviewer_id=current_user.id,
        reviewee_id=reviewee_id,
        rating=review_in.rating,
        comment=review_in.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.get("/user/{user_id}", response_model=List[ReviewResponse])
def get_user_reviews(user_id: int, db: Session = Depends(get_db)):
    """
    Get all reviews received by a specific user.
    """
    return db.query(Review).filter(Review.reviewee_id == user_id).all()