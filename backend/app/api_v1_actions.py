#!/usr/bin/env python3
"""
GOTXA SIEM/SOAR REST API - Action Endpoints
SOAR playbook execution, incident lifecycle, settings management
"""

from flask import Blueprint, request, g
from datetime import datetime
from sqlalchemy import desc
import uuid

from app.models import (
    db, Alert, Incident, Task, Evidence, PlaybookExecution, AuditEvent, Setting, SettingChange
)
from app.auth import authenticate, require_permission, error_response, success_response
from app.audit import AuditLogger

api = Blueprint('api_actions', __name__, url_prefix='/api')
audit = AuditLogger()

# ============================================================================
# 2. ALERT ACTIONS
# ============================================================================

@authenticate
@require_permission('alerts.assign')
def bulk_assign_alerts():
    """Bulk assign alerts to users."""
    try:
        data = request.get_json()
        alert_ids = data.get('alert_ids', [])
        assignee_id = data.get('assignee_id')
        reason = data.get('reason', 'Bulk assignment')
        
        if not alert_ids or not assignee_id:
            return error_response('BadRequest', 'alert_ids and assignee_id required', 400)
        
        alerts = db.session.query(Alert).filter(Alert.id.in_(alert_ids)).all()
        
        for alert in alerts:
            old_assignee = alert.assignee_id
            alert.assignee_id = assignee_id
            
            audit.log(
                actor=g.user,
                action='alert.reassigned',
                resource_type='Alert',
                resource_id=alert.id,
                change_before={'assignee_id': old_assignee},
                change_after={'assignee_id': assignee_id},
                reason=reason
            )
        
        db.session.commit()
        
        return success_response({
            'assigned_count': len(alerts),
            'timestamp': datetime.utcnow().isoformat()
        }, 'Alerts assigned', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@authenticate
@require_permission('alerts.suppress')
def suppress_alert(alert_id):
    """Suppress an alert."""
    try:
        data = request.get_json()
        reason = data.get('reason', 'Manual suppression')
        scope = data.get('scope', 'single')  # single, rule, source
        duration_hours = data.get('duration_hours', 24)
        
        alert = db.session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            return error_response('NotFound', 'Alert not found', 404)
        
        alert.is_suppressed = True
        alert.suppression_reason = reason
        alert.suppression_scope = scope
        alert.suppression_expires_at = datetime.utcnow() + __import__('datetime').timedelta(hours=duration_hours)
        
        audit.log(
            actor=g.user,
            action='alert.suppressed',
            resource_type='Alert',
            resource_id=alert.id,
            reason=reason
        )
        
        db.session.commit()
        
        return success_response({'id': alert.id, 'suppressed': True}, 'Alert suppressed', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/alerts/<alert_id>/status', methods=['PUT'])
@authenticate
def update_alert_status(alert_id):
    """Update alert status."""
    try:
        data = request.get_json()
        new_status = data.get('status')  # open, investigating, resolved, closed
        reason = data.get('reason', '')
        
        if new_status not in ['open', 'investigating', 'resolved', 'closed']:
            return error_response('BadRequest', 'Invalid status', 400)
        
        alert = db.session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            return error_response('NotFound', 'Alert not found', 404)
        
        old_status = alert.status
        alert.status = new_status
        
        audit.log(
            actor=g.user,
            action='alert.status_changed',
            resource_type='Alert',
            resource_id=alert.id,
            change_before={'status': old_status},
            change_after={'status': new_status},
            reason=reason
        )
        
        db.session.commit()
        
        return success_response({'id': alert.id, 'status': new_status}, 'Alert status updated', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

# ============================================================================
# 3. INCIDENT ACTIONS
# ============================================================================

@authenticate
@require_permission('incidents.create')
def create_incident():
    """Create a new incident."""
    try:
        data = request.get_json()
        
        incident = Incident(
            incident_id=f"INC-{uuid.uuid4().hex[:8].upper()}",
            title=data.get('title'),
            description=data.get('description', ''),
            severity=data.get('severity', 'medium'),
            priority=data.get('priority', 'medium'),
            status='open',
            owner_id=g.user.id,
            team_id=g.user.team_id,
            detected_at=datetime.utcnow(),
            affected_assets=data.get('affected_assets', []),
            mitre_tactics=data.get('mitre_tactics', [])
        )
        
        db.session.add(incident)
        db.session.flush()
        
        audit.log(
            actor=g.user,
            action='incident.created',
            resource_type='Incident',
            resource_id=incident.id,
            reason=data.get('reason', '')
        )
        
        db.session.commit()
        
        return success_response({
            'id': incident.id,
            'incident_id': incident.incident_id,
            'title': incident.title,
            'status': incident.status
        }, 'Incident created', 201)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/incidents/<incident_id>/status', methods=['PUT'])
@authenticate
@require_permission('incidents.edit')
def update_incident_status(incident_id):
    """Update incident status (lifecycle management)."""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        # Valid transitions
        valid_transitions = {
            'open': ['investigating', 'closed'],
            'investigating': ['contained', 'closed'],
            'contained': ['resolved', 'closed'],
            'resolved': ['closed'],
            'closed': []
        }
        
        incident = db.session.query(Incident).filter_by(id=incident_id).first()
        if not incident:
            return error_response('NotFound', 'Incident not found', 404)
        
        if new_status not in valid_transitions.get(incident.status, []):
            return error_response(
                'InvalidStateTransition',
                f'Cannot transition from {incident.status} to {new_status}',
                409
            )
        
        old_status = incident.status
        incident.status = new_status
        
        if new_status == 'contained':
            incident.contained_at = datetime.utcnow()
        elif new_status == 'resolved':
            incident.resolved_at = datetime.utcnow()
        elif new_status == 'closed':
            incident.closed_at = datetime.utcnow()
            incident.closure_reason = data.get('closure_reason', '')
            incident.lessons_learned = data.get('lessons_learned', '')
        
        audit.log(
            actor=g.user,
            action='incident.status_changed',
            resource_type='Incident',
            resource_id=incident.id,
            change_before={'status': old_status},
            change_after={'status': new_status},
            reason=data.get('reason', '')
        )
        
        db.session.commit()
        
        return success_response({
            'id': incident.id,
            'status': new_status,
            'timestamp': datetime.utcnow().isoformat()
        }, 'Incident status updated', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/incidents/<incident_id>/assign', methods=['POST'])
@authenticate
@require_permission('incidents.edit')
def assign_incident(incident_id):
    """Assign incident to a user."""
    try:
        data = request.get_json()
        owner_id = data.get('owner_id')
        
        incident = db.session.query(Incident).filter_by(id=incident_id).first()
        if not incident:
            return error_response('NotFound', 'Incident not found', 404)
        
        old_owner = incident.owner_id
        incident.owner_id = owner_id
        
        audit.log(
            actor=g.user,
            action='incident.reassigned',
            resource_type='Incident',
            resource_id=incident.id,
            change_before={'owner_id': old_owner},
            change_after={'owner_id': owner_id}
        )
        
        db.session.commit()
        
        return success_response({'id': incident.id, 'owner_id': owner_id}, 'Incident assigned', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/incidents/<incident_id>/link-alert', methods=['POST'])
@authenticate
def link_alert_to_incident(incident_id):
    """Link an alert to an incident."""
    try:
        data = request.get_json()
        alert_id = data.get('alert_id')
        
        incident = db.session.query(Incident).filter_by(id=incident_id).first()
        if not incident:
            return error_response('NotFound', 'Incident not found', 404)
        
        alert = db.session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            return error_response('NotFound', 'Alert not found', 404)
        
        alert.incident_id = incident.id
        
        audit.log(
            actor=g.user,
            action='alert.linked_to_incident',
            resource_type='Alert',
            resource_id=alert.id,
            reason=f'Linked to incident {incident.incident_id}'
        )
        
        db.session.commit()
        
        return success_response({'incident_id': incident.id, 'alert_id': alert.id}, 'Alert linked', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

# ============================================================================
# 4. SOAR PLAYBOOK ACTIONS
# ============================================================================

@api.route('/v1/soar/actions', methods=['GET'])
@authenticate
def list_soar_actions():
    """List available SOAR playbooks/actions."""
    return success_response({
        'actions': [
            {
                'id': 'containment.isolate_host',
                'name': 'Isolate Compromised Host',
                'description': 'Isolate host from network',
                'category': 'containment',
                'risk_level': 'high',
                'requires_approval': True,
                'estimated_time': '5 minutes'
            },
            {
                'id': 'response.reset_password',
                'name': 'Reset User Credentials',
                'description': 'Force password reset for compromised account',
                'category': 'response',
                'risk_level': 'medium',
                'requires_approval': True,
                'estimated_time': '2 minutes'
            },
            {
                'id': 'investigation.collect_artifacts',
                'name': 'Collect Forensic Artifacts',
                'description': 'Collect logs and artifacts from host',
                'category': 'investigation',
                'risk_level': 'low',
                'requires_approval': False,
                'estimated_time': '10 minutes'
            },
            {
                'id': 'enrichment.get_threat_intel',
                'name': 'Get Threat Intelligence',
                'description': 'Lookup indicators in threat feeds',
                'category': 'enrichment',
                'risk_level': 'low',
                'requires_approval': False,
                'estimated_time': '3 minutes'
            }
        ]
    })

@api.route('/v1/soar/execute', methods=['POST'])
@authenticate
@require_permission('playbooks.execute')
def execute_soar_playbook():
    """Execute a SOAR playbook."""
    try:
        data = request.get_json()
        action_id = data.get('action_id')
        incident_id = data.get('incident_id')
        parameters = data.get('parameters', {})
        reason = data.get('reason', '')
        change_ticket = data.get('change_ticket', '')
        
        execution = PlaybookExecution(
            playbook_id=action_id,
            execution_id=f"EXEC-{uuid.uuid4().hex[:8].upper()}",
            status='pending',
            mode=data.get('mode', 'live'),
            inputs=parameters,
            triggered_by_id=g.user.id,
            reason=reason,
            change_ticket=change_ticket
        )
        
        db.session.add(execution)
        db.session.flush()
        
        audit.log(
            actor=g.user,
            action='playbook.executed',
            resource_type='PlaybookExecution',
            resource_id=execution.id,
            reason=reason
        )
        
        db.session.commit()
        
        return success_response({
            'execution_id': execution.execution_id,
            'status': execution.status,
            'playbook_id': action_id
        }, 'Playbook execution started', 202)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/v1/soar/history', methods=['GET'])
@authenticate
def get_soar_history():
    """Get SOAR playbook execution history."""
    try:
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 25)), 100)
        
        query = db.session.query(PlaybookExecution).order_by(desc(PlaybookExecution.created_at))
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return success_response({
            'items': [{
                'execution_id': e.execution_id,
                'playbook_id': e.playbook_id,
                'status': e.status,
                'triggered_by': e.triggered_by.username if e.triggered_by else None,
                'created_at': e.created_at.isoformat() if e.created_at else None,
                'completed_at': e.completed_at.isoformat() if e.completed_at else None
            } for e in items],
            'total': total,
            'page': page,
            'page_size': page_size
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

# ============================================================================
# 5. SETTINGS & CONFIGURATION
# ============================================================================

@api.route('/settings', methods=['GET'])
@authenticate
@require_permission('settings.read')
def list_settings():
    """List all settings."""
    try:
        section = request.args.get('section')
        
        query = db.session.query(Setting)
        if section:
            query = query.filter_by(section=section)
        
        items = query.all()
        
        return success_response({
            'items': [{
                'section': s.section,
                'key': s.key,
                'value': None if s.is_sensitive else s.value,
                'type': s.value_type
            } for s in items]
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/settings', methods=['PUT'])
@authenticate
@require_permission('settings.write')
def update_settings():
    """Update settings."""
    try:
        data = request.get_json()
        section = data.get('section')
        key = data.get('key')
        new_value = data.get('value')
        reason = data.get('reason', '')
        
        setting = db.session.query(Setting).filter_by(section=section, key=key).first()
        if not setting:
            setting = Setting(section=section, key=key)
            db.session.add(setting)
        
        old_value = setting.value
        setting.value = new_value
        
        change = SettingChange(
            section=section,
            key=key,
            changed_by_id=g.user.id,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            status='applied'
        )
        db.session.add(change)
        
        audit.log(
            actor=g.user,
            action='setting.changed',
            resource_type='Setting',
            resource_id=f"{section}.{key}",
            change_before={'value': old_value},
            change_after={'value': new_value},
            reason=reason
        )
        
        db.session.commit()
        
        return success_response({'section': section, 'key': key}, 'Setting updated', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)
