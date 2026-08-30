from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

# Base Review Properties
class ReviewBase(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating must be between 1 and 5")
    comment: Optional[str] = None

# Creation Input
class ReviewCreate(ReviewBase):
    booking_id: int

# Response Output
class ReviewResponse(ReviewBase):
    id: int
    booking_id: int
    reviewer_id: int
    reviewee_id: int
    created_at: datetime

    class Config:
        from_attributes = True