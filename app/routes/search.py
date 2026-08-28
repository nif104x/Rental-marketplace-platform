from fastapi import FastAPI, APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from app.db import get_db
from app import schema
from app import model
from app import auth
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from decimal import Decimal
import uuid
import shutil
import math
from typing import Optional

router = APIRouter(prefix="/search", tags=["search"])

@router.get("/listings")
def get_listings(
    category: Optional[str] = None,
    query: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    geo_location: Optional[str] = None,
    start_period: Optional[datetime] = None,
    end_period: Optional[datetime] = None,
    sort_by: Optional[str] = Query("newest", pattern="^(newest|oldest|price_asc|price_desc|popular)$"),
    db: Session = Depends(get_db)
):
    listing_query = db.query(model.Listing).filter(model.Listing.status == "Active")

    # Category Filter
    if category:
        listing_query = listing_query.filter(model.Listing.category.ilike(f"%{category}%"))

    # Location Filter
    if geo_location:
        listing_query = listing_query.filter(model.Listing.geo_location.ilike(f"%{geo_location}%"))

    # Search Bar (Keywords, Title, Description, Semantic Tags)
    if query:
        search_filter = or_(
            model.Listing.title.ilike(f"%{query}%"),
            model.Listing.description.ilike(f"%{query}%"),
            model.Listing.geo_location.ilike(f"%{query}%"),
            func.cast(model.Listing.keywords_semantic_tags, model.String).ilike(f"%{query}%")
        )
        listing_query = listing_query.filter(search_filter)

    # Price Range Filter (Based on Daily Rate)
    if min_price is not None:
        listing_query = listing_query.filter(model.Listing.rental_rate_daily >= min_price)
    if max_price is not None:
        listing_query = listing_query.filter(model.Listing.rental_rate_daily <= max_price)

    # Availability Date Filter (Exclude conflicting bookings)
    if start_period and end_period:
        if start_period >= end_period:
            raise HTTPException(status_code=400, detail="End period must be after start period")

        conflicted_listing_ids = db.query(model.Booking.listing_id).filter(
            model.Booking.booking_status.in_(["Active", "Pending"]),
            model.Booking.start_period < end_period,
            model.Booking.end_period > start_period
        ).subquery()

        listing_query = listing_query.filter(~model.Listing.listing_id.in_(conflicted_listing_ids))

    # Sorting Logic
    if sort_by == "newest":
        listing_query = listing_query.order_by(model.Listing.created_at.desc())
    elif sort_by == "oldest":
        listing_query = listing_query.order_by(model.Listing.created_at.asc())
    elif sort_by == "price_asc":
        listing_query = listing_query.order_by(model.Listing.rental_rate_daily.asc())
    elif sort_by == "price_desc":
        listing_query = listing_query.order_by(model.Listing.rental_rate_daily.desc())
    elif sort_by == "popular":
        listing_query = listing_query.outerjoin(
            model.Booking, model.Listing.listing_id == model.Booking.listing_id
        ).group_by(model.Listing.listing_id).order_by(func.count(model.Booking.booking_id).desc())

    listings = listing_query.all()
    return listings

@router.post("/listings/{listing_id}/quote")
def get_booking_quote(
    listing_id: str,
    data: schema.BookingQuoteRequest,
    db: Session = Depends(get_db)
):
    lst = db.query(model.Listing).filter(model.Listing.listing_id == listing_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Listing not found")

    if data.start_period >= data.end_period:
        raise HTTPException(status_code=400, detail="End period must be after start period")

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

    return {
        "listing_id": lst.listing_id,
        "title": lst.title,
        "duration_days": days,
        "duration_hours": hours,
        "rate_daily": rate_daily,
        "rate_hourly": rate_hourly,
        "base_rental_cost": base_rental_cost,
        "security_deposit": deposit,
        "service_fee": service_fee,
        "total_amount_payable": total_payable
    }


@router.get("/test")
def test():
    return {"ola":"amigo"}