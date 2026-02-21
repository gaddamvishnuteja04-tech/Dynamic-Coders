"""
app/utils/security.py
=====================
Gruha Alankara – Security Utilities

Provides:
  • File upload validation (extension, size, MIME sniffing)
  • Secure filename generation
  • Input sanitisation helpers
  • API response helpers
  • Decorators: login_required_api, admin_required
"""

import hashlib
import hmac
import logging
import mimetypes
import os
import re
import uuid
from functools import wraps
from typing import Callable

from flask import current_app, jsonify, request
from flask_login import current_user
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# ALLOWED TYPES: Extension → expected MIME prefix
# ─────────────────────────────────────────────────────────────────────────────
ALLOWED_IMAGE_MIMES = {
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg",
    "png":  "image/png",
    "webp": "image/webp",
    "heic": "image/heic",
}

MAGIC_BYTES: dict[bytes, str] = {
    b"\xff\xd8\xff":  "image/jpeg",
    b"\x89PNG\r\n":   "image/png",
    b"RIFF":          "image/webp",   # RIFF….WEBP
    b"\x00\x00\x00":  "image/heic",  # simplified check
}

# Compiled sanitisation patterns
_RE_STRIP_TAGS  = re.compile(r"<[^>]+>")
_RE_WHITESPACE  = re.compile(r"\s+")
_RE_SAFE_NAME   = re.compile(r"[^a-zA-Z0-9_\-]")


# ─────────────────────────────────────────────────────────────────────────────
# FILE VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
def allowed_image(filename: str) -> bool:
    """Return True if the filename extension is in ALLOWED_IMAGE_MIMES."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_IMAGE_MIMES


def validate_image_file(file_storage) -> tuple[bool, str]:
    """
    Full file validation: extension, size, and magic-byte MIME sniffing.

    Args:
        file_storage: Werkzeug FileStorage object from request.files.

    Returns:
        (is_valid: bool, error_message: str)
    """
    if not file_storage or not file_storage.filename:
        return False, "No file provided."

    filename = file_storage.filename
    if not allowed_image(filename):
        allowed = ", ".join(ALLOWED_IMAGE_MIMES.keys())
        return False, f"File type not allowed. Permitted: {allowed}."

    # Check content length via seek/tell
    file_storage.seek(0, os.SEEK_END)
    size_bytes = file_storage.tell()
    file_storage.seek(0)

    max_bytes = current_app.config.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)
    if size_bytes > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        return False, f"File too large. Maximum allowed size is {max_mb} MB."

    if size_bytes == 0:
        return False, "File is empty."

    # Magic-byte verification (prevent extension spoofing)
    header = file_storage.read(16)
    file_storage.seek(0)

    detected = _detect_mime(header)
    if detected and not _mime_matches_extension(detected, filename):
        logger.warning(
            "MIME mismatch: filename=%s detected=%s — rejecting upload.", filename, detected
        )
        return False, "File content does not match its extension. Upload rejected."

    return True, ""


def _detect_mime(header: bytes) -> str | None:
    """Detect MIME type from file header magic bytes."""
    for magic, mime in MAGIC_BYTES.items():
        if header.startswith(magic):
            # Special case: RIFF files need 'WEBP' at offset 8
            if magic == b"RIFF" and header[8:12] != b"WEBP":
                continue
            return mime
    return None


def _mime_matches_extension(detected_mime: str, filename: str) -> bool:
    """Return True if detected MIME is consistent with the filename extension."""
    ext = filename.rsplit(".", 1)[-1].lower()
    expected = ALLOWED_IMAGE_MIMES.get(ext, "")
    return detected_mime == expected


# ─────────────────────────────────────────────────────────────────────────────
# SECURE FILENAME GENERATION
# ─────────────────────────────────────────────────────────────────────────────
def generate_secure_filename(original_filename: str, user_id: int | None = None) -> str:
    """
    Generate a collision-safe filename that preserves the original extension.

    Format: {user_id}_{uuid4}_{sanitised_original}.{ext}

    Args:
        original_filename: The uploaded file's original name.
        user_id:           Optional owner's user ID for namespacing.

    Returns:
        Safe filename string.
    """
    safe_original = secure_filename(original_filename)
    ext = safe_original.rsplit(".", 1)[-1].lower() if "." in safe_original else "bin"
    stem = safe_original.rsplit(".", 1)[0] if "." in safe_original else safe_original
    stem = _RE_SAFE_NAME.sub("_", stem)[:30]          # max 30 chars from original
    uid  = f"{user_id}_" if user_id else ""
    return f"{uid}{uuid.uuid4().hex[:12]}_{stem}.{ext}"


# ─────────────────────────────────────────────────────────────────────────────
# INPUT SANITISATION
# ─────────────────────────────────────────────────────────────────────────────
def sanitise_text(value: str, max_length: int = 500) -> str:
    """Strip HTML tags, collapse whitespace, and truncate."""
    if not isinstance(value, str):
        return ""
    value = _RE_STRIP_TAGS.sub("", value)
    value = _RE_WHITESPACE.sub(" ", value).strip()
    return value[:max_length]


def sanitise_email(email: str) -> str:
    """Lowercase and strip whitespace from email."""
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    """Simple RFC-5322 email format check."""
    pattern = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
    return bool(pattern.match(email))


def is_strong_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength.

    Rules:
      - Min 8 characters
      - At least one uppercase letter
      - At least one digit
      - At least one special character

    Returns:
        (is_strong: bool, feedback: str)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must include at least one uppercase letter."
    if not re.search(r"\d", password):
        return False, "Password must include at least one digit."
    if not re.search(r"[!@#$%^&*()_\-+=\[\]{};:'\",.<>?/\\|`~]", password):
        return False, "Password must include at least one special character."
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# API RESPONSE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def api_success(data: dict | list | None = None,
                message: str = "Success",
                status_code: int = 200,
                **extra) -> tuple:
    """Standardised JSON success response."""
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return jsonify(payload), status_code


def api_error(message: str,
              status_code: int = 400,
              errors: dict | list | None = None,
              **extra) -> tuple:
    """Standardised JSON error response."""
    payload = {"success": False, "error": message}
    if errors is not None:
        payload["errors"] = errors
    payload.update(extra)
    return jsonify(payload), status_code


def paginate_query(query, page: int = 1, per_page: int = 20) -> dict:
    """
    Paginate a SQLAlchemy query and return a structured pagination dict.

    Returns:
        Dict with 'items', 'pagination' keys.
    """
    per_page = min(per_page, current_app.config.get("MAX_PAGE_SIZE", 100))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "items": [item.to_dict() for item in pagination.items],
        "pagination": {
            "page":       pagination.page,
            "per_page":   pagination.per_page,
            "total":      pagination.total,
            "pages":      pagination.pages,
            "has_next":   pagination.has_next,
            "has_prev":   pagination.has_prev,
            "next_page":  pagination.next_num,
            "prev_page":  pagination.prev_num,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# AUTH DECORATORS
# ─────────────────────────────────────────────────────────────────────────────
def login_required_api(f: Callable) -> Callable:
    """
    Decorator for API routes that require an authenticated user.
    Returns JSON 401 instead of redirecting.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return api_error("Authentication required. Please login.", 401)
        if not current_user.is_active:
            return api_error("Account is deactivated. Please contact support.", 403)
        return f(*args, **kwargs)
    return decorated


def admin_required(f: Callable) -> Callable:
    """Decorator that additionally checks for admin role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return api_error("Authentication required.", 401)
        if current_user.role != "admin":
            return api_error("Administrator access required.", 403)
        return f(*args, **kwargs)
    return decorated


def ai_quota_required(f: Callable) -> Callable:
    """Decorator that checks the user still has AI analysis quota remaining."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return api_error("Authentication required.", 401)
        if not current_user.has_ai_quota:
            return api_error(
                f"AI analysis quota exhausted. You've used all "
                f"{current_user.ai_analyses_limit} analyses this period. "
                "Upgrade to Pro for unlimited access.",
                429,
            )
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_json_body(**required_fields) -> tuple[dict | None, str | None]:
    """
    Safely extract and validate a JSON request body.

    Usage:
        data, err = get_json_body(email=str, password=str)
        if err: return api_error(err)

    Returns:
        (data_dict, None) on success, (None, error_str) on failure.
    """
    if not request.is_json:
        return None, "Request must have Content-Type: application/json."

    data = request.get_json(silent=True)
    if data is None:
        return None, "Invalid or empty JSON body."

    missing = [field for field in required_fields if field not in data or data[field] is None]
    if missing:
        return None, f"Missing required fields: {', '.join(missing)}."

    return data, None


def get_client_ip() -> str:
    """Extract real client IP, respecting X-Forwarded-For in proxied setups."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"
