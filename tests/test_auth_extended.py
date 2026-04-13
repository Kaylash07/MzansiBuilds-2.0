"""Extended tests for authentication routes — fills coverage gaps.

Follows AAA pattern (Arrange, Act, Assert) with Source of Truth expected results.
"""
import io
import os
from tests.conftest import register_user, auth_header


# ── Registration — edge cases & response validation ──────────────────

class TestRegisterEdgeCases:
    """Covers empty strings, whitespace-only fields, duplicate email vs username."""

    def test_register_empty_username_string(self, client):
        """Empty string username should be rejected (stripped to '')."""
        # Arrange
        payload = {"username": "", "email": "a@a.com", "password": "secret123"}
        # Act
        resp = client.post("/api/auth/register", json=payload)
        # Assert
        assert resp.status_code == 400
        assert "required" in resp.get_json()["error"].lower()

    def test_register_whitespace_only_username(self, client):
        """Whitespace-only username should be rejected after strip."""
        # Arrange
        payload = {"username": "   ", "email": "a@a.com", "password": "secret123"}
        # Act
        resp = client.post("/api/auth/register", json=payload)
        # Assert
        assert resp.status_code == 400

    def test_register_empty_email_string(self, client):
        """Empty string email should be rejected."""
        # Arrange
        payload = {"username": "alice", "email": "", "password": "secret123"}
        # Act
        resp = client.post("/api/auth/register", json=payload)
        # Assert
        assert resp.status_code == 400

    def test_register_empty_password_string(self, client):
        """Empty string password should be rejected."""
        # Arrange
        payload = {"username": "alice", "email": "a@a.com", "password": ""}
        # Act
        resp = client.post("/api/auth/register", json=payload)
        # Assert
        assert resp.status_code == 400

    def test_register_duplicate_email_only(self, client):
        """Same email, different username should be rejected."""
        # Arrange
        register_user(client, username="alice", email="dup@x.com")
        payload = {"username": "bob", "email": "dup@x.com", "password": "password123"}
        # Act
        resp = client.post("/api/auth/register", json=payload)
        # Assert
        assert resp.status_code == 409

    def test_register_duplicate_username_only(self, client):
        """Same username, different email should be rejected."""
        # Arrange
        register_user(client, username="alice", email="a@x.com")
        payload = {"username": "alice", "email": "different@x.com", "password": "password123"}
        # Act
        resp = client.post("/api/auth/register", json=payload)
        # Assert
        assert resp.status_code == 409

    def test_register_response_excludes_password_hash(self, client):
        """Sensitive field password_hash should never appear in response."""
        # Arrange
        payload = {"username": "secuser", "email": "sec@x.com", "password": "secret123"}
        # Act
        resp = client.post("/api/auth/register", json=payload)
        # Assert
        user_data = resp.get_json()["user"]
        assert "password_hash" not in user_data

    def test_register_response_structure(self, client):
        """Source of Truth: response must contain token and full user object."""
        # Arrange
        payload = {"username": "struct", "email": "s@x.com", "password": "secret123"}
        expected_user_keys = {"id", "username", "email", "bio", "avatar_url", "created_at"}
        # Act
        resp = client.post("/api/auth/register", json=payload)
        data = resp.get_json()
        # Assert
        assert resp.status_code == 201
        assert "token" in data
        assert isinstance(data["token"], str)
        assert len(data["token"]) > 0
        assert "user" in data
        assert expected_user_keys.issubset(set(data["user"].keys()))
        assert data["user"]["username"] == "struct"
        assert data["user"]["email"] == "s@x.com"
        assert data["user"]["bio"] == ""
        assert data["user"]["avatar_url"] == ""


# ── Login — edge cases & response validation ─────────────────────────

class TestLoginEdgeCases:
    """Covers empty strings, whitespace, response field validation."""

    def test_login_empty_email(self, client):
        """Empty email on login should be rejected."""
        # Arrange
        payload = {"email": "", "password": "pass123"}
        # Act
        resp = client.post("/api/auth/login", json=payload)
        # Assert
        assert resp.status_code == 400

    def test_login_empty_password(self, client):
        """Empty password on login should be rejected."""
        # Arrange
        register_user(client, email="login@x.com")
        payload = {"email": "login@x.com", "password": ""}
        # Act
        resp = client.post("/api/auth/login", json=payload)
        # Assert
        assert resp.status_code == 400

    def test_login_response_structure(self, client):
        """Source of Truth: login response contains token and user object."""
        # Arrange
        register_user(client, email="resp@x.com", password="pass123456")
        expected_user_keys = {"id", "username", "email", "bio", "avatar_url", "created_at"}
        # Act
        resp = client.post("/api/auth/login", json={"email": "resp@x.com", "password": "pass123456"})
        data = resp.get_json()
        # Assert
        assert resp.status_code == 200
        assert "token" in data
        assert isinstance(data["token"], str)
        assert "user" in data
        assert expected_user_keys.issubset(set(data["user"].keys()))
        assert "password_hash" not in data["user"]

    def test_login_response_excludes_password_hash(self, client):
        """Password hash must never appear in login response."""
        # Arrange
        register_user(client, email="ph@x.com")
        # Act
        resp = client.post("/api/auth/login", json={"email": "ph@x.com", "password": "password123"})
        # Assert
        assert "password_hash" not in resp.get_json()["user"]


# ── GET /me — response validation ────────────────────────────────────

class TestGetMeExtended:
    """Covers response structure and field assertions."""

    def test_get_me_response_structure(self, client):
        """Source of Truth: /me returns full user dict without password_hash."""
        # Arrange
        _, token = register_user(client, username="meuser", email="me@x.com")
        expected_keys = {"id", "username", "email", "bio", "avatar_url", "created_at"}
        # Act
        resp = client.get("/api/auth/me", headers=auth_header(token))
        user_data = resp.get_json()["user"]
        # Assert
        assert resp.status_code == 200
        assert expected_keys.issubset(set(user_data.keys()))
        assert user_data["username"] == "meuser"
        assert user_data["email"] == "me@x.com"
        assert "password_hash" not in user_data

    def test_get_me_created_at_is_string(self, client):
        """created_at should be an ISO-format string."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.get("/api/auth/me", headers=auth_header(token))
        # Assert
        created_at = resp.get_json()["user"]["created_at"]
        assert isinstance(created_at, str)
        assert "T" in created_at  # ISO 8601 format includes 'T'


# ── PUT /me — extended profile update ─────────────────────────────────

class TestUpdateProfileExtended:

    def test_update_username_to_same_value(self, client):
        """Updating username to own current username should succeed."""
        # Arrange
        _, token = register_user(client, username="myname")
        # Act
        resp = client.put("/api/auth/me", json={"username": "myname"}, headers=auth_header(token))
        # Assert
        assert resp.status_code == 200
        assert resp.get_json()["user"]["username"] == "myname"

    def test_update_multiple_fields(self, client):
        """Updating username and bio simultaneously should work."""
        # Arrange
        _, token = register_user(client, username="orig", email="multi@x.com")
        # Act
        resp = client.put("/api/auth/me", json={
            "username": "newname",
            "bio": "New bio text",
        }, headers=auth_header(token))
        # Assert
        user_data = resp.get_json()["user"]
        assert user_data["username"] == "newname"
        assert user_data["bio"] == "New bio text"

    def test_update_bio_empty_string(self, client):
        """Setting bio to empty string should be allowed."""
        # Arrange
        _, token = register_user(client)
        client.put("/api/auth/me", json={"bio": "Has bio"}, headers=auth_header(token))
        # Act
        resp = client.put("/api/auth/me", json={"bio": ""}, headers=auth_header(token))
        # Assert
        assert resp.status_code == 200
        assert resp.get_json()["user"]["bio"] == ""

    def test_update_avatar_url(self, client):
        """Setting avatar_url directly should persist."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.put("/api/auth/me", json={
            "avatar_url": "/uploads/avatars/custom.png"
        }, headers=auth_header(token))
        # Assert
        assert resp.status_code == 200
        assert resp.get_json()["user"]["avatar_url"] == "/uploads/avatars/custom.png"

    def test_update_persists(self, client):
        """Changes must persist across requests (verify with GET)."""
        # Arrange
        _, token = register_user(client)
        # Act
        client.put("/api/auth/me", json={"bio": "Persistent bio"}, headers=auth_header(token))
        resp = client.get("/api/auth/me", headers=auth_header(token))
        # Assert
        assert resp.get_json()["user"]["bio"] == "Persistent bio"

    def test_update_profile_unauthenticated(self, client):
        """PUT /me without token should be rejected."""
        # Act
        resp = client.put("/api/auth/me", json={"bio": "nope"})
        # Assert
        assert resp.status_code == 401


# ── Public profile — extended ─────────────────────────────────────────

class TestPublicProfileExtended:

    def test_public_profile_response_structure(self, client):
        """Source of Truth: public profile has 'user' and 'projects' keys."""
        # Arrange
        data, token = register_user(client)
        uid = data["user"]["id"]
        # Act
        resp = client.get(f"/api/auth/users/{uid}")
        body = resp.get_json()
        # Assert
        assert "user" in body
        assert "projects" in body
        assert isinstance(body["projects"], list)

    def test_public_profile_user_with_no_projects(self, client):
        """User with no projects should return empty list."""
        # Arrange
        data, _ = register_user(client)
        uid = data["user"]["id"]
        # Act
        resp = client.get(f"/api/auth/users/{uid}")
        # Assert
        assert resp.get_json()["projects"] == []


# ── Avatar upload ─────────────────────────────────────────────────────

class TestAvatarUpload:
    """Tests for POST /api/auth/upload-avatar — previously untested endpoint."""

    def test_upload_valid_avatar(self, client):
        """Valid PNG upload should succeed and return updated user."""
        # Arrange
        _, token = register_user(client)
        data = io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        # Act
        resp = client.post("/api/auth/upload-avatar",
                           data={"avatar": (data, "photo.png")},
                           content_type="multipart/form-data",
                           headers=auth_header(token))
        # Assert
        assert resp.status_code == 200
        user_data = resp.get_json()["user"]
        assert user_data["avatar_url"].startswith("/uploads/avatars/")
        assert user_data["avatar_url"].endswith(".png")

    def test_upload_avatar_jpg(self, client):
        """JPG extension should be accepted."""
        # Arrange
        _, token = register_user(client)
        data = io.BytesIO(b'\xff\xd8\xff\xe0' + b'\x00' * 100)
        # Act
        resp = client.post("/api/auth/upload-avatar",
                           data={"avatar": (data, "photo.jpg")},
                           content_type="multipart/form-data",
                           headers=auth_header(token))
        # Assert
        assert resp.status_code == 200
        assert resp.get_json()["user"]["avatar_url"].endswith(".jpg")

    def test_upload_avatar_invalid_type(self, client):
        """Disallowed file type (txt) should be rejected."""
        # Arrange
        _, token = register_user(client)
        data = io.BytesIO(b"hello world")
        # Act
        resp = client.post("/api/auth/upload-avatar",
                           data={"avatar": (data, "notes.txt")},
                           content_type="multipart/form-data",
                           headers=auth_header(token))
        # Assert
        assert resp.status_code == 400
        assert "not allowed" in resp.get_json()["error"].lower()

    def test_upload_avatar_no_file(self, client):
        """Request without file should be rejected."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.post("/api/auth/upload-avatar",
                           data={},
                           content_type="multipart/form-data",
                           headers=auth_header(token))
        # Assert
        assert resp.status_code == 400
        assert "no file" in resp.get_json()["error"].lower()

    def test_upload_avatar_empty_filename(self, client):
        """File with empty filename should be rejected."""
        # Arrange
        _, token = register_user(client)
        data = io.BytesIO(b'\x89PNG\r\n\x1a\n')
        # Act
        resp = client.post("/api/auth/upload-avatar",
                           data={"avatar": (data, "")},
                           content_type="multipart/form-data",
                           headers=auth_header(token))
        # Assert
        assert resp.status_code == 400

    def test_upload_avatar_unauthenticated(self, client):
        """Avatar upload without auth should be rejected."""
        # Arrange
        data = io.BytesIO(b'\x89PNG\r\n\x1a\n')
        # Act
        resp = client.post("/api/auth/upload-avatar",
                           data={"avatar": (data, "photo.png")},
                           content_type="multipart/form-data")
        # Assert
        assert resp.status_code == 401

    def test_upload_avatar_uuid_filename(self, client):
        """Saved filename should be a UUID (not the original filename)."""
        # Arrange
        _, token = register_user(client)
        data = io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 50)
        # Act
        resp = client.post("/api/auth/upload-avatar",
                           data={"avatar": (data, "my_personal_photo.png")},
                           content_type="multipart/form-data",
                           headers=auth_header(token))
        # Assert
        avatar_url = resp.get_json()["user"]["avatar_url"]
        filename = avatar_url.split("/")[-1]
        name_part = filename.rsplit(".", 1)[0]
        # UUID hex is 32 chars
        assert len(name_part) == 32
        assert "my_personal_photo" not in avatar_url


# ── Password reset — extended ─────────────────────────────────────────

class TestPasswordResetExtended:

    def test_forgot_password_empty_email(self, client):
        """Empty email on forgot-password should be rejected."""
        # Act
        resp = client.post("/api/auth/forgot-password", json={"email": ""})
        # Assert
        assert resp.status_code == 400

    def test_forgot_password_no_body(self, client):
        """No JSON body on forgot-password should be rejected."""
        # Act
        resp = client.post("/api/auth/forgot-password", content_type="application/json")
        # Assert
        assert resp.status_code == 400

    def test_reset_code_is_6_digits(self, client):
        """Reset code must be exactly 6 numeric digits."""
        # Arrange
        register_user(client, email="digit@x.com")
        # Act
        resp = client.post("/api/auth/forgot-password", json={"email": "digit@x.com"})
        code = resp.get_json()["reset_code"]
        # Assert
        assert len(code) == 6
        assert code.isdigit()

    def test_reset_password_no_code_requested(self, client):
        """Reset without prior forgot-password should fail."""
        # Arrange
        register_user(client, email="noreset@x.com")
        # Act
        resp = client.post("/api/auth/reset-password", json={
            "email": "noreset@x.com", "code": "123456", "new_password": "newpass123"
        })
        # Assert
        assert resp.status_code == 400
        assert "no reset code" in resp.get_json()["error"].lower()

    def test_reset_code_used_twice_fails(self, client):
        """Using the same reset code twice should fail (token cleared after use)."""
        # Arrange
        register_user(client, email="twice@x.com")
        resp = client.post("/api/auth/forgot-password", json={"email": "twice@x.com"})
        code = resp.get_json()["reset_code"]
        # Act — first reset succeeds
        resp1 = client.post("/api/auth/reset-password", json={
            "email": "twice@x.com", "code": code, "new_password": "newpass1"
        })
        # Act — second reset with same code fails
        resp2 = client.post("/api/auth/reset-password", json={
            "email": "twice@x.com", "code": code, "new_password": "newpass2"
        })
        # Assert
        assert resp1.status_code == 200
        assert resp2.status_code == 400

    def test_reset_missing_fields(self, client):
        """Missing required fields should return 400."""
        # Act
        resp = client.post("/api/auth/reset-password", json={"email": "x@x.com"})
        # Assert
        assert resp.status_code == 400

    def test_reset_nonexistent_email(self, client):
        """Reset for unknown email should return 404."""
        # Act
        resp = client.post("/api/auth/reset-password", json={
            "email": "ghost@x.com", "code": "123456", "new_password": "newpass1"
        })
        # Assert
        assert resp.status_code == 404

    def test_old_password_fails_after_reset(self, client):
        """After resetting, old password must no longer work."""
        # Arrange
        register_user(client, email="old@x.com", password="oldpass123")
        resp = client.post("/api/auth/forgot-password", json={"email": "old@x.com"})
        code = resp.get_json()["reset_code"]
        client.post("/api/auth/reset-password", json={
            "email": "old@x.com", "code": code, "new_password": "newpass456"
        })
        # Act
        resp = client.post("/api/auth/login", json={
            "email": "old@x.com", "password": "oldpass123"
        })
        # Assert
        assert resp.status_code == 401
