# Frontend-Backend Integration Guide

## Overview

This document explains how to connect the React frontend apps to the GOTXA backend API and update static data with live API calls.

## Backend API Summary

**Base URL:** `http://localhost:5000/api`

**Authentication:** Pass `X-User-ID: admin` header (or bearer token in production)

**Documentation:** See `API_ENDPOINTS.md` for complete endpoint reference

---

## Key Differences from Static Data

### Authentication
| Method | Demo | Production |
|--------|------|-------------|
| Header | `X-User-ID: admin` | `Authorization: Bearer <jwt>` |
| Auto-create User | Yes | No |
| Default Role | admin | Determined by JWT |

### Response Format
All API responses follow this structure:
```json
{
  "data": { /* actual data */ },
  "message": "Success",
  "timestamp": "2026-08-14T10:30:45.123456"
}
```

---

## 1. SIEM Dashboard Integration

### Current: Static Data
```javascript
// frontend/siem_dashboard/src/App.jsx
const [dashboard, setDashboard] = useState({
  totalAlerts: 42,
  criticalAlerts: 3,
  openIncidents: 5,
  // ... static data
});
```

### New: Live API

**Endpoint:** `GET /api/overview`

**React Implementation:**
```javascript
import { useEffect, useState } from 'react';

export default function SIEMDashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/overview', {
          headers: {
            'X-User-ID': 'admin',
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }

        const json = await response.json();
        setDashboard(json.data); // Extract data from response wrapper
        setError(null);
      } catch (err) {
        setError(err.message);
        console.error('Dashboard fetch failed:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchDashboard, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  // Use dashboard data
  return (
    <div>
      <h1>KPI Cards</h1>
      <div>{dashboard.kpis.total_open_alerts} Open Alerts</div>
      <div>{dashboard.kpis.critical_alerts} Critical</div>
      {/* ... rest of dashboard */}
    </div>
  );
}
```

---

## 2. Raw Logs Tab Integration

### Current: Static Array
```javascript
const logs = [
  { timestamp: '10:30:45', level: 'WARNING', message: 'High CPU usage' },
  // ... static logs
];
```

### New: Live Streaming

**Endpoint:** `GET /api/raw-stream?limit=50`

**React Implementation:**
```javascript
import { useEffect, useState } from 'react';

export default function RawLogs() {
  const [logs, setLogs] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [loading, setLoading] = useState(false);

  // Initial load
  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async (nextCursor = null) => {
    try {
      setLoading(true);
      const url = new URL('http://localhost:5000/api/raw-stream');
      url.searchParams.append('limit', '50');
      if (nextCursor) {
        url.searchParams.append('cursor', nextCursor);
      }

      const response = await fetch(url, {
        headers: { 'X-User-ID': 'admin' }
      });

      const json = await response.json();
      
      if (nextCursor) {
        // Append to existing logs
        setLogs([...logs, ...json.data.items]);
      } else {
        // Replace with new logs
        setLogs(json.data.items);
      }
      
      setCursor(json.data.next_cursor);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Level</th>
            <th>Host</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id}>
              <td>{log.timestamp}</td>
              <td>{log.level}</td>
              <td>{log.host}</td>
              <td>{log.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {cursor && (
        <button onClick={() => fetchLogs(cursor)}>Load More</button>
      )}
    </div>
  );
}
```

---

## 3. SOAR Tab Integration

### Current: Static Actions
```javascript
const actions = [
  { id: '1', name: 'Isolate Host', status: 'ready' },
  { id: '2', name: 'Reset Credentials', status: 'ready' }
];
```

### New: Live Playbooks

**Endpoints:**
- `GET /api/v1/soar/actions` - List available actions
- `POST /api/v1/soar/execute` - Execute action
- `GET /api/v1/soar/history` - Execution history

**React Implementation:**
```javascript
import { useEffect, useState } from 'react';

export default function SOARTab() {
  const [actions, setActions] = useState([]);
  const [history, setHistory] = useState([]);
  const [executing, setExecuting] = useState(null);

  // Fetch available actions
  useEffect(() => {
    const fetchActions = async () => {
      const response = await fetch('http://localhost:5000/api/v1/soar/actions', {
        headers: { 'X-User-ID': 'admin' }
      });
      const json = await response.json();
      setActions(json.data.actions);
    };

    fetchActions();
  }, []);

  // Fetch execution history
  useEffect(() => {
    const fetchHistory = async () => {
      const response = await fetch('http://localhost:5000/api/v1/soar/history', {
        headers: { 'X-User-ID': 'admin' }
      });
      const json = await response.json();
      setHistory(json.data.items);
    };

    fetchHistory();
    const interval = setInterval(fetchHistory, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, []);

  // Execute action
  const handleExecute = async (action) => {
    try {
      setExecuting(action.id);

      const response = await fetch('http://localhost:5000/api/v1/soar/execute', {
        method: 'POST',
        headers: {
          'X-User-ID': 'admin',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          action_id: action.id,
          parameters: {
            hostname: 'server-01' // From incident context
          },
          reason: 'Security incident response',
          change_ticket: 'CHG-123456'
        })
      });

      const json = await response.json();

      if (response.ok) {
        alert(`Playbook started: ${json.data.execution_id}`);
        // Refresh history
        const historyResponse = await fetch('http://localhost:5000/api/v1/soar/history', {
          headers: { 'X-User-ID': 'admin' }
        });
        const historyJson = await historyResponse.json();
        setHistory(historyJson.data.items);
      } else {
        alert(`Error: ${json.error.message}`);
      }
    } catch (err) {
      console.error('Execution failed:', err);
    } finally {
      setExecuting(null);
    }
  };

  return (
    <div>
      <h2>Available Playbooks</h2>
      {actions.map((action) => (
        <div key={action.id}>
          <h3>{action.name}</h3>
          <p>{action.description}</p>
          <p>Risk: {action.risk_level} | Approval Required: {action.requires_approval ? 'Yes' : 'No'}</p>
          <button 
            onClick={() => handleExecute(action)}
            disabled={executing === action.id}
          >
            {executing === action.id ? 'Executing...' : 'Execute'}
          </button>
        </div>
      ))}

      <h2>Execution History</h2>
      <table>
        <thead>
          <tr>
            <th>Execution ID</th>
            <th>Playbook</th>
            <th>Status</th>
            <th>Triggered By</th>
            <th>Started</th>
            <th>Completed</th>
          </tr>
        </thead>
        <tbody>
          {history.map((exec) => (
            <tr key={exec.execution_id}>
              <td>{exec.execution_id}</td>
              <td>{exec.playbook_id}</td>
              <td>{exec.status}</td>
              <td>{exec.triggered_by}</td>
              <td>{new Date(exec.created_at).toLocaleString()}</td>
              <td>{exec.completed_at ? new Date(exec.completed_at).toLocaleString() : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## 4. Alerts List Integration

### Current: Static Array
```javascript
const alerts = [
  { id: 1, title: 'Suspicious Login', severity: 'high', status: 'open' },
  // ... static alerts
];
```

### New: Live Alerts

**Endpoint:** `GET /api/alerts?page=1&severity=critical&status=open`

**React Implementation:**
```javascript
import { useEffect, useState } from 'react';

export default function AlertsList() {
  const [alerts, setAlerts] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState({ severity: '', status: 'open' });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        setLoading(true);

        const url = new URL('http://localhost:5000/api/alerts');
        url.searchParams.append('page', page);
        url.searchParams.append('page_size', '25');
        
        if (filter.severity) url.searchParams.append('severity', filter.severity);
        if (filter.status) url.searchParams.append('status', filter.status);

        const response = await fetch(url, {
          headers: { 'X-User-ID': 'admin' }
        });

        const json = await response.json();
        setAlerts(json.data.items);
        setTotal(json.data.total);
      } catch (err) {
        console.error('Failed to fetch alerts:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
  }, [page, filter]);

  const handleBulkAssign = async (selectedIds) => {
    try {
      const response = await fetch('http://localhost:5000/api/alerts/bulk-assign', {
        method: 'POST',
        headers: {
          'X-User-ID': 'admin',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          alert_ids: selectedIds,
          assignee_id: 'analyst-uuid',
          reason: 'Bulk assignment from dashboard'
        })
      });

      if (response.ok) {
        alert('Alerts assigned successfully');
        // Refresh alerts
        setPage(1);
      }
    } catch (err) {
      console.error('Bulk assign failed:', err);
    }
  };

  return (
    <div>
      <h2>Alerts</h2>

      <div>
        <label>Severity:</label>
        <select 
          value={filter.severity}
          onChange={(e) => {
            setFilter({ ...filter, severity: e.target.value });
            setPage(1);
          }}
        >
          <option value="">All</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        <label>Status:</label>
        <select 
          value={filter.status}
          onChange={(e) => {
            setFilter({ ...filter, status: e.target.value });
            setPage(1);
          }}
        >
          <option value="open">Open</option>
          <option value="investigating">Investigating</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
      </div>

      {loading ? (
        <div>Loading...</div>
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Source</th>
                <th>Assigned To</th>
                <th>Detected</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert) => (
                <tr key={alert.id}>
                  <td>{alert.alert_id}</td>
                  <td>{alert.title}</td>
                  <td>{alert.severity}</td>
                  <td>{alert.status}</td>
                  <td>{alert.source}</td>
                  <td>{alert.assignee_name || 'Unassigned'}</td>
                  <td>{new Date(alert.detected_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div>
            <button 
              onClick={() => setPage(page - 1)} 
              disabled={page === 1}
            >
              Previous
            </button>
            <span>Page {page} of {Math.ceil(total / 25)}</span>
            <button 
              onClick={() => setPage(page + 1)} 
              disabled={page >= Math.ceil(total / 25)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
```

---

## 5. API Context Helper

Create a shared API service to centralize all backend calls:

**File: `frontend/lib/api.js`**

```javascript
const API_BASE = 'http://localhost:5000/api';
const USER_ID = 'admin'; // From auth context in production

export const apiCall = async (method, endpoint, body = null) => {
  const options = {
    method,
    headers: {
      'X-User-ID': USER_ID,
      'Content-Type': 'application/json'
    }
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, options);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.message || 'API error');
  }

  const data = await response.json();
  return data.data; // Return unwrapped data
};

// Convenience functions
export const alertsAPI = {
  list: (page = 1, filters = {}) => 
    apiCall('GET', `/alerts?page=${page}&${new URLSearchParams(filters)}`),
  
  get: (id) => 
    apiCall('GET', `/alerts/${id}`),
  
  bulkAssign: (alertIds, assigneeId, reason) => 
    apiCall('POST', '/alerts/bulk-assign', { alert_ids: alertIds, assignee_id: assigneeId, reason }),
  
  suppress: (id, reason, scope = 'single', durationHours = 24) => 
    apiCall('POST', `/alerts/${id}/suppress`, { reason, scope, duration_hours: durationHours }),
  
  updateStatus: (id, status, reason) => 
    apiCall('PUT', `/alerts/${id}/status`, { status, reason })
};

export const incidentsAPI = {
  list: (page = 1, filters = {}) => 
    apiCall('GET', `/incidents?page=${page}&${new URLSearchParams(filters)}`),
  
  get: (id) => 
    apiCall('GET', `/incidents/${id}`),
  
  create: (title, severity, description = '') => 
    apiCall('POST', '/incidents', { title, severity, description }),
  
  updateStatus: (id, status, reason = '') => 
    apiCall('PUT', `/incidents/${id}/status`, { status, reason }),
  
  assign: (id, ownerId) => 
    apiCall('POST', `/incidents/${id}/assign`, { owner_id: ownerId }),
  
  linkAlert: (id, alertId) => 
    apiCall('POST', `/incidents/${id}/link-alert`, { alert_id: alertId })
};

export const soarAPI = {
  listActions: () => 
    apiCall('GET', '/v1/soar/actions'),
  
  execute: (actionId, parameters = {}, reason = '', changeTicket = '') => 
    apiCall('POST', '/v1/soar/execute', { action_id: actionId, parameters, reason, change_ticket: changeTicket }),
  
  history: (page = 1) => 
    apiCall('GET', `/v1/soar/history?page=${page}`)
};

export const dashboardAPI = {
  overview: () => 
    apiCall('GET', '/overview'),
  
  rawStream: (limit = 50, cursor = null) => {
    let endpoint = `/raw-stream?limit=${limit}`;
    if (cursor) endpoint += `&cursor=${cursor}`;
    return apiCall('GET', endpoint);
  }
};

export const capabilitiesAPI = {
  list: () => 
    apiCall('GET', '/capabilities')
};
```

**Usage in components:**

```javascript
import { alertsAPI, soarAPI, dashboardAPI } from '../lib/api';

export default function AlertsComponent() {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    alertsAPI.list(1, { severity: 'critical' })
      .then(data => setAlerts(data.items))
      .catch(err => console.error(err));
  }, []);

  const handleAssign = async (alertIds) => {
    await alertsAPI.bulkAssign(alertIds, 'analyst-uuid', 'Investigation');
  };

  // ...
}
```

---

## 6. CORS Configuration

The backend is configured with CORS enabled for all origins. In production, update `main.py`:

```python
from flask_cors import CORS

# Restrict to your frontend domain
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://yourdomain.com"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "X-User-ID"]
    }
})
```

---

## 7. Error Handling

All errors follow this format:
```json
{
  "error": {
    "code": "Forbidden",
    "message": "Permission denied: alerts.assign",
    "details": {}
  }
}
```

Standard HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not found
- `409` - Conflict (e.g., invalid state transition)
- `500` - Server error

---

## 8. Testing Locally

Start both backend and frontend:

```bash
# Terminal 1 - Backend
cd backend
python main.py

# Terminal 2 - Frontend
cd frontend/siem_dashboard
npm run dev
```

Access: `http://localhost:5173`

Test endpoints:
```bash
# Terminal 3
curl -H "X-User-ID: admin" http://localhost:5000/api/overview
```

---

## 9. Production Considerations

1. **Use JWT tokens** instead of X-User-ID header
2. **Enable HTTPS** for all API calls
3. **Add rate limiting** to prevent abuse
4. **Implement caching** for frequently accessed endpoints
5. **Use connection pooling** for database
6. **Monitor API response times**
7. **Set up alerts** for API failures
8. **Use API versioning** (`/api/v1/` prefix already in place)

---

## Summary

| Component | Static | Live API | Endpoint |
|-----------|--------|----------|----------|
| Overview KPIs | Array | Fetch | `GET /api/overview` |
| Alerts List | Array | Paginated | `GET /api/alerts` |
| Raw Logs | Array | Streaming | `GET /api/raw-stream` |
| SOAR Actions | Array | Fetch | `GET /api/v1/soar/actions` |
| SOAR History | Array | Paginated | `GET /api/v1/soar/history` |
| Incidents | Array | Paginated | `GET /api/incidents` |

All changes use the `X-User-ID: admin` header for authentication in demo mode.
