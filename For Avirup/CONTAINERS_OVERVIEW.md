# GotXA — Container Stack & Technology Justification

This document provides a detailed overview of the containerized services in the GotXA platform, outlines the technical rationale for our architectural choices, and discusses future roadmap scopes.

---

## 🐋 1. Containerized Stack Overview

GotXA is orchestrated using a multi-container **Docker Compose** structure. The services communicate over an isolated bridge network (`gotxa-net`, subnet `172.26.0.0/16`).

```
                              [ API Gateway: Port 80 ]
                                         │
       ┌─────────────────────────────────┼─────────────────────────────────┐
       ▼                                 ▼                                 ▼
 [siem-frontend]                   [corp-frontend]                  [scada-frontend]
 (Internal Port 80)               (Internal Port 80)               (Internal Port 80)
       │                                 │                                 │
       └─────────────────────────────────┼─────────────────────────────────┘
                                         ▼
                               [ backend-api: Port 5000 ]
                                         │
                       ┌─────────────────┴─────────────────┐
                       ▼                                   ▼
                 [siem-postgres]                    [celery-worker]
                 (Port 5432)                          (Background)
                       │                                   │
                       └─────────────────┬─────────────────┘
                                         ▼
                                  [redis: Port 6379]
```

### Services Directory

| Container Name | Service Role | Docker Context / Image | Storage Volume Mounts | Health Checks |
| :--- | :--- | :--- | :--- | :--- |
| **`api-gateway`** | Ingress Router | `webservers/api-gateway/` | None | `wget --spider http://localhost/health` |
| **`siem-soar-frontend`**| SOC Dashboard UI | `webservers/siem-soar-frontend/` | `siem-frontend-data` | `wget --spider http://localhost/health` |
| **`corp-portal-frontend`**| Employee Portal UI | `webservers/corp-portal-frontend/` | `corp-frontend-data` | `wget --spider http://localhost/health` |
| **`scada-frontend`** | HMI Gauges UI | `webservers/scada-frontend/` | `scada-frontend-data` | `wget --spider http://localhost/health` |
| **`gotxa-backend`** | REST API Core | `backend/` | `reports-data` | `curl -f http://localhost:5000/health` |
| **`celery-worker`** | Async PDF Engine | `backend/Dockerfile.celery` | `reports-data` | Dependent on DB/Redis health status |
| **`siem-postgres`** | Persistent Database | `postgres:15-alpine` | `siem-db-data` | `pg_isready -U siem_user -d siem_db` |
| **`redis-cache`** | Broker & Cache | `redis:7-alpine` | None | `redis-cli ping` |

---

## 🛠️ 2. Architectural Technology Justification

We chose our core technology stack based on resource efficiency, developer familiarity, and realistic industrial design mapping.

### A. Python Flask (REST API Backend)
*   **Why**: Flask is a lightweight micro-framework. It allows us to build REST APIs rapidly without the overhead of heavy opinionated engines (like Django), which is ideal for deploying in resource-constrained environments like edge gateways.
*   **Alternative Considered**: FastAPI. While FastAPI provides automatic typing, Flask’s integration with standard SQLalchemy ORM is mature and robust for orchestrating dynamic state models.

### B. React + Vite (Frontend Dashboards)
*   **Why**: GotXA requires real-time dashboard updates (e.g., log streams, SCADA gauges). React's virtual DOM allows for efficient rendering of telemetry values without page refreshes. Vite provides extremely fast local hot-reload builds, streamlining development.
*   **Alternative Considered**: Angular or plain Vanilla JavaScript. Angular is too heavy for simple dashboard UIs, and Vanilla JS becomes difficult to maintain when handling complex states (like tracking pending SOAR execution status).

### C. PostgreSQL (Database Layer)
*   **Why**: Security audit logs must be immutable and possess transaction integrity (ACID compliance). PostgreSQL allows us to enforce relational constraints, run complex nested queries, and create performant indices on high-query alert fields.
*   **Alternative Considered**: MongoDB. NoSQL databases lack relational constraints, making alert-to-incident linkages and audit logs prone to consistency issues.

### D. Redis & Celery (Async Task Processing)
*   **Why**: Rendering PDF compliance reports requires significant CPU time. By offloading these tasks to Celery workers with a Redis message broker, the API gateway can respond immediately with a `202 Accepted` status, preventing the UI from freezing.

### E. Nginx (API Gateway & Asset Server)
*   **Why**: Nginx acts as a unified reverse-proxy entry point. It simplifies client-side routing, handles CORS constraints, and allows us to configure security headers and rate limits in a single, centralized location.

---

## 🔮 3. Future Scope & Roadmap

GotXA is designed to be modular. We plan to expand the platform in the following areas:

### A. Deep Threat Detection (Suricata IDS Integration)
*   **Upgrade**: Deploy a Suricata container inside the bridge network configured for packet mirroring.
*   **Outcome**: Allows the SIEM to detect network-level attacks (like port scans, DDoS, or command-and-control beacons) in addition to log-level threats.

### B. Distributed Logging Cluster (Elasticsearch/OpenSearch)
*   **Upgrade**: Replace the PostgreSQL logging table with a dedicated Elasticsearch indexing cluster.
*   **Outcome**: Enables lightning-fast full-text searches and log aggregation across thousands of host machines, simulating a true enterprise SOC.

### C. Active Directory (AD) & OAuth2 Centralization
*   **Upgrade**: Connect the backend authentication middleware to a centralized Keycloak or OpenLDAP directory server.
*   **Outcome**: Replaces the demo X-User-ID header with real-world Single Sign-On (SSO) and central RBAC user token validation.

### D. Machine Learning Anomaly Detection
*   **Upgrade**: Run a lightweight Python background service using Scikit-Learn or PyTorch to monitor Modbus registers.
*   **Outcome**: Automatically alerts on slow, subtle temperature/pressure anomalies that slip past standard static threshold rules (detecting slow-leak attacks).
