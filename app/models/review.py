from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
    )

    # Relationships
    booking = relationship("Booking", back_populates="review")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    reviewee = relationship("User", foreign_keys=[reviewee_id])