"""Unit tests for database models."""
from datetime import datetime, timezone
from server.models import User, Project, Milestone, Comment, CollaborationRequest, SupportReport, Notification, Activity
from server.extensions import db as _db
from werkzeug.security import generate_password_hash


class TestUserModel:
    def test_to_dict(self, app):
        with app.app_context():
            user = User(username="alice", email="a@x.com", password_hash=generate_password_hash("pw"))
            _db.session.add(user)
            _db.session.commit()
            d = user.to_dict()
            assert d["username"] == "alice"
            assert d["email"] == "a@x.com"
            assert "password_hash" not in d

    def test_user_relationships(self, app):
        with app.app_context():
            user = User(username="bob", email="b@x.com", password_hash="h")
            _db.session.add(user)
            _db.session.commit()
            proj = Project(title="P", description="D", owner_id=user.id)
            _db.session.add(proj)
            _db.session.commit()
            assert len(user.projects) == 1


class TestProjectModel:
    def test_to_dict(self, app):
        with app.app_context():
            user = User(username="u", email="u@x.com", password_hash="h")
            _db.session.add(user)
            _db.session.commit()
            proj = Project(title="T", description="D", tech_stack="Python", owner_id=user.id)
            _db.session.add(proj)
            _db.session.commit()
            d = proj.to_dict()
            assert d["title"] == "T"
            assert "owner" in d

    def test_to_dict_exclude_owner(self, app):
        with app.app_context():
            user = User(username="u", email="u@x.com", password_hash="h")
            _db.session.add(user)
            _db.session.commit()
            proj = Project(title="T", description="D", owner_id=user.id)
            _db.session.add(proj)
            _db.session.commit()
            d = proj.to_dict(include_owner=False)
            assert "owner" not in d


class TestMilestoneModel:
    def test_to_dict(self, app):
        with app.app_context():
            user = User(username="u", email="u@x.com", password_hash="h")
            _db.session.add(user)
            _db.session.commit()
            proj = Project(title="P", description="D", owner_id=user.id)
            _db.session.add(proj)
            _db.session.commit()
            ms = Milestone(title="MVP", project_id=proj.id)
            _db.session.add(ms)
            _db.session.commit()
            d = ms.to_dict()
            assert d["title"] == "MVP"
            assert d["is_achieved"] is False


class TestCommentModel:
    def test_to_dict(self, app):
        with app.app_context():
            user = User(username="u", email="u@x.com", password_hash="h")
            _db.session.add(user)
            _db.session.commit()
            proj = Project(title="P", description="D", owner_id=user.id)
            _db.session.add(proj)
            _db.session.commit()
            c = Comment(content="Hello", author_id=user.id, project_id=proj.id)
            _db.session.add(c)
            _db.session.commit()
            d = c.to_dict()
            assert d["content"] == "Hello"
            assert d["author"]["username"] == "u"


class TestCollaborationModel:
    def test_to_dict(self, app):
        with app.app_context():
            u1 = User(username="owner", email="o@x.com", password_hash="h")
            u2 = User(username="req", email="r@x.com", password_hash="h")
            _db.session.add_all([u1, u2])
            _db.session.commit()
            proj = Project(title="P", description="D", owner_id=u1.id)
            _db.session.add(proj)
            _db.session.commit()
            cr = CollaborationRequest(requester_id=u2.id, project_id=proj.id, message="Hi")
            _db.session.add(cr)
            _db.session.commit()
            d = cr.to_dict()
            assert d["status"] == "pending"
            assert d["requester"]["username"] == "req"


class TestSupportReportModel:
    def test_to_dict(self, app):
        with app.app_context():
            user = User(username="u", email="u@x.com", password_hash="h")
            _db.session.add(user)
            _db.session.commit()
            sr = SupportReport(category="bug", subject="S", description="D", user_id=user.id)
            _db.session.add(sr)
            _db.session.commit()
            d = sr.to_dict()
            assert d["category"] == "bug"
            assert d["status"] == "open"


class TestNotificationModel:
    def test_to_dict(self, app):
        with app.app_context():
            user = User(username="u", email="u@x.com", password_hash="h")
            _db.session.add(user)
            _db.session.commit()
            n = Notification(type="comment", message="test", user_id=user.id)
            _db.session.add(n)
            _db.session.commit()
            d = n.to_dict()
            assert d["type"] == "comment"
            assert d["is_read"] is False


class TestActivityModel:
    def test_to_dict(self, app):
        with app.app_context():
            user = User(username="u", email="u@x.com", password_hash="h")
            _db.session.add(user)
            _db.session.commit()
            proj = Project(title="P", description="D", owner_id=user.id)
            _db.session.add(proj)
            _db.session.commit()
            a = Activity(type="created", message="created project", project_id=proj.id, user_id=user.id)
            _db.session.add(a)
            _db.session.commit()
            d = a.to_dict()
            assert d["type"] == "created"
            assert d["user"]["username"] == "u"
