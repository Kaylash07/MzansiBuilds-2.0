"""Unit and integration tests for the likes feature."""
from tests.conftest import register_user, auth_header, create_project


class TestToggleLike:
    def test_like_project(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        resp = client.post(f"/api/projects/{pid}/like", headers=auth_header(token))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["liked"] is True
        assert data["like_count"] == 1

    def test_unlike_project(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        # Like
        client.post(f"/api/projects/{pid}/like", headers=auth_header(token))
        # Unlike (toggle)
        resp = client.post(f"/api/projects/{pid}/like", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["liked"] is False
        assert data["like_count"] == 0

    def test_like_unauthenticated(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        resp = client.post(f"/api/projects/{pid}/like")
        assert resp.status_code == 401

    def test_like_nonexistent_project(self, client):
        _, token = register_user(client)
        resp = client.post("/api/projects/99999/like", headers=auth_header(token))
        assert resp.status_code == 404

    def test_like_toggle_idempotent(self, client):
        """Like → unlike → like again should work."""
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/like", headers=auth_header(token))
        client.post(f"/api/projects/{pid}/like", headers=auth_header(token))
        resp = client.post(f"/api/projects/{pid}/like", headers=auth_header(token))
        assert resp.get_json()["liked"] is True
        assert resp.get_json()["like_count"] == 1


class TestGetLikes:
    def test_get_like_count(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        # No likes yet
        resp = client.get(f"/api/projects/{pid}/like")
        assert resp.status_code == 200
        assert resp.get_json()["like_count"] == 0

        # After liking
        client.post(f"/api/projects/{pid}/like", headers=auth_header(token))
        resp = client.get(f"/api/projects/{pid}/like")
        assert resp.get_json()["like_count"] == 1

    def test_get_likes_nonexistent(self, client):
        resp = client.get("/api/projects/99999/like")
        assert resp.status_code == 404


class TestLikeStatus:
    def test_like_status_liked(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/like", headers=auth_header(token))
        resp = client.get(f"/api/projects/{pid}/like/status", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["liked"] is True
        assert resp.get_json()["like_count"] == 1

    def test_like_status_not_liked(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        resp = client.get(f"/api/projects/{pid}/like/status", headers=auth_header(token))
        assert resp.get_json()["liked"] is False

    def test_like_status_unauthenticated(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        resp = client.get(f"/api/projects/{pid}/like/status")
        assert resp.status_code == 401


class TestMultiUserLikes:
    def test_multiple_users_like(self, client):
        _, tok1 = register_user(client, username="user1", email="u1@x.com")
        _, tok2 = register_user(client, username="user2", email="u2@x.com")
        _, tok3 = register_user(client, username="user3", email="u3@x.com")

        proj = create_project(client, tok1)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/like", headers=auth_header(tok1))
        client.post(f"/api/projects/{pid}/like", headers=auth_header(tok2))
        resp = client.post(f"/api/projects/{pid}/like", headers=auth_header(tok3))
        assert resp.get_json()["like_count"] == 3

        # One user unlikes
        client.post(f"/api/projects/{pid}/like", headers=auth_header(tok2))
        resp = client.get(f"/api/projects/{pid}/like")
        assert resp.get_json()["like_count"] == 2

    def test_like_count_in_project_dict(self, client):
        _, tok1 = register_user(client, username="user1", email="u1@x.com")
        _, tok2 = register_user(client, username="user2", email="u2@x.com")

        proj = create_project(client, tok1)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/like", headers=auth_header(tok1))
        client.post(f"/api/projects/{pid}/like", headers=auth_header(tok2))

        resp = client.get(f"/api/projects/{pid}")
        assert resp.get_json()["project"]["like_count"] == 2

    def test_like_count_in_feed(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/like", headers=auth_header(token))

        resp = client.get("/api/feed")
        projects = resp.get_json()["projects"]
        assert projects[0]["like_count"] == 1

    def test_like_count_on_celebration_wall(self, client):
        _, token = register_user(client)
        proj = create_project(client, token, stage="completed")
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/like", headers=auth_header(token))

        resp = client.get("/api/celebration-wall")
        assert resp.get_json()["projects"][0]["like_count"] == 1


class TestLikeCascadeDelete:
    def test_delete_project_removes_likes(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/like", headers=auth_header(token))
        client.delete(f"/api/projects/{pid}", headers=auth_header(token))

        # Project gone, like endpoint returns 404
        resp = client.get(f"/api/projects/{pid}/like")
        assert resp.status_code == 404
