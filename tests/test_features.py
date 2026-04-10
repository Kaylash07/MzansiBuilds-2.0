"""Unit tests for comments, collaborations, feed, notifications, support, celebration, activities."""
from tests.conftest import register_user, auth_header, create_project


# ── Comments ─────────────────────────────────────────────────────────

class TestComments:
    def test_add_comment(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]
        resp = client.post(f"/api/projects/{pid}/comments", json={
            "content": "Nice project!",
        }, headers=auth_header(token))
        assert resp.status_code == 201
        assert resp.get_json()["comment"]["content"] == "Nice project!"

    def test_add_comment_triggers_notification(self, client):
        """Owner gets notified when someone else comments."""
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_other = register_user(client, username="commenter", email="c@x.com")
        proj = create_project(client, tok_owner)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/comments", json={"content": "Hey!"}, headers=auth_header(tok_other))

        resp = client.get("/api/notifications", headers=auth_header(tok_owner))
        assert resp.status_code == 200
        assert resp.get_json()["unread_count"] >= 1

    def test_add_comment_empty(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]
        resp = client.post(f"/api/projects/{pid}/comments", json={"content": ""}, headers=auth_header(token))
        assert resp.status_code == 400

    def test_add_comment_too_long(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]
        resp = client.post(f"/api/projects/{pid}/comments", json={
            "content": "x" * 2001,
        }, headers=auth_header(token))
        assert resp.status_code == 400

    def test_get_comments(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]
        client.post(f"/api/projects/{pid}/comments", json={"content": "C1"}, headers=auth_header(token))
        resp = client.get(f"/api/projects/{pid}/comments")
        assert resp.status_code == 200
        assert len(resp.get_json()["comments"]) == 1

    def test_comment_project_not_found(self, client):
        _, token = register_user(client)
        resp = client.post("/api/projects/99999/comments", json={"content": "X"}, headers=auth_header(token))
        assert resp.status_code == 404


# ── Collaborations ───────────────────────────────────────────────────

class TestCollaborations:
    def test_request_collaboration(self, client):
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_other = register_user(client, username="collab", email="c@x.com")
        proj = create_project(client, tok_owner)
        pid = proj["project"]["id"]

        resp = client.post(f"/api/projects/{pid}/collaborate", json={
            "message": "I want to help!",
        }, headers=auth_header(tok_other))
        assert resp.status_code == 201
        assert resp.get_json()["collaboration"]["status"] == "pending"

    def test_cannot_collaborate_own_project(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]
        resp = client.post(f"/api/projects/{pid}/collaborate", json={}, headers=auth_header(token))
        assert resp.status_code == 400

    def test_duplicate_collaboration(self, client):
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_other = register_user(client, username="collab", email="c@x.com")
        proj = create_project(client, tok_owner)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/collaborate", json={}, headers=auth_header(tok_other))
        resp = client.post(f"/api/projects/{pid}/collaborate", json={}, headers=auth_header(tok_other))
        assert resp.status_code == 409

    def test_accept_collaboration(self, client):
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_other = register_user(client, username="collab", email="c@x.com")
        proj = create_project(client, tok_owner)
        pid = proj["project"]["id"]

        c_resp = client.post(f"/api/projects/{pid}/collaborate", json={}, headers=auth_header(tok_other))
        cid = c_resp.get_json()["collaboration"]["id"]

        resp = client.put(f"/api/collaborations/{cid}", json={"status": "accepted"}, headers=auth_header(tok_owner))
        assert resp.status_code == 200
        assert resp.get_json()["collaboration"]["status"] == "accepted"

    def test_decline_collaboration(self, client):
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_other = register_user(client, username="collab", email="c@x.com")
        proj = create_project(client, tok_owner)
        pid = proj["project"]["id"]

        c_resp = client.post(f"/api/projects/{pid}/collaborate", json={}, headers=auth_header(tok_other))
        cid = c_resp.get_json()["collaboration"]["id"]

        resp = client.put(f"/api/collaborations/{cid}", json={"status": "declined"}, headers=auth_header(tok_owner))
        assert resp.status_code == 200
        assert resp.get_json()["collaboration"]["status"] == "declined"

    def test_non_owner_cannot_respond(self, client):
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_other = register_user(client, username="collab", email="c@x.com")
        proj = create_project(client, tok_owner)
        pid = proj["project"]["id"]

        c_resp = client.post(f"/api/projects/{pid}/collaborate", json={}, headers=auth_header(tok_other))
        cid = c_resp.get_json()["collaboration"]["id"]

        resp = client.put(f"/api/collaborations/{cid}", json={"status": "accepted"}, headers=auth_header(tok_other))
        assert resp.status_code == 403

    def test_get_collaborations(self, client):
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_other = register_user(client, username="collab", email="c@x.com")
        proj = create_project(client, tok_owner)
        pid = proj["project"]["id"]
        client.post(f"/api/projects/{pid}/collaborate", json={}, headers=auth_header(tok_other))

        resp = client.get(f"/api/projects/{pid}/collaborate")
        assert resp.status_code == 200
        assert len(resp.get_json()["collaborations"]) == 1


# ── Feed ─────────────────────────────────────────────────────────────

class TestFeed:
    def test_feed_empty(self, client):
        resp = client.get("/api/feed")
        assert resp.status_code == 200
        assert resp.get_json()["total"] == 0

    def test_feed_returns_projects(self, client):
        _, token = register_user(client)
        create_project(client, token)
        resp = client.get("/api/feed")
        assert resp.get_json()["total"] == 1

    def test_feed_filter_stage(self, client):
        _, token = register_user(client)
        create_project(client, token, title="A", stage="idea")
        create_project(client, token, title="B", stage="testing")
        resp = client.get("/api/feed?stage=idea")
        assert resp.get_json()["total"] == 1

    def test_feed_filter_category(self, client):
        _, token = register_user(client)
        create_project(client, token, title="A", category="web")
        create_project(client, token, title="B", category="mobile")
        resp = client.get("/api/feed?category=web")
        assert resp.get_json()["total"] == 1

    def test_feed_search(self, client):
        _, token = register_user(client)
        create_project(client, token, title="Flask API", tech_stack="Python")
        create_project(client, token, title="React App", tech_stack="JavaScript")
        resp = client.get("/api/feed?q=Flask")
        assert resp.get_json()["total"] == 1


# ── Notifications ────────────────────────────────────────────────────

class TestNotifications:
    def test_get_notifications_empty(self, client):
        _, token = register_user(client)
        resp = client.get("/api/notifications", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["unread_count"] == 0

    def test_mark_all_read(self, client):
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_other = register_user(client, username="cmtr", email="c@x.com")
        proj = create_project(client, tok_owner)
        pid = proj["project"]["id"]
        client.post(f"/api/projects/{pid}/comments", json={"content": "Hi"}, headers=auth_header(tok_other))

        resp = client.put("/api/notifications/read", headers=auth_header(tok_owner))
        assert resp.status_code == 200

        resp = client.get("/api/notifications", headers=auth_header(tok_owner))
        assert resp.get_json()["unread_count"] == 0

    def test_mark_single_read(self, client):
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_other = register_user(client, username="cmtr", email="c@x.com")
        proj = create_project(client, tok_owner)
        pid = proj["project"]["id"]
        client.post(f"/api/projects/{pid}/comments", json={"content": "Hi"}, headers=auth_header(tok_other))

        notifs = client.get("/api/notifications", headers=auth_header(tok_owner)).get_json()
        nid = notifs["notifications"][0]["id"]

        resp = client.put(f"/api/notifications/{nid}/read", headers=auth_header(tok_owner))
        assert resp.status_code == 200
        assert resp.get_json()["notification"]["is_read"] is True


# ── Support ──────────────────────────────────────────────────────────

class TestSupport:
    def test_submit_support(self, client):
        _, token = register_user(client)
        resp = client.post("/api/support", json={
            "category": "bug",
            "subject": "Login broken",
            "description": "Cannot log in with correct password",
        }, headers=auth_header(token))
        assert resp.status_code == 201
        assert resp.get_json()["report"]["category"] == "bug"

    def test_submit_support_missing_fields(self, client):
        _, token = register_user(client)
        resp = client.post("/api/support", json={"subject": "X"}, headers=auth_header(token))
        assert resp.status_code == 400

    def test_submit_support_unauthenticated(self, client):
        resp = client.post("/api/support", json={
            "category": "bug", "subject": "X", "description": "Y",
        })
        assert resp.status_code == 401


# ── Celebration wall ─────────────────────────────────────────────────

class TestCelebration:
    def test_celebration_wall_empty(self, client):
        resp = client.get("/api/celebration-wall")
        assert resp.status_code == 200
        assert resp.get_json()["projects"] == []

    def test_celebration_wall_shows_completed(self, client):
        _, token = register_user(client)
        create_project(client, token, title="Done", stage="completed")
        create_project(client, token, title="WIP", stage="idea")
        resp = client.get("/api/celebration-wall")
        projects = resp.get_json()["projects"]
        assert len(projects) == 1
        assert projects[0]["title"] == "Done"


# ── Activities ───────────────────────────────────────────────────────

class TestActivities:
    def test_activities_on_create(self, client):
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]
        resp = client.get(f"/api/projects/{pid}/activities")
        assert resp.status_code == 200
        activities = resp.get_json()["activities"]
        assert any(a["type"] == "created" for a in activities)

    def test_activities_project_not_found(self, client):
        resp = client.get("/api/projects/99999/activities")
        assert resp.status_code == 404

    def test_activities_on_stage_change(self, client):
        _, token = register_user(client)
        proj = create_project(client, token, stage="idea")
        pid = proj["project"]["id"]
        client.put(f"/api/projects/{pid}", json={"stage": "in-progress"}, headers=auth_header(token))
        resp = client.get(f"/api/projects/{pid}/activities")
        types = [a["type"] for a in resp.get_json()["activities"]]
        assert "stage_change" in types
