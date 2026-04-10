"""Bookmark routes - Single Responsibility: handles saving/unsaving projects."""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from server.extensions import db
from server.models import Project, Bookmark

bookmarks_bp = Blueprint('bookmarks', __name__, url_prefix='/api')


@bookmarks_bp.route('/projects/<int:project_id>/bookmark', methods=['POST'])
@jwt_required()
def toggle_bookmark(project_id):
    """Toggle bookmark on a project. Save if not saved, unsave if already saved."""
    user_id = int(get_jwt_identity())
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    existing = Bookmark.query.filter_by(user_id=user_id, project_id=project_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'bookmarked': False}), 200
    else:
        bookmark = Bookmark(user_id=user_id, project_id=project_id)
        db.session.add(bookmark)
        db.session.commit()
        return jsonify({'bookmarked': True}), 201


@bookmarks_bp.route('/projects/<int:project_id>/bookmark/status', methods=['GET'])
@jwt_required()
def bookmark_status(project_id):
    """Check if current user has bookmarked a project."""
    user_id = int(get_jwt_identity())
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    bookmarked = Bookmark.query.filter_by(user_id=user_id, project_id=project_id).first() is not None
    return jsonify({'bookmarked': bookmarked}), 200


@bookmarks_bp.route('/bookmarks', methods=['GET'])
@jwt_required()
def get_my_bookmarks():
    """Get all bookmarked projects for the current user."""
    user_id = int(get_jwt_identity())
    bookmarks = Bookmark.query.filter_by(user_id=user_id).order_by(Bookmark.created_at.desc()).all()
    result = []
    for b in bookmarks:
        project = db.session.get(Project, b.project_id)
        if project:
            result.append({
                'id': b.id,
                'created_at': b.created_at.isoformat() if b.created_at else None,
                'project': project.to_dict()
            })
    return jsonify({'bookmarks': result, 'total': len(result)}), 200
