"""Feed, Comments, and Collaboration routes - following Interface Segregation."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from server.extensions import db
from server.models import Project, Comment, CollaborationRequest, User, SupportReport, Notification, Activity
from server.email_service import notify_comment_email, notify_collab_email

feed_bp = Blueprint('feed', __name__, url_prefix='/api')


# --- Live Feed ---
@feed_bp.route('/feed', methods=['GET'])
def live_feed():
    """Get live feed of all projects with latest activity."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('q', '').strip()
    stage = request.args.get('stage', '').strip()
    category = request.args.get('category', '').strip()

    query = Project.query.order_by(Project.updated_at.desc())

    if search:
        like = f'%{search}%'
        query = query.join(User, Project.owner_id == User.id).filter(
            db.or_(
                Project.title.ilike(like),
                Project.description.ilike(like),
                Project.tech_stack.ilike(like),
                User.username.ilike(like)
            )
        )

    if stage:
        query = query.filter(Project.stage == stage)

    if category:
        query = query.filter(Project.category == category)

    pagination = query.paginate(page=page, per_page=min(per_page, 50), error_out=False)

    projects = [p.to_dict() for p in pagination.items]
    return jsonify({
        'projects': projects,
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages
    }), 200


# --- Comments ---
@feed_bp.route('/projects/<int:project_id>/comments', methods=['GET'])
def get_comments(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    comments = Comment.query.filter_by(project_id=project_id).order_by(Comment.created_at.asc()).all()
    return jsonify({'comments': [c.to_dict() for c in comments]}), 200


@feed_bp.route('/projects/<int:project_id>/comments', methods=['POST'])
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


# --- Collaboration Requests ---
@feed_bp.route('/projects/<int:project_id>/collaborate', methods=['POST'])
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


@feed_bp.route('/projects/<int:project_id>/collaborate', methods=['GET'])
def get_collaborations(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    collabs = CollaborationRequest.query.filter_by(project_id=project_id).order_by(
        CollaborationRequest.created_at.desc()
    ).all()
    return jsonify({'collaborations': [c.to_dict() for c in collabs]}), 200


@feed_bp.route('/collaborations/<int:collab_id>', methods=['PUT'])
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


# --- Celebration Wall ---
@feed_bp.route('/celebration-wall', methods=['GET'])
def celebration_wall():
    """Get all completed projects and their builders."""
    completed = Project.query.filter_by(is_completed=True).order_by(
        Project.completed_at.desc()
    ).all()
    return jsonify({
        'projects': [p.to_dict() for p in completed]
    }), 200


# --- Support / Bug Reports ---
@feed_bp.route('/support', methods=['POST'])
@jwt_required()
def submit_support():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    category = data.get('category', '').strip()
    subject = data.get('subject', '').strip()
    description = data.get('description', '').strip()
    priority = data.get('priority', 'medium').strip()

    if not category or not subject or not description:
        return jsonify({'error': 'Category, subject and description are required'}), 400

    # Store the report
    report = SupportReport(
        category=category,
        subject=subject,
        description=description,
        priority=priority,
        user_id=user_id
    )
    db.session.add(report)
    db.session.commit()

    return jsonify({
        'message': 'Report submitted successfully. We will get back to you at your registered email.',
        'report': report.to_dict()
    }), 201


# --- Notifications ---
@feed_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    user_id = int(get_jwt_identity())
    notifications = Notification.query.filter_by(user_id=user_id).order_by(
        Notification.created_at.desc()
    ).limit(50).all()
    unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    return jsonify({
        'notifications': [n.to_dict() for n in notifications],
        'unread_count': unread_count
    }), 200


@feed_bp.route('/notifications/read', methods=['PUT'])
@jwt_required()
def mark_notifications_read():
    user_id = int(get_jwt_identity())
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'message': 'All notifications marked as read'}), 200


@feed_bp.route('/notifications/<int:notif_id>/read', methods=['PUT'])
@jwt_required()
def mark_notification_read(notif_id):
    user_id = int(get_jwt_identity())
    notif = db.session.get(Notification, notif_id)
    if not notif or notif.user_id != user_id:
        return jsonify({'error': 'Notification not found'}), 404
    notif.is_read = True
    db.session.commit()
    return jsonify({'notification': notif.to_dict()}), 200


# --- Activity Timeline ---
@feed_bp.route('/projects/<int:project_id>/activities', methods=['GET'])
def get_activities(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    activities = Activity.query.filter_by(project_id=project_id).order_by(
        Activity.created_at.desc()
    ).limit(100).all()
    return jsonify({'activities': [a.to_dict() for a in activities]}), 200
