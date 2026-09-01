# GotXA — Critical Infrastructure SOC & Industrial SCADA Simulation Platform

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![React](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB.svg?logo=react&logoColor=black)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2015-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Broker-Redis%207-DC382D.svg?logo=redis&logoColor=white)](https://redis.io/)
[![Modbus](https://img.shields.io/badge/Protocol-Modbus%20TCP-FF6F00.svg)](https://modbus.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**A production-grade, self-contained cyber range simulating a modern Security Operations Center (SOC) defending an industrial refinery and corporate enterprise.**

[Quick Start](#-quick-start) • [Architecture](#-architecture) • [Key Capabilities](#-key-capabilities) • [Documentation Hub](#-documentation-hub) • [Contributors](#-contributors)

</div>

---

## 📖 Overview

**GotXA** is a full-fidelity cybersecurity simulation platform designed for threat detection engineering, incident response training, and industrial control systems (ICS/OT) defense. It pairs realistic corporate web applications and autonomous Modbus TCP industrial PLCs with an enterprise SIEM, automated SOAR playbooks, parallel log ingestion pipelines, and interactive adversary simulation.

```
                                  ┌──────────────────────────┐
                                  │   API Gateway (Nginx)    │
                                  │   Public Ports 80 / 443  │
                                  └────────────┬─────────────┘
                 ┌─────────────────────────────┼─────────────────────────────┐
                 ▼                             ▼                             ▼
         SIEM/SOAR Frontend          Corporate Portal UI             SCADA HMI UI
         (React · Port 80/siem)      (React · Port 80/corp)         (React · Port 80/scada)
                 │                             │                             │
                 └─────────────────────────────┼─────────────────────────────┘
                                               ▼
                                     ┌───────────────────┐
                                     │  Backend REST API │
                                     │ Flask · Port 5000 │
                                     └─────────┬─────────┘
                               ┌───────────────┼───────────────┐
                               ▼               ▼               ▼
                         PostgreSQL          Redis       Celery Worker
                         (Port 5432)      (Port 6379)     (PDF Engine)
                               ▲               ▲               ▲
                               │               │               │
                ┌──────────────┴───────────────┴───────────────┴───────────────┐
                │                                                              │
     ┌────────────────────┐        ┌────────────────────┐           ┌────────────────────┐
     │  SCADA REST Gateway│        │ Parallel Collector │           │    New_Machine     │
     │   Port 5002 /api   │        │     Port 5006      │           │(Adversary Sim Node)│
     └──────────┬─────────┘        └──────────┬─────────┘           └──────────┬─────────┘
                │ (Modbus TCP)                │ (Multi-Threaded Tailing)       │ (Port Scan / SQLi /
        ┌───────┴───────┐             ┌───────┴───────┐                        │  Brute / OT Override)
        ▼               ▼             ▼               ▼                        ▼
     PLC-1 (5003)    PLC-2 (5004)  /logs/corp/*    /logs/ot-*            Target: gotxa-net
```

---

## ✨ Key Capabilities

### ⚡ 1. Normalized Industry-Standard JSON Ingestion
*   **OT Network Telemetry (`OT_Sensor_Zone3`)**: Deep Packet Inspection (DPI) sensor format detailing `dest_asset`, `protocol`, `mitre_ics_tactic` (`TA0108`), `mitre_ics_technique` (`T836`), `tag_name`, and register values.
*   **SCADA HMI Audit Logs (`SCADA_HMI_Node_A`)**: Captures operator setpoint modifications, emergency valve trips, `user`, `session_id`, and `process_area`.
*   **Corporate Portal WAF (`Corp_Vendor_Portal_WAF`)**: Ingests web authentication events, failed logins, credential sprays, `geoip_country`, `request_uri`, and `user_agent`.

### 🔗 2. Cross-Boundary Multi-Stage Attack Correlation
*   **Automated Attack Chain Detection**: Built-in correlation engine detects multi-stage lateral movement:
    1. **Stage 1 (Corporate IT)**: Credential stuffing or failed login brute-force attempts.
    2. **Stage 2 (SCADA HMI)**: Operator session compromise and setpoint adjustments.
    3. **Stage 3 (Physical OT)**: Unauthorized actuator overrides or thermal overrun commands.
*   **High-Priority Incident Creation**: Automatically correlates all three stages into a single high-priority security incident `CORR-MULTI-STAGE-ICS-ATTACK` with full MITRE ICS technique mapping.

### ⚔️ 3. Isolated Adversary Simulation Node (`New_Machine`)
*   **Dedicated Red Team Container**: `New_Machine` runs inside `gotxa-net` (`172.26.0.5`) to simulate adversary attacks.
*   **Automated Exploit Suites**: Pre-packaged scripts for internal reconnaissance (`port_scanner.py`), SQL injection (`attack_sqli.py`), corporate credential spraying (`attack_bruteforce.py`), and OT Modbus overrides (`attack_modbus_ot.py`).
*   **Real-Time SIEM Ingestion Verification**: All attacks executed from `New_Machine` generate real-time SIEM logs with actual source IP attribution (`172.26.0.5`).

### 🛡️ 4. Automated SOAR Response Playbooks
*   **Closed-Loop Defense**: Attack $\rightarrow$ Real-Time Ingestion $\rightarrow$ Rule Engine $\rightarrow$ Alert Generation $\rightarrow$ SOAR Playbook Execution.
*   **Active Mitigations**: Dynamic `iptables` IP blocking, Docker container lateral isolation, session revocation, and automated containment.

### 🏭 5. Industrial OT Simulation & Holographic SCADA HMI
*   **Refinery 1 (Port 5003)**: Crude oil heater (temperature 170–210 °C, pressure 45–75 PSI).
*   **Refinery 2 (Port 5004)**: Chemical mixer tank (flow rate 25–80 L/min).
*   **Audited Controls**: Operator setpoint modifications and emergency stop actions are range-validated, executed on Modbus registers, and audited into SIEM.

---

## 🚀 Quick Start

### 1. Prerequisites
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v24.0+) & Docker Compose
*   Python 3.11+

### 2. Launch the Stack
```bash
# Clone the repository
git clone https://github.com/Gibberlin/GotXA.git
cd GotXA

# Build and launch all multi-tier microservices
docker compose up -d --build
```

### 3. Access Web Dashboards

| Application | URL | Default Auth / Notes |
| :--- | :--- | :--- |
| **SIEM & SOAR Hub** | `http://localhost/` or `http://localhost/siem/` | Security operations console, live event stream, and incident manager. |
| **Corporate Portal** | `http://localhost/corp/` | Enterprise workspace with 1-click Demo Account selectors (`admin` / `admin`). |
| **SCADA HMI Dashboard** | `http://localhost/scada/` | Real-time industrial process visualization and Modbus setpoint controls. |
| **Unified API Gateway** | `http://localhost/api/` | Reverse-proxied backend REST routes. |
| **Direct Backend API** | `http://localhost:5000` | Core Flask API (Health: `/health`). |

---

## 🔌 Default Ports & Services Reference

| Container / Service | Internal Port | External Port | Function |
| :--- | :--- | :--- | :--- |
| `api-gateway` | `80`, `443` | `80`, `443` | Nginx reverse proxy routing `/`, `/corp/`, `/scada/`, `/siem/`, and `/api/`. |
| `gotxa-backend` | `5000` | `5000` | Core Flask REST API, authentication, and SIEM rule engine. |
| `corp-portal-frontend` | `80` | Internal | Corporate Portal React SPA. |
| `scada-frontend` | `80` | Internal | SCADA HMI Holographic Dashboard React SPA. |
| `siem-soar-frontend` | `80` | Internal | SIEM Operations Console React SPA. |
| `New_Machine` | Internal | Internal | Red Team & Adversary Simulation Node (`172.26.0.5`). |
| `siem-postgres` | `5432` | `5432` | PostgreSQL relational database (`siem_db`). |
| `redis-cache` | `6379` | Internal | Celery broker, rate limiting, and cache. |
| `celery-worker` | Internal | Internal | Asynchronous PDF report generator. |
| `ot-scada-gateway` | `5002` | `5002` | SCADA Modbus polling & command gateway. |
| `ot-plc-refinery-1` | `5003` | `5003` | Modbus TCP PLC 1 (Heater & Pressure). |
| `ot-plc-refinery-2` | `5004` | `5004` | Modbus TCP PLC 2 (Flow Rate Mixer). |

---

## 🧪 Security & Threat Simulation

Execute adversary attacks directly from the **`New_Machine`** container:

```bash
# 1. Run the entire automated penetration testing suite
docker exec -it New_Machine bash run_all_attacks.sh

# 2. Or run specific attack vectors:
docker exec -it New_Machine python3 attack_bruteforce.py  # Corporate portal credential spray
docker exec -it New_Machine python3 attack_sqli.py        # SQL injection testing
docker exec -it New_Machine python3 attack_modbus_ot.py   # Unauthorized PLC Modbus overrides
docker exec -it New_Machine python3 port_scanner.py       # Internal network recon scan
```

---

## 📚 Documentation Hub

Exhaustive architectural reports, API references, runbooks, and implementation guides are located in the **[`doc/`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/doc)** and **[`For Avirup/`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/For%20Avirup)** directories:

| Document | Purpose |
| :--- | :--- |
| **[`doc/IMPORTANT_FACTS.md`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/doc/IMPORTANT_FACTS.md)** | **Start Here.** Cheat sheet covering ports, credentials, environment variables, and directories. |
| **[`doc/ARCHITECTURE.md`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/doc/ARCHITECTURE.md)** | In-depth technical architecture, network zones, correlation engine, and ORM models. |
| **[`doc/API_SPECIFICATION.md`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/doc/API_SPECIFICATION.md)** | Exhaustive REST API specification for all endpoints with request/response schemas. |
| **[`doc/TESTING_AND_INTEGRATION.md`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/doc/TESTING_AND_INTEGRATION.md)** | Testing guides, test runners, and React frontend integration standards. |
| **[`For Avirup/CONTAINERS_OVERVIEW.md`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/For%20Avirup/CONTAINERS_OVERVIEW.md)** | Comprehensive Docker container topology, internal networks, and dependencies. |
| **[`For Avirup/PENTESTING_GUIDE.md`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/For%20Avirup/PENTESTING_GUIDE.md)** | Complete guide to running red team attacks with `New_Machine`. |
| **[`For Avirup/MITRE_MAPPING.md`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/For%20Avirup/MITRE_MAPPING.md)** | MITRE ATT&CK for Enterprise and ICS matrix coverage. |

---

## 👥 Contributors

| Name | Role | Profile |
| :--- | :--- | :--- |
| **Syed Yashin Hussain** | Project Lead & SIEM Architect | [@Gibberlin](https://github.com/Gibberlin) |
| **Avirup Roy** | Lead SOAR Architect & Documentation | [@aviruproyy-hub](https://github.com/aviruproyy-hub) |
| **Antara Deb** | SIEM Contributor, Detection Rules, & Log Analysis | [@antaradeb0045](https://github.com/antaradeb0045) |

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
