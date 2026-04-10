"""Unit and integration tests for the bookmarks feature."""
from tests.conftest import register_user, auth_header, create_project


class TestToggleBookmark:
    def test_bookmark_project(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        resp = client.post(f"/api/projects/{pid}/bookmark", headers=auth_header(token))
        assert resp.status_code == 201
        assert resp.get_json()["bookmarked"] is True

    def test_unbookmark_project(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/bookmark", headers=auth_header(token))
        resp = client.post(f"/api/projects/{pid}/bookmark", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["bookmarked"] is False

    def test_bookmark_unauthenticated(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        resp = client.post(f"/api/projects/{pid}/bookmark")
        assert resp.status_code == 401

    def test_bookmark_nonexistent_project(self, client):
        _, token = register_user(client)
        resp = client.post("/api/projects/99999/bookmark", headers=auth_header(token))
        assert resp.status_code == 404

    def test_bookmark_toggle_idempotent(self, client):
        """Bookmark → unbookmark → bookmark again should work."""
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/bookmark", headers=auth_header(token))
        client.post(f"/api/projects/{pid}/bookmark", headers=auth_header(token))
        resp = client.post(f"/api/projects/{pid}/bookmark", headers=auth_header(token))
        assert resp.get_json()["bookmarked"] is True


class TestBookmarkStatus:
    def test_status_bookmarked(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/bookmark", headers=auth_header(token))
        resp = client.get(f"/api/projects/{pid}/bookmark/status", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["bookmarked"] is True

    def test_status_not_bookmarked(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        resp = client.get(f"/api/projects/{pid}/bookmark/status", headers=auth_header(token))
        assert resp.get_json()["bookmarked"] is False

    def test_status_unauthenticated(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        resp = client.get(f"/api/projects/{pid}/bookmark/status")
        assert resp.status_code == 401

    def test_status_nonexistent_project(self, client):
        _, token = register_user(client)
        resp = client.get("/api/projects/99999/bookmark/status", headers=auth_header(token))
        assert resp.status_code == 404


class TestGetMyBookmarks:
    def test_get_empty_bookmarks(self, client):
        _, token = register_user(client)
        resp = client.get("/api/bookmarks", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["bookmarks"] == []
        assert data["total"] == 0

    def test_get_bookmarks_with_projects(self, client):
        _, token = register_user(client)
        p1 = create_project(client, token, title="Project A")
        p2 = create_project(client, token, title="Project B")

        client.post(f"/api/projects/{p1['project']['id']}/bookmark", headers=auth_header(token))
        client.post(f"/api/projects/{p2['project']['id']}/bookmark", headers=auth_header(token))

        resp = client.get("/api/bookmarks", headers=auth_header(token))
        data = resp.get_json()
        assert data["total"] == 2
        assert len(data["bookmarks"]) == 2
        # Most recent first
        assert data["bookmarks"][0]["project"]["title"] == "Project B"
        assert data["bookmarks"][1]["project"]["title"] == "Project A"

    def test_bookmarks_contain_project_data(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/bookmark", headers=auth_header(token))
        resp = client.get("/api/bookmarks", headers=auth_header(token))
        bookmark = resp.get_json()["bookmarks"][0]
        assert "project" in bookmark
        assert "created_at" in bookmark
        assert bookmark["project"]["id"] == pid

    def test_bookmarks_unauthenticated(self, client):
        resp = client.get("/api/bookmarks")
        assert resp.status_code == 401

    def test_unbookmark_removes_from_list(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/bookmark", headers=auth_header(token))
        client.post(f"/api/projects/{pid}/bookmark", headers=auth_header(token))  # toggle off

        resp = client.get("/api/bookmarks", headers=auth_header(token))
        assert resp.get_json()["total"] == 0


class TestBookmarkCascadeDelete:
    def test_delete_project_removes_bookmarks(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/bookmark", headers=auth_header(token))
        client.delete(f"/api/projects/{pid}", headers=auth_header(token))

        resp = client.get("/api/bookmarks", headers=auth_header(token))
        assert resp.get_json()["total"] == 0


class TestMultiUserBookmarks:
    def test_bookmarks_are_per_user(self, client):
        _, tok1 = register_user(client, username="user1", email="u1@x.com")
        _, tok2 = register_user(client, username="user2", email="u2@x.com")

        proj = create_project(client, tok1)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/bookmark", headers=auth_header(tok1))

        # User 2 should not see user 1's bookmarks
        resp = client.get("/api/bookmarks", headers=auth_header(tok2))
        assert resp.get_json()["total"] == 0

        # User 2 bookmarks the same project
        client.post(f"/api/projects/{pid}/bookmark", headers=auth_header(tok2))
        resp = client.get("/api/bookmarks", headers=auth_header(tok2))
        assert resp.get_json()["total"] == 1
