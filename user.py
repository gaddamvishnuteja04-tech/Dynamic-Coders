"""
app/models/user.py
==================
User model – authentication, session management, profile.
"""

from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db


class User(UserMixin, db.Model):
    """
    Represents a registered Gruha Alankara user.
    Implements Flask-Login's UserMixin interface for session handling.
    """
    __tablename__ = "users"

    # ── Primary fields ────────────────────────────────────────────────────────
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(255), unique=True, nullable=False, index=True)
    _password_hash = db.Column("password_hash", db.String(256), nullable=False)
    phone         = db.Column(db.String(20), nullable=True)
    role          = db.Column(db.String(30), default="homeowner")  # homeowner|designer|architect|admin

    # ── Status & verification ─────────────────────────────────────────────────
    is_active      = db.Column(db.Boolean, default=True, nullable=False)
    is_verified    = db.Column(db.Boolean, default=False, nullable=False)
    email_token    = db.Column(db.String(64), nullable=True)

    # ── Subscription / plan ───────────────────────────────────────────────────
    plan           = db.Column(db.String(20), default="free")   # free|pro|enterprise
    ai_analyses_used  = db.Column(db.Integer, default=0)
    ai_analyses_limit = db.Column(db.Integer, default=5)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at     = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at     = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                                onupdate=lambda: datetime.now(timezone.utc))
    last_login_at  = db.Column(db.DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    design_projects = db.relationship(
        "DesignProject", backref="owner", lazy="dynamic",
        cascade="all, delete-orphan"
    )
    bookings = db.relationship(
        "FurnitureBooking", backref="customer", lazy="dynamic",
        cascade="all, delete-orphan"
    )

    # ── Password property ─────────────────────────────────────────────────────
    @property
    def password(self):
        raise AttributeError("password is not a readable attribute.")

    @password.setter
    def password(self, raw_password: str) -> None:
        """Hash and store password using Werkzeug's PBKDF2-HMAC-SHA256."""
        self._password_hash = generate_password_hash(
            raw_password,
            method="pbkdf2:sha256:260000",  # 260k iterations
            salt_length=16,
        )

    def check_password(self, raw_password: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        return check_password_hash(self._password_hash, raw_password)

    # ── AI quota helpers ──────────────────────────────────────────────────────
    @property
    def has_ai_quota(self) -> bool:
        """Returns True if user can still perform AI analyses this period."""
        return self.ai_analyses_used < self.ai_analyses_limit

    def consume_ai_quota(self) -> None:
        """Increment usage counter."""
        self.ai_analyses_used = (self.ai_analyses_used or 0) + 1

    # ── Serialisation ─────────────────────────────────────────────────────────
    def to_dict(self, include_private: bool = False) -> dict:
        """Convert model to dictionary for JSON responses."""
        data = {
            "id":           self.id,
            "name":         self.name,
            "email":        self.email,
            "phone":        self.phone,
            "role":         self.role,
            "plan":         self.plan,
            "is_verified":  self.is_verified,
            "ai_quota":     {
                "used":  self.ai_analyses_used,
                "limit": self.ai_analyses_limit,
                "remaining": max(0, self.ai_analyses_limit - self.ai_analyses_used),
            },
            "created_at":   self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
        return data

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
