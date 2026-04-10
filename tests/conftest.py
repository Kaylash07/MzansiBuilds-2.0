"""Shared test fixtures — uses in-memory SQLite so the production DB is never touched."""
import os
import pytest
from server.app import create_app
from server.extensions import db as _db
from server.config import Config


class TestConfig(Config):
    """Override config for testing: in-memory DB, testing mode, no emails."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-secret-key"
    SECRET_KEY = "test-secret"
    MAIL_ENABLED = False
    RATELIMIT_ENABLED = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "_test_uploads")


@pytest.fixture(scope="session")
def app():
    """Create the Flask app once per test session."""
    application = create_app(TestConfig)
    yield application


@pytest.fixture(autouse=True)
def db(app):
    """Create fresh tables before each test and drop them after."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


# ── helpers ──────────────────────────────────────────────────────────

def register_user(client, username="testuser", email="test@example.com", password="password123"):
    """Helper: register a user and return (response_json, token)."""
    resp = client.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
    })
    data = resp.get_json()
    token = data.get("token")
    return data, token


def auth_header(token):
    """Return Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}


def create_project(client, token, **overrides):
    """Helper: create a project and return response json."""
    payload = {
        "title": "Test Project",
        "description": "A test project description",
        "tech_stack": "Python, Flask",
        "category": "web",
        "stage": "idea",
    }
    payload.update(overrides)
    resp = client.post("/api/projects", json=payload, headers=auth_header(token))
    return resp.get_json()
