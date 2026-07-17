#!/usr/bin/env python3
"""
Vulnerable Flask Application for Cyber Range
Demonstrates SQL Injection and Command Injection vulnerabilities
Sends logs to log-collector-dedicated container via HTTP POST
"""

import os
import sys
import logging
import subprocess
import sqlite3
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from pathlib import Path

app = Flask(__name__)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Local SQLite database for user authentication
DB_PATH = '/tmp/corp_users.db'
LOG_FILE = '/logs/corp-portal/app.log'

# Correct URL to log collector using container name
LOG_COLLECTOR_URL = 'http://log-collector-dedicated:5005/ingest'

def init_database():
    """Initialize local user database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    ''')
    cursor.execute("DELETE FROM users")
    cursor.execute("INSERT INTO users VALUES (1, 'admin', 'SecureP@ssw0rd', 'admin')")
    cursor.execute("INSERT INTO users VALUES (2, 'user1', 'password123', 'user')")
    cursor.execute("INSERT INTO users VALUES (3, 'user2', 'password456', 'user')")
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def log_activity(activity_type, details):
    """Log activity to file and send to collector."""
    timestamp = datetime.utcnow().isoformat()
    log_entry = f"[{timestamp}] {activity_type}: {details}\n"
    
    # Ensure log directory exists
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"Failed to write log: {e}")
    
    # Determine severity for collector
    severity = 'LOW'
    if any(x in activity_type for x in ['ERROR', 'FAILURE', 'INJECTION', 'COMMAND']):
        severity = 'HIGH'
    elif any(x in activity_type for x in ['AUTH', 'SQL']):
        severity = 'MEDIUM'
    
    # Send to log collector
    try:
        log_json = {
            'timestamp': timestamp,
            'level': severity,
            'message': f'{activity_type}: {details}',
            'host': 'corp-portal-agent',
            'source_type': 'corporate'
        }
        requests.post(
            LOG_COLLECTOR_URL,
            json=log_json,
            timeout=3
        )
    except Exception as e:
        logger.debug(f"Failed to send to collector: {e}")
    
    logger.info(f"{activity_type}: {details}")

@app.route('/', methods=['GET'])
def index():
    """Serve the vulnerable login dashboard."""
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Corporate Portal - Vulnerable Auth</title>
        <style>
            body { font-family: Arial; background: #f5f5f5; padding: 50px; }
            .container { max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; }
            .form-group { margin: 15px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
            button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background: #0056b3; }
            .warning { color: #d32f2f; font-size: 12px; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔓 Corporate Authentication Portal</h1>
            <form method="POST" action="/login">
                <div class="form-group">
                    <label>Username:</label>
                    <input type="text" name="username" placeholder="e.g., admin">
                </div>
                <div class="form-group">
                    <label>Password:</label>
                    <input type="password" name="password" placeholder="e.g., SecureP@ssw0rd">
                </div>
                <button type="submit">Login</button>
            </form>
            <p class="warning">⚠️ WARNING: This is a VULNERABLE application for cyber range testing only!</p>
        </div>
    </body>
    </html>
    '''
    return html, 200, {'Content-Type': 'text/html'}

@app.route('/login', methods=['POST'])
def login_vulnerable():
    """VULNERABLE: SQL Injection endpoint"""
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    
    log_activity('AUTH_ATTEMPT', f'username={username}')
    
    sql_query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    log_activity('SQL_EXECUTED', sql_query)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql_query)
        result = cursor.fetchone()
        conn.close()
        
        if result:
            log_activity('AUTH_SUCCESS', f'User {username} authenticated')
            return jsonify({
                "status": "success",
                "message": f"Welcome {dict(result)['username']}!",
                "user": dict(result)
            }), 200
        else:
            log_activity('AUTH_FAILURE', f'Invalid credentials for {username}')
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401
    
    except Exception as e:
        log_activity('SQL_ERROR', str(e))
        return jsonify({"status": "error", "message": f"Error: {str(e)}"}), 500

@app.route('/diagnostic', methods=['POST'])
def diagnostic_vulnerable():
    """VULNERABLE: Command Injection endpoint"""
    host = request.form.get('host', '')
    
    log_activity('DIAGNOSTIC_REQUEST', f'host={host}')
    
    command = f"ping -c 1 {host}"
    log_activity('COMMAND_EXECUTED', command)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            timeout=5,
            text=True
        )
        
        log_activity('COMMAND_OUTPUT', result.stdout[:200])
        
        return jsonify({
            "status": "success",
            "command": command,
            "output": result.stdout
        }), 200
    
    except subprocess.TimeoutExpired:
        log_activity('COMMAND_TIMEOUT', command)
        return jsonify({"status": "error", "message": "Command timeout"}), 500
    except Exception as e:
        log_activity('COMMAND_ERROR', str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "corp-portal-agent"}), 200

if __name__ == '__main__':
    init_database()
    logger.info("Starting vulnerable Flask application on 0.0.0.0:5001")
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
