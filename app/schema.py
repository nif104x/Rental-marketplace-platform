from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

# ==========================================
# USER SCHEMAS
# ==========================================
class UserBase(BaseModel):
    role: str
    contact_details: str # E.g., email or phone
    mfa_enabled: Optional[bool] = False
    personal_bio: Optional[str] = None
    location_preferences: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., description="Raw password to be hashed in backend")

class UserResponse(UserBase):
    user_id: int
    verification_status: str
    account_status: str

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# LISTING & IMAGE SCHEMAS
# ==========================================
class ImageBase(BaseModel):
    image_file_url: str
    is_primary_preview: Optional[bool] = False

class ImageResponse(ImageBase):
    image_id: int
    listing_id: int
    model_config = ConfigDict(from_attributes=True)

class ListingBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    rental_rate_hourly: Optional[Decimal] = None
    rental_rate_daily: Optional[Decimal] = None
    rental_rate_weekly: Optional[Decimal] = None
    seasonal_pricing_tiers: Optional[List[Dict[str, Any]]] = None
    security_deposit: Optional[Decimal] = 0.00
    item_rules: Optional[str] = None
    availability_schedules: Optional[Dict[str, Any]] = None
    geo_location: Optional[str] = None
    keywords_semantic_tags: Optional[List[str]] = None

class ListingCreate(ListingBase):
    pass # lessor_id will be extracted from current logged-in user

class ListingResponse(ListingBase):
    listing_id: int
    lessor_id: int
    status: str
    images: List[ImageResponse] = [] # Includes nested images

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# BOOKING & PAYMENT SCHEMAS
# ==========================================
class BookingBase(BaseModel):
    start_period: datetime
    end_period: datetime
    rental_cost: Decimal
    deposit_held: Optional[Decimal] = 0.00
    service_fee: Optional[Decimal] = 0.00

class BookingCreate(BookingBase):
    listing_id: int

class BookingResponse(BookingBase):
    booking_id: int
    listing_id: int
    lessee_id: int
    booking_status: str
    lessor_condition_verified: bool
    lessee_condition_verified: bool

    model_config = ConfigDict(from_attributes=True)

class PaymentResponse(BaseModel):
    payment_id: int
    booking_id: int
    payment_status: str
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# WISHLIST SCHEMAS
# ==========================================
class WishlistCreate(BaseModel):
    listing_id: int

class WishlistResponse(BaseModel):
    wishlist_id: int
    user_id: int
    listing_id: int
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# MESSAGING SCHEMAS
# ==========================================
class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    message_id: int
    conversation_id: int
    sender_id: int
    is_read: bool
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class ConversationResponse(BaseModel):
    conversation_id: int
    listing_id: int
    booking_id: Optional[int] = None
    lessor_id: int
    lessee_id: int
    created_at: datetime
    last_message_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# REVIEW & REPORT SCHEMAS
# ==========================================
class ReviewCreate(BaseModel):
    target_user_id: Optional[int] = None
    target_listing_id: Optional[int] = None
    rating_score: Decimal = Field(..., ge=0, le=5)
    qualitative_review: Optional[str] = None

class ReviewResponse(ReviewCreate):
    review_id: int
    reviewer_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ReportCreate(BaseModel):
    reported_entity_id: int
    flag_reason: str

class ReportResponse(ReportCreate):
    report_id: int
    reporter_id: int
    admin_resolution: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)