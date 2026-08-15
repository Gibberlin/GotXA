#!/usr/bin/env python3
"""
RBAC (Role-Based Access Control) and authentication utilities.
"""

from functools import wraps
from flask import request, jsonify, g
from datetime import datetime
import uuid

PERMISSIONS = {
    'admin': {
        'alerts.view': True,
        'alerts.assign': True,
        'alerts.suppress': True,
        'incidents.create': True,
        'incidents.edit': True,
        'incidents.close': True,
        'incidents.assign': True,
        'playbooks.execute': True,
        'playbooks.approve': True,
        'containment.execute': True,
        'containment.approve': True,
        'settings.read': True,
        'settings.write': True,
        'settings.approve': True,
        'reports.generate': True,
        'audit.view': True,
        'users.manage': True,
    },
    'soc_manager': {
        'alerts.view': True,
        'alerts.assign': True,
        'alerts.suppress': True,
        'incidents.create': True,
        'incidents.edit': True,
        'incidents.close': True,
        'incidents.assign': True,
        'playbooks.execute': True,
        'playbooks.approve': False,
        'containment.execute': True,
        'containment.approve': False,
        'settings.read': True,
        'settings.write': False,
        'settings.approve': False,
        'reports.generate': True,
        'audit.view': True,
        'users.manage': False,
    },
    'analyst': {
        'alerts.view': True,
        'alerts.assign': False,
        'alerts.suppress': False,
        'incidents.create': True,
        'incidents.edit': True,
        'incidents.close': False,
        'incidents.assign': False,
        'playbooks.execute': False,
        'playbooks.approve': False,
        'containment.execute': False,
        'containment.approve': False,
        'settings.read': False,
        'settings.write': False,
        'settings.approve': False,
        'reports.generate': False,
        'audit.view': False,
        'users.manage': False,
    }
}

class AuthContext:
    """Represents the authenticated user context."""
    
    def __init__(self, user):
        self.user = user
        self.user_id = user.id if user else None
        self.username = user.username if user else None
        self.role = user.role if user else None
        self.team_id = user.team_id if user else None
        self.correlation_id = str(uuid.uuid4())
    
    def has_permission(self, action):
        """Check if user has permission for an action."""
        if not self.role:
            return False
        perms = PERMISSIONS.get(self.role, {})
        return perms.get(action, False)
    
    def can_access_alert(self, alert):
        """Check if user can access an alert (team-based)."""
        if self.role == 'admin':
            return True
        if self.team_id and alert.team_id == self.team_id:
            return True
        return False
    
    def can_access_incident(self, incident):
        """Check if user can access an incident (team-based)."""
        if self.role == 'admin':
            return True
        if self.team_id and incident.team_id == self.team_id:
            return True
        if self.user_id == incident.owner_id:
            return True
        return False

def authenticate(f):
    """Decorator to check authentication and set g.auth_context."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.models import User, db
        
        user = None
        
        # Check Bearer token
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            # TODO: Validate JWT token
            pass
        
        # Check X-User-ID header (demo)
        if not user:
            user_id = request.headers.get('X-User-ID')
            if user_id:
                user = db.session.get(User, user_id)
        
        # Demo: create admin user if not exists
        if not user:
            user = db.session.query(User).filter_by(username='admin').first()
            if not user:
                user = User(
                    username='admin',
                    email='admin@gotxa.local',
                    password_hash='demo',
                    role='admin'
                )
                db.session.add(user)
                db.session.commit()
        
        if not user:
            return error_response('Unauthorized', 'Invalid or missing credentials', 401)
        
        g.auth_context = AuthContext(user)
        g.user = user
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_permission(permission):
    """Decorator to require a specific permission."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'auth_context'):
                return error_response('Unauthorized', 'Authentication required', 401)
            
            if not g.auth_context.has_permission(permission):
                return error_response('Forbidden', f'Permission denied: {permission}', 403)
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator

def error_response(code, message, status_code=400, details=None):
    """Format a standard error response."""
    return jsonify({
        'error': {
            'code': code,
            'message': message,
            'details': details or {}
        }
    }), status_code

def success_response(data=None, message='Success', status_code=200):
    """Format a standard success response."""
    if isinstance(data, dict) and 'items' in data:
        return jsonify(data), status_code
    
    return jsonify({
        'data': data,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }), status_code

def list_response(items, total, page=1, page_size=25):
    """Format a paginated list response."""
    return {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size
    }
