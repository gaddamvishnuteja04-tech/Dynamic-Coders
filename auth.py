"""
app/api/auth.py
===============
Authentication API – Register, Login, Logout, Profile, Password Change.

Routes:
  POST /api/auth/register
  POST /api/auth/login
  POST /api/auth/logout
  GET  /api/auth/me
  PUT  /api/auth/me
  POST /api/auth/change-password
"""

from datetime import datetime, timezone

from flask import Blueprint, request, current_app
from flask_login import login_user, logout_user, current_user

from app import db, limiter
from app.models.user import User
from app.utils.security import (
    api_success, api_error, get_json_body,
    sanitise_text, sanitise_email,
    is_valid_email, is_strong_password,
    login_required_api,
)

auth_bp = Blueprint("auth", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.post("/register")
@limiter.limit("10 per hour")
def register():
    """
    Register a new user.

    Body (JSON):
        name     (str, required)
        email    (str, required)
        password (str, required, ≥8 chars)
        phone    (str, optional)
        role     (str, optional)  homeowner|designer|architect

    Returns 201 on success, 409 if email already registered.
    """
    data, err = get_json_body(name="str", email="str", password="str")
    if err:
        return api_error(err, 400)

    name     = sanitise_text(data["name"], 120)
    email    = sanitise_email(data["email"])
    password = data["password"]
    phone    = sanitise_text(data.get("phone", ""), 20)
    role     = data.get("role", "homeowner")

    # Validate
    if len(name) < 2:
        return api_error("Name must be at least 2 characters.", 400)

    if not is_valid_email(email):
        return api_error("Invalid email address.", 400)

    strong, msg = is_strong_password(password)
    if not strong:
        return api_error(msg, 400)

    allowed_roles = {"homeowner", "designer", "architect"}
    if role not in allowed_roles:
        role = "homeowner"

    # Duplicate check
    if User.query.filter_by(email=email).first():
        return api_error("An account with this email already exists.", 409)

    # Create user
    user = User(
        name=name,
        email=email,
        phone=phone or None,
        role=role,
    )
    user.password = password  # triggers hashing via setter

    try:
        db.session.add(user)
        db.session.commit()
        current_app.logger.info("New user registered: id=%d email=%s", user.id, email)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Registration DB error: %s", e)
        return api_error("Registration failed. Please try again.", 500)

    # Auto-login after registration
    login_user(user, remember=False)

    return api_success(
        data=user.to_dict(),
        message="Account created successfully. Welcome to Gruha Alankara!",
        status_code=201,
    )


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.post("/login")
@limiter.limit("20 per hour; 5 per minute")
def login():
    """
    Authenticate a user and start a session.

    Body (JSON):
        email      (str, required)
        password   (str, required)
        remember   (bool, optional, default False)

    Returns 200 with user data on success, 401 on bad credentials.
    """
    data, err = get_json_body(email="str", password="str")
    if err:
        return api_error(err, 400)

    email    = sanitise_email(data["email"])
    password = data["password"]
    remember = bool(data.get("remember", False))

    user = User.query.filter_by(email=email).first()

    # Use constant-time comparison via check_password (prevents timing attacks)
    if not user or not user.check_password(password):
        current_app.logger.warning("Failed login attempt for email=%s", email)
        return api_error("Invalid email or password.", 401)

    if not user.is_active:
        return api_error("Your account has been deactivated. Please contact support.", 403)

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()

    login_user(user, remember=remember)
    current_app.logger.info("User logged in: id=%d email=%s", user.id, email)

    return api_success(
        data=user.to_dict(),
        message=f"Welcome back, {user.name}!",
    )


# ─────────────────────────────────────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.post("/logout")
@login_required_api
def logout():
    """End the current user's session."""
    user_id = current_user.id
    logout_user()
    current_app.logger.info("User logged out: id=%d", user_id)
    return api_success(message="You have been logged out successfully.")


# ─────────────────────────────────────────────────────────────────────────────
# GET PROFILE
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.get("/me")
@login_required_api
def get_profile():
    """Return the authenticated user's profile data."""
    return api_success(data=current_user.to_dict())


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE PROFILE
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.put("/me")
@login_required_api
def update_profile():
    """
    Update user profile fields (name, phone, role).

    Body (JSON): any subset of { name, phone, role }
    """
    data = request.get_json(silent=True) or {}

    if "name" in data:
        name = sanitise_text(data["name"], 120)
        if len(name) < 2:
            return api_error("Name must be at least 2 characters.", 400)
        current_user.name = name

    if "phone" in data:
        current_user.phone = sanitise_text(data["phone"], 20) or None

    if "role" in data:
        allowed = {"homeowner", "designer", "architect"}
        if data["role"] in allowed:
            current_user.role = data["role"]

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return api_error("Profile update failed.", 500)

    return api_success(data=current_user.to_dict(), message="Profile updated.")


# ─────────────────────────────────────────────────────────────────────────────
# CHANGE PASSWORD
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.post("/change-password")
@login_required_api
@limiter.limit("5 per hour")
def change_password():
    """
    Change the authenticated user's password.

    Body (JSON):
        current_password (str, required)
        new_password     (str, required)
    """
    data, err = get_json_body(current_password="str", new_password="str")
    if err:
        return api_error(err, 400)

    if not current_user.check_password(data["current_password"]):
        return api_error("Current password is incorrect.", 401)

    strong, msg = is_strong_password(data["new_password"])
    if not strong:
        return api_error(msg, 400)

    if data["current_password"] == data["new_password"]:
        return api_error("New password must differ from the current password.", 400)

    current_user.password = data["new_password"]

    try:
        db.session.commit()
        current_app.logger.info("Password changed: user_id=%d", current_user.id)
    except Exception:
        db.session.rollback()
        return api_error("Password change failed.", 500)

    return api_success(message="Password changed successfully.")
