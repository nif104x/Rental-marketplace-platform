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

router = APIRouter(prefix="/notification", tags=["notification"])

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

@router.get("/get")
def get_user_notifications(
    current_user: model.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    notifications = db.query(model.Notification).filter(
        model.Notification.user_id == current_user.user_id
    ).order_by(model.Notification.created_at.desc()).all()

    return notifications


@router.delete("/{notification_id}")
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

@router.get("/test")
def test():
    return {"ola":"amigo"}