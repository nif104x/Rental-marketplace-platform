import enum
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class UserRole(str, enum.Enum):
    LESSEE = "lessee"
    LESSOR = "lessor"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.LESSEE, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    listings = relationship("Listing", back_populates="lessor", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="lessee")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    bio = Column(Text, nullable=True)
    phone_number = Column(String, nullable=True)
    location = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="profile")