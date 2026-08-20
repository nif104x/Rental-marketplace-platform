# from fastapi import FastAPI, HTTPException, status, Response, Depends, APIRouter
# from sqlalchemy.orm import Session, joinedload
# from sqlalchemy import func

# from app.organizer.database import get_db
# from app.organizer import models, schemas, utils, ouath2, database
# from app.organizer.routers import auth

# import uuid

# # For jinja2 templates
# from fastapi import Request, Form
# from fastapi.templating import Jinja2Templates
# from fastapi.responses import RedirectResponse, HTMLResponse


# templates = Jinja2Templates(directory="app/organizer/templates")


# router = APIRouter(
#     prefix="/organizer",
#     tags = ["organizer"]
# )



# # @router.get("/", response_model=list[schemas.OrganizerInfoSchema])
# # def homePage(db: Session=Depends(get_db), current_user: models.OrganizerInfo = Depends(ouath2.get_current_user)):
# #     users = db.query(models.OrganizerInfo).all()
# #     return users

# @router.get("/dashboard", name="dashboard", include_in_schema=False)
# def dashboard_page(request: Request, current_user: models.OrganizerInfo = Depends(ouath2.get_current_user), db: Session=Depends(get_db)):
#     analytics = db.query(models.VendorAnalytics).filter(models.VendorAnalytics.org_id==current_user.org_id).first()
    
#     orders_pending = db.query(models.Event).filter(
#         models.Event.org_id == current_user.org_id,
#         models.Event.status == "Pending"
#     ).all()

#     gigs = db.query(models.ServiceListing).options(
#         joinedload(models.ServiceListing.images)
#     ).filter(
#         models.ServiceListing.org_id == current_user.org_id
#     ).all()

#     average_rating = db.query(func.avg(models.VendorReview.rating)).filter(
#         models.VendorReview.vendor_id == current_user.org_id
#         ).scalar()
    
#     display_rating = round(average_rating, 1) if average_rating else "0.0"

#     completed = db.query(models.Event).options(
#         joinedload(models.Event.order) 
#     ).filter(
#         models.Event.org_id == current_user.org_id,
#         models.Event.status == "Completed" 
#     ).all()

#     return templates.TemplateResponse(
#         request=request, 
#         name="organizer/dashboard.html", 
#         context={
#             "request": request, 
#             "user": current_user, 
#             "gigs": gigs,             
#             "analytics": analytics, 
#             "pending": orders_pending,
#             "rating": display_rating,
#             "completed": completed
#         }
#     )







# @router.get("/creategig", name="creategig", include_in_schema=False)
# def creategig(request: Request):
#     return templates.TemplateResponse(request, "organizer/creategig.html", {'data':1})


# @router.post("/creategig", name="handle_create_gig", include_in_schema=False)
# def handle_create_gig(
#     request: Request,
#     form:schemas.GigCreateRequest = Depends(),
#     db:Session=Depends(get_db),
#     current_user: models.OrganizerInfo = Depends(ouath2.get_current_user)
# ):
#     listing_id = f"LIST-{uuid.uuid4().hex[:6].upper()}"
#     new_gig = models.ServiceListing(
#         id=listing_id,
#         org_id=current_user.org_id,
#         title = form.title,
#         category=form.category,
#         base_price = form.base_price
#     )
#     db.add(new_gig)
#     image_id = f"IMG-{uuid.uuid4().hex[:6].upper()}"
#     new_image = models.ListingImage(
#         id=image_id,
#         listing_id=listing_id,
#         image_url=form.image_url
#     )
#     db.add(new_image)

#     for name, price in zip(form.addon_names, form.addon_prices):
#         if name.strip():  
#             addon_id = f"ADD-{str(uuid.uuid4())[:8]}"
#             new_addon = models.ServiceAddon(
#                 id=addon_id,
#                 listing_id=listing_id,
#                 addon_name=name,
#                 price=price
#             )
#             db.add(new_addon)

#     db.commit()

#     return RedirectResponse(
#         url=request.url_for("dashboard"), 
#         status_code=303
#     )



# ## Registration ##
# @router.post("/registration", status_code=status.HTTP_201_CREATED)
# def user_registration(data:schemas.OrganizerRegisterSchema, db : Session=Depends(get_db)):
#     new_user_id = f"ORG-{uuid.uuid4().hex[:6].upper()}"
#     hashed_password = utils.hash_password(data.password)
#     if db.query(models.OrganizerInfo).filter(models.OrganizerInfo.email==data.email).first():
#         raise HTTPException(400, "Email already exist")
#     # insert into user_main
#     user = models.UserMain(
#         id = new_user_id,
#         username = data.username,
#         password = hashed_password,
#         role = data.role
#     )
#     db.add(user)

#     # insert into organizer_info
#     organizer = models.OrganizerInfo(
#             org_id = new_user_id,
#             email = data.email,
#             company_name = data.company_name,
#             primary_category = data.primary_category,
#             is_verified = data.is_verified,      
#     )
#     db.add(organizer)
#     db.commit()
#     return{"message": "Organizer created successfully"}




# # LOG IN HANDLING:
# @router.get("/login", name="login", response_class=HTMLResponse)
# def login_page(request: Request):
#     return templates.TemplateResponse(request,"organizer/login.html", {"request": request})

# from datetime import timedelta

# @router.post("/login", name="login_post")
# def login(request:Request, username:str=Form(...), password: str = Form(...), db: Session=Depends(database.get_db)):
    
#     user = db.query(models.UserMain).filter(models.UserMain.username==username).first()
#     if not user:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Invalid credential")
    
#     if user.password != password:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Invalid credential")

#     access_token = ouath2.create_access_token(
#         data = {"user_id": user.id},
#         expires_delta=timedelta(minutes=ouath2.ACCESS_TOKEN_EXPIRE_MINUTES)
#     )

#     redirect = RedirectResponse(url= request.url_for("dashboard"), status_code=status.HTTP_303_SEE_OTHER)
#     redirect.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, path="/")

#     return redirect