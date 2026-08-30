import enum
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class RateType(str, enum.Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"

class ListingStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    SUSPENDED = "suspended"

class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    lessor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, index=True, nullable=False)
    rental_rate = Column(Float, nullable=False)
    rate_type = Column(Enum(RateType), default=RateType.DAILY, nullable=False)
    security_deposit = Column(Float, default=0.0, nullable=False)
    rules = Column(Text, nullable=True)
    location = Column(String, index=True, nullable=True)
    status = Column(Enum(ListingStatus), default=ListingStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    lessor = relationship("User", back_populates="listings")
    images = relationship("ListingImage", back_populates="listing", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="listing")

class ListingImage(Base):
    __tablename__ = "listing_images"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    image_url = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)

    # Relationships
    listing = relationship("Listing", back_populates="images")
