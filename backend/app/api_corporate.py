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


def corporate_authenticate(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        token = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
        session = SESSIONS.get(token)
        if not session or session['expires_at'] <= datetime.utcnow():
            return error_response('Unauthorized', 'A valid Corporate Portal session is required', 401)
        user = db.session.get(User, session['user_id'])
        if not user or not user.is_active:
            return error_response('Unauthorized', 'User account is unavailable', 401)
        g.corporate_user = user
        return handler(*args, **kwargs)
    return wrapped


@api.route('/auth/login', methods=['POST'])
def login():
    body = request.get_json(silent=True) or request.form
    username = (body.get('username') or '').strip()
    password = body.get('password') or ''
    if not username or not password:
        return error_response('BadRequest', 'username and password are required', 400)
    if username != 'admin' or password != DEMO_PASSWORD:
        return error_response('InvalidCredentials', 'Invalid username or password', 401)

    user = db.session.query(User).filter_by(username=username).first()
    if not user:
        user = User(username='admin', email='admin@gotxa.local', password_hash='demo', role='admin')
        db.session.add(user)
        db.session.commit()

    token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=8)
    SESSIONS[token] = {'user_id': user.id, 'expires_at': expires_at}
    return jsonify({'user': _user_payload(user), 'access_token': token, 'expires_at': expires_at.isoformat()}), 200


@api.route('/auth/logout', methods=['POST'])
@corporate_authenticate
def logout():
    token = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
    SESSIONS.pop(token, None)
    return '', 204


@api.route('/me', methods=['GET'])
@corporate_authenticate
def me():
    return jsonify(_user_payload(g.corporate_user))


@api.route('/dashboard', methods=['GET'])
@corporate_authenticate
def dashboard():
    user = g.corporate_user
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
        return error_response('Forbidden', 'Administrator access is required', 403)
    return jsonify({
        'kpis': {'active_systems': 5, 'open_service_issues': 1, 'task_completion_rate': 78, 'average_response_minutes': 14},
        'team_workload': [{'team': 'Corporate Operations', 'open': 2, 'in_progress': 1}],
        'access_review_count': 1,
    })
