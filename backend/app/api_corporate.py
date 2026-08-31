"""Corporate Portal API endpoints.

The portal has its own lightweight session tokens so it can be used without
changing the SIEM API's demo authentication behaviour.
"""

from datetime import datetime, timedelta
from functools import wraps
import uuid

from flask import Blueprint, g, jsonify, request

from app.auth import error_response
from app.models import User, db

api = Blueprint('corporate_api', __name__, url_prefix='/api/corporate')

DEMO_PASSWORD = 'SecureP@ssw0rd'
SESSIONS = {}
SYSTEMS = [
    {'id': 'email', 'name': 'Corporate Email', 'status': 'operational', 'message': 'All systems normal'},
    {'id': 'vpn', 'name': 'Remote Access VPN', 'status': 'operational', 'message': 'All regions available'},
    {'id': 'erp', 'name': 'ERP Platform', 'status': 'degraded', 'message': 'Scheduled maintenance window'},
    {'id': 'files', 'name': 'File Storage', 'status': 'operational', 'message': 'All systems normal'},
    {'id': 'hr', 'name': 'HR Services', 'status': 'operational', 'message': 'All systems normal'},
]
ANNOUNCEMENTS = [
    {'id': 'ann-001', 'title': 'VPN maintenance', 'body': 'Brief maintenance is scheduled this weekend.', 'severity': 'info'},
    {'id': 'ann-002', 'title': 'Security awareness reminder', 'body': 'Report suspicious messages using the phishing button.', 'severity': 'medium'},
]
TASKS = [
    {'id': 'task-001', 'title': 'Review quarterly access confirmation', 'status': 'open', 'due_at': None, 'priority': 'high'},
    {'id': 'task-002', 'title': 'Complete security awareness training', 'status': 'in_progress', 'due_at': None, 'priority': 'medium'},
]


def _now():
    return datetime.utcnow().isoformat()


def _user_payload(user):
    return {
        'id': user.id,
        'name': user.username,
        'email': user.email,
        'role': user.role,
        'department': user.team.name if user.team else 'Corporate Operations',
        'last_login': _now(),
        'permissions': ['corporate.dashboard.read', 'corporate.tasks.write'] + (
            ['corporate.admin.read'] if user.role == 'admin' else []
        ),
    }


from app.auth import error_response, create_user_session, revoke_user_session
from app.models import User, UserSession, SecurityEvent, Device, LogSource, db
from app.audit import AuditLogger

def _log_corp_security_event(level, message, details=None):
    """Log an actual security and audit event for Corporate Portal monitoring."""
    try:
        occurred_at = datetime.utcnow()
        host = 'corp-portal'
        
        # Update device tracking
        device = db.session.query(Device).filter_by(hostname=host).first()
        if not device:
            device = Device(
                hostname=host,
                device_type='web-server',
                trust_state='trusted',
                first_seen_at=occurred_at,
                last_seen_at=occurred_at
            )
            db.session.add(device)
        else:
            device.last_seen_at = occurred_at
            
        # Update LogSource
        source = db.session.query(LogSource).filter_by(name=host).first()
        if not source:
            source = LogSource(
                id=str(uuid.uuid4()),
                name=host,
                connector_type='web-application',
                status='healthy',
                last_event_timestamp=occurred_at,
                total_events_ingested=1,
                ingestion_rate=1
            )
            db.session.add(source)
        else:
            source.last_event_timestamp = occurred_at
            source.total_events_ingested = (source.total_events_ingested or 0) + 1
            source.status = 'healthy'

        event = SecurityEvent(
            device_id=device.id if device else None,
            source=host,
            severity=level.lower(),
            message=message,
            occurred_at=occurred_at,
            raw_event=details or {'host': host, 'level': level, 'message': message}
        )
        db.session.add(event)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

def corporate_authenticate(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        token = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
        if not token:
            _log_corp_security_event('WARN', f"Unauthenticated request to {request.path} from {request.remote_addr}")
            return error_response('Unauthorized', 'A valid Corporate Portal session token is required', 401)
            
        session = db.session.query(UserSession).filter_by(token=token, is_active=True).first()
        if not session or session.expires_at <= datetime.utcnow():
            _log_corp_security_event('WARN', f"Expired or invalid session access attempt to {request.path} from {request.remote_addr}")
            return error_response('Unauthorized', 'A valid Corporate Portal session is required', 401)
            
        user = session.user
        if not user or not user.is_active:
            _log_corp_security_event('HIGH', f"Access attempt by deactivated user from {request.remote_addr}")
            return error_response('Unauthorized', 'User account is unavailable', 401)
            
        session.last_accessed_at = datetime.utcnow()
        db.session.commit()
        
        g.corporate_user = user
        g.corporate_session = session
        return handler(*args, **kwargs)
    return wrapped


@api.route('/auth/login', methods=['POST'])
def login():
    body = request.get_json(silent=True) or request.form
    username = (body.get('username') or '').strip()
    password = body.get('password') or ''
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    if not username or not password:
        _log_corp_security_event('WARN', f"Corporate Portal login attempted with missing credentials from {client_ip}")
        return error_response('BadRequest', 'username and password are required', 400)
        
    if username != 'admin' or password != DEMO_PASSWORD:
        _log_corp_security_event('HIGH', f"Failed Corporate Portal login attempt for user '{username}' from {client_ip}", {
            'action': 'auth.login.failed',
            'username': username,
            'ip_address': client_ip,
            'user_agent': request.headers.get('User-Agent')
        })
        return error_response('InvalidCredentials', 'Invalid username or password', 401)

    user = db.session.query(User).filter_by(username=username).first()
    if not user:
        user = User(username='admin', email='admin@gotxa.local', password_hash='demo', role='admin')
        db.session.add(user)
        db.session.commit()

    # Create and record real persistent session in database with audit event
    session = create_user_session(user, duration_hours=8, ip_address=client_ip, user_agent=request.headers.get('User-Agent'))
    
    _log_corp_security_event('INFO', f"Corporate Portal user '{username}' successfully authenticated from {client_ip}", {
        'action': 'auth.login.success',
        'username': username,
        'user_id': user.id,
        'session_id': session.id,
        'ip_address': client_ip
    })
    
    return jsonify({
        'user': _user_payload(user),
        'access_token': session.token,
        'expires_at': session.expires_at.isoformat()
    }), 200


@api.route('/auth/logout', methods=['POST'])
@corporate_authenticate
def logout():
    token = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
    user = g.corporate_user
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    revoke_user_session(token)
    _log_corp_security_event('INFO', f"Corporate Portal user '{user.username}' logged out (Session terminated) from {client_ip}")
    return '', 204



@api.route('/me', methods=['GET'])
@corporate_authenticate
def me():
    return jsonify(_user_payload(g.corporate_user))


@api.route('/dashboard', methods=['GET'])
@corporate_authenticate
def dashboard():
    user = g.corporate_user
    _log_corp_security_event('INFO', f"User '{user.username}' accessed Corporate Portal dashboard")
    activity = [
        {'id': 'act-001', 'type': 'sign_in', 'message': 'Signed in to Corporate Portal', 'created_at': _now()},
        {'id': 'act-002', 'type': 'task', 'message': 'Access review task assigned', 'created_at': _now()},
    ]
    payload = {
        'system_summary': SYSTEMS,
        'my_tasks': TASKS,
        'announcements': [{**item, 'published_at': _now()} for item in ANNOUNCEMENTS],
        'activity': activity,
    }
    if user.role == 'admin':
        payload['admin_summary'] = {
            'kpis': {'active_systems': 5, 'open_service_issues': 1, 'task_completion_rate': 78, 'average_response_minutes': 14},
            'team_workload': [{'team': 'Corporate Operations', 'open': 2, 'in_progress': 1}],
            'access_review_count': 1,
        }
    return jsonify(payload)


@api.route('/systems', methods=['GET'])
@corporate_authenticate
def systems():
    return jsonify({'items': [{**item, 'updated_at': _now()} for item in SYSTEMS]})


@api.route('/tasks', methods=['GET'])
@corporate_authenticate
def tasks():
    status = request.args.get('status')
    items = [task for task in TASKS if not status or task['status'] == status]
    return jsonify({'items': items})


@api.route('/tasks/<task_id>', methods=['PATCH'])
@corporate_authenticate
def update_task(task_id):
    body = request.get_json(silent=True) or {}
    status = body.get('status')
    if status not in {'open', 'in_progress', 'completed'}:
        return error_response('BadRequest', 'status must be open, in_progress, or completed', 400)
    task = next((item for item in TASKS if item['id'] == task_id), None)
    if not task:
        return error_response('NotFound', 'Task not found', 404)
    task['status'] = status
    task['updated_at'] = _now()
    _log_corp_security_event('INFO', f"User '{g.corporate_user.username}' updated corporate task '{task['title']}' to {status}")
    return jsonify(task)


@api.route('/announcements', methods=['GET'])
@corporate_authenticate
def announcements():
    return jsonify({'items': [{**item, 'published_at': _now()} for item in ANNOUNCEMENTS]})


@api.route('/activity', methods=['GET'])
@corporate_authenticate
def activity():
    return jsonify({'items': [{'id': 'act-001', 'type': 'sign_in', 'message': 'Signed in to Corporate Portal', 'created_at': _now()}]})


@api.route('/admin/overview', methods=['GET'])
@corporate_authenticate
def admin_overview():
    if g.corporate_user.role != 'admin':
        _log_corp_security_event('HIGH', f"Unauthorized access attempt to admin overview by user '{g.corporate_user.username}'")
        return error_response('Forbidden', 'Administrator access is required', 403)
    _log_corp_security_event('INFO', f"Admin '{g.corporate_user.username}' accessed administrative operations overview")
    return jsonify({
        'kpis': {'active_systems': 5, 'open_service_issues': 1, 'task_completion_rate': 78, 'average_response_minutes': 14},
        'team_workload': [{'team': 'Corporate Operations', 'open': 2, 'in_progress': 1}],
        'access_review_count': 1,
    })

