# BACKEND API HANDOFF - INTEGRATION GUIDE

## Quick Start

### 1. Deploy Backend + Frontend

```bash
# Build all services
docker compose build

# Start everything
docker compose up
```

### 2. Access Applications

```
Corporate Portal:  http://localhost/corp_portal/
SCADA Dashboard:   http://localhost/scada_dashboard/
SIEM Dashboard:    http://localhost/siem_dashboard/
API Health:        http://localhost/api/status
```

### 3. Test SOAR Dashboard

1. Navigate to `http://localhost/siem_dashboard/`
2. Click **SOAR Response** tab
3. Verify:
   - ✅ **Active Mitigations** showing with countdown timers
   - ✅ **Action History** table loading (or demo data)
   - ✅ **Playbooks** listing 3 example playbooks

### 4. Test Raw Logs

1. Click **Raw Logs** tab
2. Verify:
   - ✅ Live log stream updates every 1 second
   - ✅ Play/Pause button works
   - ✅ Auto-scroll checkbox toggles
   - ✅ Clear button removes logs
   - ✅ Color-coded by severity

---

## Backend Endpoints Reference

### Alert Management
```bash
# List open alerts
curl -H "X-User-ID: user-123" http://localhost/api/alerts?status=open

# Get alert details
curl -H "X-User-ID: user-123" http://localhost/api/alerts/{alert_id}

# Get investigation context
curl -H "X-User-ID: user-123" http://localhost/api/alerts/{alert_id}/investigation

# Assign multiple alerts
curl -X POST http://localhost/api/alerts/bulk-assign \
  -H "X-User-ID: user-123" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_ids": ["AL-001", "AL-002"],
    "assignee_id": "user-456",
    "reason": "Initial triage"
  }'

# Suppress alert
curl -X POST http://localhost/api/alerts/{alert_id}/suppress \
  -H "X-User-ID: user-123" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "False positive",
    "expires_at": "2024-01-20T10:00:00Z",
    "scope": "alert"
  }'
```

### Incident Management
```bash
# Create incident
curl -X POST http://localhost/api/incidents \
  -H "X-User-ID: user-123" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Lateral movement detected",
    "severity": "high",
    "priority": "high"
  }'

# Update incident (status transition)
curl -X PATCH http://localhost/api/incidents/{incident_id} \
  -H "X-User-ID: user-123" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "contained",
    "root_cause": "Compromised service account",
    "response_actions": ["Isolate endpoint", "Rotate credentials"]
  }'

# Create task
curl -X POST http://localhost/api/incidents/{incident_id}/tasks \
  -H "X-User-ID: user-123" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Collect endpoint forensics",
    "assigned_to_id": "user-456"
  }'
```

### SOAR Execution
```bash
# List playbooks
curl -H "X-User-ID: user-123" http://localhost/api/playbooks

# Execute playbook (dry-run)
curl -X POST http://localhost/api/playbooks/brute_force_ip_block/executions \
  -H "X-User-ID: user-123" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {"target_ip": "10.0.1.50"},
    "mode": "dry_run",
    "reason": "Brute force detected"
  }'

# Approve high-risk execution
curl -X POST http://localhost/api/playbook-executions/{execution_id}/approve \
  -H "X-User-ID: user-123"
```

### Audit & Visibility
```bash
# Check user capabilities
curl -H "X-User-ID: user-123" http://localhost/api/capabilities

# List audit events
curl -H "X-User-ID: admin-user" http://localhost/api/audit-events

# Get overview dashboard
curl -H "X-User-ID: user-123" http://localhost/api/overview
```

---

## Frontend Integration Points

### Corporate Portal
- **Login:** `POST /api/login` (FormData: username, password)
- **Metrics:** `GET /api/dashboard-metrics`
- **Activity:** `GET /api/recent-activity`

### SCADA Dashboard
- **Modbus Data:** `GET /api/modbus`

### SIEM Dashboard
- **Overview:** `GET /api/overview`
- **Dashboard Data:** `GET /api/dashboard-data` (legacy)
- **Alerts:** `GET /api/alerts`
- **SOAR Actions:** `GET /api/v1/soar/actions`
- **SOAR Mitigations:** `GET /api/v1/soar/mitigations`
- **Playbooks:** `GET /api/v1/soar/playbooks`
- **Raw Logs:** `GET /api/raw-stream`

---

## Demo Data

### Sample Users
```python
admin (role: admin) - Full access
soc-manager (role: soc_manager) - Escalation workflow
analyst-1 (role: analyst) - Investigation only
```

### Sample Alerts
Created on-demand from incoming logs.

### Sample Incidents
Auto-generated from high-severity alert patterns.

### Sample Playbooks
- `brute_force_ip_block` - Triggers on multiple failed logins
- `critical_error_restart` - Triggers on critical service errors
- `ransomware_containment` - Triggers on suspicious encryption patterns

---

## Testing Workflow

### 1. Verify Authentication
```bash
# Should return 401 Unauthorized
curl http://localhost/api/alerts

# Should return data
curl -H "X-User-ID: admin" http://localhost/api/alerts
```

### 2. Verify RBAC
```bash
# Analyst trying to approve playbook (should get 403)
curl -X POST http://localhost/api/playbook-executions/{id}/approve \
  -H "X-User-ID: analyst-1"

# SOC Manager can approve (should succeed)
curl -X POST http://localhost/api/playbook-executions/{id}/approve \
  -H "X-User-ID: soc-manager"
```

### 3. Verify Audit Trail
```bash
# Create incident
INCIDENT=$(curl -X POST http://localhost/api/incidents \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test"}' | jq -r '.data.id')

# Check audit events for this incident
curl -H "X-User-ID: admin" \
  "http://localhost/api/audit-events?resource_id=$INCIDENT"
```

### 4. Verify State Validation
```bash
# Try invalid transition (should return 409)
curl -X PATCH http://localhost/api/incidents/{id} \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{"status": "closed"}'
# ^ Should fail because incident is still "open", not "resolved"
```

---

## Monitoring & Debugging

### Logs
```bash
# Watch backend logs
docker compose logs -f siem-soar-server

# Watch NGINX logs
docker compose logs -f frontend-webserver
```

### Database Inspection
```bash
# Connect to PostgreSQL
docker exec -it siem-postgres psql -U siem_user -d siem_db

# Check alerts
SELECT id, alert_id, title, severity FROM alerts LIMIT 10;

# Check audit trail
SELECT actor_id, action, resource_type, resource_id, created_at 
FROM audit_events ORDER BY created_at DESC LIMIT 20;

# Check incidents
SELECT incident_id, title, status FROM incidents;
```

### API Health
```bash
# Server health
curl http://localhost/health

# API status
curl http://localhost/api/status

# User capabilities
curl -H "X-User-ID: admin" http://localhost/api/capabilities
```

---

## Common Issues & Fixes

### 401 Unauthorized on all endpoints
- **Cause:** Missing X-User-ID header
- **Fix:** Add `-H "X-User-ID: admin"` to curl commands

### 403 Forbidden on action endpoint
- **Cause:** Role lacks permission for action
- **Fix:** Check `/api/capabilities` to see available actions
- **Alternative:** Use admin user for testing

### 404 Resource not found
- **Cause:** Alert/Incident ID doesn't exist
- **Fix:** Verify ID from `GET /api/alerts` or `GET /api/incidents`

### 409 Invalid State Transition
- **Cause:** Trying invalid incident status transition
- **Fix:** Check incident's current status and valid next states

### Database connection error
- **Cause:** PostgreSQL container not ready
- **Fix:** Wait 10 seconds, then retry
- **Verify:** `docker ps` shows siem-postgres running

---

## Next Steps

1. **Frontend Testing**
   - [ ] SIEM dashboard loads overview
   - [ ] SOAR tab loads actions from API
   - [ ] Raw logs stream updates in real-time
   - [ ] Alert assignment works

2. **Automated Testing**
   - [ ] Unit tests for auth/RBAC
   - [ ] Integration tests for workflows
   - [ ] End-to-end tests for incident lifecycle

3. **Load Testing**
   - [ ] Test with 10k+ alerts
   - [ ] Measure query performance
   - [ ] Optimize indexes if needed

4. **Production Hardening**
   - [ ] Enable JWT for token auth
   - [ ] Set up SSL/TLS
   - [ ] Configure rate limiting
   - [ ] Deploy to cloud (AWS, Azure, GCP)

---

## Support

For issues:
1. Check logs: `docker compose logs -f siem-soar-server`
2. Verify connectivity: `curl http://localhost/health`
3. Check database: `docker exec -it siem-postgres psql -U siem_user -d siem_db`
4. Review API.md for endpoint specifications
5. Consult current_state.txt for architecture overview
