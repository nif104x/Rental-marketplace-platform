from dataclasses import dataclass
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.admin.schemas import AdminSetUserStatusIn
from app.paths import APP_DIR
from app.database import get_db
from app.organizer import ouath2 as organizer_oauth2
from app.organizer import utils as organizer_utils
from app.models import (
    AdminInfo,
    Event,
    EventAddonSelection,
    EventOrder,
    OrganizerInfo,
    ServiceListing,
    UserMain,
    UserStatus,
)
from app.tasks.services.reminders import send_customer_due_reminders

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=str(APP_DIR / "admin" / "templates"))

def _set_no_store(resp) -> None:
    """
    Prevent browser caching (incl. bfcache heuristics) for admin pages.
    This mitigates Back-button showing stale authenticated HTML after logout.
    """
    try:
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    except Exception:
        pass



@dataclass(frozen=True)
class AdminSession:
    user_id: str
    username: str
    source: str  # "hardcoded" | "db"


def _role_is_admin(role_val) -> bool:
    role = str(role_val or "").strip()
    return role == "Admin" or role.endswith(".Admin")


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> AdminSession:
    """
    Cookie-auth like organizer portal, but must resolve to an Admin profile.
    Raises 401 (JSON routes); UI routes should catch and redirect.
    """
    token_cookie = request.cookies.get("access_token")
    if not token_cookie or not token_cookie.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized")
    token = token_cookie.split(" ", 1)[1].strip()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = organizer_oauth2.verify_access_token(token, credentials_exception)


    admin = (
        db.query(AdminInfo)
        .options(joinedload(AdminInfo.user))
        .filter(AdminInfo.admin_id == token_data.id)
        .first()
    )
    if admin is None or admin.user is None or not _role_is_admin(admin.user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an admin session")
    return AdminSession(
        user_id=str(admin.admin_id),
        username=str(admin.user.username),
        source="db",
    )


def require_admin_ui(
    request: Request, db: Session = Depends(get_db)
) -> AdminSession | RedirectResponse:
    try:
        return get_current_admin(request=request, db=db)
    except HTTPException:
        nxt = quote(str(request.url), safe="")
        return RedirectResponse(url=f"/admin/login?next={nxt}", status_code=303)


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def admin_login_page(request: Request, next: str | None = None):
    resp = templates.TemplateResponse(
        request,
        "admin/login.html",
        {
            "request": request,
            "next": next or "/admin/ui",
            "role_badge": "Admin",
            "nav_active": "admin",
        },
    )
    _set_no_store(resp)
    return resp


@router.post("/login", include_in_schema=False)
def admin_login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    uname = (username or "").strip()
    pwd = (password or "").strip()

    user = db.query(UserMain).filter(UserMain.username == uname).first()
    if user is None or not organizer_utils.password_matches_stored(pwd, user.password):
        # Keep message generic: don't leak whether username exists.
        raise HTTPException(status_code=404, detail="Invalid credential")
    if not _role_is_admin(user.role):
        raise HTTPException(status_code=403, detail="Not an admin account")
    admin = db.query(AdminInfo).filter(AdminInfo.admin_id == user.id).first()
    if admin is None:
        raise HTTPException(status_code=403, detail="Admin profile missing")

    access_token = organizer_oauth2.create_access_token(
        data={"user_id": user.id},
        expires_delta=None,
    )
    redirect_to = (next or "/admin/ui").strip() or "/admin/ui"
    resp = RedirectResponse(url=redirect_to, status_code=303)
    resp.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, path="/")
    _set_no_store(resp)
    return resp


@router.post("/logout", include_in_schema=False)
def admin_logout(next: str | None = Form(default=None)):
    resp = RedirectResponse(url=(next or "/admin/login").strip() or "/admin/login", status_code=303)
    resp.delete_cookie(key="access_token", path="/")
    _set_no_store(resp)
    return resp


def _admin_ui_data(db: Session):
    listings = (
        db.query(ServiceListing, OrganizerInfo.company_name)
        .outerjoin(OrganizerInfo, ServiceListing.org_id == OrganizerInfo.org_id)
        .order_by(ServiceListing.id)
        .all()
    )

    orders = (
        db.query(EventOrder)
        .options(
            joinedload(EventOrder.event).joinedload(Event.customer),
            joinedload(EventOrder.event).joinedload(Event.organizer),
            joinedload(EventOrder.listing),
            joinedload(EventOrder.selections).joinedload(EventAddonSelection.addon),
        )
        .order_by(EventOrder.id)
        .all()
    )

    users = (
        db.query(UserMain, UserStatus)
        .outerjoin(UserStatus, UserMain.id == UserStatus.user_id)
        .order_by(UserMain.id)
        .all()
    )

    return listings, orders, users


@router.get("/listings")
def listings(
    db: Session = Depends(get_db),
    _: AdminSession = Depends(get_current_admin),
):
    rows = (
        db.query(ServiceListing, OrganizerInfo.company_name)
        .outerjoin(OrganizerInfo, ServiceListing.org_id == OrganizerInfo.org_id)
        .order_by(ServiceListing.id)
        .all()
    )
    out = []
    for sl, company_name in rows:
        out.append(
            {
                "id": sl.id,
                "org_id": sl.org_id,
                "company_name": company_name,
                "category": sl.category,
                "title": sl.title,
                "base_price": float(sl.base_price),
                "is_deleted": bool(sl.is_deleted) if sl.is_deleted is not None else False,
            }
        )
    return out


@router.delete("/listings/{listing_id}")
def delete_listing(
    listing_id: str,
    db: Session = Depends(get_db),
    _: AdminSession = Depends(get_current_admin),
):
    listing = db.query(ServiceListing).filter(ServiceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.is_deleted = True
    db.commit()
    return {"message": "Listing deleted"}


@router.get("/orders")
def orders(
    db: Session = Depends(get_db),
    _: AdminSession = Depends(get_current_admin),
):
    base_rows = (
        db.query(EventOrder)
        .options(
            joinedload(EventOrder.event).joinedload(Event.customer),
            joinedload(EventOrder.event).joinedload(Event.organizer),
            joinedload(EventOrder.listing),
            joinedload(EventOrder.selections).joinedload(EventAddonSelection.addon),
        )
        .order_by(EventOrder.id)
        .all()
    )

    out = []
    for eo in base_rows:
        ev = eo.event
        sl = eo.listing
        oi = ev.organizer if ev else None
        ci = ev.customer if ev else None
        addons = []
        for sel in eo.selections or []:
            ad = sel.addon
            addons.append(
                {
                    "addon_id": sel.addon_id,
                    "addon_name": ad.addon_name if ad else None,
                    "unit_price": float(sel.unit_price),
                }
            )
        addons_total = sum(a["unit_price"] for a in addons)
        base_price = float(eo.base_price_at_booking)
        out.append(
            {
                "order_id": eo.id,
                "event_id": eo.event_id,
                "listing_id": eo.listing_id,
                "listing_title": sl.title if sl else None,
                "org_id": ev.org_id if ev else None,
                "organizer_name": oi.company_name if oi else None,
                "customer_id": ev.customer_id if ev else None,
                "customer_name": ci.full_name if ci else None,
                "event_date": str(ev.event_date) if ev and ev.event_date else None,
                "event_status": ev.status if ev else None,
                "payment_status": eo.payment_status,
                "base_price_at_booking": base_price,
                "addons": addons,
                "addons_total": addons_total,
                "total_price_calculated": base_price + addons_total,
            }
        )
    return out


@router.get("/users")
def users(
    db: Session = Depends(get_db),
    _: AdminSession = Depends(get_current_admin),
):
    rows = (
        db.query(UserMain, UserStatus)
        .outerjoin(UserStatus, UserMain.id == UserStatus.user_id)
        .order_by(UserMain.id)
        .all()
    )
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "status": s.status if s else "Active",
        }
        for u, s in rows
    ]


@router.patch("/users/{user_id}/status")
def set_status(
    user_id: str,
    body: AdminSetUserStatusIn,
    db: Session = Depends(get_db),
    _: AdminSession = Depends(get_current_admin),
):
    user = db.query(UserMain).filter(UserMain.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    row = db.query(UserStatus).filter(UserStatus.user_id == user_id).first()
    if row:
        row.status = body.status
        row.reason = body.reason
    else:
        db.add(UserStatus(user_id=user_id, status=body.status, reason=body.reason))
    db.commit()
    return {"message": "User status updated"}


@router.get("/ui", response_class=HTMLResponse)
def admin_ui(
    request: Request,
    db: Session = Depends(get_db),
    admin_or_redirect: AdminSession | RedirectResponse = Depends(require_admin_ui),
):
    if isinstance(admin_or_redirect, RedirectResponse):
        return admin_or_redirect
    listings, orders, users = _admin_ui_data(db)

    resp = templates.TemplateResponse(
        request,
        "admin/admin.html",
        {
            "listings": listings,
            "orders": orders,
            "users": users,
            "nav_active": "admin",
            "role_badge": "Admin",
            "admin_user": admin_or_redirect,
        },
    )
    _set_no_store(resp)
    return resp

@router.post("/ui/send-customer-reminders")
def admin_ui_send_customer_reminders(
    request: Request,
    db: Session = Depends(get_db),
    admin_or_redirect: AdminSession | RedirectResponse = Depends(require_admin_ui),
):
    if isinstance(admin_or_redirect, RedirectResponse):
        return admin_or_redirect
    result = send_customer_due_reminders(db, manual=True)
    listings, orders, users = _admin_ui_data(db)
    resp = templates.TemplateResponse(
        request,
        "admin/admin.html",
        {
            "listings": listings,
            "orders": orders,
            "users": users,
            "nav_active": "admin",
            "role_badge": "Admin",
            "admin_user": admin_or_redirect,
            "task_result": result,
            "initial_tab": "orders",
        },
    )
    _set_no_store(resp)
    return resp


@router.post("/ui/listings/{listing_id}/toggle-delete")
def admin_ui_toggle_listing_deleted(
    listing_id: str,
    tab: str | None = Form(default=None),
    db: Session = Depends(get_db),
    admin_or_redirect: AdminSession | RedirectResponse = Depends(require_admin_ui),
):
    if isinstance(admin_or_redirect, RedirectResponse):
        return admin_or_redirect
    listing = db.query(ServiceListing).filter(ServiceListing.id == listing_id).first()
    if listing:
        if listing.is_deleted:
            listing.is_deleted = False
        else:
            listing.is_deleted = True
        db.commit()
    safe_tab = tab if tab in {"listings", "orders", "users"} else "listings"
    return RedirectResponse(url=f"/admin/ui?tab={safe_tab}", status_code=303)


@router.post("/ui/users/{user_id}/status")
def admin_ui_set_user_status(
    user_id: str,
    status: str = Form(...),
    reason: str | None = Form(default=None),
    tab: str | None = Form(default=None),
    db: Session = Depends(get_db),
    admin_or_redirect: AdminSession | RedirectResponse = Depends(require_admin_ui),
):
    if isinstance(admin_or_redirect, RedirectResponse):
        return admin_or_redirect
    user = db.query(UserMain).filter(UserMain.id == user_id).first()
    if user:
        row = db.query(UserStatus).filter(UserStatus.user_id == user_id).first()
        if row:
            row.status = status
            row.reason = reason
        else:
            db.add(UserStatus(user_id=user_id, status=status, reason=reason))
        db.commit()
    safe_tab = tab if tab in {"listings", "orders", "users"} else "users"
    return RedirectResponse(url=f"/admin/ui?tab={safe_tab}", status_code=303)
