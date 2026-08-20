# GotXA — Testing & Frontend Integration Guide

This guide details how to verify the threat detection/SOAR loops and integrate React frontend apps with the REST API.

---

## 🧪 Part 1: Security Testing & Simulation Guide

GotXA includes simulated attacks and service tests to verify the closed-loop defense pipeline (Attack → Log Ingestion → Detection Rule → Alert Generation → SOAR Playbook Execution).

```
 ┌────────────────┐      SQLi / RCE / Brute force      ┌─────────────────┐
 │ Attack Script  ├───────────────────────────────────>│ Vulnerable App  │
 └────────────────┘                                    └────────┬────────┘
                                                                │ logs
                                                                ▼
 ┌────────────────┐         Automated Action           ┌─────────────────┐
 │  SOAR Engine   │<───────────────────────────────────┤  Log Collector  │
 └──────┬─────────┘                                    └─────────────────┘
        │ iptables Block / Docker Isolate / Reboot
        ▼
 ┌────────────────┐
 │ Attacker Block │
 └────────────────┘
```

### 1. Unified SOAR Threat Testing Framework
The script **`test_soar.py`** in the repository root automates end-to-end testing of the alert-to-remediation loop. It checks service health, clears queues, triggers attack payloads, and polls the database to confirm matching mitigations were successfully applied.

#### Run the Test Suite:
```bash
# Enter the root directory and execute the test runner
python test_soar.py
```

#### Monitored Scenarios:
1.  **Brute Force Attack** $\rightarrow$ Triggers `ip_block` (injects an `iptables` drop rule).
2.  **Brute Force Threshold** $\rightarrow$ Triggers `credential_lock` (account lock in database).
3.  **Remote Code Execution** $\rightarrow$ Triggers `container_isolate` (docker disconnect from `corp_net`).
4.  **Critical Server crash** $\rightarrow$ Triggers `service_restart` (reboots the service container).
5.  **Network Anomaly** $\rightarrow$ Triggers combined `ip_block` and `rate_limit` playbooks.

---

### 2. Manual Penetration Testing Scripts
Individual exploit scripts are located inside **`pentesting_scripts/`** to simulate targeted network threats.

#### A. SQL Injection Attack (SQLi)
Queries the vulnerable endpoint using injection payloads to bypass portal authentication.
*   **Trigger Command**: `python pentesting_scripts/attack_sqli.py`
*   **Exploit Vector**: `POST http://localhost:5001/login` with body payload `{"username": "' OR 1=1 --", "password": "any"}`.

#### B. Portal Login Brute Force
Fires a fast stream of bad authentication attempts to simulate password-spraying threats.
*   **Trigger Command**: `python pentesting_scripts/attack_bruteforce.py`

#### C. Remote Code Execution (RCE)
Sends injection payloads to the corporate portal diagnostic endpoint.
*   **Trigger Command**: `python pentesting_scripts/attack_rce.py`
*   **Exploit Vector**: `POST http://localhost:5001/diagnostic` with command injection payloads (e.g., `; cat /etc/passwd`).

---

## 🔌 Part 2: React Frontend Integration Guide

React frontends are served through Nginx. Use the patterns below to transition from static state constants to dynamic REST API controllers.

### 1. HTTP Client Configuration (Axios Pattern)
Define a global API client incorporating the demo authentication header:
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost/api', // Router gateway URL path
  headers: {
    'Content-Type': 'application/json',
    'X-User-ID': 'admin' // Demo mode authentication header
  }
});

export default api;
```

### 2. Dashboard KPIs & Charts Fetching
Connect the SIEM home page to the overview endpoints, using state updates and polling intervals to maintain fresh statistics.
```javascript
import React, { useState, useEffect } from 'react';
import api from './api';

export function SIEMOverview() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchMetrics = async () => {
    try {
      const response = await api.get('/overview');
      setMetrics(response.data.data); // Extract payload wrapper
    } catch (err) {
      console.error('Failed to retrieve dashboard metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const poll = setInterval(fetchMetrics, 15000); // 15-second refresh
    return () => clearInterval(poll);
  }, []);

  if (loading) return <div>Loading telemetry streams...</div>;

  return (
    <div>
      <h3>Active Incidents: {metrics.kpis.open_incidents}</h3>
      <h3>Critical Alerts: {metrics.kpis.critical_alerts}</h3>
    </div>
  );
}
```

### 3. Managing Asynchronous SOAR Playbook Triggering
Triggering playbooks returns a status of `202 Accepted` indicating the containment execution is running in the background. The frontend must parse this response, display a spinner, and poll the task ID to update the UI once the action completes.

```javascript
import React, { useState } from 'react';
import api from './api';

export function TriggerPlaybook({ playbookId }) {
  const [status, setStatus] = useState('idle');

  const handleExecution = async (targetEntity) => {
    setStatus('executing');
    try {
      // Trigger execution request
      const initResponse = await api.post(`/playbooks/${playbookId}/executions`, {
        target: targetEntity,
        dry_run: false
      });
      const executionId = initResponse.data.data.execution_id;

      // Poll task status endpoint
      const checkStatus = setInterval(async () => {
        const checkResponse = await api.get(`/playbook-executions/${executionId}`);
        const currentStatus = checkResponse.data.data.status;

        if (currentStatus === 'success' || currentStatus === 'completed') {
          setStatus('mitigated');
          clearInterval(checkStatus);
        } else if (currentStatus === 'failed') {
          setStatus('failure');
          clearInterval(checkStatus);
        }
      }, 2000); // Check every 2 seconds

    } catch (err) {
      console.error('Containment run failed:', err);
      setStatus('failure');
    }
  };

  return (
    <button onClick={() => handleExecution('172.24.0.12')} disabled={status === 'executing'}>
      {status === 'idle' && 'Isolate Host Target'}
      {status === 'executing' && 'Applying Network Quarantine...'}
      {status === 'mitigated' && 'Host Isolated ✓'}
      {status === 'failure' && 'Mitigation Failed!'}
    </button>
  );
}
```
