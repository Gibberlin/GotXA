"""
Flask Blueprint for log ingestion and management API endpoints.
Handles high-throughput structured JSON log intake from agents.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Log, Alert
from engine import alert_engine

logger = logging.getLogger(__name__)

ingress_bp = Blueprint('ingress', __name__, url_prefix='/api/v1')


@ingress_bp.route('/ingress', methods=['POST'])
def ingest_logs():
    """
    High-throughput unified log ingestion endpoint for agents.
    
    Expects JSON payload (single object or array of objects):
    {
        "timestamp": "2026-07-14T19:31:20Z",
        "level": "ERROR",
        "message": "Database connection failed",
        "host": "agent-1"
    }
    
    Returns:
        200 OK with ingestion summary on success
        400 Bad Request on malformed input
        500 Internal Server Error on DB failure
    """
    try:
        data = request.get_json()
        if not data:
            logger.warning("Ingress: Received empty JSON payload")
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Normalize to list
        events = data if isinstance(data, list) else [data]
        if not events:
            return jsonify({"error": "Empty events list"}), 400
        
        ingested_count = 0
        alert_count = 0
        
        try:
            for event in events:
                # Validate required fields
                if not isinstance(event, dict):
                    logger.warning(f"Ingress: Event is not a dictionary: {type(event)}")
                    continue
                
                required_fields = ['message', 'host']
                if not all(field in event for field in required_fields):
                    logger.warning(f"Ingress: Event missing required fields: {event}")
                    continue
                
                try:
                    # Parse and validate timestamp
                    timestamp_str = event.get('timestamp')
                    if timestamp_str:
                        try:
                            # Handle ISO 8601 format
                            if 'T' in str(timestamp_str):
                                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            else:
                                timestamp = datetime.utcnow()
                        except (ValueError, TypeError):
                            timestamp = datetime.utcnow()
                    else:
                        timestamp = datetime.utcnow()
                    
                    level = event.get('level', 'INFO').upper()
                    if level not in ['DEBUG', 'INFO', 'WARN', 'ERROR']:
                        level = 'INFO'
                    
                    message = str(event.get('message', '')).strip()
                    if not message:
                        logger.warning("Ingress: Event message is empty")
                        continue
                    
                    host = str(event.get('host', 'unknown')).strip()
                    if not host:
                        host = 'unknown'
                    
                    # Create log record
                    log = Log(
                        timestamp=timestamp,
                        level=level,
                        message=message,
                        host=host,
                        ingested_at=datetime.utcnow()
                    )
                    db.session.add(log)
                    db.session.flush()  # Get log ID without committing
                    
                    # Analyze and generate alerts
                    detected_alerts = alert_engine.analyze_log(log.id, host, message, level)
                    for severity, rule_name, rule_details in detected_alerts:
                        alert = Alert(
                            host=host,
                            severity=severity,
                            rule=rule_name,
                            log_message=rule_details,
                            status='Open',
                            log_id=log.id
                        )
                        db.session.add(alert)
                        alert_count += 1
                    
                    ingested_count += 1
                    logger.info(f"Ingress: Logged from {host}: {message[:50]} | {len(detected_alerts)} alerts generated")
                
                except Exception as e:
                    logger.error(f"Ingress: Error processing event {event}: {e}", exc_info=True)
                    continue
            
            # Commit all changes
            db.session.commit()
            
            return jsonify({
                "status": "success",
                "logs_ingested": ingested_count,
                "alerts_generated": alert_count,
                "timestamp": datetime.utcnow().isoformat()
            }), 200
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ingress: Database error: {e}", exc_info=True)
            return jsonify({"error": "Database error", "detail": str(e)}), 500
    
    except Exception as e:
        logger.error(f"Ingress: Unexpected error: {e}", exc_info=True)
        return jsonify({"error": "Unexpected server error"}), 500


@ingress_bp.route('/logs', methods=['GET'])
def get_logs():
    """
    Retrieve historical logs with pagination.
    
    Query Parameters:
        limit: Number of records (default 100, max 1000)
        offset: Starting position (default 0)
        host: Filter by hostname
        level: Filter by log level
    
    Returns:
        200 OK with array of log objects
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        host_filter = request.args.get('host', None, type=str)
        level_filter = request.args.get('level', None, type=str)
        
        # Validate pagination params
        limit = min(max(limit, 1), 1000)  # Clamp 1-1000
        offset = max(offset, 0)
        
        query = Log.query.order_by(Log.created_at.desc())
        
        if host_filter:
            query = query.filter(Log.host == host_filter)
        if level_filter:
            query = query.filter(Log.level == level_filter.upper())
        
        total = query.count()
        logs = query.offset(offset).limit(limit).all()
        
        return jsonify({
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": [log.to_dict() for log in logs]
        }), 200
    
    except Exception as e:
        logger.error(f"get_logs error: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve logs"}), 500


@ingress_bp.route('/logs/<int:log_id>', methods=['DELETE'])
def delete_log(log_id):
    """
    Administrative endpoint to delete/archive a log record.
    
    Args:
        log_id: ID of log to delete
    
    Returns:
        200 OK on success
        404 Not Found if log doesn't exist
    """
    try:
        log = Log.query.get(log_id)
        if not log:
            return jsonify({"error": "Log not found"}), 404
        
        # Cascade delete alerts via relationship
        db.session.delete(log)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": f"Log {log_id} deleted"
        }), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"delete_log error: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete log"}), 500


@ingress_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """
    Retrieve security alerts with pagination.
    
    Query Parameters:
        limit: Number of records (default 100, max 1000)
        offset: Starting position (default 0)
        severity: Filter by severity (HIGH, MEDIUM, LOW)
        status: Filter by status (Open, Investigating, Resolved)
        host: Filter by hostname
    
    Returns:
        200 OK with array of alert objects
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        severity_filter = request.args.get('severity', None, type=str)
        status_filter = request.args.get('status', None, type=str)
        host_filter = request.args.get('host', None, type=str)
        
        limit = min(max(limit, 1), 1000)
        offset = max(offset, 0)
        
        query = Alert.query.order_by(Alert.created_at.desc())
        
        if severity_filter:
            query = query.filter(Alert.severity == severity_filter.upper())
        if status_filter:
            query = query.filter(Alert.status == status_filter)
        if host_filter:
            query = query.filter(Alert.host == host_filter)
        
        total = query.count()
        alerts = query.offset(offset).limit(limit).all()
        
        return jsonify({
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": [alert.to_dict() for alert in alerts]
        }), 200
    
    except Exception as e:
        logger.error(f"get_alerts error: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve alerts"}), 500


@ingress_bp.route('/alerts/<int:alert_id>', methods=['PUT'])
def update_alert(alert_id):
    """
    Update an alert's incident lifecycle status.
    
    Payload:
    {
        "status": "Investigating" | "Resolved" | "Open",
        "notes": "Optional analyst notes"
    }
    
    Returns:
        200 OK with updated alert object
        400 Bad Request on invalid status
        404 Not Found if alert doesn't exist
    """
    try:
        alert = Alert.query.get(alert_id)
        if not alert:
            return jsonify({"error": "Alert not found"}), 404
        
        data = request.get_json() or {}
        
        new_status = data.get('status', '').strip()
        valid_statuses = ['Open', 'Investigating', 'Resolved']
        
        if new_status and new_status not in valid_statuses:
            return jsonify({
                "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }), 400
        
        if new_status:
            alert.status = new_status
            alert.updated_at = datetime.utcnow()
        
        db.session.commit()
        logger.info(f"Alert {alert_id} updated to status: {alert.status}")
        
        return jsonify({
            "status": "success",
            "data": alert.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"update_alert error: {e}", exc_info=True)
        return jsonify({"error": "Failed to update alert"}), 500
