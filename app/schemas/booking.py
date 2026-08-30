from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.booking import BookingStatus
from app.schemas.listing import ListingResponse

# Base Booking properties
class BookingBase(BaseModel):
    start_date: datetime
    end_date: datetime

# Creation Input (from Lessee)
class BookingCreate(BookingBase):
    listing_id: int

# Status Update Input (from Lessor/Admin)
class BookingStatusUpdate(BaseModel):
    status: BookingStatus
    cancellation_reason: Optional[str] = None

# Response Output
class BookingResponse(BookingBase):
    id: int
    lessee_id: int
    listing_id: int
    total_cost: float
    security_deposit: float
    status: BookingStatus
    cancellation_reason: Optional[str] = None
    created_at: datetime
    listing: Optional[ListingResponse] = None

    class Config:
        from_attributes = True