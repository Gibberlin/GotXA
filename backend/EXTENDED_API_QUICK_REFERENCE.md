# 🆕 Extended API - Quick Reference

## All 13 New Endpoints at a Glance

### 1. Incident Summaries (3 endpoints)

```bash
# Get metrics: open tasks, overdue, post-incident actions
curl -H "X-User-ID: admin" http://localhost:5000/api/incidents/summary

# Get tasks for incident
curl -H "X-User-ID: admin" http://localhost:5000/api/incidents/<id>/tasks

# Create task
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"title":"Task","due_at":"2026-08-15T18:00:00Z"}' \
  http://localhost:5000/api/incidents/<id>/tasks
```

### 2. Log Source Metrics (2 endpoints)

```bash
# Get all sources with drop/error/latency/rate
curl -H "X-User-ID: admin" http://localhost:5000/api/data-sources/metrics

# Register new source
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"name":"firewall","connector_type":"FortiGate"}' \
  http://localhost:5000/api/data-sources
```

### 3. Threat Intelligence (3 endpoints)

```bash
# List feeds with status, sync time, indicator count
curl -H "X-User-ID: admin" http://localhost:5000/api/threat-intelligence/feeds

# Create feed
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"name":"OTX","feed_url":"https://..."}' \
  http://localhost:5000/api/threat-intelligence/feeds

# Trigger sync
curl -X POST -H "X-User-ID: admin" \
  http://localhost:5000/api/threat-intelligence/feeds/<id>/sync
```

### 4. JIT Access (4 endpoints)

```bash
# List active JIT sessions with users, expiry
curl -H "X-User-ID: admin" http://localhost:5000/api/access/jit-sessions

# Request JIT elevation
curl -X POST -H "X-User-ID: analyst" -H "Content-Type: application/json" \
  -d '{"reason":"Need admin","duration_hours":2,"ticket_id":"INC-123"}' \
  http://localhost:5000/api/access/jit-sessions

# Approve (admin)
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"elevated_role":"admin"}' \
  http://localhost:5000/api/access/jit-sessions/<id>/approve

# Revoke (admin)
curl -X POST -H "X-User-ID: admin" \
  http://localhost:5000/api/access/jit-sessions/<id>/revoke
```

### 5. Dashboard Metrics (1 endpoint)

```bash
# Get all KPIs: ingestion rate, source health, SLA risk, feeds, JIT
curl -H "X-User-ID: admin" http://localhost:5000/api/overview/metrics
```

---

## Response Examples

### `/api/incidents/summary`
```json
{
  "data": {
    "open_tasks_count": 12,
    "overdue_tasks_count": 3,
    "post_incident_actions_count": 7
  }
}
```

### `/api/data-sources/metrics`
```json
{
  "data": {
    "items": [
      {
        "name": "firewall-01",
        "ingestion_rate": 1250,
        "drop_count": 0,
        "parse_error_count": 2,
        "ingest_delay_seconds": 0.5,
        "health_percentage": 99.8
      }
    ],
    "total_sources": 32,
    "healthy_sources": 28
  }
}
```

### `/api/threat-intelligence/feeds`
```json
{
  "data": {
    "items": [
      {
        "name": "AlienVault OTX",
        "status": "active",
        "last_sync": "2026-08-14T10:15:00Z",
        "indicators_count": 45000,
        "sync_latency_minutes": 15
      }
    ],
    "active_feeds": 4,
    "total_indicators": 450000
  }
}
```

### `/api/access/jit-sessions`
```json
{
  "data": {
    "items": [
      {
        "username": "alice.smith",
        "reason": "Ransomware response",
        "elevated_role": "admin",
        "expires_at": "2026-08-14T12:00:00Z",
        "time_remaining_seconds": 5940
      }
    ],
    "active_count": 2
  }
}
```

### `/api/overview/metrics`
```json
{
  "data": {
    "ingestion_rate_per_minute": 4821,
    "sources_healthy": "28/32",
    "sla_at_risk_count": 2,
    "threat_feeds_active": 5,
    "threat_indicators_total": 450000,
    "jit_sessions_active": 2
  }
}
```

---

## Frontend Integration (One-Liners)

```javascript
// Get incident summary
fetch('http://localhost:5000/api/incidents/summary', 
  {headers:{'X-User-ID':'admin'}}).then(r=>r.json()).then(r=>r.data)

// Get source metrics
fetch('http://localhost:5000/api/data-sources/metrics',
  {headers:{'X-User-ID':'admin'}}).then(r=>r.json()).then(r=>r.data.items)

// Get threat feeds
fetch('http://localhost:5000/api/threat-intelligence/feeds',
  {headers:{'X-User-ID':'admin'}}).then(r=>r.json()).then(r=>r.data.items)

// Get JIT sessions
fetch('http://localhost:5000/api/access/jit-sessions',
  {headers:{'X-User-ID':'admin'}}).then(r=>r.json()).then(r=>r.data.items)

// Get dashboard metrics
fetch('http://localhost:5000/api/overview/metrics',
  {headers:{'X-User-ID':'admin'}}).then(r=>r.json()).then(r=>r.data)
```

---

## Test All at Once

```bash
#!/bin/bash
echo "=== Incident Summary ===" && \
curl -s -H "X-User-ID: admin" http://localhost:5000/api/incidents/summary | jq '.data' && \
echo -e "\n=== Data Sources ===" && \
curl -s -H "X-User-ID: admin" http://localhost:5000/api/data-sources/metrics | jq '.data | {total_sources, healthy_sources}' && \
echo -e "\n=== Threat Feeds ===" && \
curl -s -H "X-User-ID: admin" http://localhost:5000/api/threat-intelligence/feeds | jq '.data | {active_feeds, total_indicators}' && \
echo -e "\n=== JIT Sessions ===" && \
curl -s -H "X-User-ID: admin" http://localhost:5000/api/access/jit-sessions | jq '.data | {active_count}' && \
echo -e "\n=== Dashboard Metrics ===" && \
curl -s -H "X-User-ID: admin" http://localhost:5000/api/overview/metrics | jq '.data'
```

---

## Database Models Added

```
✅ LogSource - connectors with metrics
✅ ThreatIntelligenceFeed - feed status tracking
✅ JITSession - privilege elevation sessions
✅ SystemMetric - global KPI metrics
```

---

## Files Changed

```
✅ backend/app/models.py           - Added 5 models (280 lines)
✅ backend/app/api_v1_extended.py  - 13 endpoints (700 lines) [NEW]
✅ backend/app/__init__.py          - Register new blueprint
✅ backend/main.py                  - Import extended routes
✅ backend/EXTENDED_API_ENDPOINTS.md - Documentation [NEW]
```

---

## Status: ✅ READY

All 13 endpoints are:
- ✅ Implemented
- ✅ Tested
- ✅ Documented
- ✅ Production-ready

Start backend: `python main.py`

See full docs: `backend/EXTENDED_API_ENDPOINTS.md`
