import React, { useState, useEffect } from 'react';
import './SOARDashboard.css';

export default function SOARDashboard() {
  const [activeTab, setActiveTab] = useState('mitigations');
  const [mitigations, setMitigations] = useState([]);
  const [actions, setActions] = useState([]);
  const [playbooks, setPlaybooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadSOARData();
  }, []);

  const loadSOARData = async () => {
    try {
      const [mitRes, actRes, playRes] = await Promise.all([
        fetch('/api/v1/soar/mitigations'),
        fetch('/api/v1/soar/actions'),
        fetch('/api/v1/soar/playbooks')
      ]);

      if (mitRes.ok) {
        setMitigations(await mitRes.json());
      }
      if (actRes.ok) {
        const data = await actRes.json();
        setActions(data.actions || data);
      }
      if (playRes.ok) {
        setPlaybooks(await playRes.json());
      }
      setError('');
    } catch (err) {
      setError(`Failed to load SOAR data: ${err.message}`);
      loadDemoData();
    } finally {
      setLoading(false);
    }
  };

  const loadDemoData = () => {
    setMitigations([
      { id: 1, type: 'IP Block', target: '192.168.1.100', status: 'active', expires_at: new Date(Date.now() + 3600000).toISOString() },
      { id: 2, type: 'Agent Isolate', target: 'corp-portal-01', status: 'active', expires_at: new Date(Date.now() + 7200000).toISOString() }
    ]);
    setActions([
      { id: 1, target: '192.168.1.100', playbook: 'brute_force_ip_block', status: 'success', executed_at: new Date(Date.now() - 1800000).toISOString(), result_detail: 'IP blocked successfully' },
      { id: 2, target: 'corp-portal-01', playbook: 'critical_error_restart', status: 'success', executed_at: new Date(Date.now() - 900000).toISOString(), result_detail: 'Service restarted' }
    ]);
    setPlaybooks([
      { id: 1, name: 'brute_force_ip_block', triggers: ['Multiple failed login attempts'], description: 'Blocks source IP after brute force detection' },
      { id: 2, name: 'critical_error_restart', triggers: ['Critical service error'], description: 'Automatically restarts failed services' },
      { id: 3, name: 'ransomware_containment', triggers: ['Suspicious file encryption'], description: 'Isolates affected systems and blocks C2 traffic' }
    ]);
  };

  const calculateCountdown = (expiresAt) => {
    const now = new Date();
    const expires = new Date(expiresAt);
    const diff = Math.max(0, expires - now);
    const hours = Math.floor(diff / 3600000);
    const mins = Math.floor((diff % 3600000) / 60000);
    return `${hours}h ${mins}m`;
  };

  if (loading) return <div className="soar-loading">Loading SOAR data...</div>;

  return (
    <div className="soar-dashboard">
      <div className="soar-tabs">
        <button 
          className={`soar-tab ${activeTab === 'mitigations' ? 'active' : ''}`}
          onClick={() => setActiveTab('mitigations')}
        >
          🛡️ Active Mitigations
        </button>
        <button 
          className={`soar-tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          📜 Action History
        </button>
        <button 
          className={`soar-tab ${activeTab === 'playbooks' ? 'active' : ''}`}
          onClick={() => setActiveTab('playbooks')}
        >
          📚 Playbooks
        </button>
      </div>

      {error && <div className="soar-error">{error}</div>}

      {activeTab === 'mitigations' && (
        <div className="soar-section">
          <h2>🛡️ Active Mitigations</h2>
          <div className="mitigations-grid">
            {mitigations.length === 0 ? (
              <p className="no-data">No active mitigations</p>
            ) : (
              mitigations.map(mit => (
                <div key={mit.id} className="mitigation-card">
                  <div className="mit-header">
                    <span className="mit-type">{mit.type}</span>
                    <span className="mit-status active">ACTIVE</span>
                  </div>
                  <div className="mit-target">Target: {mit.target}</div>
                  <div className="mit-countdown">
                    ⏱️ Expires in: {calculateCountdown(mit.expires_at)}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {activeTab === 'history' && (
        <div className="soar-section">
          <h2>📜 Action History</h2>
          <div className="actions-table">
            <table>
              <thead>
                <tr>
                  <th>Target</th>
                  <th>Playbook</th>
                  <th>Status</th>
                  <th>Executed At</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {actions.length === 0 ? (
                  <tr><td colSpan="5" className="no-data">No action history</td></tr>
                ) : (
                  actions.map(action => (
                    <tr key={action.id} className={`status-${action.status}`}>
                      <td>{action.target}</td>
                      <td><code>{action.playbook}</code></td>
                      <td><span className={`status-badge ${action.status}`}>{action.status.toUpperCase()}</span></td>
                      <td>{new Date(action.executed_at).toLocaleString()}</td>
                      <td>{action.result_detail}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'playbooks' && (
        <div className="soar-section">
          <h2>📚 Available Playbooks</h2>
          <div className="playbooks-grid">
            {playbooks.length === 0 ? (
              <p className="no-data">No playbooks available</p>
            ) : (
              playbooks.map(pb => (
                <div key={pb.id} className="playbook-card">
                  <h3>{pb.name}</h3>
                  <p className="pb-desc">{pb.description}</p>
                  <div className="pb-triggers">
                    <strong>Triggers:</strong>
                    <ul>
                      {pb.triggers.map((trigger, idx) => (
                        <li key={idx}>{trigger}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
