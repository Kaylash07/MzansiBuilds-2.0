"""Database models following Single Responsibility and Open/Closed Principles."""
from datetime import datetime, timezone
from server.extensions import db


class User(db.Model):
    """User account model."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    bio = db.Column(db.Text, default='')
    avatar_url = db.Column(db.String(256), default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    projects = db.relationship('Project', backref='owner', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy=True, cascade='all, delete-orphan')
    collaborations = db.relationship('CollaborationRequest', backref='requester', lazy=True,
                                     foreign_keys='CollaborationRequest.requester_id', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'bio': self.bio,
            'avatar_url': self.avatar_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Project(db.Model):
    """Project model - tracks what developers are building."""
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    tech_stack = db.Column(db.String(500), default='')
    repo_url = db.Column(db.String(500), default='')
    category = db.Column(db.String(100), default='')  # web, mobile, api, data-science, ai-ml, devops, iot, fintech, edtech, healthtech, gaming, other
    stage = db.Column(db.String(50), nullable=False, default='idea')  # idea, planning, in-progress, testing, completed
    support_needed = db.Column(db.Text, default='')
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    milestones = db.relationship('Milestone', backref='project', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='project', lazy=True, cascade='all, delete-orphan')
    collaboration_requests = db.relationship('CollaborationRequest', backref='project', lazy=True,
                                              cascade='all, delete-orphan')

    def to_dict(self, include_owner=True):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'tech_stack': self.tech_stack,
            'repo_url': self.repo_url,
            'category': self.category,
            'stage': self.stage,
            'support_needed': self.support_needed,
            'is_completed': self.is_completed,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'owner_id': self.owner_id,
            'milestone_count': len(self.milestones),
            'comment_count': len(self.comments),
            'collab_count': len(self.collaboration_requests),
        }
        if include_owner and self.owner:
            data['owner'] = self.owner.to_dict()
        return data


class Milestone(db.Model):
    """Milestone model - tracks project progress."""
    __tablename__ = 'milestones'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    is_achieved = db.Column(db.Boolean, default=False)
    achieved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'is_achieved': self.is_achieved,
            'achieved_at': self.achieved_at.isoformat() if self.achieved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'project_id': self.project_id
        }


class Comment(db.Model):
    """Comment model - for the live feed interactions."""
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'author_id': self.author_id,
            'project_id': self.project_id,
            'author': self.author.to_dict() if self.author else None
        }


class CollaborationRequest(db.Model):
    """Collaboration request - raise hand to collaborate."""
    __tablename__ = 'collaboration_requests'

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='pending')  # pending, accepted, declined
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'requester_id': self.requester_id,
            'project_id': self.project_id,
            'requester': self.requester.to_dict() if self.requester else None
        }


class SupportReport(db.Model):
    """Support/bug report model."""
    __tablename__ = 'support_reports'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False, default='other')
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='medium')
    status = db.Column(db.String(20), default='open')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reporter = db.relationship('User', backref='support_reports', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'subject': self.subject,
            'description': self.description,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user_id': self.user_id
        }


class Notification(db.Model):
    """Notification model - alerts users of activity on their projects."""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(30), nullable=False)  # comment, collaboration
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    triggered_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    recipient = db.relationship('User', foreign_keys=[user_id], backref='notifications')
    triggered_by = db.relationship('User', foreign_keys=[triggered_by_id])
    project = db.relationship('Project', backref='notifications')

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user_id': self.user_id,
            'project_id': self.project_id,
            'triggered_by': self.triggered_by.to_dict() if self.triggered_by else None
        }


class Activity(db.Model):
    """Activity log for project timeline."""
    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # created, stage_change, milestone_added, milestone_achieved, comment, collaboration
    message = db.Column(db.Text, nullable=False)
    detail = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    project = db.relationship('Project', backref=db.backref('activities', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'message': self.message,
            'detail': self.detail,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'project_id': self.project_id,
            'user': self.user.to_dict() if self.user else None
        }
