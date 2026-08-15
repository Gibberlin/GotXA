#!/usr/bin/env python3
"""
Audit logging system for immutable event tracking.
"""

from flask import g, request
from app.models import AuditEvent, db
from datetime import datetime

class AuditLogger:
    """Centralized audit logging."""
    
    @staticmethod
    def log(action, resource_type, resource_id, status='success', 
            change_before=None, change_after=None, reason=None):
        """
        Log an audit event.
        
        Args:
            action: e.g., 'alert.assigned', 'incident.created', 'setting.changed'
            resource_type: e.g., 'alert', 'incident', 'playbook_execution'
            resource_id: Unique ID of the resource
            status: 'success', 'failure', 'denied'
            change_before: Previous state
            change_after: New state
            reason: Why the action was taken
        """
        
        actor_id = g.auth_context.user_id if hasattr(g, 'auth_context') else None
        correlation_id = g.auth_context.correlation_id if hasattr(g, 'auth_context') else None
        
        event = AuditEvent(
            correlation_id=correlation_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            change_before=change_before,
            change_after=change_after,
            reason=reason,
            ip_address=request.remote_addr if request else None,
            user_agent=request.user_agent.string if request and request.user_agent else None
        )
        
        db.session.add(event)
        db.session.commit()
        
        return event
    
    @staticmethod
    def log_alert_action(alert, action, reason=None):
        """Log alert-related action."""
        AuditLogger.log(
            action=f'alert.{action}',
            resource_type='alert',
            resource_id=alert.id,
            change_after={'status': alert.status, 'assignee_id': alert.assignee_id},
            reason=reason
        )
    
    @staticmethod
    def log_incident_action(incident, action, reason=None, change_before=None, change_after=None):
        """Log incident-related action."""
        AuditLogger.log(
            action=f'incident.{action}',
            resource_type='incident',
            resource_id=incident.id,
            change_before=change_before,
            change_after=change_after,
            reason=reason
        )
    
    @staticmethod
    def log_playbook_execution(execution, action, reason=None):
        """Log playbook execution."""
        AuditLogger.log(
            action=f'playbook.{action}',
            resource_type='playbook_execution',
            resource_id=execution.id,
            change_after={'status': execution.status, 'mode': execution.mode},
            reason=reason
        )
    
    @staticmethod
    def log_setting_change(section, key, old_value, new_value, reason=None):
        """Log settings change."""
        # High-risk settings require explicit approval
        high_risk_settings = [
            'retention',
            'evidence_deletion',
            'rule_disable',
            'data_source_disable',
            'firewall_response',
            'ot_playbook',
            'privilege_changes'
        ]
        
        is_high_risk = any(setting in f'{section}.{key}' for setting in high_risk_settings)
        
        AuditLogger.log(
            action=f'setting.changed',
            resource_type='setting',
            resource_id=f'{section}.{key}',
            change_before={'value': old_value},
            change_after={'value': new_value},
            reason=reason
        )
        
        return is_high_risk
