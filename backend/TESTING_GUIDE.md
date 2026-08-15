# Backend Testing Guide

Complete testing instructions for the GOTXA SIEM/SOAR backend API.

## Prerequisites

- Backend running on `http://localhost:5000`
- PostgreSQL with `siem_db` database initialized
- `curl` installed (or Postman)

---

## Quick Health Check

```bash
# Health endpoint (no auth required)
curl http://localhost:5000/health

# Expected response:
# {"status":"healthy","timestamp":"2026-08-14T10:30:45.123456Z","database":"connected"}
```

---

## Test All Endpoints

### 1. Overview Dashboard
```bash
curl -H "X-User-ID: admin" http://localhost:5000/api/overview
```

**Expected:** KPI cards, recent alerts, source health

---

### 2. List Alerts
```bash
# All alerts
curl -H "X-User-ID: admin" http://localhost:5000/api/alerts

# With filters
curl -H "X-User-ID: admin" \
  "http://localhost:5000/api/alerts?severity=critical&status=open&page=1"

# Custom page size
curl -H "X-User-ID: admin" \
  "http://localhost:5000/api/alerts?page=1&page_size=10"
```

**Expected:** Paginated alert list with pagination metadata

---

### 3. Get Alert Details
```bash
# First, get an alert ID from list
ALERT_ID=$(curl -s -H "X-User-ID: admin" \
  http://localhost:5000/api/alerts \
  | jq -r '.data.items[0].id')

# Get details
curl -H "X-User-ID: admin" \
  http://localhost:5000/api/alerts/$ALERT_ID
```

**Expected:** Full alert details with raw_event, entities, mitre_tactics, related alerts

---

### 4. Update Alert Status
```bash
ALERT_ID="<alert-uuid>"

curl -X PUT \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{"status":"investigating","reason":"Starting investigation"}' \
  http://localhost:5000/api/alerts/$ALERT_ID/status
```

**Expected:** Success response with updated status

---

### 5. Suppress Alert
```bash
ALERT_ID="<alert-uuid>"

curl -X POST \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "reason":"False positive",
    "scope":"single",
    "duration_hours":24
  }' \
  http://localhost:5000/api/alerts/$ALERT_ID/suppress
```

**Expected:** Alert marked as suppressed

---

### 6. Bulk Assign Alerts
```bash
# Get two alert IDs
curl -s -H "X-User-ID: admin" \
  http://localhost:5000/api/alerts?page_size=2 \
  | jq -r '.data.items[].id' > /tmp/alert_ids.txt

ALERT_IDS=$(jq -R -s -c 'split("\n")[:-1]' /tmp/alert_ids.txt)

curl -X POST \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d "{
    \"alert_ids\": $ALERT_IDS,
    \"assignee_id\": \"analyst-user-id\",
    \"reason\": \"Bulk assignment for triage\"
  }" \
  http://localhost:5000/api/alerts/bulk-assign
```

**Expected:** Confirmation of assignment

---

### 7. Raw Log Stream
```bash
# Initial load
curl -H "X-User-ID: admin" \
  "http://localhost:5000/api/raw-stream?limit=10"

# With cursor for next page
CURSOR="<cursor-from-previous-response>"
curl -H "X-User-ID: admin" \
  "http://localhost:5000/api/raw-stream?limit=10&cursor=$CURSOR"
```

**Expected:** Array of raw log entries with next_cursor

---

### 8. List Incidents
```bash
# All incidents
curl -H "X-User-ID: admin" http://localhost:5000/api/incidents

# Filtered
curl -H "X-User-ID: admin" \
  "http://localhost:5000/api/incidents?status=open&priority=high"
```

**Expected:** Paginated incident list

---

### 9. Create Incident
```bash
curl -X POST \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Suspected Data Exfiltration",
    "description":"Large data transfer detected",
    "severity":"critical",
    "priority":"high",
    "affected_assets":["server-01","workstation-05"],
    "mitre_tactics":["T1041"],
    "reason":"Created from alert correlation"
  }' \
  http://localhost:5000/api/incidents
```

**Expected:** New incident with incident_id (INC-XXXXX)

---

### 10. Get Incident Details
```bash
INCIDENT_ID="<incident-uuid>"

curl -H "X-User-ID: admin" \
  http://localhost:5000/api/incidents/$INCIDENT_ID
```

**Expected:** Full incident details with alerts, tasks, evidence counts

---

### 11. Update Incident Status (Lifecycle)
```bash
INCIDENT_ID="<incident-uuid>"

# Transition: open → investigating
curl -X PUT \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "status":"investigating",
    "reason":"Beginning analysis of affected systems"
  }' \
  http://localhost:5000/api/incidents/$INCIDENT_ID/status

# Later: investigating → contained
curl -X PUT \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "status":"contained",
    "reason":"Isolated compromised systems"
  }' \
  http://localhost:5000/api/incidents/$INCIDENT_ID/status

# Later: contained → resolved
curl -X PUT \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "status":"resolved",
    "reason":"Remediation completed"
  }' \
  http://localhost:5000/api/incidents/$INCIDENT_ID/status

# Finally: resolved → closed
curl -X PUT \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "status":"closed",
    "closure_reason":"Threat eliminated",
    "lessons_learned":"Implement additional monitoring on critical data systems"
  }' \
  http://localhost:5000/api/incidents/$INCIDENT_ID/status
```

**Expected:** Successful transitions only (409 Conflict on invalid transitions)

---

### 12. Assign Incident
```bash
INCIDENT_ID="<incident-uuid>"
USER_ID="<analyst-user-id>"

curl -X POST \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d "{"owner_id":"$USER_ID"}" \
  http://localhost:5000/api/incidents/$INCIDENT_ID/assign
```

**Expected:** Incident reassigned

---

### 13. Link Alert to Incident
```bash
INCIDENT_ID="<incident-uuid>"
ALERT_ID="<alert-uuid>"

curl -X POST \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d "{\"alert_id\":\"$ALERT_ID\"}" \
  http://localhost:5000/api/incidents/$INCIDENT_ID/link-alert
```

**Expected:** Alert linked (now visible in incident details)

---

### 14. List SOAR Actions
```bash
curl -H "X-User-ID: admin" \
  http://localhost:5000/api/v1/soar/actions
```

**Expected:** Array of available playbooks with metadata

---

### 15. Execute SOAR Playbook
```bash
curl -X POST \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "action_id":"containment.isolate_host",
    "incident_id":"<incident-uuid>",
    "parameters":{
      "hostname":"server-01",
      "network_segment":"production"
    },
    "reason":"Isolating compromised host from network",
    "change_ticket":"CHG-123456",
    "mode":"live"
  }' \
  http://localhost:5000/api/v1/soar/execute
```

**Expected:** Execution started with execution_id (EXEC-XXXXX)

---

### 16. SOAR Execution History
```bash
curl -H "X-User-ID: admin" \
  "http://localhost:5000/api/v1/soar/history?page=1&page_size=10"
```

**Expected:** List of playbook executions with status

---

### 17. List Settings
```bash
curl -H "X-User-ID: admin" \
  http://localhost:5000/api/settings

# Filter by section
curl -H "X-User-ID: admin" \
  "http://localhost:5000/api/settings?section=alert_rules"
```

**Expected:** Settings list (sensitive values masked)

---

### 18. Update Settings
```bash
curl -X PUT \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "section":"alert_rules",
    "key":"min_severity_threshold",
    "value":"high",
    "reason":"Reducing noise from low-severity alerts"
  }' \
  http://localhost:5000/api/settings
```

**Expected:** Setting updated

---

### 19. List Audit Events
```bash
curl -H "X-User-ID: admin" \
  "http://localhost:5000/api/audit-events?page=1"
```

**Expected:** Immutable audit trail entries

---

### 20. Get Capabilities
```bash
curl -H "X-User-ID: admin" \
  http://localhost:5000/api/capabilities
```

**Expected:** User's available actions based on role

---

## Permission Tests

### Admin Role (Full Access)
```bash
# Should succeed
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"section":"test","key":"test","value":"123"}' \
  http://localhost:5000/api/settings
```

### Analyst Role (Limited)
```bash
# Should fail with 403 Forbidden
curl -X POST -H "X-User-ID: analyst" -H "Content-Type: application/json" \
  -d '{"section":"test","key":"test","value":"123"}' \
  http://localhost:5000/api/settings
```

---

## Workflow Test: Full Incident Response

Complete workflow from alert to resolution:

```bash
#!/bin/bash

# 1. View alert
echo "=== Getting Alert ==="
ALERT=$(curl -s -H "X-User-ID: admin" http://localhost:5000/api/alerts?page_size=1)
ALERT_ID=$(echo $ALERT | jq -r '.data.items[0].id')
ALERT_TITLE=$(echo $ALERT | jq -r '.data.items[0].title')
echo "Alert: $ALERT_TITLE ($ALERT_ID)"

# 2. Create incident
echo "=== Creating Incident ==="
INCIDENT=$(curl -s -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d "{
    \"title\":\"Incident from $ALERT_TITLE\",
    \"severity\":\"critical\",
    \"description\":\"Auto-created from alert\"
  }" \
  http://localhost:5000/api/incidents)
INCIDENT_ID=$(echo $INCIDENT | jq -r '.data.id')
INCIDENT_NUM=$(echo $INCIDENT | jq -r '.data.incident_id')
echo "Created: $INCIDENT_NUM ($INCIDENT_ID)"

# 3. Link alert
echo "=== Linking Alert to Incident ==="
curl -s -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d "{\"alert_id\":\"$ALERT_ID\"}" \
  http://localhost:5000/api/incidents/$INCIDENT_ID/link-alert | jq '.message'

# 4. Update status: open → investigating
echo "=== Updating Status: open → investigating ==="
curl -s -X PUT -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"status":"investigating","reason":"Starting analysis"}' \
  http://localhost:5000/api/incidents/$INCIDENT_ID/status | jq '.data.status'

# 5. Execute playbook
echo "=== Executing SOAR Playbook ==="
EXEC=$(curl -s -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{
    "action_id":"containment.isolate_host",
    "parameters":{"hostname":"server-01"},
    "reason":"Containing threat"
  }' \
  http://localhost:5000/api/v1/soar/execute)
EXEC_ID=$(echo $EXEC | jq -r '.data.execution_id')
echo "Started: $EXEC_ID"

# 6. Update status: investigating → contained
echo "=== Updating Status: investigating → contained ==="
curl -s -X PUT -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"status":"contained","reason":"Host isolated"}' \
  http://localhost:5000/api/incidents/$INCIDENT_ID/status | jq '.data.status'

# 7. Update status: contained → resolved
echo "=== Updating Status: contained → resolved ==="
curl -s -X PUT -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"status":"resolved","reason":"Remediation complete"}' \
  http://localhost:5000/api/incidents/$INCIDENT_ID/status | jq '.data.status'

# 8. Close incident
echo "=== Updating Status: resolved → closed ==="
curl -s -X PUT -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{
    "status":"closed",
    "closure_reason":"Threat neutralized",
    "lessons_learned":"Implement EDR on all servers"
  }' \
  http://localhost:5000/api/incidents/$INCIDENT_ID/status | jq '.data.status'

# 9. View audit trail
echo "=== Audit Trail ==="
curl -s -H "X-User-ID: admin" http://localhost:5000/api/audit-events?page_size=5 | jq '.data.items[] | {action, resource_type, resource_id}'

echo "=== Workflow Complete ==="
```

Save as `test_workflow.sh`, make executable, and run:
```bash
chmod +x test_workflow.sh
./test_workflow.sh
```

---

## Error Handling Tests

### Invalid State Transition
```bash
# Try to go directly from "open" to "resolved" (skipping "investigating")
curl -X PUT \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{"status":"resolved"}' \
  http://localhost:5000/api/incidents/<incident-id>/status

# Expected: 409 Conflict
# {"error":{"code":"InvalidStateTransition","message":"Cannot transition from open to resolved"}}
```

### Permission Denied
```bash
# Analyst trying to update settings (requires admin)
curl -X PUT \
  -H "X-User-ID: analyst" \
  -H "Content-Type: application/json" \
  -d '{"section":"test","key":"test","value":"value"}' \
  http://localhost:5000/api/settings

# Expected: 403 Forbidden
# {"error":{"code":"Forbidden","message":"Permission denied: settings.write"}}
```

### Not Found
```bash
curl -H "X-User-ID: admin" \
  http://localhost:5000/api/alerts/nonexistent-id

# Expected: 404 Not Found
# {"error":{"code":"NotFound","message":"Alert not found"}}
```

---

## Performance Testing

```bash
# Load test: 100 concurrent requests
ab -n 100 -c 10 -H "X-User-ID: admin" http://localhost:5000/api/alerts

# Expected: Response time < 100ms per request
```

---

## Database Verification

```bash
# Connect to PostgreSQL
psql -U siem_user -d siem_db

# Check tables
\dt

# Verify audit events were logged
SELECT correlation_id, action, resource_type, actor_id, created_at 
FROM audit_events 
ORDER BY created_at DESC 
LIMIT 10;

# Check alert suppression
SELECT alert_id, is_suppressed, suppression_reason, suppression_expires_at 
FROM alerts 
WHERE is_suppressed = true;

# Check incident status history
SELECT incident_id, status, updated_at 
FROM incidents 
ORDER BY updated_at DESC 
LIMIT 10;
```

---

## Summary

| Test | Endpoint | Method | Expected |
|------|----------|--------|----------|
| Health | `/health` | GET | 200, healthy |
| Overview | `/api/overview` | GET | 200, KPI data |
| List Alerts | `/api/alerts` | GET | 200, paginated list |
| Create Incident | `/api/incidents` | POST | 201, incident_id |
| Update Status | `/api/incidents/<id>/status` | PUT | 200, new status |
| Link Alert | `/api/incidents/<id>/link-alert` | POST | 200, linked |
| Execute Playbook | `/api/v1/soar/execute` | POST | 202, execution_id |
| Audit Trail | `/api/audit-events` | GET | 200, immutable events |

All tests use `X-User-ID: admin` for demo authentication.
