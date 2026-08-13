import React, { useState, useEffect, useRef } from 'react';
import './RawLogs.css';

export default function RawLogs() {
  const [logs, setLogs] = useState([]);
  const [isPaused, setPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [error, setError] = useState('');
  const logsEndRef = useRef(null);

  useEffect(() => {
    const interval = setInterval(fetchLogs, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const fetchLogs = async () => {
    if (isPaused) return;
    try {
      const response = await fetch('/api/raw-logs');
      if (response.ok) {
        const data = await response.json();
        setLogs(prev => [...prev.slice(-99), ...(Array.isArray(data) ? data : [data])]);
        setError('');
      }
    } catch (err) {
      setError(`Connection error: ${err.message}`);
    }
  };

  const clearLogs = () => {
    setLogs([]);
  };

  return (
    <div className="raw-logs-container">
      <div className="logs-toolbar">
        <div className="toolbar-info">
          <span className="status-dot"></span>
          <span className="log-count">Logs: {logs.length}</span>
        </div>
        <div className="toolbar-buttons">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            Auto-scroll
          </label>
          <button 
            className={`btn ${isPaused ? 'resume' : 'pause'}`}
            onClick={() => setPaused(!isPaused)}
          >
            {isPaused ? '▶ Resume' : '⏸ Pause'}
          </button>
          <button className="btn clear" onClick={clearLogs}>
            🗑️ Clear
          </button>
        </div>
      </div>

      {error && <div className="logs-error">{error}</div>}

      <div className="logs-console">
        {logs.length === 0 ? (
          <div className="logs-placeholder">
            [SYSTEM READY] Waiting for incoming telemetry…
          </div>
        ) : (
          logs.map((log, idx) => (
            <div key={idx} className={`log-entry ${log.level ? log.level.toLowerCase() : 'info'}`}>
              <span className="log-timestamp">{new Date().toLocaleTimeString()}</span>
              <span className="log-level">[{(log.level || 'INFO').toUpperCase()}]</span>
              <span className="log-host">{log.host || 'SYSTEM'}</span>
              <span className="log-message">{typeof log === 'string' ? log : log.message || JSON.stringify(log)}</span>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}
