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

router = APIRouter(prefix="/wishlist", tags=["wishlist"])

@router.post("/{listing_id}")
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


@router.get("/get")
def get_my_wishlist(
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    items = db.query(model.WishlistItem).filter(
        model.WishlistItem.user_id == current_user.user_id
    ).all()
    return items


@router.delete("/{listing_id}")
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

@router.get("/test")
def test():
    return {"ola":"amigo"}