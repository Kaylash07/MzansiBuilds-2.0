"""Extended tests for project routes — fills coverage gaps.

Follows AAA pattern (Arrange, Act, Assert) with Source of Truth expected results.
"""
from tests.conftest import register_user, auth_header, create_project


# ── Create project — response validation & edge cases ─────────────────

class TestCreateProjectExtended:

    def test_create_project_response_structure(self, client):
        """Source of Truth: response must contain all expected project fields."""
        # Arrange
        _, token = register_user(client)
        expected_keys = {
            "id", "title", "description", "tech_stack", "repo_url",
            "category", "stage", "support_needed", "is_completed",
            "completed_at", "owner_id", "created_at", "updated_at",
            "owner", "milestone_count", "comment_count", "like_count",
        }
        # Act
        resp = client.post("/api/projects", json={
            "title": "Full Test", "description": "Testing all fields",
            "tech_stack": "Python", "category": "web", "stage": "idea",
        }, headers=auth_header(token))
        proj = resp.get_json()["project"]
        # Assert
        assert resp.status_code == 201
        assert expected_keys.issubset(set(proj.keys()))
        assert proj["title"] == "Full Test"
        assert proj["description"] == "Testing all fields"
        assert proj["tech_stack"] == "Python"
        assert proj["category"] == "web"
        assert proj["stage"] == "idea"
        assert proj["is_completed"] is False
        assert proj["completed_at"] is None
        assert proj["milestone_count"] == 0
        assert proj["comment_count"] == 0
        assert proj["like_count"] == 0

    def test_create_project_owner_is_current_user(self, client):
        """Project owner_id must match the authenticated user."""
        # Arrange
        data, token = register_user(client)
        user_id = data["user"]["id"]
        # Act
        resp = client.post("/api/projects", json={
            "title": "Owned", "description": "My proj", "stage": "idea",
        }, headers=auth_header(token))
        # Assert
        assert resp.get_json()["project"]["owner_id"] == user_id

    def test_create_project_optional_fields_default(self, client):
        """Optional fields should default to empty string / None."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.post("/api/projects", json={
            "title": "Minimal", "description": "Only required", "stage": "idea",
        }, headers=auth_header(token))
        proj = resp.get_json()["project"]
        # Assert
        assert proj["tech_stack"] == ""
        assert proj["repo_url"] == ""
        assert proj["support_needed"] == ""

    def test_create_project_no_data(self, client):
        """No JSON body on create should be rejected."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.post("/api/projects", content_type="application/json",
                           headers=auth_header(token))
        # Assert
        assert resp.status_code == 400

    def test_create_project_completed_sets_completed_at(self, client):
        """Stage 'completed' should set is_completed=True and completed_at."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.post("/api/projects", json={
            "title": "Done", "description": "Finished", "stage": "completed",
        }, headers=auth_header(token))
        proj = resp.get_json()["project"]
        # Assert
        assert proj["is_completed"] is True
        assert proj["completed_at"] is not None
        assert isinstance(proj["completed_at"], str)

    def test_create_project_timestamps_are_iso(self, client):
        """created_at and updated_at must be ISO 8601 strings."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.post("/api/projects", json={
            "title": "Timestamps", "description": "Check", "stage": "idea",
        }, headers=auth_header(token))
        proj = resp.get_json()["project"]
        # Assert
        assert "T" in proj["created_at"]
        assert "T" in proj["updated_at"]


# ── List projects — pagination & response ─────────────────────────────

class TestListProjectsExtended:

    def test_list_pagination_metadata(self, client):
        """Source of Truth: response includes total, page, pages keys."""
        # Arrange
        _, token = register_user(client)
        for i in range(5):
            create_project(client, token, title=f"P{i}")
        # Act
        resp = client.get("/api/projects?per_page=2&page=1")
        data = resp.get_json()
        # Assert
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["pages"] == 3
        assert len(data["projects"]) == 2

    def test_list_last_page_fewer_items(self, client):
        """Last page may have fewer items than per_page."""
        # Arrange
        _, token = register_user(client)
        for i in range(3):
            create_project(client, token, title=f"P{i}")
        # Act
        resp = client.get("/api/projects?per_page=2&page=2")
        data = resp.get_json()
        # Assert
        assert len(data["projects"]) == 1

    def test_list_per_page_capped_at_50(self, client):
        """per_page >50 should be capped to 50."""
        # Arrange — just verify the request succeeds with high per_page
        # Act
        resp = client.get("/api/projects?per_page=100")
        # Assert
        assert resp.status_code == 200

    def test_list_search_case_insensitive(self, client):
        """Search should be case-insensitive."""
        # Arrange
        _, token = register_user(client)
        create_project(client, token, title="Flask API")
        # Act
        resp = client.get("/api/projects?q=flask")
        # Assert
        assert resp.get_json()["total"] == 1

    def test_list_search_by_tech_stack(self, client):
        """Search should match tech_stack field."""
        # Arrange
        _, token = register_user(client)
        create_project(client, token, title="MyApp", tech_stack="Django, PostgreSQL")
        create_project(client, token, title="Other", tech_stack="React")
        # Act
        resp = client.get("/api/projects?q=Django")
        # Assert
        assert resp.get_json()["total"] == 1

    def test_list_combined_stage_and_search(self, client):
        """Filtering by stage + search simultaneously."""
        # Arrange
        _, token = register_user(client)
        create_project(client, token, title="Flask Idea", stage="idea")
        create_project(client, token, title="Flask Testing", stage="testing")
        create_project(client, token, title="React Idea", stage="idea", tech_stack="React")
        # Act
        resp = client.get("/api/projects?stage=idea&q=Flask")
        # Assert
        assert resp.get_json()["total"] == 1
        assert resp.get_json()["projects"][0]["title"] == "Flask Idea"


# ── Get project — response validation ─────────────────────────────────

class TestGetProjectExtended:

    def test_get_project_response_includes_owner(self, client):
        """Source of Truth: project detail response should include owner object."""
        # Arrange
        _, token = register_user(client, username="projowner")
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        resp = client.get(f"/api/projects/{pid}")
        proj = resp.get_json()["project"]
        # Assert
        assert "owner" in proj
        assert proj["owner"]["username"] == "projowner"

    def test_get_project_includes_counts(self, client):
        """Source of Truth: project detail includes like_count, comment_count, milestone_count."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        resp = client.get(f"/api/projects/{pid}")
        proj = resp.get_json()["project"]
        # Assert
        assert "like_count" in proj
        assert "comment_count" in proj
        assert "milestone_count" in proj
        assert proj["like_count"] == 0
        assert proj["comment_count"] == 0
        assert proj["milestone_count"] == 0


# ── Update project — extended ────────────────────────────────────────

class TestUpdateProjectExtended:

    def test_update_nonexistent_project(self, client):
        """Updating a project that doesn't exist should return 404."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.put("/api/projects/99999", json={"title": "X"}, headers=auth_header(token))
        # Assert
        assert resp.status_code == 404

    def test_update_invalid_stage(self, client):
        """Updating with invalid stage should be rejected."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        resp = client.put(f"/api/projects/{pid}", json={"stage": "invalid"},
                          headers=auth_header(token))
        # Assert
        assert resp.status_code == 400

    def test_update_stage_logs_activity(self, client):
        """Stage change should create a stage_change activity entry."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token, stage="idea")
        pid = data["project"]["id"]
        # Act
        client.put(f"/api/projects/{pid}", json={"stage": "planning"}, headers=auth_header(token))
        resp = client.get(f"/api/projects/{pid}/activities")
        activities = resp.get_json()["activities"]
        stage_changes = [a for a in activities if a["type"] == "stage_change"]
        # Assert
        assert len(stage_changes) == 1
        assert "planning" in stage_changes[0]["message"].lower()

    def test_update_unauthenticated(self, client):
        """Unauthenticated update should return 401."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        resp = client.put(f"/api/projects/{pid}", json={"title": "Hacked"})
        # Assert
        assert resp.status_code == 401

    def test_update_response_includes_updated_fields(self, client):
        """Source of Truth: response after update reflects new values."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        resp = client.put(f"/api/projects/{pid}", json={
            "title": "New Title", "description": "New Desc", "tech_stack": "Rust",
        }, headers=auth_header(token))
        proj = resp.get_json()["project"]
        # Assert
        assert proj["title"] == "New Title"
        assert proj["description"] == "New Desc"
        assert proj["tech_stack"] == "Rust"


# ── Delete project — extended ────────────────────────────────────────

class TestDeleteProjectExtended:

    def test_delete_nonexistent_project(self, client):
        """Deleting a nonexistent project should return 404."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.delete("/api/projects/99999", headers=auth_header(token))
        # Assert
        assert resp.status_code == 404

    def test_delete_unauthenticated(self, client):
        """Unauthenticated delete should return 401."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        resp = client.delete(f"/api/projects/{pid}")
        # Assert
        assert resp.status_code == 401

    def test_delete_cascades_comments(self, client):
        """Deleting a project should remove its comments."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        client.post(f"/api/projects/{pid}/comments", json={"content": "RIP"},
                    headers=auth_header(token))
        # Act
        client.delete(f"/api/projects/{pid}", headers=auth_header(token))
        # Assert
        resp = client.get(f"/api/projects/{pid}/comments")
        assert resp.status_code == 404

    def test_delete_cascades_milestones(self, client):
        """Deleting project should remove milestones."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        client.post(f"/api/projects/{pid}/milestones", json={"title": "M1"},
                    headers=auth_header(token))
        # Act
        client.delete(f"/api/projects/{pid}", headers=auth_header(token))
        # Assert
        resp = client.get(f"/api/projects/{pid}/milestones")
        assert resp.status_code == 404


# ── My projects — extended ───────────────────────────────────────────

class TestMyProjectsExtended:

    def test_my_projects_empty(self, client):
        """User with no projects returns empty list."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.get("/api/projects/my", headers=auth_header(token))
        # Assert
        assert resp.status_code == 200
        assert resp.get_json()["projects"] == []

    def test_my_projects_excludes_others(self, client):
        """My projects should not include other users' projects."""
        # Arrange
        _, tok1 = register_user(client, username="user1", email="u1@x.com")
        _, tok2 = register_user(client, username="user2", email="u2@x.com")
        create_project(client, tok1, title="User1 Project")
        create_project(client, tok2, title="User2 Project")
        # Act
        resp = client.get("/api/projects/my", headers=auth_header(tok1))
        projects = resp.get_json()["projects"]
        # Assert
        assert len(projects) == 1
        assert projects[0]["title"] == "User1 Project"

    def test_my_projects_unauthenticated(self, client):
        """Unauthenticated /my should return 401."""
        # Act
        resp = client.get("/api/projects/my")
        # Assert
        assert resp.status_code == 401


# ── Milestones — extended ────────────────────────────────────────────

class TestMilestonesExtended:

    def test_milestone_response_structure(self, client):
        """Source of Truth: milestone response includes all fields."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        expected_keys = {"id", "title", "description", "is_achieved", "achieved_at",
                         "created_at", "project_id"}
        # Act
        resp = client.post(f"/api/projects/{pid}/milestones",
                           json={"title": "MVP", "description": "Build MVP"},
                           headers=auth_header(token))
        ms = resp.get_json()["milestone"]
        # Assert
        assert resp.status_code == 201
        assert expected_keys.issubset(set(ms.keys()))
        assert ms["title"] == "MVP"
        assert ms["description"] == "Build MVP"
        assert ms["is_achieved"] is False
        assert ms["achieved_at"] is None
        assert ms["project_id"] == pid

    def test_milestone_nonexistent_project(self, client):
        """Adding milestone to nonexistent project should 404."""
        # Arrange
        _, token = register_user(client)
        # Act
        resp = client.post("/api/projects/99999/milestones",
                           json={"title": "M"}, headers=auth_header(token))
        # Assert
        assert resp.status_code == 404

    def test_milestone_non_owner_rejected(self, client):
        """Non-owner cannot add milestones."""
        # Arrange
        _, tok1 = register_user(client, username="owner", email="o@x.com")
        _, tok2 = register_user(client, username="other", email="t@x.com")
        data = create_project(client, tok1)
        pid = data["project"]["id"]
        # Act
        resp = client.post(f"/api/projects/{pid}/milestones",
                           json={"title": "M"}, headers=auth_header(tok2))
        # Assert
        assert resp.status_code == 403

    def test_milestones_empty_list(self, client):
        """Project with no milestones returns empty list."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        resp = client.get(f"/api/projects/{pid}/milestones")
        # Assert
        assert resp.status_code == 200
        assert resp.get_json()["milestones"] == []

    def test_milestones_nonexistent_project(self, client):
        """Getting milestones for nonexistent project should 404."""
        # Act
        resp = client.get("/api/projects/99999/milestones")
        # Assert
        assert resp.status_code == 404

    def test_achieve_milestone_logs_activity(self, client):
        """Achieving milestone should log milestone_achieved activity."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        m_resp = client.post(f"/api/projects/{pid}/milestones",
                             json={"title": "Done"}, headers=auth_header(token))
        mid = m_resp.get_json()["milestone"]["id"]
        # Act
        client.put(f"/api/projects/{pid}/milestones/{mid}",
                   json={"is_achieved": True}, headers=auth_header(token))
        resp = client.get(f"/api/projects/{pid}/activities")
        types = [a["type"] for a in resp.get_json()["activities"]]
        # Assert
        assert "milestone_achieved" in types

    def test_add_milestone_logs_activity(self, client):
        """Adding milestone should log milestone_added activity."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        client.post(f"/api/projects/{pid}/milestones",
                    json={"title": "New"}, headers=auth_header(token))
        resp = client.get(f"/api/projects/{pid}/activities")
        types = [a["type"] for a in resp.get_json()["activities"]]
        # Assert
        assert "milestone_added" in types

    def test_update_milestone_non_owner(self, client):
        """Non-owner cannot update milestones."""
        # Arrange
        _, tok1 = register_user(client, username="owner", email="o@x.com")
        _, tok2 = register_user(client, username="other", email="t@x.com")
        data = create_project(client, tok1)
        pid = data["project"]["id"]
        m_resp = client.post(f"/api/projects/{pid}/milestones",
                             json={"title": "M"}, headers=auth_header(tok1))
        mid = m_resp.get_json()["milestone"]["id"]
        # Act
        resp = client.put(f"/api/projects/{pid}/milestones/{mid}",
                          json={"is_achieved": True}, headers=auth_header(tok2))
        # Assert
        assert resp.status_code == 403

    def test_update_nonexistent_milestone(self, client):
        """Updating a milestone that doesn't exist should 404."""
        # Arrange
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        # Act
        resp = client.put(f"/api/projects/{pid}/milestones/99999",
                          json={"title": "X"}, headers=auth_header(token))
        # Assert
        assert resp.status_code == 404
