import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './SCADADashboard.css';

export default function SCADADashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 2000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const response = await fetch('/api/modbus');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setData(await response.json());
      setError('');
    } catch (err) {
      setError(`Error: ${err.message}`);
      setData({
        refinery_1: { temperature: 185.2, pressure: 51.8 },
        refinery_2: { flow_rate: 52.4, temperature: 175.8 }
      });
    }
  };

  if (!data) return <div className="loading">Loading...</div>;

  return (
    <div className="scada-dashboard">
      <header>
        <h1>SCADA Dashboard</h1>
        <Link to="/scada_dashboard/hmi" className="nav-link">Go to HMI →</Link>
      </header>
      
      {error && <div className="error">{error}</div>}

      <div className="dashboard-grid">
        <div className="gauge-card">
          <h3>Temperature (PLC-1)</h3>
          <div className="value">{data.refinery_1?.temperature?.toFixed(1)}°C</div>
          <div className="range">Safe: 170-190°C</div>
        </div>

        <div className="gauge-card">
          <h3>Pressure (PLC-1)</h3>
          <div className="value">{data.refinery_1?.pressure?.toFixed(1)} PSI</div>
          <div className="range">Safe: 45-55 PSI</div>
        </div>

        <div className="gauge-card">
          <h3>Flow Rate (PLC-2)</h3>
          <div className="value">{data.refinery_2?.flow_rate?.toFixed(1)} L/min</div>
          <div className="range">Safe: 40-60 L/min</div>
        </div>

        <div className="gauge-card">
          <h3>Temperature (PLC-2)</h3>
          <div className="value">{data.refinery_2?.temperature?.toFixed(1)}°C</div>
          <div className="range">Safe: 170-190°C</div>
        </div>
      </div>
    </div>
  );
}
