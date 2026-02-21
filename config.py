"""
config.py
=========
Gruha Alankara – Configuration Management
Supports Development, Testing, and Production environments.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


# ─────────────────────────────────────────────────────────────────────────────
# BASE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
class Config:
    """Base configuration shared across all environments."""

    # ── Core Flask ────────────────────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "gruha-alankara-dev-secret-change-in-prod-2024")
    DEBUG = False
    TESTING = False

    # ── Database ──────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'gruha_alankara.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # ── File Upload ───────────────────────────────────────────────────────────
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "images")
    AUDIO_FOLDER  = os.path.join(BASE_DIR, "uploads", "audio")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB hard limit
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "heic"}
    ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "ogg"}

    # ── Session ───────────────────────────────────────────────────────────────
    SESSION_COOKIE_HTTPONLY   = True
    SESSION_COOKIE_SAMESITE   = "Lax"
    SESSION_COOKIE_SECURE     = False   # True in production (HTTPS)
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # ── CSRF ──────────────────────────────────────────────────────────────────
    WTF_CSRF_ENABLED       = True
    WTF_CSRF_TIME_LIMIT    = 3600          # 1 hour token validity
    WTF_CSRF_SSL_STRICT    = False         # True in production

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATELIMIT_DEFAULT        = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URL    = "memory://"
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STRATEGY       = "fixed-window"

    # ── AI / ML ───────────────────────────────────────────────────────────────
    AI_MODEL_NAME      = os.getenv("AI_MODEL_NAME", "Salesforce/blip-image-captioning-base")
    AI_USE_MOCK        = os.getenv("AI_USE_MOCK", "true").lower() == "true"
    AI_MAX_TOKENS      = 512
    AI_TEMPERATURE     = 0.7

    # ── LangChain ─────────────────────────────────────────────────────────────
    OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY", "")
    LANGCHAIN_VERBOSE  = os.getenv("LANGCHAIN_VERBOSE", "false").lower() == "true"

    # ── gTTS ──────────────────────────────────────────────────────────────────
    TTS_DEFAULT_LANG   = "en"
    TTS_SLOW_SPEECH    = False
    SUPPORTED_LANGUAGES = {
        "english": "en",
        "telugu":  "te",
        "hindi":   "hi",
        "en":      "en",
        "te":      "te",
        "hi":      "hi",
    }

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_FOLDER     = os.path.join(BASE_DIR, "logs")
    LOG_LEVEL      = "INFO"
    LOG_MAX_BYTES  = 5 * 1024 * 1024   # 5 MB per file
    LOG_BACKUP_COUNT = 3

    # ── Pagination ────────────────────────────────────────────────────────────
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE     = 100

    @staticmethod
    def init_app(app):
        """Run post-init setup: ensure upload directories exist."""
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        os.makedirs(app.config["AUDIO_FOLDER"],  exist_ok=True)
        os.makedirs(app.config["LOG_FOLDER"],     exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# DEVELOPMENT
# ─────────────────────────────────────────────────────────────────────────────
class DevelopmentConfig(Config):
    DEBUG  = True
    LOG_LEVEL = "DEBUG"
    WTF_CSRF_ENABLED = False          # Easier API testing in dev
    RATELIMIT_DEFAULT = "10000 per day"  # Relaxed for local dev
    AI_USE_MOCK = True                # Always mock in dev — no GPU needed


# ─────────────────────────────────────────────────────────────────────────────
# TESTING
# ─────────────────────────────────────────────────────────────────────────────
class TestingConfig(Config):
    TESTING   = True
    DEBUG     = True
    WTF_CSRF_ENABLED = False
    AI_USE_MOCK      = True
    RATELIMIT_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    UPLOAD_FOLDER = "/tmp/gruha_test_uploads"
    AUDIO_FOLDER  = "/tmp/gruha_test_audio"


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCTION
# ─────────────────────────────────────────────────────────────────────────────
class ProductionConfig(Config):
    DEBUG  = False
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT   = True
    LOG_LEVEL = "WARNING"
    AI_USE_MOCK = False
    RATELIMIT_DEFAULT = "500 per day;100 per hour"
    RATELIMIT_STORAGE_URL = os.getenv("REDIS_URL", "memory://")

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # In production, also configure centralised logging (e.g., Sentry)


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY
# ─────────────────────────────────────────────────────────────────────────────
config = {
    "development": DevelopmentConfig,
    "testing":     TestingConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}
