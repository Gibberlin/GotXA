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

**GotXA** is a full-fidelity cybersecurity simulation platform designed for threat detection engineering, incident response training, and industrial control systems (ICS/OT) defense. It pairs realistic corporate web applications and autonomous Modbus TCP industrial PLCs with an enterprise SIEM, automated SOAR playbooks, parallel log ingestion pipelines, and interactive attack daemons.

```
                                 ┌──────────────────────────┐
                                 │   API Gateway (Nginx)    │
                                 │   Public Ports 80 / 443  │
                                 └────────────┬─────────────┘
                 ┌────────────────────────────┼────────────────────────────┐
                 ▼                            ▼                            ▼
         SIEM/SOAR Frontend         Corporate Portal UI            SCADA HMI UI
         (React · Port 80)           (React · Port 80)           (React · Port 80)
                 │                            │                            │
                 └────────────────────────────┼────────────────────────────┘
                                              ▼
                                    ┌───────────────────┐
                                    │  Backend REST API │
                                    │ Flask · Port 5000 │
                                    └─────────┬─────────┘
                              ┌───────────────┼───────────────┐
                              ▼               ▼               ▼
                        PostgreSQL          Redis       Celery Worker
                        (Port 5432)      (Port 6379)     (PDF Engine)
                              ▲
                              │
               ┌──────────────┴──────────────┐
               │                             │
    ┌────────────────────┐        ┌────────────────────┐
    │  SCADA REST Gateway│        │ Parallel Collector │
    │   Port 5002 /api   │        │     Port 5006      │
    └──────────┬─────────┘        └──────────┬─────────┘
               │ (Modbus TCP)                │ (Multi-Threaded Tailing)
       ┌───────┴───────┐             ┌───────┴───────┐
       ▼               ▼             ▼               ▼
    PLC-1 (5003)    PLC-2 (5004)  /logs/corp/*    /logs/ot-*
```

---

## ✨ Key Capabilities

### ⚡ 1. Parallel Telemetry & High-Throughput Ingestion
*   **Zero Polling Bottlenecks**: SCADA Modbus polling runs on dedicated asyncio event loops with connection pooling.
*   **Asynchronous Batch Publishing**: Decoupled `SiemPublisher` buffers operational telemetry in a thread-safe queue and streams batches to SIEM via worker threads.
*   **Multi-Threaded Log Tailing**: `ParallelLogCollector` concurrently tails log streams across multiple endpoints without cross-blocking.

### 🔍 2. Real Operational & Forensic Logging
*   **Authentic Telemetry**: Eliminated all pseudo-random placeholder strings.
*   **Modbus Operations**: Emits structured logs on register read/writes, setpoint updates, and safety envelope violations.
*   **Audit Trail**: Records authentic application events (SQL queries, auth attempts, diagnostic commands) with ISO-8601 timestamps and IP metadata.

### 🌐 3. Dynamic Machine Auto-Discovery
*   **SCADA Dynamic Registry**: Discover and register new PLCs at runtime via `POST /api/scada/machines/register` with automated poller task instantiation.
*   **Dynamic Log Discovery**: Scans the `/logs` directory tree, automatically detecting newly created machine folders without service restarts.
*   **SIEM Device Inventory**: Automatically catalogs new network devices in PostgreSQL, assigns trust states, and raises `NEW_DEVICE_DETECTED` alerts.

### 🛡️ 4. Automated SOAR Response Playbooks
*   **Closed-Loop Defense**: Attack $\rightarrow$ Real Log Ingestion $\rightarrow$ Rule Engine $\rightarrow$ Alert Generation $\rightarrow$ SOAR Playbook Execution.
*   **Active Mitigations**: Dynamic `iptables` IP blocking, Docker container lateral isolation, service reboot, and account credential locking.
*   **Safety Guardrails**: 60-second cooldown timers, subnet whitelisting (protects bridges/gateways), and dual-approval workflows for high-risk actions.

### 🏭 5. Industrial OT Simulation & Holographic SCADA HMI
*   **Refinery 1 (Port 5003)**: Crude oil heater (temperature 170–210 °C, pressure 45–75 PSI).
*   **Refinery 2 (Port 5004)**: Chemical mixer tank (flow rate 25–80 L/min).
*   **Audited Controls**: Operator setpoint modifications and emergency stop actions are range-validated, executed on Modbus registers, and audited.

---

## 🚀 Quick Start

### 1. Prerequisites
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v24.0+) & Docker Compose (v2.20+)
*   Git

### 2. Launch the Stack
```bash
# Clone the repository
git clone https://github.com/Gibberlin/GotXA.git
cd GotXA

# Create environment file
cp .env.example .env

# Build and launch all multi-tier services
docker-compose up -d --build
```

### 3. Access Web Dashboards

| Application | URL | Default Auth / Notes |
| :--- | :--- | :--- |
| **SIEM & SOAR Hub** | `http://localhost/` | Security operations console & alerts. |
| **Corporate Portal** | `http://localhost/corp` | Corporate employee and administrative portal. |
| **SCADA HMI Dashboard** | `http://localhost/scada` | Real-time industrial process visualization. |
| **Unified API Gateway** | `http://localhost/api/` | Reverse-proxied backend REST routes. |
| **Direct Flask API** | `http://localhost:5000` | Direct backend API (Health: `/health`). |

---

## 🔌 Default Ports & Services Reference

| Service | Internal Port | External Port | Function |
| :--- | :--- | :--- | :--- |
| `api-gateway` | `80`, `443` | `80`, `443` | Nginx reverse proxy routing. |
| `gotxa-backend` | `5000` | `5000` | Core Flask REST API. |
| `siem-postgres` | `5432` | `5432` | PostgreSQL relational database (`siem_db`). |
| `redis-cache` | `6379` | Internal | Celery broker and cache. |
| `celery-worker` | Internal | Internal | Asynchronous PDF report generator. |
| `corp-portal-agent` | `5001` | `5001` | Vulnerable corporate web app for cyber range exercises. |
| `ot-scada-gateway` | `5002` | `5002` | SCADA Modbus polling & command gateway. |
| `ot-plc-refinery-1` | `5003` | `5003` | Modbus TCP PLC 1 (Heater & Pressure). |
| `ot-plc-refinery-2` | `5004` | `5004` | Modbus TCP PLC 2 (Flow Rate Mixer). |
| `log-collector` | `5006` | `5006` | Parallel multi-threaded real log collector. |

---

## 🧪 Security & Threat Simulation

Verify the automated defense loop by running the built-in test runner or penetration scripts:

```bash
# Run the automated end-to-end SOAR test suite
python test_soar.py

# Or execute specific cyber range exploit scripts:
python pentesting_scripts/attack_sqli.py        # SQL Injection attack
python pentesting_scripts/attack_bruteforce.py  # Credential brute force
python pentesting_scripts/attack_rce.py         # Remote code execution
```

---

## 📚 Documentation Hub

Exhaustive architectural reports, API references, runbooks, and implementation guides are located in the **[`doc/`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/doc)** directory:

| Document | Purpose |
| :--- | :--- |
| **[`doc/IMPORTANT_FACTS.md`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/doc/IMPORTANT_FACTS.md)** | **Start Here.** Cheat sheet covering ports, credentials, environment variables, and directories. |
| **[`doc/ARCHITECTURE.md`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/doc/ARCHITECTURE.md)** | In-depth technical architecture, network zones, parallel pipelines, discovery, and ORM models. |
| **[`doc/API_SPECIFICATION.md`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/doc/API_SPECIFICATION.md)** | Exhaustive REST API specification for all 40+ endpoints with request/response schemas. |
| **[`doc/TESTING_AND_INTEGRATION.md`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/doc/TESTING_AND_INTEGRATION.md)** | Testing guides, test runners, pentest scripts, and React frontend integration standards. |
| **[`doc/CODE_SNIPPETS.md`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/doc/CODE_SNIPPETS.md)** | Production code snippets for IP blocking, container quarantine, Modbus loops, and publisher workers. |
| **[`doc/SYSTEM_REFERENCE.md`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/doc/SYSTEM_REFERENCE.md)** | Technical runtime reference for Docker containers, database tables, and production checklists. |
| **[`doc/vision_corp.md`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/doc/vision_corp.md)** | Corporate Portal vision, user journey, component hierarchy, and API handoff. |
| **[`doc/vision_scada.md`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/doc/vision_scada.md)** | SCADA HMI Hologram Dashboard vision, operator controls, and API handoff. |
| **[`For Avirup/`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/For%20Avirup)** | Compliance mappings, alarm thresholds, MITRE matrix mappings, and incident response runbooks. |

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
