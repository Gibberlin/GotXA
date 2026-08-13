import React, { useState, useEffect } from 'react';
import './CorpDashboard.css';

export default function CorpDashboard({ user, onLogout }) {
  const [metrics, setMetrics] = useState(null);
  const [activities, setActivities] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    loadDashboard();
    const interval = setInterval(loadDashboard, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboard = async () => {
    try {
      const metricsRes = await fetch('/api/dashboard-metrics');
      const activitiesRes = await fetch('/api/recent-activity');

      if (metricsRes.ok) {
        setMetrics(await metricsRes.json());
      }
      if (activitiesRes.ok) {
        const data = await activitiesRes.json();
        setActivities(data.activities || []);
      }
      setError('');
    } catch (err) {
      setError(`Failed to load dashboard: ${err.message}`);
      loadDemoData();
    }
  };

  const loadDemoData = () => {
    setMetrics({
      active_systems: 5,
      total_transactions: 1234,
      open_issues: 3,
      security_score: 92,
      response_time: 45,
      data_volume: 2.3
    });
    setActivities([
      { timestamp: '14:32:15', description: 'System health check passed', status: 'success' },
      { timestamp: '14:28:42', description: 'Database backup completed', status: 'success' },
      { timestamp: '14:15:09', description: 'Configuration update applied', status: 'success' }
    ]);
  };

  if (!metrics) return <div className="loading">Loading...</div>;

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>📊 Corporate Dashboard</h1>
          <p>Business Intelligence & Operations</p>
        </div>
        <div className="user-section">
          <div className="user-name">{user.username}</div>
          <button onClick={onLogout}>Logout</button>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <div className="metrics-grid">
        <div className="metric-card">
          <h3>🖥️ Active Systems</h3>
          <div className="metric-value">{metrics.active_systems}</div>
          <div className="metric-label">Infrastructure nodes</div>
        </div>

        <div className="metric-card">
          <h3>📝 Total Transactions</h3>
          <div className="metric-value">{metrics.total_transactions}</div>
          <div className="metric-label">This session</div>
        </div>

        <div className="metric-card">
          <h3>⚠️ Open Issues</h3>
          <div className="metric-value">{metrics.open_issues}</div>
          <div className="metric-label">Alerts</div>
        </div>

        <div className="metric-card">
          <h3>🔐 Security Score</h3>
          <div className="metric-value">{metrics.security_score}%</div>
          <div className="metric-label">Posture</div>
        </div>

        <div className="metric-card">
          <h3>⏱️ Response Time</h3>
          <div className="metric-value">{metrics.response_time}ms</div>
          <div className="metric-label">API latency</div>
        </div>

        <div className="metric-card">
          <h3>💾 Data Volume</h3>
          <div className="metric-value">{metrics.data_volume}GB</div>
          <div className="metric-label">Logs processed</div>
        </div>
      </div>

      <div className="activity-section">
        <h2>📋 Recent Activity</h2>
        <div className="activity-list">
          {activities.length === 0 ? (
            <p className="no-activity">No recent activity.</p>
          ) : (
            activities.map((activity, idx) => (
              <div key={idx} className="activity-item">
                <span className="activity-time">{activity.timestamp}</span>
                <span className="activity-desc">{activity.description}</span>
                <span className={`activity-status ${activity.status}`}>
                  {activity.status}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
