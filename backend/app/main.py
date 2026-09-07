from fastapi import FastAPI
from sqlalchemy import text
from fastapi.staticfiles import StaticFiles

from backend.app.db import engine
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routes import admin, booking, conversation, listings, login, notification, report, review, search, user, wishlist
from pathlib import Path

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(admin.router)
app.include_router(booking.router)
app.include_router(conversation.router)
app.include_router(listings.router)
app.include_router(notification.router)
app.include_router(report.router)
app.include_router(review.router)
app.include_router(search.router)
app.include_router(user.router)
app.include_router(wishlist.router)
app.include_router(login.router)


# app.mount("/images", StaticFiles(directory="../frontend/images"), name="images")

@app.get("/")
def home():
    return {"message": "API is running"}

@app.get("/db-test")
def db_test():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"database": "connected"}
