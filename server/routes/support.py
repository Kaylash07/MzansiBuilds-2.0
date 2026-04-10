"""Support routes - Single Responsibility: handles support and bug reports."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from server.extensions import db
from server.models import User, SupportReport

support_bp = Blueprint('support', __name__, url_prefix='/api')


@support_bp.route('/support', methods=['POST'])
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
