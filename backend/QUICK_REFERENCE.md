# Quick Reference - GOTXA Backend

## 🚀 Start Backend (30 seconds)

```bash
cd backend
python main.py
# OR with docker
docker build -t backend . && docker run -p 5000:5000 -e DATABASE_URL=... backend
```

**Verify:** `curl http://localhost:5000/health`

---

## 📚 Documentation

| File | Purpose | Read Time |
|------|---------|-----------|
| **README.md** | Package overview | 5 min |
| **API_ENDPOINTS.md** | All 23 endpoints + examples | 20 min |
| **SETUP_GUIDE.md** | Installation & deployment | 10 min |
| **TESTING_GUIDE.md** | Test all endpoints | 15 min |
| **FRONTEND_INTEGRATION.md** | Connect React frontend | 20 min |
| **DEPLOYMENT_PACKAGE.md** | This complete package | 10 min |

---

## 🔗 Key Endpoints (Copy-Paste)

### Overview (Dashboard)
```bash
curl -H "X-User-ID: admin" http://localhost:5000/api/overview
```

### Alerts
```bash
# List
curl -H "X-User-ID: admin" \
  "http://localhost:5000/api/alerts?severity=critical&page=1"

# Bulk assign
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"alert_ids":["id1","id2"],"assignee_id":"user-id"}' \
  http://localhost:5000/api/alerts/bulk-assign
```

### Incidents
```bash
# Create
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"title":"Incident","severity":"critical"}' \
  http://localhost:5000/api/incidents

# Update status
curl -X PUT -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"status":"investigating"}' \
  http://localhost:5000/api/incidents/inc-id/status
```

### SOAR Playbooks
```bash
# List actions
curl -H "X-User-ID: admin" http://localhost:5000/api/v1/soar/actions

# Execute
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"action_id":"containment.isolate_host","parameters":{"hostname":"server-01"}}' \
  http://localhost:5000/api/v1/soar/execute
```

---

## 🔐 Authentication

**Header:** `X-User-ID: admin` (demo)

**Roles:** admin, soc_manager, analyst

**Permissions:** See API_ENDPOINTS.md for full matrix

---

## 📊 23 Core Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/overview` | Dashboard KPIs |
| GET | `/api/alerts` | List alerts |
| GET | `/api/alerts/<id>` | Alert details |
| POST | `/api/alerts/bulk-assign` | Assign alerts |
| POST | `/api/alerts/<id>/suppress` | Suppress alert |
| PUT | `/api/alerts/<id>/status` | Change status |
| GET | `/api/incidents` | List incidents |
| GET | `/api/incidents/<id>` | Incident details |
| POST | `/api/incidents` | Create incident |
| PUT | `/api/incidents/<id>/status` | Change status |
| POST | `/api/incidents/<id>/assign` | Assign owner |
| POST | `/api/incidents/<id>/link-alert` | Link alert |
| GET | `/api/v1/soar/actions` | List playbooks |
| POST | `/api/v1/soar/execute` | Execute playbook |
| GET | `/api/v1/soar/history` | Execution history |
| GET | `/api/settings` | List settings |
| PUT | `/api/settings` | Update settings |
| GET | `/api/audit-events` | Audit trail |
| GET | `/api/capabilities` | User permissions |
| GET | `/api/raw-stream` | Log streaming |
| GET | `/health` | Health check |
| GET | `/api/status` | API status |

---

## 💾 Files

```
backend/
├── app/
│   ├── models.py (12 tables)
│   ├── auth.py (RBAC)
│   ├── api_v1.py (read endpoints)
│   ├── api_v1_actions.py (action endpoints)
│   └── audit.py (logging)
├── main.py (Flask app)
├── wsgi.py (production)
├── requirements.txt
├── Dockerfile
└── Documentation (6 files, 61.8KB)
```

---

## ⚙️ Environment

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/siem_db

# Optional
FLASK_ENV=production
DEBUG=False
LOG_LEVEL=INFO
```

---

## 🧪 Quick Test Script

```bash
#!/bin/bash
# Test all key endpoints

echo "=== Health ===" && curl http://localhost:5000/health

echo "=== Overview ===" && curl -H "X-User-ID: admin" http://localhost:5000/api/overview

echo "=== Alerts ===" && curl -H "X-User-ID: admin" http://localhost:5000/api/alerts

echo "=== Create Incident ===" && curl -X POST -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","severity":"high"}' \
  http://localhost:5000/api/incidents

echo "=== SOAR Actions ===" && curl -H "X-User-ID: admin" \
  http://localhost:5000/api/v1/soar/actions

echo "=== Audit Events ===" && curl -H "X-User-ID: admin" \
  http://localhost:5000/api/audit-events
```

---

## 🔄 Status Transitions (Incident Lifecycle)

```
open ──→ investigating
investigating ──→ contained
contained ──→ resolved
resolved ──→ closed
(any state) ──→ closed
```

Return 409 Conflict on invalid transitions.

---

## 🛠️ Database

**Tables:** 12
**Connections:** Pooled
**Indexes:** On foreign keys & query columns
**Audit:** Every mutation logged

---

## 🚨 Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Missing X-User-ID | Add header |
| 403 Forbidden | Wrong role | Check permissions |
| 404 Not Found | Resource doesn't exist | Check ID |
| 409 Conflict | Invalid state transition | Check SETUP_GUIDE.md |
| 500 Internal Error | Database issue | Check logs |

---

## 📊 Response Format

```json
{
  "data": { /* response */ },
  "message": "Success",
  "timestamp": "2026-08-14T10:30:45Z"
}
```

---

## 🐳 Docker Commands

```bash
# Build
docker build -t gotxa-backend .

# Run
docker run -p 5000:5000 \
  -e DATABASE_URL=postgresql://... \
  gotxa-backend

# Logs
docker logs -f <container>

# Test
docker exec <container> curl localhost:5000/health
```

---

## 📦 Dependencies

```
Flask==3.1.3
Flask-CORS==4.0.0
Flask-SQLAlchemy==3.1.1
SQLAlchemy==2.0.36
psycopg2-binary==2.9.9
python-dotenv==1.0.0
gunicorn==21.2.0
```

Install: `pip install -r requirements.txt`

---

## 🎯 Integration Checklist

- [ ] Backend running on port 5000
- [ ] Database connected
- [ ] Health check passes
- [ ] Test all endpoints
- [ ] Update frontend API calls
- [ ] Connect SOAR actions to UI
- [ ] Test incident workflow
- [ ] Verify audit logging
- [ ] Test permissions (403 errors)
- [ ] Deploy to production

---

## 📞 Where to Find Help

- **API details** → API_ENDPOINTS.md
- **Setup issues** → SETUP_GUIDE.md
- **Testing** → TESTING_GUIDE.md
- **React integration** → FRONTEND_INTEGRATION.md
- **Complete guide** → DEPLOYMENT_PACKAGE.md

---

## 💡 Pro Tips

1. **Use API service** - Create shared `api.js` for all backend calls
2. **Cache /overview** - Update every 30s, not on every render
3. **Batch operations** - Use bulk-assign for multiple alerts
4. **Add retry logic** - Network errors in production
5. **Monitor 409 errors** - Invalid state transitions indicate data issues
6. **Use correlation IDs** - Track related actions in audit trail

---

## 🎓 Example: Full Workflow

```bash
# 1. Get critical alert
ALERT=$(curl -s -H "X-User-ID: admin" \
  "http://localhost:5000/api/alerts?severity=critical&page_size=1" | jq '.data.items[0]')
ALERT_ID=$(echo $ALERT | jq -r '.id')

# 2. Create incident
INC=$(curl -s -X POST -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"From Alert\",\"severity\":\"critical\"}" \
  http://localhost:5000/api/incidents)
INC_ID=$(echo $INC | jq -r '.data.id')

# 3. Link alert
curl -X POST -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d "{\"alert_id\":\"$ALERT_ID\"}" \
  http://localhost:5000/api/incidents/$INC_ID/link-alert

# 4. Execute playbook
curl -X POST -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{"action_id":"containment.isolate_host","parameters":{"hostname":"server-01"}}' \
  http://localhost:5000/api/v1/soar/execute

# 5. Update status
curl -X PUT -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{"status":"contained"}' \
  http://localhost:5000/api/incidents/$INC_ID/status
```

---

**Last Updated:** 2026-08-14  
**Status:** ✅ Production Ready
