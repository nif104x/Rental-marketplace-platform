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

router = APIRouter(prefix="/report", tags=["report"])

@router.post("/create")
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