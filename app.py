"""
app.py
======
Gruha Alankara – Application Entry Point

Usage:
    # Development
    python app.py

    # Production (Gunicorn)
    gunicorn -w 4 -b 0.0.0.0:5000 "app:create_application()"

    # With environment variable
    FLASK_ENV=production python app.py
"""

import os
import sys

from app import create_app

# ── Detect runtime environment ────────────────────────────────────────────────
ENV = os.getenv("FLASK_ENV", os.getenv("APP_ENV", "development"))

# Create the Flask application
application = create_app(ENV)   # 'application' is the Gunicorn/PaaS standard name
app = application               # Alias for dev convenience


def create_application():
    """Factory function for Gunicorn entry point."""
    return create_app(ENV)


if __name__ == "__main__":
    # ── CLI argument parsing for quick port/host overrides ────────────────────
    host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    debug = ENV == "development"

    app.logger.info(
        "Starting Gruha Alankara API [env=%s host=%s port=%d debug=%s]",
        ENV, host, port, debug,
    )

    # Print available routes in development
    if debug:
        print("\n" + "=" * 60)
        print("  GRUHA ALANKARA API – Route Map")
        print("=" * 60)
        rules = sorted(app.url_map.iter_rules(), key=lambda r: r.rule)
        for rule in rules:
            methods = ", ".join(sorted(m for m in rule.methods if m not in ("HEAD", "OPTIONS")))
            print(f"  {methods:20s}  {rule.rule}")
        print("=" * 60 + "\n")

    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=debug,
        threaded=True,
    )
