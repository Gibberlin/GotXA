# GOTXA Multi-Server Deployment Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY (Nginx)                        │
│                      Port 80 / 443                              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Routes:                                                  │  │
│  │  /         → SIEM/SOAR Frontend (port 3001)             │  │
│  │  /corp     → Corp Portal Frontend (port 3002)           │  │
│  │  /scada    → SCADA Dashboard (port 3003)                │  │
│  │  /api/     → Backend API (port 5000)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
           ↓                    ↓                      ↓
    ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
    │   SIEM/     │      │    CORP     │      │   SCADA     │
    │   SOAR      │      │   PORTAL    │      │ DASHBOARD   │
    │ Frontend    │      │  Frontend   │      │  Frontend   │
    │ (Nginx)     │      │  (Nginx)    │      │   (Nginx)   │
    │ Port 80     │      │  Port 80    │      │   Port 80   │
    └─────────────┘      └─────────────┘      └─────────────┘
                                    ↓
                          ┌──────────────────┐
                          │  Backend API     │
                          │  (Flask/Python)  │
                          │  Port 5000       │
                          └──────────────────┘
                                    ↓
                          ┌──────────────────┐
                          │   PostgreSQL     │
                          │   Database       │
                          │  Port 5432       │
                          └──────────────────┘
```

## Directory Structure

```
GotXA/
├── backend/                               # Backend API service
│   ├── app/
│   │   ├── models.py
│   │   ├── auth.py
│   │   ├── api_v1.py
│   │   ├── api_v1_actions.py
│   │   └── api_v1_extended.py
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                              # Frontend applications
│   ├── siem_dashboard/
│   │   ├── src/
│   │   ├── package.json
│   │   └── vite.config.js
│   ├── corp_portal/
│   │   ├── src/
│   │   ├── package.json
│   │   └── vite.config.js
│   └── scada_dashboard/
│       ├── src/
│       ├── package.json
│       └── vite.config.js
│
├── webservers/                            # Dedicated web servers
│   ├── api-gateway/
│   │   ├── Dockerfile
│   │   └── nginx.conf
│   ├── siem-soar-frontend/
│   │   ├── Dockerfile
│   │   └── nginx.conf
│   ├── corp-portal-frontend/
│   │   ├── Dockerfile
│   │   └── nginx.conf
│   └── scada-frontend/
│       ├── Dockerfile
│       └── nginx.conf
│
└── docker-compose.yml                    # Orchestration
```

---

## Services Overview

### 1. API Gateway (Reverse Proxy)
**Port:** 80/443  
**Role:** Route traffic to appropriate services  
**Technology:** Nginx  

**Routing:**
- `/` → SIEM/SOAR Frontend
- `/corp` → Corp Portal Frontend
- `/scada` → SCADA Dashboard Frontend
- `/api/` → Backend API Server

---

### 2. SIEM/SOAR Frontend
**Port:** 3001 (internal) / 80 (via gateway)  
**URL:** `http://localhost/`  
**Role:** Main dashboard for security operations  
**Technology:** React + Vite + Nginx  

---

### 3. Corp Portal Frontend
**Port:** 3002 (internal) / 80 (via gateway)  
**URL:** `http://localhost/corp`  
**Role:** Corporate login & admin dashboard  
**Technology:** React + Vite + Nginx  

---

### 4. SCADA Dashboard Frontend
**Port:** 3003 (internal) / 80 (via gateway)  
**URL:** `http://localhost/scada`  
**Role:** Real-time industrial HMI  
**Technology:** React + Vite + Nginx  

---

### 5. Backend API Server
**Port:** 5000  
**URL:** `http://localhost/api/`  
**Role:** REST API for all frontend apps  
**Technology:** Flask + Python + SQLAlchemy  

**Endpoints:**
- 36+ REST API endpoints
- RBAC authentication
- Immutable audit logging
- Database integration

---

### 6. PostgreSQL Database
**Port:** 5432 (internal) / 5432 (exposed for dev)  
**Role:** Persistent data storage  
**Database:** `siem_db`  
**User:** `siem_user`  

---

## Quick Start

### 1. Prerequisites
- Docker & Docker Compose installed
- 4GB RAM minimum
- Ports 80, 443 available

### 2. Clone/Navigate to Project
```bash
cd C:\Users\RJDhu\OneDrive\Desktop\Project\GotXA
```

### 3. Set Environment
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your secrets (passwords, JWT secrets)
# Note: [REDACTED] placeholders need real values in production
```

### 4. Build All Services
```bash
docker-compose build
```

### 5. Start All Services
```bash
docker-compose up -d
```

### 6. Verify All Services Running
```bash
docker-compose ps

# Output should show all healthy:
# api-gateway           running  0.0.0.0:80->80/tcp
# siem-soar-frontend    running
# corp-portal-frontend  running
# scada-frontend        running
# backend              running  0.0.0.0:5000->5000/tcp
# siem-postgres         running  0.0.0.0:5432->5432/tcp
```

### 7. Access Applications

| Application | URL | Default Login |
|-------------|-----|---|
| SIEM/SOAR Dashboard | http://localhost/ | admin / (X-User-ID) |
| Corp Portal | http://localhost/corp | admin / (X-User-ID) |
| SCADA Dashboard | http://localhost/scada | admin / (X-User-ID) |
| Backend API | http://localhost/api/overview | Header: X-User-ID: admin |

---

## Testing

### Health Checks
```bash
# Gateway health
curl http://localhost/health

# Individual services
curl http://localhost/api/health           # Backend
curl http://localhost:3001/health         # SIEM (internal)
curl http://localhost:3002/health         # Corp Portal (internal)
curl http://localhost:3003/health         # SCADA (internal)
```

### API Endpoints
```bash
# Get overview metrics
curl -H "X-User-ID: admin" http://localhost/api/overview

# Get incidents
curl -H "X-User-ID: admin" http://localhost/api/incidents

# Get threat feeds
curl -H "X-User-ID: admin" http://localhost/api/threat-intelligence/feeds
```

### Frontend Tests
```bash
# Open in browser
http://localhost/              # SIEM Dashboard
http://localhost/corp          # Corp Portal
http://localhost/scada         # SCADA Dashboard
```

---

## Logs

### View All Logs
```bash
docker-compose logs -f
```

### View Specific Service Logs
```bash
docker-compose logs -f backend
docker-compose logs -f api-gateway
docker-compose logs -f siem-soar-frontend
docker-compose logs -f corp-portal-frontend
docker-compose logs -f scada-frontend
docker-compose logs -f siem-postgres
```

### Docker Compose Commands
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Rebuild images
docker-compose build --no-cache

# View running containers
docker-compose ps

# Access service shell
docker-compose exec backend bash
docker-compose exec siem-postgres psql -U siem_user -d siem_db

# Restart specific service
docker-compose restart backend
```

---

## Configuration

### Environment Variables (.env)

**Backend Configuration**
```
DATABASE_URL=postgresql://siem_user:[REDACTED]@siem-postgres:5432/siem_db
FLASK_ENV=production
DEBUG=False
```

**Frontend URLs (auto-configured)**
```
SIEM_API_URL=http://localhost/api
CORP_API_URL=http://localhost/api
SCADA_API_URL=http://localhost/api
```

**Gateway Configuration**
```
GATEWAY_PORT=80
GATEWAY_HTTPS_PORT=443
```

---

## Database Access

### Connect from Local Machine
```bash
# Install psql client
# macOS: brew install postgresql
# Windows: https://www.postgresql.org/download/windows/
# Linux: apt-get install postgresql-client

# Connect to database
psql -h localhost -U siem_user -d siem_db
# Password: (from .env DATABASE_URL)

# Or use docker exec
docker-compose exec siem-postgres psql -U siem_user -d siem_db
```

### Common Database Commands
```sql
-- List tables
\dt

-- View audit events
SELECT * FROM audit_events ORDER BY created_at DESC LIMIT 10;

-- View incidents
SELECT incident_id, status, severity FROM incidents;

-- View alerts
SELECT alert_id, severity, status FROM alerts;

-- Check connections
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;
```

---

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose logs backend

# Rebuild
docker-compose build --no-cache backend

# Restart
docker-compose restart backend
```

### Database Connection Failed
```bash
# Check PostgreSQL is running
docker-compose ps siem-postgres

# Check logs
docker-compose logs siem-postgres

# Verify from local machine
psql -h localhost -U siem_user -d siem_db

# Rebuild database
docker-compose down -v  # Remove volumes
docker-compose up -d    # Recreate
```

### Frontend Not Loading
```bash
# Check gateway logs
docker-compose logs api-gateway

# Verify frontend containers running
docker-compose ps siem-soar-frontend

# Check nginx config
docker-compose exec api-gateway nginx -t
```

### API Slow/Timing Out
```bash
# Check backend logs
docker-compose logs -f backend

# Check database performance
docker-compose exec siem-postgres psql -U siem_user -d siem_db -c "\dt+"

# Restart backend
docker-compose restart backend
```

---

## Production Deployment

### Pre-Production Checklist
- [ ] All services passing health checks
- [ ] Database backups configured
- [ ] SSL certificates obtained (for HTTPS)
- [ ] Secrets updated in .env
- [ ] Environment set to `FLASK_ENV=production`
- [ ] DEBUG set to `False`
- [ ] CORS origins configured
- [ ] Rate limiting tested

### SSL/HTTPS Setup
```bash
# Create nginx-ssl.conf with certificate paths
# Update docker-compose.yml to use nginx-ssl.conf
# Mount certificates into container
# Update gateway port 443 configuration

volumes:
  - /path/to/certs:/etc/nginx/certs:ro
```

### Scaling
```bash
# Run multiple backend instances (behind gateway load balancer)
docker-compose up -d --scale backend=3

# Gateway automatically distributes requests
```

---

## Performance Tuning

### Database Optimization
```bash
# Connect to database
docker-compose exec siem-postgres psql -U siem_user -d siem_db

# Check slow queries
SELECT * FROM pg_stat_statements WHERE mean_time > 1000;

# Create indexes if needed
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_incidents_status ON incidents(status);
```

### Nginx Caching
Already configured in nginx.conf:
- Static assets: 365 days cache
- HTML: no-cache (ensures fresh SPA)
- Gzip compression enabled
- Connection pooling enabled

### Backend Optimization
Already configured:
- SQLAlchemy connection pooling (10 connections)
- Query optimization with indexes
- Pagination on all list endpoints
- Response caching headers

---

## Monitoring

### Container Health
```bash
# Monitor in real-time
docker-compose ps

# Detailed status
docker inspect gotxa-backend | grep -A 20 Healthcheck
```

### Resource Usage
```bash
# View container resource usage
docker stats

# Limit resources in docker-compose
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

---

## Summary

**Architecture:**
- ✅ API Gateway routes all traffic
- ✅ 3 independent frontend servers
- ✅ 1 centralized backend API
- ✅ 1 PostgreSQL database
- ✅ Full RBAC & audit logging

**Services:**
- ✅ SIEM/SOAR at `/`
- ✅ Corp Portal at `/corp`
- ✅ SCADA Dashboard at `/scada`
- ✅ Backend API at `/api/`

**Deployment:**
- ✅ Single `docker-compose up -d`
- ✅ All services orchestrated
- ✅ Health checks on all
- ✅ Auto-restart on failure

---

**Status: ✅ READY FOR DEPLOYMENT**

Start with: `docker-compose up -d`

Access at: `http://localhost/`
