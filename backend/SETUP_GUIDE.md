# GOTXA Backend - Setup & Deployment Guide

## Project Structure

```
backend/
├── main.py                  # Flask app factory
├── wsgi.py                  # WSGI entry point
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container image definition
├── .env                     # Environment variables
├── app/
│   ├── __init__.py         # Package init
│   ├── models.py           # SQLAlchemy ORM models (12 tables)
│   ├── auth.py             # RBAC & authentication
│   ├── audit.py            # Immutable audit logging
│   ├── api_v1.py           # Core read endpoints (40+ endpoints)
│   └── api_v1_actions.py   # SOAR action endpoints
└── API_ENDPOINTS.md        # Complete API documentation
```

## Quick Start (Local Development)

### 1. Prerequisites
- Python 3.11+
- PostgreSQL 13+
- pip

### 2. Installation

```bash
# Clone/enter backend directory
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb siem_db
createuser siem_user --createdb --password
psql siem_db -c "ALTER USER siem_user CREATEDB;"

# Set DATABASE_URL in .env
# DATABASE_URL=postgresql://siem_user:password@localhost:5432/siem_db
```

### 4. Run Locally

```bash
# Development mode (with auto-reload)
python main.py

# Production mode (with gunicorn)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

### 5. Verify
```bash
# Health check
curl http://localhost:5000/health

# Test API (demo auth with X-User-ID header)
curl -H "X-User-ID: admin" http://localhost:5000/api/overview
```

---

## Docker Deployment

### Build Image

```bash
docker build -t gotxa-backend:latest .
```

### Run Container

```bash
docker run -d \
  --name siem-backend \
  -p 5000:5000 \
  -e DATABASE_URL=postgresql://siem_user:password@postgres:5432/siem_db \
  -e FLASK_ENV=production \
  --network siem-network \
  gotxa-backend:latest
```

### Docker Compose Integration

```yaml
services:
  siem-backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://siem_user:${DB_PASSWORD}@siem-postgres:5432/siem_db
      - FLASK_ENV=production
    depends_on:
      - siem-postgres
    networks:
      - siem-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

---

## API Endpoints

See **API_ENDPOINTS.md** for complete documentation of all 40+ endpoints.

### Quick Examples

**Get Dashboard Overview:**
```bash
curl -H "X-User-ID: admin" http://localhost:5000/api/overview
```

**List Alerts:**
```bash
curl -H "X-User-ID: admin" \
  "http://localhost:5000/api/alerts?severity=critical&page=1"
```

**Create Incident:**
```bash
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"title":"Incident Title","severity":"critical"}' \
  http://localhost:5000/api/incidents
```

**Execute SOAR Playbook:**
```bash
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"action_id":"containment.isolate_host","parameters":{"hostname":"server-01"}}' \
  http://localhost:5000/api/v1/soar/execute
```

---

## Database Schema

### Tables (12 total)

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `users` | User accounts & roles | id, username, role, team_id |
| `teams` | Team organization | id, name, description |
| `alerts` | Security alerts | id, alert_id, severity, status |
| `incidents` | Security incidents | id, incident_id, status, owner_id |
| `tasks` | Incident tasks | id, incident_id, status |
| `evidence` | Incident evidence | id, incident_id, type |
| `playbook_executions` | SOAR playbook runs | id, execution_id, status |
| `audit_events` | Immutable audit trail | id, correlation_id, action |
| `settings` | Configuration | section, key, value |
| `setting_changes` | Setting audit trail | section, key, changed_by_id |
| `reports` | Generated reports | id, report_id, status |

### Relationships

```
User (1) ──→ (many) Alert (assignee)
User (1) ──→ (many) Incident (owner)
User (1) ──→ (many) Team (members)

Incident (1) ──→ (many) Alert
Incident (1) ──→ (many) Task
Incident (1) ──→ (many) Evidence

Alert (1) ──→ (many) AuditEvent
```

---

## Authentication & Authorization

### Authentication Methods

1. **X-User-ID Header (Demo)**
   ```bash
   curl -H "X-User-ID: admin" http://localhost:5000/api/overview
   ```

2. **Bearer Token (Future)**
   ```bash
   curl -H "Authorization: Bearer <jwt-token>" http://localhost:5000/api/overview
   ```

### RBAC Roles

| Role | Permissions | Use Case |
|------|-------------|----------|
| `admin` | All actions | Platform administrators |
| `soc_manager` | Manage alerts/incidents, execute playbooks | Security Operations Center managers |
| `analyst` | Create/edit incidents, view alerts | Security analysts |

### Permissions Matrix

See **API_ENDPOINTS.md** for complete permissions matrix.

---

## Audit Logging

Every mutation is logged with:
- **Correlation ID** - Track related actions across the system
- **Actor** - User performing the action
- **Action** - What was done (e.g., "alert.suppressed")
- **Before/After State** - Change tracking
- **Reason** - Why the action was performed
- **Timestamp** - When it happened

Query audit events:
```bash
curl -H "X-User-ID: admin" \
  "http://localhost:5000/api/audit-events?page=1"
```

---

## Development

### Adding New Endpoints

1. Create route in `app/api_v1.py` or `app/api_v1_actions.py`
2. Use `@authenticate` decorator for auth
3. Use `@require_permission('action.name')` for authorization
4. Use `AuditLogger().log()` for mutations
5. Return `success_response()` or `error_response()`

Example:
```python
@api.route('/new-endpoint', methods=['POST'])
@authenticate
@require_permission('resource.create')
def create_resource():
    try:
        data = request.get_json()
        # ... business logic ...
        audit.log(
            actor=g.user,
            action='resource.created',
            resource_type='Resource',
            resource_id=resource.id,
            reason=data.get('reason', '')
        )
        db.session.commit()
        return success_response({'id': resource.id}, 'Created', 201)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)
```

### Adding New Models

1. Define class in `app/models.py` inheriting from `db.Model`
2. Include audit fields (created_at, updated_at)
3. Add relationships
4. Run `db.create_all()` in `create_app()`

---

## Environment Variables

```bash
# Database connection
DATABASE_URL=postgresql://user:password@host:5432/database

# Flask configuration
FLASK_ENV=production|development
DEBUG=False

# Logging
LOG_LEVEL=INFO

# Optional: API integrations
SLACK_WEBHOOK=https://hooks.slack.com/...
DATADOG_API_KEY=...
```

---

## Monitoring & Health Checks

### Health Check Endpoint
```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-08-14T10:30:45Z",
  "database": "connected"
}
```

### Kubernetes Probe Configuration

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 5
  periodSeconds: 10
```

---

## Troubleshooting

### Database Connection Errors

```bash
# Check connection string
echo $DATABASE_URL

# Test PostgreSQL connection
psql postgresql://user:password@host:5432/database -c "SELECT 1"
```

### Import Errors

```bash
# Verify Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Check imports
python -c "from app.models import db; print('OK')"
```

### Permission Denied Errors

```bash
# Ensure user has correct role
curl -H "X-User-ID: analyst" http://localhost:5000/api/settings
# Should return 403 Forbidden for analyst role
```

---

## Performance Tuning

### Database Optimization
- Add indexes on frequently queried columns (done in models)
- Use `order_by(desc(...))` for paginated results
- Batch operations when possible

### API Response Caching
- Implement Redis cache for `/overview` endpoint
- Cache SOAR action list for 1 hour
- Invalidate cache on mutations

### Connection Pooling
```python
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
}
```

---

## Security Best Practices

1. **Always use HTTPS in production**
2. **Implement JWT token validation** (replace X-User-ID header)
3. **Rotate database credentials** regularly
4. **Enable query parameter validation** for all endpoints
5. **Rate limit** API endpoints
6. **Log sensitive operations** to audit trail
7. **Use environment variables** for secrets (not in code)
8. **Implement CORS** appropriately for your domain

---

## Testing

### Unit Tests
```bash
pip install pytest pytest-mock
pytest tests/
```

### Integration Tests
```bash
pytest tests/integration/ --postgresql
```

### Manual Testing (curl)
See examples in **API_ENDPOINTS.md**

---

## Deployment Checklist

- [ ] Database created and migrations run
- [ ] Environment variables configured
- [ ] HTTPS certificate obtained
- [ ] CORS configured for frontend domain
- [ ] Monitoring/alerting set up
- [ ] Backup strategy defined
- [ ] Health checks passing
- [ ] Load tested with expected traffic
- [ ] Security audit completed
- [ ] Documentation updated
