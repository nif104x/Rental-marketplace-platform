from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

# ==========================================
# USER SCHEMAS
# ==========================================
class UserBase(BaseModel):
    contact_details: str
    personal_bio: Optional[str] = None
    location_preferences: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., description="Raw password to be hashed in backend")

class UserResponse(UserBase):
    user_id: str
    verification_status: str
    account_status: str

    model_config = ConfigDict(from_attributes=True)

class userlogin(BaseModel):
    email: str
    password: str
# ==========================================
# LISTING & IMAGE SCHEMAS
# ==========================================
class ImageBase(BaseModel):
    image_file_url: str
    is_primary_preview: Optional[bool] = False

class ImageCreate(ImageBase):
    pass

class ImageResponse(ImageBase):
    image_id: str
    listing_id: str

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
    pass

class ListingResponse(ListingBase):
    listing_id: str
    lessor_id: str
    status: str
    images: List[ImageResponse] = []

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
    listing_id: str

class BookingResponse(BookingBase):
    booking_id: str
    listing_id: str
    lessee_id: str
    booking_status: str
    lessor_condition_verified: bool
    lessee_condition_verified: bool

    model_config = ConfigDict(from_attributes=True)

class PaymentResponse(BaseModel):
    payment_id: str
    booking_id: str
    payment_status: str

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# WISHLIST SCHEMAS
# ==========================================
class WishlistCreate(BaseModel):
    listing_id: str

class WishlistResponse(BaseModel):
    wishlist_id: str
    user_id: str
    listing_id: str

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# MESSAGING SCHEMAS
# ==========================================
class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    message_id: str
    conversation_id: str
    sender_id: str
    is_read: bool
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class ConversationResponse(BaseModel):
    conversation_id: str
    listing_id: str
    booking_id: Optional[str] = None
    lessor_id: str
    lessee_id: str
    created_at: datetime
    last_message_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# NOTIFICATION SCHEMAS
# ==========================================
class NotificationResponse(BaseModel):
    notification_id: str
    user_id: str
    delivery_method: str
    type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# REVIEW & REPORT SCHEMAS
# ==========================================
class ReviewCreate(BaseModel):
    target_user_id: Optional[str] = None
    target_listing_id: Optional[str] = None
    rating_score: Decimal = Field(..., ge=0, le=5)
    qualitative_review: Optional[str] = None

class ReviewResponse(ReviewCreate):
    review_id: str
    reviewer_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ReportCreate(BaseModel):
    reported_entity_id: str
    flag_reason: str

class ReportResponse(ReportCreate):
    report_id: str
    reporter_id: str
    admin_resolution: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)