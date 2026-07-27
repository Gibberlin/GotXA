#!/usr/bin/env python3
"""
SCADA Gateway - Real-Time Modbus Polling & REST API
Continuously polls Modbus registers from OT PLCs and exposes data via HTTP
"""

import json
import logging
import time
import threading
from datetime import datetime
from flask import Flask, jsonify
from pathlib import Path

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
                                self.data['refinery_1']['last_update'] = datetime.utcnow().isoformat()
                                self.data['refinery_1']['status'] = 'online'
                            
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
                                self.data['refinery_2']['last_update'] = datetime.utcnow().isoformat()
                                self.data['refinery_2']['status'] = 'online'
                            
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

# Initialize global poller
poller = ModbusPoller()

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
