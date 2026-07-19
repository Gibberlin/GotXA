# Dashboard APIs - Verification & Fix Report

## Issues Found & Fixed

### 1. ✓ SIEM Dashboard API Endpoint Missing
**Problem:** Dashboard HTML was calling `/api/dashboard-data` but endpoint didn't exist
**Solution:** Added `/api/dashboard-data` route to `app/wsgi.py` 
**Verification:** 
```bash
curl http://localhost:5000/api/dashboard-data | jq .
```
Returns: 2967 logs, 612 alerts with aggregated stats

### 2. ✓ Log Data Not Updating on Dashboard
**Problem:** Frontend was fetching from correct endpoint but API route was missing
**Solution:** Implemented full dashboard data aggregation in wsgi.py:
- Total logs & alerts count
- Logs grouped by level (ERROR, INFO, WARN, DEBUG)
- Alerts grouped by severity (HIGH, MEDIUM, LOW)
- Logs by host (top 10)
- Recent logs (last 20)
- Recent alerts (last 20)

### 3. ✓ Database Logs Not Persisting
**Problem:** Logs were being ingested but question about persistence
**Solution:** Verified database persistence:
```
✓ 2,967 logs stored in PostgreSQL
✓ 612 alerts stored in PostgreSQL
✓ Data persists across container restarts
✓ All log sources tracked: corp-portal, ot-plc-1, ot-plc-2, scada-gateway
```

### 4. ✓ SCADA Dashboard API Route
**Problem:** SCADA dashboard called `/api/modbus` which is on different port
**Solution:** SCADA gateway provides `/api/modbus` on port 5002 (correct)
- Refinery-1: Temperature (180°C), Pressure (50 PSI)
- Refinery-2: Flow Rate (50 L/min)
- All PLCs reporting "online" status

## Working APIs

### SIEM Dashboard (Port 5000)
- **GET `/api/dashboard-data`** → Aggregated logs & alerts for visualization
- **GET `/api/v1/dashboard/stats`** → Detailed statistics
- **GET `/api/v1/dashboard/recent`** → Recent events
- **GET `/api/v1/ingress`** → Log ingestion
- **GET `/`** → SIEM Dashboard HTML
- **GET `/scada`** → SCADA Dashboard HTML

### SCADA Gateway (Port 5002)
- **GET `/api/modbus`** → Real-time Modbus register data (all PLCs)
- **GET `/api/modbus/refinery-1`** → Refinery-1 only (temperature, pressure)
- **GET `/api/modbus/refinery-2`** → Refinery-2 only (flow rate)
- **GET `/health`** → Gateway health (both PLCs online)

### Corporate Portal (Port 5001)
- **GET `/`** → Portal login page
- **POST `/login`** → SQL injection vulnerable endpoint
- **POST `/diagnostic`** → Command injection vulnerable endpoint
- **GET `/health`** → Portal health check

## Database Status

### PostgreSQL (siem-postgres)
**Connected to:** `postgresql://siem_user:siem_password@siem-postgres:5432/siem_db`

**Tables:**
- `logs` (2,967 records)
  - id, timestamp, level, message, host, ingested_at, created_at
  - Indexed on: host, level, timestamp
  
- `alerts` (612 records)
  - id, timestamp, host, severity, rule, log_message, log_id, status, updated_at
  - Indexed on: host, severity, timestamp
  - Linked to logs via foreign key

**Data Sources:**
```
corp-portal-agent       10 logs (from test ingestion)
ot-plc-refinery-1       992 logs (from Modbus simulation)
ot-plc-refinery-2       965 logs (from Modbus simulation)
ot-scada-gateway        999 logs (from gateway polling)
test-host               1 log (from API test)
```

## Frontend Status

### All Dashboards Load Successfully
✓ SIEM Dashboard (`http://localhost:5000/`)
✓ SCADA HMI (`http://localhost:5000/scada`)
✓ Corp Portal (`http://localhost:5001/`)

### API Integration
- SIEM Dashboard → `/api/dashboard-data` (working)
- SCADA Dashboard → `/api/modbus` (working)
- Corp Portal → `/login`, `/diagnostic` (working)

## Alert Rules Active

The SIEM enforces multiple detection rules:

1. **Rogue Device Detection (CRITICAL)**
   - Any log from IP outside 172.24.X.X or 172.25.X.X triggers alert

2. **Brute Force Detection (HIGH)**
   - Keywords: failed login, authentication failed, invalid credentials

3. **Critical Errors (HIGH)**
   - Keywords: critical, fatal, emergency, panic, segmentation fault

4. **API Failures (MEDIUM)**
   - Keywords: API fail, service down, connection refused

5. **Network Anomalies (HIGH)**
   - Keywords: port scan, syn flood, ddos, anomalous traffic

6. **Privilege Escalation (HIGH)**
   - Keywords: sudo, root access, privilege escalation

7. **Infrastructure Anomalies (MEDIUM)**
   - Keywords: disk full, memory critical, CPU spike, temperature high

## Real-Time Data Flow

```
OT PLCs (Modbus)
    ↓
SCADA Gateway (polls every 2 seconds)
    ↓
SCADA Dashboard + API (/api/modbus)
    ↓
Real-time SVG gauges (2-second refresh)

Corp Portal (HTTP/form)
    ↓
Vulnerable App (SQLi, Command Injection)
    ↓
Log Collector (ingest endpoint)
    ↓
PostgreSQL (persistent storage)
    ↓
SIEM Dashboard (/api/dashboard-data)
    ↓
Live dashboard charts
```

## Testing Commands

### Inject Test Logs
```bash
curl -X POST http://localhost:5000/api/v1/ingress \
  -H "Content-Type: application/json" \
  -d '{"timestamp":"2026-07-19T18:00:00Z","level":"ERROR","message":"Test error","host":"test-host"}'
```

### Check Dashboard Data
```bash
curl http://localhost:5000/api/dashboard-data | jq .
```

### Check SCADA Data
```bash
curl http://localhost:5002/api/modbus | jq .
```

### Check Database
```bash
docker exec siem-postgres psql -U siem_user -d siem_db -c "SELECT COUNT(*) FROM logs;"
docker exec siem-postgres psql -U siem_user -d siem_db -c "SELECT COUNT(*) FROM alerts;"
```

## Summary

✓ All dashboard APIs operational
✓ All logs persisted in PostgreSQL  
✓ Real-time data flows working
✓ Frontend pages load successfully
✓ Alert correlation active
✓ SCADA Modbus polling active
✓ Network segmentation enforced

---
*Verified: 2026-07-19*
