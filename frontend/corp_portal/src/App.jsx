import React, { useState, useEffect } from 'react';
import CorpLogin from './pages/CorpLogin';
import CorpDashboard from './pages/CorpDashboard';
import './App.css';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const storedUser = sessionStorage.getItem('corp_user');
    if (storedUser) {
      setUser(JSON.parse(storedUser));
      setIsAuthenticated(true);
    }
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
    setIsAuthenticated(true);
    sessionStorage.setItem('corp_user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    setIsAuthenticated(false);
    sessionStorage.removeItem('corp_user');
  };

  return (
    <div className="app">
      {isAuthenticated ? (
        <CorpDashboard user={user} onLogout={handleLogout} />
      ) : (
        <CorpLogin onLogin={handleLogin} />
      )}
    </div>
  );
}
