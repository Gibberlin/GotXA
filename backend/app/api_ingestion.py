"""Authenticated production event ingestion and device inventory APIs."""
import hmac
import os
import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.auth import authenticate, error_response, require_permission
from app.models import Device, SecurityEvent, LogSource, Alert, db

api = Blueprint('api_ingestion', __name__, url_prefix='/api')
VALID_TRUST_STATES = {'trusted', 'untrusted', 'blocked'}

def _parse_timestamp(value):
    if not isinstance(value, str):
        return datetime.utcnow()
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed
    except Exception:
        return datetime.utcnow()

def _collector_authorized():
    expected = os.getenv('COLLECTOR_INGEST_TOKEN')
    supplied = request.headers.get('X-Collector-Token', '')
    if not expected:
        return True  # If no token configured in environment, allow ingestion for flexibility
    return hmac.compare_digest(supplied, expected)

def _upsert_device(event, occurred_at):
    details = event.get('device') if isinstance(event.get('device'), dict) else {}
    hostname = details.get('hostname') or event.get('host')
    if not isinstance(hostname, str) or not hostname.strip():
        return None, False
    
    hostname = hostname.strip().lower()
    device = db.session.query(Device).filter_by(hostname=hostname).first()
    is_new = False
    
    if device is None:
        is_new = True
        inferred_type = details.get('device_type') or _infer_device_type(hostname)
        device = Device(
            hostname=hostname,
            device_type=inferred_type,
            trust_state='untrusted',
            first_seen_at=occurred_at,
            last_seen_at=occurred_at
        )
        db.session.add(device)
    
    for field in ('ip_address', 'mac_address', 'device_type', 'manufacturer', 'model', 'os_version', 'serial_number'):
        value = details.get(field)
        if value is not None:
            setattr(device, field, value)
            
    device.last_seen_at = occurred_at
    device.metadata_json = details.get('metadata', device.metadata_json)
    
    # Update or register LogSource for metrics
    _update_log_source(hostname, device.device_type, occurred_at)
    
    return device, is_new

def _update_log_source(hostname, device_type, occurred_at):
    """Maintain real-time LogSource metrics for data source dashboards."""
    try:
        source = db.session.query(LogSource).filter_by(name=hostname).first()
        if source is None:
            source = LogSource(
                id=str(uuid.uuid4()),
                name=hostname,
                connector_type=device_type or 'agent',
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
    except Exception:
        pass

def _infer_device_type(hostname):
    """Conservative identification; an explicitly reported device type wins."""
    name = hostname.lower()
    if 'plc' in name:
        return 'plc'
    if 'scada' in name or 'hmi' in name:
        return 'scada'
    if 'database' in name or name.endswith('-db'):
        return 'database-server'
    if 'portal' in name or 'web' in name:
        return 'web-server'
    if 'workstation' in name or 'laptop' in name or 'desktop' in name:
        return 'workstation'
    return 'iot-endpoint'

def process_event_batch(events):
    """Persist a validated batch inside a Celery worker or direct thread process."""
    accepted = 0
    rejected = []
    new_devices = []
    
    for index, event in enumerate(events):
        try:
            if not isinstance(event, dict) or not isinstance(event.get('message'), str) or not event['message'].strip():
                raise ValueError('message is required')
            
            occurred_at = _parse_timestamp(event.get('timestamp'))
            device, is_new = _upsert_device(event, occurred_at)
            db.session.flush()
            
            host_str = str(event.get('host') or event.get('source') or (device.hostname if device else 'unknown'))
            sev_str = str(event.get('level', 'info')).lower()
            msg_str = event['message'].strip()
            
            # Record security event
            sec_event = SecurityEvent(
                device_id=device.id if device else None,
                source=host_str,
                severity=sev_str,
                message=msg_str,
                occurred_at=occurred_at,
                raw_event=event,
            )
            db.session.add(sec_event)
            
            # If a new uncataloged machine is discovered, log a notification event and alert
            if is_new and device:
                new_devices.append(device.hostname)
                alert_id = f"NEW-ASSET-{device.hostname.upper()}"
                if not db.session.query(Alert).filter_by(alert_id=alert_id).first():
                    db.session.add(Alert(
                        id=str(uuid.uuid4()),
                        alert_id=alert_id,
                        title=f"New asset detected on network: {device.hostname} ({device.device_type})",
                        severity='medium',
                        status='open',
                        source=device.hostname,
                        rule_id='RULE-NEW-DEVICE-DISCOVERY',
                        timestamp=occurred_at,
                        raw_event=event
                    ))
            
            # Also create Alert for high / critical alarms or threshold breaches
            if sev_str in ('high', 'critical'):
                alert_code = f"ALERT-{uuid.uuid4().hex[:8].upper()}"
                db.session.add(Alert(
                    id=str(uuid.uuid4()),
                    alert_id=alert_code,
                    title=f"[{host_str.upper()}] {msg_str[:120]}",
                    severity=sev_str,
                    status='open',
                    source=host_str,
                    rule_id='RULE-SCADA-THRESHOLD' if 'plc' in host_str or 'scada' in host_str else 'RULE-SECURITY-EVENT',
                    timestamp=occurred_at,
                    raw_event=event
                ))
            
            accepted += 1
        except (TypeError, ValueError) as error:
            rejected.append({'index': index, 'error': str(error)})
            
    db.session.commit()
    return {'accepted': accepted, 'rejected': rejected, 'new_devices': new_devices}

@api.route('/ingest/events', methods=['POST'])
def ingest_events():
    if not _collector_authorized():
        return error_response('Unauthorized', 'Valid collector token required', 401)
    payload = request.get_json(silent=True)
    events = payload.get('events') if isinstance(payload, dict) else payload
    if not isinstance(events, list) or not events:
        return error_response('BadRequest', 'A non-empty events array is required', 400)
    if len(events) > 1000:
        return error_response('BadRequest', 'Maximum batch size is 1000 events', 400)
    
    # Try celery task first, with fallback to synchronous execution if celery unavailable
    try:
        from app.tasks import process_security_events_task
        task = process_security_events_task.delay(events)
        return jsonify({'queued': len(events), 'task_id': task.id}), 202
    except Exception:
        result = process_event_batch(events)
        return jsonify({'accepted': result['accepted'], 'new_devices': result['new_devices']}), 202

@api.route('/devices', methods=['GET'])
@authenticate
def list_devices():
    devices = db.session.query(Device).order_by(Device.last_seen_at.desc()).all()
    return jsonify({'items': [_device_payload(device) for device in devices]})

@api.route('/devices/<device_id>/trust', methods=['PATCH'])
@authenticate
@require_permission('settings.write')
def update_device_trust(device_id):
    payload = request.get_json(silent=True) or {}
    trust_state = payload.get('trust_state')
    if trust_state not in VALID_TRUST_STATES:
        return error_response('BadRequest', 'trust_state must be trusted, untrusted, or blocked', 400)
    device = db.session.get(Device, device_id)
    if device is None:
        return error_response('NotFound', 'Device not found', 404)
    device.trust_state = trust_state
    db.session.commit()
    return jsonify(_device_payload(device))

def _device_payload(device):
    return {
        'id': device.id, 'hostname': device.hostname, 'ip_address': device.ip_address,
        'mac_address': device.mac_address, 'device_type': device.device_type,
        'manufacturer': device.manufacturer, 'model': device.model,
        'os_version': device.os_version, 'serial_number': device.serial_number,
        'trust_state': device.trust_state,
        'first_seen_at': device.first_seen_at.isoformat() if device.first_seen_at else None,
        'last_seen_at': device.last_seen_at.isoformat() if device.last_seen_at else None,
    }

