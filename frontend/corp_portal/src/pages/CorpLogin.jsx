import React, { useState } from 'react';
import './CorpLogin.css';

export default function CorpLogin({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('password', password);

      const response = await fetch('/api/login', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        setMessageType('success');
        setMessage(`✓ Welcome ${data.user.username}!`);
        onLogin(data.user);
      } else {
        setMessageType('error');
        setMessage(`✗ ${data.message || 'Authentication failed'}`);
      }
    } catch (error) {
      setMessageType('error');
      setMessage(`✗ Error: ${error.message}`);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>🔐 Corporate Portal</h1>
        <p className="subtitle">Secure Authentication System</p>

        {message && <div className={`message ${messageType}`}>{message}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g., admin"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
            />
          </div>

          <button type="submit">Login</button>
        </form>

        <div className="demo-creds">
          <p><strong>Demo Credentials:</strong></p>
          <p>👤 Username: <code>admin</code></p>
          <p>🔑 Password: <code>SecureP@ssw0rd</code></p>
        </div>

        <div className="warning">
          ⚠️ <strong>TESTING ENVIRONMENT:</strong> Authorized testing only.
        </div>
      </div>
    </div>
  );
}
