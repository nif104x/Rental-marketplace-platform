from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.controllers.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User, UserProfile
from app.schemas.user import Token, UserCreate, UserProfileUpdate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    hashed_pwd = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        role=user_in.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    new_profile = UserProfile(
        user_id=new_user.id,
        full_name=user_in.full_name,
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive account",
        )

    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/profile", response_model=UserResponse)
def update_profile(
    profile_in: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id, full_name=profile_in.full_name or "")
        db.add(profile)

    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user