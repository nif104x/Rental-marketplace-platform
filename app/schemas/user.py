from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole

# Shared properties for profiles
class UserProfileBase(BaseModel):
    full_name: str
    bio: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    avatar_url: Optional[str] = None

class UserProfileUpdate(UserProfileBase):
    full_name: Optional[str] = None

class UserProfileResponse(UserProfileBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

# User Registration Input
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Optional[UserRole] = UserRole.LESSEE

# User Response Output
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    profile: Optional[UserProfileResponse] = None

    class Config:
        from_attributes = True

# JWT Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None