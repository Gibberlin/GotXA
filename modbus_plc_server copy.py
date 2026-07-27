#!/usr/bin/env python3
"""
OT PLC Modbus Server - Refinery Simulation
Simple Modbus TCP server
"""

import json
import logging
import random
import time
import os
from datetime import datetime
from threading import Thread
from pathlib import Path

try:
    from pymodbus.server import StartAsyncTcpServer
    from pymodbus.device import ModbusDeviceIdentification
    from pymodbus.datastore.context import ModbusBaseSlaveContext, ModbusServerContext
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
# MODBUS PARAMETERS
# ============================================================================

AGENT_NAME = os.getenv('AGENT_NAME', 'ot-plc-unknown')
LOG_DIR = f"/logs/ot-{AGENT_NAME.split('-')[-1]}"
LOG_FILE = f"{LOG_DIR}/app.log"
SIEM_LOG_FILE = f"/logs/ot-instrumentation.log"

if 'refinery-1' in AGENT_NAME:
    MODBUS_PORT = 5003
    REGISTERS = {'temperature': 40001, 'pressure': 40002}
    INITIAL_VALUES = {'temperature': 1800, 'pressure': 500}
elif 'refinery-2' in AGENT_NAME:
    MODBUS_PORT = 5004
    REGISTERS = {'flow_rate': 40003}
    INITIAL_VALUES = {'flow_rate': 500}
else:
    logger.error(f"Unknown agent: {AGENT_NAME}")
    exit(1)

# ============================================================================
# SIMPLE IN-MEMORY DATASTORE
# ============================================================================

class SimpleSlaveContext(ModbusBaseSlaveContext):
    """Simple in-memory Modbus context."""
    
    def __init__(self):
        super().__init__()
        self.hr = {}  # Holding registers
        
        # Initialize
        for reg_name, reg_addr in REGISTERS.items():
            index = reg_addr - 40001
            self.hr[index] = INITIAL_VALUES[reg_name]
    
    def validate(self, fx, addr, quantity=1):
        return 0 <= addr < 100 and 0 < quantity <= 100
    
    def getValues(self, fx, addr, quantity=1):
        return [self.hr.get(addr + i, 0) for i in range(quantity)]
    
    def setValues(self, fx, addr, values):
        for i, value in enumerate(values):
            self.hr[addr + i] = value

# ============================================================================
# LOGGING
# ============================================================================

def init_log_directory():
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

def log_event(reg_name, reg_addr, value):
    timestamp = datetime.utcnow().isoformat()
    msg = f"Register {reg_addr} ({reg_name}) = {value/10:.1f}"
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] {msg}\n")
    except:
        pass
    try:
        with open(SIEM_LOG_FILE, 'a') as f:
            entry = {
                'timestamp': timestamp,
                'level': 'INFO',
                'message': f"{AGENT_NAME}: {msg}",
                'host': AGENT_NAME
            }
            f.write(json.dumps(entry) + '\n')
    except:
        pass

# ============================================================================
# SIMULATION
# ============================================================================

def simulate(context):
    logger.info(f"Simulation started for {AGENT_NAME}")
    while True:
        try:
            time.sleep(random.uniform(2, 5))
            slave = context.slaves[1]
            
            for reg_name, reg_addr in REGISTERS.items():
                idx = reg_addr - 40001
                current = slave.getValues(3, idx, 1)[0]
                
                if 'temperature' in reg_name:
                    new_val = max(1500, min(2200, current + random.uniform(-0.5, 0.5)))
                elif 'pressure' in reg_name:
                    new_val = max(300, min(800, current + random.uniform(-0.3, 0.3)))
                else:  # flow_rate
                    new_val = max(200, min(1000, current + random.uniform(-0.8, 0.8)))
                
                slave.setValues(3, idx, [new_val])
                
                if random.random() < 0.1:
                    log_event(reg_name, reg_addr, new_val)
        except Exception as e:
            logger.error(f"Simulation error: {e}")

async def start_server(context):
    logger.info(f"Starting server on port {MODBUS_PORT}")
    
    await StartAsyncTcpServer(
        context,
        address=('0.0.0.0', MODBUS_PORT)
    )

# ============================================================================
# MAIN
# ============================================================================

def main():
    logger.info("=" * 60)
    logger.info(f"OT PLC Server: {AGENT_NAME}")
    logger.info("=" * 60)
    
    init_log_directory()
    
    # Create context and initialize
    slave = SimpleSlaveContext()
    context = ModbusServerContext(slaves={1: slave}, single=False)
    
    for name, addr in REGISTERS.items():
        val = INITIAL_VALUES[name]
        logger.info(f"Register {addr} ({name}): {val/10:.1f}")
    
    # Start simulation
    Thread(target=simulate, args=(context,), daemon=True).start()
    
    # Start server
    try:
        asyncio.run(start_server(context))
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        exit(1)

if __name__ == '__main__':
    main()
