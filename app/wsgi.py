#!/usr/bin/env python3
"""
SIEM/SOAR Central Server WSGI Entry Point
Production-Grade Architecture with Gunicorn
"""

import os
import sys
import logging
from datetime import datetime

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, '..')
sys.path.insert(0, APP_DIR)

from flask import Flask, jsonify
from sqlalchemy import text

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# IMPORT APP COMPONENTS
# ============================================================================

try:
    from models import db
    from api.ingress import ingress_bp
    from api.dashboard import dashboard_bp
    from api.soar_api import soar_bp
    logger.info("✓ Successfully imported app components")
except Exception as e:
    logger.error(f"✗ Failed to import app components: {e}", exc_info=True)
    raise

# ============================================================================
# FLASK APPLICATION FACTORY
# ============================================================================

def create_app():
    """Create and configure Flask application."""
    
    app = Flask(
        __name__,
        static_folder=os.path.join(BASE_DIR, 'static'),
        static_url_path='/static',
        template_folder=os.path.join(BASE_DIR, 'templates')
    )
    
    # Configuration
    db_url = os.getenv(
        'DATABASE_URL',
        'postgresql://siem_user:siem_password@postgres:5432/siem_db'
    )
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_SORT_KEYS'] = False
    
    logger.info(f"Database: {db_url.split('@')[1] if '@' in db_url else 'local'}")
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(ingress_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(soar_bp)
    
    # ========================================================================
    # ROOT ROUTE - SERVE DASHBOARD
    # ========================================================================
    
    @app.route('/', methods=['GET'])
    def dashboard():
        """Serve the main SIEM operations dashboard."""
        try:
            dashboard_path = os.path.join(BASE_DIR, 'static', 'dashboard', 'index.html')
            logger.debug(f"Loading dashboard from: {dashboard_path}")
            with open(dashboard_path, 'r', encoding='utf-8') as f:
                return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}
        except FileNotFoundError:
            logger.error(f"Dashboard not found at: {dashboard_path}")
            return jsonify({"error": "Dashboard not found"}), 404
        except Exception as e:
            logger.error(f"Error serving dashboard: {e}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
    
    # ========================================================================
    # LEGACY LOG INGESTION COMPATIBILITY ROUTE
    # ========================================================================
    
    @app.route('/logs/ingest', methods=['POST'])
    def legacy_ingest_logs():
        """Route legacy log ingress requests to the new v1 API handler."""
        from api.ingress import ingest_logs
        return ingest_logs()
    
    # ========================================================================
    # HEALTH CHECK ENDPOINT
    # ========================================================================
    
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint."""
        try:
            db.session.execute(text('SELECT 1'))
            return jsonify({
                "status": "healthy",
                "service": "SIEM/SOAR Operations Center",
                "timestamp": datetime.utcnow().isoformat()
            }), 200
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return jsonify({"status": "unhealthy", "error": str(e)}), 503
    
    # ========================================================================
    # ERROR HANDLERS
    # ========================================================================
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle bad request errors."""
        logger.warning(f"Bad request: {error}")
        desc = getattr(error, 'description', 'Bad request')
        return jsonify({"error": "Bad request", "message": desc}), 400
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle not found errors."""
        logger.debug(f"404 Not found: {error}")
        return jsonify({"error": "Resource not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors."""
        logger.error(f"500 Internal server error: {error}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500
    
    # ========================================================================
    # DATABASE INITIALIZATION
    # ========================================================================
    
    with app.app_context():
        try:
            db.create_all()
            # Auto-migrate: Add missing SOAR columns to pre-existing alerts table if they don't exist
            db.session.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Open' NOT NULL;"))
            db.session.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW() NOT NULL;"))
            db.session.commit()
            logger.info("✓ Database tables initialized/verified and schema migrated")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database initialization/migration error: {e}", exc_info=True)
    
    # Start SOAR engine background thread
    try:
        from soar_engine import SoarEngine
        import soar_engine as soar_module
        engine = SoarEngine(app)
        engine.start()
        soar_module.soar_engine_instance = engine
        logger.info("✓ SOAR engine started")
    except Exception as e:
        logger.error(f"Failed to start SOAR engine: {e}", exc_info=True)
    
    return app

# ============================================================================
# GUNICORN ENTRY POINT
# ============================================================================

# This is the app that gunicorn imports
app = create_app()

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("🔒 SIEM/SOAR Operations Center - STARTING (Development Mode)")
    logger.info("=" * 70)
    logger.info("📊 Dashboard:     http://localhost:5000/")
    logger.info("🔌 API v1:        http://localhost:5000/api/v1/")
    logger.info("❤️  Health Check:  http://localhost:5000/health")
    logger.info("=" * 70)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
