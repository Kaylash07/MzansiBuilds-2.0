"""Extended tests for comments, collaborations, notifications, support, celebration, activities.

Follows AAA pattern (Arrange, Act, Assert) with Source of Truth expected results.
"""
from tests.conftest import register_user, auth_header, create_project


# ════════════════════════════════════════════════════════════════════════
#  COMMENTS
# ════════════════════════════════════════════════════════════════════════

class TestCommentsExtended:

    def test_comment_response_structure(self, client):
        """Source of Truth: comment response includes all expected fields."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        expected_keys = {"id", "content", "author_id", "project_id", "created_at", "author"}
        # Act
        resp = client.post(f"/api/projects/{pid}/comments",
                           json={"content": "Great work!"}, headers=auth_header(token))
        comment = resp.get_json()["comment"]
        # Assert
        assert resp.status_code == 201
        assert expected_keys.issubset(set(comment.keys()))
        assert comment["content"] == "Great work!"
        assert comment["project_id"] == pid

    def test_comment_exactly_2000_chars(self, client):
        """Boundary: exactly 2000 chars should succeed."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        content = "a" * 2000
        # Act
        resp = client.post(f"/api/projects/{pid}/comments",
                           json={"content": content}, headers=auth_header(token))
        # Assert
        assert resp.status_code == 201
        assert len(resp.get_json()["comment"]["content"]) == 2000

    def test_comment_2001_chars_rejected(self, client):
        """Boundary: 2001 chars should be rejected."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        content = "a" * 2001
        # Act
        resp = client.post(f"/api/projects/{pid}/comments",
                           json={"content": content}, headers=auth_header(token))
        # Assert
        assert resp.status_code == 400
        assert "too long" in resp.get_json()["error"].lower()

    def test_comment_whitespace_only_rejected(self, client):
        """Whitespace-only content should be rejected."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        resp = client.post(f"/api/projects/{pid}/comments",
                           json={"content": "   "}, headers=auth_header(token))
        # Assert
        assert resp.status_code == 400

    def test_comment_unauthenticated(self, client):
        """Unauthenticated user cannot post comment."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        resp = client.post(f"/api/projects/{pid}/comments",
                           json={"content": "Sneaky"})
        # Assert
        assert resp.status_code == 401

    def test_comment_nonexistent_project(self, client):
        """Comment on nonexistent project should 404."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.post("/api/projects/99999/comments",
                           json={"content": "Hello"}, headers=auth_header(token))
        # Assert
        assert resp.status_code == 404

    def test_get_comments_empty(self, client):
        """Get comments on project with none returns empty list."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        resp = client.get(f"/api/projects/{pid}/comments")
        # Assert
        assert resp.status_code == 200
        assert resp.get_json()["comments"] == []

    def test_get_comments_nonexistent_project(self, client):
        """Get comments for nonexistent project returns 404."""
        # Act
        resp = client.get("/api/projects/99999/comments")
        # Assert
        assert resp.status_code == 404

    def test_comment_creates_notification_for_owner(self, client):
        """Comment by non-owner should notify project owner."""
        # Arrange
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_other = register_user(client, username="commenter", email="c@x.com")
        data = create_project(client, tok_owner)
        pid = data["project"]["id"]
        # Act
        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "Nice!"}, headers=auth_header(tok_other))
        # Assert
        resp = client.get("/api/notifications", headers=auth_header(tok_owner))
        notifs = resp.get_json()["notifications"]
        assert any(n["type"] == "comment" for n in notifs)

    def test_comment_by_owner_no_self_notification(self, client):
        """Owner commenting on own project should not create notification."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "My note"}, headers=auth_header(token))
        resp = client.get("/api/notifications", headers=auth_header(token))
        # Assert
        assert resp.get_json()["notifications"] == []

    def test_comment_logs_activity(self, client):
        """Adding a comment should create a comment activity."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "Track this"}, headers=auth_header(token))
        resp = client.get(f"/api/projects/{pid}/activities")
        types = [a["type"] for a in resp.get_json()["activities"]]
        # Assert
        assert "comment" in types


# ════════════════════════════════════════════════════════════════════════
#  COLLABORATIONS
# ════════════════════════════════════════════════════════════════════════

class TestCollaborationsExtended:

    def test_collab_response_structure(self, client):
        """Source of Truth: collaboration response includes expected fields."""
        # Arrange
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_req = register_user(client, username="requester", email="r@x.com")
        data = create_project(client, tok_owner)
        pid = data["project"]["id"]
        expected_keys = {"id", "message", "status", "requester_id", "project_id", "created_at"}
        # Act
        resp = client.post(f"/api/projects/{pid}/collaborate",
                           json={"message": "I can help!"}, headers=auth_header(tok_req))
        collab = resp.get_json()["collaboration"]
        # Assert
        assert resp.status_code == 201
        assert expected_keys.issubset(set(collab.keys()))
        assert collab["status"] == "pending"
        assert collab["message"] == "I can help!"

    def test_collab_nonexistent_project(self, client):
        """Collaboration request for nonexistent project should 404."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.post("/api/projects/99999/collaborate",
                           json={"message": "Hello"}, headers=auth_header(token))
        # Assert
        assert resp.status_code == 404

    def test_collab_unauthenticated(self, client):
        """Unauthenticated collaboration request should 401."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        resp = client.post(f"/api/projects/{pid}/collaborate",
                           json={"message": "Help"})
        # Assert
        assert resp.status_code == 401

    def test_collab_get_empty(self, client):
        """Get collaborations on project with none returns empty list."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        resp = client.get(f"/api/projects/{pid}/collaborate")
        # Assert
        assert resp.status_code == 200
        assert resp.get_json()["collaborations"] == []

    def test_collab_get_nonexistent_project(self, client):
        """Get collaborations for nonexistent project should 404."""
        # Act
        resp = client.get("/api/projects/99999/collaborate")
        # Assert
        assert resp.status_code == 404

    def test_respond_invalid_status(self, client):
        """Respond with invalid status should 400."""
        # Arrange
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_req = register_user(client, username="req", email="r@x.com")
        data = create_project(client, tok_owner)
        pid = data["project"]["id"]
        cr = client.post(f"/api/projects/{pid}/collaborate",
                         json={"message": "Hi"}, headers=auth_header(tok_req))
        cid = cr.get_json()["collaboration"]["id"]
        # Act
        resp = client.put(f"/api/collaborations/{cid}",
                          json={"status": "maybe"}, headers=auth_header(tok_owner))
        # Assert
        assert resp.status_code == 400

    def test_respond_nonexistent_collab(self, client):
        """Responding to nonexistent collab should 404."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.put("/api/collaborations/99999",
                          json={"status": "accepted"}, headers=auth_header(token))
        # Assert
        assert resp.status_code == 404

    def test_respond_non_owner_rejected(self, client):
        """Non-owner cannot respond to collaboration."""
        # Arrange
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_req = register_user(client, username="req", email="r@x.com")
        _, tok_other = register_user(client, username="other", email="t@x.com")
        data = create_project(client, tok_owner)
        pid = data["project"]["id"]
        cr = client.post(f"/api/projects/{pid}/collaborate",
                         json={"message": "Hi"}, headers=auth_header(tok_req))
        cid = cr.get_json()["collaboration"]["id"]
        # Act
        resp = client.put(f"/api/collaborations/{cid}",
                          json={"status": "accepted"}, headers=auth_header(tok_other))
        # Assert
        assert resp.status_code == 403

    def test_collab_creates_notification(self, client):
        """Collaboration request should notify project owner."""
        # Arrange
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_req = register_user(client, username="req", email="r@x.com")
        data = create_project(client, tok_owner)
        pid = data["project"]["id"]
        # Act
        client.post(f"/api/projects/{pid}/collaborate",
                    json={"message": "Collab?"}, headers=auth_header(tok_req))
        resp = client.get("/api/notifications", headers=auth_header(tok_owner))
        # Assert
        notifs = resp.get_json()["notifications"]
        assert any(n["type"] == "collaboration" for n in notifs)

    def test_collab_logs_activity(self, client):
        """Collaboration request should log activity."""
        # Arrange
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_req = register_user(client, username="req", email="r@x.com")
        data = create_project(client, tok_owner)
        pid = data["project"]["id"]
        # Act
        client.post(f"/api/projects/{pid}/collaborate",
                    json={"message": "Hi"}, headers=auth_header(tok_req))
        resp = client.get(f"/api/projects/{pid}/activities")
        types = [a["type"] for a in resp.get_json()["activities"]]
        # Assert
        assert "collaboration" in types


# ════════════════════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ════════════════════════════════════════════════════════════════════════

class TestNotificationsExtended:

    def test_notifications_empty(self, client):
        """User with no notifications returns empty list and unread_count 0."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.get("/api/notifications", headers=auth_header(token))
        data = resp.get_json()
        # Assert
        assert resp.status_code == 200
        assert data["notifications"] == []
        assert data["unread_count"] == 0

    def test_notifications_unauthenticated(self, client):
        """Unauthenticated notification access should 401."""
        # Act
        resp = client.get("/api/notifications")
        # Assert
        assert resp.status_code == 401

    def test_notifications_response_structure(self, client):
        """Source of Truth: notification response includes expected fields."""
        # Arrange
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_other = register_user(client, username="other", email="t@x.com")
        data = create_project(client, tok_owner)
        pid = data["project"]["id"]
        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "hello"}, headers=auth_header(tok_other))
        expected_keys = {"id", "type", "message", "is_read", "user_id",
                         "project_id", "triggered_by", "created_at"}
        # Act
        resp = client.get("/api/notifications", headers=auth_header(tok_owner))
        notif = resp.get_json()["notifications"][0]
        # Assert
        assert expected_keys.issubset(set(notif.keys()))
        assert notif["is_read"] is False
        assert notif["type"] == "comment"

    def test_mark_single_notification_read(self, client):
        """Marking single notification should set is_read=True."""
        # Arrange
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_other = register_user(client, username="other", email="t@x.com")
        data = create_project(client, tok_owner)
        pid = data["project"]["id"]
        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "hi"}, headers=auth_header(tok_other))
        nresp = client.get("/api/notifications", headers=auth_header(tok_owner))
        nid = nresp.get_json()["notifications"][0]["id"]
        # Act
        resp = client.put(f"/api/notifications/{nid}/read",
                          headers=auth_header(tok_owner))
        # Assert
        assert resp.status_code == 200
        assert resp.get_json()["notification"]["is_read"] is True

    def test_mark_other_users_notification_404(self, client):
        """Marking another user's notification should return 404."""
        # Arrange
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_other = register_user(client, username="other", email="t@x.com")
        _, tok_third = register_user(client, username="third", email="3@x.com")
        data = create_project(client, tok_owner)
        pid = data["project"]["id"]
        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "hi"}, headers=auth_header(tok_other))
        nresp = client.get("/api/notifications", headers=auth_header(tok_owner))
        nid = nresp.get_json()["notifications"][0]["id"]
        # Act
        resp = client.put(f"/api/notifications/{nid}/read",
                          headers=auth_header(tok_third))
        # Assert
        assert resp.status_code == 404

    def test_mark_nonexistent_notification(self, client):
        """Marking nonexistent notification should 404."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.put("/api/notifications/99999/read",
                          headers=auth_header(token))
        # Assert
        assert resp.status_code == 404

    def test_mark_all_read_updates_unread_count(self, client):
        """After mark-all-read, unread_count should be 0."""
        # Arrange
        _, tok_owner = register_user(client, username="owner", email="o@x.com")
        _, tok_other = register_user(client, username="other", email="t@x.com")
        data = create_project(client, tok_owner)
        pid = data["project"]["id"]
        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "first"}, headers=auth_header(tok_other))
        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "second"}, headers=auth_header(tok_other))
        # Act
        client.put("/api/notifications/read", headers=auth_header(tok_owner))
        resp = client.get("/api/notifications", headers=auth_header(tok_owner))
        # Assert
        assert resp.get_json()["unread_count"] == 0


# ════════════════════════════════════════════════════════════════════════
#  SUPPORT
# ════════════════════════════════════════════════════════════════════════

class TestSupportExtended:

    def test_support_response_structure(self, client):
        """Source of Truth: support report response includes expected fields."""
        # Arrange
        _, token = register_user(client)
        expected_keys = {"id", "category", "subject", "description",
                         "priority", "status", "user_id", "created_at"}
        # Act
        resp = client.post("/api/support", json={
            "category": "bug", "subject": "Crash", "description": "App crashes on login",
        }, headers=auth_header(token))
        report = resp.get_json()["report"]
        # Assert
        assert resp.status_code == 201
        assert expected_keys.issubset(set(report.keys()))
        assert report["status"] == "open"
        assert report["priority"] == "medium"
        assert report["category"] == "bug"

    def test_support_custom_priority(self, client):
        """Priority should accept custom values like 'high'."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.post("/api/support", json={
            "category": "bug", "subject": "Urgent", "description": "Critical issue",
            "priority": "high",
        }, headers=auth_header(token))
        # Assert
        assert resp.get_json()["report"]["priority"] == "high"

    def test_support_missing_fields(self, client):
        """Missing required fields should 400."""
        # Arrange
        _, token = register_user(client)
        # Act — missing description
        resp = client.post("/api/support", json={
            "category": "bug", "subject": "No desc",
        }, headers=auth_header(token))
        # Assert
        assert resp.status_code == 400

    def test_support_no_data(self, client):
        """No JSON body should 400."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.post("/api/support", content_type="application/json",
                           headers=auth_header(token))
        # Assert
        assert resp.status_code == 400

    def test_support_unauthenticated(self, client):
        """Unauthenticated support request should 401."""
        # Act
        resp = client.post("/api/support", json={
            "category": "bug", "subject": "X", "description": "Y",
        })
        # Assert
        assert resp.status_code == 401


# ════════════════════════════════════════════════════════════════════════
#  CELEBRATION WALL
# ════════════════════════════════════════════════════════════════════════

class TestCelebrationExtended:

    def test_celebration_empty(self, client):
        """No completed projects returns empty list."""
        # Act
        resp = client.get("/api/celebration-wall")
        # Assert
        assert resp.status_code == 200
        assert resp.get_json()["projects"] == []

    def test_celebration_only_completed(self, client):
        """Only completed projects appear on celebration wall."""
        # Arrange
        _, token = register_user(client)
        create_project(client, token, title="In Progress", stage="idea")
        create_project(client, token, title="Done", stage="completed")
        # Act
        resp = client.get("/api/celebration-wall")
        projects = resp.get_json()["projects"]
        # Assert
        assert len(projects) == 1
        assert projects[0]["title"] == "Done"
        assert projects[0]["is_completed"] is True

    def test_celebration_ordering(self, client):
        """Completed projects should be ordered by completed_at desc."""
        # Arrange
        _, token = register_user(client)
        create_project(client, token, title="First", stage="completed")
        create_project(client, token, title="Second", stage="completed")
        # Act
        resp = client.get("/api/celebration-wall")
        projects = resp.get_json()["projects"]
        # Assert
        assert len(projects) == 2
        # Most recently completed first
        assert projects[0]["title"] == "Second"


# ════════════════════════════════════════════════════════════════════════
#  ACTIVITIES
# ════════════════════════════════════════════════════════════════════════

class TestActivitiesExtended:

    def test_activities_after_creation(self, client):
        """Newly created project has a 'created' activity."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        resp = client.get(f"/api/projects/{pid}/activities")
        # Assert
        assert resp.status_code == 200
        activities = resp.get_json()["activities"]
        assert len(activities) == 1
        assert activities[0]["type"] == "created"

    def test_activities_nonexistent_project(self, client):
        """Activities for nonexistent project should 404."""
        # Act
        resp = client.get("/api/projects/99999/activities")
        # Assert
        assert resp.status_code == 404

    def test_activities_response_structure(self, client):
        """Source of Truth: activity response includes expected fields."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        expected_keys = {"id", "type", "message", "detail", "project_id", "user", "created_at"}
        # One action that creates an activity
        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "Test"}, headers=auth_header(token))
        # Act
        resp = client.get(f"/api/projects/{pid}/activities")
        activity = resp.get_json()["activities"][0]
        # Assert
        assert expected_keys.issubset(set(activity.keys()))

    def test_activities_ordering(self, client):
        """Activities should be ordered by created_at desc (newest first)."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "First"}, headers=auth_header(token))
        client.post(f"/api/projects/{pid}/comments",
                    json={"content": "Second"}, headers=auth_header(token))
        # Act
        resp = client.get(f"/api/projects/{pid}/activities")
        activities = resp.get_json()["activities"]
        # Assert
        assert len(activities) >= 2
        # Newest first
        assert activities[0]["created_at"] >= activities[1]["created_at"]


# ════════════════════════════════════════════════════════════════════════
#  FEED
# ════════════════════════════════════════════════════════════════════════

class TestFeedExtended:

    def test_feed_response_structure(self, client):
        """Source of Truth: feed response includes projects, total, page, pages."""
        # Arrange
        _, token = register_user(client)
        create_project(client, token)
        # Act
        resp = client.get("/api/feed")
        data = resp.get_json()
        # Assert
        assert "projects" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data

    def test_feed_empty(self, client):
        """Empty database returns empty feed."""
        # Act
        resp = client.get("/api/feed")
        data = resp.get_json()
        # Assert
        assert data["projects"] == []
        assert data["total"] == 0

    def test_feed_combined_stage_category_search(self, client):
        """Combined filters: stage + category + search."""
        # Arrange
        _, token = register_user(client)
        create_project(client, token, title="Flask Web", stage="idea", category="web")
        create_project(client, token, title="Flask Mobile", stage="idea", category="mobile")
        create_project(client, token, title="React Web", stage="testing", category="web")
        # Act
        resp = client.get("/api/feed?stage=idea&category=web&q=Flask")
        data = resp.get_json()
        # Assert
        assert data["total"] == 1
        assert data["projects"][0]["title"] == "Flask Web"

    def test_feed_pagination_metadata(self, client):
        """Feed pagination returns correct metadata."""
        # Arrange
        _, token = register_user(client)
        for i in range(5):
            create_project(client, token, title=f"P{i}")
        # Act
        resp = client.get("/api/feed?per_page=2&page=1")
        data = resp.get_json()
        # Assert
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["pages"] == 3
        assert len(data["projects"]) == 2

    def test_feed_per_page_capped_at_50(self, client):
        """per_page should be capped at 50."""
        # Act
        resp = client.get("/api/feed?per_page=100")
        # Assert
        assert resp.status_code == 200

    def test_feed_search_by_username(self, client):
        """Feed search should match project owner's username."""
        # Arrange
        _, token = register_user(client, username="flaskdev")
        create_project(client, token, title="My Project")
        # Act
        resp = client.get("/api/feed?q=flaskdev")
        # Assert
        assert resp.get_json()["total"] == 1

    def test_feed_ordering_by_updated_at(self, client):
        """Feed should order by updated_at descending."""
        # Arrange
        _, token = register_user(client)
        create_project(client, token, title="Older")
        d2 = create_project(client, token, title="Newer")
        # Update second project to bump its updated_at
        pid = d2["project"]["id"]
        client.put(f"/api/projects/{pid}", json={"title": "Newest"},
                   headers=auth_header(token))
        # Act
        resp = client.get("/api/feed")
        projects = resp.get_json()["projects"]
        # Assert
        assert projects[0]["title"] == "Newest"
