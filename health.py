"""
app/api/health.py
=================
Health-check and platform info endpoints.

Routes:
  GET /api/health         – liveness probe
  GET /api/health/ready   – readiness probe (checks DB)
  GET /api/info           – platform metadata
"""

from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify

from app import db

health_bp = Blueprint("health", __name__)

_START_TIME = datetime.now(timezone.utc)


@health_bp.get("/health")
def liveness():
    """Kubernetes/Docker liveness probe – always returns 200 if process is alive."""
    return jsonify({
        "status":  "ok",
        "service": "gruha-alankara-api",
        "time":    datetime.now(timezone.utc).isoformat(),
    }), 200


@health_bp.get("/health/ready")
def readiness():
    """
    Readiness probe – checks database connectivity.
    Returns 200 if ready to serve, 503 if degraded.
    """
    try:
        db.session.execute(db.text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        current_app.logger.error("DB health check failed: %s", e)
        db_status = "error"

    ready = db_status == "ok"
    uptime_s = (datetime.now(timezone.utc) - _START_TIME).total_seconds()

    payload = {
        "status":   "ready" if ready else "degraded",
        "database": db_status,
        "uptime_seconds": round(uptime_s, 1),
    }
    return jsonify(payload), 200 if ready else 503


@health_bp.get("/info")
def platform_info():
    """Return non-sensitive platform metadata."""
    import sys
    import flask
    return jsonify({
        "platform":    "Gruha Alankara AI Interior Design",
        "version":     "2.0.0",
        "python":      sys.version.split()[0],
        "flask":       flask.__version__,
        "ai_mock":     current_app.config.get("AI_USE_MOCK", True),
        "environment": current_app.env if hasattr(current_app, "env") else "unknown",
        "docs":        "/api/info",
        "endpoints": {
            "auth":    "/api/auth",
            "design":  "/api/design",
            "voice":   "/api/voice",
            "booking": "/api/booking",
        },
    }), 200
