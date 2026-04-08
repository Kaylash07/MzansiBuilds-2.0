"""Flask application factory - Dependency Inversion Principle."""
import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from server.config import Config
from server.extensions import db, jwt


def create_app(config_class=Config):
    app = Flask(
        __name__,
        static_folder='../static',
        template_folder='../templates'
    )
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    CORS(app)

    # Register blueprints (Open/Closed - extensible via new blueprints)
    from server.routes.auth import auth_bp
    from server.routes.projects import projects_bp
    from server.routes.feed import feed_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(feed_bp)

    # Serve uploaded files
    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        upload_root = os.path.join(os.path.dirname(app.root_path), 'uploads')
        return send_from_directory(upload_root, filename)

    # Serve frontend
    @app.route('/')
    def index():
        return send_from_directory(app.template_folder, 'index.html')

    @app.route('/<path:path>')
    def serve_static(path):
        if path.startswith('api/'):
            return {'error': 'Not found'}, 404
        try:
            return send_from_directory(app.static_folder, path)
        except Exception:
            return send_from_directory(app.template_folder, 'index.html')

    # Create tables and ensure upload directory exists
    with app.app_context():
        db.create_all()
        os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)

    return app
