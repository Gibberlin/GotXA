import React from 'react';
import './SiemDashboard.css';

export default function SiemDashboard() {
  return (
    <div className="siem-container">
      <header>
        <h1>🛡️ SIEM Dashboard</h1>
        <p>Security Information & Event Management</p>
      </header>

      <div className="dashboard-content">
        <div className="card">
          <h2>📊 Dashboard Loading...</h2>
          <p>React SIEM dashboard is ready. Backend API integration pending.</p>
          <p className="info">
            This will display real-time security events, alerts, and SOAR automation actions.
          </p>
        </div>

        <div className="card">
          <h2>🎯 Features Coming Soon</h2>
          <ul>
            <li>Real-time log streaming</li>
            <li>Security alert management</li>
            <li>SOAR automated responses</li>
            <li>Threat intelligence dashboard</li>
            <li>Compliance reporting</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
