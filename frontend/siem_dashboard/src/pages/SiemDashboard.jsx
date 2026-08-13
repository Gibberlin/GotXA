import React, { useState, useEffect } from 'react';
import SOARDashboard from './SOARDashboard';
import RawLogs from './RawLogs';
import './SiemDashboard.css';

export default function SiemDashboard() {
  const [activeTab, setActiveTab] = useState('overview');
  const [metrics, setMetrics] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      const dashRes = await fetch('/api/dashboard-data');
      const alertsRes = await fetch('/api/alerts');

      if (dashRes.ok) {
        setMetrics(await dashRes.json());
      }
      if (alertsRes.ok) {
        const data = await alertsRes.json();
        setAlerts(data.alerts || []);
      }
      setError('');
    } catch (err) {
      setError(`Failed to load dashboard: ${err.message}`);
      loadDemoData();
    }
  };

  const loadDemoData = () => {
    setMetrics({
      total_logs: 3021,
      total_alerts: 12,
      critical_alerts: 2,
      active_hosts: 8
    });
    setAlerts([
      { id: 1, severity: 'critical', message: 'Brute-force detected', host: 'web-01', timestamp: new Date().toISOString() },
      { id: 2, severity: 'high', message: 'Unusual Modbus activity', host: 'ot-gateway', timestamp: new Date().toISOString() }
    ]);
  };

  return (
    <div className="siem-container">
      <header className="siem-header">
        <h1>🛡️ SIEM Security Dashboard</h1>
        <p>Real-Time Security Monitoring & Automated Response</p>
      </header>

      <div className="tab-navigation">
        <button 
          className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          📊 Overview
        </button>
        <button 
          className={`tab-btn ${activeTab === 'soar' ? 'active' : ''}`}
          onClick={() => setActiveTab('soar')}
        >
          🤖 SOAR Response
        </button>
        <button 
          className={`tab-btn ${activeTab === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveTab('logs')}
        >
          📝 Raw Logs
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {activeTab === 'overview' && metrics && (
        <div className="overview-section">
          <div className="metrics-grid">
            <div className="metric-card">
              <h3>📊 Total Logs</h3>
              <div className="metric-value">{metrics.total_logs}</div>
              <div className="metric-desc">Events processed</div>
            </div>
            <div className="metric-card">
              <h3>⚠️ Total Alerts</h3>
              <div className="metric-value">{metrics.total_alerts}</div>
              <div className="metric-desc">Triggered this period</div>
            </div>
            <div className="metric-card alert-critical">
              <h3>🚨 Critical</h3>
              <div className="metric-value">{metrics.critical_alerts}</div>
              <div className="metric-desc">Require attention</div>
            </div>
            <div className="metric-card">
              <h3>🖥️ Active Hosts</h3>
              <div className="metric-value">{metrics.active_hosts}</div>
              <div className="metric-desc">Infrastructure nodes</div>
            </div>
          </div>

          <div className="alerts-section">
            <h2>📋 Recent Alerts</h2>
            <div className="alerts-list">
              {alerts.length === 0 ? (
                <p className="no-data">No alerts</p>
              ) : (
                alerts.slice(0, 5).map(alert => (
                  <div key={alert.id} className={`alert-item severity-${alert.severity}`}>
                    <div className="alert-content">
                      <span className="severity-badge">{alert.severity.toUpperCase()}</span>
                      <span className="message">{alert.message}</span>
                      <span className="host">{alert.host}</span>
                    </div>
                    <span className="timestamp">{new Date(alert.timestamp).toLocaleTimeString()}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'soar' && <SOARDashboard />}

      {activeTab === 'logs' && <RawLogs />}
    </div>
  );
}
