from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from app.controllers.deps import get_db
from app.models.listing import Listing, ListingStatus
from app.views.renderer import templates

router = APIRouter(tags=["Frontend Views"])

@router.get("/")
def home_page(request: Request, db: Session = Depends(get_db)):
    listings = db.query(Listing).filter(Listing.status == ListingStatus.ACTIVE).all()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"listings": listings}
    )

@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )

@router.get("/listings/new")
def create_listing_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="create_listing.html"
    )

@router.get("/listings/{listing_id}")
def listing_detail_page(request: Request, listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return templates.TemplateResponse(
        request=request,
        name="listing_detail.html",
        context={"listing": listing}
    )

@router.get("/dashboard")
def dashboard_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html"
    )
