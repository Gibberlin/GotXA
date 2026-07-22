# Security Orchestration, Automation, and Response (SOAR) Documentation

This document provides a detailed, production-grade technical overview of the **Security Orchestration, Automation, and Response (SOAR)** implementation in the GotXA Cyber Range. 

The GotXA SOAR system is designed to close the loop between threat detection and threat mitigation automatically. It processes incoming telemetry, detects security anomalies, matches them to structured response playbooks, executes containment commands (both simulated and real-world), and logs full audit trails.

---

## 1. High-Level Architecture & Lifecycle Flow

The SOAR implementation follows a linear, event-driven data flow. The diagram below illustrates how raw log data is processed and mitigated by the system.

Click the below link to open the diagram in full screen and explore it in detail

[Mermaid Diagram Link](https://mermaid.live/view#pako:eNqtVV1v4zYQ_CsLPlQO4MayFTuJHg4Q8gGkNc4-O3cFCgMHRtpThFCkSlG58wX5712SluXEToqi9YNFUjs7s8Ml9cRSlSGLWY1_NShTvCx4rnm50isJ9OONUbIp71C3KxXXpkiLiksDSY70z-vNYABTlcONzLE2h8Lpjca6toB2mMxvoDfgVTF4HA4Kv3h0CHvJDb_jNVrwXNWGIpefptvlQ5ArmRfSAZazZNFOe5ccSyXh9l4jzw5yzQVf3yn14Lja8dUPTMmMgz7ccp2jM-JCScMLWWK32rtU6QPqQVGRVIG-vDaLM-7XDx82fsQwny1v4bfl7KPz0pbXhm5CKLgtOoY_dGEQNP8OgqKNgoCedQCOaR-4ZVk0EhKB2nhTjrnkYv0TvxK6t7WEC-NdIvfRYGowa1-9r4fbzE6NG7V6oLc03DREH8wqlMGWCGX2WitlddaQVKwrJTMYhSHMfoeeb6-CdnDZpOluu7RPoVQFV4-o1zCGJaaErqE3n02nX28-3l4tviTTo91CvAcv6vjUWLSX6cuhDNOiLAzpeAFuMVaxT2Qlm0ZLUITegHcRu2Mn9VppQJ7eg6Xz27Ib80JiR1Er8Yhde_6yabc3kV1xF3ZLEYKl4jpJrZXBztag63M6isHR61yv57ZBFjaVc4Yg0JuENaRKiUx9l1Ch3qgaeJ69jG8o_FxlNm0ncEdfqspKUDtmQd-60AjqkaBTQet7LCjo3vDnt3PsXSltkD8p1fY-aMUUZSOIMgPaugVycbCwNgnl8y7EkFSVWJNB3SVB5ZRcZu_i91vLu-LLJzn-IAyueSH6kCElF_X_6_Ug-EZJnelv5cf9Kg41TCJE17WesfZHGTPM_p1od1agdnLdfbM5FllwsAUSuX5NDdeurP9IeyMf7Z2Uc3du_sGYnSkNWZ_lushYbHSDfVaiLrmdsicbsmLmHktcsZiGGdcPK7aSz4Shz86fSpUtTKsmv2fxN05l9lnjZG6-5NsQIkN9oRppWDyMTlwOFj-xHywejaLjcBKejMaj6GwSnQ37bM3i6OR4FIXj8_NhGEXD08nwuc9-OtLw-Hw8HE_Oz4aTMDqJTsPT578BHVKbGQ)


## 2. Database Models & Schema

The SOAR engine integrates closely with the relational database schema defined in `app/models.py`. The two primary models that drive the alerting and mitigation cycles are `Alert` and `SoarAction`.

### 2.1 The `Alert` Model (Table: `alerts`)
Represents a security anomaly or attack signature detected during log ingestion.

*   **`id`** (`Integer`, Primary Key): Unique auto-incrementing ID.
*   **`timestamp`** (`DateTime`): The timestamp when the detection occurred.
*   **`host`** (`String`): The host agent or system container from which the log originated.
*   **`severity`** (`String`): Severity rating (`HIGH`, `MEDIUM`, `LOW`).
*   **`rule`** (`String`): The rule name triggered (e.g., `Brute Force Attempt`).
*   **`log_message`** (`Text`): Snippet or details of the underlying log message.
*   **`status`** (`String`): Lifecycle state of the alert. Values: `'Open'`, `'Investigating'`, `'Resolved'`.
*   **`log_id`** (`Integer`, Foreign Key): Reference to the original raw `Log` record (cascading deletes enabled).
*   **`created_at` / `updated_at`** (`DateTime`): Timestamps tracking creation and modification times.

### 2.2 The `SoarAction` Model (Table: `soar_actions`)
Represents an action executed by the SOAR engine in response to an alert. It functions as the central audit trail.

*   **`id`** (`Integer`, Primary Key): Unique auto-incrementing action ID.
*   **`alert_id`** (`Integer`, Foreign Key): Reference to the parent `Alert` model.
*   **`action_type`** (`String`): Type of containment action. Values:
    *   `ip_block` (Packet filtering)
    *   `container_isolate` (Network disconnection)
    *   `service_restart` (Container reboot)
    *   `rate_limit` (Traffic throttling)
    *   `credential_lock` (Account lockout)
    *   `log_escalation` (Incident ticketing)
    *   `monitor_escalation` (Telemetry rate adjustment)
*   **`target`** (`String`): The entity being acted upon (e.g., IP address, container name, account, or target team).
*   **`status`** (`String`): Current execution status. Values: `'pending'`, `'executing'`, `'completed'`, `'failed'`.
*   **`description`** (`Text`): Human-readable summary of the action.
*   **`playbook`** (`String`): The name of the specific playbook executing this action.
*   **`executed_at`** (`DateTime`): Timestamp when execution was initiated.
*   **`completed_at`** (`DateTime`): Timestamp when execution finished.
*   **`result_detail`** (`Text`): Output details, execution trails, command parameters, rate-limit reasons, or failure error traces.
*   **`created_at`** (`DateTime`): Timestamp tracking database insertion.

---

## 3. The Detection-to-Remediation Mapping

The SOAR engine correlates detected rules with specific response playbooks using a configured mapping (`RULE_PLAYBOOK_MAP` in `app/soar_engine.py`). 

Here is the exact rule-to-playbook mapping implemented in the engine, along with how targets and descriptions are generated:

| Triggered Alert Rule | Severity | Action Type | Playbook Name | Target Determination | Generated Action Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Brute Force Attempt** | HIGH | `ip_block` | `brute_force_ip_block` | Extracts IP from log message. | "Blocked malicious IP `<ip>` — triggered by 'Brute Force Attempt' on `<host>`" |
| **Brute Force Threshold Exceeded** | HIGH | `ip_block`<br>`credential_lock` | `brute_force_ip_block`<br>`brute_force_credential_lock` | **IP**: Searches recent logs from host for an IP.<br>**Account**: Searches recent logs from host for a username. | **IP**: "Blocked malicious IP `<ip>`..."<br>**Lock**: "Locked account `<user>` — triggered by 'Brute Force Threshold Exceeded' on `<host>`" |
| **Critical System Error** | HIGH | `service_restart` | `critical_error_restart` | The host reporting the crash (`alert.host`). | "Restarted service `<host>` — triggered by 'Critical System Error'" |
| **Network Anomaly Detected** | HIGH | `ip_block`<br>`rate_limit` | `network_anomaly_block`<br>`network_anomaly_rate_limit` | Extracts IP from log message. | **IP**: "Blocked malicious IP `<ip>`..."<br>**Rate**: "Applied rate limiting to IP `<ip>` — triggered by 'Network Anomaly Detected' on `<host>`" |
| **Privilege Escalation** | HIGH | `container_isolate` | `privilege_escalation_isolate` | The compromised host container (`alert.host`). | "Isolated container `<host>` from network — triggered by 'Privilege Escalation'" |
| **Service Availability Issue** | MEDIUM | `service_restart` | `service_availability_restart` | The affected service container (`alert.host`). | "Restarted service `<host>` — triggered by 'Service Availability Issue'" |
| **Infrastructure Anomaly** | MEDIUM | `service_restart` | `infrastructure_restart` | The affected service container (`alert.host`). | "Restarted service `<host>` — triggered by 'Infrastructure Anomaly'" |
| **Error Event** | MEDIUM | `log_escalation` | `error_event_escalation` | Defaults to target `"SOC-L2-Team"`. | "Escalated incident to SOC-L2-Team — triggered by 'Error Event' on `<host>`" |
| **Warning Event** | LOW | `monitor_escalation` | `warning_monitor_escalation` | The warning host container (`alert.host`). | "Increased monitoring for `<host>` — triggered by 'Warning Event'" |

### 3.1 Target Resolution Algorithms
*   **IP Extraction (`_extract_ip`)**: Standard regex matching IP patterns: `\b(?:\d{1,3}\.){3}\d{1,3}\b`. If none is found or if the alert is threshold-based, the system queries the database to find the last ingested log containing `%from%` or `%ip=%` on that host and extracts the IP from that log.
*   **Username Extraction (`_extract_account`)**: Extracts accounts using patterns like `username=xxx`, `User xxx`, `account=xxx`, or `credentials for xxx`. For threshold alerts where the summarizing alert doesn't contain the username, it queries the database for the last log on the host matching `%credentials%`, `%login%`, or `%user%` and extracts the account name from it.

---

## 4. Playbook Execution Layer

The core execution logic is contained in `app/playbooks.py` via the `PlaybookExecutor` class. It supports two execution modes, determined by the environment variable `SOAR_REAL_MODE`:

### 4.1 Safe Simulated Mode (`SOAR_REAL_MODE=false`)
The default safe mode. Instead of making system configuration changes, it generates realistic execution logs, delays execution using `random.uniform()` to simulate network latency, and returns a successful `ActionResult` with simulated details. This allows safe dry-runs of the range in local or test setups.

### 4.2 Real-World Action Mode (`SOAR_REAL_MODE=true`)
In real mode, the engine issues actual system commands to quarantine, throttle, or reboot targets.

#### A. IP Blocking (`execute_ip_block`)
*   **Action**: Inserts a packet filtering drop rule inside the SIEM container using `iptables`.
*   **Command**: `iptables -A INPUT -s <target_ip> -j DROP`
*   **Safeguards**: Never blocks loopback (`127.0.0.1`) or Docker network ranges (`172.17.0.X`, `172.18.0.X`, `172.24.0.X`, `172.25.0.X`). This prevents the SIEM and host from locking themselves out during automated defense demonstrations.
*   **Fallback**: If the container lacks system privileges (`NET_ADMIN` capability) or `iptables` fails, it logs a warning and falls back to logging a simulated block.

#### B. Container Network Isolation (`execute_container_isolate`)
*   **Action**: Automatically severs network connectivity of a compromised Docker container.
*   **Mechanism**: Uses the official Docker SDK for Python (communicating via the mounted `/var/run/docker.sock`).
*   **Details**: Inspects the target container, discovers all attached Docker network interfaces, and disconnects it from any network matching `'corp'` or `'corporate'` (e.g., `corporate_net`). This effectively quarantines the container from business and database zones while preserving management networks if configured.

#### C. Service Restarts (`execute_service_restart`)
*   **Action**: Reboots system containers that crash or experience fatal errors.
*   **Mechanism**: Employs the Docker SDK for Python.
*   **Details**: Executes `docker.from_env().containers.get(service_name).restart()` to reboot the container. This auto-remedies panic, OOM, and memory-leak issues in telemetry agents or application services.

#### D. Simulated Real-World Actions (Remaining Playbooks)
*   `rate_limit`: Throttles connection frequency to 10 connections/min (`iptables -A INPUT -s <target_ip> -p tcp --dport 80 -m limit --limit 10/min -j ACCEPT`).
*   `credential_lock`: Disables/locks accounts in the security environment database (`passwd -l <account_name>`).
*   `log_escalation`: Creates a mock incident response ticket (e.g., `INC-12845`) and routes it to SOC Level 2.
*   `monitor_escalation`: Decreases telemetry polling intervals (e.g., from 60 seconds to 10 seconds) on targeted servers to gather high-resolution post-incident forensic data.

---

## 5. Built-in Safeguards & Platform Controls

To ensure system stability, prevent loops, and facilitate manual controls, the SOAR engine implements three major control loops:

### 5.1 Rate Limiting Cooldown (60 Seconds)
To prevent command storms (e.g., running `iptables` 100 times for 100 fast failed logins), the engine runs a cooldown verification before firing playbooks.
```python
recent_limit = datetime.utcnow() - timedelta(seconds=60)
recent_duplicate = SoarAction.query.filter(
    SoarAction.action_type == action_type,
    SoarAction.target == target,
    SoarAction.status == 'completed',
    SoarAction.completed_at >= recent_limit
).first()
```
If a duplicate action type was executed on the same target in the last 60 seconds, the action is marked as `completed` with status details `[RATE LIMITED] Action skipped...`.

### 5.2 Network Exclusion list
During `ip_block` playbooks, the engine filters IPs against internal subnets:
*   `127.0.0.1` (Local host loopback)
*   `172.17.0.0/16` & `172.18.0.0/16` (Default Docker bridges)
*   `172.24.0.0/16` (Corporate network subnet)
*   `172.25.0.0/16` (OT network subnet)

### 5.3 Automated Status Escalation
*   If **all** actions configured for an alert's playbook complete successfully, the alert's status is automatically marked as **`Resolved`**.
*   If **any** action fails, the status is set to **`Investigating`**, surfacing it to SOC analysts for manual triage.

---

## 6. REST API Endpoints & Analyst Triggers

The Flask blueprint in `app/api/soar_api.py` exposes REST endpoints for dashboard UI integration, metrics reporting, and manual SOC analyst overrides:

### `GET /api/v1/soar/actions`
*   **Purpose**: Retrieves list of executed SOAR actions.
*   **Parameters**: `limit` (max 500), `offset`, `status` (pending/executing/completed/failed), `action_type`.

### `GET /api/v1/soar/actions/<action_id>`
*   **Purpose**: Fetches complete execution details of a specific action, including its parent alert's details.

### `GET /api/v1/soar/stats`
*   **Purpose**: Aggregates SOAR statistics for UI charts.
*   **Output**: Total action counts, counts grouped by type and status, total auto-resolved alerts, average mitigation response time in milliseconds, total active IP blocks, and actions triggered in the last 24 hours.

### `GET /api/v1/soar/notifications`
*   **Purpose**: Feeds live-notifications (toast messages/activity tickers) on the SIEM dashboard.
*   **Parameters**: `limit`, `since_id` (polling tracker).

### `POST /api/v1/soar/trigger`
*   **Purpose**: Allows analysts to manually fire actions directly from the dashboard.
*   **Payload**:
    ```json
    {
      "alert_id": 45,
      "action_type": "ip_block",
      "target": "10.0.2.15"
    }
    ```
*   **Execution**: Bypasses the polling queue, creates a completed `SoarAction` labeled `manual_<action_type>`, and sets the parent alert status to `Resolved`.

---

## 7. Threat Testing & Playbook Verification Framework

The SOAR engine's detection rules and automated response playbooks are verified using the test suite in `test_soar.py`. 

The test framework injects real and simulated malicious activities and monitors the SOAR API to verify successful resolution:

1.  **Test 1: Critical System Error (Service Restart Playbook)**
    *   *Action*: Ingests a simulated kernel panic log from `corp-portal-agent`.
    *   *Verification*: Polls the API to ensure the `service_restart` action is completed on target `corp-portal-agent`.
2.  **Test 2: Privilege Escalation (Container Isolation Playbook)**
    *   *Action*: Triggers 10 command execution exploits using `sudo` via `/diagnostic` on `corp-portal-agent`.
    *   *Verification*: Ensures the `container_isolate` action is triggered, which disconnects the container from `gotxa_corporate-net`. It automatically reconnects the container post-test to restore environment telemetry.
3.  **Test 3: Brute Force Threshold (IP Block + Credential Lock Playbook)**
    *   *Action*: Sends 10 invalid login requests via `/login` to simulate password spraying.
    *   *Verification*: Verifies that **both** playbooks (`ip_block` on the source IP and `credential_lock` on the username) are executed successfully.
4.  **Test 4: Network Anomaly Detected (IP Block + Rate Limit Playbook)**
    *   *Action*: Ingests an NMAP port scanner alert from `corp-workstation-agent`.
    *   *Verification*: Assures that both an `ip_block` and `rate_limit` action are triggered and completed for the scanner's source IP.
5.  **Test 5: Warning Event (Monitoring Escalation Playbook)**
    *   *Action*: Ingests a high-temperature threshold warning from the operational OT refinery PLC `ot-plc-refinery-1`.
    *   *Verification*: Assures that the `monitor_escalation` playbook successfully executes to decrease telemetry polling intervals on the affected controller.
