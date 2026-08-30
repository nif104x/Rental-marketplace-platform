from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.controllers.deps import get_current_active_lessor, get_current_user
from app.core.database import get_db
from app.models.listing import Listing, ListingImage, ListingStatus
from app.models.user import User
from app.schemas.listing import ListingCreate, ListingResponse, ListingUpdate

router = APIRouter(prefix="/listings", tags=["Listings"])


@router.get("/", response_model=List[ListingResponse])
def get_listings(
    category: Optional[str] = None,
    location: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    query = db.query(Listing).filter(Listing.status == ListingStatus.ACTIVE)
    if category:
        query = query.filter(Listing.category.ilike(f"%{category}%"))
    if location:
        query = query.filter(Listing.location.ilike(f"%{location}%"))
    return query.offset(skip).limit(limit).all()


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing_by_id(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found",
        )
    return listing


@router.post("/", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
def create_listing(
    listing_in: ListingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_lessor),
):
    listing_data = listing_in.model_dump(exclude={"images"})
    listing = Listing(**listing_data, lessor_id=current_user.id)
    db.add(listing)
    db.commit()
    db.refresh(listing)

    if listing_in.images:
        for img in listing_in.images:
            db_img = ListingImage(**img.model_dump(), listing_id=listing.id)
            db.add(db_img)
        db.commit()
        db.refresh(listing)

    return listing


@router.put("/{listing_id}", response_model=ListingResponse)
def update_listing(
    listing_id: int,
    listing_in: ListingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_lessor),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found",
        )

    if listing.lessor_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this listing",
        )

    update_data = listing_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(listing, field, value)

    db.commit()
    db.refresh(listing)
    return listing