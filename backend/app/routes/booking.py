from fastapi import FastAPI, APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from backend.app.db import get_db
from backend.app import schema
from backend.app import model
from backend.app import auth
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from decimal import Decimal
import uuid
import shutil
import math
from typing import Optional
from backend.app.routes.notification import notify_user

router = APIRouter(prefix="/booking", tags=["booking"])

def is_available(listing_id: str, start_period, end_period, db: Session):

    conflict = db.query(model.Booking).filter(
        model.Booking.listing_id == listing_id,
        model.Booking.booking_status.in_(["Active", "Pending"]),
        model.Booking.start_period < end_period,
        model.Booking.end_period > start_period
    ).first()

    return conflict is None


@router.post("/{listing_id}")
def create_booking(
    listing_id: str,
    data: schema.BookingCreate,
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):

    lst = db.query(model.Listing).filter(model.Listing.listing_id == listing_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Listing not found")

    if lst.lessor_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="You cannot book your own listing")

    if data.start_period >= data.end_period:
        raise HTTPException(status_code=400, detail="End period must be after start period")

    if not is_available(listing_id, data.start_period, data.end_period, db):
        raise HTTPException(status_code=409, detail="Selected dates are already booked")


    duration = data.end_period - data.start_period
    total_hours = duration.total_seconds() / 3600
    days = int(total_hours // 24)
    hours = math.ceil(total_hours % 24)


    rate_daily = lst.rental_rate_daily or Decimal("0.00")
    rate_hourly = lst.rental_rate_hourly or Decimal("0.00")
    deposit = lst.security_deposit or Decimal("0.00")
    base_rental_cost = (rate_daily * days) + (rate_hourly * Decimal(str(hours)))
    
    # 5% platform service fee calculation
    service_fee = (base_rental_cost * Decimal("0.05")).quantize(Decimal("0.01"))
    total_payable = base_rental_cost + deposit + service_fee

    booking_id = f"BK-{uuid.uuid4().hex[:6].upper()}"
    bk = model.Booking(
        booking_id = booking_id,
        listing_id = listing_id,
        lessee_id = current_user.user_id,
        start_period = data.start_period,
        end_period = data.end_period,
        rental_cost = total_payable,
        deposit_held = deposit,
        service_fee = service_fee,
        booking_status = "Pending"
    )

    conv_id = f"CONV-{uuid.uuid4().hex[:6].upper()}"
    conv = model.Conversation(
        conversation_id=conv_id,
        listing_id=listing_id,
        booking_id=booking_id,
        lessor_id=lst.lessor_id,
        lessee_id=current_user.user_id
    )

    ntf = notify_user(
            user_id=bk.lessee_id,
            notif_type="Booking Update",
            delivery_method="IN-APP",
            db=db
        )
    
    notify_user(
            user_id=lst.lessor_id,
            notif_type="Booking REQUEST",
            delivery_method="IN-APP",
            db=db
        )


    db.add(bk)
    db.add(conv)
    db.commit()
    db.refresh(bk)
    db.refresh(conv)

    return {
        "message": "Booked successfully",
        "booking_id": bk.booking_id,
        "rental_cost": bk.rental_cost,
        "deposit_held": bk.deposit_held,
        "conversation_id": conv_id,
        "notification_type": ntf.type
    }


@router.get("/requests")
def get_lessor_booking_requests(
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    bookings = db.query(model.Booking).join(
        model.Listing, model.Booking.listing_id == model.Listing.listing_id
    ).filter(
        model.Listing.lessor_id == current_user.user_id,
        model.Booking.booking_status == "Pending"
    ).all()

    return bookings


@router.patch("/{booking_id}/accept")
def accept_booking(
    booking_id: str,
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    bk = db.query(model.Booking).filter(model.Booking.booking_id == booking_id).first()
    if not bk:
        raise HTTPException(status_code=404, detail="Booking not found")

    lst = db.query(model.Listing).filter(model.Listing.listing_id == bk.listing_id).first()
    if not lst or lst.lessor_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to accept this booking")

    if bk.booking_status != "Pending":
        raise HTTPException(status_code=400, detail=f"Cannot accept booking with status: {bk.booking_status}")

    bk.booking_status = "Active"
    
    ntf = notify_user(
        user_id=bk.lessee_id,
        notif_type="Booking Accepted",
        delivery_method="IN-APP",
        db=db
    )

    db.commit()
    db.refresh(bk)

    return {
        "message": "Booking accepted successfully",
        "booking_id": bk.booking_id,
        "booking_status": bk.booking_status,
        "notification_type": ntf.type
    }

@router.delete("/{booking_id}/reject")
def reject_and_delete_booking(
    booking_id: str,
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    bk = db.query(model.Booking).filter(model.Booking.booking_id == booking_id).first()
    if not bk:
        raise HTTPException(status_code=404, detail="Booking not found")

    lst = db.query(model.Listing).filter(model.Listing.listing_id == bk.listing_id).first()
    if not lst or lst.lessor_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to reject this booking")

    lessee_id = bk.lessee_id

    ntf = notify_user(
        user_id=lessee_id,
        notif_type="Booking Rejected",
        delivery_method="IN-APP",
        db=db
    )

    db.delete(bk)
    db.commit()

    return {
        "message": "Booking rejected and removed successfully",
        "booking_id": booking_id,
        "notification_type": ntf.type
    }