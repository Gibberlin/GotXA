#!/usr/bin/env python3
"""
SCADA Gateway - Real-Time Modbus Polling, REST API & Parallel SIEM Ingestion
Continuously polls Modbus registers from OT PLCs, supports dynamic machine discovery,
and streams telemetry and security events in parallel to the SIEM.
"""

import json
import os
import logging
import time
import threading
import queue
from collections import deque
from datetime import datetime
from flask import Flask, jsonify, request
from pathlib import Path
import uuid
from concurrent.futures import ThreadPoolExecutor
import requests

try:
    from pymodbus.client import AsyncModbusTcpClient
    import asyncio
except ImportError as e:
    AsyncModbusTcpClient = None
    import asyncio
    logging.warning(f"pymodbus not available in local environment: {e}")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SIEM_INGEST_URL = os.getenv('SIEM_INGEST_URL', 'http://backend:5000/api/ingest/events')
COLLECTOR_TOKEN = os.getenv('COLLECTOR_INGEST_TOKEN', '')
PLC_REFINERY_1_HOST = os.getenv('PLC_REFINERY_1_HOST', 'ot-plc-refinery-1')
PLC_REFINERY_2_HOST = os.getenv('PLC_REFINERY_2_HOST', 'ot-plc-refinery-2')

# ============================================================================
# PARALLEL HIGH-THROUGHPUT SIEM PUBLISHER
# ============================================================================

class SiemPublisher:
    """Non-blocking, parallel batch publisher for SCADA telemetry and security events."""
    def __init__(self):
        self.queue = queue.Queue(maxsize=10000)
        self.session = requests.Session()
        self.running = True
        self.worker_threads = []
        for i in range(2):
            t = threading.Thread(target=self._batch_worker, daemon=True, name=f"siem-pub-worker-{i}")
            t.start()
            self.worker_threads.append(t)

    def publish_event(self, event_type, host, message, level='info', device_meta=None, extra_meta=None):
        """Enqueue an event for asynchronous parallel transmission to SIEM."""
        timestamp = datetime.utcnow().isoformat()
        event = {
            'timestamp': timestamp + 'Z',
            'level': level,
            'source': 'ot-scada-gateway',
            'host': host,
            'message': message,
            'event_type': event_type,
            'device': {
                'hostname': host,
                'device_type': 'plc' if 'plc' in host.lower() else 'scada',
                'metadata': {
                    'reported_by': 'ot-scada-gateway',
                    **(device_meta or {}),
                    **(extra_meta or {})
                }
            }
        }
        try:
            self.queue.put_nowait(event)
        except queue.Full:
            logger.warning("SIEM publisher queue full - dropping event")

    def publish_change(self, machine_id, metric, value, timestamp):
        host = f"ot-plc-{machine_id}"
        self.publish_event(
            event_type='SCADA_METRIC_CHANGE',
            host=host,
            message=f"{machine_id} {metric} changed to {value}",
            level='info',
            device_meta={'machine_id': machine_id, 'metric': metric, 'value': value}
        )

    def publish_command(self, machine_id, command, value, reason, status, actor):
        host = f"ot-plc-{machine_id}"
        level = 'high' if command == 'emergency_stop' or status == 'rejected' else 'info'
        self.publish_event(
            event_type='SCADA_COMMAND',
            host=host,
            message=f"Operator '{actor}' executed {command}={value} on {machine_id} (Status: {status}, Reason: {reason})",
            level=level,
            device_meta={'machine_id': machine_id, 'command': command, 'value': value, 'actor': actor, 'status': status}
        )

    def publish_alarm(self, alarm_id, machine_id, metric, status, message, severity):
        host = f"ot-plc-{machine_id}"
        self.publish_event(
            event_type='SCADA_ALARM',
            host=host,
            message=f"Alarm [{alarm_id}] for {machine_id} {metric}: {message} (State: {status})",
            level=severity.lower(),
            device_meta={'alarm_id': alarm_id, 'machine_id': machine_id, 'metric': metric, 'status': status}
        )

    def publish_machine_discovered(self, machine_id, name, host, port):
        self.publish_event(
            event_type='SCADA_MACHINE_DISCOVERY',
            host=host,
            message=f"New machine detected and registered: {name} ({machine_id}) at {host}:{port}",
            level='info',
            device_meta={'machine_id': machine_id, 'name': name, 'host': host, 'port': port}
        )

    def _batch_worker(self):
        """Worker thread that drains the queue and posts batches to SIEM."""
        while self.running:
            batch = []
            try:
                # Wait for at least one item
                item = self.queue.get(timeout=1.0)
                batch.append(item)
                # Drain additional items up to batch size 50
                while len(batch) < 50:
                    try:
                        batch.append(self.queue.get_nowait())
                    except queue.Empty:
                        break
            except queue.Empty:
                continue

            if not batch:
                continue

            if not COLLECTOR_TOKEN:
                # If token is not set yet, discard batch silently
                continue

            try:
                headers = {'X-Collector-Token': COLLECTOR_TOKEN, 'Content-Type': 'application/json'}
                response = self.session.post(SIEM_INGEST_URL, json={'events': batch}, headers=headers, timeout=5)
                if response.status_code not in (200, 202):
                    logger.warning(f"SIEM ingestion returned status {response.status_code}")
            except Exception as e:
                logger.error(f"Failed to post batch to SIEM: {e}")

siem_publisher = SiemPublisher()

# ============================================================================
# FLASK APPLICATION
# ============================================================================

app = Flask(__name__)

# ============================================================================
# DYNAMIC MACHINE REGISTRY & MODBUS POLLING ENGINE
# ============================================================================

CONTROL_LOCK = threading.Lock()
COMMANDS = {}
AUDIT_LOG = deque(maxlen=500)
ALARMS = {}

DEFAULT_MACHINES = {
    'refinery-1': {
        'name': 'Refinery 1 Heater',
        'host': PLC_REFINERY_1_HOST,
        'port': 5003,
        'slave_id': 1,
        'poll_interval': 2,
        'registers': {
            'temperature': {'addr': 0, 'qty': 1, 'scale': 0.1, 'unit': '°C', 'threshold_high': 210, 'threshold_low': 150},
            'pressure': {'addr': 1, 'qty': 1, 'scale': 0.1, 'unit': 'PSI', 'threshold_high': 75, 'threshold_low': 35}
        },
        'controls': [
            {'command': 'set_temperature', 'label': 'Temperature setpoint', 'min': 150, 'max': 220, 'unit': '°C', 'reg_addr': 0},
            {'command': 'set_heater_enabled', 'label': 'Heater enabled', 'type': 'toggle'},
            {'command': 'emergency_stop', 'label': 'Emergency stop', 'type': 'action'},
        ],
        'control_state': {'heater_enabled': True}
    },
    'refinery-2': {
        'name': 'Refinery 2 Flow Unit',
        'host': PLC_REFINERY_2_HOST,
        'port': 5004,
        'slave_id': 1,
        'poll_interval': 2,
        'registers': {
            'flow_rate': {'addr': 2, 'qty': 1, 'scale': 0.1, 'unit': 'L/min', 'threshold_high': 95, 'threshold_low': 25}
        },
        'controls': [
            {'command': 'set_flow_rate', 'label': 'Flow-rate setpoint', 'min': 20, 'max': 100, 'unit': 'L/min', 'reg_addr': 2},
            {'command': 'set_pump_enabled', 'label': 'Pump enabled', 'type': 'toggle'},
            {'command': 'emergency_stop', 'label': 'Emergency stop', 'type': 'action'},
        ],
        'control_state': {'pump_enabled': True}
    },
}

class ModbusPoller:
    """Dynamic multi-machine Modbus polling engine."""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.machines = json.loads(json.dumps(DEFAULT_MACHINES))
        self.data = {}
        self.history = {}
        self.active_tasks = {}
        self.event_loop = None

        for machine_id, config in self.machines.items():
            self._init_machine_structures(machine_id, config)

    def _init_machine_structures(self, machine_id, config):
        key = machine_id.replace('-', '_')
        initial_data = {'status': 'offline', 'last_update': None}
        for reg_name in config.get('registers', {}):
            initial_data[reg_name] = 0.0
        self.data[key] = initial_data
        self.data[machine_id] = initial_data

        if machine_id not in self.history:
            self.history[machine_id] = {reg_name: deque(maxlen=900) for reg_name in config.get('registers', {})}

    def _record(self, machine_id, metric, value, timestamp):
        history = self.history.get(machine_id, {}).get(metric)
        if history is None:
            return
        previous = history[-1]['value'] if history else None
        history.append({'timestamp': timestamp, 'value': value})
        if previous != value:
            siem_publisher.publish_change(machine_id, metric, value, timestamp)

    def get_data(self):
        with self.lock:
            return json.loads(json.dumps(self.data))

    def get_history(self, machine_id, metric):
        with self.lock:
            return list(self.history.get(machine_id, {}).get(metric, []))

    def register_machine(self, machine_id, config):
        """Dynamically add or update a machine at runtime and spawn polling."""
        with self.lock:
            self.machines[machine_id] = config
            self._init_machine_structures(machine_id, config)
        
        siem_publisher.publish_machine_discovered(
            machine_id=machine_id,
            name=config.get('name', machine_id),
            host=config.get('host', machine_id),
            port=config.get('port', 5002)
        )

        # Spawn polling task if loop is running
        if self.event_loop and self.event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self.poll_machine(machine_id), self.event_loop)
            logger.info(f"Dynamically spawned poller for new machine: {machine_id}")

    async def poll_machine(self, machine_id):
        """Asynchronously poll registers for a specific machine."""
        config = self.machines[machine_id]
        host = config.get('host', 'localhost')
        port = config.get('port', 5003)
        slave_id = config.get('slave_id', 1)
        poll_interval = config.get('poll_interval', 2)
        key = machine_id.replace('-', '_')

        last_status = None

        while True:
            try:
                client = AsyncModbusTcpClient(host=host, port=port)
                await client.connect()
                
                if client.connected:
                    logger.info(f"Connected to PLC machine {machine_id} ({host}:{port})")
                    if last_status != 'online':
                        last_status = 'online'
                        siem_publisher.publish_event(
                            'SCADA_PLC_ONLINE', f"ot-plc-{machine_id}",
                            f"PLC connection established for {machine_id} on {host}:{port}",
                            level='info'
                        )

                while client.connected:
                    try:
                        timestamp = datetime.utcnow().isoformat()
                        updates = {}
                        has_error = False

                        for reg_name, reg_info in config.get('registers', {}).items():
                            addr = reg_info.get('addr', 0)
                            qty = reg_info.get('qty', 1)
                            scale = reg_info.get('scale', 0.1)

                            result = await client.read_holding_registers(addr, qty, slave=slave_id)
                            if not result.isError():
                                val = round(result.registers[0] * scale, 2)
                                updates[reg_name] = val
                                self._record(machine_id, reg_name, val, timestamp)
                            else:
                                has_error = True
                                logger.warning(f"Error reading {machine_id} register {reg_name} (addr {addr})")

                        with self.lock:
                            status = 'error' if has_error else 'online'
                            self.data[key].update(updates)
                            self.data[key]['last_update'] = timestamp
                            self.data[key]['status'] = status

                            self.data[machine_id].update(updates)
                            self.data[machine_id]['last_update'] = timestamp
                            self.data[machine_id]['status'] = status

                        await asyncio.sleep(poll_interval)

                    except Exception as e:
                        logger.error(f"Polling cycle error for {machine_id}: {e}")
                        with self.lock:
                            self.data[key]['status'] = 'error'
                            self.data[machine_id]['status'] = 'error'
                        break

                await client.close()

            except Exception as e:
                logger.debug(f"PLC {machine_id} connection error: {e}")
                with self.lock:
                    self.data[key]['status'] = 'offline'
                    self.data[machine_id]['status'] = 'offline'
                if last_status != 'offline':
                    last_status = 'offline'
                    siem_publisher.publish_event(
                        'SCADA_PLC_OFFLINE', f"ot-plc-{machine_id}",
                        f"PLC connection unreachable for {machine_id} on {host}:{port}",
                        level='warn'
                    )
                await asyncio.sleep(5)

poller = ModbusPoller()

def machine_status(machine_id):
    data = poller.get_data()
    key = machine_id.replace('-', '_')
    return data.get(key) or data.get(machine_id) or {'status': 'offline', 'last_update': None}

def refresh_alarms():
    """Inspect all registered machine telemetry against configured thresholds."""
    with CONTROL_LOCK:
        for machine_id, config in poller.machines.items():
            status = machine_status(machine_id)
            for reg_name, reg_info in config.get('registers', {}).items():
                val = status.get(reg_name)
                if val is None:
                    continue

                th_high = reg_info.get('threshold_high')
                th_low = reg_info.get('threshold_low')

                if th_high is not None:
                    alarm_id = f"{machine_id}-{reg_name}-high"
                    active = val > th_high
                    if active and alarm_id not in ALARMS:
                        alarm = {
                            'id': alarm_id, 'machine_id': machine_id, 'metric': reg_name,
                            'severity': 'high', 'message': f'{reg_name} high threshold ({th_high}) exceeded: {val}',
                            'raised_at': datetime.utcnow().isoformat(), 'status': 'active'
                        }
                        ALARMS[alarm_id] = alarm
                        siem_publisher.publish_alarm(alarm_id, machine_id, reg_name, 'active', alarm['message'], 'high')
                    elif not active and alarm_id in ALARMS and ALARMS[alarm_id]['status'] == 'active':
                        ALARMS[alarm_id]['status'] = 'cleared'
                        siem_publisher.publish_alarm(alarm_id, machine_id, reg_name, 'cleared', f'{reg_name} returned to normal: {val}', 'info')

                if th_low is not None:
                    alarm_id = f"{machine_id}-{reg_name}-low"
                    active = val < th_low
                    if active and alarm_id not in ALARMS:
                        alarm = {
                            'id': alarm_id, 'machine_id': machine_id, 'metric': reg_name,
                            'severity': 'high', 'message': f'{reg_name} low threshold ({th_low}) breached: {val}',
                            'raised_at': datetime.utcnow().isoformat(), 'status': 'active'
                        }
                        ALARMS[alarm_id] = alarm
                        siem_publisher.publish_alarm(alarm_id, machine_id, reg_name, 'active', alarm['message'], 'high')
                    elif not active and alarm_id in ALARMS and ALARMS[alarm_id]['status'] == 'active':
                        ALARMS[alarm_id]['status'] = 'cleared'
                        siem_publisher.publish_alarm(alarm_id, machine_id, reg_name, 'cleared', f'{reg_name} returned to normal: {val}', 'info')

async def write_machine_register(machine_id, reg_addr, value):
    config = poller.machines.get(machine_id)
    if not config:
        raise RuntimeError(f"Machine {machine_id} not configured")
    host = config.get('host', 'localhost')
    port = config.get('port', 5003)
    slave_id = config.get('slave_id', 1)

    client = AsyncModbusTcpClient(host=host, port=port)
    await client.connect()
    if not client.connected:
        raise RuntimeError(f"PLC {machine_id} connection unavailable at {host}:{port}")
    try:
        result = await client.write_register(reg_addr, int(value * 10), slave=slave_id)
        if result.isError():
            raise RuntimeError('PLC rejected the register write')
    finally:
        await client.close()

def record_command(machine_id, command, value, reason, status, rejection_reason=None):
    command_id = str(uuid.uuid4())
    actor = request.headers.get('X-Operator', 'anonymous-operator')
    entry = {
        'command_id': command_id, 'machine_id': machine_id, 'command': command,
        'value': value, 'reason': reason, 'actor': actor,
        'requested_at': datetime.utcnow().isoformat(), 'status': status,
    }
    if status == 'applied':
        entry['applied_at'] = datetime.utcnow().isoformat()
    if rejection_reason:
        entry['rejection_reason'] = rejection_reason
    with CONTROL_LOCK:
        COMMANDS[command_id] = entry
        AUDIT_LOG.appendleft(entry)
    
    siem_publisher.publish_command(machine_id, command, value, reason, status, actor)
    return entry

def start_polling():
    """Start async polling engine in a dedicated background event loop."""
    def polling_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        poller.event_loop = loop
        
        # Gather all current machine pollers
        tasks = [poller.poll_machine(m_id) for m_id in poller.machines]
        loop.run_until_complete(asyncio.gather(*tasks))
    
    thread = threading.Thread(target=polling_thread, daemon=True, name="scada-polling-engine")
    thread.start()
    logger.info("Started SCADA dynamic Modbus polling engine")

# ============================================================================
# REST API ENDPOINTS
# ============================================================================

@app.route('/api/modbus', methods=['GET'])
def get_modbus_data():
    """Get current Modbus register values for all machines."""
    try:
        data = poller.get_data()
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Error in /api/modbus: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/modbus/<machine_id>', methods=['GET'])
def get_machine_modbus(machine_id):
    """Get telemetry data for a specific machine."""
    try:
        data = poller.get_data()
        key = machine_id.replace('-', '_')
        result = data.get(key) or data.get(machine_id)
        if not result:
            return jsonify({"error": "Machine not found"}), 404
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error in /api/modbus/{machine_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scada/machines', methods=['GET'])
def list_machines():
    """List all machines, live statuses, and controls."""
    refresh_alarms()
    items = []
    for machine_id, definition in poller.machines.items():
        items.append({
            'id': machine_id,
            'name': definition.get('name', machine_id),
            'controls': definition.get('controls', []),
            'status': machine_status(machine_id),
            'control_state': definition.get('control_state', {})
        })
    return jsonify({'items': items})

@app.route('/api/scada/machines/register', methods=['POST'])
def register_new_machine():
    """Dynamically register a new machine/PLC into the SCADA network."""
    body = request.get_json(silent=True) or {}
    machine_id = body.get('id')
    if not machine_id:
        return jsonify({'error': {'code': 'BadRequest', 'message': 'Machine id is required'}}), 400
    
    name = body.get('name', f"PLC Unit {machine_id}")
    host = body.get('host', f"ot-plc-{machine_id}")
    port = int(body.get('port', 5005))
    registers = body.get('registers', {'process_val': {'addr': 0, 'qty': 1, 'scale': 0.1, 'unit': 'Units'}})
    controls = body.get('controls', [{'command': 'emergency_stop', 'label': 'Emergency stop', 'type': 'action'}])
    
    config = {
        'name': name,
        'host': host,
        'port': port,
        'slave_id': int(body.get('slave_id', 1)),
        'poll_interval': int(body.get('poll_interval', 2)),
        'registers': registers,
        'controls': controls,
        'control_state': {}
    }
    
    poller.register_machine(machine_id, config)
    return jsonify({
        'status': 'registered',
        'machine': {'id': machine_id, **config}
    }), 201

@app.route('/api/scada/machines/<machine_id>/commands', methods=['POST'])
def submit_command(machine_id):
    """Validate, apply, and audit a SCADA command."""
    if machine_id not in poller.machines:
        return jsonify({'error': {'code': 'NotFound', 'message': 'Machine not found'}}), 404
    
    body = request.get_json(silent=True) or {}
    command = body.get('command')
    value = body.get('value')
    reason = body.get('reason', '')
    
    machine_def = poller.machines[machine_id]
    allowed = {control['command']: control for control in machine_def.get('controls', [])}
    if command not in allowed:
        return jsonify({'error': {'code': 'BadRequest', 'message': 'Unsupported command'}}), 400
    if command == 'emergency_stop' and not reason:
        return jsonify({'error': {'code': 'BadRequest', 'message': 'A reason is required for emergency stop'}}), 400

    try:
        control = allowed[command]
        if 'min' in control and 'max' in control:
            value = float(value)
            if not (control['min'] <= value <= control['max']):
                entry = record_command(machine_id, command, value, reason, 'rejected', 'Value outside allowed operating range')
                return jsonify(entry), 422
            
            reg_addr = control.get('reg_addr', 0)
            asyncio.run(write_machine_register(machine_id, reg_addr, value))
        elif control.get('type') == 'toggle':
            if not isinstance(value, bool):
                return jsonify({'error': {'code': 'BadRequest', 'message': 'Toggle value must be boolean'}}), 400
            with CONTROL_LOCK:
                machine_def.setdefault('control_state', {})[command] = value
        elif command == 'emergency_stop':
            asyncio.run(write_machine_register(machine_id, 0, 0))
            with CONTROL_LOCK:
                machine_def.setdefault('control_state', {})['emergency_stopped'] = True

        entry = record_command(machine_id, command, value, reason, 'applied')
        return jsonify(entry), 202
    except Exception as exc:
        logger.error(f"SCADA command error: {exc}")
        entry = record_command(machine_id, command, value, reason, 'rejected', str(exc))
        return jsonify(entry), 503

@app.route('/api/scada/commands/<command_id>', methods=['GET'])
def get_command(command_id):
    with CONTROL_LOCK:
        entry = COMMANDS.get(command_id)
    if not entry:
        return jsonify({'error': {'code': 'NotFound', 'message': 'Command not found'}}), 404
    return jsonify(entry)

@app.route('/api/scada/machines/<machine_id>/history', methods=['GET'])
def machine_history(machine_id):
    if machine_id not in poller.machines:
        return jsonify({'error': {'code': 'NotFound', 'message': 'Machine not found'}}), 404
    metric = request.args.get('metric')
    valid_metrics = set(poller.machines[machine_id].get('registers', {}).keys())
    if metric not in valid_metrics:
        return jsonify({'error': {'code': 'BadRequest', 'message': f'metric is required and must be one of {list(valid_metrics)}'}}), 400
    return jsonify({'machine_id': machine_id, 'metric': metric, 'samples': poller.get_history(machine_id, metric)})

@app.route('/api/scada/alarms', methods=['GET'])
def list_alarms():
    refresh_alarms()
    with CONTROL_LOCK:
        items = list(ALARMS.values())
    return jsonify({'items': items})

@app.route('/api/scada/alarms/<alarm_id>/acknowledge', methods=['POST'])
def acknowledge_alarm(alarm_id):
    body = request.get_json(silent=True) or {}
    with CONTROL_LOCK:
        alarm = ALARMS.get(alarm_id)
        if not alarm:
            return jsonify({'error': {'code': 'NotFound', 'message': 'Alarm not found'}}), 404
        alarm['status'] = 'acknowledged'
        alarm['acknowledged_at'] = datetime.utcnow().isoformat()
        actor = request.headers.get('X-Operator', 'anonymous-operator')
        alarm['acknowledged_by'] = actor
        alarm['note'] = body.get('note', '')
        siem_publisher.publish_alarm(
            alarm_id=alarm_id,
            machine_id=alarm.get('machine_id', 'unknown'),
            metric=alarm.get('metric', ''),
            status='acknowledged',
            message=f"Alarm acknowledged by {actor}: {alarm['note']}",
            severity='info'
        )
        return jsonify(alarm)

@app.route('/api/scada/audit', methods=['GET'])
def control_audit():
    machine_id = request.args.get('machine_id')
    with CONTROL_LOCK:
        items = [item for item in AUDIT_LOG if not machine_id or item['machine_id'] == machine_id]
    return jsonify({'items': items})

@app.route('/health', methods=['GET'])
def health():
    data = poller.get_data()
    is_any_online = any(m.get('status') == 'online' for m in data.values() if isinstance(m, dict))
    status = 'healthy' if is_any_online else 'degraded'
    return jsonify({
        "status": status,
        "service": "scada-gateway",
        "machines_count": len(poller.machines),
        "machines": {m_id: poller.data.get(m_id, {}).get('status', 'unknown') for m_id in poller.machines}
    }), 200

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("🏢 SCADA Gateway - Dynamic Modbus Engine & Parallel SIEM Ingestion")
    logger.info("=" * 70)
    
    start_polling()
    time.sleep(2)
    
    logger.info("Starting SCADA Gateway HTTP Server on port 5002")
    app.run(host='0.0.0.0', port=5002, debug=False, threaded=True)
