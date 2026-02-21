"""
app/api/booking.py
==================
Furniture Booking API – create, list, view, cancel bookings.

Business rules:
  • A user cannot have two PENDING bookings for the same furniture_id.
  • Cancellation is allowed only for 'pending' or 'confirmed' status.
  • Cancellation reason is stored for analytics.

Routes:
  POST   /api/booking/               – Create a new booking
  GET    /api/booking/               – List user's bookings
  GET    /api/booking/<id>           – Get single booking
  POST   /api/booking/<id>/cancel    – Cancel a booking
  GET    /api/booking/catalogue      – Browse available furniture catalogue
"""

from datetime import date

from flask import Blueprint, request
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from app import db, limiter
from app.models.booking import FurnitureBooking
from app.utils.security import (
    api_success, api_error, login_required_api,
    sanitise_text, get_json_body, paginate_query,
)

booking_bp = Blueprint("booking", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# FURNITURE CATALOGUE  (static data in lieu of a product DB)
# ─────────────────────────────────────────────────────────────────────────────
FURNITURE_CATALOGUE: list[dict] = [
    {"id": "SOF-MOD-001", "name": "Sectional Sofa",          "category": "Seating",   "style": "Modern",       "price_inr": 45000, "in_stock": True},
    {"id": "SOF-TRD-002", "name": "Teak Diwan",              "category": "Seating",   "style": "Traditional",  "price_inr": 35000, "in_stock": True},
    {"id": "TBL-MOD-003", "name": "Glass Coffee Table",      "category": "Table",     "style": "Modern",       "price_inr": 12000, "in_stock": True},
    {"id": "BED-MIN-004", "name": "Platform Bed (Queen)",    "category": "Sleeping",  "style": "Minimalist",   "price_inr": 28000, "in_stock": True},
    {"id": "SHL-MOD-005", "name": "Modular Bookshelf",       "category": "Storage",   "style": "Modern",       "price_inr": 18000, "in_stock": False},
    {"id": "CHR-BOH-006", "name": "Rattan Peacock Chair",    "category": "Seating",   "style": "Bohemian",     "price_inr": 15000, "in_stock": True},
    {"id": "RUG-BOH-007", "name": "Persian Area Rug (8×10)", "category": "Textiles",  "style": "Bohemian",     "price_inr": 20000, "in_stock": True},
    {"id": "LMP-MOD-008", "name": "Arc Floor Lamp",          "category": "Lighting",  "style": "Modern",       "price_inr": 5500,  "in_stock": True},
    {"id": "CAB-TRD-009", "name": "Carved Wooden Cabinet",   "category": "Storage",   "style": "Traditional",  "price_inr": 55000, "in_stock": True},
    {"id": "PLN-NAT-010", "name": "Monstera Plant + Pot",    "category": "Decor",     "style": "Biophilic",    "price_inr": 2500,  "in_stock": True},
    {"id": "MIR-MOD-011", "name": "Oversized Round Mirror",  "category": "Decor",     "style": "Modern",       "price_inr": 8500,  "in_stock": True},
    {"id": "SOF-HAV-012", "name": "Jharokha Frame (Decor)",  "category": "Architectural","style": "Haveli",    "price_inr": 65000, "in_stock": True},
]

_CATALOGUE_MAP: dict[str, dict] = {item["id"]: item for item in FURNITURE_CATALOGUE}


# ─────────────────────────────────────────────────────────────────────────────
# BROWSE CATALOGUE
# ─────────────────────────────────────────────────────────────────────────────
@booking_bp.get("/catalogue")
def browse_catalogue():
    """
    Return the furniture catalogue with optional filtering.

    Query params:
        style     – filter by style name
        category  – filter by category
        in_stock  – '1' for in-stock only
    """
    items   = list(FURNITURE_CATALOGUE)
    style   = request.args.get("style",    "").strip()
    cat     = request.args.get("category", "").strip()
    in_stock = request.args.get("in_stock")

    if style:
        items = [i for i in items if i["style"].lower() == style.lower()]
    if cat:
        items = [i for i in items if i["category"].lower() == cat.lower()]
    if in_stock == "1":
        items = [i for i in items if i["in_stock"]]

    return api_success(
        data={
            "catalogue": items,
            "total":     len(items),
            "filters": {"style": style, "category": cat},
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# CREATE BOOKING
# ─────────────────────────────────────────────────────────────────────────────
@booking_bp.post("/")
@login_required_api
@limiter.limit("20 per hour")
def create_booking():
    """
    Book a furniture item.

    Body (JSON):
        furniture_id       (str, required)  – catalogue ID e.g. "SOF-MOD-001"
        quantity           (int, optional)  – default 1
        delivery_address   (str, required)
        delivery_date      (str, optional)  – ISO date "YYYY-MM-DD"
        delivery_notes     (str, optional)
        design_project_id  (int, optional)  – link to a design project

    Business rules:
        - furniture_id must exist in catalogue
        - item must be in_stock
        - no duplicate pending booking for the same furniture_id + user
    """
    data, err = get_json_body(furniture_id="str", delivery_address="str")
    if err:
        return api_error(err, 400)

    furniture_id     = data["furniture_id"].strip().upper()
    delivery_address = sanitise_text(data["delivery_address"], 500)
    quantity         = int(data.get("quantity", 1))
    delivery_notes   = sanitise_text(data.get("delivery_notes", ""), 300)
    design_project_id = data.get("design_project_id")

    # Validate quantity
    if quantity < 1 or quantity > 20:
        return api_error("Quantity must be between 1 and 20.", 400)

    # Validate delivery address
    if len(delivery_address) < 10:
        return api_error("Please provide a complete delivery address.", 400)

    # Parse delivery date
    delivery_date = None
    if data.get("delivery_date"):
        try:
            delivery_date = date.fromisoformat(data["delivery_date"])
            if delivery_date < date.today():
                return api_error("Delivery date cannot be in the past.", 400)
        except ValueError:
            return api_error("Invalid delivery_date format. Use YYYY-MM-DD.", 400)

    # Validate against catalogue
    item = _CATALOGUE_MAP.get(furniture_id)
    if not item:
        return api_error(f"Furniture ID '{furniture_id}' not found in catalogue.", 404)
    if not item["in_stock"]:
        return api_error(f"'{item['name']}' is currently out of stock.", 409)

    # Duplicate pending booking check
    existing = FurnitureBooking.query.filter_by(
        user_id=current_user.id,
        furniture_id=furniture_id,
        status="pending",
    ).first()
    if existing:
        return api_error(
            f"You already have a pending booking for '{item['name']}' "
            f"(Booking #{existing.id}). Cancel it before creating a new one.",
            409,
        )

    # Create booking
    unit_price = item.get("price_inr", 0)
    booking = FurnitureBooking(
        user_id          = current_user.id,
        furniture_id     = furniture_id,
        furniture_name   = item["name"],
        furniture_category = item.get("category"),
        furniture_style    = item.get("style"),
        quantity         = quantity,
        unit_price       = unit_price,
        delivery_address = delivery_address,
        delivery_date    = delivery_date,
        delivery_notes   = delivery_notes or None,
        design_project_id = int(design_project_id) if design_project_id else None,
        status           = "pending",
    )
    booking.compute_total()

    try:
        db.session.add(booking)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_error(
            f"You already have a pending booking for '{item['name']}'.", 409
        )
    except Exception as e:
        db.session.rollback()
        return api_error("Failed to create booking. Please try again.", 500)

    return api_success(
        data=booking.to_dict(),
        message=f"Booking confirmed for '{item['name']}'! "
                f"Estimated delivery: {delivery_date or 'TBD'}.",
        status_code=201,
    )


# ─────────────────────────────────────────────────────────────────────────────
# LIST BOOKINGS
# ─────────────────────────────────────────────────────────────────────────────
@booking_bp.get("/")
@login_required_api
def list_bookings():
    """
    Return paginated list of the authenticated user's bookings.

    Query params:
        status   (str, optional)  – filter by status
        page     (int, default 1)
        per_page (int, default 20)
    """
    page     = max(1, request.args.get("page",     1,  type=int))
    per_page = max(1, request.args.get("per_page", 20, type=int))
    status   = request.args.get("status")

    query = FurnitureBooking.query.filter_by(user_id=current_user.id).order_by(
        FurnitureBooking.created_at.desc()
    )
    if status:
        query = query.filter_by(status=status)

    paged = paginate_query(query, page=page, per_page=per_page)
    return api_success(data=paged)


# ─────────────────────────────────────────────────────────────────────────────
# GET SINGLE BOOKING
# ─────────────────────────────────────────────────────────────────────────────
@booking_bp.get("/<int:booking_id>")
@login_required_api
def get_booking(booking_id: int):
    """Return details of a single booking (must belong to current user)."""
    booking = FurnitureBooking.query.filter_by(
        id=booking_id, user_id=current_user.id
    ).first_or_404()
    return api_success(data=booking.to_dict())


# ─────────────────────────────────────────────────────────────────────────────
# CANCEL BOOKING
# ─────────────────────────────────────────────────────────────────────────────
@booking_bp.post("/<int:booking_id>/cancel")
@login_required_api
@limiter.limit("10 per hour")
def cancel_booking(booking_id: int):
    """
    Cancel a pending or confirmed booking.

    Body (JSON):
        reason (str, optional) – cancellation reason

    Business rules:
        - Only 'pending' or 'confirmed' bookings may be cancelled.
        - Delivered or already-cancelled bookings return 409.
    """
    booking = FurnitureBooking.query.filter_by(
        id=booking_id, user_id=current_user.id
    ).first_or_404()

    if not booking.is_cancellable:
        return api_error(
            f"Booking #{booking_id} cannot be cancelled "
            f"(current status: '{booking.status}').",
            409,
        )

    data   = request.get_json(silent=True) or {}
    reason = sanitise_text(data.get("reason", "Cancelled by customer"), 300)

    booking.cancel(reason=reason)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return api_error("Failed to cancel booking.", 500)

    return api_success(
        data=booking.to_dict(),
        message=f"Booking #{booking_id} has been cancelled.",
    )
