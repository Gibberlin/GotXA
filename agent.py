#!/usr/bin/env python3
"""
Lightweight agent container - generates structured JSON logs and ships to SIEM.
Direct HTTP POST ingestion (no intermediate log-processor).
"""

import json
import requests
import time
import logging
import random
from datetime import datetime
from socket import gethostname

# ============================================================================
# AGENT CONFIGURATION
# ============================================================================

SIEM_INGRESS_URL = 'http://siem-server:5000/api/v1/ingress'
AGENT_HOSTNAME = gethostname()
LOG_BATCH_SIZE = 5
BATCH_INTERVAL = 3
REQUEST_TIMEOUT = 5

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# LOG GENERATION & TEMPLATES
# ============================================================================

LOG_LEVELS = ['DEBUG', 'INFO', 'WARN', 'ERROR']

LOG_MESSAGES = [
    'Database connection timeout',
    'Request processed successfully',
    'Memory usage above threshold',
    'User login attempt',
    'API call failed',
    'Cache invalidated',
    'Disk space running low',
    'Service restarted',
    'Configuration loaded',
    'Task completed',
    'Authentication failed',
    'Permission denied',
    'Network unreachable',
    'File not found',
    'Connection refused',
]

# Slightly bias toward realistic log patterns
REALISTIC_PATTERNS = [
    'Failed login from 192.168.1.100',
    'Brute force attempt detected',
    'Unauthorized access to /admin',
    'Port scan detected from 10.0.0.50',
    'Critical system error: out of memory',
    'Service down for maintenance',
    'SSL certificate expiring in 7 days',
    'Database backup completed',
    'Configuration deployment failed',
    'SSH key changed',
]

# ============================================================================
# LOG GENERATION ENGINE
# ============================================================================

def generate_log():
    """Generate a single structured log entry."""
    level = random.choice(LOG_LEVELS)
    
    # 30% chance of realistic pattern, 70% generic messages
    if random.random() < 0.3:
        message = random.choice(REALISTIC_PATTERNS)
    else:
        message = random.choice(LOG_MESSAGES)
    
    return {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'level': level,
        'message': message,
        'host': AGENT_HOSTNAME
    }

# ============================================================================
# LOG SHIPPING ENGINE
# ============================================================================

def ship_logs(batch):
    """Send batch of logs to SIEM ingress endpoint via HTTP POST."""
    try:
        headers = {'Content-Type': 'application/json'}
        payload = json.dumps(batch)
        
        logger.info(f"Shipping {len(batch)} logs to {SIEM_INGRESS_URL}")
        
        response = requests.post(
            SIEM_INGRESS_URL,
            data=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(
                f"✓ Shipped {len(batch)} logs | "
                f"Ingested: {result.get('logs_ingested', 0)} | "
                f"Alerts: {result.get('alerts_generated', 0)}"
            )
            return True
        else:
            logger.error(
                f"✗ Ship failed: HTTP {response.status_code} - {response.text[:100]}"
            )
            return False
    
    except requests.exceptions.Timeout:
        logger.error(f"✗ Ship timeout: {SIEM_INGRESS_URL}")
        return False
    except requests.exceptions.ConnectionError:
        logger.error(f"✗ Connection error: {SIEM_INGRESS_URL}")
        return False
    except Exception as e:
        logger.error(f"✗ Ship error: {e}", exc_info=True)
        return False

# ============================================================================
# AGENT MAIN LOOP
# ============================================================================

def main():
    """Main agent loop - generates and ships logs in batches."""
    logger.info(f"🚀 Agent '{AGENT_HOSTNAME}' starting")
    logger.info(f"📤 Shipping logs to: {SIEM_INGRESS_URL}")
    logger.info(f"⏱️  Batch size: {LOG_BATCH_SIZE}, interval: {BATCH_INTERVAL}s")
    
    batch = []
    
    try:
        while True:
            # Generate log
            log = generate_log()
            batch.append(log)
            
            logger.debug(f"Generated: {log['level']} - {log['message']}")
            
            # Ship batch when full
            if len(batch) >= LOG_BATCH_SIZE:
                ship_logs(batch)
                batch = []
            
            # Wait before next log
            time.sleep(BATCH_INTERVAL / LOG_BATCH_SIZE)
    
    except KeyboardInterrupt:
        logger.info("Agent shutting down...")
        if batch:
            logger.info(f"Shipping final batch of {len(batch)} logs...")
            ship_logs(batch)
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        if batch:
            ship_logs(batch)
        raise

if __name__ == '__main__':
    main()
