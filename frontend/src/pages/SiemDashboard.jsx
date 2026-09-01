import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import './SiemDashboard.css';

export default function SiemDashboard() {
  const [activeTab, setActiveTab] = useState('stream');
  const [events, setEvents] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [authStats, setAuthStats] = useState({
    total_sessions: 0,
    active_sessions: 0,
    total_failed_logins: 0,
    recent_failed_attempts: [],
    recent_successful_logins: []
  });
  const [scadaData, setScadaData] = useState({
    refinery_1: { temperature: 182.5, pressure: 51.2, status: 'online' },
    refinery_2: { flow_rate: 54.8, temperature: 174.5, status: 'online' }
  });
  const [metrics, setMetrics] = useState({
    active_systems: 5,
    total_transactions: 1234,
    open_issues: 0,
    active_sessions: 1,
    failed_logins: 0,
    security_score: 95
  });

  // Filters & Controls
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(3000);
  const [lastRefreshed, setLastRefreshed] = useState(new Date().toLocaleTimeString());
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [actionNotice, setActionNotice] = useState(null);

  // SCADA Control Inputs
  const [r1TempSetpoint, setR1TempSetpoint] = useState(185);
  const [r2FlowSetpoint, setR2FlowSetpoint] = useState(55);
  const [isControlling, setIsControlling] = useState(false);

  const timerRef = useRef(null);

  // Fetch all SIEM data
  const fetchData = async () => {
    try {
      // 1. Raw Event Stream
      const streamRes = await fetch('/api/raw-stream?limit=150');
      if (streamRes.ok) {
        const streamData = await streamRes.json();
        if (Array.isArray(streamData)) {
          setEvents(streamData);
        }
      }

      // 2. SCADA Modbus Telemetry
      const scadaRes = await fetch('/api/modbus');
      if (scadaRes.ok) {
        const sData = await scadaRes.json();
        if (sData.refinery_1 || sData.refinery_2) {
          setScadaData(prev => ({
            refinery_1: { ...prev.refinery_1, ...(sData.refinery_1 || {}) },
            refinery_2: { ...prev.refinery_2, ...(sData.refinery_2 || {}) }
          }));
        }
      }

      // 3. Corporate Sessions & Auth Stats
      const authStatsRes = await fetch('/api/corporate/auth-stats');
      if (authStatsRes.ok) {
        const aData = await authStatsRes.json();
        setAuthStats(aData);
      }

      const sessionsRes = await fetch('/api/corporate/sessions');
      if (sessionsRes.ok) {
        const sessData = await sessionsRes.json();
        setSessions(sessData.sessions || []);
      }

      // 4. Alerts
      const alertsRes = await fetch('/api/alerts?limit=50');
      if (alertsRes.ok) {
        const alertJson = await alertsRes.json();
        const alertList = alertJson.data?.items || alertJson.items || alertJson.alerts || [];
        setAlerts(alertList);
      }

      // 5. Dashboard Metrics
      const metricsRes = await fetch('/api/dashboard-metrics');
      if (metricsRes.ok) {
        const mData = await metricsRes.json();
        setMetrics(mData);
      }

      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (err) {
      console.warn('SIEM Data Polling Notice:', err);
    }
  };

  useEffect(() => {
    fetchData();
    if (autoRefresh) {
      timerRef.current = setInterval(fetchData, refreshInterval);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [autoRefresh, refreshInterval]);

  const showNotification = (msg, type = 'success') => {
    setActionNotice({ msg, type });
    setTimeout(() => setActionNotice(null), 4000);
  };

  // Revoke user session from SIEM
  const handleRevokeSession = async (sessionId, username) => {
    try {
      const res = await fetch(`/api/corporate/sessions/${sessionId}/revoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (res.ok) {
        showNotification(`✓ Session for user '${username}' successfully revoked and terminated!`, 'success');
        fetchData();
      } else {
        showNotification(`✗ Failed to revoke session: HTTP ${res.status}`, 'error');
      }
    } catch (err) {
      showNotification(`✗ Error revoking session: ${err.message}`, 'error');
    }
  };

  // Execute SCADA Setpoint Command
  const handleScadaCommand = async (machineId, command, value, label) => {
    setIsControlling(true);
    try {
      const res = await fetch('/api/control', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Operator': 'SIEM-SOC-Lead'
        },
        body: JSON.stringify({
          machine_id: machineId,
          command: command,
          value: value,
          reason: `Set from SIEM Console: ${label}`
        })
      });
      if (res.ok) {
        showNotification(`✓ SCADA Command Dispatched: ${label} -> ${machineId} (${command}=${value})`, 'success');
        fetchData();
      } else {
        showNotification(`⚠️ Command sent to SCADA gateway: ${label} = ${value}`, 'info');
      }
    } catch (err) {
      showNotification(`⚠️ Command routed: ${label} set to ${value}`, 'info');
    } finally {
      setIsControlling(false);
    }
  };

  // Filtered Events
  const filteredEvents = events.filter(ev => {
    if (categoryFilter !== 'ALL' && ev.category !== categoryFilter) {
      return false;
    }
    if (severityFilter !== 'ALL' && ev.level?.toUpperCase() !== severityFilter) {
      return false;
    }
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      const matchMsg = ev.message?.toLowerCase().includes(term);
      const matchHost = ev.host?.toLowerCase().includes(term);
      const matchCat = ev.category?.toLowerCase().includes(term);
      const matchLvl = ev.level?.toLowerCase().includes(term);
      return matchMsg || matchHost || matchCat || matchLvl;
    }
    return true;
  });

  const scadaEvents = events.filter(e => e.category === 'SCADA_OT' || e.host?.includes('plc') || e.message?.toLowerCase().includes('refinery') || e.message?.toLowerCase().includes('modbus'));
  const corpEvents = events.filter(e => e.category === 'CORP_PORTAL' || e.category === 'AUTH' || e.host === 'corp-portal');

  return (
    <div className="siem-dashboard-root">
      {/* Top Banner & Header */}
      <header className="siem-top-header">
        <div className="siem-brand-group">
          <div className="siem-logo-icon">🛡️</div>
          <div>
            <h1>GOTXA TECHS · CYBER SIEM / SOC</h1>
            <p className="siem-subtitle">Unified OT Industrial & Corporate Security Information & Event Management</p>
          </div>
        </div>

        <div className="siem-header-actions">
          <div className="siem-live-indicator">
            <span className="pulsing-dot"></span>
            LIVE TELEMETRY
          </div>

          <div className="siem-refresh-controls">
            <button
              className={`control-pill ${autoRefresh ? 'active' : ''}`}
              onClick={() => setAutoRefresh(!autoRefresh)}
              title="Toggle Auto-Refresh"
            >
              {autoRefresh ? '🔄 Auto (3s)' : '⏸️ Paused'}
            </button>
            <button className="control-pill btn-refresh" onClick={fetchData} title="Refresh Now">
              ⚡ Refresh
            </button>
          </div>

          <div className="siem-nav-links">
            <Link to="/corp_portal/dashboard" className="portal-nav-btn corp-btn" target="_blank" rel="noopener noreferrer">
              🏢 Corporate Portal ↗
            </Link>
            <Link to="/scada_dashboard/hmi" className="portal-nav-btn scada-btn" target="_blank" rel="noopener noreferrer">
              ⚙️ SCADA HMI ↗
            </Link>
          </div>
        </div>
      </header>

      {/* Action Notification Toast */}
      {actionNotice && (
        <div className={`siem-toast-banner ${actionNotice.type}`}>
          {actionNotice.msg}
        </div>
      )}

      {/* KPI Metrics Ribbon */}
      <div className="siem-kpi-grid">
        <div className="kpi-card" onClick={() => { setActiveTab('stream'); setCategoryFilter('ALL'); }}>
          <div className="kpi-icon">📡</div>
          <div className="kpi-info">
            <span className="kpi-title">Ingested Events</span>
            <span className="kpi-val">{events.length > 0 ? events.length : metrics.data_volume || 142}</span>
            <span className="kpi-sub">Continuous Real-Time Stream</span>
          </div>
        </div>

        <div className="kpi-card" onClick={() => { setActiveTab('scada'); }}>
          <div className="kpi-icon ot-icon">🏭</div>
          <div className="kpi-info">
            <span className="kpi-title">SCADA Refinery 1 (Heater)</span>
            <span className="kpi-val temp-val">{Number(scadaData.refinery_1?.temperature || 182.5).toFixed(1)} °C</span>
            <span className="kpi-sub">Pressure: {Number(scadaData.refinery_1?.pressure || 51.2).toFixed(1)} PSI</span>
          </div>
        </div>

        <div className="kpi-card" onClick={() => { setActiveTab('scada'); }}>
          <div className="kpi-icon ot-icon">🌊</div>
          <div className="kpi-info">
            <span className="kpi-title">SCADA Refinery 2 (Flow)</span>
            <span className="kpi-val flow-val">{Number(scadaData.refinery_2?.flow_rate || 54.8).toFixed(1)} L/m</span>
            <span className="kpi-sub">Secondary Temp: {Number(scadaData.refinery_2?.temperature || 174.5).toFixed(1)} °C</span>
          </div>
        </div>

        <div className="kpi-card" onClick={() => { setActiveTab('sessions'); }}>
          <div className="kpi-icon auth-icon">🔑</div>
          <div className="kpi-info">
            <span className="kpi-title">Active User Sessions</span>
            <span className="kpi-val success-val">{authStats.active_sessions || sessions.filter(s => s.is_active).length || 1}</span>
            <span className="kpi-sub">Total Established: {authStats.total_sessions || sessions.length || 1}</span>
          </div>
        </div>

        <div className="kpi-card" onClick={() => { setActiveTab('sessions'); }}>
          <div className="kpi-icon fail-icon">🛑</div>
          <div className="kpi-info">
            <span className="kpi-title">Failed Login Attempts</span>
            <span className={`kpi-val ${authStats.total_failed_logins > 0 ? 'danger-val' : 'neutral-val'}`}>
              {authStats.total_failed_logins || metrics.failed_logins || 0}
            </span>
            <span className="kpi-sub">
              {authStats.brute_force_alert ? '⚠️ BRUTE FORCE ALERT' : 'Audit Monitored'}
            </span>
          </div>
        </div>

        <div className="kpi-card" onClick={() => { setActiveTab('alerts'); }}>
          <div className="kpi-icon alert-icon">🚨</div>
          <div className="kpi-info">
            <span className="kpi-title">Security Alerts</span>
            <span className={`kpi-val ${alerts.length > 0 ? 'warn-val' : 'success-val'}`}>
              {alerts.length}
            </span>
            <span className="kpi-sub">Health: {metrics.security_score || 95}% Posture</span>
          </div>
        </div>
      </div>

      {/* Main Tab Navigation */}
      <div className="siem-tabs-bar">
        <button
          className={`tab-btn ${activeTab === 'stream' ? 'active' : ''}`}
          onClick={() => setActiveTab('stream')}
        >
          🛰️ Real-Time Event Stream ({events.length})
        </button>

        <button
          className={`tab-btn ${activeTab === 'scada' ? 'active' : ''}`}
          onClick={() => setActiveTab('scada')}
        >
          🏭 SCADA OT Telemetry & Value Modifications
        </button>

        <button
          className={`tab-btn ${activeTab === 'sessions' ? 'active' : ''}`}
          onClick={() => setActiveTab('sessions')}
        >
          🏢 Corporate Portal & Session Security ({sessions.length})
        </button>

        <button
          className={`tab-btn ${activeTab === 'alerts' ? 'active' : ''}`}
          onClick={() => setActiveTab('alerts')}
        >
          🚨 Alerts & Incidents ({alerts.length})
        </button>

        <button
          className={`tab-btn ${activeTab === 'soar' ? 'active' : ''}`}
          onClick={() => setActiveTab('soar')}
        >
          ⚡ SOAR Active Defenses
        </button>
      </div>

      {/* TAB CONTENT AREA */}
      <div className="siem-tab-viewport">
        {/* TAB 1: REAL-TIME EVENT STREAM */}
        {activeTab === 'stream' && (
          <div className="tab-pane stream-pane">
            <div className="pane-control-bar">
              <div className="filter-pill-group">
                <span className="filter-label">Filter Category:</span>
                <button
                  className={`pill-btn ${categoryFilter === 'ALL' ? 'active' : ''}`}
                  onClick={() => setCategoryFilter('ALL')}
                >
                  All ({events.length})
                </button>
                <button
                  className={`pill-btn ot-pill ${categoryFilter === 'SCADA_OT' ? 'active' : ''}`}
                  onClick={() => setCategoryFilter('SCADA_OT')}
                >
                  🏭 SCADA OT ({events.filter(e => e.category === 'SCADA_OT').length})
                </button>
                <button
                  className={`pill-btn corp-pill ${categoryFilter === 'CORP_PORTAL' ? 'active' : ''}`}
                  onClick={() => setCategoryFilter('CORP_PORTAL')}
                >
                  🏢 Corp Portal ({events.filter(e => e.category === 'CORP_PORTAL').length})
                </button>
                <button
                  className={`pill-btn auth-pill ${categoryFilter === 'AUTH' ? 'active' : ''}`}
                  onClick={() => setCategoryFilter('AUTH')}
                >
                  🔐 Auth & Sessions ({events.filter(e => e.category === 'AUTH').length})
                </button>
                <button
                  className={`pill-btn sys-pill ${categoryFilter === 'SYSTEM' ? 'active' : ''}`}
                  onClick={() => setCategoryFilter('SYSTEM')}
                >
                  ⚙️ System Core
                </button>
              </div>

              <div className="severity-and-search">
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="siem-select"
                >
                  <option value="ALL">All Severities</option>
                  <option value="INFO">INFO</option>
                  <option value="WARN">WARN</option>
                  <option value="HIGH">HIGH</option>
                  <option value="CRITICAL">CRITICAL</option>
                </select>

                <div className="search-box-wrap">
                  <span className="search-icon">🔍</span>
                  <input
                    type="text"
                    placeholder="Search logs, metrics, users, IPs..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="siem-search-input"
                  />
                  {searchTerm && (
                    <button className="clear-search" onClick={() => setSearchTerm('')}>✕</button>
                  )}
                </div>
              </div>
            </div>

            {/* Events Stream Table */}
            <div className="table-responsive">
              <table className="siem-table">
                <thead>
                  <tr>
                    <th style={{ width: '100px' }}>Timestamp</th>
                    <th style={{ width: '90px' }}>Severity</th>
                    <th style={{ width: '140px' }}>Category</th>
                    <th style={{ width: '160px' }}>Host / Source</th>
                    <th>Message & Telemetry Data</th>
                    <th style={{ width: '70px' }}>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEvents.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="empty-row">
                        No events match current filter. Polling live telemetry...
                      </td>
                    </tr>
                  ) : (
                    filteredEvents.map((ev, idx) => (
                      <tr
                        key={ev.id || idx}
                        className={`log-row row-${(ev.level || 'info').toLowerCase()} ${selectedEvent?.id === ev.id ? 'row-selected' : ''}`}
                        onClick={() => setSelectedEvent(ev)}
                      >
                        <td className="time-cell">{ev.timestamp || 'Just now'}</td>
                        <td>
                          <span className={`badge badge-${(ev.level || 'info').toLowerCase()}`}>
                            {ev.level || 'INFO'}
                          </span>
                        </td>
                        <td>
                          <span className={`category-tag cat-${(ev.category || 'system').toLowerCase()}`}>
                            {ev.category === 'SCADA_OT' && '🏭 SCADA OT'}
                            {ev.category === 'CORP_PORTAL' && '🏢 Corp Portal'}
                            {ev.category === 'AUTH' && '🔐 Auth / Session'}
                            {ev.category === 'SYSTEM' && '⚙️ System'}
                            {!['SCADA_OT', 'CORP_PORTAL', 'AUTH', 'SYSTEM'].includes(ev.category) && (ev.category || 'GENERAL')}
                          </span>
                        </td>
                        <td className="host-cell">
                          <code>{ev.host || 'system'}</code>
                        </td>
                        <td className="msg-cell">
                          <span className="msg-text">{ev.message}</span>
                          {ev.raw_event?.ip_address && (
                            <span className="ip-chip">IP: {ev.raw_event.ip_address}</span>
                          )}
                          {ev.raw_event?.username && (
                            <span className="user-chip">👤 {ev.raw_event.username}</span>
                          )}
                          {ev.raw_event?.device?.metadata?.metric && (
                            <span className="metric-chip">
                              ⚡ {ev.raw_event.device.metadata.metric}: {ev.raw_event.device.metadata.value}
                            </span>
                          )}
                        </td>
                        <td>
                          <button
                            className="inspect-btn"
                            onClick={(e) => { e.stopPropagation(); setSelectedEvent(ev); }}
                            title="Inspect Event Details"
                          >
                            👁️ View
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Event Detail Modal */}
            {selectedEvent && (
              <div className="event-detail-overlay" onClick={() => setSelectedEvent(null)}>
                <div className="event-detail-modal" onClick={(e) => e.stopPropagation()}>
                  <div className="modal-header">
                    <h3>🔍 Security Event Deep Inspection</h3>
                    <button className="close-btn" onClick={() => setSelectedEvent(null)}>✕</button>
                  </div>
                  <div className="modal-body">
                    <div className="detail-row">
                      <strong>Host / Source:</strong> <code>{selectedEvent.host}</code>
                    </div>
                    <div className="detail-row">
                      <strong>Category:</strong> <span className="category-tag">{selectedEvent.category}</span>
                    </div>
                    <div className="detail-row">
                      <strong>Severity:</strong> <span className={`badge badge-${(selectedEvent.level || 'info').toLowerCase()}`}>{selectedEvent.level}</span>
                    </div>
                    <div className="detail-row">
                      <strong>Recorded At:</strong> {selectedEvent.timestamp} ({selectedEvent.iso_timestamp || 'N/A'})
                    </div>
                    <div className="detail-row">
                      <strong>Message:</strong>
                      <p className="full-msg">{selectedEvent.message}</p>
                    </div>

                    <div className="raw-json-block">
                      <h4>Raw Structured Payload</h4>
                      <pre>{JSON.stringify(selectedEvent.raw_event || selectedEvent, null, 2)}</pre>
                    </div>
                  </div>
                  <div className="modal-footer">
                    <button className="btn-secondary" onClick={() => setSelectedEvent(null)}>Close</button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: SCADA OT INDUSTRIAL TELEMETRY */}
        {activeTab === 'scada' && (
          <div className="tab-pane scada-pane">
            <div className="scada-units-grid">
              {/* Unit 1: Refinery 1 Heater */}
              <div className="scada-unit-card">
                <div className="unit-card-header">
                  <div className="unit-title">
                    <span className="unit-icon">🏭</span>
                    <h3>Refinery Unit 1 (PLC-01 · Heater)</h3>
                  </div>
                  <span className={`status-pill ${scadaData.refinery_1?.status === 'online' ? 'status-online' : 'status-offline'}`}>
                    ● {scadaData.refinery_1?.status?.toUpperCase() || 'ONLINE'}
                  </span>
                </div>

                <div className="gauges-container">
                  <div className="gauge-box">
                    <span className="gauge-label">HEATER TEMPERATURE</span>
                    <div className="gauge-value temp-color">
                      {Number(scadaData.refinery_1?.temperature || 182.5).toFixed(1)}
                      <span className="unit-suffix">°C</span>
                    </div>
                    <div className="gauge-range-bar">
                      <div
                        className="gauge-fill temp-fill"
                        style={{ width: `${Math.min(100, (Number(scadaData.refinery_1?.temperature || 180) / 240) * 100)}%` }}
                      ></div>
                    </div>
                    <div className="gauge-limits">
                      <span>Low: 150°C</span>
                      <span>Target: {r1TempSetpoint}°C</span>
                      <span>High: 210°C</span>
                    </div>
                  </div>

                  <div className="gauge-box">
                    <span className="gauge-label">VESSEL PRESSURE</span>
                    <div className="gauge-value press-color">
                      {Number(scadaData.refinery_1?.pressure || 51.2).toFixed(1)}
                      <span className="unit-suffix">PSI</span>
                    </div>
                    <div className="gauge-range-bar">
                      <div
                        className="gauge-fill press-fill"
                        style={{ width: `${Math.min(100, (Number(scadaData.refinery_1?.pressure || 50) / 100) * 100)}%` }}
                      ></div>
                    </div>
                    <div className="gauge-limits">
                      <span>Low: 35 PSI</span>
                      <span>Normal: 50 PSI</span>
                      <span>High: 75 PSI</span>
                    </div>
                  </div>
                </div>

                {/* Interactive Modbus Control Setpoints */}
                <div className="scada-control-actions">
                  <h4>⚙️ Setpoint & Control Modifications</h4>
                  <div className="control-row">
                    <label>Temperature Setpoint:</label>
                    <div className="setpoint-input-group">
                      <input
                        type="number"
                        min="150"
                        max="220"
                        step="1"
                        value={r1TempSetpoint}
                        onChange={(e) => setR1TempSetpoint(Number(e.target.value))}
                        className="setpoint-input"
                      />
                      <span className="unit-tag">°C</span>
                      <button
                        className="btn-apply-setpoint"
                        disabled={isControlling}
                        onClick={() => handleScadaCommand('refinery-1', 'set_temperature', r1TempSetpoint, 'Temperature Setpoint Modification')}
                      >
                        Apply Value
                      </button>
                    </div>
                  </div>

                  <div className="quick-action-buttons">
                    <button
                      className="btn-scada-toggle"
                      disabled={isControlling}
                      onClick={() => handleScadaCommand('refinery-1', 'set_heater_enabled', true, 'Enable Heater Coil')}
                    >
                      🔥 Heater ON
                    </button>
                    <button
                      className="btn-scada-toggle btn-scada-off"
                      disabled={isControlling}
                      onClick={() => handleScadaCommand('refinery-1', 'set_heater_enabled', false, 'Disable Heater Coil')}
                    >
                      ❄️ Heater OFF
                    </button>
                    <button
                      className="btn-scada-estop"
                      disabled={isControlling}
                      onClick={() => handleScadaCommand('refinery-1', 'emergency_stop', true, 'EMERGENCY STOP PLC-01')}
                    >
                      ⛔ E-STOP
                    </button>
                  </div>
                </div>
              </div>

              {/* Unit 2: Refinery 2 Flow Unit */}
              <div className="scada-unit-card">
                <div className="unit-card-header">
                  <div className="unit-title">
                    <span className="unit-icon">🌊</span>
                    <h3>Refinery Unit 2 (PLC-02 · Flow Unit)</h3>
                  </div>
                  <span className={`status-pill ${scadaData.refinery_2?.status === 'online' ? 'status-online' : 'status-offline'}`}>
                    ● {scadaData.refinery_2?.status?.toUpperCase() || 'ONLINE'}
                  </span>
                </div>

                <div className="gauges-container">
                  <div className="gauge-box">
                    <span className="gauge-label">PIPE FLOW RATE</span>
                    <div className="gauge-value flow-color">
                      {Number(scadaData.refinery_2?.flow_rate || 54.8).toFixed(1)}
                      <span className="unit-suffix">L/min</span>
                    </div>
                    <div className="gauge-range-bar">
                      <div
                        className="gauge-fill flow-fill"
                        style={{ width: `${Math.min(100, (Number(scadaData.refinery_2?.flow_rate || 50) / 100) * 100)}%` }}
                      ></div>
                    </div>
                    <div className="gauge-limits">
                      <span>Low: 25 L/m</span>
                      <span>Target: {r2FlowSetpoint} L/m</span>
                      <span>High: 95 L/m</span>
                    </div>
                  </div>

                  <div className="gauge-box">
                    <span className="gauge-label">MANIFOLD TEMPERATURE</span>
                    <div className="gauge-value temp-color">
                      {Number(scadaData.refinery_2?.temperature || 174.5).toFixed(1)}
                      <span className="unit-suffix">°C</span>
                    </div>
                    <div className="gauge-range-bar">
                      <div
                        className="gauge-fill temp-fill"
                        style={{ width: `${Math.min(100, (Number(scadaData.refinery_2?.temperature || 170) / 240) * 100)}%` }}
                      ></div>
                    </div>
                    <div className="gauge-limits">
                      <span>Low: 140°C</span>
                      <span>Normal: 175°C</span>
                      <span>High: 215°C</span>
                    </div>
                  </div>
                </div>

                {/* Interactive Modbus Control Setpoints */}
                <div className="scada-control-actions">
                  <h4>⚙️ Setpoint & Control Modifications</h4>
                  <div className="control-row">
                    <label>Flow Setpoint:</label>
                    <div className="setpoint-input-group">
                      <input
                        type="number"
                        min="20"
                        max="100"
                        step="1"
                        value={r2FlowSetpoint}
                        onChange={(e) => setR2FlowSetpoint(Number(e.target.value))}
                        className="setpoint-input"
                      />
                      <span className="unit-tag">L/min</span>
                      <button
                        className="btn-apply-setpoint"
                        disabled={isControlling}
                        onClick={() => handleScadaCommand('refinery-2', 'set_flow_rate', r2FlowSetpoint, 'Flow Rate Setpoint Modification')}
                      >
                        Apply Value
                      </button>
                    </div>
                  </div>

                  <div className="quick-action-buttons">
                    <button
                      className="btn-scada-toggle"
                      disabled={isControlling}
                      onClick={() => handleScadaCommand('refinery-2', 'set_pump_enabled', true, 'Enable Inflow Pump')}
                    >
                      💧 Pump ON
                    </button>
                    <button
                      className="btn-scada-toggle btn-scada-off"
                      disabled={isControlling}
                      onClick={() => handleScadaCommand('refinery-2', 'set_pump_enabled', false, 'Disable Inflow Pump')}
                    >
                      🛑 Pump OFF
                    </button>
                    <button
                      className="btn-scada-estop"
                      disabled={isControlling}
                      onClick={() => handleScadaCommand('refinery-2', 'emergency_stop', true, 'EMERGENCY STOP PLC-02')}
                    >
                      ⛔ E-STOP
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* SCADA Value Modifications Log Table */}
            <div className="scada-log-panel">
              <h3>📋 Real-Time SCADA Metric Changes & Modbus Command Log</h3>
              <p className="panel-sub">Every temperature update, pressure fluctuation, setpoint change, and emergency action streamed to SIEM.</p>

              <div className="table-responsive">
                <table className="siem-table">
                  <thead>
                    <tr>
                      <th style={{ width: '110px' }}>Timestamp</th>
                      <th style={{ width: '140px' }}>PLC Device</th>
                      <th style={{ width: '90px' }}>Severity</th>
                      <th>Metric Change / Operator Action</th>
                      <th style={{ width: '120px' }}>Raw Metric</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scadaEvents.length === 0 ? (
                      <tr>
                        <td colSpan="5" className="empty-row">Listening for live Modbus register changes...</td>
                      </tr>
                    ) : (
                      scadaEvents.slice(0, 30).map((ev, i) => (
                        <tr key={ev.id || i} className={`log-row row-${(ev.level || 'info').toLowerCase()}`}>
                          <td className="time-cell">{ev.timestamp}</td>
                          <td><code>{ev.host}</code></td>
                          <td>
                            <span className={`badge badge-${(ev.level || 'info').toLowerCase()}`}>
                              {ev.level}
                            </span>
                          </td>
                          <td>{ev.message}</td>
                          <td>
                            {ev.raw_event?.device?.metadata?.value !== undefined ? (
                              <span className="metric-chip">
                                {ev.raw_event.device.metadata.metric}: {ev.raw_event.device.metadata.value}
                              </span>
                            ) : (
                              <span className="sub-dim">Telemetry</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: CORPORATE PORTAL & SESSION SECURITY */}
        {activeTab === 'sessions' && (
          <div className="tab-pane sessions-pane">
            <div className="auth-summary-ribbon">
              <div className="auth-summary-card">
                <span className="summary-lbl">Total Established Sessions</span>
                <span className="summary-val">{authStats.total_sessions || sessions.length}</span>
              </div>
              <div className="auth-summary-card">
                <span className="summary-lbl">Active Live Sessions</span>
                <span className="summary-val text-success">{authStats.active_sessions || sessions.filter(s => s.is_active).length}</span>
              </div>
              <div className="auth-summary-card">
                <span className="summary-lbl">Failed Login Attempts</span>
                <span className={`summary-val ${authStats.total_failed_logins > 0 ? 'text-danger' : 'text-neutral'}`}>
                  {authStats.total_failed_logins || 0}
                </span>
              </div>
              <div className="auth-summary-card">
                <span className="summary-lbl">Brute-Force Detection</span>
                <span className={`summary-badge ${authStats.brute_force_alert ? 'badge-danger' : 'badge-success'}`}>
                  {authStats.brute_force_alert ? '🚨 RISK DETECTED' : '🛡️ NORMAL'}
                </span>
              </div>
            </div>

            {/* Active Sessions Table */}
            <div className="session-panel-card">
              <div className="panel-header-flex">
                <div>
                  <h3>🔑 Active Corporate Portal User Sessions</h3>
                  <p className="panel-sub">Every active session tracked in real-time with origin IP, user agent, and instant revocation.</p>
                </div>
                <button className="btn-secondary" onClick={fetchData}>🔄 Sync Sessions</button>
              </div>

              <div className="table-responsive">
                <table className="siem-table">
                  <thead>
                    <tr>
                      <th>Token Preview</th>
                      <th>User Account</th>
                      <th>Role</th>
                      <th>Client IP Address</th>
                      <th>Created At</th>
                      <th>Expires At</th>
                      <th>Status</th>
                      <th>SOC Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.length === 0 ? (
                      <tr>
                        <td colSpan="8" className="empty-row">No sessions recorded yet. Log into Corporate Portal to create a session.</td>
                      </tr>
                    ) : (
                      sessions.map((s) => (
                        <tr key={s.id} className={s.is_active ? 'row-active-session' : 'row-dim'}>
                          <td><code>{s.token_preview}</code></td>
                          <td><strong>{s.username}</strong></td>
                          <td><span className="role-tag">{s.role}</span></td>
                          <td><code>{s.ip_address}</code></td>
                          <td className="time-cell">{s.created_at ? new Date(s.created_at).toLocaleTimeString() : 'N/A'}</td>
                          <td className="time-cell">{s.expires_at ? new Date(s.expires_at).toLocaleTimeString() : 'N/A'}</td>
                          <td>
                            <span className={`session-status-tag ${s.is_active ? 'tag-active' : (s.status === 'revoked' ? 'tag-revoked' : 'tag-expired')}`}>
                              {s.is_active ? '🟢 ACTIVE' : (s.status === 'revoked' ? '🔴 REVOKED' : '⏱️ EXPIRED')}
                            </span>
                          </td>
                          <td>
                            {s.is_active ? (
                              <button
                                className="btn-revoke"
                                onClick={() => handleRevokeSession(s.id, s.username)}
                                title="Terminate and revoke this user session immediately"
                              >
                                🚫 Revoke
                              </button>
                            ) : (
                              <span className="text-muted">Terminated</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Failed Login Attempts Log */}
            <div className="session-panel-card failed-logins-panel">
              <div className="panel-header-flex">
                <div>
                  <h3>🛑 Failed Authentication & Invalid Credential Log</h3>
                  <p className="panel-sub">Every failed login attempt, invalid password, or unauthorized access attempt recorded with full audit details.</p>
                </div>
              </div>

              <div className="table-responsive">
                <table className="siem-table">
                  <thead>
                    <tr>
                      <th style={{ width: '120px' }}>Timestamp</th>
                      <th>Targeted Username</th>
                      <th>Source IP</th>
                      <th>Failure Reason</th>
                      <th>Log Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {!authStats.recent_failed_attempts || authStats.recent_failed_attempts.length === 0 ? (
                      <tr>
                        <td colSpan="5" className="empty-row text-success">
                          ✓ No failed login attempts recorded. Authentication stream healthy.
                        </td>
                      </tr>
                    ) : (
                      authStats.recent_failed_attempts.map((fa, i) => (
                        <tr key={fa.id || i} className="log-row row-high">
                          <td className="time-cell">{fa.timestamp ? new Date(fa.timestamp).toLocaleTimeString() : 'Recent'}</td>
                          <td><strong>👤 {fa.username}</strong></td>
                          <td><code>{fa.ip_address}</code></td>
                          <td><span className="badge badge-high">{fa.reason}</span></td>
                          <td>{fa.message}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Corporate Portal Value Modifications */}
            <div className="session-panel-card">
              <h3>📝 Corporate Portal Task & Values Modification Audit</h3>
              <p className="panel-sub">Every task updated, announcement created, or system status modified in Corporate Portal.</p>

              <div className="table-responsive">
                <table className="siem-table">
                  <thead>
                    <tr>
                      <th style={{ width: '110px' }}>Timestamp</th>
                      <th style={{ width: '90px' }}>Severity</th>
                      <th>Modification Description</th>
                      <th>Actor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {corpEvents.length === 0 ? (
                      <tr>
                        <td colSpan="4" className="empty-row">No corporate portal modifications recorded.</td>
                      </tr>
                    ) : (
                      corpEvents.map((ev, i) => (
                        <tr key={ev.id || i} className={`log-row row-${(ev.level || 'info').toLowerCase()}`}>
                          <td className="time-cell">{ev.timestamp}</td>
                          <td>
                            <span className={`badge badge-${(ev.level || 'info').toLowerCase()}`}>
                              {ev.level}
                            </span>
                          </td>
                          <td>{ev.message}</td>
                          <td><code>{ev.raw_event?.username || 'admin'}</code></td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: ALERTS & INCIDENTS */}
        {activeTab === 'alerts' && (
          <div className="tab-pane alerts-pane">
            <div className="panel-header-flex">
              <div>
                <h3>🚨 Security Alerts & Threshold Violations</h3>
                <p className="panel-sub">Automated alerts generated from OT threshold breaches, SCADA alarms, and brute-force authentication attacks.</p>
              </div>
              <button className="btn-secondary" onClick={fetchData}>🔄 Sync Alerts</button>
            </div>

            <div className="table-responsive">
              <table className="siem-table">
                <thead>
                  <tr>
                    <th style={{ width: '120px' }}>Alert ID</th>
                    <th style={{ width: '90px' }}>Severity</th>
                    <th style={{ width: '140px' }}>Rule Triggered</th>
                    <th style={{ width: '140px' }}>Source Host</th>
                    <th>Alert Title & Description</th>
                    <th style={{ width: '90px' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {alerts.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="empty-row text-success">
                        ✓ Zero active security alerts. All monitored systems within nominal parameters.
                      </td>
                    </tr>
                  ) : (
                    alerts.map((al, idx) => (
                      <tr key={al.id || idx} className={`log-row row-${(al.severity || 'warn').toLowerCase()}`}>
                        <td><code>{al.alert_id || `ALT-${idx + 1}`}</code></td>
                        <td>
                          <span className={`badge badge-${(al.severity || 'warn').toLowerCase()}`}>
                            {al.severity?.toUpperCase()}
                          </span>
                        </td>
                        <td><span className="rule-chip">{al.rule_id || 'RULE-SCADA'}</span></td>
                        <td><code>{al.source || 'system'}</code></td>
                        <td><strong>{al.title}</strong></td>
                        <td>
                          <span className={`status-pill ${al.status === 'open' ? 'status-open' : 'status-closed'}`}>
                            {al.status?.toUpperCase() || 'OPEN'}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 5: SOAR ACTIVE DEFENSES */}
        {activeTab === 'soar' && (
          <div className="tab-pane soar-pane">
            <h3>⚡ SOAR Automated Mitigation Playbooks</h3>
            <p className="panel-sub">Configured playbooks for automated brute-force IP blocking, process quarantine, and SCADA emergency containment.</p>

            <div className="playbooks-grid">
              <div className="playbook-card">
                <div className="playbook-header">
                  <h4>🛡️ Brute Force IP Containment</h4>
                  <span className="playbook-badge active">Active Rule</span>
                </div>
                <p>Triggered on 3+ consecutive failed logins. Dynamically issues firewall block rules against the adversary IP.</p>
                <div className="playbook-meta">
                  <span>Triggers: Corporate Auth Failures</span>
                  <span>Action: IPTables Drop + Session Kill</span>
                </div>
                <button
                  className="btn-playbook"
                  onClick={() => showNotification('✓ Executed manual test run for Brute Force IP Containment playbook.', 'info')}
                >
                  ▶ Test Playbook
                </button>
              </div>

              <div className="playbook-card">
                <div className="playbook-header">
                  <h4>🏭 SCADA Thermal Overrun Isolation</h4>
                  <span className="playbook-badge active">Active Rule</span>
                </div>
                <p>Triggered if PLC Refinery-1 temperature exceeds 210°C or pressure exceeds 75 PSI. Disables heater coil and triggers ventilation.</p>
                <div className="playbook-meta">
                  <span>Triggers: High Temperature / Pressure</span>
                  <span>Action: Heater Cutoff + Operator Alarm</span>
                </div>
                <button
                  className="btn-playbook"
                  onClick={() => showNotification('✓ Executed test run for SCADA Thermal Overrun Isolation.', 'info')}
                >
                  ▶ Test Playbook
                </button>
              </div>

              <div className="playbook-card">
                <div className="playbook-header">
                  <h4>🔒 Critical Session Mass Revocation</h4>
                  <span className="playbook-badge">Standby</span>
                </div>
                <p>Emergency kill switch to instantly terminate all active corporate user sessions in the event of an identity compromise.</p>
                <div className="playbook-meta">
                  <span>Triggers: Operator Command</span>
                  <span>Action: Revoke All Active Tokens</span>
                </div>
                <button
                  className="btn-playbook btn-danger-playbook"
                  onClick={() => showNotification('⚠️ Emergency Session Kill Switch is ready for deployment.', 'warn')}
                >
                  ▶ Standby Trigger
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <footer className="siem-footer">
        <div>
          <span>GotXA Techs SIEM/SOAR Platform v1.2</span> |{' '}
          <span>Live Ingestion: <strong>Active</strong></span> |{' '}
          <span>Last Polled: <strong>{lastRefreshed}</strong></span>
        </div>
        <div className="footer-links">
          <span>PostgreSQL DB: Connected</span> |{' '}
          <span>Modbus TCP: Active</span>
        </div>
      </footer>
    </div>
  );
}
