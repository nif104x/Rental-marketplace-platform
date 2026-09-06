from fastapi import FastAPI, APIRouter, Depends, HTTPException
from backend.app.db import get_db
from backend.app import schema
from backend.app import model
from backend.app import auth
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/login", tags=["login"])


@router.post("/")
def login(data:schema.userlogin, db=Depends(get_db)):
    user = db.query(model.User).filter(model.User.email==data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"Invalid credential")

    if user.encrypted_credentials!= data.password:
        raise HTTPException(status_code=404, detail=f"Invalid credential")

    access_token = auth.create_access_token(
        data = {"user_id": user.user_id},
        expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer"}