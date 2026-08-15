# GOTXA SIEM/SOAR Backend - Complete API Reference

## Base URL
```
http://localhost:5000/api
```

## Authentication
All endpoints except `/health` and `/api/status` require authentication via:
- **X-User-ID** header (demo mode): `curl -H "X-User-ID: admin" http://localhost:5000/api/overview`
- **Bearer token** (future): `curl -H "Authorization: Bearer <token>" http://localhost:5000/api/overview`

## Response Format
All responses follow a standard format:

### Success Response
```json
{
  "data": { /* response data */ },
  "message": "Success",
  "timestamp": "2026-08-14T10:30:45.123456"
}
```

### Error Response
```json
{
  "error": {
    "code": "ErrorCode",
    "message": "Error description",
    "details": { /* optional */ }
  }
}
```

---

## CORE READ ENDPOINTS

### 1. GET `/overview`
Dashboard overview with KPI cards, alerts, and source health.

**Request:**
```bash
curl -H "X-User-ID: admin" http://localhost:5000/api/overview
```

**Response:**
```json
{
  "data": {
    "kpis": {
      "total_open_alerts": 42,
      "critical_alerts": 3,
      "open_incidents": 5,
      "assigned_to_me": 8
    },
    "recent_alerts": [
      {
        "id": "uuid",
        "alert_id": "ALERT-001",
        "title": "Suspicious Login Activity",
        "severity": "high",
        "source": "auth-server-01",
        "detected_at": "2026-08-14T10:15:00Z"
      }
    ],
    "source_health": [
      {
        "source": "firewall-01",
        "alert_count": 145,
        "status": "warning"
      }
    ],
    "timestamp": "2026-08-14T10:30:45Z"
  }
}
```

---

### 2. GET `/dashboard-data`
Legacy dashboard endpoint for backward compatibility.

**Request:**
```bash
curl -H "X-User-ID: admin" http://localhost:5000/api/dashboard-data
```

**Response:**
```json
{
  "data": {
    "total_logs": 1250,
    "total_alerts": 42,
    "critical_alerts": 3,
    "active_hosts": 15
  }
}
```

---

### 3. GET `/raw-stream`
Stream raw logs with cursor-based pagination.

**Query Parameters:**
- `limit` (int, default: 50, max: 250) - Number of items to return
- `cursor` (string) - Pagination cursor from previous response

**Request:**
```bash
curl -H "X-User-ID: admin" "http://localhost:5000/api/raw-stream?limit=50"
```

**Response:**
```json
{
  "data": {
    "items": [
      {
        "id": "uuid",
        "timestamp": "2026-08-14T10:30:00Z",
        "level": "WARNING",
        "host": "web-server-01",
        "message": "High CPU usage detected",
        "raw_event": { /* raw log data */ }
      }
    ],
    "next_cursor": "uuid-of-last-item"
  }
}
```

---

### 4. GET `/alerts`
List alerts with filtering and pagination.

**Query Parameters:**
- `page` (int, default: 1)
- `page_size` (int, default: 25, max: 100)
- `severity` (string) - Filter by severity: critical, high, medium, low
- `status` (string) - Filter by status: open, investigating, resolved, closed
- `assignee` (string) - Filter by assignee user ID

**Request:**
```bash
curl -H "X-User-ID: admin" "http://localhost:5000/api/alerts?severity=critical&status=open&page=1"
```

**Response:**
```json
{
  "data": {
    "items": [
      {
        "id": "uuid",
        "alert_id": "ALERT-001",
        "title": "Suspicious Login",
        "severity": "critical",
        "status": "open",
        "source": "auth-server",
        "assignee_id": "user-uuid",
        "assignee_name": "john.doe",
        "detected_at": "2026-08-14T10:15:00Z",
        "created_at": "2026-08-14T10:15:10Z"
      }
    ],
    "total": 42,
    "page": 1,
    "page_size": 25,
    "pages": 2
  }
}
```

---

### 5. GET `/alerts/<alert_id>`
Get full alert details with investigation context and related alerts.

**Request:**
```bash
curl -H "X-User-ID: admin" http://localhost:5000/api/alerts/alert-uuid
```

**Response:**
```json
{
  "data": {
    "id": "uuid",
    "alert_id": "ALERT-001",
    "title": "Suspicious Login Attempt",
    "severity": "critical",
    "status": "open",
    "source": "auth-server-01",
    "rule_id": "rule-login-anomaly",
    "assignee_id": "user-uuid",
    "assignee_name": "john.doe",
    "is_suppressed": false,
    "suppression_reason": null,
    "raw_event": {
      "username": "admin",
      "source_ip": "192.168.1.100",
      "timestamp": "2026-08-14T10:15:00Z"
    },
    "normalized_event": { /* normalized data */ },
    "entities": ["192.168.1.100", "admin"],
    "mitre_tactics": ["T1110.001"],
    "incident_id": null,
    "detected_at": "2026-08-14T10:15:00Z",
    "created_at": "2026-08-14T10:15:10Z",
    "related_alerts": [
      {
        "id": "uuid",
        "alert_id": "ALERT-002",
        "title": "Failed Login Attempts",
        "created_at": "2026-08-14T10:14:00Z"
      }
    ]
  }
}
```

---

### 6. GET `/incidents`
List incidents with filtering and pagination.

**Query Parameters:**
- `page` (int, default: 1)
- `page_size` (int, default: 25, max: 100)
- `status` (string) - Filter by status: open, investigating, contained, resolved, closed
- `priority` (string) - Filter by priority: low, medium, high, critical

**Request:**
```bash
curl -H "X-User-ID: admin" "http://localhost:5000/api/incidents?status=open&priority=high"
```

**Response:**
```json
{
  "data": {
    "items": [
      {
        "id": "uuid",
        "incident_id": "INC-ABC12345",
        "title": "Suspected Data Exfiltration",
        "status": "investigating",
        "severity": "critical",
        "priority": "high",
        "owner_id": "user-uuid",
        "owner_name": "john.doe",
        "alert_count": 15,
        "created_at": "2026-08-14T10:00:00Z"
      }
    ],
    "total": 5,
    "page": 1,
    "page_size": 25,
    "pages": 1
  }
}
```

---

### 7. GET `/incidents/<incident_id>`
Get full incident details with related alerts, tasks, and evidence.

**Request:**
```bash
curl -H "X-User-ID: admin" http://localhost:5000/api/incidents/incident-uuid
```

**Response:**
```json
{
  "data": {
    "id": "uuid",
    "incident_id": "INC-ABC12345",
    "title": "Suspected Data Exfiltration",
    "description": "Large data transfer detected from user system",
    "status": "investigating",
    "severity": "critical",
    "priority": "high",
    "owner_id": "user-uuid",
    "owner_name": "john.doe",
    "team_id": "team-uuid",
    "root_cause": null,
    "affected_assets": ["server-01", "user-laptop-05"],
    "response_actions": ["Isolate network segment", "Revoke credentials"],
    "mitre_tactics": ["T1041", "T1030"],
    "resolution_notes": null,
    "closure_reason": null,
    "lessons_learned": null,
    "alert_count": 15,
    "task_count": 3,
    "evidence_count": 2,
    "detected_at": "2026-08-14T10:00:00Z",
    "created_at": "2026-08-14T10:05:00Z"
  }
}
```

---

### 8. GET `/capabilities`
Return user's available capabilities based on role.

**Request:**
```bash
curl -H "X-User-ID: admin" http://localhost:5000/api/capabilities
```

**Response:**
```json
{
  "data": {
    "actions": {
      "alerts.bulk_assign": true,
      "alerts.suppress": true,
      "incidents.create": true,
      "incidents.edit": true,
      "incidents.close": true,
      "playbooks.execute": true,
      "playbooks.approve": true,
      "containment.execute": true,
      "settings.write": true
    },
    "version": "1.0",
    "user_role": "admin"
  }
}
```

---

### 9. GET `/audit-events`
List audit events (admin only).

**Query Parameters:**
- `page` (int, default: 1)
- `page_size` (int, default: 25, max: 100)

**Request:**
```bash
curl -H "X-User-ID: admin" "http://localhost:5000/api/audit-events?page=1"
```

**Response:**
```json
{
  "data": {
    "items": [
      {
        "id": "uuid",
        "correlation_id": "corr-123",
        "actor": "john.doe",
        "action": "alert.suppressed",
        "resource_type": "Alert",
        "resource_id": "alert-uuid",
        "status": "success",
        "created_at": "2026-08-14T10:30:00Z"
      }
    ],
    "total": 150,
    "page": 1,
    "page_size": 25,
    "pages": 6
  }
}
```

---

## ALERT ACTIONS

### 10. POST `/alerts/bulk-assign`
Bulk assign alerts to a user.

**Required Permissions:** `alerts.assign` (SOC Manager, Admin)

**Request Body:**
```json
{
  "alert_ids": ["alert-uuid-1", "alert-uuid-2", "alert-uuid-3"],
  "assignee_id": "user-uuid",
  "reason": "Assigned to incident INC-ABC12345"
}
```

**Request:**
```bash
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"alert_ids":["id1","id2"],"assignee_id":"user-id","reason":"Investigation"}' \
  http://localhost:5000/api/alerts/bulk-assign
```

**Response:**
```json
{
  "data": {
    "assigned_count": 2,
    "timestamp": "2026-08-14T10:30:45Z"
  },
  "message": "Alerts assigned"
}
```

---

### 11. POST `/alerts/<alert_id>/suppress`
Suppress an alert (hide from dashboards).

**Required Permissions:** `alerts.suppress` (SOC Manager, Admin)

**Request Body:**
```json
{
  "reason": "False positive - known maintenance window",
  "scope": "single",
  "duration_hours": 24
}
```

**Request:**
```bash
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"reason":"False positive","scope":"single","duration_hours":24}' \
  http://localhost:5000/api/alerts/alert-uuid/suppress
```

**Response:**
```json
{
  "data": {
    "id": "alert-uuid",
    "suppressed": true
  },
  "message": "Alert suppressed"
}
```

---

### 12. PUT `/alerts/<alert_id>/status`
Update alert status.

**Request Body:**
```json
{
  "status": "investigating",
  "reason": "Starting investigation"
}
```

**Request:**
```bash
curl -X PUT -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"status":"investigating","reason":"Starting investigation"}' \
  http://localhost:5000/api/alerts/alert-uuid/status
```

**Response:**
```json
{
  "data": {
    "id": "alert-uuid",
    "status": "investigating"
  },
  "message": "Alert status updated"
}
```

---

## INCIDENT ACTIONS

### 13. POST `/incidents`
Create a new incident.

**Required Permissions:** `incidents.create`

**Request Body:**
```json
{
  "title": "Suspected Data Exfiltration",
  "description": "Large data transfer detected from user system",
  "severity": "critical",
  "priority": "high",
  "affected_assets": ["server-01", "user-laptop-05"],
  "mitre_tactics": ["T1041"],
  "reason": "Created from alert ALERT-001"
}
```

**Request:**
```bash
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{
    "title":"Data Exfiltration",
    "severity":"critical",
    "affected_assets":["server-01"]
  }' \
  http://localhost:5000/api/incidents
```

**Response:**
```json
{
  "data": {
    "id": "incident-uuid",
    "incident_id": "INC-ABC12345",
    "title": "Suspected Data Exfiltration",
    "status": "open"
  },
  "message": "Incident created"
}
```

---

### 14. PUT `/incidents/<incident_id>/status`
Update incident status (lifecycle management).

**Required Permissions:** `incidents.edit`

**Valid Transitions:**
- `open` → `investigating`, `closed`
- `investigating` → `contained`, `closed`
- `contained` → `resolved`, `closed`
- `resolved` → `closed`

**Request Body:**
```json
{
  "status": "investigating",
  "reason": "Beginning investigation of affected systems"
}
```

**Request:**
```bash
curl -X PUT -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"status":"investigating","reason":"Starting investigation"}' \
  http://localhost:5000/api/incidents/incident-uuid/status
```

**Response:**
```json
{
  "data": {
    "id": "incident-uuid",
    "status": "investigating",
    "timestamp": "2026-08-14T10:30:45Z"
  },
  "message": "Incident status updated"
}
```

---

### 15. POST `/incidents/<incident_id>/assign`
Assign incident to a user.

**Required Permissions:** `incidents.edit`

**Request Body:**
```json
{
  "owner_id": "user-uuid"
}
```

**Request:**
```bash
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"owner_id":"user-uuid"}' \
  http://localhost:5000/api/incidents/incident-uuid/assign
```

**Response:**
```json
{
  "data": {
    "id": "incident-uuid",
    "owner_id": "user-uuid"
  },
  "message": "Incident assigned"
}
```

---

### 16. POST `/incidents/<incident_id>/link-alert`
Link an alert to an incident.

**Request Body:**
```json
{
  "alert_id": "alert-uuid"
}
```

**Request:**
```bash
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"alert_id":"alert-uuid"}' \
  http://localhost:5000/api/incidents/incident-uuid/link-alert
```

**Response:**
```json
{
  "data": {
    "incident_id": "incident-uuid",
    "alert_id": "alert-uuid"
  },
  "message": "Alert linked"
}
```

---

## SOAR PLAYBOOK ACTIONS

### 17. GET `/v1/soar/actions`
List available SOAR playbooks/actions.

**Request:**
```bash
curl -H "X-User-ID: admin" http://localhost:5000/api/v1/soar/actions
```

**Response:**
```json
{
  "data": {
    "actions": [
      {
        "id": "containment.isolate_host",
        "name": "Isolate Compromised Host",
        "description": "Isolate host from network",
        "category": "containment",
        "risk_level": "high",
        "requires_approval": true,
        "estimated_time": "5 minutes"
      },
      {
        "id": "response.reset_password",
        "name": "Reset User Credentials",
        "description": "Force password reset for compromised account",
        "category": "response",
        "risk_level": "medium",
        "requires_approval": true,
        "estimated_time": "2 minutes"
      }
    ]
  }
}
```

---

### 18. POST `/v1/soar/execute`
Execute a SOAR playbook.

**Required Permissions:** `playbooks.execute`

**Request Body:**
```json
{
  "action_id": "containment.isolate_host",
  "incident_id": "incident-uuid",
  "parameters": {
    "hostname": "server-01",
    "network_segment": "production"
  },
  "reason": "Isolating compromised host from network",
  "change_ticket": "CHG-123456",
  "mode": "live"
}
```

**Request:**
```bash
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{
    "action_id":"containment.isolate_host",
    "parameters":{"hostname":"server-01"},
    "reason":"Security incident response"
  }' \
  http://localhost:5000/api/v1/soar/execute
```

**Response:**
```json
{
  "data": {
    "execution_id": "EXEC-ABC12345",
    "status": "pending",
    "playbook_id": "containment.isolate_host"
  },
  "message": "Playbook execution started"
}
```

---

### 19. GET `/v1/soar/history`
Get SOAR playbook execution history.

**Query Parameters:**
- `page` (int, default: 1)
- `page_size` (int, default: 25, max: 100)

**Request:**
```bash
curl -H "X-User-ID: admin" "http://localhost:5000/api/v1/soar/history?page=1"
```

**Response:**
```json
{
  "data": {
    "items": [
      {
        "execution_id": "EXEC-ABC12345",
        "playbook_id": "containment.isolate_host",
        "status": "completed",
        "triggered_by": "john.doe",
        "created_at": "2026-08-14T10:15:00Z",
        "completed_at": "2026-08-14T10:20:00Z"
      }
    ],
    "total": 25,
    "page": 1,
    "page_size": 25
  }
}
```

---

## SETTINGS & CONFIGURATION

### 20. GET `/settings`
List all settings.

**Required Permissions:** `settings.read` (Admin only)

**Query Parameters:**
- `section` (string) - Filter by section (e.g., "alert_rules", "integrations")

**Request:**
```bash
curl -H "X-User-ID: admin" "http://localhost:5000/api/settings?section=alert_rules"
```

**Response:**
```json
{
  "data": {
    "items": [
      {
        "section": "alert_rules",
        "key": "min_severity_threshold",
        "value": "medium",
        "type": "string"
      },
      {
        "section": "integrations",
        "key": "slack_webhook",
        "value": null,
        "type": "string"
      }
    ]
  }
}
```

---

### 21. PUT `/settings`
Update settings.

**Required Permissions:** `settings.write` (Admin only)

**Request Body:**
```json
{
  "section": "alert_rules",
  "key": "min_severity_threshold",
  "value": "high",
  "reason": "Reducing noise from low-severity alerts"
}
```

**Request:**
```bash
curl -X PUT -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{
    "section":"alert_rules",
    "key":"min_severity_threshold",
    "value":"high"
  }' \
  http://localhost:5000/api/settings
```

**Response:**
```json
{
  "data": {
    "section": "alert_rules",
    "key": "min_severity_threshold"
  },
  "message": "Setting updated"
}
```

---

## HEALTH & STATUS

### 22. GET `/health`
Health check endpoint (no auth required).

**Request:**
```bash
curl http://localhost:5000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-08-14T10:30:45Z",
  "database": "connected"
}
```

---

### 23. GET `/api/status`
API status endpoint (no auth required).

**Request:**
```bash
curl http://localhost:5000/api/status
```

**Response:**
```json
{
  "status": "running",
  "version": "1.0",
  "timestamp": "2026-08-14T10:30:45Z"
}
```

---

## Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `Unauthorized` | 401 | Invalid or missing credentials |
| `Forbidden` | 403 | Permission denied for this action |
| `NotFound` | 404 | Resource not found |
| `BadRequest` | 400 | Invalid request parameters |
| `InvalidStateTransition` | 409 | Invalid state transition (e.g., incident status) |
| `InternalError` | 500 | Server error |

---

## RBAC Permissions Matrix

| Action | Admin | SOC Manager | Analyst |
|--------|-------|-------------|---------|
| `alerts.view` | ✓ | ✓ | ✓ |
| `alerts.assign` | ✓ | ✓ | ✗ |
| `alerts.suppress` | ✓ | ✓ | ✗ |
| `incidents.create` | ✓ | ✓ | ✓ |
| `incidents.edit` | ✓ | ✓ | ✓ |
| `incidents.close` | ✓ | ✓ | ✗ |
| `playbooks.execute` | ✓ | ✓ | ✗ |
| `playbooks.approve` | ✓ | ✗ | ✗ |
| `containment.execute` | ✓ | ✓ | ✗ |
| `settings.write` | ✓ | ✗ | ✗ |
| `audit.view` | ✓ | ✓ | ✗ |

---

## Example Workflows

### Workflow 1: Respond to Critical Alert

```bash
# 1. View alert details
curl -H "X-User-ID: analyst1" \
  http://localhost:5000/api/alerts/alert-uuid

# 2. Create incident
curl -X POST -H "X-User-ID: soc-manager" -H "Content-Type: application/json" \
  -d '{"title":"Incident","severity":"critical"}' \
  http://localhost:5000/api/incidents

# 3. Link alert to incident
curl -X POST -H "X-User-ID: soc-manager" -H "Content-Type: application/json" \
  -d '{"alert_id":"alert-uuid"}' \
  http://localhost:5000/api/incidents/incident-uuid/link-alert

# 4. Execute containment playbook
curl -X POST -H "X-User-ID: soc-manager" -H "Content-Type: application/json" \
  -d '{
    "action_id":"containment.isolate_host",
    "parameters":{"hostname":"server-01"}
  }' \
  http://localhost:5000/api/v1/soar/execute

# 5. Update incident status
curl -X PUT -H "X-User-ID: soc-manager" -H "Content-Type: application/json" \
  -d '{"status":"contained","reason":"Host isolated"}' \
  http://localhost:5000/api/incidents/incident-uuid/status
```

---

## Testing Commands

```bash
# Test authentication
curl -H "X-User-ID: admin" http://localhost:5000/api/overview

# Test list alerts with filters
curl -H "X-User-ID: admin" \
  "http://localhost:5000/api/alerts?severity=critical&status=open&page=1"

# Test alert bulk assignment
curl -X POST \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_ids":["id1","id2"],
    "assignee_id":"analyst-uuid",
    "reason":"Investigation"
  }' \
  http://localhost:5000/api/alerts/bulk-assign

# Test capabilities
curl -H "X-User-ID: admin" http://localhost:5000/api/capabilities
```
