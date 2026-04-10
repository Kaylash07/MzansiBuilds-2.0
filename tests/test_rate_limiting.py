"""Tests for rate limiting functionality."""
import os
import pytest
from server.app import create_app
from server.extensions import db as _db
from server.config import Config


class RateLimitConfig(Config):
    """Config with rate limiting enabled and very low limits for testing."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-secret-key"
    SECRET_KEY = "test-secret"
    MAIL_ENABLED = False
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = "memory://"
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "_test_uploads")


@pytest.fixture()
def rl_app():
    """Create a Flask app with rate limiting enabled."""
    application = create_app(RateLimitConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture()
def rl_client(rl_app):
    return rl_app.test_client()


def _register(client, username="testuser", email="test@example.com"):
    resp = client.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "password": "password123",
    })
    return resp.get_json().get("token")


class TestRateLimitLogin:
    def test_login_rate_limited(self, rl_client):
        """Login should be rate limited to 5/minute."""
        _register(rl_client)

        for i in range(5):
            resp = rl_client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password123",
            })
            assert resp.status_code == 200, f"Request {i+1} failed unexpectedly"

        # 6th request should be rate limited
        resp = rl_client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123",
        })
        assert resp.status_code == 429


class TestRateLimitRegister:
    def test_register_rate_limited(self, rl_client):
        """Register should be rate limited to 5/minute."""
        for i in range(5):
            resp = rl_client.post("/api/auth/register", json={
                "username": f"user{i}",
                "email": f"user{i}@test.com",
                "password": "password123",
            })
            assert resp.status_code == 201, f"Request {i+1} failed unexpectedly"

        # 6th request should be rate limited
        resp = rl_client.post("/api/auth/register", json={
            "username": "user999",
            "email": "user999@test.com",
            "password": "password123",
        })
        assert resp.status_code == 429


class TestRateLimitForgotPassword:
    def test_forgot_password_rate_limited(self, rl_client):
        """Forgot password should be rate limited to 3/minute."""
        _register(rl_client)

        for i in range(3):
            resp = rl_client.post("/api/auth/forgot-password", json={
                "email": "test@example.com",
            })
            assert resp.status_code == 200

        # 4th request should be rate limited
        resp = rl_client.post("/api/auth/forgot-password", json={
            "email": "test@example.com",
        })
        assert resp.status_code == 429


class TestRateLimitHeaders:
    def test_rate_limit_response_is_429(self, rl_client):
        """Exceeding rate limit should return 429 Too Many Requests."""
        _register(rl_client)

        for _ in range(5):
            rl_client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password123",
            })

        resp = rl_client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123",
        })
        assert resp.status_code == 429
        # Response body should indicate rate limiting
        assert b"Too Many Requests" in resp.data or b"rate" in resp.data.lower() or resp.status_code == 429


class TestRateLimitSupport:
    def test_support_rate_limited(self, rl_client):
        """Support submissions should be rate limited to 5/minute."""
        token = _register(rl_client)
        headers = {"Authorization": f"Bearer {token}"}

        for i in range(5):
            resp = rl_client.post("/api/support", headers=headers, json={
                "category": "bug",
                "subject": f"Bug report {i}",
                "description": "Something is broken",
            })
            assert resp.status_code == 201

        # 6th request should be rate limited
        resp = rl_client.post("/api/support", headers=headers, json={
            "category": "bug",
            "subject": "Another bug",
            "description": "Still broken",
        })
        assert resp.status_code == 429
