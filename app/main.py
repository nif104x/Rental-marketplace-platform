from fastapi import FastAPI
from sqlalchemy import text
from fastapi.staticfiles import StaticFiles

from app.routes import admin, booking, conversation, listings, notification, report, review, search, user, wishlist
from app.db import engine

app = FastAPI()

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


# app.mount("/images", StaticFiles(directory="../frontend/images"), name="images")

@app.get("/")
def home():
    return {"message": "API is running"}

@app.get("/db-test")
def db_test():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"database": "connected"}
