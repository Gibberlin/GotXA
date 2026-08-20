# GotXA — Critical Infrastructure SOC Simulation Platform

GotXA is a self-contained, high-fidelity platform that simulates a Security Operations Center (SOC) protecting a critical-infrastructure environment (refinery/OT setup). It integrates real-time corporate IT and industrial SCADA control panels, detection-rule engines, automated SOAR playbooks, log collectors, and a cyber range with attack-simulation daemons.

---

## 👥 Contributors

| Name | Role | Link |
| :--- | :--- | :--- |
| **Syed Yashin Hussain** | Project Lead & SIEM Architect | [GitHub](https://github.com/Gibberlin) |
| **Avirup Roy** | Lead SOAR Architect & Documentation | [GitHub](https://github.com/aviruproyy-hub) |
| **Antara Deb** | SIEM Contributor, Detection Rules, & Log Analysis | [GitHub](https://github.com/antaradeb0045) |
| **Community** | Maintenance, Bug Fixes, & Features | — |

---

## 🧠 Core System Concepts

*   **SIEM Ingestion & Rules**: Ingests JSON telemetry logs from multiple endpoints (Nginx, host systems, PLCs, vulnerable-app), matches signatures against Python regex detection rules, and outputs high-fidelity PostgreSQL security alerts.
*   **SOAR Automation**: Auto-mitigates incoming threats. Runs dynamic containment steps (iptables IP bans, Docker socket isolations, or container restarts) matching rules to playbooks.
*   **OT SCADA Simulation**: Models real Modbus TCP PLCs running crude oil heater processes. A gateway polls telemetry registers every 2 seconds, exposing REST API metrics for a real-time SVG HMI.
*   **Cyber Range Attacker**: Employs Python attack scripts (SQL Injection, Remote Code Execution, login brute forcing) that exploit intentionally vulnerable assets, generating real telemetry and triggering the SOAR loop.

---

## 🚀 Quick Start Setup

### 1. Provision Services
```bash
# Clone and enter the repository
git clone https://github.com/Gibberlin/GotXA.git
cd GotXA

# Copy environment template and adjust secrets if needed
cp .env.example .env

# Build and start the entire multi-service container stack
docker-compose up -d --build
```

### 2. Services Landing Pages
Once Docker reports all services are healthy, open the following URLs in your web browser:

| Application Dashboard | Accessible URL | Purpose |
| :--- | :--- | :--- |
| **SIEM & SOAR Hub** | `http://localhost/` | Main security analyst monitoring console. |
| **Corporate Employee Portal** | `http://localhost/corp` | Admin portal for simulated employees. |
| **SCADA HMI panel** | `http://localhost/scada` | SVG control panel gauges (Refinery 1 & 2). |
| **REST Backend API Gateway** | `http://localhost/api/` | Base proxy path for API queries. |
| **Direct Flask API** | `http://localhost:5000` | Direct backend API route (bypasses Nginx). |

---

## 📁 Repository Layout

```
GotXA/
├── backend/                     # Primary Flask REST API source code
│   ├── app/                     # Controllers, models, RBAC authorization, and audit logs
│   ├── main.py                  # API service factory
│   └── Dockerfile               # Production API container definitions
├── frontend/                    # User interface source codes
│   ├── siem_dashboard/          # SIEM, SOAR, and raw log scrolling console
│   ├── corp_portal/             # Corporate landing portals
│   └── scada_dashboard/         # SVG process control telemetry panels
├── webservers/                  # Reverse proxy and static file hosting
│   ├── api-gateway/             # Main Nginx router gateway configurations
│   ├── siem-soar-frontend/      # Hosts static React files for the SOC dashboard
│   ├── corp-portal-frontend/    # Hosts corporate static files
│   └── scada-frontend/          # Hosts SCADA HMI static files
├── pentesting_scripts/          # Automation attack scripts (RCE, brute force, SQLi)
├── vulnerable_app.py            # Simulated vulnerable portal backend
├── scada_gateway.py             # Modbus PLC polling gateway
├── modbus_plc_server.py         # Autonomous Pymodbus TCP simulators (PLCs 1 & 2)
├── log_collector.py             # Telemetry log shipper daemon
├── agent.py                     # Synthetic background log generator
└── docker-compose.yml           # Orchestrates the multi-container stack
```

---

## 📚 Documentation Index

Please refer to the following report guides for detailed configurations and specifications:

1.  **[IMPORTANT_FACTS.md](./IMPORTANT_FACTS.md)** — **Start Here.** Cheat-sheet reference detailing port maps, default credentials, environment variables, directories, alerts mapping, and debugging CLI scripts.
2.  **[ARCHITECTURE.md](./ARCHITECTURE.md)** — In-depth architectural report detailing segmented network zones, relational database schemas, authentication/RBAC matrices, audit logger logic, OT PLCs, SCADA gateways, and the SOAR playbook engine.
3.  **[API_SPECIFICATION.md](./API_SPECIFICATION.md)** — REST API specifications detailing response wrappers, authentication headers, error formats, and request/response payloads for all 40+ endpoints.
4.  **[TESTING_AND_INTEGRATION.md](./TESTING_AND_INTEGRATION.md)** — Comprehensive guide for running security test scenarios, log ingestion verification, and React frontend API service integration.
5.  **[CODE_SNIPPETS.md](./CODE_SNIPPETS.md)** — Implementation references compiling code snippets for IP bans, Docker quarantines, reboots, RBAC permission handlers, and Modbus simulation loops.
6.  **[For Avirup/](./For%20Avirup/)** — Specialized documentation directory containing compliance mappings, alarm thresholds, MITRE matrix mappings, layman guides, incident response runbooks, glossary lists, and docker container overviews.
7.  **[backend/README.md](./backend/README.md)** — Redirection reference index for backend developers.
