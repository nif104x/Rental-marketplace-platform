from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.controllers import auth_router, listing_router, booking_router, review_router
from app.controllers.view_controller import router as view_router
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Rental Marketplace Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Views (HTML pages)
app.include_router(view_router)

# API Endpoints
app.include_router(auth_router, prefix="/api")
app.include_router(listing_router, prefix="/api")
app.include_router(booking_router, prefix="/api")
app.include_router(review_router, prefix="/api")