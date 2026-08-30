import enum
from sqlalchemy import Column, Integer, Float, Enum, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class BookingStatus(str, enum.Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    DECLINED = "declined"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELED = "canceled"

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    lessee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    total_cost = Column(Float, nullable=False)
    security_deposit = Column(Float, default=0.0, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.REQUESTED, nullable=False)
    cancellation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    lessee = relationship("User", back_populates="bookings")
    listing = relationship("Listing", back_populates="bookings")
    review = relationship("Review", back_populates="booking", uselist=False)
    