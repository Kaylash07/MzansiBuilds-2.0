"""Project routes - CRUD operations following Single Responsibility."""
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from server.extensions import db
from server.models import Project, Milestone, Activity, User

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')

VALID_STAGES = ['idea', 'planning', 'in-progress', 'testing', 'completed']


@projects_bp.route('', methods=['POST'])
@jwt_required()
def create_project():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    stage = data.get('stage', 'idea').strip()

    if not title or not description:
        return jsonify({'error': 'Title and description are required'}), 400

    if stage not in VALID_STAGES:
        return jsonify({'error': f'Stage must be one of: {", ".join(VALID_STAGES)}'}), 400

    project = Project(
        title=title,
        description=description,
        tech_stack=data.get('tech_stack', '').strip(),
        repo_url=data.get('repo_url', '').strip(),
        category=data.get('category', '').strip(),
        stage=stage,
        support_needed=data.get('support_needed', '').strip(),
        owner_id=user_id,
        is_completed=(stage == 'completed')
    )
    if stage == 'completed':
        project.completed_at = datetime.now(timezone.utc)

    db.session.add(project)
    db.session.flush()  # get project.id

    # Log activity
    user = db.session.get(User, user_id)
    activity = Activity(
        type='created',
        message=f'{user.username} created this project',
        project_id=project.id,
        user_id=user_id
    )
    db.session.add(activity)
    db.session.commit()
    return jsonify({'project': project.to_dict()}), 201


@projects_bp.route('', methods=['GET'])
def list_projects():
    """Get all projects (public feed)."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    stage = request.args.get('stage', '')
    search = request.args.get('q', '').strip()

    query = Project.query.order_by(Project.updated_at.desc())
    if stage and stage in VALID_STAGES:
        query = query.filter_by(stage=stage)
    if search:
        like = f'%{search}%'
        from server.models import User
        query = query.join(User, Project.owner_id == User.id).filter(
            db.or_(
                Project.title.ilike(like),
                Project.description.ilike(like),
                Project.tech_stack.ilike(like),
                User.username.ilike(like)
            )
        )

    pagination = query.paginate(page=page, per_page=min(per_page, 50), error_out=False)
    projects = [p.to_dict() for p in pagination.items]

    return jsonify({
        'projects': projects,
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages
    }), 200


@projects_bp.route('/my', methods=['GET'])
@jwt_required()
def my_projects():
    user_id = int(get_jwt_identity())
    projects = Project.query.filter_by(owner_id=user_id).order_by(Project.updated_at.desc()).all()
    return jsonify({'projects': [p.to_dict(include_owner=False) for p in projects]}), 200


@projects_bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify({'project': project.to_dict()}), 200


@projects_bp.route('/<int:project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id):
    user_id = int(get_jwt_identity())
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    if project.owner_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    if data.get('title'):
        project.title = data['title'].strip()
    if data.get('description'):
        project.description = data['description'].strip()
    if data.get('tech_stack') is not None:
        project.tech_stack = data['tech_stack'].strip()
    if data.get('repo_url') is not None:
        project.repo_url = data['repo_url'].strip()
    if data.get('category') is not None:
        project.category = data['category'].strip()
    if data.get('support_needed') is not None:
        project.support_needed = data['support_needed'].strip()
    if data.get('stage'):
        if data['stage'] not in VALID_STAGES:
            return jsonify({'error': f'Stage must be one of: {", ".join(VALID_STAGES)}'}), 400
        old_stage = project.stage
        project.stage = data['stage']
        if data['stage'] == 'completed' and not project.is_completed:
            project.is_completed = True
            project.completed_at = datetime.now(timezone.utc)
        # Log stage change activity
        if old_stage != data['stage']:
            user = db.session.get(User, user_id)
            activity = Activity(
                type='stage_change',
                message=f'{user.username} moved project to {data["stage"]}',
                detail=f'{old_stage} → {data["stage"]}',
                project_id=project_id,
                user_id=user_id
            )
            db.session.add(activity)

    project.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'project': project.to_dict()}), 200


@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    user_id = int(get_jwt_identity())
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    if project.owner_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project deleted'}), 200


# --- Milestones ---

@projects_bp.route('/<int:project_id>/milestones', methods=['POST'])
@jwt_required()
def add_milestone(project_id):
    user_id = int(get_jwt_identity())
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    if project.owner_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'error': 'Milestone title is required'}), 400

    milestone = Milestone(
        title=title,
        description=data.get('description', '').strip(),
        project_id=project_id
    )
    db.session.add(milestone)

    # Log activity
    user = db.session.get(User, user_id)
    activity = Activity(
        type='milestone_added',
        message=f'{user.username} added milestone "{title}"',
        project_id=project_id,
        user_id=user_id
    )
    db.session.add(activity)
    project.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'milestone': milestone.to_dict()}), 201


@projects_bp.route('/<int:project_id>/milestones', methods=['GET'])
def get_milestones(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    milestones = Milestone.query.filter_by(project_id=project_id).order_by(Milestone.created_at.asc()).all()
    return jsonify({'milestones': [m.to_dict() for m in milestones]}), 200


@projects_bp.route('/<int:project_id>/milestones/<int:milestone_id>', methods=['PUT'])
@jwt_required()
def update_milestone(project_id, milestone_id):
    user_id = int(get_jwt_identity())
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    if project.owner_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    milestone = db.session.get(Milestone, milestone_id)
    if not milestone or milestone.project_id != project_id:
        return jsonify({'error': 'Milestone not found'}), 404

    data = request.get_json()
    if data.get('title'):
        milestone.title = data['title'].strip()
    if data.get('description') is not None:
        milestone.description = data['description'].strip()
    if data.get('is_achieved') is not None:
        milestone.is_achieved = bool(data['is_achieved'])
        if milestone.is_achieved and not milestone.achieved_at:
            milestone.achieved_at = datetime.now(timezone.utc)
            # Log activity
            user = db.session.get(User, user_id)
            activity = Activity(
                type='milestone_achieved',
                message=f'{user.username} achieved milestone "{milestone.title}"',
                project_id=project_id,
                user_id=user_id
            )
            db.session.add(activity)

    project.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'milestone': milestone.to_dict()}), 200
