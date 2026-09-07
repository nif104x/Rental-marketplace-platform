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



from pathlib import Path
from fastapi.staticfiles import StaticFiles

# Path: backend/app/uploads
APP_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = APP_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 1. Mount /uploads FIRST
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# 2. Mount / (frontend) LAST
FRONTEND_DIR = APP_DIR.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

@app.get("/")
def home():
    return {"message": "API is running"}

@app.get("/db-test")
def db_test():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"database": "connected"}


from fastapi.responses import RedirectResponse

@app.get("/dashboard")
def redirect_to_dashboard_html():
    return RedirectResponse(url="/dashboard.html")
