from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.db import get_db
from app import schema
from app import model
from app import auth
from datetime import datetime, timedelta, timezone
import uuid

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


