#!/usr/bin/env python3
"""
Lightweight Logstash replacement - receives logs via TCP and forwards to SIEM server.
"""

import socket
import json
import requests
import threading
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SIEM_URL = "http://siem-server:5000/logs/ingest"
TCP_HOST = "0.0.0.0"
TCP_PORT = 5000

def forward_to_siem(log_data):
    """Forward parsed log to SIEM server."""
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(SIEM_URL, json=log_data, headers=headers, timeout=5)
        if response.status_code == 200:
            logger.info(f"Forwarded: {log_data.get('host', 'unknown')}")
        else:
            logger.error(f"SIEM returned {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to forward: {e}")

def parse_log(raw_log, host):
    """Parse raw log line into structured format."""
    try:
        # Expected format: [2026-01-15T10:30:45] LEVEL - message
        parts = raw_log.strip().split('] ', 1)
        if len(parts) == 2:
            timestamp = parts[0].lstrip('[')
            rest = parts[1].split(' - ', 1)
            if len(rest) == 2:
                level = rest[0]
                message = rest[1]
                return {
                    'timestamp': timestamp,
                    'level': level,
                    'message': message,
                    'host': host,
                    '@siem_ingested_at': datetime.utcnow().isoformat()
                }
    except Exception as e:
        logger.debug(f"Parse error: {e}")
    
    # Fallback
    return {
        'message': raw_log,
        'host': host,
        '@siem_ingested_at': datetime.utcnow().isoformat()
    }

def handle_client(conn, addr):
    """Handle incoming TCP connection from an agent."""
    logger.info(f"Connection from {addr}")
    host = addr[0]
    
    try:
        data = conn.recv(2048).decode('utf-8').strip()
        if data:
            log = parse_log(data, host)
            forward_to_siem(log)
    except Exception as e:
        logger.error(f"Error handling {addr}: {e}")
    finally:
        conn.close()

def start_tcp_server():
    """Start TCP server to receive logs."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((TCP_HOST, TCP_PORT))
    server.listen(5)
    logger.info(f"Log processor listening on {TCP_HOST}:{TCP_PORT}")
    
    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        server.close()

if __name__ == '__main__':
    start_tcp_server()
