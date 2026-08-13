import React, { useState, useEffect } from 'react';
import './SCADAHmi.css';

export default function SCADAHmi() {
  const [plc1Temp, setPlc1Temp] = useState(0);
  const [plc1Pressure, setPlc1Pressure] = useState(0);
  const [plc2Flow, setPlc2Flow] = useState(0);
  const [plc2Temp, setPlc2Temp] = useState(0);
  const [timestamp, setTimestamp] = useState(new Date().toLocaleTimeString());
  const [error, setError] = useState('');
  const [alarms, setAlarms] = useState([]);
  const [plc1Online, setPlc1Online] = useState(true);
  const [plc2Online, setPlc2Online] = useState(true);

  const THRESHOLDS = {
    temperature: { normal: [170, 190], warning: [160, 200] },
    pressure: { normal: [45, 55], warning: [40, 60] },
    flow_rate: { normal: [40, 60], warning: [30, 70] }
  };

  const getStatus = (value, type) => {
    const thresholds = THRESHOLDS[type];
    if (value >= thresholds.normal[0] && value <= thresholds.normal[1]) return 'NORMAL';
    if (value >= thresholds.warning[0] && value <= thresholds.warning[1]) return 'WARNING';
    return 'CRITICAL';
  };

  useEffect(() => {
    loadSCADAData();
    const interval = setInterval(loadSCADAData, 2000);
    return () => clearInterval(interval);
  }, []);

  const loadSCADAData = async () => {
    try {
      const response = await fetch('/api/modbus');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      const now = new Date().toLocaleTimeString();

      setPlc1Temp(data.refinery_1?.temperature || 0);
      setPlc1Pressure(data.refinery_1?.pressure || 0);
      setPlc2Flow(data.refinery_2?.flow_rate || 0);
      setPlc2Temp(data.refinery_2?.temperature || 0);
      setTimestamp(now);
      setPlc1Online(true);
      setPlc2Online(true);
      setError('');

      // Check for alarms
      const newAlarms = [];
      if (getStatus(data.refinery_1?.temperature, 'temperature') === 'CRITICAL') {
        newAlarms.push({ msg: 'PLC-1 Temperature CRITICAL', time: now });
      }
      if (getStatus(data.refinery_1?.pressure, 'pressure') === 'CRITICAL') {
        newAlarms.push({ msg: 'PLC-1 Pressure CRITICAL', time: now });
      }
      if (getStatus(data.refinery_2?.flow_rate, 'flow_rate') === 'CRITICAL') {
        newAlarms.push({ msg: 'PLC-2 Flow Rate CRITICAL', time: now });
      }
      setAlarms(newAlarms);
    } catch (err) {
      setError(`SCADA Gateway Error: ${err.message}`);
      setPlc1Online(false);
      setPlc2Online(false);
      loadDemoData();
    }
  };

  const loadDemoData = () => {
    const now = new Date().toLocaleTimeString();
    setPlc1Temp(185.2);
    setPlc1Pressure(51.8);
    setPlc2Flow(52.4);
    setPlc2Temp(175.8);
    setTimestamp(now);
  };

  const formatValue = (value) => value.toFixed(1);

  return (
    <div className="scada-container">
      <header className="scada-header">
        <h1>⚙️ SCADA HMI - Real-Time Control System</h1>
        <p className="header-info">
          <span className="status-indicator"></span>
          Industrial Process Automation | Live Modbus Monitoring
        </p>
      </header>

      {error && <div className="error">⚠️ {error}</div>}

      <div className="hmi-grid">
        {/* PLC-1 */}
        <div className="plc-unit">
          <div className="plc-header">🏭 Refinery Unit 1 (PLC-01)</div>

          <div className="registers-grid">
            <div className="register">
              <div className="register-label">Crude Oil Heater</div>
              <div className="register-value">{formatValue(plc1Temp)}°C</div>
              <div className="register-unit">Register: 40001</div>
              <div className="register-address">
                Status: {getStatus(plc1Temp, 'temperature')}
              </div>
            </div>

            <div className="register">
              <div className="register-label">Pressure Valve</div>
              <div className="register-value">{formatValue(plc1Pressure)} PSI</div>
              <div className="register-unit">Register: 40002</div>
              <div className="register-address">
                Status: {getStatus(plc1Pressure, 'pressure')}
              </div>
            </div>
          </div>

          <div className="status-bar">
            <div className="status-item">
              <div className="status-label">PLC Status</div>
              <div className={`status-value ${!plc1Online ? 'offline' : ''}`}>
                {plc1Online ? 'ONLINE ✓' : 'OFFLINE'}
              </div>
            </div>
            <div className="status-item">
              <div className="status-label">Last Update</div>
              <div className="status-value">{timestamp}</div>
            </div>
            <div className="status-item">
              <div className="status-label">Cycle Time</div>
              <div className="status-value">100ms</div>
            </div>
          </div>
        </div>

        {/* PLC-2 */}
        <div className="plc-unit">
          <div className="plc-header">🏭 Refinery Unit 2 (PLC-02)</div>

          <div className="registers-grid">
            <div className="register">
              <div className="register-label">Chemical Mixer Flow</div>
              <div className="register-value">{formatValue(plc2Flow)} L/min</div>
              <div className="register-unit">Register: 40003</div>
              <div className="register-address">
                Status: {getStatus(plc2Flow, 'flow_rate')}
              </div>
            </div>

            <div className="register">
              <div className="register-label">Reactor Temperature</div>
              <div className="register-value">{formatValue(plc2Temp)}°C</div>
              <div className="register-unit">Register: 40004</div>
              <div className="register-address">
                Status: {getStatus(plc2Temp, 'temperature')}
              </div>
            </div>
          </div>

          <div className="status-bar">
            <div className="status-item">
              <div className="status-label">PLC Status</div>
              <div className={`status-value ${!plc2Online ? 'offline' : ''}`}>
                {plc2Online ? 'ONLINE ✓' : 'OFFLINE'}
              </div>
            </div>
            <div className="status-item">
              <div className="status-label">Last Update</div>
              <div className="status-value">{timestamp}</div>
            </div>
            <div className="status-item">
              <div className="status-label">Cycle Time</div>
              <div className="status-value">100ms</div>
            </div>
          </div>
        </div>
      </div>

      {alarms.length > 0 && (
        <div className="alarm-section">
          <div className="alarm-title">🚨 Active Alarms</div>
          <div className="alarm-list">
            {alarms.map((alarm, idx) => (
              <div key={idx} className="alarm-item critical">
                {alarm.msg}
                <span className="alarm-timestamp">{alarm.time}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="info-panel">
        📊 <strong>Real-Time Data:</strong> Updates every 2 seconds from Modbus registers via SCADA gateway.
        All values in engineering units (°C, PSI, L/min). Safe ranges: Temperature 170-190°C,
        Pressure 45-55 PSI, Flow 40-60 L/min.
      </div>
    </div>
  );
}
