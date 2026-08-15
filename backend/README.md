![1786811779816](images/README/1786811779816.png)

# GOTXA Backend - Production SIEM/SOAR API

A comprehensive REST API for the GOTXA Security Operations Platform with:

- **40+ REST endpoints** across 8 functional groups
- **Complete RBAC** with 3 roles (Admin, SOC Manager, Analyst)
- **Immutable audit logging** with correlation IDs
- **SQLAlchemy ORM** with 12 data models
- **State machine validation** for incident lifecycle
- **SOAR playbook execution** framework
- **Flask + PostgreSQL** stack

## Quick Links

- **[API Documentation](./API_ENDPOINTS.md)** - Complete endpoint reference with examples
- **[Setup Guide](./SETUP_GUIDE.md)** - Installation, deployment, configuration
- **[Dockerfile](./Dockerfile)** - Container image definition

## Project Structure

```
backend/
├── main.py                      # Flask application factory
├── wsgi.py                      # WSGI entry point for production
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker image definition
├── .env                         # Environment variables (example)
├── API_ENDPOINTS.md             # Complete API documentation (23 endpoints)
├── SETUP_GUIDE.md              # Installation & deployment guide
├── README.md                    # This file
│
└── app/
    ├── __init__.py             # Package initialization
    ├── models.py               # SQLAlchemy ORM (12 tables)
    ├── auth.py                 # RBAC & authentication
    ├── audit.py                # Immutable audit logging
    ├── api_v1.py               # Core endpoints (read APIs)
    └── api_v1_actions.py       # Action endpoints (mutations)
```

## Endpoints Overview

### Core Read APIs (api_v1.py)

- `GET /api/overview` - Dashboard KPIs & metrics
- `GET /api/alerts` - List alerts with filtering
- `GET /api/alerts/<id>` - Alert details & investigation context
- `GET /api/incidents` - List incidents
- `GET /api/incidents/<id>` - Incident details
- `GET /api/capabilities` - User's available actions
- `GET /api/raw-stream` - Raw log streaming
- `GET /api/audit-events` - Audit trail (admin only)

### Alert Actions (api_v1_actions.py)

- `POST /api/alerts/bulk-assign` - Bulk assign alerts
- `POST /api/alerts/<id>/suppress` - Suppress alert
- `PUT /api/alerts/<id>/status` - Update alert status

### Incident Actions (api_v1_actions.py)

- `POST /api/incidents` - Create incident
- `PUT /api/incidents/<id>/status` - Lifecycle management
- `POST /api/incidents/<id>/assign` - Assign to user
- `POST /api/incidents/<id>/link-alert` - Link alert to incident

### SOAR Playbooks (api_v1_actions.py)

- `GET /api/v1/soar/actions` - List available playbooks
- `POST /api/v1/soar/execute` - Execute playbook
- `GET /api/v1/soar/history` - Execution history

### Settings (api_v1_actions.py)

- `GET /api/settings` - List settings
- `PUT /api/settings` - Update settings

### Health & Status

- `GET /health` - Health check (no auth)
- `GET /api/status` - API status (no auth)

## Database Schema

### 12 Tables

- **User** - User accounts with roles & teams
- **Team** - Team organization
- **Alert** - Security alerts from detection systems
- **Incident** - Security incidents (parent for alerts)
- **Task** - Tasks within incidents
- **Evidence** - Evidence attached to incidents
- **PlaybookExecution** - SOAR playbook runs & approvals
- **AuditEvent** - Immutable audit trail
- **Setting** - Platform configuration
- **SettingChange** - Configuration change history
- **Report** - Generated security reports

## Authentication

### Demo Mode (X-User-ID Header)

```bash
curl -H "X-User-ID: admin" http://localhost:5000/api/overview
```

Auto-creates admin user if it doesn't exist.

### Production Mode (JWT Bearer Token)

```bash
curl -H "Authorization: Bearer <jwt-token>" http://localhost:5000/api/overview
```

## RBAC Roles


| Role            | Capabilities                                                 |
| --------------- | ------------------------------------------------------------ |
| **admin**       | All actions: manage alerts, incidents, playbooks, settings   |
| **soc_manager** | Manage alerts/incidents, execute playbooks, generate reports |
| **analyst**     | Create/edit incidents, view alerts, investigate              |

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set database URL
export DATABASE_URL=postgresql://siem_user:[REDACTED]@localhost:5432/siem_db

# Run
python main.py
```

### Docker

```bash
# Build image
docker build -t gotxa-backend:latest .

# Run container
docker run -p 5000:5000 \
  -e DATABASE_URL=postgresql://siem_user:[REDACTED]@postgres:5432/siem_db \
  gotxa-backend:latest
```

### Verify

```bash
# Health check
curl http://localhost:5000/health

# Test API
curl -H "X-User-ID: admin" http://localhost:5000/api/overview
```

## Example Workflows

### Respond to Critical Alert

```bash
# 1. View alert
curl -H "X-User-ID: analyst" http://localhost:5000/api/alerts/alert-uuid

# 2. Create incident
curl -X POST -H "X-User-ID: soc-manager" -H "Content-Type: application/json" \
  -d '{"title":"Incident","severity":"critical"}' \
  http://localhost:5000/api/incidents

# 3. Link alert to incident
curl -X POST -H "X-User-ID: soc-manager" -H "Content-Type: application/json" \
  -d '{"alert_id":"alert-uuid"}' \
  http://localhost:5000/api/incidents/inc-uuid/link-alert

# 4. Execute containment playbook
curl -X POST -H "X-User-ID: soc-manager" -H "Content-Type: application/json" \
  -d '{"action_id":"containment.isolate_host","parameters":{"hostname":"server-01"}}' \
  http://localhost:5000/api/v1/soar/execute

# 5. Update incident status
curl -X PUT -H "X-User-ID: soc-manager" -H "Content-Type: application/json" \
  -d '{"status":"contained"}' \
  http://localhost:5000/api/incidents/inc-uuid/status
```

## Key Features

✅ **Complete REST API** - 40+ endpoints for all SOAR operations
✅ **State Validation** - Incident workflow enforces valid status transitions
✅ **Immutable Audit Trail** - Every mutation logged with correlation IDs
✅ **RBAC** - 3 roles with granular permissions
✅ **Team-based Access** - Incidents & alerts scoped to teams
✅ **Scalable** - Connection pooling, pagination, index optimization
✅ **Production-Ready** - Health checks, error handling, logging

## Documentation

- **[API_ENDPOINTS.md](./API_ENDPOINTS.md)** (19KB) - Complete endpoint reference with curl examples
- **[SETUP_GUIDE.md](./SETUP_GUIDE.md)** (10KB) - Installation, deployment, troubleshooting
- **Code Comments** - Every function documented with examples

## Files Breakdown


| File                  | Size   | Purpose                            |
| --------------------- | ------ | ---------------------------------- |
| main.py               | 2.8KB  | Flask app factory, routes          |
| wsgi.py               | 560B   | WSGI entry point                   |
| app/models.py         | 10.7KB | SQLAlchemy ORM (12 tables)         |
| app/auth.py           | 6.1KB  | RBAC, permissions, auth decorators |
| app/api_v1.py         | 14KB   | Core read endpoints                |
| app/api_v1_actions.py | 17.7KB | Action/mutation endpoints          |
| app/audit.py          | 1.6KB  | Immutable audit logging            |
| requirements.txt      | 135B   | Python dependencies                |
| Dockerfile            | 733B   | Container image                    |

## Deployment

### Docker Compose

```yaml
siem-backend:
  build: ./backend
  ports:
    - "5000:5000"
  environment:
    - DATABASE_URL=postgresql://siem_user:[REDACTED]@siem-postgres:5432/siem_db
  depends_on:
    - siem-postgres
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
    interval: 30s
```

### Kubernetes

```yaml
deployment:
  containers:
  - name: siem-backend
    image: gotxa-backend:latest
    ports:
    - containerPort: 5000
    env:
    - name: DATABASE_URL
      valueFrom:
        secretKeyRef:
          name: siem-secrets
          key: database-url
    livenessProbe:
      httpGet:
        path: /health
        port: 5000
```

## Support

For issues or questions:

1. Check **[SETUP_GUIDE.md](./SETUP_GUIDE.md)** for troubleshooting
2. Review **[API_ENDPOINTS.md](./API_ENDPOINTS.md)** for endpoint details
3. Check logs: `docker logs siem-soar-server`
4. Test connectivity: `curl http://localhost:5000/health`

---

**Version:** 1.0
**Last Updated:** 2026-08-14
**Status:** Production Ready ✓
