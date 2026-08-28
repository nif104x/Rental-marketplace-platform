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

router = APIRouter(prefix="/listings", tags=["listings"])

@router.post("/createListing")
def creategig(data:schema.ListingCreate, current_user: model.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    lst_id = f"LST-{uuid.uuid4().hex[:6].upper()}"
    lst = model.Listing(
        listing_id = lst_id,
        lessor_id = current_user.user_id,
        title = data.title,
        description = data.description,
        category= data.category,
        rental_rate_hourly = data.rental_rate_hourly,
        rental_rate_daily = data.rental_rate_daily,
        rental_rate_weekly = data.rental_rate_weekly,
        seasonal_pricing_tiers = data.seasonal_pricing_tiers,
        security_deposit = data.security_deposit,
        item_rules = data.item_rules,
        availability_schedules = data.availability_schedules,
        geo_location = data.geo_location,
        keywords_semantic_tags = data.keywords_semantic_tags,
        status = data.status if hasattr(data, 'status') else "Active"
    )
    db.add(lst)
    db.commit()
    db.refresh(lst)
    return {
        "message": "Listing created successfully",
        "lst_id": lst.lst_id
    }


@router.post("/upload-image")
def upload_image(lst_id: str = Form(...), image:UploadFile = File(...), db: Session = Depends(get_db)):
    image_id = f"IMG-{uuid.uuid4().hex[:6].upper()}"
    file_path = f"../frontend/images/{image_id}.jpg"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    image_file_url = f"/images/{image_id}.jpg"
    img = model.Image(
        image_id = image_id,
        listing_id = lst_id,
        image_file_url = image_file_url
    )
    db.add(img)
    db.commit()
    db.refresh(img)
    return {
        "message": "Image uploaded successfully",
    }

# tutul eikhan e age listing save korle listing id paiba oita deya pore image save koiro. 
# ekloge er logic ta vaiba paitasilam na. me noob :,)

@router.patch("/editlisting/{listing_id}")
def editListing(listing_id: str, data: schema.ListingUpdate, current_user: model.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    lst = db.query(model.Listing).filter(model.Listing.listing_id == listing_id).first()
    
    if not lst:
        raise HTTPException(status_code=404, detail="Listing not found")
        
    if lst.lessor_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this listing")

    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(lst, field, value)
        
    db.commit()
    db.refresh(lst)
    
    return {
        "message": "Listing updated successfully",
        "listing": lst
    }

@router.delete("/deletelisting/{listing_id}")
def deleteListing(
    listing_id: str,
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    lst = db.query(model.Listing).filter(
        model.Listing.listing_id == listing_id
    ).first()

    if not lst:
        raise HTTPException(status_code=404, detail="Listing not found")

    if lst.lessor_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this listing"
        )

    db.delete(lst) # maybe in future i will delete the image file manually by code hehe!
    db.commit()

    return {
        "message": "Listing deleted successfully"
    }

@router.get("/my-listings")
def get_my_listings(
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    listings = db.query(model.Listing).filter(
        model.Listing.lessor_id == current_user.user_id
    ).all()

    return listings

@router.get("/{listing_id}/lessee") # tutul eilhan theika current keda nise oita paiba
def get_listing_lessee_details(
    listing_id: str,
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    lst = db.query(model.Listing).filter(model.Listing.listing_id == listing_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Listing not found")

    if lst.lessor_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view lessee details for this listing")

    booking = db.query(model.Booking).filter(
        model.Booking.listing_id == listing_id,
        model.Booking.booking_status.in_(["Active", "Completed"])
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="No booking found for this listing")

    lessee = db.query(model.User).filter(model.User.user_id == booking.lessee_id).first()
    if not lessee:
        raise HTTPException(status_code=404, detail="Lessee not found")

    return {
        "booking_id": booking.booking_id,
        "booking_status": booking.booking_status,
        "name": lessee.name,
        "contact_details": lessee.email,
        "account_status": lessee.account_status,
        "role": lessee.role
    }

@router.get("/{listing_id}/reviews")
def get_listing_reviews(
    listing_id: str,
    db: Session = Depends(get_db)
):
    lst = db.query(model.Listing).filter(model.Listing.listing_id == listing_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Listing not found")

    reviews = db.query(model.Review).filter(
        model.Review.target_listing_id == listing_id
    ).all()

    return reviews



CATEGORIES = [
    "electronics",
    "tools",
    "events",
    "outdoor",
    "sports",
    "music",
    "vehicles",
    "appliances",
    "apparel",
    "baby",
    "books"
]

@router.get("/categories", response_model=list[str])
def get_categories():
    return CATEGORIES



@router.get("/test")
def test():
    return {"ola":"amigo"}