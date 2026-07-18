"""
Flask Blueprint for SOAR (System Orchestration and Automated Response) API endpoints.
Provides REST endpoints for viewing SOAR actions, notifications, stats, and manual triggers.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Alert, SoarAction

# Use db.func instead of importing sqlalchemy.func directly
func = db.func

logger = logging.getLogger(__name__)

soar_bp = Blueprint('soar', __name__, url_prefix='/api/v1/soar')


@soar_bp.route('/actions', methods=['GET'])
def get_soar_actions():
    """
    List all SOAR actions with pagination and filtering.
    
    Query Parameters:
        limit: Number of records (default 50, max 500)
        offset: Starting position (default 0)
        status: Filter by status (pending, executing, completed, failed)
        action_type: Filter by action type (ip_block, container_isolate, etc.)
    
    Returns:
        200 OK with array of SOAR action objects
    """
    try:
        limit = min(max(request.args.get('limit', 50, type=int), 1), 500)
        offset = max(request.args.get('offset', 0, type=int), 0)
        status_filter = request.args.get('status', None, type=str)
        type_filter = request.args.get('action_type', None, type=str)

        query = SoarAction.query.order_by(SoarAction.created_at.desc())

        if status_filter:
            query = query.filter(SoarAction.status == status_filter)
        if type_filter:
            query = query.filter(SoarAction.action_type == type_filter)

        total = query.count()
        actions = query.offset(offset).limit(limit).all()

        return jsonify({
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": [action.to_dict() for action in actions]
        }), 200

    except Exception as e:
        logger.error(f"get_soar_actions error: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve SOAR actions"}), 500


@soar_bp.route('/actions/<int:action_id>', methods=['GET'])
def get_soar_action_detail(action_id):
    """
    Get details of a specific SOAR action.
    
    Args:
        action_id: ID of the SOAR action
    
    Returns:
        200 OK with SOAR action object
        404 if not found
    """
    try:
        action = SoarAction.query.get(action_id)
        if not action:
            return jsonify({"error": "SOAR action not found"}), 404

        # Include the parent alert info
        result = action.to_dict()
        if action.alert:
            result['alert'] = action.alert.to_dict()

        return jsonify({
            "status": "success",
            "data": result
        }), 200

    except Exception as e:
        logger.error(f"get_soar_action_detail error: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve SOAR action"}), 500


@soar_bp.route('/stats', methods=['GET'])
def get_soar_stats():
    """
    Get SOAR module statistics for the dashboard.
    
    Returns:
        200 OK with SOAR stats:
        {
            "total_actions": int,
            "actions_by_type": {type: count},
            "actions_by_status": {status: count},
            "auto_resolved_alerts": int,
            "avg_response_time_ms": float,
            "active_blocks": int,
            "actions_last_24h": int
        }
    """
    try:
        # Total SOAR actions
        total_actions = db.session.query(func.count(SoarAction.id)).scalar() or 0

        # Actions by type
        actions_by_type = db.session.query(
            SoarAction.action_type,
            func.count(SoarAction.id).label('count')
        ).group_by(SoarAction.action_type).all()
        actions_by_type_dict = {atype: count for atype, count in actions_by_type}

        # Actions by status
        actions_by_status = db.session.query(
            SoarAction.status,
            func.count(SoarAction.id).label('count')
        ).group_by(SoarAction.status).all()
        actions_by_status_dict = {status: count for status, count in actions_by_status}

        # Auto-resolved alerts (alerts resolved by SOAR)
        auto_resolved = db.session.query(func.count(Alert.id)).filter(
            Alert.status == 'Resolved'
        ).scalar() or 0

        # Average response time (completed actions only)
        avg_response = None
        completed_actions = SoarAction.query.filter(
            SoarAction.status == 'completed',
            SoarAction.executed_at.isnot(None),
            SoarAction.completed_at.isnot(None)
        ).all()
        
        if completed_actions:
            total_ms = 0
            count = 0
            for action in completed_actions:
                if action.executed_at and action.completed_at:
                    delta = (action.completed_at - action.executed_at).total_seconds() * 1000
                    total_ms += delta
                    count += 1
            avg_response = round(total_ms / count, 1) if count > 0 else 0

        # Active IP blocks (completed ip_block actions)
        active_blocks = db.session.query(func.count(SoarAction.id)).filter(
            SoarAction.action_type == 'ip_block',
            SoarAction.status == 'completed'
        ).scalar() or 0

        # Actions in last 24h
        cutoff_24h = datetime.utcnow() - timedelta(hours=24)
        actions_24h = db.session.query(func.count(SoarAction.id)).filter(
            SoarAction.created_at >= cutoff_24h
        ).scalar() or 0

        return jsonify({
            "status": "success",
            "data": {
                "total_actions": total_actions,
                "actions_by_type": actions_by_type_dict,
                "actions_by_status": actions_by_status_dict,
                "auto_resolved_alerts": auto_resolved,
                "avg_response_time_ms": avg_response,
                "active_blocks": active_blocks,
                "actions_last_24h": actions_24h,
                "timestamp": datetime.utcnow().isoformat()
            }
        }), 200

    except Exception as e:
        logger.error(f"get_soar_stats error: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve SOAR stats"}), 500


@soar_bp.route('/notifications', methods=['GET'])
def get_soar_notifications():
    """
    Get recent SOAR notifications for the dashboard live feed.
    Returns the most recent SOAR actions for toast notifications and activity feed.
    
    Query Parameters:
        limit: Number of notifications (default 30, max 100)
        since_id: Return only notifications after this ID (for incremental polling)
    
    Returns:
        200 OK with array of notification objects
    """
    try:
        limit = min(max(request.args.get('limit', 30, type=int), 1), 100)
        since_id = request.args.get('since_id', 0, type=int)

        query = SoarAction.query.order_by(SoarAction.created_at.desc())

        if since_id > 0:
            query = query.filter(SoarAction.id > since_id)

        actions = query.limit(limit).all()

        # Build notification objects with enhanced info
        notifications = []
        for action in actions:
            alert_rule = action.alert.rule if action.alert else 'Unknown'
            alert_severity = action.alert.severity if action.alert else 'MEDIUM'
            alert_host = action.alert.host if action.alert else 'unknown'

            # Icon and label for action types
            action_icons = {
                'ip_block': '🛡️',
                'container_isolate': '🔒',
                'service_restart': '🔄',
                'rate_limit': '⏱️',
                'credential_lock': '🔐',
                'log_escalation': '📋',
                'monitor_escalation': '📡',
            }

            action_labels = {
                'ip_block': 'IP Blocked',
                'container_isolate': 'Container Isolated',
                'service_restart': 'Service Restarted',
                'rate_limit': 'Rate Limited',
                'credential_lock': 'Credential Locked',
                'log_escalation': 'Incident Escalated',
                'monitor_escalation': 'Monitoring Escalated',
            }

            notifications.append({
                'id': action.id,
                'action_type': action.action_type,
                'action_icon': action_icons.get(action.action_type, '⚡'),
                'action_label': action_labels.get(action.action_type, action.action_type),
                'target': action.target,
                'status': action.status,
                'description': action.description,
                'alert_rule': alert_rule,
                'alert_severity': alert_severity,
                'alert_host': alert_host,
                'playbook': action.playbook,
                'created_at': action.created_at.isoformat() if action.created_at else None,
                'completed_at': action.completed_at.isoformat() if action.completed_at else None,
            })

        return jsonify({
            "status": "success",
            "data": notifications,
            "count": len(notifications)
        }), 200

    except Exception as e:
        logger.error(f"get_soar_notifications error: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve notifications"}), 500


@soar_bp.route('/trigger', methods=['POST'])
def manual_trigger():
    """
    Manually trigger a SOAR action on a specific alert.
    
    Payload:
    {
        "alert_id": 123,
        "action_type": "ip_block",
        "target": "192.168.1.100"
    }
    
    Returns:
        200 OK with the created SOAR action
        400 Bad Request if invalid
        404 if alert not found
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        alert_id = data.get('alert_id')
        action_type = data.get('action_type')
        target = data.get('target')

        if not all([alert_id, action_type, target]):
            return jsonify({"error": "Missing required fields: alert_id, action_type, target"}), 400

        valid_types = ['ip_block', 'container_isolate', 'service_restart', 
                       'rate_limit', 'credential_lock', 'log_escalation', 'monitor_escalation']
        if action_type not in valid_types:
            return jsonify({"error": f"Invalid action_type. Must be one of: {', '.join(valid_types)}"}), 400

        alert = Alert.query.get(alert_id)
        if not alert:
            return jsonify({"error": "Alert not found"}), 404

        # Create manual SOAR action
        soar_action = SoarAction(
            alert_id=alert_id,
            action_type=action_type,
            target=target,
            status='completed',
            description=f"Manual {action_type} on {target} — triggered by analyst",
            playbook=f"manual_{action_type}",
            executed_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            result_detail=f"[MANUAL] Action {action_type} manually triggered by SOC analyst on target {target}"
        )
        db.session.add(soar_action)

        # Update alert status
        alert.status = 'Resolved'
        alert.updated_at = datetime.utcnow()

        db.session.commit()

        logger.info(f"[SOAR] Manual action: {action_type} on {target} for alert #{alert_id}")

        return jsonify({
            "status": "success",
            "data": soar_action.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"manual_trigger error: {e}", exc_info=True)
        return jsonify({"error": "Failed to trigger SOAR action"}), 500
