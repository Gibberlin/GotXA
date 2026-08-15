#!/usr/bin/env python3
"""
GOTXA SIEM/SOAR REST API - Continuation (Actions, SOAR, Settings)
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from sqlalchemy import desc
import uuid

from app.models import (
    db, Alert, Incident, Task, PlaybookExecution, AuditEvent, Setting, SettingChange, Report, User
)
from app.auth import (
    authenticate, require_permission, error_response, success_response, list_response, AuthContext
)
from app.audit import AuditLogger

api = Blueprint('api_actions', __name__, url_prefix='/api')

# ============================================================================
# 2. ALERT ACTIONS
# ============================================================================

@api.route('/alerts/bulk-assign', methods=['POST'])
@authenticate
@require_permission('alerts.assign')
def bulk_assign_alerts():
    """Assign multiple alerts to a user/team."""
    try:
        data = request.get_json()
        alert_ids = data.get('alert_ids', [])
        assignee_id = data.get('assignee_id')
        team_id = data.get('team_id')
        reason = data.get('reason')
        
        if not alert_ids or (not assignee_id and not team_id):
            return error_response('BadRequest', 'Missing required fields', 400)
        
        alerts = db.session.query(Alert).filter(Alert.id.in_(alert_ids)).all()
        
        for alert in alerts:
            if assignee_id:
                alert.assignee_id = assignee_id
            if team_id:
                alert.team_id = team_id
            
            AuditLogger.log_alert_action(alert, 'assigned', reason)
        
        db.session.commit()
        
        return success_response({
            'updated_count': len(alerts)
        }, 'Alerts assigned successfully', 200)
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/alerts/<alert_id>/suppress', methods=['POST'])
@authenticate
@require_permission('alerts.suppress')
def suppress_alert(alert_id):
    """Suppress an alert."""
    try:
        data = request.get_json()
        alert = db.session.query(Alert).filter_by(id=alert_id).first()
        
        if not alert:
            return error_response('NotFound', 'Alert not found', 404)
        
        alert.is_suppressed = True
        alert.suppression_reason = data.get('reason')
        alert.suppression_scope = data.get('scope', 'alert')  # alert, rule, entity
        
        if data.get('expires_at'):
            alert.suppression_expires_at = datetime.fromisoformat(data['expires_at'])
        
        AuditLogger.log_alert_action(alert, 'suppressed', data.get('reason'))
        db.session.commit()
        
        return success_response(None, 'Alert suppressed', 200)
    except Exception as e:
        return error_response('InternalError', str(e), 500)

# ============================================================================
# 3. INCIDENT WORKFLOW
# ============================================================================

@api.route('/incidents', methods=['POST'])
@authenticate
@require_permission('incidents.create')
def create_incident():
    """Create a new incident (optionally from alerts)."""
    try:
        data = request.get_json()
        
        incident = Incident(
            incident_id=f'INC-{uuid.uuid4().hex[:8].upper()}',
            title=data.get('title'),
            description=data.get('description'),
            severity=data.get('severity', 'medium'),
            priority=data.get('priority', 'medium'),
            owner_id=data.get('owner_id') or g.user.id,
            team_id=data.get('team_id') or g.auth_context.team_id,
            detected_at=datetime.utcnow()
        )
        
        # Link alerts if provided
        alert_ids = data.get('alert_ids', [])
        if alert_ids:
            alerts = db.session.query(Alert).filter(Alert.id.in_(alert_ids)).all()
            for alert in alerts:
                alert.incident_id = incident.id
                alert.status = 'investigating'
        
        db.session.add(incident)
        db.session.commit()
        
        AuditLogger.log_incident_action(incident, 'created', data.get('reason'))
        
        return success_response({
            'id': incident.id,
            'incident_id': incident.incident_id,
            'title': incident.title
        }, 'Incident created', 201)
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/incidents/<incident_id>', methods=['PATCH'])
@authenticate
@require_permission('incidents.edit')
def update_incident(incident_id):
    """Update incident (status, assignment, analysis, closure)."""
    try:
        data = request.get_json()
        incident = db.session.query(Incident).filter_by(id=incident_id).first()
        
        if not incident:
            return error_response('NotFound', 'Incident not found', 404)
        
        if not g.auth_context.can_access_incident(incident):
            return error_response('Forbidden', 'Cannot modify this incident', 403)
        
        # Validate state transitions
        new_status = data.get('status')
        if new_status:
            valid_transitions = {
                'open': ['investigating', 'dismissed'],
                'investigating': ['contained', 'resolved', 'open'],
                'contained': ['resolved', 'investigating'],
                'resolved': ['closed'],
                'closed': []
            }
            
            if new_status not in valid_transitions.get(incident.status, []):
                return error_response(
                    'InvalidStateTransition',
                    f'Cannot transition from {incident.status} to {new_status}',
                    409
                )
            
            incident.status = new_status
            
            # Update timestamps
            if new_status == 'contained':
                incident.contained_at = datetime.utcnow()
            elif new_status == 'resolved':
                incident.resolved_at = datetime.utcnow()
            elif new_status == 'closed':
                incident.closed_at = datetime.utcnow()
                # Require closure fields
                if not data.get('closure_reason'):
                    return error_response('BadRequest', 'Closure reason required', 400)
                incident.closure_reason = data.get('closure_reason')
                incident.resolution_notes = data.get('resolution_notes')
                incident.lessons_learned = data.get('lessons_learned')
        
        # Update other fields
        if 'owner_id' in data:
            incident.owner_id = data['owner_id']
        if 'priority' in data:
            incident.priority = data['priority']
        if 'root_cause' in data:
            incident.root_cause = data['root_cause']
        if 'affected_assets' in data:
            incident.affected_assets = data['affected_assets']
        if 'response_actions' in data:
            incident.response_actions = data['response_actions']
        if 'mitre_tactics' in data:
            incident.mitre_tactics = data['mitre_tactics']
        
        db.session.commit()
        
        AuditLogger.log_incident_action(
            incident, 'updated',
            change_after={'status': new_status},
            reason=data.get('reason')
        )
        
        return success_response(None, 'Incident updated', 200)
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/incidents/<incident_id>/tasks', methods=['POST'])
@authenticate
@require_permission('incidents.edit')
def create_task(incident_id):
    """Create a task for an incident."""
    try:
        data = request.get_json()
        incident = db.session.query(Incident).filter_by(id=incident_id).first()
        
        if not incident:
            return error_response('NotFound', 'Incident not found', 404)
        
        task = Task(
            incident_id=incident_id,
            title=data.get('title'),
            description=data.get('description'),
            assigned_to_id=data.get('assigned_to_id'),
            due_at=datetime.fromisoformat(data['due_at']) if data.get('due_at') else None
        )
        
        db.session.add(task)
        db.session.commit()
        
        return success_response({'id': task.id, 'title': task.title}, 'Task created', 201)
    except Exception as e:
        return error_response('InternalError', str(e), 500)

# ============================================================================
# 4. SOAR AND RESPONSE
# ============================================================================

@api.route('/playbooks/<playbook_id>/executions', methods=['POST'])
@authenticate
@require_permission('playbooks.execute')
def execute_playbook(playbook_id):
    """Execute a playbook (with approval flow for high-risk actions)."""
    try:
        data = request.get_json()
        
        # Check if high-risk (requires approval)
        high_risk_playbooks = ['isolation', 'firewall_block', 'user_disable', 'ransomware']
        requires_approval = any(hri in playbook_id.lower() for hri in high_risk_playbooks)
        
        execution = PlaybookExecution(
            playbook_id=playbook_id,
            execution_id=f'EXE-{uuid.uuid4().hex[:8].upper()}',
            mode=data.get('mode', 'dry_run') if requires_approval else data.get('mode', 'live'),
            inputs=data.get('inputs', {}),
            triggered_by_id=g.user.id,
            reason=data.get('reason'),
            change_ticket=data.get('change_ticket'),
            status='pending' if requires_approval else 'running'
        )
        
        db.session.add(execution)
        db.session.commit()
        
        AuditLogger.log_playbook_execution(execution, 'triggered', data.get('reason'))
        
        return success_response({
            'execution_id': execution.execution_id,
            'status': execution.status,
            'requires_approval': requires_approval
        }, 'Playbook execution initiated', 202)
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/playbook-executions/<execution_id>/approve', methods=['POST'])
@authenticate
@require_permission('playbooks.approve')
def approve_playbook_execution(execution_id):
    """Approve a playbook execution (for high-risk actions)."""
    try:
        execution = db.session.query(PlaybookExecution).filter_by(execution_id=execution_id).first()
        
        if not execution:
            return error_response('NotFound', 'Execution not found', 404)
        
        if execution.status != 'pending':
            return error_response('InvalidState', f'Cannot approve execution in {execution.status} state', 409)
        
        execution.status = 'running'
        execution.approved_by_id = g.user.id
        
        db.session.commit()
        
        AuditLogger.log_playbook_execution(execution, 'approved')
        
        return success_response({'status': 'approved'}, 'Execution approved', 200)
    except Exception as e:
        return error_response('InternalError', str(e), 500)

# ============================================================================
# 8. HEALTH AND CAPABILITIES
# ============================================================================

@api.route('/capabilities', methods=['GET'])
@authenticate
def get_capabilities():
    """Return user's available capabilities based on role."""
    return success_response({
        'actions': {
            'alerts.bulk_assign': g.auth_context.has_permission('alerts.assign'),
            'alerts.suppress': g.auth_context.has_permission('alerts.suppress'),
            'incidents.create': g.auth_context.has_permission('incidents.create'),
            'incidents.edit': g.auth_context.has_permission('incidents.edit'),
            'incidents.close': g.auth_context.has_permission('incidents.close'),
            'playbooks.execute': g.auth_context.has_permission('playbooks.execute'),
            'playbooks.approve': g.auth_context.has_permission('playbooks.approve'),
            'containment.execute': g.auth_context.has_permission('containment.execute'),
            'settings.write': g.auth_context.has_permission('settings.write'),
        },
        'version': '1.0',
        'user_role': g.auth_context.role
    })

@api.route('/audit-events', methods=['GET'])
@authenticate
@require_permission('audit.view')
def list_audit_events():
    """List audit events."""
    try:
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 25)), 100)
        
        query = db.session.query(AuditEvent).order_by(desc(AuditEvent.created_at))
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return success_response(list_response([{
            'id': e.id,
            'correlation_id': e.correlation_id,
            'actor': e.actor.username if e.actor else 'system',
            'action': e.action,
            'resource_type': e.resource_type,
            'resource_id': e.resource_id,
            'status': e.status,
            'created_at': e.created_at.isoformat()
        } for e in items], total, page, page_size))
    except Exception as e:
        return error_response('InternalError', str(e), 500)
