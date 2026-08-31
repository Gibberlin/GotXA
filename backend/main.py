#!/usr/bin/env python3
"""
GOTXA SIEM/SOAR Backend - Main Application Entry Point
Production-ready Flask app with SQLAlchemy ORM, RBAC, Audit Logging, and Celery
"""

import os
import sys
from datetime import datetime
import logging

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy import text
from flask import Flask, jsonify, g
from flask_cors import CORS

from app.models import db
from app.auth import error_response
from app import api_v1, api_v1_actions, api_v1_extended, api_v1_consolidated, api_v1_reports, api_v1_db
from app import api_corporate, api_ingestion
from app.celery_app import make_celery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Application factory."""
    app = Flask(__name__)
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'postgresql://siem_user:[REDACTED]@siem-postgres:5432/siem_db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_SORT_KEYS'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize Celery
    celery = make_celery(app)
    
    # Create tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables initialized")
    
    # Register blueprints
    app.register_blueprint(api_v1.api)
    app.register_blueprint(api_v1_actions.api)
    app.register_blueprint(api_v1_extended.api)
    app.register_blueprint(api_v1_consolidated.api)
    app.register_blueprint(api_v1_reports.api)
    app.register_blueprint(api_v1_db.api)
    app.register_blueprint(api_corporate.api)
    app.register_blueprint(api_ingestion.api)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return error_response('NotFound', 'Endpoint not found', 404)
    
    @app.errorhandler(405)
    def method_not_allowed(e):
        return error_response('MethodNotAllowed', 'HTTP method not allowed', 405)
    
    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f'Internal error: {e}')
        return error_response('InternalError', 'Internal server error', 500)
    
    # Health checks
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint."""
        try:
            db.session.execute(text('SELECT 1'))
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'database': 'connected'
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    @app.route('/api/status', methods=['GET'])
    def status():
        """API status endpoint."""
        return jsonify({
            'status': 'running',
            'version': '1.0',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    return app

if __name__ == '__main__':
    app = create_app()
    logger.info("Starting GOTXA SIEM/SOAR Backend on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)
