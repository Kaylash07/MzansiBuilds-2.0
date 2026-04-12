"""Authentication routes - Single Responsibility."""
import os
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from server.extensions import db
from server.models import User, Project
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'error': 'Username, email and password are required'}), 400

    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400

    if not _validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({'error': 'Username or email already exists'}), 409

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        bio=data.get('bio', '')
    )
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': user.to_dict()}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': user.to_dict()}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/users/<int:user_id>', methods=['GET'])
def public_profile(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    projects = Project.query.filter_by(owner_id=user_id).order_by(Project.updated_at.desc()).all()
    return jsonify({
        'user': user.to_dict(),
        'projects': [p.to_dict(include_owner=False) for p in projects]
    }), 200


@auth_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    if data.get('username'):
        existing = User.query.filter(User.username == data['username'], User.id != user_id).first()
        if existing:
            return jsonify({'error': 'Username already taken'}), 409
        user.username = data['username'].strip()
    if data.get('bio') is not None:
        user.bio = data['bio'].strip()
    if data.get('avatar_url') is not None:
        user.avatar_url = data['avatar_url'].strip()

    db.session.commit()
    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/upload-avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if 'avatar' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not _allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Use PNG, JPG, GIF, or WebP'}), 400

    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)

    ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    user.avatar_url = f"/uploads/avatars/{filename}"
    db.session.commit()
    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email = data.get('email', '').strip()
    if not email:
        return jsonify({'error': 'Email is required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'No account found with that email'}), 404

    # Generate a 6-digit reset code
    reset_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    user.reset_token = generate_password_hash(reset_code)
    user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(minutes=15)
    db.session.commit()

    # In production, this would be sent via email
    return jsonify({
        'message': 'Reset code generated. Check your email.',
        'reset_code': reset_code  # Shown directly since no email service
    }), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email = data.get('email', '').strip()
    code = data.get('code', '').strip()
    new_password = data.get('new_password', '')

    if not email or not code or not new_password:
        return jsonify({'error': 'Email, code and new password are required'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'No account found with that email'}), 404

    if not user.reset_token or not user.reset_token_expiry:
        return jsonify({'error': 'No reset code requested. Please request one first.'}), 400

    expiry = user.reset_token_expiry.replace(tzinfo=timezone.utc) if user.reset_token_expiry.tzinfo is None else user.reset_token_expiry
    if datetime.now(timezone.utc) > expiry:
        return jsonify({'error': 'Reset code has expired. Please request a new one.'}), 400

    if not check_password_hash(user.reset_token, code):
        return jsonify({'error': 'Invalid reset code'}), 400

    user.password_hash = generate_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.session.commit()

    return jsonify({'message': 'Password reset successful. You can now login.'}), 200
