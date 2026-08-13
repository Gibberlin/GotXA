import React from 'react';
import { Link } from 'react-router-dom';
import './NotFound.css';

export default function NotFound() {
  return (
    <div className="not-found">
      <div className="error-card">
        <h1>404</h1>
        <h2>Page Not Found</h2>
        <p>The page you're looking for doesn't exist.</p>
        <div className="nav-buttons">
          <Link to="/" className="btn btn-primary">Go to SIEM Dashboard</Link>
          <Link to="/corp_portal" className="btn btn-secondary">Go to Corporate Portal</Link>
          <Link to="/scada_dashboard/hmi" className="btn btn-secondary">Go to SCADA HMI</Link>
        </div>
      </div>
    </div>
  );
}
