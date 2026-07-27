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
        """Serve the main SIEM operations dashboard from frontend directory."""
        try:
            frontend_path = '/app/frontend/siem_dashboard/index.html'
            logger.debug(f"Loading dashboard from: {frontend_path}")
            with open(frontend_path, 'r', encoding='utf-8') as f:
                return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}
        except FileNotFoundError:
            logger.error(f"Dashboard not found at: {frontend_path}")
            return jsonify({"error": "Dashboard not found"}), 404
        except Exception as e:
            logger.error(f"Error serving dashboard: {e}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
    
    # ========================================================================
    # SCADA DASHBOARD ROUTE
    # ========================================================================
    
    @app.route('/scada', methods=['GET'])
    def scada_dashboard():
        """Serve the SCADA HMI dashboard from frontend directory."""
        try:
            frontend_path = '/app/frontend/scada_dashboard/index.html'
            logger.debug(f"Loading SCADA dashboard from: {frontend_path}")
            with open(frontend_path, 'r', encoding='utf-8') as f:
                return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}
        except FileNotFoundError:
            logger.error(f"SCADA dashboard not found at: {frontend_path}")
            return jsonify({"error": "SCADA dashboard not found"}), 404
        except Exception as e:
            logger.error(f"Error serving SCADA dashboard: {e}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
    
    # ========================================================================
    # SCADA GATEWAY PROXY ROUTES - FORWARD TO PORT 5002
    # ========================================================================
    
    @app.route('/api/modbus', methods=['GET'])
    def modbus_proxy():
        """Proxy Modbus data from SCADA gateway (port 5002)."""
        try:
            import requests
            response = requests.get('http://ot-scada-gateway:5002/api/modbus', timeout=5)
            return jsonify(response.json()), response.status_code
        except Exception as e:
            logger.error(f"Error proxying to SCADA gateway: {e}")
            return jsonify({
                "error": "Cannot connect to SCADA gateway",
                "refinery_1": {"status": "offline", "temperature": 0, "pressure": 0},
                "refinery_2": {"status": "offline", "flow_rate": 0}
            }), 503
    
    @app.route('/api/modbus/refinery-1', methods=['GET'])
    def modbus_refinery1_proxy():
        """Proxy Refinery-1 Modbus data from SCADA gateway."""
        try:
            import requests
            response = requests.get('http://ot-scada-gateway:5002/api/modbus/refinery-1', timeout=5)
            return jsonify(response.json()), response.status_code
        except Exception as e:
            logger.error(f"Error proxying to SCADA gateway: {e}")
            return jsonify({"status": "offline", "temperature": 0, "pressure": 0}), 503
    
    @app.route('/api/modbus/refinery-2', methods=['GET'])
    def modbus_refinery2_proxy():
        """Proxy Refinery-2 Modbus data from SCADA gateway."""
        try:
            import requests
            response = requests.get('http://ot-scada-gateway:5002/api/modbus/refinery-2', timeout=5)
            return jsonify(response.json()), response.status_code
        except Exception as e:
            logger.error(f"Error proxying to SCADA gateway: {e}")
            return jsonify({"status": "offline", "flow_rate": 0}), 503
    
    # ========================================================================
    # DASHBOARD DATA API - FOR FRONTEND VISUALIZATION
    # ========================================================================
    
    @app.route('/api/dashboard-data', methods=['GET'])
    def dashboard_data():
        """Get aggregated data for the dashboard (legacy format)."""
        try:
            from models import Log, Alert
            from sqlalchemy import func
            
            # Total stats
            total_logs = db.session.query(func.count(Log.id)).scalar() or 0
            total_alerts = db.session.query(func.count(Alert.id)).scalar() or 0
            
            # Logs by level
            logs_by_level = db.session.query(
                Log.level,
                func.count(Log.id).label('count')
            ).group_by(Log.level).all()
            logs_by_level_dict = {level: count for level, count in logs_by_level}
            
            # Alerts by severity
            alerts_by_severity = db.session.query(
                Alert.severity,
                func.count(Alert.id).label('count')
            ).group_by(Alert.severity).all()
            alerts_by_severity_dict = {sev: count for sev, count in alerts_by_severity}
            
            # Logs by host (top 10)
            logs_by_host = db.session.query(
                Log.host,
                func.count(Log.id).label('count')
            ).group_by(Log.host).order_by(func.count(Log.id).desc()).limit(10).all()
            logs_by_host_dict = {host: count for host, count in logs_by_host}
            
            # Recent logs (last 20)
            recent_logs = Log.query.order_by(Log.created_at.desc()).limit(20).all()
            
            # Recent alerts (last 20)
            recent_alerts = Alert.query.order_by(Alert.created_at.desc()).limit(20).all()
            
            return jsonify({
                "total_logs": total_logs,
                "total_alerts": total_alerts,
                "logs_by_level": logs_by_level_dict,
                "alerts_by_severity": alerts_by_severity_dict,
                "logs_by_host": logs_by_host_dict,
                "recent_logs": [log.to_dict() for log in recent_logs],
                "recent_alerts": [alert.to_dict() for alert in recent_alerts]
            }), 200
        except Exception as e:
            logger.error(f"Error in dashboard_data: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
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
    logger.info("🎯 SCADA HMI:     http://localhost:5000/scada")
    logger.info("🔌 API v1:        http://localhost:5000/api/v1/")
    logger.info("📡 Modbus API:    http://localhost:5000/api/modbus (proxied to 5002)")
    logger.info("❤️  Health Check:  http://localhost:5000/health")
    logger.info("=" * 70)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
