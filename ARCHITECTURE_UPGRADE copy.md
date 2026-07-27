# Architectural Upgrade - Industrial SCADA Simulation & Frontend Decoupling

## Summary

This upgrade implements a comprehensive refactoring of the cyber range infrastructure:

### 1. Frontend Decoupling & Separation

**New Structure:**
```
frontend/
├── siem_dashboard/
│   └── index.html          # SIEM dashboard served from external path
├── corp_portal/
│   └── index.html          # Corporate auth portal frontend
├── scada_dashboard/
│   └── index.html          # SCADA HMI real-time monitoring UI
└── log_stream/
    └── (reserved for future log streaming UI)
```

**Benefits:**
- Frontend developers can work with VS Code Live Server without Docker
- Decoupled templating - UIs independent of backend services
- Enables rapid frontend iteration and local testing
- Clean separation between frontend and application logic

**Implementation:**
- All Flask apps (`corp-portal-agent`, `siem-soar-server`) mount `./frontend` volume
- Apps serve from external paths (e.g., `/app/frontend/siem_dashboard/index.html`)
- JavaScript APIs properly configured for cross-service communication

### 2. High-Fidelity Industrial Simulation (OT PLCs)

**Modbus TCP Servers Deployed:**

**PLC-1 (ot-plc-refinery-1)** - Port 5003
- Register 40001: Crude Oil Heater Temperature (default 180°C, range 150-220°C)
- Register 40002: Pressure Valve (default 50 PSI, range 30-80 PSI)
- Autonomous register simulation with realistic process variations
- Instrumentation logging (JSON + local logs)

**PLC-2 (ot-plc-refinery-2)** - Port 5004
- Register 40003: Chemical Mixer Flow Rate (default 50 L/min, range 20-100 L/min)
- Realistic flow rate fluctuations
- Structured OT event logging

**Features:**
- Lightweight Modbus TCP servers using pymodbus 3.5.0
- Registers update autonomously with ±0.5-1.0% per cycle variations
- All register changes logged to shared volume for audit trails
- No dummy scripts - real industrial process simulation

### 3. SCADA HMI Dashboard

**New SCADA Gateway Service** (ot-scada-gateway:5002)
- Continuously polls all Modbus registers every 2 seconds
- Real-time REST API: `/api/modbus`, `/api/modbus/refinery-1`, `/api/modbus/refinery-2`
- Thread-safe data aggregation with async Modbus clients

**Dashboard UI** (`frontend/scada_dashboard/index.html`)
- Live SVG gauge graphics for each register
- Three real-time gauges:
  1. **Temperature**: Green (170-190°C) | Orange (160-200°C) | Red (Critical)
  2. **Pressure**: Green (45-55 PSI) | Orange (40-60 PSI) | Red (Critical)
  3. **Flow Rate**: Green (40-60 L/min) | Orange (30-70 L/min) | Red (Critical)
- 2-second refresh interval
- Responsive grid layout
- System status panel (PLC online/offline, last update)

### 4. Network Segmentation & Rogue Device Detection (SIEM)

**Network Architecture:**
- Corporate Network: `172.24.0.0/16` (5001: corp-portal-agent)
- OT/SCADA Network: `172.25.0.0/16` (5003, 5004: PLCs; 5002: SCADA gateway)
- Security Control: `172.23.0.0/16` (5000: SIEM)

**Rogue Device Alerting:**
- Updated SIEM alert engine (`app/engine.py`) enforces subnet validation
- Rule 0 (CRITICAL): Any log from IP outside 172.24.X.X or 172.25.X.X triggers alert
- Alert Payload: "WARNING: Unregistered Device Detected on Network"
- All rogue access attempts logged with HIGH priority

**Implementation:**
- Network segmentation via docker-compose network isolation
- IP validation in ingest pipeline before alert generation
- Centralized alert correlation in PostgreSQL

### 5. Updated Infrastructure

**New/Modified Files:**
- `modbus_plc_server.py` - Modbus TCP server for both PLCs
- `scada_gateway.py` - REST API gateway polling Modbus registers
- `Dockerfile.scada` - SCADA gateway container definition
- `Dockerfile.agent` - Updated to use Python 3.11 + pymodbus
- `app/engine.py` - Enhanced with network segmentation rules
- `app/wsgi.py` - Routes for SCADA dashboard (/scada)
- `vulnerable_app.py` - Serves frontend from external path
- `frontend/` - New frontend directory structure
- `docker-compose.yml` - Updated with SCADA gateway, volume mounts, new networks

**Port Mapping:**
```
5000  →  SIEM/SOAR Dashboard & API
5001  →  Corporate Portal (Vulnerable App)
5002  →  SCADA Gateway REST API
5003  →  Modbus TCP (PLC Refinery-1)
5004  →  Modbus TCP (PLC Refinery-2)
5005  →  Log Collector
```

**Volumes:**
- `./frontend` - Mounted to SIEM and Corp Portal containers
- `/logs` - Shared log volume (all services write instrumentation events)
- `postgres_data` - Persistent database storage

### Verification

All containers start cleanly:
```bash
docker compose up -d
docker compose ps  # All services "Up"
curl http://localhost:5000/health     # SIEM healthy
curl http://localhost:5002/health     # SCADA gateway healthy (both PLCs online)
curl http://localhost:5001/health     # Corp portal healthy
curl http://localhost:5002/api/modbus # Live register data
```

**Dashboard URLs:**
- SIEM: http://localhost:5000/
- SCADA HMI: http://localhost:5000/scada
- Corp Portal: http://localhost:5001/
- SCADA API: http://localhost:5002/api/modbus

### Benefits of This Architecture

1. **Operational Technology Fidelity**
   - Realistic Modbus protocol implementation
   - Independent PLC simulation with autonomous register changes
   - Audit-trail logging for all industrial events

2. **Frontend Flexibility**
   - Developers can iterate locally without containerization
   - Clean API boundaries enable parallel development
   - Decoupled UI from backend logic

3. **Network Security**
   - Strict segmentation enforced at Docker network layer
   - Centralized rogue device detection
   - Compliance-ready audit trails

4. **Scalability**
   - Easy to add new PLCs (just new REGISTERS config)
   - SCADA gateway can poll unlimited Modbus devices
   - Modular frontend components

---

*Upgrade completed: 2026-07-19*
