"""Feed routes - Single Responsibility: handles the live project feed."""
from flask import Blueprint, request, jsonify
from server.extensions import db
from server.models import Project, User

feed_bp = Blueprint('feed', __name__, url_prefix='/api')


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
