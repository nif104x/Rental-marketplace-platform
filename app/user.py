from fastapi import FastAPI, APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from app.db import get_db
from app import schema
from app import model
from app import auth
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import uuid
import shutil

router = APIRouter(prefix="/user", tags=["User"])


@router.post("/signup")
def signup(data: schema.UserCreate, db=Depends(get_db)):
    user_id = f"U-{uuid.uuid4().hex[:6].upper()}"
    user = model.User(
        user_id=user_id,
        role = "user",
        personal_bio=data.personal_bio,
        contact_details=data.contact_details,
        encrypted_credentials=data.password,
        verification_status="pending",
        account_status="Active"
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return JSONResponse(status_code=201, content={"message": "User created successfully"})

    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/login")
def login(data:schema.userlogin, db=Depends(get_db)):
    user = db.query(model.User).filter(model.User.contact_details==data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"Invalid credential")

    if user.encrypted_credentials!= data.password:
        raise HTTPException(status_code=404, detail=f"Invalid credential")

    access_token = auth.create_access_token(
        data = {"user_id": user.user_id},
        expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer"}

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

#### work on booking after prayer


router.post("/booking/{listing_id}")
def create_booking(
        listing_id : str,
        data:schema.BookingCreate,
        current_user: model.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):

    lst = db.query(model.Listing).filter(model.Listing.listing_id == listing_id).first()

    booking_id = f"BK-{uuid.uuid4().hex[:6].upper()}"
    lessee_id = current_user.user_id
    duration = data.end_period - data.start_period
    total_hours = duration.total_seconds() / 3600
    days = int(total_hours // 24)
    hours = total_hours % 24
    rental_cost = (lst.rental_rate_daily*days)+(lst.rental_rate_hourly*hours)+ lst.security_deposit + data.service_fee

    bk = model.Booking(
        booking_id = booking_id,
        listind_id = listing_id,
        lessee_id = lessee_id,
        start_period = data.start_period,
        end_period = data.end_period,
        rental_cost = rental_cost,
        deposit_held = lst.security_deposit
    )

def is_available(listing_id, start_period, end_period, db):
    conflict = db.query(model.Booking).filter(
        model.Booking.listing_id == listing_id,
        model.Booking.status == "accepted",
        model.Booking.start_period < end_period,
        model.Booking.end_period > start_period
    ).first()

    return conflict is None