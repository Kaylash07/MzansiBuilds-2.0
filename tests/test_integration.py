"""Integration tests — multi-step workflows that verify components work together.

Uses an in-memory SQLite database so the production DB is never touched.
"""
from tests.conftest import register_user, auth_header, create_project


# ── Full project lifecycle ───────────────────────────────────────────

class TestProjectLifecycle:
    """Register → create project → add milestones → achieve them → mark completed → appears on celebration wall."""

    def test_full_lifecycle(self, client):
        # 1. Register
        data, token = register_user(client, username="builder", email="builder@x.com")
        assert data["user"]["username"] == "builder"

        # 2. Create project in idea stage
        resp = client.post("/api/projects", json={
            "title": "My Startup",
            "description": "Building the next big thing",
            "tech_stack": "Python, React",
            "category": "web",
            "stage": "idea",
        }, headers=auth_header(token))
        assert resp.status_code == 201
        pid = resp.get_json()["project"]["id"]

        # 3. Add milestones
        m1 = client.post(f"/api/projects/{pid}/milestones",
                         json={"title": "Design mockups"}, headers=auth_header(token))
        m2 = client.post(f"/api/projects/{pid}/milestones",
                         json={"title": "Build MVP"}, headers=auth_header(token))
        assert m1.status_code == 201
        assert m2.status_code == 201
        mid1 = m1.get_json()["milestone"]["id"]
        mid2 = m2.get_json()["milestone"]["id"]

        # 4. Progress through stages
        client.put(f"/api/projects/{pid}", json={"stage": "planning"}, headers=auth_header(token))
        client.put(f"/api/projects/{pid}", json={"stage": "in-progress"}, headers=auth_header(token))

        # 5. Achieve milestones
        client.put(f"/api/projects/{pid}/milestones/{mid1}",
                   json={"is_achieved": True}, headers=auth_header(token))
        client.put(f"/api/projects/{pid}/milestones/{mid2}",
                   json={"is_achieved": True}, headers=auth_header(token))

        # 6. Move to testing then completed
        client.put(f"/api/projects/{pid}", json={"stage": "testing"}, headers=auth_header(token))
        resp = client.put(f"/api/projects/{pid}", json={"stage": "completed"}, headers=auth_header(token))
        proj = resp.get_json()["project"]
        assert proj["is_completed"] is True
        assert proj["completed_at"] is not None

        # 7. Verify it shows on celebration wall
        resp = client.get("/api/celebration-wall")
        wall = resp.get_json()["projects"]
        assert any(p["id"] == pid for p in wall)

        # 8. Verify activity timeline has all events
        resp = client.get(f"/api/projects/{pid}/activities")
        types = [a["type"] for a in resp.get_json()["activities"]]
        assert "created" in types
        assert "stage_change" in types
        assert "milestone_added" in types
        assert "milestone_achieved" in types

        # 9. Milestones all achieved
        resp = client.get(f"/api/projects/{pid}/milestones")
        milestones = resp.get_json()["milestones"]
        assert all(m["is_achieved"] for m in milestones)


# ── Comment → notification → read flow ──────────────────────────────

class TestCommentNotificationFlow:
    """User A creates project → User B comments → User A gets notification → marks it read."""

    def test_comment_triggers_and_clears_notification(self, client):
        _, tok_owner = register_user(client, username="alice", email="alice@x.com")
        _, tok_commenter = register_user(client, username="bob", email="bob@x.com")

        proj = create_project(client, tok_owner, title="Alice's Project")
        pid = proj["project"]["id"]

        # Bob comments
        resp = client.post(f"/api/projects/{pid}/comments",
                           json={"content": "Looks awesome!"}, headers=auth_header(tok_commenter))
        assert resp.status_code == 201

        # Alice checks notifications — should have 1 unread
        resp = client.get("/api/notifications", headers=auth_header(tok_owner))
        notifs = resp.get_json()
        assert notifs["unread_count"] == 1
        assert "bob" in notifs["notifications"][0]["message"].lower()
        nid = notifs["notifications"][0]["id"]

        # Alice marks it read
        resp = client.put(f"/api/notifications/{nid}/read", headers=auth_header(tok_owner))
        assert resp.status_code == 200

        # Unread count is now 0
        resp = client.get("/api/notifications", headers=auth_header(tok_owner))
        assert resp.get_json()["unread_count"] == 0

    def test_self_comment_no_notification(self, client):
        """Owner commenting on own project should NOT create a notification."""
        _, token = register_user(client)
        proj = create_project(client, token)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "Note to self"}, headers=auth_header(token))

        resp = client.get("/api/notifications", headers=auth_header(token))
        assert resp.get_json()["unread_count"] == 0


# ── Collaboration request → accept/decline flow ─────────────────────

class TestCollaborationFlow:
    """User A creates project → User B requests collab → User A accepts → verified."""

    def test_full_collab_accept_flow(self, client):
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_dev = register_user(client, username="dev", email="d@x.com")

        proj = create_project(client, tok_owner, title="Open Source Tool")
        pid = proj["project"]["id"]

        # Dev requests collaboration
        resp = client.post(f"/api/projects/{pid}/collaborate",
                           json={"message": "I can help with the backend!"},
                           headers=auth_header(tok_dev))
        assert resp.status_code == 201
        cid = resp.get_json()["collaboration"]["id"]
        assert resp.get_json()["collaboration"]["status"] == "pending"

        # Owner gets notification about the collab request
        resp = client.get("/api/notifications", headers=auth_header(tok_owner))
        assert resp.get_json()["unread_count"] >= 1
        assert any("collaborate" in n["message"].lower()
                    for n in resp.get_json()["notifications"])

        # Owner accepts
        resp = client.put(f"/api/collaborations/{cid}",
                          json={"status": "accepted"}, headers=auth_header(tok_owner))
        assert resp.status_code == 200
        assert resp.get_json()["collaboration"]["status"] == "accepted"

        # Verify activity logged
        resp = client.get(f"/api/projects/{pid}/activities")
        types = [a["type"] for a in resp.get_json()["activities"]]
        assert "collaboration" in types

        # Collaboration visible in project collabs list
        resp = client.get(f"/api/projects/{pid}/collaborate")
        collabs = resp.get_json()["collaborations"]
        assert len(collabs) == 1
        assert collabs[0]["status"] == "accepted"

    def test_duplicate_collab_blocked(self, client):
        """Same user can't request collaboration twice on the same project."""
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_dev = register_user(client, username="dev", email="d@x.com")

        proj = create_project(client, tok_owner)
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/collaborate", json={}, headers=auth_header(tok_dev))
        resp = client.post(f"/api/projects/{pid}/collaborate", json={}, headers=auth_header(tok_dev))
        assert resp.status_code == 409


# ── Feed + search integration ───────────────────────────────────────

class TestFeedIntegration:
    """Multiple users create projects → feed shows them all with correct filtering."""

    def test_multi_user_feed(self, client):
        _, tok1 = register_user(client, username="alice", email="a@x.com")
        _, tok2 = register_user(client, username="bob", email="b@x.com")

        create_project(client, tok1, title="Flask API", category="web", stage="idea", tech_stack="Python")
        create_project(client, tok2, title="React Dashboard", category="web", stage="in-progress", tech_stack="JavaScript")
        create_project(client, tok1, title="ML Pipeline", category="ai-ml", stage="testing", tech_stack="Python, TensorFlow")

        # Full feed has all 3
        resp = client.get("/api/feed")
        assert resp.get_json()["total"] == 3

        # Filter by category
        resp = client.get("/api/feed?category=ai-ml")
        data = resp.get_json()
        assert data["total"] == 1
        assert data["projects"][0]["title"] == "ML Pipeline"

        # Filter by stage
        resp = client.get("/api/feed?stage=in-progress")
        data = resp.get_json()
        assert data["total"] == 1
        assert data["projects"][0]["title"] == "React Dashboard"

        # Search by keyword
        resp = client.get("/api/feed?q=Dashboard")
        assert resp.get_json()["total"] == 1

        # Search by username
        resp = client.get("/api/feed?q=alice")
        assert resp.get_json()["total"] == 2

    def test_feed_pagination(self, client):
        _, token = register_user(client)
        for i in range(5):
            create_project(client, token, title=f"Project {i}", tech_stack=f"Tech{i}")

        resp = client.get("/api/feed?per_page=2&page=1")
        data = resp.get_json()
        assert len(data["projects"]) == 2
        assert data["total"] == 5
        assert data["pages"] == 3

        resp = client.get("/api/feed?per_page=2&page=3")
        assert len(resp.get_json()["projects"]) == 1


# ── Profile + project ownership ──────────────────────────────────────

class TestProfileProjectIntegration:
    """User creates projects → public profile shows them → my-projects endpoint works."""

    def test_profile_shows_projects(self, client):
        data, token = register_user(client)
        uid = data["user"]["id"]

        create_project(client, token, title="Proj A")
        create_project(client, token, title="Proj B")

        # Public profile includes projects
        resp = client.get(f"/api/auth/users/{uid}")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["projects"]) == 2

        # /my endpoint matches
        resp = client.get("/api/projects/my", headers=auth_header(token))
        assert len(resp.get_json()["projects"]) == 2

    def test_deleted_project_removed_from_profile(self, client):
        data, token = register_user(client)
        uid = data["user"]["id"]

        proj = create_project(client, token, title="Temp")
        pid = proj["project"]["id"]

        client.delete(f"/api/projects/{pid}", headers=auth_header(token))

        resp = client.get(f"/api/auth/users/{uid}")
        assert len(resp.get_json()["projects"]) == 0


# ── Password reset → login flow ─────────────────────────────────────

class TestPasswordResetLogin:
    """Register → forget password → reset → login with new password → old password fails."""

    def test_reset_changes_login_credentials(self, client):
        register_user(client, email="reset@test.com", password="oldpass123")

        # Request reset code
        resp = client.post("/api/auth/forgot-password", json={"email": "reset@test.com"})
        code = resp.get_json()["reset_code"]

        # Reset to new password
        resp = client.post("/api/auth/reset-password", json={
            "email": "reset@test.com", "code": code, "new_password": "newpass456",
        })
        assert resp.status_code == 200

        # Old password fails
        resp = client.post("/api/auth/login", json={
            "email": "reset@test.com", "password": "oldpass123",
        })
        assert resp.status_code == 401

        # New password works
        resp = client.post("/api/auth/login", json={
            "email": "reset@test.com", "password": "newpass456",
        })
        assert resp.status_code == 200
        assert "token" in resp.get_json()


# ── Cross-user authorization ────────────────────────────────────────

class TestCrossUserAuthorization:
    """Verify users can't modify each other's resources."""

    def test_cannot_edit_other_users_project(self, client):
        _, tok1 = register_user(client, username="user1", email="u1@x.com")
        _, tok2 = register_user(client, username="user2", email="u2@x.com")

        proj = create_project(client, tok1, title="Private Idea")
        pid = proj["project"]["id"]

        # User2 can read it
        resp = client.get(f"/api/projects/{pid}")
        assert resp.status_code == 200

        # User2 cannot update it
        resp = client.put(f"/api/projects/{pid}",
                          json={"title": "Stolen"}, headers=auth_header(tok2))
        assert resp.status_code == 403

        # User2 cannot delete it
        resp = client.delete(f"/api/projects/{pid}", headers=auth_header(tok2))
        assert resp.status_code == 403

        # User2 cannot add milestones to it
        resp = client.post(f"/api/projects/{pid}/milestones",
                           json={"title": "Hijack"}, headers=auth_header(tok2))
        assert resp.status_code == 403

        # User2 cannot respond to collab requests on it
        _, tok3 = register_user(client, username="user3", email="u3@x.com")
        c_resp = client.post(f"/api/projects/{pid}/collaborate",
                             json={}, headers=auth_header(tok3))
        cid = c_resp.get_json()["collaboration"]["id"]
        resp = client.put(f"/api/collaborations/{cid}",
                          json={"status": "accepted"}, headers=auth_header(tok2))
        assert resp.status_code == 403

    def test_cannot_read_other_users_notifications(self, client):
        _, tok1 = register_user(client, username="user1", email="u1@x.com")
        _, tok2 = register_user(client, username="user2", email="u2@x.com")

        proj = create_project(client, tok1)
        pid = proj["project"]["id"]

        # User2 comments → user1 gets notification
        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "Hi"}, headers=auth_header(tok2))

        # User2 sees 0 notifications (they're user1's)
        resp = client.get("/api/notifications", headers=auth_header(tok2))
        assert resp.get_json()["unread_count"] == 0

        # User1 sees 1
        resp = client.get("/api/notifications", headers=auth_header(tok1))
        assert resp.get_json()["unread_count"] == 1


# ── Support ticket integration ──────────────────────────────────────

class TestSupportIntegration:
    """Register → submit support ticket → verify it persists."""

    def test_submit_and_verify_support(self, client):
        _, token = register_user(client)

        resp = client.post("/api/support", json={
            "category": "bug",
            "subject": "Login page broken",
            "description": "Getting 500 error when I try to log in",
            "priority": "high",
        }, headers=auth_header(token))
        assert resp.status_code == 201
        report = resp.get_json()["report"]
        assert report["category"] == "bug"
        assert report["priority"] == "high"
        assert report["status"] == "open"


# ── Multiple comments + activity timeline ────────────────────────────

class TestCommentActivityTimeline:
    """Multiple users comment → activity timeline records all events in order."""

    def test_comments_appear_in_activities(self, client):
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_a = register_user(client, username="alice", email="a@x.com")
        _, tok_b = register_user(client, username="bob", email="b@x.com")

        proj = create_project(client, tok_owner, title="Community Project")
        pid = proj["project"]["id"]

        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "First comment"}, headers=auth_header(tok_a))
        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "Second comment"}, headers=auth_header(tok_b))
        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "Third comment"}, headers=auth_header(tok_a))

        # 3 comment activities + 1 created activity = 4
        resp = client.get(f"/api/projects/{pid}/activities")
        activities = resp.get_json()["activities"]
        comment_activities = [a for a in activities if a["type"] == "comment"]
        assert len(comment_activities) == 3

        # Comments endpoint also has 3
        resp = client.get(f"/api/projects/{pid}/comments")
        assert len(resp.get_json()["comments"]) == 3

        # Owner has 3 notifications (from alice x2 and bob x1)
        resp = client.get("/api/notifications", headers=auth_header(tok_owner))
        assert resp.get_json()["unread_count"] == 3

    def test_mark_all_notifications_read(self, client):
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_a = register_user(client, username="alice", email="a@x.com")

        proj = create_project(client, tok_owner)
        pid = proj["project"]["id"]

        # Generate several notifications
        for i in range(4):
            client.post(f"/api/projects/{pid}/comments",
                        json={"content": f"Comment {i}"}, headers=auth_header(tok_a))

        resp = client.get("/api/notifications", headers=auth_header(tok_owner))
        assert resp.get_json()["unread_count"] == 4

        # Mark all read in one call
        client.put("/api/notifications/read", headers=auth_header(tok_owner))

        resp = client.get("/api/notifications", headers=auth_header(tok_owner))
        assert resp.get_json()["unread_count"] == 0


# ── Cascade delete ───────────────────────────────────────────────────

class TestCascadeDelete:
    """Deleting a project removes its comments, milestones, collabs, and activities."""

    def test_delete_project_cascades(self, client):
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_other = register_user(client, username="other", email="t@x.com")

        proj = create_project(client, tok_owner)
        pid = proj["project"]["id"]

        # Add related data
        client.post(f"/api/projects/{pid}/milestones",
                    json={"title": "M1"}, headers=auth_header(tok_owner))
        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "C1"}, headers=auth_header(tok_other))
        client.post(f"/api/projects/{pid}/collaborate",
                    json={"message": "Hi"}, headers=auth_header(tok_other))

        # Delete project
        resp = client.delete(f"/api/projects/{pid}", headers=auth_header(tok_owner))
        assert resp.status_code == 200

        # All related endpoints return 404
        assert client.get(f"/api/projects/{pid}").status_code == 404
        assert client.get(f"/api/projects/{pid}/milestones").status_code == 404
        assert client.get(f"/api/projects/{pid}/comments").status_code == 404
        assert client.get(f"/api/projects/{pid}/collaborate").status_code == 404
        assert client.get(f"/api/projects/{pid}/activities").status_code == 404
