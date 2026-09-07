from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timedelta

from backend.app.db import get_db
from backend.app import schema, model, auth

router = APIRouter(prefix="/login", tags=["login"])

@router.post("")
@router.post("/")
def login(data: schema.userlogin, db: Session = Depends(get_db)):
    user = db.query(model.User).filter(
        func.lower(model.User.email) == data.email.strip().lower()
    ).first()

    if not user or user.encrypted_credentials != data.password:
        raise HTTPException(status_code=404, detail="Invalid credential")[cite: 4]

    if user.account_status in ["Suspended", "Banned"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.account_status}"
        )

    access_token = auth.create_access_token(
        data={"user_id": user.user_id, "role": user.role},
        expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.user_id,
        "role": user.role
    }