# GotXA SIEM/SOAR Platform - Complete API Reference

## Overview
GotXA is a production-grade Security Information and Event Management (SIEM) and Security Orchestration, Automation and Response (SOAR) platform. This document provides a complete reference for all REST API endpoints.

**Base URL:** `http://localhost:5000/api`  
**Authentication:** Bearer token (via `X-User-ID` header or `Authorization: Bearer <token>`)

---

## Table of Contents
1. [Core SIEM Endpoints](#core-siem-endpoints)
2. [Alert Management](#alert-management)
3. [Incident Management](#incident-management)
4. [SOAR Automation](#soar-automation)
5. [Access Control & JIT](#access-control--jit)
6. [Settings & Configuration](#settings--configuration)
7. [Reports & Export](#reports--export)
8. [Authentication](#authentication)
9. [Database Query](#database-query)
10. [SCADA/OT Control](#scadaot-control)

---

## CORE SIEM ENDPOINTS

### Overview & Dashboard

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/overview` | GET | Query params (none) | KPIs, charts, alerts, source health | Get dashboard overview metrics and health status |
| `/overview/metrics` | GET | Query params (none) | Active incidents, ingestion rate, critical alerts | Get consolidated SIEM metrics |
| `/dashboard-data` | GET | Query params (none) | Total logs, alerts, critical alerts, hosts | Legacy dashboard endpoint (backward compatible) |
| `/raw-stream` | GET | `limit`, `source`, `category` | Raw log events with timestamps | Stream live logs for real-time dashboard |
| `/data-sources/metrics` | GET | Query params (none) | Source health, ingestion rates, status | Get data source connector health |
| `/recent-activity` | GET | Query params (none) | Recent incidents, alerts, tasks | Get activity feed |

---

## ALERT MANAGEMENT

### List & Retrieve Alerts

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/alerts` | GET | `page`, `page_size`, `severity`, `status`, `assignee` | Paginated alert list with enriched forensics | List all alerts with filtering |
| `/alerts/<alert_id>` | GET | `alert_id` (path) | Alert details, forensic telemetry, related alerts | Get full alert investigation context |
| `/alerts/bulk-assign` | POST | `{ "alert_ids": [...], "assignee_id": "..." }` | Assignment confirmation | Bulk assign alerts to analyst |
| `/alerts/<alert_id>/suppress` | POST | `{ "duration_minutes": 60, "reason": "..." }` | Suppression confirmation | Suppress alert for specified duration |
| `/alerts/<alert_id>/status` | PUT | `{ "status": "open\|acknowledged\|resolved" }` | Status update confirmation | Update alert status in workflow |

---

## INCIDENT MANAGEMENT

### Create & Manage Incidents

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/incidents` | GET | `page`, `page_size`, `status`, `priority` | Paginated incident list | List all incidents with filtering |
| `/incidents` | POST | `{ "title": "...", "severity": "...", "source_alert_ids": [...] }` | New incident with ID | Create incident from alerts |
| `/incidents/<incident_id>` | GET | `incident_id` (path) | Full incident details, timeline, artifacts | Get incident investigation details |
| `/incidents/<incident_id>/status` | PUT | `{ "status": "open\|investigating\|contained\|resolved" }` | Status update confirmation | Update incident lifecycle status |
| `/incidents/<incident_id>/assign` | POST | `{ "owner_id": "...", "team_id": "..." }` | Assignment confirmation | Assign incident to team/analyst |
| `/incidents/<incident_id>/link-alert` | POST | `{ "alert_id": "..." }` | Link confirmation | Link additional alert to incident |
| `/incidents/summary` | GET | Query params (none) | Open tasks, overdue items, post-incident actions | Get incident workflow summary |

---

## SOAR AUTOMATION

### Playbook Execution & Task Management

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/v1/soar/actions` | GET | Query params (none) | Available SOAR actions, playbook list | List all available automation actions |
| `/v1/soar/execute` | POST | `{ "playbook_id": "...", "incident_id": "...", "inputs": {...} }` | Execution confirmation, job_id | Execute SOAR playbook manually |
| `/v1/soar/history` | GET | `page`, `limit`, `status` | Playbook execution history | View past automation executions |
| `/v1/soar/executions` | GET | `page`, `limit`, `playbook_id` | Active/completed playbook runs | List playbook execution records |
| `/playbooks/<playbook_id>/executions` | POST | `{ "incident_id": "...", "inputs": {...} }` | Execution confirmation | Execute specific playbook |
| `/containment-requests` | POST | `{ "type": "network\|asset\|user", "target": "...", "reason": "..." }` | Containment job_id | Request automated containment action |

---

## ACCESS CONTROL & JIT

### Just-In-Time Privilege Management

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/access/jit-sessions` | GET | `page`, `limit`, `status` | JIT session list with expiry | List active JIT privilege sessions |
| `/access/jit-sessions` | POST | `{ "user_id": "...", "privilege_level": "...", "duration_minutes": 60 }` | Session approval + token | Request temporary elevated privileges |
| `/access/review` | GET | Query params (none) | Recent privilege requests, approvals | Review access request audit trail |

---

## SETTINGS & CONFIGURATION

### System Configuration

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/settings` | GET | `page`, `limit` | Current settings by section | Retrieve system configuration |
| `/settings` | PUT | `{ "section": "alerts", "key": "retention_days", "value": 90 }` | Update confirmation | Update system setting |
| `/settings/<section>` | PATCH | `{ "key1": "value1", "key2": "value2" }` | Bulk update confirmation | Update multiple settings in section |
| `/settings/history` | GET | `page`, `limit`, `section` | Settings change audit trail | View configuration change history |
| `/detection-rules/<rule_id>/test` | POST | `{ "test_data": {...} }` | Test result (pass/fail) | Test detection rule against data |
| `/detection-rules/<rule_id>/versions` | GET | `limit` | Rule version history | View rule evolution/changes |

---

## THREAT INTELLIGENCE

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/threat-intelligence/feeds` | GET | Query params (none) | Active threat feeds, last update time | List threat intelligence sources |

---

## REPORTS & EXPORT

### Report Generation & Asset Export

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/reports` | POST | `{ "type": "incident\|alert\|soar", "date_range": {...}, "format": "pdf" }` | Report job_id + download_url | Generate compliance/incident report |
| `/reports/<report_id>` | GET | `report_id` (path) | Report metadata + status | Check report generation status |
| `/reports/<report_id>/download` | GET | `report_id` (path) | Binary PDF file | Download generated report |
| `/assets/export` | GET | `format` (csv/json), `filter` | CSV/JSON asset inventory | Export asset inventory |

---

## AUTHENTICATION

### User Session Management

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/auth/login` | POST | `{ "username": "...", "password": "...", "role": "..." }` | Access token, user info, expiry | Authenticate and get session token |
| `/auth/logout` | POST | Authorization header | Logout confirmation | Revoke session token |
| `/auth/me` | GET | Authorization header | Current user info, session metadata | Get authenticated user profile |
| `/auth/sessions` | GET | Authorization header | List of active sessions | View all active user sessions |

---

## DATABASE QUERY

### Direct Table Access (Admin Only)

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/tables` | GET | Query params (none) | List of available tables with columns | Discover database schema |
| `/tables/<table_name>` | GET | `page`, `limit`, `filter` | Table data with pagination | Query table contents |
| `/tables/<table_name>` | POST | JSON row data | Inserted row ID | Insert new record |
| `/tables/<table_name>` | PUT | `{ "id": "...", "column": "value" }` | Update confirmation | Update table record |
| `/tables/<table_name>` | DELETE | `{ "id": "..." }` | Deletion confirmation | Delete table record |
| `/query` | POST | `{ "sql": "SELECT ... FROM ...", "params": [...] }` | Query result set | Execute custom SQL query (admin) |

---

## SCADA/OT CONTROL

### Industrial Control System Integration

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/v1/scada/control` | POST | `{ "machine_id": "r1_heater", "action": "SET_TEMP", "target_temperature": 75, "operator": "..." }` | Control confirmation, event_id | Send SCADA control command (audited) |
| `/scada/control` | POST | `{ "machine_id": "...", "command": "...", "value": ... }` | Command execution result | Alternative SCADA endpoint |
| `/control` | POST | `{ "target": "plc", "parameter": "...", "value": ... }` | Execution status | Generic control proxy |
| `/modbus` | GET | `device_id`, `registers` | Modbus register values | Read Modbus TCP registers |
| `/modbus/refinery-1` | GET | Query params (none) | Refinery PLC1 telemetry | Get Refinery PLC1 status |
| `/modbus/refinery-2` | GET | Query params (none) | Refinery PLC2 telemetry | Get Refinery PLC2 status |
| `/scada/<path:subpath>` | GET/POST/PUT/DELETE | Proxy request | Proxy response | Generic SCADA gateway |
| `/dashboard-metrics` | GET | Query params (none) | SCADA system KPIs | Get OT/SCADA metrics |

---

## ADMIN & UTILITIES

### Administrative Functions

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/capabilities` | GET | Authorization header | Available actions for current role | Check role-based permissions |
| `/audit-events` | GET | `page`, `limit`, `action`, `resource_type` | Audit trail records | View system audit log |
| `/saved-views` | GET | Query params (none) | User's saved dashboard views | List saved dashboard configurations |
| `/saved-views` | POST | `{ "name": "...", "filters": {...} }` | View saved confirmation | Save custom dashboard view |
| `/dashboard-metrics` | GET | Query params (none) | System health, performance metrics | Get system dashboard metrics |

---

## ADDITIONAL ENDPOINTS

### Extended Operations

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/login` | POST | `{ "username": "...", "password": "..." }` | Session token | Simple login (corporate portal) |
| `/health` | GET | Query params (none) | `{"status": "healthy"}` | System health check |
| `/tasks` | GET | `page`, `status`, `assigned_to` | Task list | List SOAR tasks |
| `/tasks/<task_id>` | GET | `task_id` (path) | Task details | Get task details |
| `/tasks/<task_id>` | PUT | `{ "status": "complete" }` | Update confirmation | Mark task complete |

---

## Response Format

### Success Response
```json
{
  "data": {
    "id": "...",
    "status": "open",
    ...
  },
  "timestamp": "2026-09-09T21:22:00Z"
}
```

### Error Response
```json
{
  "error": {
    "code": "NotFound",
    "message": "Alert not found",
    "details": {}
  },
  "timestamp": "2026-09-09T21:22:00Z"
}
```

### List Response (Paginated)
```json
{
  "data": [...],
  "total": 100,
  "page": 1,
  "page_size": 25,
  "pages": 4
}
```

---

## Authentication Headers

All endpoints require authentication via one of:

1. **Bearer Token:**
```bash
Authorization: Bearer <token>
```

2. **User ID Header:**
```bash
X-User-ID: admin
```

3. **Session Cookie:**
```
Cookie: session_id=<token>
```

---

## Common Query Parameters

| Parameter | Type | Example | Description |
|-----------|------|---------|-------------|
| `page` | int | `1` | Page number (1-indexed) |
| `page_size` | int | `25` | Records per page (max 100) |
| `limit` | int | `50` | Alias for page_size |
| `sort` | string | `-created_at` | Sort field (- for descending) |
| `filter` | string | `status=open` | Filter condition |
| `status` | string | `open\|investigating\|resolved` | Filter by status |
| `severity` | string | `critical\|high\|medium\|low\|info` | Filter by severity |
| `assignee` | string | `user_id` | Filter by assignee |

---

## Example Usage

### Get Dashboard Metrics
```bash
curl -H "X-User-ID: admin" http://localhost:5000/api/overview/metrics
```

### List Alerts
```bash
curl -H "X-User-ID: admin" \
  "http://localhost:5000/api/alerts?page=1&page_size=25&severity=critical"
```

### Create Incident
```bash
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"title":"Security Incident","severity":"high","source_alert_ids":["alert-1"]}' \
  http://localhost:5000/api/incidents
```

### Execute SOAR Playbook
```bash
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"playbook_id":"pb-001","incident_id":"inc-123","inputs":{}}' \
  http://localhost:5000/api/v1/soar/execute
```

### Update Alert Status
```bash
curl -X PUT -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"status":"acknowledged"}' \
  http://localhost:5000/api/alerts/alert-123/status
```

---

## Role-Based Access Control

### Admin
- Full access to all endpoints
- Can modify settings, rules, and configurations
- Can execute any SOAR action

### SOC Manager
- Access to alerts and incidents
- Can assign incidents to teams
- Can execute approved SOAR playbooks
- Can view audit logs

### Analyst
- Can view assigned alerts and incidents
- Can create tasks
- Can execute SOAR tasks
- Cannot modify settings

### Read-Only
- Can view all data
- Cannot create or modify anything
- Cannot execute any actions

---

## Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| NotFound | 404 | Resource not found |
| Forbidden | 403 | Access denied |
| Unauthorized | 401 | Authentication required |
| BadRequest | 400 | Invalid request format |
| InternalError | 500 | Server error |
| Conflict | 409 | Resource conflict |
| RateLimited | 429 | Too many requests |

---

## Performance & Limits

- **Max page size:** 100 records
- **Max query timeout:** 30 seconds
- **Rate limit:** 1000 requests/minute per user
- **Response timeout:** 60 seconds
- **Concurrent connections:** 100 per user

---

## WebHooks & Events

Endpoints automatically trigger:
- Alert creation → SOAR correlation checks
- Incident creation → Playbook execution triggers
- Status changes → Audit logging
- SCADA commands → Security event generation

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-09-09 | Initial release (60+ endpoints) |
| 1.0.1 | 2026-09-10 | Added SCADA/OT endpoints |
| 1.0.2 | 2026-09-11 | Added JIT access endpoints |

---

## Support & Documentation

- **API Status:** http://localhost:5000/health
- **Schema Discovery:** http://localhost:5000/api/tables
- **Live API Explorer:** http://localhost/api-docs

---

**Last Updated:** September 9, 2026  
**Platform:** GotXA SIEM/SOAR v1.0  
**Status:** Production Ready ✅
