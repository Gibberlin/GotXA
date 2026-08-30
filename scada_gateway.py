#!/usr/bin/env python3
"""
SCADA Gateway - Real-Time Modbus Polling & REST API
Continuously polls Modbus registers from OT PLCs and exposes data via HTTP
"""

import json
import logging
import time
import threading
from collections import deque
from datetime import datetime
from flask import Flask, jsonify, request
from pathlib import Path
import uuid

try:
    from pymodbus.client import AsyncModbusTcpClient
    import asyncio
except ImportError as e:
    print(f"ERROR: Import failed - {e}")
    exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# FLASK APPLICATION
# ============================================================================

app = Flask(__name__)

# ============================================================================
# MODBUS POLLING ENGINE
# ============================================================================

class ModbusPoller:
    """Modbus client for polling PLC registers."""
    
    def __init__(self):
        self.data = {
            'refinery_1': {
                'temperature': 0,
                'pressure': 0,
                'last_update': None,
                'status': 'offline'
            },
            'refinery_2': {
                'flow_rate': 0,
                'last_update': None,
                'status': 'offline'
            }
        }
        self.lock = threading.Lock()
        self.history = {
            'refinery-1': {'temperature': deque(maxlen=900), 'pressure': deque(maxlen=900)},
            'refinery-2': {'flow_rate': deque(maxlen=900)}
        }

    def _record(self, machine_id, metric, value, timestamp):
        self.history[machine_id][metric].append({'timestamp': timestamp, 'value': value})
    
    async def poll_refinery_1(self):
        """Poll temperature and pressure from ot-plc-refinery-1."""
        while True:
            try:
                client = AsyncModbusTcpClient(host='ot-plc-refinery-1', port=5003)
                await client.connect()
                
                logger.info("Connected to ot-plc-refinery-1")
                
                while True:
                    try:
                        # Read holding registers 40001 (index 0) and 40002 (index 1)
                        result = await client.read_holding_registers(0, 2, slave=1)
                        
                        if not result.isError():
                            temp = result.registers[0] / 10.0
                            pressure = result.registers[1] / 10.0
                            
                            with self.lock:
                                self.data['refinery_1']['temperature'] = temp
                                self.data['refinery_1']['pressure'] = pressure
                                timestamp = datetime.utcnow().isoformat()
                                self.data['refinery_1']['last_update'] = timestamp
                                self.data['refinery_1']['status'] = 'online'
                                self._record('refinery-1', 'temperature', temp, timestamp)
                                self._record('refinery-1', 'pressure', pressure, timestamp)
                            
                            logger.debug(f"PLC-1: Temp={temp}°C, Pressure={pressure}PSI")
                        else:
                            logger.warning("Error reading PLC-1 registers")
                            with self.lock:
                                self.data['refinery_1']['status'] = 'error'
                        
                        await asyncio.sleep(2)
                    
                    except Exception as e:
                        logger.error(f"Error polling PLC-1: {e}")
                        with self.lock:
                            self.data['refinery_1']['status'] = 'error'
                        break
                
                await client.close()
            
            except Exception as e:
                logger.error(f"PLC-1 connection error: {e}")
                with self.lock:
                    self.data['refinery_1']['status'] = 'offline'
                await asyncio.sleep(5)
    
    async def poll_refinery_2(self):
        """Poll flow rate from ot-plc-refinery-2."""
        while True:
            try:
                client = AsyncModbusTcpClient(host='ot-plc-refinery-2', port=5004)
                await client.connect()
                
                logger.info("Connected to ot-plc-refinery-2")
                
                while True:
                    try:
                        # Read holding register 40003 (index 2)
                        result = await client.read_holding_registers(2, 1, slave=1)
                        
                        if not result.isError():
                            flow_rate = result.registers[0] / 10.0
                            
                            with self.lock:
                                self.data['refinery_2']['flow_rate'] = flow_rate
                                timestamp = datetime.utcnow().isoformat()
                                self.data['refinery_2']['last_update'] = timestamp
                                self.data['refinery_2']['status'] = 'online'
                                self._record('refinery-2', 'flow_rate', flow_rate, timestamp)
                            
                            logger.debug(f"PLC-2: FlowRate={flow_rate}L/min")
                        else:
                            logger.warning("Error reading PLC-2 registers")
                            with self.lock:
                                self.data['refinery_2']['status'] = 'error'
                        
                        await asyncio.sleep(2)
                    
                    except Exception as e:
                        logger.error(f"Error polling PLC-2: {e}")
                        with self.lock:
                            self.data['refinery_2']['status'] = 'error'
                        break
                
                await client.close()
            
            except Exception as e:
                logger.error(f"PLC-2 connection error: {e}")
                with self.lock:
                    self.data['refinery_2']['status'] = 'offline'
                await asyncio.sleep(5)
    
    def get_data(self):
        """Thread-safe data retrieval."""
        with self.lock:
            return json.loads(json.dumps(self.data))

    def get_history(self, machine_id, metric):
        with self.lock:
            return list(self.history.get(machine_id, {}).get(metric, []))

# Initialize global poller
poller = ModbusPoller()

# The control API is intentionally a simulation layer. Commands are range
# validated, recorded, and, for numeric setpoints, written to the simulated PLC.
CONTROL_LOCK = threading.Lock()
COMMANDS = {}
AUDIT_LOG = deque(maxlen=500)
ALARMS = {}
CONTROL_STATE = {
    'refinery-1': {'heater_enabled': True},
    'refinery-2': {'pump_enabled': True},
}
MACHINES = {
    'refinery-1': {
        'name': 'Refinery 1 Heater',
        'controls': [
            {'command': 'set_temperature', 'label': 'Temperature setpoint', 'min': 150, 'max': 220, 'unit': '°C'},
            {'command': 'set_heater_enabled', 'label': 'Heater enabled', 'type': 'toggle'},
            {'command': 'emergency_stop', 'label': 'Emergency stop', 'type': 'action'},
        ],
    },
    'refinery-2': {
        'name': 'Refinery 2 Flow Unit',
        'controls': [
            {'command': 'set_flow_rate', 'label': 'Flow-rate setpoint', 'min': 20, 'max': 100, 'unit': 'L/min'},
            {'command': 'set_pump_enabled', 'label': 'Pump enabled', 'type': 'toggle'},
            {'command': 'emergency_stop', 'label': 'Emergency stop', 'type': 'action'},
        ],
    },
}


def machine_status(machine_id):
    data = poller.get_data()
    return data['refinery_1' if machine_id == 'refinery-1' else 'refinery_2']


def refresh_alarms():
    checks = [
        ('refinery-1', 'temperature', machine_status('refinery-1').get('temperature'), 210, 'high'),
        ('refinery-1', 'pressure', machine_status('refinery-1').get('pressure'), 75, 'high'),
        ('refinery-2', 'flow_rate', machine_status('refinery-2').get('flow_rate'), 25, 'low'),
    ]
    with CONTROL_LOCK:
        for machine_id, metric, value, threshold, direction in checks:
            active = value is not None and (value > threshold if direction == 'high' else value < threshold)
            alarm_id = f'{machine_id}-{metric}-{direction}'
            if active and alarm_id not in ALARMS:
                ALARMS[alarm_id] = {'id': alarm_id, 'machine_id': machine_id, 'severity': 'high', 'message': f'{metric} {direction} threshold exceeded', 'raised_at': datetime.utcnow().isoformat(), 'status': 'active'}
            elif not active and alarm_id in ALARMS and ALARMS[alarm_id]['status'] == 'active':
                ALARMS[alarm_id]['status'] = 'cleared'


async def write_simulated_register(machine_id, value):
    host, address = ('ot-plc-refinery-1', 0) if machine_id == 'refinery-1' else ('ot-plc-refinery-2', 2)
    client = AsyncModbusTcpClient(host=host, port=5003 if machine_id == 'refinery-1' else 5004)
    await client.connect()
    if not client.connected:
        raise RuntimeError('PLC connection unavailable')
    try:
        result = await client.write_register(address, int(value * 10), slave=1)
        if result.isError():
            raise RuntimeError('PLC rejected the register write')
    finally:
        await client.close()


def record_command(machine_id, command, value, reason, status, rejection_reason=None):
    command_id = str(uuid.uuid4())
    entry = {
        'command_id': command_id, 'machine_id': machine_id, 'command': command,
        'value': value, 'reason': reason, 'actor': request.headers.get('X-Operator', 'anonymous-operator'),
        'requested_at': datetime.utcnow().isoformat(), 'status': status,
    }
    if status == 'applied':
        entry['applied_at'] = datetime.utcnow().isoformat()
    if rejection_reason:
        entry['rejection_reason'] = rejection_reason
    with CONTROL_LOCK:
        COMMANDS[command_id] = entry
        AUDIT_LOG.appendleft(entry)
    return entry

def start_polling():
    """Start async polling in background threads."""
    
    async def run_polling():
        """Run both polling tasks concurrently."""
        await asyncio.gather(
            poller.poll_refinery_1(),
            poller.poll_refinery_2()
        )
    
    def polling_thread():
        """Thread wrapper for asyncio."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_polling())
        except Exception as e:
            logger.error(f"Polling thread error: {e}", exc_info=True)
    
    thread = threading.Thread(target=polling_thread, daemon=True)
    thread.start()
    logger.info("Started Modbus polling threads")

# ============================================================================
# REST API ENDPOINTS
# ============================================================================

@app.route('/api/modbus', methods=['GET'])
def get_modbus_data():
    """Get current Modbus register values."""
    try:
        data = poller.get_data()
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Error in /api/modbus: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/modbus/refinery-1', methods=['GET'])
def get_refinery_1():
    """Get Refinery-1 data (temperature and pressure)."""
    try:
        data = poller.get_data()
        return jsonify(data['refinery_1']), 200
    except Exception as e:
        logger.error(f"Error in /api/modbus/refinery-1: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/modbus/refinery-2', methods=['GET'])
def get_refinery_2():
    """Get Refinery-2 data (flow rate)."""
    try:
        data = poller.get_data()
        return jsonify(data['refinery_2']), 200
    except Exception as e:
        logger.error(f"Error in /api/modbus/refinery-2: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/scada/machines', methods=['GET'])
def list_machines():
    """Machine metadata, live status, and allowed simulated controls."""
    refresh_alarms()
    return jsonify({'items': [
        {'id': machine_id, **definition, 'status': machine_status(machine_id), 'control_state': CONTROL_STATE[machine_id]}
        for machine_id, definition in MACHINES.items()
    ]})


@app.route('/api/scada/machines/<machine_id>/commands', methods=['POST'])
def submit_command(machine_id):
    """Validate, apply, and audit a simulated SCADA command."""
    if machine_id not in MACHINES:
        return jsonify({'error': {'code': 'NotFound', 'message': 'Machine not found'}}), 404
    body = request.get_json(silent=True) or {}
    command, value, reason = body.get('command'), body.get('value'), body.get('reason', '')
    allowed = {control['command']: control for control in MACHINES[machine_id]['controls']}
    if command not in allowed:
        return jsonify({'error': {'code': 'BadRequest', 'message': 'Unsupported command'}}), 400
    if command == 'emergency_stop' and not reason:
        return jsonify({'error': {'code': 'BadRequest', 'message': 'A reason is required for emergency stop'}}), 400

    try:
        if command in {'set_temperature', 'set_flow_rate'}:
            value = float(value)
            control = allowed[command]
            if not control['min'] <= value <= control['max']:
                entry = record_command(machine_id, command, value, reason, 'rejected', 'Value is outside allowed operating range')
                return jsonify(entry), 422
            asyncio.run(write_simulated_register(machine_id, value))
        elif command in {'set_heater_enabled', 'set_pump_enabled'}:
            if not isinstance(value, bool):
                return jsonify({'error': {'code': 'BadRequest', 'message': 'Toggle value must be boolean'}}), 400
            with CONTROL_LOCK:
                CONTROL_STATE[machine_id]['heater_enabled' if command == 'set_heater_enabled' else 'pump_enabled'] = value
        elif command == 'emergency_stop':
            asyncio.run(write_simulated_register(machine_id, 0))
            with CONTROL_LOCK:
                if machine_id == 'refinery-1':
                    CONTROL_STATE[machine_id]['heater_enabled'] = False
                else:
                    CONTROL_STATE[machine_id]['pump_enabled'] = False
        entry = record_command(machine_id, command, value, reason, 'applied')
        return jsonify(entry), 202
    except Exception as exc:
        logger.error('SCADA command failed: %s', exc)
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
    if machine_id not in MACHINES:
        return jsonify({'error': {'code': 'NotFound', 'message': 'Machine not found'}}), 404
    metric = request.args.get('metric')
    valid_metrics = {'refinery-1': {'temperature', 'pressure'}, 'refinery-2': {'flow_rate'}}
    if metric not in valid_metrics[machine_id]:
        return jsonify({'error': {'code': 'BadRequest', 'message': 'metric is required and must belong to the machine'}}), 400
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
        alarm['acknowledged_by'] = request.headers.get('X-Operator', 'anonymous-operator')
        alarm['note'] = body.get('note', '')
        return jsonify(alarm)


@app.route('/api/scada/audit', methods=['GET'])
def control_audit():
    machine_id = request.args.get('machine_id')
    with CONTROL_LOCK:
        items = [item for item in AUDIT_LOG if not machine_id or item['machine_id'] == machine_id]
    return jsonify({'items': items})

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    data = poller.get_data()
    status = 'healthy' if (
        data['refinery_1']['status'] == 'online' or 
        data['refinery_2']['status'] == 'online'
    ) else 'degraded'
    
    return jsonify({
        "status": status,
        "service": "scada-gateway",
        "plc_1": data['refinery_1']['status'],
        "plc_2": data['refinery_2']['status']
    }), 200

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("🏢 SCADA Gateway - Modbus Polling & REST API")
    logger.info("=" * 70)
    
    # Start polling threads
    start_polling()
    
    # Allow polling to initialize
    time.sleep(2)
    
    # Start Flask server
    logger.info("Starting SCADA Gateway on port 5002")
    app.run(host='0.0.0.0', port=5002, debug=False, threaded=True)
