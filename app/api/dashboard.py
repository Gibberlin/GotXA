"""
Flask Blueprint for dashboard data aggregation endpoints.
Provides analytics and visualization data for the frontend.
"""

from flask import Blueprint, jsonify
from datetime import datetime, timedelta
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Log, Alert, SoarAction

# Use db.func instead of importing sqlalchemy.func directly
func = db.func

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/v1')


@dashboard_bp.route('/dashboard/stats', methods=['GET'])
def dashboard_stats():
    """
    Get aggregated statistics for the dashboard.
    
    Returns:
        200 OK with stats object:
        {
            "total_logs": int,
            "total_alerts": int,
            "logs_by_level": {level: count, ...},
            "alerts_by_severity": {severity: count, ...},
            "alerts_by_status": {status: count, ...},
            "logs_by_host": {host: count, ...}
        }
    """
    try:
        # Total counts
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
        
        # Alerts by status
        alerts_by_status = db.session.query(
            Alert.status,
            func.count(Alert.id).label('count')
        ).group_by(Alert.status).all()
        
        alerts_by_status_dict = {status: count for status, count in alerts_by_status}
        
        # Logs by host (top 10)
        logs_by_host = db.session.query(
            Log.host,
            func.count(Log.id).label('count')
        ).group_by(Log.host).order_by(func.count(Log.id).desc()).limit(10).all()
        
        logs_by_host_dict = {host: count for host, count in logs_by_host}
        
        # SOAR stats
        total_soar_actions = db.session.query(func.count(SoarAction.id)).scalar() or 0
        auto_resolved = db.session.query(func.count(Alert.id)).filter(
            Alert.status == 'Resolved'
        ).scalar() or 0
        active_blocks = db.session.query(func.count(SoarAction.id)).filter(
            SoarAction.action_type == 'ip_block',
            SoarAction.status == 'completed'
        ).scalar() or 0
        
        # SOAR actions by type
        soar_by_type = db.session.query(
            SoarAction.action_type,
            func.count(SoarAction.id).label('count')
        ).group_by(SoarAction.action_type).all()
        soar_by_type_dict = {atype: count for atype, count in soar_by_type}
        
        return jsonify({
            "status": "success",
            "data": {
                "total_logs": total_logs,
                "total_alerts": total_alerts,
                "logs_by_level": logs_by_level_dict,
                "alerts_by_severity": alerts_by_severity_dict,
                "alerts_by_status": alerts_by_status_dict,
                "logs_by_host": logs_by_host_dict,
                "total_soar_actions": total_soar_actions,
                "auto_resolved": auto_resolved,
                "active_blocks": active_blocks,
                "soar_actions_by_type": soar_by_type_dict,
                "timestamp": datetime.utcnow().isoformat()
            }
        }), 200
    
    except Exception as e:
        logger.error(f"dashboard_stats error: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve stats"}), 500


@dashboard_bp.route('/dashboard/recent', methods=['GET'])
def dashboard_recent():
    """
    Get recent logs and alerts for dashboard display.
    
    Returns:
        200 OK with recent events:
        {
            "recent_logs": [{log_object}, ...],
            "recent_alerts": [{alert_object}, ...]
        }
    """
    try:
        recent_logs = Log.query.order_by(Log.created_at.desc()).limit(20).all()
        recent_alerts = Alert.query.order_by(Alert.created_at.desc()).limit(20).all()
        recent_soar_actions = SoarAction.query.order_by(SoarAction.created_at.desc()).limit(20).all()
        
        return jsonify({
            "status": "success",
            "data": {
                "recent_logs": [log.to_dict() for log in recent_logs],
                "recent_alerts": [alert.to_dict() for alert in recent_alerts],
                "recent_soar_actions": [action.to_dict() for action in recent_soar_actions],
                "timestamp": datetime.utcnow().isoformat()
            }
        }), 200
    
    except Exception as e:
        logger.error(f"dashboard_recent error: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve recent events"}), 500


@dashboard_bp.route('/dashboard/timeline', methods=['GET'])
def dashboard_timeline():
    """
    Get time-series data for dashboard charts.
    Returns logs/alerts grouped by hour for the last 24 hours.
    
    Returns:
        200 OK with timeline data
    """
    try:
        # Last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        # Logs by hour
        logs_timeline = db.session.query(
            func.date_trunc('hour', Log.created_at).label('hour'),
            func.count(Log.id).label('count')
        ).filter(Log.created_at >= cutoff).group_by(
            func.date_trunc('hour', Log.created_at)
        ).order_by('hour').all()
        
        # Alerts by hour
        alerts_timeline = db.session.query(
            func.date_trunc('hour', Alert.created_at).label('hour'),
            func.count(Alert.id).label('count')
        ).filter(Alert.created_at >= cutoff).group_by(
            func.date_trunc('hour', Alert.created_at)
        ).order_by('hour').all()
        
        return jsonify({
            "status": "success",
            "data": {
                "logs_timeline": [
                    {"timestamp": hour.isoformat() if hour else None, "count": count}
                    for hour, count in logs_timeline
                ],
                "alerts_timeline": [
                    {"timestamp": hour.isoformat() if hour else None, "count": count}
                    for hour, count in alerts_timeline
                ]
            }
        }), 200
    
    except Exception as e:
        logger.error(f"dashboard_timeline error: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve timeline"}), 500
