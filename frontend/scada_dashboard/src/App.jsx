import React, { useState, useEffect } from 'react';
import SCADAHmi from './pages/SCADAHmi';
import './App.css';

export default function App() {
  const [view, setView] = useState('hmi');

  return (
    <div className="app">
      <SCADAHmi />
    </div>
  );
}
