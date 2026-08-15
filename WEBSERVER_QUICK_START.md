# 🚀 GOTXA Multi-Server Deployment - Quick Start

## One-Command Deployment

```bash
cd C:\Users\RJDhu\OneDrive\Desktop\Project\GotXA
docker-compose up -d
```

---

## Access Applications (30 seconds later)

| App | URL |
|-----|-----|
| **SIEM/SOAR Dashboard** | http://localhost/ |
| **Corp Portal** | http://localhost/corp |
| **SCADA Dashboard** | http://localhost/scada |
| **Backend API** | http://localhost/api/ |

---

## Verify All Running

```bash
docker-compose ps

# Expected output:
# CONTAINER           STATUS
# api-gateway         Up (healthy)
# siem-soar-frontend  Up (healthy)
# corp-portal-frontend Up (healthy)
# scada-frontend      Up (healthy)
# backend             Up (healthy)
# siem-postgres       Up (healthy)
```

---

## Test Endpoints

```bash
# Health check
curl http://localhost/health

# SIEM Dashboard overview
curl -H "X-User-ID: admin" http://localhost/api/overview

# List alerts
curl -H "X-User-ID: admin" http://localhost/api/alerts

# List incidents
curl -H "X-User-ID: admin" http://localhost/api/incidents
```

---

## View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f api-gateway
docker-compose logs -f siem-soar-frontend
```

---

## Common Commands

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (DELETES DATA)
docker-compose down -v

# Rebuild images
docker-compose build --no-cache

# Restart specific service
docker-compose restart backend

# Execute command in container
docker-compose exec backend python -c "print('OK')"

# Connect to database
docker-compose exec siem-postgres psql -U siem_user -d siem_db
```

---

## Architecture at a Glance

```
                    API GATEWAY (80/443)
                           |
        ┌──────────────────┼──────────────────┐
        |                  |                  |
      SIEM/SOAR          CORP              SCADA
      (http://)       (http://corp)    (http://scada)
        |                  |                  |
        └──────────────────┼──────────────────┘
                           |
                      BACKEND API
                      (http://api/)
                           |
                      PostgreSQL
```

---

## Services Overview

| Service | Port | URL | Role |
|---------|------|-----|------|
| **API Gateway** | 80/443 | http://localhost | Reverse proxy, routing |
| **SIEM/SOAR** | 3001 | http://localhost/ | Main dashboard |
| **Corp Portal** | 3002 | http://localhost/corp | Admin portal |
| **SCADA** | 3003 | http://localhost/scada | Industrial HMI |
| **Backend** | 5000 | http://localhost/api/ | REST API (36 endpoints) |
| **Database** | 5432 | localhost:5432 | PostgreSQL (development) |

---

## Authentication

Default: **X-User-ID: admin** (demo mode)

```bash
# Any API call
curl -H "X-User-ID: admin" http://localhost/api/overview

# Roles available:
# - admin (all permissions)
# - soc_manager (alerts, incidents, playbooks)
# - analyst (create/edit incidents, view alerts)
```

---

## Environment Setup

### 1. Copy Example Env
```bash
cp .env.example .env
```

### 2. Edit .env (Required for Production)
```
DATABASE_URL=postgresql://siem_user:PASSWORD@siem-postgres:5432/siem_db
FLASK_ENV=production
DEBUG=False
JWT_SECRET=your-secret-here
```

### 3. Build & Run
```bash
docker-compose build
docker-compose up -d
```

---

## Troubleshooting

### Service won't start
```bash
# Check logs
docker-compose logs <service-name>

# Rebuild
docker-compose build --no-cache <service-name>

# Restart
docker-compose restart <service-name>
```

### Database connection error
```bash
# Verify PostgreSQL running
docker-compose ps siem-postgres

# Check database
docker-compose exec siem-postgres psql -U siem_user -d siem_db -c "SELECT 1"

# Rebuild database (WARNING: deletes data)
docker-compose down -v
docker-compose up -d
```

### API returning 502 Bad Gateway
```bash
# Check backend health
curl http://localhost/api/health

# Check backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend
```

### Frontend not loading
```bash
# Check gateway logs
docker-compose logs api-gateway

# Verify nginx config
docker-compose exec api-gateway nginx -t

# Restart gateway
docker-compose restart api-gateway
```

---

## Performance Tips

1. **Mount volumes in development:**
   ```bash
   # Edit docker-compose.yml for backend:
   volumes:
     - ./backend:/app  # Hot reload
   ```

2. **Scale backend instances:**
   ```bash
   docker-compose up -d --scale backend=3
   ```

3. **Monitor resources:**
   ```bash
   docker stats
   ```

---

## Database Access (Local Development)

```bash
# Connect from terminal
docker-compose exec siem-postgres psql -U siem_user -d siem_db

# Or use local psql client
psql -h localhost -U siem_user -d siem_db
Password: siem_password_secure  # From docker-compose.yml
```

---

## Production Checklist

- [ ] All services passing health checks
- [ ] SSL certificates configured
- [ ] Database backups enabled
- [ ] Secrets updated in .env
- [ ] DEBUG=False
- [ ] FLASK_ENV=production
- [ ] CORS origins configured
- [ ] Rate limiting tested
- [ ] Monitoring setup
- [ ] Logging centralized

---

## File Structure Created

```
GotXA/
├── webservers/
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
├── docker-compose.yml
└── DEPLOYMENT_ARCHITECTURE.md
```

---

## Next Steps

1. ✅ `docker-compose up -d` - Start all services
2. ✅ `docker-compose ps` - Verify running
3. ✅ `http://localhost/` - Open SIEM dashboard
4. ✅ `curl http://localhost/api/overview` - Test API
5. ✅ `docker-compose logs -f backend` - Monitor

---

**Status: ✅ READY TO DEPLOY**

```bash
cd GotXA && docker-compose up -d
```

Then visit: **http://localhost/**
