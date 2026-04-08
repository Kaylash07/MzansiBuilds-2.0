"""Celebration routes - Single Responsibility: handles the celebration wall."""
from flask import Blueprint, jsonify
from server.extensions import db
from server.models import Project

celebration_bp = Blueprint('celebration', __name__, url_prefix='/api')


@celebration_bp.route('/celebration-wall', methods=['GET'])
def celebration_wall():
    """Get all completed projects and their builders."""
    completed = Project.query.filter_by(is_completed=True).order_by(
        Project.completed_at.desc()
    ).all()
    return jsonify({
        'projects': [p.to_dict() for p in completed]
    }), 200
