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

router = APIRouter(prefix="/conv", tags=["conversation"])

@router.post("/{conversation_id}/messages")
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

@router.get("/{conversation_id}/messages")
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
