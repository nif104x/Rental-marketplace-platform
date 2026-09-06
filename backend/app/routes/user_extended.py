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

router = APIRouter(prefix="/user", tags=["User"])


@router.post("/signup")
def signup(data: schema.UserCreate, db=Depends(get_db)):
    user_id = f"U-{uuid.uuid4().hex[:6].upper()}"
    user = model.User(
        user_id=user_id,
        role = "user",
        name=data.name,
        email = data.email,
        contact_details=data.contact_details, # use this as mobile no.
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

@router.get("/my-listings")
def get_my_listings(
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    listings = db.query(model.Listing).filter(
        model.Listing.lessor_id == current_user.user_id
    ).all()

    return listings

@router.get("/listings/{listing_id}/lessee") # tutul eilhan theika current keda nise oita paiba
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


@router.get("/booking-requests")
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


@router.patch("/booking/{booking_id}/accept")
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

@router.delete("/booking/{booking_id}/reject")
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

## review and report part:
@router.post("/reviews")
def create_review(
    data: schema.ReviewCreate,
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not data.target_user_id and not data.target_listing_id:
        raise HTTPException(status_code=400, detail="Must provide target_user_id or target_listing_id")

    if data.rating_score < 0 or data.rating_score > 5:
        raise HTTPException(status_code=400, detail="Rating score must be between 0 and 5")

    if data.target_listing_id:
        listing = db.query(model.Listing).filter(model.Listing.listing_id == data.target_listing_id).first()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        valid_booking = db.query(model.Booking).filter(
            model.Booking.listing_id == data.target_listing_id,
            model.Booking.lessee_id == current_user.user_id,
            model.Booking.booking_status == "Completed"
        ).first()

        if not valid_booking:
            raise HTTPException(
                status_code=403, 
                detail="You can only review a listing after a successfully completed rental cycle"
            )

    if data.target_user_id:
        if data.target_user_id == current_user.user_id:
            raise HTTPException(status_code=400, detail="You cannot review yourself")

        target_user = db.query(model.User).filter(model.User.user_id == data.target_user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")

        valid_cycle = db.query(model.Booking).join(
            model.Listing, model.Booking.listing_id == model.Listing.listing_id
        ).filter(
            model.Booking.booking_status == "Completed",
            or_(
                and_(model.Booking.lessee_id == current_user.user_id, model.Listing.lessor_id == data.target_user_id),
                and_(model.Listing.lessor_id == current_user.user_id, model.Booking.lessee_id == data.target_user_id)
            )
        ).first()

        if not valid_cycle:
            raise HTTPException(
                status_code=403, 
                detail="You can only review a counter-party after a successfully completed rental cycle"
            )

    rev_id = f"REV-{uuid.uuid4().hex[:6].upper()}"
    rev = model.Review(
        review_id=rev_id,
        reviewer_id=current_user.user_id,
        target_user_id=data.target_user_id,
        target_listing_id=data.target_listing_id,
        rating_score=data.rating_score,
        qualitative_review=data.qualitative_review
    )
    db.add(rev)
    db.commit()
    db.refresh(rev)

    return {
        "message": "Review submitted successfully",
        "review_id": rev.review_id
    }

@router.get("/listings/{listing_id}/reviews")
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


@router.post("/reports")
def create_report(
    data: schema.ReportCreate,
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    user_exists = db.query(model.User).filter(model.User.user_id == data.reported_entity_id).first()
    listing_exists = db.query(model.Listing).filter(model.Listing.listing_id == data.reported_entity_id).first()

    if not user_exists and not listing_exists:
        raise HTTPException(status_code=404, detail="Reported entity not found")

    rep_id = f"REP-{uuid.uuid4().hex[:6].upper()}"
    rep = model.Report(
        report_id=rep_id,
        reporter_id=current_user.user_id,
        reported_entity_id=data.reported_entity_id,
        flag_reason=data.flag_reason,
        admin_resolution="Pending"
    )
    db.add(rep)
    db.commit()
    db.refresh(rep)

    return {
        "message": "Report submitted successfully",
        "report_id": rep.report_id
    }

## wishlist:

@router.post("/wishlist/{listing_id}")
def add_to_wishlist(
    listing_id: str,
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    lst = db.query(model.Listing).filter(model.Listing.listing_id == listing_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Listing not found")

    existing = db.query(model.WishlistItem).filter(
        model.WishlistItem.user_id == current_user.user_id,
        model.WishlistItem.listing_id == listing_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Item already in wishlist")

    wsh_id = f"WSH-{uuid.uuid4().hex[:6].upper()}"
    item = model.WishlistItem(
        wishlist_id=wsh_id,
        user_id=current_user.user_id,
        listing_id=listing_id
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "message": "Added to wishlist successfully",
        "wishlist_id": item.wishlist_id
    }


@router.get("/wishlist")
def get_my_wishlist(
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    items = db.query(model.WishlistItem).filter(
        model.WishlistItem.user_id == current_user.user_id
    ).all()
    return items


@router.delete("/wishlist/{listing_id}")
def remove_from_wishlist(
    listing_id: str,
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(model.WishlistItem).filter(
        model.WishlistItem.user_id == current_user.user_id,
        model.WishlistItem.listing_id == listing_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found in wishlist")

    db.delete(item)
    db.commit()

    return {"message": "Removed from wishlist successfully"}

# Notification
def notify_user(
    user_id: str,
    notif_type: str,
    delivery_method: str,
    db: Session
):
    notif_id = f"NTF-{uuid.uuid4().hex[:6].upper()}"
    notif = model.Notification(
        notification_id=notif_id,
        user_id=user_id,
        delivery_method=delivery_method,
        type=notif_type
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    return notif

@router.get("/notifications")
def get_user_notifications(
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    notifications = db.query(model.Notification).filter(
        model.Notification.user_id == current_user.user_id
    ).order_by(model.Notification.created_at.desc()).all()

    return notifications


@router.delete("/notifications/{notification_id}")
def dismiss_notification(
    notification_id: str,
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    notif = db.query(model.Notification).filter(
        model.Notification.notification_id == notification_id,
        model.Notification.user_id == current_user.user_id
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    db.delete(notif)
    db.commit()

    return {"message": "Notification dismissed successfully"}



###### searching##########
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

