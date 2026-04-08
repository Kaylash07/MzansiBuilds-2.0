"""Activity routes - Single Responsibility: handles project activity timelines."""
from flask import Blueprint, jsonify
from server.extensions import db
from server.models import Project, Activity

activities_bp = Blueprint('activities', __name__, url_prefix='/api')


@activities_bp.route('/projects/<int:project_id>/activities', methods=['GET'])
def get_activities(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    activities = Activity.query.filter_by(project_id=project_id).order_by(
        Activity.created_at.desc()
    ).limit(100).all()
    return jsonify({'activities': [a.to_dict() for a in activities]}), 200
