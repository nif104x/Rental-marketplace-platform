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

router = APIRouter(prefix="/review", tags=["review"])

@router.post("/create")
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

# @router.get("/listings/{listing_id}/reviews")
# def get_listing_reviews(
#     listing_id: str,
#     db: Session = Depends(get_db)
# ):
#     lst = db.query(model.Listing).filter(model.Listing.listing_id == listing_id).first()
#     if not lst:
#         raise HTTPException(status_code=404, detail="Listing not found")

#     reviews = db.query(model.Review).filter(
#         model.Review.target_listing_id == listing_id
#     ).all()

#     return reviews