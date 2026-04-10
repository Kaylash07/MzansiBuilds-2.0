"""Unit tests for authentication routes."""
from tests.conftest import register_user, auth_header


# ── Registration ─────────────────────────────────────────────────────

class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "secret123",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert "token" in data
        assert data["user"]["username"] == "alice"
        assert data["user"]["email"] == "alice@example.com"

    def test_register_missing_fields(self, client):
        resp = client.post("/api/auth/register", json={"username": "a"})
        assert resp.status_code == 400

    def test_register_short_username(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "ab", "email": "x@x.com", "password": "123456",
        })
        assert resp.status_code == 400
        assert "3 characters" in resp.get_json()["error"]

    def test_register_invalid_email(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "alice", "email": "not-an-email", "password": "123456",
        })
        assert resp.status_code == 400
        assert "email" in resp.get_json()["error"].lower()

    def test_register_short_password(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "alice", "email": "a@a.com", "password": "123",
        })
        assert resp.status_code == 400
        assert "6 characters" in resp.get_json()["error"]

    def test_register_duplicate(self, client):
        register_user(client, username="dup", email="dup@x.com")
        resp = client.post("/api/auth/register", json={
            "username": "dup", "email": "dup@x.com", "password": "password123",
        })
        assert resp.status_code == 409

    def test_register_no_body(self, client):
        resp = client.post("/api/auth/register", content_type="application/json")
        assert resp.status_code == 400


# ── Login ────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_success(self, client):
        register_user(client, email="log@in.com")
        resp = client.post("/api/auth/login", json={
            "email": "log@in.com", "password": "password123",
        })
        assert resp.status_code == 200
        assert "token" in resp.get_json()

    def test_login_wrong_password(self, client):
        register_user(client, email="wp@x.com")
        resp = client.post("/api/auth/login", json={
            "email": "wp@x.com", "password": "wrong",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "noone@nowhere.com", "password": "123456",
        })
        assert resp.status_code == 401

    def test_login_no_body(self, client):
        resp = client.post("/api/auth/login", content_type="application/json")
        assert resp.status_code == 400


# ── Current user / profile ───────────────────────────────────────────

class TestProfile:
    def test_get_me(self, client):
        _, token = register_user(client)
        resp = client.get("/api/auth/me", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["user"]["username"] == "testuser"

    def test_get_me_unauthenticated(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_update_profile(self, client):
        _, token = register_user(client)
        resp = client.put("/api/auth/me", json={"bio": "Hello!"}, headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["user"]["bio"] == "Hello!"

    def test_update_username_conflict(self, client):
        register_user(client, username="taken", email="t@x.com")
        _, token2 = register_user(client, username="other", email="o@x.com")
        resp = client.put("/api/auth/me", json={"username": "taken"}, headers=auth_header(token2))
        assert resp.status_code == 409

    def test_public_profile(self, client):
        data, _ = register_user(client)
        uid = data["user"]["id"]
        resp = client.get(f"/api/auth/users/{uid}")
        assert resp.status_code == 200
        assert "projects" in resp.get_json()

    def test_public_profile_not_found(self, client):
        resp = client.get("/api/auth/users/99999")
        assert resp.status_code == 404


# ── Password reset ───────────────────────────────────────────────────

class TestPasswordReset:
    def test_forgot_and_reset(self, client):
        register_user(client, email="reset@x.com")

        # Request code
        resp = client.post("/api/auth/forgot-password", json={"email": "reset@x.com"})
        assert resp.status_code == 200
        code = resp.get_json()["reset_code"]

        # Reset password
        resp = client.post("/api/auth/reset-password", json={
            "email": "reset@x.com", "code": code, "new_password": "newpass123",
        })
        assert resp.status_code == 200

        # Login with new password
        resp = client.post("/api/auth/login", json={
            "email": "reset@x.com", "password": "newpass123",
        })
        assert resp.status_code == 200

    def test_forgot_nonexistent_email(self, client):
        resp = client.post("/api/auth/forgot-password", json={"email": "x@x.com"})
        assert resp.status_code == 404

    def test_reset_wrong_code(self, client):
        register_user(client, email="rc@x.com")
        client.post("/api/auth/forgot-password", json={"email": "rc@x.com"})
        resp = client.post("/api/auth/reset-password", json={
            "email": "rc@x.com", "code": "000000", "new_password": "newpass1",
        })
        assert resp.status_code == 400

    def test_reset_short_password(self, client):
        register_user(client, email="sp@x.com")
        resp_forgot = client.post("/api/auth/forgot-password", json={"email": "sp@x.com"})
        code = resp_forgot.get_json()["reset_code"]
        resp = client.post("/api/auth/reset-password", json={
            "email": "sp@x.com", "code": code, "new_password": "12",
        })
        assert resp.status_code == 400
