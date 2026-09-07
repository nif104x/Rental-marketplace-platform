from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from decimal import Decimal
from datetime import datetime
from typing import Optional

from backend.app.db import get_db
from backend.app import model, schema

router = APIRouter(prefix="/search", tags=["search"])

def format_listing_result(listing: model.Listing) -> dict:
    primary_image = None
    if hasattr(listing, "images") and listing.images:
        for img in listing.images:
            if getattr(img, "is_primary_preview", False) and primary_image is None:
                primary_image = img.image_file_url
        if not primary_image and len(listing.images) > 0:
            primary_image = listing.images[0].image_file_url

    return {
        "listing_id": listing.listing_id,
        "title": listing.title,
        "description": listing.description,
        "category": listing.category,
        "rental_rate_daily": float(listing.rental_rate_daily or 0.0),
        "rental_rate_hourly": float(listing.rental_rate_hourly or 0.0),
        "security_deposit": float(listing.security_deposit or 0.0),
        "geo_location": listing.geo_location,
        "status": listing.status,
        "primary_image": primary_image
    }

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
    listing_query = (
        db.query(model.Listing)
        .options(joinedload(model.Listing.images))
        .filter(model.Listing.status == "Active")
    )

    if category:
        listing_query = listing_query.filter(model.Listing.category.ilike(f"%{category}%"))

    if geo_location:
        listing_query = listing_query.filter(model.Listing.geo_location.ilike(f"%{geo_location}%"))

    if query:
        search_filter = or_(
            model.Listing.title.ilike(f"%{query}%"),
            model.Listing.description.ilike(f"%{query}%"),
            model.Listing.geo_location.ilike(f"%{query}%")
        )
        if hasattr(model.Listing, "keywords_semantic_tags"):
            search_filter = or_(
                search_filter,
                func.cast(model.Listing.keywords_semantic_tags, model.String).ilike(f"%{query}%")
            )
        listing_query = listing_query.filter(search_filter)

    if min_price is not None:
        listing_query = listing_query.filter(model.Listing.rental_rate_daily >= min_price)
    if max_price is not None:
        listing_query = listing_query.filter(model.Listing.rental_rate_daily <= max_price)

    if start_period and end_period:
        if start_period >= end_period:
            raise HTTPException(status_code=400, detail="End period must be after start period")

        conflicted_ids = db.query(model.Booking.listing_id).filter(
            model.Booking.booking_status.in_(["Active", "Pending"]),
            model.Booking.start_period < end_period,
            model.Booking.end_period > start_period
        ).subquery()

        listing_query = listing_query.filter(~model.Listing.listing_id.in_(conflicted_ids))

    # Safe sorting fallback
    has_created_at = hasattr(model.Listing, "created_at")
    if sort_by == "newest":
        listing_query = listing_query.order_by(model.Listing.created_at.desc() if has_created_at else model.Listing.listing_id.desc())
    elif sort_by == "oldest":
        listing_query = listing_query.order_by(model.Listing.created_at.asc() if has_created_at else model.Listing.listing_id.asc())
    elif sort_by == "price_asc":
        listing_query = listing_query.order_by(model.Listing.rental_rate_daily.asc())
    elif sort_by == "price_desc":
        listing_query = listing_query.order_by(model.Listing.rental_rate_daily.desc())
    elif sort_by == "popular":
        listing_query = listing_query.outerjoin(
            model.Booking, model.Listing.listing_id == model.Booking.listing_id
        ).group_by(model.Listing.listing_id).order_by(func.count(model.Booking.booking_id).desc())

    listings = listing_query.all()
    return [format_listing_result(l) for l in listings]

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
    hours = int(total_hours % 24)

    rate_daily = lst.rental_rate_daily or Decimal("0.00")
    rate_hourly = lst.rental_rate_hourly or Decimal("0.00")
    deposit = lst.security_deposit or Decimal("0.00")

    base_rental_cost = (rate_daily * days) + (rate_hourly * Decimal(str(hours)))
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