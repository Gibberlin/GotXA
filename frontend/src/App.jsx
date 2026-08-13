import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import CorpLogin from './pages/CorpLogin';
import CorpDashboard from './pages/CorpDashboard';
import SCADADashboard from './pages/SCADADashboard';
import SCADAHmi from './pages/SCADAHmi';
import SiemDashboard from './pages/SiemDashboard';
import NotFound from './pages/NotFound';

function App() {
  return (
    <Router>
      <Routes>
        {/* Corporate Portal */}
        <Route path="/corp_portal" element={<CorpLogin />} />
        <Route path="/corp_portal/dashboard" element={<CorpDashboard />} />

        {/* SCADA Dashboards */}
        <Route path="/scada_dashboard" element={<SCADADashboard />} />
        <Route path="/scada_dashboard/hmi" element={<SCADAHmi />} />

        {/* SIEM Dashboard */}
        <Route path="/siem_dashboard" element={<SiemDashboard />} />

        {/* Redirect root to SIEM dashboard */}
        <Route path="/" element={<Navigate to="/siem_dashboard" replace />} />

        {/* 404 */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}

export default App;
