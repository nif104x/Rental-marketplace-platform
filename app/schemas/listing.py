from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.models.listing import RateType, ListingStatus

# Image Schemas
class ListingImageBase(BaseModel):
    image_url: str
    is_primary: bool = False

class ListingImageCreate(ListingImageBase):
    pass

class ListingImageResponse(ListingImageBase):
    id: int
    listing_id: int

    class Config:
        from_attributes = True

# Base Listing
class ListingBase(BaseModel):
    title: str
    description: str
    category: str
    rental_rate: float
    rate_type: RateType = RateType.DAILY
    security_deposit: float = 0.0
    rules: Optional[str] = None
    location: Optional[str] = None

# Listing Creation Input
class ListingCreate(ListingBase):
    images: Optional[List[ListingImageCreate]] = []

# Listing Update Input
class ListingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    rental_rate: Optional[float] = None
    rate_type: Optional[RateType] = None
    security_deposit: Optional[float] = None
    rules: Optional[str] = None
    location: Optional[str] = None
    status: Optional[ListingStatus] = None

# Listing Output Response
class ListingResponse(ListingBase):
    id: int
    lessor_id: int
    status: ListingStatus
    created_at: datetime
    images: List[ListingImageResponse] = []

    class Config:
        from_attributes = True