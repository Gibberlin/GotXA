# GotXA — Important Facts & Quick Reference Guide

This document is a distilled executive summary and quick-reference cheat-sheet for developers, security analysts, and administrators working with the GotXA platform.

---

## 🔌 System Ports & Services Map

The following table lists every service, its container name, internal/external ports, and default accessibility in the Docker network (`gotxa-net` with subnet `172.26.0.0/16` or default bridge).

| Service / Container Name | Internal Port | External Port | Access / Route Protocol | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **api-gateway** | `80`, `443` | `80`, `443` | `http://localhost/` | Single entry point reverse proxy (Nginx). |
| **siem-soar-frontend** | `80` | None | Proxied to `/` | SIEM & SOAR React dashboard. |
| **corp-portal-frontend** | `80` | None | Proxied to `/corp` | Corporate login & corporate admin dashboard. |
| **scada-frontend** | `80` | None | Proxied to `/scada` | SCADA Industrial HMI dashboard. |
| **gotxa-backend** | `5000` | `5000` | `http://localhost:5000/api` | Primary Flask REST API. Also proxied to `/api/`. |
| **celery-worker** | None | None | Internal | Celery background worker (PDF report generation). |
| **siem-postgres** | `5432` | `5432` | `localhost:5432` | PostgreSQL relational database. |
| **redis-cache** | `6379` | None | Internal | Redis cache and Celery broker. |
| **corp-portal-agent** | `5001` | `5001` | `http://localhost:5001/` | Vulnerable corporate site (simulates attacks). |
| **ot-scada-gateway** | `5002` | `5002` | `http://localhost:5002/api` | Modbus SCADA polling REST gateway. |
| **ot-plc-refinery-1** | `5003` | `5003` | Modbus TCP (`5003`) | PLC 1 simulation (temperature & pressure). |
| **ot-plc-refinery-2** | `5004` | `5004` | Modbus TCP (`5004`) | PLC 2 simulation (flow rate mixer). |

---

## 🔑 Default Credentials & Authentication

### 1. Web UI & REST API Demo Access (RBAC)
When debugging or integrating the REST API, authenticate by passing the **`X-User-ID`** header. The backend automatically provisions a demo account if it doesn't already exist.

*   **`admin`** role: `X-User-ID: admin` (Full permissions)
*   **`soc_manager`** role: `X-User-ID: soc_manager` (Incident triage + execution, requires escalation approvals for containment)
*   **`analyst`** role: `X-User-ID: analyst` (Read-only alerts/incidents, cannot run playbooks)

### 2. Relational Database Connection (PostgreSQL)
*   **Host**: `localhost` (external) or `siem-postgres` (Docker internal)
*   **Port**: `5432`
*   **Database Name**: `siem_db`
*   **Database User**: `siem_user`
*   **Database Password**: `siem_password_secure`
*   **ORM Connection String**: `postgresql://siem_user:siem_password_secure@siem-postgres:5432/siem_db`

### 3. Vulnerable Corporate Portal (SQLi/RCE Target)
*   **Attacking Target URL**: `http://localhost:5001/login`
*   **Legitimate Username**: `admin@corporate.gotxa`
*   **Legitimate Password**: `admin_password_123`
*   **SQL Injection Bypass (Exploit)**: `' OR 1=1 --` (forces login bypass)

---

## ⚙️ Core Environment Variables

Copy `.env.example` to `.env` in the root folder before starting.

| Environment Variable | Recommended Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://siem_user:siem_password_secure@siem-postgres:5432/siem_db` | PostgreSQL connection string. |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Redis broker URI for Celery. |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` | Redis backend URI for Celery results. |
| `FLASK_ENV` | `production` | Enables or disables production routing/logs. |
| `SOAR_REAL_MODE` | `false` | `false` runs playbooks as dry-run simulation; `true` executes real `iptables`/`docker disconnect` rules. |
| `REPORTS_DIR` | `/app/reports` | Directory where Celery writes PDF reports (mounted volume). |

---

## 📁 Directory Structure Overview

*   `backend/` - Flask API source code, dependency definitions, and docker configs.
    *   `app/` - Core blueprints: `api_v1.py` (read APIs), `api_v1_actions.py` (actions/settings/SOAR), `models.py` (ORM).
*   `frontend/` - React frontend sub-projects.
    *   `siem_dashboard/` - Main SOC platform UI (alerts, incidents, playbooks, logs).
    *   `corp_portal/` - Simulated corporate employee portal.
    *   `scada_dashboard/` - Industrial control SVG gauges.
*   `webservers/` - Nginx proxy configurations for the gateway and dashboards.
*   `pentesting_scripts/` - Attack automation scripts (RCE, brute-force, SQL injection).
*   `vulnerable_app.py` - Flask script running the vulnerable portal simulation.
*   `scada_gateway.py` - Modbus-to-REST polling daemon.
*   `modbus_plc_server.py` - Pymodbus TCP simulators for PLC 1 & 2.
*   `log_collector.py` - File tailing log forwarder.

---

## 🚨 Security Alerts & Playbook Actions Mapping

When an alert is ingested, the engine matches the rule name to a predefined containment playbook.

| Ingested Alert Rule | Severity | Playbook Name | Active Mitigation Action |
| :--- | :--- | :--- | :--- |
| **Brute Force Attempt** | HIGH | `brute_force_ip_block` | **IP Block**: Bans attacker's IP on port 80 via `iptables`. |
| **Brute Force Threshold Exceeded** | HIGH | `brute_force_ip_block`<br>`brute_force_credential_lock` | **Dual Action**: Bans attacker IP + disables/locks username in corporate database. |
| **Critical System Error** | HIGH | `critical_error_restart` | **Service Restart**: Automatically reboots the crashed container. |
| **Network Anomaly Detected** | HIGH | `network_anomaly_block`<br>`network_anomaly_rate_limit` | **Dual Action**: Bans malicious IP + applies Nginx traffic rate-limiting. |
| **Privilege Escalation** | HIGH | `privilege_escalation_isolate` | **Isolate**: Uses Docker socket to disconnect compromised container from the `corp` network. |
| **Service Availability Issue** | MEDIUM | `service_availability_restart` | **Service Restart**: Reboots the unresponsive container. |

---

## 🛠️ Verification & Troubleshooting Commands

### Docker Compose Lifecycle
```bash
# Build and run all services in detached mode
docker-compose up -d --build

# View logs of the backend API
docker-compose logs -f backend

# Stop the entire stack
docker-compose down
```

### Database Administration (CLI)
```bash
# Exec into PostgreSQL container and enter psql shell
docker exec -it siem-postgres psql -U siem_user -d siem_db

# Query total number of alerts and incidents
SELECT status, COUNT(*) FROM alerts GROUP BY status;
SELECT priority, COUNT(*) FROM incidents GROUP BY priority;

# Clear audit logs for a fresh demo run
TRUNCATE TABLE audit_events RESTART IDENTITY CASCADE;
```

### Manual API Smoke Testing
```bash
# 1. Server health check (should return 200)
curl http://localhost:5000/health

# 2. Query SIEM dashboard overview using demo headers
curl -H "X-User-ID: admin" http://localhost:5000/api/overview

# 3. Simulate creating a new incident manually
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"title": "Unauthorized Sudo Access", "priority": "high", "category": "privilege_escalation"}' \
  http://localhost:5000/api/incidents
```
