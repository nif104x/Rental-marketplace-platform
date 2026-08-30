from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.controllers.deps import get_current_user
from app.core.database import get_db
from app.models.booking import Booking, BookingStatus
from app.models.listing import Listing
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingResponse, BookingStatusUpdate

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_in: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = db.query(Listing).filter(Listing.id == booking_in.listing_id).first()
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found",
        )

    # Calculate duration and total cost
    days = (booking_in.end_date - booking_in.start_date).days
    if days <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date",
        )

    total_cost = days * listing.rental_rate

    booking = Booking(
        lessee_id=current_user.id,
        listing_id=listing.id,
        start_date=booking_in.start_date,
        end_date=booking_in.end_date,
        total_cost=total_cost,
        security_deposit=listing.security_deposit,
        status=BookingStatus.REQUESTED,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/my-bookings", response_model=List[BookingResponse])
def get_user_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Booking).filter(Booking.lessee_id == current_user.id).all()


@router.patch("/{booking_id}/status", response_model=BookingResponse)
def update_booking_status(
    booking_id: int,
    status_in: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    listing = db.query(Listing).filter(Listing.id == booking.listing_id).first()

    # Only Lessor of the item or the Lessee cancelling can update status
    is_lessor = listing.lessor_id == current_user.id
    is_lessee = booking.lessee_id == current_user.id

    if not (is_lessor or is_lessee):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this booking",
        )

    booking.status = status_in.status
    if status_in.cancellation_reason:
        booking.cancellation_reason = status_in.cancellation_reason

    db.commit()
    db.refresh(booking)
    return booking