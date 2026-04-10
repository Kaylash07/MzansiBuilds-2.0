"""Unit tests for project routes (CRUD + milestones)."""
from tests.conftest import register_user, auth_header, create_project


class TestCreateProject:
    def test_create_project(self, client):
        _, token = register_user(client)
        resp = client.post("/api/projects", json={
            "title": "My App",
            "description": "Building something great",
            "stage": "idea",
        }, headers=auth_header(token))
        assert resp.status_code == 201
        proj = resp.get_json()["project"]
        assert proj["title"] == "My App"
        assert proj["stage"] == "idea"

    def test_create_project_completed_stage(self, client):
        _, token = register_user(client)
        resp = client.post("/api/projects", json={
            "title": "Done App", "description": "Already done", "stage": "completed",
        }, headers=auth_header(token))
        assert resp.status_code == 201
        assert resp.get_json()["project"]["is_completed"] is True

    def test_create_project_missing_fields(self, client):
        _, token = register_user(client)
        resp = client.post("/api/projects", json={"title": "X"}, headers=auth_header(token))
        assert resp.status_code == 400

    def test_create_project_invalid_stage(self, client):
        _, token = register_user(client)
        resp = client.post("/api/projects", json={
            "title": "X", "description": "Y", "stage": "invalid",
        }, headers=auth_header(token))
        assert resp.status_code == 400

    def test_create_project_unauthenticated(self, client):
        resp = client.post("/api/projects", json={
            "title": "X", "description": "Y",
        })
        assert resp.status_code == 401


class TestListProjects:
    def test_list_empty(self, client):
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        assert resp.get_json()["projects"] == []

    def test_list_with_projects(self, client):
        _, token = register_user(client)
        create_project(client, token, title="P1")
        create_project(client, token, title="P2")
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        assert resp.get_json()["total"] == 2

    def test_list_filter_by_stage(self, client):
        _, token = register_user(client)
        create_project(client, token, title="Idea", stage="idea")
        create_project(client, token, title="Testing", stage="testing")
        resp = client.get("/api/projects?stage=testing")
        data = resp.get_json()
        assert data["total"] == 1
        assert data["projects"][0]["title"] == "Testing"

    def test_list_search(self, client):
        _, token = register_user(client)
        create_project(client, token, title="Flask API", tech_stack="Python")
        create_project(client, token, title="React App", tech_stack="JavaScript")
        resp = client.get("/api/projects?q=Flask")
        assert resp.get_json()["total"] == 1


class TestGetProject:
    def test_get_project(self, client):
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        resp = client.get(f"/api/projects/{pid}")
        assert resp.status_code == 200
        assert resp.get_json()["project"]["id"] == pid

    def test_get_project_not_found(self, client):
        resp = client.get("/api/projects/99999")
        assert resp.status_code == 404


class TestUpdateProject:
    def test_update_project(self, client):
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        resp = client.put(f"/api/projects/{pid}", json={
            "title": "Updated Title", "stage": "in-progress",
        }, headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["project"]["title"] == "Updated Title"
        assert resp.get_json()["project"]["stage"] == "in-progress"

    def test_update_to_completed(self, client):
        _, token = register_user(client)
        data = create_project(client, token, stage="testing")
        pid = data["project"]["id"]
        resp = client.put(f"/api/projects/{pid}", json={"stage": "completed"}, headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["project"]["is_completed"] is True

    def test_update_unauthorized(self, client):
        _, token1 = register_user(client, username="owner", email="o@x.com")
        _, token2 = register_user(client, username="other", email="t@x.com")
        data = create_project(client, token1)
        pid = data["project"]["id"]
        resp = client.put(f"/api/projects/{pid}", json={"title": "Hacked"}, headers=auth_header(token2))
        assert resp.status_code == 403


class TestDeleteProject:
    def test_delete_project(self, client):
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        resp = client.delete(f"/api/projects/{pid}", headers=auth_header(token))
        assert resp.status_code == 200
        # Verify it's gone
        assert client.get(f"/api/projects/{pid}").status_code == 404

    def test_delete_unauthorized(self, client):
        _, token1 = register_user(client, username="owner", email="o@x.com")
        _, token2 = register_user(client, username="other", email="t@x.com")
        data = create_project(client, token1)
        pid = data["project"]["id"]
        resp = client.delete(f"/api/projects/{pid}", headers=auth_header(token2))
        assert resp.status_code == 403


class TestMyProjects:
    def test_my_projects(self, client):
        _, token = register_user(client)
        create_project(client, token)
        resp = client.get("/api/projects/my", headers=auth_header(token))
        assert resp.status_code == 200
        assert len(resp.get_json()["projects"]) == 1


# ── Milestones ─────────────────────────────────────────────────────

class TestMilestones:
    def test_add_milestone(self, client):
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        resp = client.post(f"/api/projects/{pid}/milestones", json={
            "title": "MVP", "description": "Minimum viable product",
        }, headers=auth_header(token))
        assert resp.status_code == 201
        assert resp.get_json()["milestone"]["title"] == "MVP"

    def test_add_milestone_missing_title(self, client):
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        resp = client.post(f"/api/projects/{pid}/milestones", json={"description": "x"}, headers=auth_header(token))
        assert resp.status_code == 400

    def test_get_milestones(self, client):
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        client.post(f"/api/projects/{pid}/milestones", json={"title": "M1"}, headers=auth_header(token))
        client.post(f"/api/projects/{pid}/milestones", json={"title": "M2"}, headers=auth_header(token))
        resp = client.get(f"/api/projects/{pid}/milestones")
        assert resp.status_code == 200
        assert len(resp.get_json()["milestones"]) == 2

    def test_achieve_milestone(self, client):
        _, token = register_user(client)
        data = create_project(client, token)
        pid = data["project"]["id"]
        m_resp = client.post(f"/api/projects/{pid}/milestones", json={"title": "Done"}, headers=auth_header(token))
        mid = m_resp.get_json()["milestone"]["id"]
        resp = client.put(f"/api/projects/{pid}/milestones/{mid}", json={
            "is_achieved": True,
        }, headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["milestone"]["is_achieved"] is True
        assert resp.get_json()["milestone"]["achieved_at"] is not None
