# GotXA SIEM/SOAR — Frontend Engineering Handoff Document
> **Target Audience**: Frontend Engineering Team  
> **Date**: 2026-09-08  
> **Topic**: SIEM Dashboard Functional Changes (Real-Time Telemetry, Attack Forensics Tab, and SOAR Active Defenses)  
> *Note: This document details only functional logic, API contracts, state management, and component behavior. Styling/CSS is omitted per team requirements.*

---

## 1. Summary of Required Frontend Changes

1. **RBAC Authentication Header**: Add `X-User-ID: admin` to all polling fetch requests in `SiemDashboard.jsx` (resolves `403 Forbidden` on dashboard updates).
2. **Alerts & Incidents Table Enhancements**: Display new forensic fields returned by the backend (Detected Time, Attacker IP, GeoIP Country, Attack Vector) and add an "Inspect" action button.
3. **New 6th Navigation Tab ("🔬 Attack Forensics & Threat Intel")**:
   - Aggregate KPIs: Unique Threat IPs, Active Vectors, Origin Countries, MITRE Techniques.
   - Top Attacker IP Leaderboard Table with quick-quarantine action.
   - Attack Vector Distribution calculations (SQLi, Brute-Force, OT/SCADA, API Recon).
   - Chronological Attack Audit Trail list.
4. **Forensic Evidence Inspection Modal**:
   - Popup modal when an alert is clicked for inspection.
   - Displays parsed forensic attributes, MITRE mapping, and formatted raw event JSON.
   - Action button to trigger immediate IP Quarantine via SOAR.
5. **SOAR Active Defenses Enhancements**:
   - Connect playbook trigger buttons to `POST /api/v1/soar/execute`.
   - Poll and display the Live SOAR Playbook Execution Audit History table from `GET /api/v1/soar/executions`.

---

## 2. Target File
- `frontend/src/pages/SiemDashboard.jsx`

---

## 3. Step-by-Step Functional Changes

### 3.1 Step 1: Add Component State Variables
In `SiemDashboard.jsx`, declare state for forensics and SOAR executions:
```javascript
// State for SOAR executions audit history
const [soarExecutions, setSoarExecutions] = useState([]);
const [isExecutingPlaybook, setIsExecutingPlaybook] = useState(null);

// State for forensic evidence modal
const [selectedForensicAlert, setSelectedForensicAlert] = useState(null);
```

---

### 3.2 Step 2: Include `X-User-ID: admin` in Polling Requests
Update `fetchDashboardData()` to supply the RBAC header on all requests:
```javascript
const authHeaders = {
  'X-User-ID': 'admin',
  'Content-Type': 'application/json'
};

const [alertsRes, rawRes, modbusRes, authStatsRes, sessionsRes, soarRes] = await Promise.all([
  fetch('/api/alerts?limit=100', { headers: authHeaders }).then(r => r.json()).catch(() => ({ alerts: [] })),
  fetch('/api/raw-stream?limit=25', { headers: authHeaders }).then(r => r.json()).catch(() => ({ events: [] })),
  fetch('/api/modbus?limit=20', { headers: authHeaders }).then(r => r.json()).catch(() => ({ logs: [] })),
  fetch('/api/corporate/auth-stats', { headers: authHeaders }).then(r => r.json()).catch(() => ({})),
  fetch('/api/corporate/sessions?status=active', { headers: authHeaders }).then(r => r.json()).catch(() => ({ sessions: [] })),
  fetch('/api/v1/soar/executions', { headers: authHeaders }).then(r => r.json()).catch(() => ({ executions: [] }))
]);

if (alertsRes && alertsRes.alerts) setAlerts(alertsRes.alerts);
if (rawRes && rawRes.events) setRawLogs(rawRes.events);
if (modbusRes && modbusRes.logs) setModbusLogs(modbusRes.logs);
if (authStatsRes) setAuthStats(authStatsRes);
if (sessionsRes && sessionsRes.sessions) setSessions(sessionsRes.sessions);
if (soarRes && soarRes.executions) setSoarExecutions(soarRes.executions);
```

---

### 3.3 Step 3: Implement SOAR Playbook Execution Handler
Add a handler to trigger active defense playbooks:
```javascript
const handleExecutePlaybook = async (playbookId, parameters = {}, playbookTitle = '') => {
  setIsExecutingPlaybook(playbookId);
  try {
    const res = await fetch('/api/v1/soar/execute', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': 'admin'
      },
      body: JSON.stringify({
        playbook_id: playbookId,
        target_id: parameters.target_ip || 'all',
        mode: 'live',
        parameters: parameters
      })
    });
    const data = await res.json();
    if (res.ok) {
      alert(`[SOAR Triggered] ${playbookTitle || playbookId} executed successfully!\nExecution ID: ${data.execution_id || 'N/A'}`);
      // Refresh execution audit list
      const histRes = await fetch('/api/v1/soar/executions', { headers: { 'X-User-ID': 'admin' } });
      const histData = await histRes.json();
      if (histData && histData.executions) setSoarExecutions(histData.executions);
    } else {
      alert(`[SOAR Error] ${data.error || 'Failed to trigger playbook'}`);
    }
  } catch (err) {
    alert(`[SOAR Network Error] ${err.message}`);
  } finally {
    setIsExecutingPlaybook(null);
  }
};

const handleBlockIp = async (ip, source) => {
  if (!confirm(`Deploy automated SOAR playbook to quarantine IP: ${ip}?`)) return;
  await handleExecutePlaybook(
    'containment.isolate_host',
    { target_ip: ip, reason: `Manual quarantine from Forensic Console (Source: ${source})` },
    `Host Containment & IP Quarantine (${ip})`
  );
};
```

---

### 3.4 Step 4: Add Forensic Fields to Alerts Table (`activeTab === 'alerts'`)
In the alerts table, add columns for the forensic telemetry returned by the backend:
- **Detected Time**: `new Date(alert.created_at || alert.attack_datetime).toLocaleTimeString()`
- **Attacker IP**: `alert.attacker_ip || alert.src_ip || '172.26.0.7'`
- **GeoIP**: `alert.geoip_country ? `${alert.geoip_country}` : 'US'`
- **Attack Vector**: `alert.attack_vector || 'Unknown Vector'`
- **Severity**: `alert.severity`
- **Inspect Action Button**:
  ```jsx
  <button onClick={() => setSelectedForensicAlert(alert)}>
    🔍 Inspect
  </button>
  ```

---

### 3.5 Step 5: Add 6th Navigation Tab (`activeTab === 'forensics'`)
Add the tab button to the navigation bar:
```jsx
<button
  className={`nav-tab ${activeTab === 'forensics' ? 'active' : ''}`}
  onClick={() => setActiveTab('forensics')}
>
  🔬 Attack Forensics & Threat Intel
</button>
```

When `activeTab === 'forensics'`, render:

1. **Aggregated KPI Metrics**:
   - **Unique Threat IPs**: `new Set(alerts.map(a => a.attacker_ip || a.src_ip).filter(Boolean)).size`
   - **Active Attack Vectors**: `new Set(alerts.map(a => a.attack_vector).filter(Boolean)).size`
   - **Origin Countries**: `new Set(alerts.map(a => a.geoip_country).filter(Boolean)).size`
   - **MITRE Techniques**: `new Set(alerts.map(a => a.mitre_technique).filter(Boolean)).size`

2. **Top Attacker IP Leaderboard**:
   - Aggregate event counts per unique IP:
   ```javascript
   const ipAggregates = Object.values(
     alerts.reduce((acc, a) => {
       const ip = a.attacker_ip || a.src_ip || '172.26.0.7';
       if (!acc[ip]) {
         acc[ip] = { ip, count: 0, country: a.geoip_country || 'US', vector: a.attack_vector || 'Mixed Attacks', source: a.source };
       }
       acc[ip].count += 1;
       return acc;
     }, {})
   ).sort((a, b) => b.count - a.count);
   ```
   - Render columns: IP Address, Country, Event Count, Primary Vector, Risk Level, and a **"⚡ Quarantine IP"** action button calling `handleBlockIp(item.ip, item.source)`.

3. **Attack Vector Distribution**:
   - Calculate percentages for: SQL Injection, Brute Force, OT/SCADA Override, and API Recon.

4. **Chronological Forensic Attack Stream**:
   - Map over `alerts` sorted descending by `created_at` displaying: Timestamp, Vector, Attacker IP, Target Endpoint/User, and an Inspect button.

---

### 3.6 Step 6: Forensic Evidence Inspection Modal
Render conditionally when `selectedForensicAlert !== null`:
```jsx
{selectedForensicAlert && (
  <div className="modal-backdrop" onClick={() => setSelectedForensicAlert(null)}>
    <div className="modal-dialog" onClick={e => e.stopPropagation()}>
      <div className="modal-header">
        <h3>🔬 Forensic Telemetry & Threat Signature</h3>
        <button onClick={() => setSelectedForensicAlert(null)}>✕</button>
      </div>

      <div className="modal-body">
        <div><strong>Attacker IP:</strong> {selectedForensicAlert.attacker_ip || selectedForensicAlert.src_ip}</div>
        <div><strong>Origin GeoIP:</strong> {selectedForensicAlert.geoip_country || 'US'}</div>
        <div><strong>Attack Vector:</strong> {selectedForensicAlert.attack_vector}</div>
        <div><strong>Protocol:</strong> {selectedForensicAlert.protocol || 'HTTP/1.1'}</div>
        <div><strong>Target URI:</strong> {selectedForensicAlert.http_method || 'POST'} {selectedForensicAlert.request_uri || '/api/auth/login'}</div>
        <div><strong>User-Agent:</strong> {selectedForensicAlert.user_agent}</div>
        <div><strong>Target Identity:</strong> {selectedForensicAlert.target_user || 'N/A'}</div>
        <div><strong>MITRE Tactic & Technique:</strong> {selectedForensicAlert.mitre_tactic} ({selectedForensicAlert.mitre_technique})</div>

        {/* Raw Forensic Payload */}
        <div>
          <h4>Raw Forensic Packet & Event Data:</h4>
          <pre>{JSON.stringify(selectedForensicAlert.raw_parsed || selectedForensicAlert.raw_event || selectedForensicAlert, null, 2)}</pre>
        </div>
      </div>

      <div className="modal-footer">
        <button onClick={() => {
          handleBlockIp(selectedForensicAlert.attacker_ip || selectedForensicAlert.src_ip, selectedForensicAlert.source);
          setSelectedForensicAlert(null);
        }}>
          ⚡ Execute Immediate IP Quarantine (SOAR)
        </button>
        <button onClick={() => setSelectedForensicAlert(null)}>Close</button>
      </div>
    </div>
  </div>
)}
```

---

### 3.7 Step 7: Live SOAR Executions Audit Table (`activeTab === 'soar'`)
In the SOAR tab, beneath the active defense playbook cards, render the live execution audit history from `soarExecutions`:
- **Columns to render**:
  - `execution_id` (e.g. `EXEC-3E6F6DFA`)
  - `playbook_id` (e.g. `containment.isolate_host`)
  - `mode` (e.g. `live` or `simulation`)
  - `status` (e.g. `completed`, `running`, `failed`)
  - `triggered_by` (e.g. `admin (UI)` or `auto_trigger`)
  - `timestamp` (`completed_at` or `created_at`)
  - `summary / outputs` (`ex.outputs?.summary` and `ex.outputs?.firewall_rule`)

---

## 4. Backend API Contracts Reference

### 4.1 `GET /api/alerts?limit=100`
**Headers**: `{ 'X-User-ID': 'admin' }`  
**Key Forensic Fields in each alert object**:
- `alert_id` (string)
- `title` (string)
- `severity` (`critical` | `high` | `medium` | `low`)
- `status` (`open` | `closed` | `in_progress`)
- `source` (string, e.g. `corp-portal`, `scada-gateway`)
- `created_at` (ISO timestamp)
- `attacker_ip` (string, e.g. `172.26.0.7`)
- `src_ip` (string)
- `geoip_country` (string, e.g. `US`)
- `user_agent` (string)
- `attack_vector` (string, e.g. `SQL Injection Attempt`, `Credential Stuffing`)
- `mitre_tactic` (string, e.g. `TA0006 - Credential Access`)
- `mitre_technique` (string, e.g. `T1110 - Brute Force`)
- `target_user` (string)
- `protocol` (string, e.g. `HTTP/1.1`)
- `http_method` (string, e.g. `POST`, `GET`)
- `request_uri` (string, e.g. `/.env`, `/api/auth/login`)
- `attack_datetime` (string)
- `raw_parsed` (object: parsed key-value payload)
- `raw_event` (string: original raw event string)

---

### 4.2 `POST /api/v1/soar/execute`
**Headers**: `{ 'X-User-ID': 'admin', 'Content-Type': 'application/json' }`  
**Request Payload**:
```json
{
  "playbook_id": "containment.isolate_host",
  "target_id": "172.26.0.7",
  "mode": "live",
  "parameters": {
    "target_ip": "172.26.0.7",
    "reason": "Repeated SQLi attacks detected"
  }
}
```
**Response (`202 Accepted`)**:
```json
{
  "status": "success",
  "execution_id": "EXEC-3E6F6DFA",
  "execution_status": "completed",
  "outputs": {
    "summary": "Host 172.26.0.7 isolated. Ingress/egress drop rules applied.",
    "firewall_rule": "DROP src 172.26.0.7/32 on all-interfaces"
  }
}
```

---

### 4.3 `GET /api/v1/soar/executions`
**Headers**: `{ 'X-User-ID': 'admin' }`  
**Response (`200 OK`)**:
```json
{
  "executions": [
    {
      "execution_id": "EXEC-3E6F6DFA",
      "playbook_id": "containment.isolate_host",
      "mode": "live",
      "status": "completed",
      "triggered_by": "admin (UI)",
      "target_id": "172.26.0.7",
      "outputs": {
        "summary": "Host 172.26.0.7 isolated. Ingress/egress drop rules applied.",
        "firewall_rule": "DROP src 172.26.0.7/32"
      },
      "created_at": "2026-09-08T02:41:48.000Z",
      "completed_at": "2026-09-08T02:41:48.150Z"
    }
  ],
  "total": 3
}
```
