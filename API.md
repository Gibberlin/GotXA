# GOTXA SIEM/SOAR API SPECIFICATION

## Overview

Base URL: `/api`
Authentication: Bearer token or secure session
Content-Type: `application/json`

## Response Formats

### Success Response
```json
{
  "data": {},
  "message": "Success",
  "timestamp": "2024-01-15T10:30:00"
}
```

### List Response
```json
{
  "items": [],
  "total": 100,
  "page": 1,
  "page_size": 25,
  "pages": 4
}
```

### Error Response
```json
{
  "error": {
    "code": "InvalidRequest",
    "message": "Description of error",
    "details": {}
  }
}
```

## Authentication

All endpoints require authentication via:
- Bearer token header: `Authorization: Bearer <token>`
- Session cookie: `X-User-ID: <user-id>`

## Endpoints

### 1. READ-ONLY DASHBOARD

#### GET /overview
Returns KPI cards, charts, priority queue, source health.

**Response:**
```json
{
  "kpis": {
    "total_open_alerts": 45,
    "critical_alerts": 3,
    "open_incidents": 12,
    "assigned_to_me": 8
  },
  "recent_alerts": [...],
  "source_health": [...]
}
```

#### GET /dashboard-data
Legacy endpoint for backward compatibility.

#### GET /raw-stream?limit=50&cursor=<cursor>
Cursor-based pagination for logs (max 250 per page).

**Parameters:**
- `limit`: Number of items (1-250)
- `cursor`: Pagination cursor

### 2. ALERTS

#### GET /alerts?severity=&status=&assignee=&page=&page_size=
List alerts with filtering.

**Parameters:**
- `severity`: critical, high, medium, low, info
- `status`: open, investigating, dismissed, resolved
- `assignee`: User ID
- `page`: Page number (default 1)
- `page_size`: Items per page (default 25, max 100)

#### GET /alerts/{alert_id}
Get alert details with full context.

#### GET /alerts/{alert_id}/investigation
Get investigation context: entities, MITRE mappings, timeline, related incidents.

#### POST /alerts/bulk-assign
Assign multiple alerts to user/team.

**Body:**
```json
{
  "alert_ids": ["AL-001", "AL-002"],
  "assignee_id": "user-123",
  "team_id": "soc-tier-2",
  "reason": "Initial triage"
}
```

**Permissions:** `alerts.assign`

#### POST /alerts/{alert_id}/suppress
Suppress an alert.

**Body:**
```json
{
  "reason": "False positive - whitelisted domain",
  "expires_at": "2024-01-20T10:00:00Z",
  "scope": "alert|rule|entity"
}
```

**Permissions:** `alerts.suppress`

### 3. INCIDENTS

#### GET /incidents?status=&priority=&owner=&page=&page_size=
List incidents.

**Parameters:**
- `status`: open, investigating, contained, resolved, closed
- `priority`: critical, high, medium, low
- `owner`: Owner user ID

#### GET /incidents/{incident_id}
Get incident details.

#### POST /incidents
Create a new incident.

**Body:**
```json
{
  "title": "Lateral movement detected",
  "description": "...",
  "severity": "high",
  "priority": "high",
  "owner_id": "user-123",
  "team_id": "soc-tier-2",
  "alert_ids": ["AL-001", "AL-002"]
}
```

**Permissions:** `incidents.create`
**Response:** 201 Created

#### PATCH /incidents/{incident_id}
Update incident (status, assignment, analysis, closure).

**Body:**
```json
{
  "status": "contained",
  "owner_id": "user-123",
  "priority": "critical",
  "root_cause": "...",
  "affected_assets": [...],
  "response_actions": [...],
  "mitre_tactics": ["T1110", "T1078"],
  "closure_reason": "resolved",
  "resolution_notes": "..."
}
```

**State Transitions:**
- open → investigating, dismissed
- investigating → contained, resolved, open
- contained → resolved, investigating
- resolved → closed
- closed → (no transitions)

**Permissions:** `incidents.edit`

**Validation:** Closure requires `closure_reason`, `resolution_notes`.

#### POST /incidents/{incident_id}/tasks
Create task for incident.

**Body:**
```json
{
  "title": "Collect endpoint logs",
  "description": "...",
  "assigned_to_id": "user-123",
  "due_at": "2024-01-16T18:00:00Z"
}
```

#### POST /incidents/{incident_id}/merge
Merge incidents (idempotent).

#### POST /incidents/{incident_id}/split
Split incident into multiple.

#### POST /incidents/{incident_id}/evidence
Add evidence to incident.

### 4. SOAR & RESPONSE

#### POST /playbooks/{playbook_id}/executions
Execute a playbook.

**Body:**
```json
{
  "inputs": { "target_host": "10.0.1.50" },
  "mode": "live|dry_run",
  "reason": "Isolate compromised endpoint",
  "change_ticket": "CHG-1048"
}
```

**Response:** 202 Accepted (for high-risk, returns approval_required: true)

**High-Risk Playbooks:** isolation, firewall_block, user_disable, ransomware

**Permissions:** `playbooks.execute`

#### POST /playbook-executions/{execution_id}/approve
Approve execution.

**Permissions:** `playbooks.approve`

#### POST /playbook-executions/{execution_id}/rollback
Rollback execution.

#### POST /containment-requests
Request immediate containment action.

**Body:**
```json
{
  "alert_id": "AL-001",
  "action": "isolate_endpoint|block_ip|disable_user",
  "target": "host-123",
  "reason": "Ransomware detected"
}
```

### 5. SETTINGS & CONFIGURATION

#### GET /settings/overview
Get all settings (masked if sensitive).

#### GET /settings/{section}
Get settings by section.

#### PATCH /settings/{section}
Update settings (high-risk requires approval).

**Body:**
```json
{
  "values": { "retention_days": 90 },
  "reason": "Compliance requirement",
  "change_ticket": "CHG-1048",
  "rollback_plan": "..."
}
```

**High-Risk Settings:**
- retention_days changes
- Disabling critical source/rule
- Privilege role changes
- Firewall response automation
- OT playbook edits
- Evidence deletion

**Response:** 202 Accepted if approval required

**Permissions:** `settings.write`

#### GET /settings/history
Get setting change history.

#### POST /settings/{section}/validate
Validate setting before apply.

#### POST /settings/{section}/test
Test setting in safe environment.

### 6. REPORTING & ASSETS

#### GET /assets?zone=&criticality=&health=&page=&page_size=
List assets.

#### GET /assets/export?format=csv|xlsx
Export assets.

#### POST /reports
Generate report.

**Body:**
```json
{
  "type": "nist|executive|coverage|post_incident",
  "format": "pdf|csv|xlsx",
  "range": { "from": "2024-01-01T00:00:00Z", "to": "2024-01-15T00:00:00Z" }
}
```

**Response:** 202 Accepted with report_id

#### GET /reports/{report_id}/download
Download generated report.

#### POST /saved-views
Save view/filter for later.

#### GET /saved-views
List saved views.

### 7. AUDIT & ADMIN

#### GET /audit-events?page=&page_size=
List audit events.

**Permissions:** `audit.view`

#### GET /capabilities
Get user's available actions.

**Response:**
```json
{
  "actions": {
    "alerts.bulk_assign": true,
    "incidents.create": true,
    "playbooks.execute": false,
    "settings.write": false
  },
  "version": "1.0",
  "user_role": "analyst"
}
```

### 8. HEALTH

#### GET /health
Server health check.

#### GET /api/status
API status.

## Error Codes

- `BadRequest` (400): Invalid request
- `Unauthorized` (401): Authentication required
- `Forbidden` (403): Permission denied
- `NotFound` (404): Resource not found
- `InvalidStateTransition` (409): Workflow state error
- `InternalError` (500): Server error

## Rate Limiting

- 100 requests per minute per user
- 1000 requests per minute per API key

## Audit Trail

All mutations are logged with:
- Actor (user ID)
- Action (create, update, delete)
- Resource (type, ID)
- Change (before, after)
- Reason
- Timestamp
- IP address
- Correlation ID

## Security

- RBAC enforced server-side
- Secrets masked based on permissions
- High-risk actions require additional approval
- Idempotency keys for external integrations
- All responses include `correlation_id` header
