#!/usr/bin/env python3
"""
GOTXA SIEM/SOAR REST API Blueprint - All endpoints.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from sqlalchemy import desc, and_, or_
import uuid

from app.models import (
    db, User, Team, Alert, Incident, Task, Evidence, PlaybookExecution,
    AuditEvent, Setting, SettingChange, Report
)
from app.auth import (
    authenticate, require_permission, error_response, success_response, list_response, AuthContext
)
from app.audit import AuditLogger

api = Blueprint('api', __name__, url_prefix='/api')

# ============================================================================
# 1. CORE READ APIs
# ============================================================================

@api.route('/overview', methods=['GET'])
@authenticate
def get_overview():
    """Get KPI cards, charts, priority queue, source health, and update time."""
    try:
        # KPI metrics
        total_alerts = db.session.query(Alert).filter_by(status='open').count()
        critical_alerts = db.session.query(Alert).filter(
            Alert.status == 'open',
            Alert.severity == 'critical'
        ).count()
        
        open_incidents = db.session.query(Incident).filter(
            Incident.status.in_(['open', 'investigating', 'contained'])
        ).count()
        
        # Recent alerts
        recent_alerts = db.session.query(Alert).filter_by(status='open').order_by(
            desc(Alert.detected_at)
        ).limit(10).all()
        
        # Source health
        sources = db.session.query(Alert.source, db.func.count(Alert.id)).group_by(
            Alert.source
        ).all()
        
        source_health = [{
            'source': source[0],
            'alert_count': source[1],
            'status': 'healthy' if source[1] < 100 else 'warning' if source[1] < 500 else 'critical'
        } for source in sources]
        
        return success_response({
            'kpis': {
                'total_open_alerts': total_alerts,
                'critical_alerts': critical_alerts,
                'open_incidents': open_incidents,
                'assigned_to_me': db.session.query(Alert).filter_by(
                    assignee_id=g.user.id,
                    status='open'
                ).count()
            },
            'recent_alerts': [{
                'id': a.id,
                'alert_id': a.alert_id,
                'title': a.title,
                'severity': a.severity,
                'source': a.source,
                'detected_at': a.detected_at.isoformat()
            } for a in recent_alerts],
            'source_health': source_health,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/dashboard-data', methods=['GET'])
@authenticate
def get_dashboard_data():
    """Legacy dashboard endpoint for backward compatibility."""
    try:
        total_logs = db.session.query(Alert).count()
        total_alerts = db.session.query(Alert).filter_by(status='open').count()
        
        return success_response({
            'total_logs': total_logs,
            'total_alerts': total_alerts,
            'critical_alerts': db.session.query(Alert).filter(
                Alert.severity == 'critical',
                Alert.status == 'open'
            ).count(),
            'active_hosts': db.session.query(Alert.source).distinct().count()
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/raw-stream', methods=['GET'])
@authenticate
def get_raw_stream():
    """Stream raw logs with cursor-based pagination."""
    try:
        limit = min(int(request.args.get('limit', 50)), 250)  # Max 250
        cursor = request.args.get('cursor')
        
        query = db.session.query(Alert).order_by(desc(Alert.created_at))
        
        if cursor:
            # Find the alert by cursor and get newer ones
            cursor_alert = db.session.query(Alert).filter_by(id=cursor).first()
            if cursor_alert:
                query = query.filter(Alert.created_at < cursor_alert.created_at)
        
        items = query.limit(limit + 1).all()
        
        next_cursor = None
        if len(items) > limit:
            next_cursor = items[-2].id
            items = items[:-1]
        
        return success_response({
            'items': [{
                'id': a.id,
                'timestamp': a.timestamp.isoformat() if a.timestamp else None,
                'level': a.severity.upper(),
                'host': a.source,
                'message': a.title,
                'raw_event': a.raw_event
            } for a in items],
            'next_cursor': next_cursor
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/alerts', methods=['GET'])
@authenticate
def list_alerts():
    """List alerts with filtering and pagination."""
    try:
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 25)), 100)
        severity = request.args.get('severity')
        status = request.args.get('status')
        assignee = request.args.get('assignee')
        sort = request.args.get('sort', 'detected_at')
        order = request.args.get('order', 'desc')
        
        query = db.session.query(Alert)
        
        # Filter by user's team if not admin
        if g.auth_context.role != 'admin' and g.auth_context.team_id:
            query = query.filter_by(team_id=g.auth_context.team_id)
        
        if severity:
            query = query.filter_by(severity=severity)
        if status:
            query = query.filter_by(status=status)
        if assignee:
            query = query.filter_by(assignee_id=assignee)
        
        total = query.count()
        
        if order == 'asc':
            query = query.order_by(getattr(Alert, sort).asc())
        else:
            query = query.order_by(getattr(Alert, sort).desc())
        
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return success_response(list_response([{
            'id': a.id,
            'alert_id': a.alert_id,
            'title': a.title,
            'severity': a.severity,
            'status': a.status,
            'source': a.source,
            'assignee_id': a.assignee_id,
            'assignee_name': a.assignee.username if a.assignee else None,
            'detected_at': a.detected_at.isoformat(),
            'created_at': a.created_at.isoformat()
        } for a in items], total, page, page_size))
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/alerts/<alert_id>', methods=['GET'])
@authenticate
def get_alert_detail(alert_id):
    """Get full alert details with investigation context."""
    try:
        alert = db.session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            return error_response('NotFound', 'Alert not found', 404)
        
        if not g.auth_context.can_access_alert(alert):
            return error_response('Forbidden', 'Cannot access this alert', 403)
        
        # Get related alerts
        related_alerts = db.session.query(Alert).filter(
            Alert.source == alert.source,
            Alert.id != alert.id,
            Alert.created_at > alert.created_at - timedelta(hours=24)
        ).limit(10).all()
        
        return success_response({
            'id': alert.id,
            'alert_id': alert.alert_id,
            'title': alert.title,
            'severity': alert.severity,
            'status': alert.status,
            'source': alert.source,
            'rule_id': alert.rule_id,
            'assignee_id': alert.assignee_id,
            'assignee_name': alert.assignee.username if alert.assignee else None,
            'is_suppressed': alert.is_suppressed,
            'suppression_reason': alert.suppression_reason if alert.is_suppressed else None,
            'raw_event': alert.raw_event,
            'normalized_event': alert.normalized_event,
            'entities': alert.entities,
            'mitre_tactics': alert.mitre_tactics,
            'incident_id': alert.incident_id,
            'detected_at': alert.detected_at.isoformat(),
            'created_at': alert.created_at.isoformat(),
            'related_alerts': [{
                'id': a.id,
                'alert_id': a.alert_id,
                'title': a.title,
                'created_at': a.created_at.isoformat()
            } for a in related_alerts]
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/alerts/<alert_id>/investigation', methods=['GET'])
@authenticate
def get_alert_investigation(alert_id):
    """Get full investigation context for an alert."""
    try:
        alert = db.session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            return error_response('NotFound', 'Alert not found', 404)
        
        if not g.auth_context.can_access_alert(alert):
            return error_response('Forbidden', 'Cannot access this alert', 403)
        
        # Get related evidence, incidents, and audit trail
        related_incidents = db.session.query(Incident).filter(
            Incident.alerts.any(Alert.id == alert.id)
        ).all()
        
        audit_trail = db.session.query(AuditEvent).filter(
            AuditEvent.resource_id == alert.id
        ).order_by(desc(AuditEvent.created_at)).all()
        
        return success_response({
            'alert': {
                'id': alert.id,
                'title': alert.title,
                'severity': alert.severity,
                'status': alert.status,
                'source': alert.source,
                'detected_at': alert.detected_at.isoformat()
            },
            'entities': alert.entities or [],
            'mitre_tactics': alert.mitre_tactics or [],
            'timeline': [{
                'timestamp': a.created_at.isoformat(),
                'action': a.action,
                'actor': a.actor.username if a.actor else 'system',
                'change': {
                    'before': a.change_before,
                    'after': a.change_after
                }
            } for a in audit_trail],
            'related_incidents': [{
                'id': i.id,
                'incident_id': i.incident_id,
                'title': i.title,
                'status': i.status
            } for i in related_incidents]
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/incidents', methods=['GET'])
@authenticate
def list_incidents():
    """List incidents with filtering and pagination."""
    try:
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 25)), 100)
        status = request.args.get('status')
        priority = request.args.get('priority')
        owner = request.args.get('owner')
        
        query = db.session.query(Incident)
        
        # Filter by user's team if not admin
        if g.auth_context.role != 'admin':
            query = query.filter(
                or_(
                    Incident.team_id == g.auth_context.team_id,
                    Incident.owner_id == g.user.id
                )
            )
        
        if status:
            query = query.filter_by(status=status)
        if priority:
            query = query.filter_by(priority=priority)
        if owner:
            query = query.filter_by(owner_id=owner)
        
        total = query.count()
        items = query.order_by(desc(Incident.created_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return success_response(list_response([{
            'id': i.id,
            'incident_id': i.incident_id,
            'title': i.title,
            'status': i.status,
            'severity': i.severity,
            'priority': i.priority,
            'owner_id': i.owner_id,
            'owner_name': i.owner.username if i.owner else None,
            'alert_count': len(i.alerts),
            'created_at': i.created_at.isoformat()
        } for i in items], total, page, page_size))
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/incidents/<incident_id>', methods=['GET'])
@authenticate
def get_incident_detail(incident_id):
    """Get full incident details."""
    try:
        incident = db.session.query(Incident).filter_by(id=incident_id).first()
        if not incident:
            return error_response('NotFound', 'Incident not found', 404)
        
        if not g.auth_context.can_access_incident(incident):
            return error_response('Forbidden', 'Cannot access this incident', 403)
        
        return success_response({
            'id': incident.id,
            'incident_id': incident.incident_id,
            'title': incident.title,
            'description': incident.description,
            'status': incident.status,
            'severity': incident.severity,
            'priority': incident.priority,
            'owner_id': incident.owner_id,
            'owner_name': incident.owner.username if incident.owner else None,
            'team_id': incident.team_id,
            'root_cause': incident.root_cause,
            'affected_assets': incident.affected_assets or [],
            'response_actions': incident.response_actions or [],
            'mitre_tactics': incident.mitre_tactics or [],
            'resolution_notes': incident.resolution_notes,
            'closure_reason': incident.closure_reason,
            'lessons_learned': incident.lessons_learned,
            'alert_count': len(incident.alerts),
            'task_count': len(incident.tasks),
            'evidence_count': len(incident.evidence),
            'detected_at': incident.detected_at.isoformat(),
            'created_at': incident.created_at.isoformat()
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

# ... (continuing with more endpoints in next part)
