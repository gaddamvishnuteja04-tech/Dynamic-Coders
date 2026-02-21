"""
tests/test_auth.py
==================
Unit + integration tests for the Authentication API.
"""

import json
import pytest
from app import create_app, db as _db


@pytest.fixture(scope="session")
def app():
    """Create test Flask application."""
    _app = create_app("testing")
    with _app.app_context():
        _db.create_all()
        yield _app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Wipe tables between tests."""
    with app.app_context():
        _db.session.remove()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


def post_json(client, url, data):
    return client.post(
        url,
        data=json.dumps(data),
        content_type="application/json",
    )


# ─────────────────────────────────────────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────────────────────────────────────────
class TestRegister:
    def test_register_success(self, client):
        rv = post_json(client, "/api/auth/register", {
            "name": "Priya Sharma",
            "email": "priya@example.com",
            "password": "Gruha@1234",
        })
        assert rv.status_code == 201
        body = rv.get_json()
        assert body["success"] is True
        assert body["data"]["email"] == "priya@example.com"

    def test_register_duplicate_email(self, client):
        payload = {"name": "A", "email": "dup@test.com", "password": "Test@1234"}
        post_json(client, "/api/auth/register", payload)
        rv = post_json(client, "/api/auth/register", payload)
        assert rv.status_code == 409

    def test_register_weak_password(self, client):
        rv = post_json(client, "/api/auth/register", {
            "name": "B",
            "email": "b@test.com",
            "password": "weak",
        })
        assert rv.status_code == 400

    def test_register_invalid_email(self, client):
        rv = post_json(client, "/api/auth/register", {
            "name": "C",
            "email": "not-an-email",
            "password": "Strong@123",
        })
        assert rv.status_code == 400

    def test_register_missing_fields(self, client):
        rv = post_json(client, "/api/auth/register", {"name": "D"})
        assert rv.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────
class TestLogin:
    def _register(self, client):
        post_json(client, "/api/auth/register", {
            "name": "Test User",
            "email": "user@test.com",
            "password": "Gruha@1234",
        })

    def test_login_success(self, client):
        self._register(client)
        rv = post_json(client, "/api/auth/login", {
            "email": "user@test.com",
            "password": "Gruha@1234",
        })
        assert rv.status_code == 200
        assert rv.get_json()["success"] is True

    def test_login_wrong_password(self, client):
        self._register(client)
        rv = post_json(client, "/api/auth/login", {
            "email": "user@test.com",
            "password": "WrongPass@1",
        })
        assert rv.status_code == 401

    def test_login_nonexistent_user(self, client):
        rv = post_json(client, "/api/auth/login", {
            "email": "nobody@test.com",
            "password": "Gruha@1234",
        })
        assert rv.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────────────────────────────────────
class TestProfile:
    def _login(self, client):
        post_json(client, "/api/auth/register", {
            "name": "Profile User",
            "email": "profile@test.com",
            "password": "Test@12345",
        })

    def test_get_profile_authenticated(self, client):
        self._login(client)
        rv = client.get("/api/auth/me")
        assert rv.status_code == 200
        assert rv.get_json()["data"]["email"] == "profile@test.com"

    def test_get_profile_unauthenticated(self, client):
        rv = client.get("/api/auth/me")
        assert rv.status_code == 401

    def test_update_profile(self, client):
        self._login(client)
        rv = client.put(
            "/api/auth/me",
            data=json.dumps({"name": "Updated Name"}),
            content_type="application/json",
        )
        assert rv.status_code == 200
        assert rv.get_json()["data"]["name"] == "Updated Name"


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────────────────────────────────────
class TestHealth:
    def test_liveness(self, client):
        rv = client.get("/api/health")
        assert rv.status_code == 200
        assert rv.get_json()["status"] == "ok"

    def test_readiness(self, client):
        rv = client.get("/api/health/ready")
        assert rv.status_code in (200, 503)

    def test_info(self, client):
        rv = client.get("/api/info")
        assert rv.status_code == 200
        body = rv.get_json()
        assert "platform" in body
        assert "endpoints" in body
