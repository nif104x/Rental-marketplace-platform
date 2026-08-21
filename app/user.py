from fastapi import FastAPI, APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from app.db import get_db
from app import schema
from app import model
from app import auth
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from decimal import Decimal
import uuid
import shutil
import math

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

# if current user id needed by tutul-ruhi-lamia
@router.get("/me")
def me(current_user: model.User = Depends(auth.get_current_user)):
    return current_user.user_id

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

#### work on booking after prayer
def is_available(listing_id: str, start_period, end_period, db: Session):

    conflict = db.query(model.Booking).filter(
        model.Booking.listing_id == listing_id,
        model.Booking.booking_status.in_(["Active", "Pending"]),
        model.Booking.start_period < end_period,
        model.Booking.end_period > start_period
    ).first()

    return conflict is None


@router.post("/booking/{listing_id}")
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
    service_fee = getattr(data, "service_fee", Decimal("0.00")) or Decimal("0.00")

    rental_cost = (rate_daily * days) + (rate_hourly * Decimal(str(hours)))

    booking_id = f"BK-{uuid.uuid4().hex[:6].upper()}"
    bk = model.Booking(
        booking_id = booking_id,
        listing_id = listing_id,
        lessee_id = current_user.user_id,
        start_period = data.start_period,
        end_period = data.end_period,
        rental_cost = rental_cost,
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
        "conversation_id": conv_id
    }

# working on conversationa and messages
@router.post("/conversations/{conversation_id}/messages")
def send_message(
    conversation_id: str,
    data: schema.MessageCreate,
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    conv = db.query(model.Conversation).filter(model.Conversation.conversation_id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if current_user.user_id not in [conv.lessor_id, conv.lessee_id]:
        raise HTTPException(status_code=403, detail="Not authorized to send messages in this conversation")

    msg_id = f"MSG-{uuid.uuid4().hex[:6].upper()}"
    msg = model.Message(
        message_id=msg_id,
        conversation_id=conversation_id,
        sender_id=current_user.user_id,
        content=data.content,
        is_read=False
    )

    conv.last_message_at = datetime.now(timezone.utc)

    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {
        "message": "Message sent successfully",
        "message_id": msg.message_id,
        "timestamp": msg.timestamp
    }

@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: str,
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    conv = db.query(model.Conversation).filter(model.Conversation.conversation_id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if current_user.user_id not in [conv.lessor_id, conv.lessee_id]:
        raise HTTPException(status_code=403, detail="Not authorized to view these messages")

    db.query(model.Message).filter(
        model.Message.conversation_id == conversation_id,
        model.Message.sender_id != current_user.user_id,
        model.Message.is_read == False
    ).update({"is_read": True})
    db.commit()

    messages = db.query(model.Message).filter(
        model.Message.conversation_id == conversation_id
    ).order_by(model.Message.timestamp.asc()).all()

    return messages # tutul tomar current user id lagle /me endpoint call korba



