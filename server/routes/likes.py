"""Like routes - Single Responsibility: handles project likes/endorsements."""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from server.extensions import db
from server.models import Project, Like

likes_bp = Blueprint('likes', __name__, url_prefix='/api')


@likes_bp.route('/projects/<int:project_id>/like', methods=['POST'])
@jwt_required()
def toggle_like(project_id):
    """Toggle like on a project. Like if not liked, unlike if already liked."""
    user_id = int(get_jwt_identity())
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    existing = Like.query.filter_by(user_id=user_id, project_id=project_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        like_count = Like.query.filter_by(project_id=project_id).count()
        return jsonify({'liked': False, 'like_count': like_count}), 200
    else:
        like = Like(user_id=user_id, project_id=project_id)
        db.session.add(like)
        db.session.commit()
        like_count = Like.query.filter_by(project_id=project_id).count()
        return jsonify({'liked': True, 'like_count': like_count}), 201


@likes_bp.route('/projects/<int:project_id>/like', methods=['GET'])
def get_likes(project_id):
    """Get like count and whether current user has liked (if authenticated)."""
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    like_count = Like.query.filter_by(project_id=project_id).count()
    return jsonify({'like_count': like_count}), 200


@likes_bp.route('/projects/<int:project_id>/like/status', methods=['GET'])
@jwt_required()
def like_status(project_id):
    """Check if current user has liked a project."""
    user_id = int(get_jwt_identity())
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    liked = Like.query.filter_by(user_id=user_id, project_id=project_id).first() is not None
    like_count = Like.query.filter_by(project_id=project_id).count()
    return jsonify({'liked': liked, 'like_count': like_count}), 200
