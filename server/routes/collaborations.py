"""Collaboration routes - Single Responsibility: handles collaboration requests."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from server.extensions import db
from server.models import Project, CollaborationRequest, User, Notification, Activity
from server.email_service import notify_collab_email

collaborations_bp = Blueprint('collaborations', __name__, url_prefix='/api')


@collaborations_bp.route('/projects/<int:project_id>/collaborate', methods=['POST'])
@jwt_required()
def request_collaboration(project_id):
    user_id = int(get_jwt_identity())
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    if project.owner_id == user_id:
        return jsonify({'error': 'Cannot collaborate on your own project'}), 400

    existing = CollaborationRequest.query.filter_by(
        requester_id=user_id, project_id=project_id
    ).first()
    if existing:
        return jsonify({'error': 'You already requested to collaborate'}), 409

    data = request.get_json() or {}
    collab = CollaborationRequest(
        message=data.get('message', '').strip(),
        requester_id=user_id,
        project_id=project_id
    )
    db.session.add(collab)

    # Log activity
    requester = db.session.get(User, user_id)
    activity = Activity(
        type='collaboration',
        message=f'{requester.username} requested to collaborate',
        detail=data.get('message', '')[:200],
        project_id=project_id,
        user_id=user_id
    )
    db.session.add(activity)
    db.session.commit()

    # Notify project owner of collaboration request
    owner = db.session.get(User, project.owner_id)
    notif = Notification(
        type='collaboration',
        message=f'{requester.username} wants to collaborate on your project "{project.title}"',
        user_id=project.owner_id,
        project_id=project_id,
        triggered_by_id=user_id
    )
    db.session.add(notif)
    db.session.commit()

    # Email notification
    notify_collab_email(
        owner.email, owner.username,
        requester.username, project.title,
        data.get('message', '')
    )

    return jsonify({'collaboration': collab.to_dict()}), 201


@collaborations_bp.route('/projects/<int:project_id>/collaborate', methods=['GET'])
def get_collaborations(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    collabs = CollaborationRequest.query.filter_by(project_id=project_id).order_by(
        CollaborationRequest.created_at.desc()
    ).all()
    return jsonify({'collaborations': [c.to_dict() for c in collabs]}), 200


@collaborations_bp.route('/collaborations/<int:collab_id>', methods=['PUT'])
@jwt_required()
def respond_collaboration(collab_id):
    user_id = int(get_jwt_identity())
    collab = db.session.get(CollaborationRequest, collab_id)
    if not collab:
        return jsonify({'error': 'Collaboration request not found'}), 404

    project = db.session.get(Project, collab.project_id)
    if project.owner_id != user_id:
        return jsonify({'error': 'Only project owner can respond'}), 403

    data = request.get_json()
    status = data.get('status', '').strip()
    if status not in ('accepted', 'declined'):
        return jsonify({'error': 'Status must be accepted or declined'}), 400

    collab.status = status
    db.session.commit()
    return jsonify({'collaboration': collab.to_dict()}), 200
