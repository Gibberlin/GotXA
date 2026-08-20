# GotXA — REST API Specification Report

This document specifies the REST API endpoints exposed by the GotXA Security Operations Platform.

---

## 🔒 Base Configurations & Auth

### Base URL
```
http://localhost:5000/api
```

### Authentication Headers
All endpoints except `/health` and `/api/status` require identity context passed through:
*   **Demo Mode (Header)**: `X-User-ID: <username>` (e.g., `X-User-ID: admin`). Auto-provisions a database user with the specified role.
*   **Production Token (Header)**: `Authorization: Bearer <JWT_TOKEN>`.

---

## 📦 Global Data Wrappers

### 1. Success Data Wrapper
All successful responses return HTTP status code `200` (or `201`/`202` for creations/background tasks) wrapped in a standard JSON block.
```json
{
  "data": {
    "key": "value"
  },
  "message": "Success",
  "timestamp": "2026-08-14T10:30:45.123456"
}
```

### 2. Paginated List Wrapper
For operations returning array items, the response is structured as:
```json
{
  "items": [],
  "total": 100,
  "page": 1,
  "page_size": 25,
  "pages": 4
}
```

### 3. Error Response Wrapper
Failed operations return the appropriate HTTP error code (`400`, `401`, `403`, `404`, `409`, `500`) with details:
```json
{
  "error": {
    "code": "InvalidCredentials",
    "message": "The credentials provided are incorrect.",
    "details": {
      "field": "password"
    }
  }
}
```

---

## 📂 REST Endpoint Groups

### 1. Core Read Analytics & Streams
Overview statistics, logs pagination, and incident summaries.

#### `GET /overview`
Retrieves dashboard summary statistics, priority queues, and network telemetry health statuses.
*   **Access**: Analyst, SOC Manager, Admin
*   **Sample Response**:
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
          { "id": "uuid", "alert_id": "ALERT-001", "title": "Brute Force Attack", "severity": "high" }
        ],
        "source_health": [
          { "source": "firewall-01", "status": "active" }
        ]
      }
    }
    ```

#### `GET /raw-stream`
Cursor-based pagination of raw telemetry collector logs.
*   **Parameters**:
    *   `limit`: Integer (default: 50, max: 250)
    *   `cursor`: String pagination pointer.

---

### 2. Security Alerts Management

#### `GET /alerts`
Lists security alerts with filter parameters.
*   **Parameters**: `severity`, `status`, `assignee`, `page`, `page_size`.

#### `GET /alerts/{id}/investigation`
Retrieves forensic investigation context for a specific alert, including related assets, MITRE ATT&CK techniques, and IOC details.

#### `POST /alerts/bulk-assign`
Assigns multiple alerts to a designated user or analyst division.
*   **Request Body**:
    ```json
    {
      "alert_ids": [12, 13, 14],
      "assignee_id": 4,
      "team_id": 2
    }
    ```

#### `POST /alerts/{id}/suppress`
Suppresses matching future alerts.
*   **Request Body**:
    ```json
    {
      "reason": "False positive testing",
      "duration_seconds": 3600,
      "scope": "alert_rule"
    }
    ```

---

### 3. Incident Triage & Workflows

#### `POST /incidents`
Creates a security incident case.
*   **Request Body**:
    ```json
    {
      "title": "Suspected SQLi Compromise",
      "priority": "high",
      "category": "database_compromise",
      "description": "SQL Injection logs detected on vulnerable-app."
    }
    ```

#### `PATCH /incidents/{id}`
Updates incident status, enforcing validated state transitions.
*   **Valid States**: `open` → `investigating` → `contained` → `resolved` → `closed`.
*   **Transitions Rules**: Closing an incident requires closure notes.
*   **Request Body**:
    ```json
    {
      "status": "contained",
      "notes": "Isolated attacker IP and restarted vulnerable services."
    }
    ```

#### `POST /incidents/{id}/tasks`
Adds a task inside an incident workspace.
*   **Request Body**:
    ```json
    {
      "title": "Extract Nginx Access Logs",
      "assignee_id": 8,
      "due_date": "2026-08-22T12:00:00Z"
    }
    ```

#### `POST /incidents/{id}/merge`
Merges duplicate incidents into a primary parent incident.
*   **Request Body**:
    ```json
    {
      "duplicate_ids": [108, 109]
    }
    ```

#### `POST /incidents/{id}/evidence`
Attaches digital evidence details to an incident case.
*   **Request Body**:
    ```json
    {
      "file_name": "firewall_log.txt",
      "file_type": "text/plain",
      "file_path": "/uploads/forensics/firewall_log.txt"
    }
    ```

---

### 4. SOAR Playbooks & Containment

#### `POST /playbooks/{playbook_id}/executions`
Triggers execution of a response playbook.
*   **High-Risk Actions**: `isolation`, `firewall_block`, or `credential_lock` require manager approval when running in live mode.
*   **Request Body**:
    ```json
    {
      "target": "172.24.0.12",
      "dry_run": false,
      "reason": "Host privilege escalation"
    }
    ```
*   **Response (202 Accepted)**:
    ```json
    {
      "data": {
        "execution_id": 145,
        "status": "pending_approval"
      }
    }
    ```

#### `POST /playbook-executions/{execution_id}/approve`
Approves a pending high-risk containment execution.
*   **Access**: SOC Manager, Admin

#### `POST /playbook-executions/{execution_id}/rollback`
Reverts the network or host containment action.
*   **Request Body**:
    ```json
    {
      "reason": "Investigation completed, host cleared."
    }
    ```

---

### 5. Detection Engineering

#### `POST /detection-rules/{rule_id}/test`
Tests a detection rule schema within a sandbox environment.
*   **Request Body**:
    ```json
    {
      "rule_logic": "grep('SELECT' && 'UNION')",
      "test_logs": "172.24.0.1 - - [21/Aug/2026] 'GET /login?user=admin%27%20UNION...'"
    }
    ```

#### `PATCH /detection-rules/{rule_id}`
Updates a live detection rule, creating a incremented rule version.

---

### 6. Platform Settings & Configurations

#### `PATCH /settings/{section}`
Modifies settings in a configuration category (e.g., `retention`, `auth_policies`). High-risk operations (e.g., changing password policies) trigger multi-approver changesets.
*   **Request Body**:
    ```json
    {
      "retention_days": 90,
      "change_ticket": "CHG-1082",
      "reason": "Audit policy alignment"
    }
    ```

#### `GET /settings/history`
Retrieves dynamic changelogs for settings modifications.

---

### 7. Reporting & Exports

#### `POST /reports`
Triggers async rendering of security compliance and incident PDF reports.
*   **Request Body**:
    ```json
    {
      "type": "NIST_800_61",
      "incident_id": 12,
      "title": "Post Incident Report - Ransomware Containment"
    }
    ```
*   **Response (202 Accepted)**:
    ```json
    {
      "data": {
        "report_id": 89,
        "status": "generating"
      }
    }
    ```

#### `GET /reports/{id}/download`
Serves the rendered PDF document binary file.

---

### 8. Health & System Metrics

#### `GET /health`
Returns direct service connectivity check (bypasses authorization headers).
*   **Response (200 OK)**:
    ```json
    {
      "status": "healthy",
      "services": {
        "database": "connected",
        "redis": "connected"
      }
    }
    ```
