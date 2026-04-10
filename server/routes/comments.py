"""Comments routes - Single Responsibility: handles project comments."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from server.extensions import db
from server.models import Project, Comment, User, Notification, Activity
from server.email_service import notify_comment_email

comments_bp = Blueprint('comments', __name__, url_prefix='/api')


@comments_bp.route('/projects/<int:project_id>/comments', methods=['GET'])
def get_comments(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    comments = Comment.query.filter_by(project_id=project_id).order_by(Comment.created_at.asc()).all()
    return jsonify({'comments': [c.to_dict() for c in comments]}), 200


@comments_bp.route('/projects/<int:project_id>/comments', methods=['POST'])
@jwt_required()
def add_comment(project_id):
    user_id = int(get_jwt_identity())
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Comment content is required'}), 400
    if len(content) > 2000:
        return jsonify({'error': 'Comment too long (max 2000 chars)'}), 400

    comment = Comment(
        content=content,
        author_id=user_id,
        project_id=project_id
    )
    db.session.add(comment)

    # Log activity
    commenter = db.session.get(User, user_id)
    activity = Activity(
        type='comment',
        message=f'{commenter.username} commented',
        detail=content[:200],
        project_id=project_id,
        user_id=user_id
    )
    db.session.add(activity)
    db.session.commit()

    # Notify project owner if commenter is not the owner
    if project.owner_id != user_id:
        owner = db.session.get(User, project.owner_id)
        notif = Notification(
            type='comment',
            message=f'{commenter.username} commented on your project "{project.title}"',
            user_id=project.owner_id,
            project_id=project_id,
            triggered_by_id=user_id
        )
        db.session.add(notif)
        db.session.commit()

        # Email notification
        notify_comment_email(
            owner.email, owner.username,
            commenter.username, project.title, content
        )

    return jsonify({'comment': comment.to_dict()}), 201
