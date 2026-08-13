#!/usr/bin/env python3
"""
SIEM server with SQL database storage, REST API, and SOAR action tracking.
Receives logs via HTTP, parses them, stores in PostgreSQL, and triggers alerts.
"""

from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging
import os
from collections import defaultdict

app = Flask(__name__)

# Database config
DB_HOST = os.getenv('DB_HOST', 'siem-postgres')
DB_PORT = os.getenv('DB_PORT', 5432)
DB_NAME = os.getenv('DB_NAME', 'siem_db')
DB_USER = os.getenv('DB_USER', 'siem_user')
DB_PASS = os.getenv('DB_PASS', 'siem_password')

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        return None

def init_db():
    """Initialize database schema."""
    conn = get_db_connection()
    if not conn:
        logger.error("Cannot initialize DB - connection failed")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Create logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP,
                level VARCHAR(10),
                message TEXT,
                host VARCHAR(255),
                ingested_at TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS idx_logs_host ON logs(host);
            CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
            CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
        """)
        
        # Create alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                host VARCHAR(255),
                severity VARCHAR(10),
                rule VARCHAR(255),
                log_message TEXT,
                log_id INTEGER REFERENCES logs(id),
                created_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS idx_alerts_host ON alerts(host);
            CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
            CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp);
        """)
        
        # Create SOAR actions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS soar_actions (
                id SERIAL PRIMARY KEY,
                target VARCHAR(255) NOT NULL,
                playbook VARCHAR(255) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                executed_at TIMESTAMP DEFAULT NOW(),
                result_detail TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS idx_soar_target ON soar_actions(target);
            CREATE INDEX IF NOT EXISTS idx_soar_playbook ON soar_actions(playbook);
            CREATE INDEX IF NOT EXISTS idx_soar_status ON soar_actions(status);
            CREATE INDEX IF NOT EXISTS idx_soar_executed ON soar_actions(executed_at);
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"DB init failed: {e}")
        return False

@app.route('/logs/ingest', methods=['POST'])
def ingest_logs():
    """Endpoint to receive and store logs."""
    try:
        data = request.get_json()
        logger.info(f"[INGEST] Received payload: {json.dumps(data)[:200]}")
        if not data:
            return jsonify({"error": "No JSON data"}), 400
        
        events = data if isinstance(data, list) else [data]
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "DB connection failed"}), 500
        
        cursor = conn.cursor()
        ingested_count = 0
        
        for event in events:
            try:
                timestamp = event.get('timestamp') or datetime.utcnow().isoformat()
                level = event.get('level', 'INFO')
                message = event.get('message', '')
                host = event.get('host', 'unknown')
                
                # Insert log
                cursor.execute("""
                    INSERT INTO logs (timestamp, level, message, host, ingested_at, created_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    RETURNING id;
                """, (timestamp, level, message, host))
                
                log_id = cursor.fetchone()[0]
                
                # Check alert rules
                check_alerts(cursor, log_id, host, message, level)
                
                ingested_count += 1
                logger.info(f"Ingested log from {host}: {message[:50]}")
            except Exception as e:
                logger.error(f"Error processing event: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "logs_ingested": ingested_count
        }), 200
    except Exception as e:
        logger.error(f"Error in ingest_logs: {e}")
        return jsonify({"error": str(e)}), 500

def check_alerts(cursor, log_id, host, message, level):
    """Generate alerts based on log content."""
    message_lower = (message or '').lower()
    
    # Alert rule 1: Error patterns
    if any(word in message_lower for word in ['error', 'fail', 'critical', 'exception']):
        cursor.execute("""
            INSERT INTO alerts (timestamp, host, severity, rule, log_message, log_id)
            VALUES (NOW(), %s, %s, %s, %s, %s);
        """, (host, 'HIGH', 'Error detected', message, log_id))
        logger.warning(f"ALERT: Error on {host} - {message}")
    
    # Alert rule 2: Warn level
    if level.upper() == 'WARN':
        cursor.execute("""
            INSERT INTO alerts (timestamp, host, severity, rule, log_message, log_id)
            VALUES (NOW(), %s, %s, %s, %s, %s);
        """, (host, 'MEDIUM', 'Warning detected', message, log_id))

@app.route('/status', methods=['GET'])
def status():
    """Health check and stats endpoint."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"status": "db_error"}), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT COUNT(*) as count FROM logs;")
        total_logs = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM alerts;")
        total_alerts = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT severity, COUNT(*) as count FROM alerts 
            GROUP BY severity;
        """)
        alert_summary = {row['severity']: row['count'] for row in cursor.fetchall()}
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "running",
            "total_logs": total_logs,
            "total_alerts": total_alerts,
            "alert_summary": alert_summary
        }), 200
    except Exception as e:
        logger.error(f"Error in status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    """Retrieve recent logs (last 100)."""
    try:
        limit = request.args.get('limit', 100, type=int)
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "DB error"}), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, timestamp, level, message, host, ingested_at
            FROM logs
            ORDER BY created_at DESC
            LIMIT %s;
        """, (limit,))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify([dict(row) for row in rows]), 200
    except Exception as e:
        logger.error(f"Error in get_logs: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/raw-logs', methods=['GET'])
def get_raw_logs():
    """Stream raw logs for live telemetry."""
    try:
        limit = request.args.get('limit', 50, type=int)
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "DB error"}), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, timestamp, level, message, host
            FROM logs
            ORDER BY created_at DESC
            LIMIT %s;
        """, (limit,))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify([dict(row) for row in rows]), 200
    except Exception as e:
        logger.error(f"Error in get_raw_logs: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/alerts', methods=['GET'])
def get_alerts():
    """Retrieve recent alerts (last 100)."""
    try:
        limit = request.args.get('limit', 100, type=int)
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "DB error"}), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, timestamp, host, severity, rule, log_message
            FROM alerts
            ORDER BY created_at DESC
            LIMIT %s;
        """, (limit,))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({"alerts": [dict(row) for row in rows]}), 200
    except Exception as e:
        logger.error(f"Error in get_alerts: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/soar/actions', methods=['GET'])
def get_soar_actions():
    """Retrieve SOAR action history."""
    try:
        limit = request.args.get('limit', 100, type=int)
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "DB error"}), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, target, playbook, status, executed_at, result_detail
            FROM soar_actions
            ORDER BY executed_at DESC
            LIMIT %s;
        """, (limit,))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({"actions": [dict(row) for row in rows]}), 200
    except Exception as e:
        logger.error(f"Error in get_soar_actions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/soar/actions', methods=['POST'])
def create_soar_action():
    """Create a SOAR action record."""
    try:
        data = request.get_json()
        if not data or 'target' not in data or 'playbook' not in data:
            return jsonify({"error": "Missing required fields"}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "DB error"}), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            INSERT INTO soar_actions (target, playbook, status, result_detail)
            VALUES (%s, %s, %s, %s)
            RETURNING *;
        """, (data['target'], data['playbook'], data.get('status', 'success'), data.get('result_detail', '')))
        
        action = dict(cursor.fetchone())
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify(action), 201
    except Exception as e:
        logger.error(f"Error in create_soar_action: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/soar/mitigations', methods=['GET'])
def get_mitigations():
    """Get active mitigations (demo data)."""
    return jsonify([
        {
            "id": 1,
            "type": "IP Block",
            "target": "192.168.1.100",
            "status": "active",
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        },
        {
            "id": 2,
            "type": "Agent Isolate",
            "target": "corp-portal-01",
            "status": "active",
            "expires_at": (datetime.utcnow() + timedelta(hours=2)).isoformat()
        }
    ]), 200

@app.route('/api/v1/soar/playbooks', methods=['GET'])
def get_playbooks():
    """Get available playbooks."""
    return jsonify([
        {
            "id": 1,
            "name": "brute_force_ip_block",
            "triggers": ["Multiple failed login attempts"],
            "description": "Blocks source IP after brute force detection"
        },
        {
            "id": 2,
            "name": "critical_error_restart",
            "triggers": ["Critical service error"],
            "description": "Automatically restarts failed services"
        },
        {
            "id": 3,
            "name": "ransomware_containment",
            "triggers": ["Suspicious file encryption"],
            "description": "Isolates affected systems and blocks C2 traffic"
        }
    ]), 200

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate user (demo)."""
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Demo authentication
        if username == 'admin' and password == 'SecureP@ssw0rd':
            return jsonify({
                "user": {
                    "username": username,
                    "id": 1,
                    "role": "admin"
                }
            }), 200
        else:
            return jsonify({"message": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dashboard-metrics', methods=['GET'])
def dashboard_metrics():
    """Get dashboard metrics."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "active_systems": 5,
                "total_transactions": 1234,
                "open_issues": 3,
                "security_score": 92,
                "response_time": 45,
                "data_volume": 2.3
            }), 200
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT COUNT(DISTINCT host) as count FROM logs;")
        active_systems = cursor.fetchone()['count'] or 5
        
        cursor.execute("SELECT COUNT(*) as count FROM logs;")
        total_transactions = cursor.fetchone()['count'] or 1234
        
        cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE severity IN ('HIGH', 'CRITICAL');")
        open_issues = cursor.fetchone()['count'] or 3
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "active_systems": active_systems,
            "total_transactions": total_transactions,
            "open_issues": open_issues,
            "security_score": 92,
            "response_time": 45,
            "data_volume": 2.3
        }), 200
    except Exception as e:
        logger.error(f"Error in dashboard_metrics: {e}")
        return jsonify({
            "active_systems": 5,
            "total_transactions": 1234,
            "open_issues": 3,
            "security_score": 92,
            "response_time": 45,
            "data_volume": 2.3
        }), 200

@app.route('/api/recent-activity', methods=['GET'])
def recent_activity():
    """Get recent system activity."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"activities": []}), 200
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT timestamp, 'Log ingested' as description, 'success' as status
            FROM logs
            ORDER BY created_at DESC
            LIMIT 10;
        """)
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        activities = [dict(row) for row in rows]
        return jsonify({"activities": activities}), 200
    except Exception as e:
        logger.error(f"Error in recent_activity: {e}")
        return jsonify({"activities": []}), 200

@app.route('/', methods=['GET'])
def dashboard():
    """Serve the dashboard HTML."""
    return render_template('dashboard.html')

if __name__ == '__main__':
    logger.info("Initializing SIEM database...")
    init_db()
    logger.info("SIEM Server starting on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)
