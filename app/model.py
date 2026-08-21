import uuid
from sqlalchemy import (
    Column, String, Boolean, Text, Numeric, 
    DateTime, ForeignKey, CheckConstraint, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from app.db import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = 'users'

    user_id = Column(String(64), primary_key=True, default=generate_uuid, index=True)
    role = Column(String(50), nullable=False)
    encrypted_credentials = Column(String(255), nullable=False)
    mfa_enabled = Column(Boolean, default=False)
    contact_details = Column(String(255), nullable=False)
    personal_bio = Column(Text, nullable=True)
    verification_status = Column(String(50), default='Pending')
    location_preferences = Column(Text, nullable=True)
    account_status = Column(String(50), default='Active')

    listings = relationship("Listing", back_populates="lessor", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="lessee")
    wishlist_items = relationship("WishlistItem", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class Listing(Base):
    __tablename__ = 'listings'

    listing_id = Column(String(64), primary_key=True, default=generate_uuid, index=True)
    lessor_id = Column(String(64), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    rental_rate_hourly = Column(Numeric(10, 2), nullable=True)
    rental_rate_daily = Column(Numeric(10, 2), nullable=True)
    rental_rate_weekly = Column(Numeric(10, 2), nullable=True)
    seasonal_pricing_tiers = Column(JSONB, nullable=True)
    security_deposit = Column(Numeric(10, 2), default=0.00)
    item_rules = Column(Text, nullable=True)
    availability_schedules = Column(JSONB, nullable=True)
    geo_location = Column(String(255), nullable=True)
    keywords_semantic_tags = Column(ARRAY(String), nullable=True)
    status = Column(String(50), default='Active')

    lessor = relationship("User", back_populates="listings")
    images = relationship("Image", back_populates="listing", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="listing")


class Image(Base):
    __tablename__ = 'images'

    image_id = Column(String(64), primary_key=True, default=generate_uuid, index=True)
    listing_id = Column(String(64), ForeignKey('listings.listing_id', ondelete='CASCADE'), nullable=False)
    image_file_url = Column(Text, nullable=False)
    is_primary_preview = Column(Boolean, default=False)

    listing = relationship("Listing", back_populates="images")
 

class Booking(Base):
    __tablename__ = 'bookings'

    booking_id = Column(String(64), primary_key=True, default=generate_uuid, index=True)
    listing_id = Column(String(64), ForeignKey('listings.listing_id', ondelete='RESTRICT'), nullable=False)
    lessee_id = Column(String(64), ForeignKey('users.user_id', ondelete='RESTRICT'), nullable=False)
    start_period = Column(DateTime, nullable=False)
    end_period = Column(DateTime, nullable=False)
    rental_cost = Column(Numeric(10, 2), nullable=False)
    deposit_held = Column(Numeric(10, 2), default=0.00)
    service_fee = Column(Numeric(10, 2), default=0.00)
    booking_status = Column(String(50), default='Pending')
    lessor_condition_verified = Column(Boolean, default=False)
    lessee_condition_verified = Column(Boolean, default=False)

    listing = relationship("Listing", back_populates="bookings")
    lessee = relationship("User", back_populates="bookings")
    payment = relationship("Payment", back_populates="booking", uselist=False, cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = 'payments'

    payment_id = Column(String(64), primary_key=True, default=generate_uuid, index=True)
    booking_id = Column(String(64), ForeignKey('bookings.booking_id', ondelete='CASCADE'), nullable=False)
    payment_status = Column(String(50), default='Pending')

    booking = relationship("Booking", back_populates="payment")


class WishlistItem(Base):
    __tablename__ = 'wishlist_items'
    __table_args__ = (UniqueConstraint('user_id', 'listing_id', name='uq_user_listing'),)

    wishlist_id = Column(String(64), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(64), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    listing_id = Column(String(64), ForeignKey('listings.listing_id', ondelete='CASCADE'), nullable=False)

    user = relationship("User", back_populates="wishlist_items")
    listing = relationship("Listing")


class Conversation(Base):
    __tablename__ = 'conversations'

    conversation_id = Column(String(64), primary_key=True, default=generate_uuid, index=True)
    listing_id = Column(String(64), ForeignKey('listings.listing_id', ondelete='CASCADE'), nullable=False)
    booking_id = Column(String(64), ForeignKey('bookings.booking_id', ondelete='SET NULL'), nullable=True)
    lessor_id = Column(String(64), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    lessee_id = Column(String(64), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    last_message_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    lessor = relationship("User", foreign_keys=[lessor_id])
    lessee = relationship("User", foreign_keys=[lessee_id])


class Message(Base):
    __tablename__ = 'messages'

    message_id = Column(String(64), primary_key=True, default=generate_uuid, index=True)
    conversation_id = Column(String(64), ForeignKey('conversations.conversation_id', ondelete='CASCADE'), nullable=False)
    sender_id = Column(String(64), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User")


class Notification(Base):
    __tablename__ = 'notifications'

    notification_id = Column(String(64), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(64), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    delivery_method = Column(String(50), nullable=False)
    type = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="notifications")


class Review(Base):
    __tablename__ = 'reviews'
    __table_args__ = (
        CheckConstraint('target_user_id IS NOT NULL OR target_listing_id IS NOT NULL', name='check_review_target'),
    )

    review_id = Column(String(64), primary_key=True, default=generate_uuid, index=True)
    reviewer_id = Column(String(64), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    target_user_id = Column(String(64), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=True)
    target_listing_id = Column(String(64), ForeignKey('listings.listing_id', ondelete='CASCADE'), nullable=True)
    rating_score = Column(Numeric(3, 2))
    qualitative_review = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    reviewer = relationship("User", foreign_keys=[reviewer_id])


class Report(Base):
    __tablename__ = 'reports'

    report_id = Column(String(64), primary_key=True, default=generate_uuid, index=True)
    reporter_id = Column(String(64), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    reported_entity_id = Column(String(64), nullable=False)
    flag_reason = Column(String(255), nullable=False)
    admin_resolution = Column(String(255), default='Pending')
    created_at = Column(DateTime, server_default=func.now())

    reporter = relationship("User", foreign_keys=[reporter_id])