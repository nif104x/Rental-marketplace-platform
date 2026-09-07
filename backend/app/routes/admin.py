from decimal import Decimal
from typing import Optional
import uuid
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.db import get_db
from backend.app import schema, model, auth
from backend.app.routes.notification import notify_user

router = APIRouter(prefix="/admin", tags=["Admin Operations"])


class UserVerificationUpdate(BaseModel):
    verification_status: str


# --- 1. Single Admin Signup ---

@router.post("/signup")
def signup(data: schema.UserCreate, db: Session = Depends(get_db)):
    # Enforce strict single-admin rule across the platform
    existing_admin = db.query(model.User).filter(model.User.role == "admin").first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An administrator account already exists. Only one admin user is allowed."
        )

    # Prevent duplicate email collisions
    existing_email = db.query(model.User).filter(model.User.email == data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered."
        )

    user_id = f"U-{uuid.uuid4().hex[:6].upper()}"
    user = model.User(
        user_id=user_id,
        role="admin",
        name=data.name,
        email=data.email,
        contact_details=data.contact_details,
        encrypted_credentials=data.password,
        verification_status="verified",
        account_status="Active"
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Admin user created successfully", "admin_id": user.user_id}
        )
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error while creating admin.")


# --- 2. Admin Authentication Guard ---

def require_admin(current_user: model.User = Depends(auth.get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required"
        )
    return current_user


# --- 3. Dashboard KPI Statistics ---

@router.get("/dashboard/stats")
def get_dashboard_stats(
    admin: model.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    total_users = db.query(func.count(model.User.user_id)).scalar() or 0
    total_listings = db.query(func.count(model.Listing.listing_id)).scalar() or 0
    active_bookings = db.query(func.count(model.Booking.booking_id)).filter(
        model.Booking.booking_status == "Active"
    ).scalar() or 0
    pending_reports = db.query(func.count(model.Report.report_id)).filter(
        model.Report.admin_resolution == "Pending"
    ).scalar() or 0
    pending_verifications = db.query(func.count(model.User.user_id)).filter(
        model.User.verification_status.ilike("pending")
    ).scalar() or 0

    total_fees_collected = db.query(func.sum(model.Booking.service_fee)).filter(
        model.Booking.booking_status.in_(["Active", "Completed"])
    ).scalar() or Decimal("0.00")

    return {
        "total_users": total_users,
        "total_listings": total_listings,
        "active_bookings": active_bookings,
        "pending_reports": pending_reports,
        "pending_verifications": pending_verifications,
        "total_service_revenue": total_fees_collected
    }


# --- 4. User Moderation & Verification (KYC) ---

@router.get("/users")
def get_all_users(
    role: Optional[str] = None,
    status: Optional[str] = None,
    admin: model.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(model.User)
    if role:
        query = query.filter(model.User.role == role)
    if status:
        query = query.filter(model.User.account_status == status)

    users = query.all()
    return [
        {
            "user_id": u.user_id,
            "name": getattr(u, "name", "User"),
            "email": getattr(u, "email", "N/A"),
            "contact_details": u.contact_details,
            "role": u.role,
            "verification_status": getattr(u, "verification_status", "pending"),
            "account_status": u.account_status,
            "created_at": getattr(u, "created_at", None)
        }
        for u in users
    ]


@router.patch("/users/{user_id}/verify")
def verify_user(
    user_id: str,
    payload: UserVerificationUpdate,
    admin: model.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(model.User).filter(model.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.verification_status = payload.verification_status
    db.commit()
    db.refresh(user)

    return {
        "message": f"User verification updated to {payload.verification_status}",
        "user_id": user.user_id,
        "verification_status": user.verification_status
    }


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: str,
    new_status: str = Query(..., pattern="^(Active|Suspended|Banned)$"),
    admin: model.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(model.User).filter(model.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="Cannot alter own admin account status")

    user.account_status = new_status
    db.commit()
    db.refresh(user)

    return {
        "message": f"User status updated to {new_status}",
        "user_id": user.user_id,
        "account_status": user.account_status
    }


# --- 5. Catalog Listing Moderation ---

@router.get("/listings")
def get_all_listings(
    status: Optional[str] = None,
    category: Optional[str] = None,
    admin: model.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(model.Listing)
    if status:
        query = query.filter(model.Listing.status == status)
    if category:
        query = query.filter(model.Listing.category.ilike(f"%{category}%"))

    return query.all()


@router.patch("/listings/{listing_id}/status")
def update_listing_status(
    listing_id: str,
    new_status: str = Query(..., pattern="^(Active|Inactive|Suspended|Removed)$"),
    admin: model.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    listing = db.query(model.Listing).filter(model.Listing.listing_id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    listing.status = new_status
    db.commit()
    db.refresh(listing)

    return {
        "message": f"Listing status updated to {new_status}",
        "listing_id": listing.listing_id,
        "status": listing.status
    }


@router.delete("/listings/{listing_id}")
def delete_listing_admin(
    listing_id: str,
    admin: model.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    listing = db.query(model.Listing).filter(model.Listing.listing_id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    db.delete(listing)
    db.commit()

    return {"message": "Listing permanently deleted by administrator", "listing_id": listing_id}


# --- 6. Incident & Dispute Reports ---

@router.get("/reports")
def get_reports(
    resolution: Optional[str] = Query(None, pattern="^(Pending|Resolved|Dismissed)$"),
    admin: model.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(model.Report)
    if resolution:
        query = query.filter(model.Report.admin_resolution == resolution)

    if hasattr(model.Report, "created_at"):
        query = query.order_by(model.Report.created_at.desc())
    else:
        query = query.order_by(model.Report.report_id.desc())

    return query.all()


@router.patch("/reports/{report_id}/resolve")
def resolve_report_and_moderate(
    report_id: str,
    resolution: str = Query(..., pattern="^(Resolved|Dismissed)$"),
    action_taken: Optional[str] = Query(None, pattern="^(None|Suspend_User|Ban_User|Remove_Listing)$"),
    admin: model.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    report = db.query(model.Report).filter(model.Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.admin_resolution = resolution

    if action_taken == "Suspend_User":
        user = db.query(model.User).filter(model.User.user_id == report.reported_entity_id).first()
        if user:
            user.account_status = "Suspended"
    elif action_taken == "Ban_User":
        user = db.query(model.User).filter(model.User.user_id == report.reported_entity_id).first()
        if user:
            user.account_status = "Banned"
    elif action_taken == "Remove_Listing":
        listing = db.query(model.Listing).filter(model.Listing.listing_id == report.reported_entity_id).first()
        if listing:
            listing.status = "Removed"

    db.commit()
    db.refresh(report)

    return {
        "message": "Report processed successfully",
        "report_id": report.report_id,
        "resolution": report.admin_resolution,
        "action_taken": action_taken or "None"
    }


# --- 7. Platform Bookings Audit ---

@router.get("/bookings")
def get_all_bookings(
    status: Optional[str] = None,
    admin: model.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(model.Booking)
    if status:
        query = query.filter(model.Booking.booking_status == status)

    if hasattr(model.Booking, "created_at"):
        query = query.order_by(model.Booking.created_at.desc())
    else:
        query = query.order_by(model.Booking.booking_id.desc())

    return query.all()