import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './CorpDashboard.css';

export default function CorpDashboard() {
  const [user, setUser] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [activities, setActivities] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [taskPriority, setTaskPriority] = useState('medium');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const getHeaders = () => {
    const token = sessionStorage.getItem('corp_token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  };

  useEffect(() => {
    const storedUser = sessionStorage.getItem('corp_user');
    if (!storedUser) {
      navigate('/corp_portal');
      return;
    }
    setUser(JSON.parse(storedUser));
    loadDashboard();
    loadTasks();
  }, [navigate]);

  const loadDashboard = async () => {
    try {
      const metricsRes = await fetch('/api/dashboard-metrics');
      const activitiesRes = await fetch('/api/recent-activity');

      if (metricsRes.ok) {
        setMetrics(await metricsRes.json());
      }
      if (activitiesRes.ok) {
        const data = await activitiesRes.json();
        setActivities(data.activities || []);
      }
      setError('');
    } catch (err) {
      setError(`Failed to load dashboard: ${err.message}`);
      loadDemoData();
    }
  };

  const loadTasks = async () => {
    try {
      const res = await fetch('/api/corporate/tasks', { headers: getHeaders() });
      if (res.ok) {
        const data = await res.json();
        setTasks(data.items || []);
      }
    } catch (e) {
      console.warn('Could not fetch tasks:', e);
    }
  };

  const handleUpdateTask = async (taskId, newStatus) => {
    try {
      const res = await fetch(`/api/corporate/tasks/${taskId}`, {
        method: 'PATCH',
        headers: getHeaders(),
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        setNotice(`✓ Task status updated to ${newStatus} (Logged to SIEM)`);
        setTimeout(() => setNotice(''), 3000);
        loadTasks();
        loadDashboard();
      }
    } catch (e) {
      setError(`Failed to update task: ${e.message}`);
    }
  };

  const handleCreateTask = async (e) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;
    try {
      const res = await fetch('/api/corporate/tasks', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ title: newTaskTitle, priority: taskPriority })
      });
      if (res.ok) {
        setNotice(`✓ Created task "${newTaskTitle}" (Logged to SIEM)`);
        setNewTaskTitle('');
        setTimeout(() => setNotice(''), 3000);
        loadTasks();
        loadDashboard();
      }
    } catch (e) {
      setError(`Failed to create task: ${e.message}`);
    }
  };

  const loadDemoData = () => {
    setMetrics({
      active_systems: 5,
      total_transactions: 1234,
      open_issues: 3,
      security_score: 92,
      response_time: 45,
      data_volume: 2.3
    });
    setActivities([
      { timestamp: '14:32:15', description: 'System health check passed', status: 'success' },
      { timestamp: '14:28:42', description: 'Database backup completed', status: 'success' },
      { timestamp: '14:15:09', description: 'Configuration update applied', status: 'success' }
    ]);
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/corporate/auth/logout', {
        method: 'POST',
        headers: getHeaders()
      });
    } catch (e) {
      // ignore
    }
    sessionStorage.removeItem('corp_user');
    sessionStorage.removeItem('corp_token');
    navigate('/corp_portal');
  };

  if (!user) return <div className="loading">Loading...</div>;

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>📊 Corporate Portal Operations</h1>
          <p>Centralized Business Operations & Security Audited Environment</p>
        </div>
        <div className="user-section">
          <div className="user-name">👤 {user.username} ({user.role || 'Admin'})</div>
          <button onClick={handleLogout}>Logout</button>
        </div>
      </header>

      {notice && <div className="notice-banner">{notice}</div>}
      {error && <div className="error">{error}</div>}

      {metrics && (
        <>
          <div className="metrics-grid">
            <div className="metric-card">
              <h3>🖥️ Active Systems</h3>
              <div className="metric-value">{metrics.active_systems}</div>
              <div className="metric-label">Infrastructure nodes online</div>
              <div className="metric-badge success">Status: Monitoring</div>
            </div>

            <div className="metric-card">
              <h3>📝 Total Transactions</h3>
              <div className="metric-value">{metrics.total_transactions}</div>
              <div className="metric-label">Processed this session</div>
              <div className="metric-badge success">Active Processing</div>
            </div>

            <div className="metric-card">
              <h3>⚠️ Open Issues</h3>
              <div className="metric-value">{metrics.open_issues}</div>
              <div className="metric-label">Alerts requiring attention</div>
              <div className="metric-badge warning">Review Required</div>
            </div>

            <div className="metric-card">
              <h3>🔐 Security Score</h3>
              <div className="metric-value">{metrics.security_score}%</div>
              <div className="metric-label">Overall security posture</div>
              <div className="metric-badge success">Secure</div>
            </div>

            <div className="metric-card">
              <h3>⏱️ Avg Response Time</h3>
              <div className="metric-value">{metrics.response_time}ms</div>
              <div className="metric-label">API response latency</div>
              <div className="metric-badge success">Optimal</div>
            </div>

            <div className="metric-card">
              <h3>💾 Data Volume</h3>
              <div className="metric-value">{metrics.data_volume} Events</div>
              <div className="metric-label">Logs processed by SIEM</div>
              <div className="metric-badge success">Healthy</div>
            </div>
          </div>

          {/* Interactive Corporate Task Management & Value Modifications */}
          <div className="task-section-card">
            <h2>📝 Corporate Operational Tasks & Modifications</h2>
            <p className="sub-text">Modifications made here are audited and transmitted in real-time to the SIEM SOC Console.</p>

            <form onSubmit={handleCreateTask} className="task-create-form">
              <input
                type="text"
                placeholder="Add new corporate compliance / operational task..."
                value={newTaskTitle}
                onChange={(e) => setNewTaskTitle(e.target.value)}
                className="task-input"
              />
              <select
                value={taskPriority}
                onChange={(e) => setTaskPriority(e.target.value)}
                className="priority-select"
              >
                <option value="low">Low Priority</option>
                <option value="medium">Medium Priority</option>
                <option value="high">High Priority</option>
              </select>
              <button type="submit" className="btn-add-task">+ Create Task</button>
            </form>

            <div className="tasks-list">
              {tasks.length === 0 ? (
                <p className="no-tasks">No active tasks.</p>
              ) : (
                tasks.map((task) => (
                  <div key={task.id} className={`task-row status-${task.status}`}>
                    <div className="task-info">
                      <span className="task-title">{task.title}</span>
                      <span className={`priority-badge prio-${task.priority || 'medium'}`}>
                        {task.priority || 'medium'}
                      </span>
                    </div>
                    <div className="task-actions">
                      <button
                        className={`status-btn ${task.status === 'open' ? 'current' : ''}`}
                        onClick={() => handleUpdateTask(task.id, 'open')}
                      >
                        Open
                      </button>
                      <button
                        className={`status-btn ${task.status === 'in_progress' ? 'current' : ''}`}
                        onClick={() => handleUpdateTask(task.id, 'in_progress')}
                      >
                        In Progress
                      </button>
                      <button
                        className={`status-btn ${task.status === 'completed' ? 'current' : ''}`}
                        onClick={() => handleUpdateTask(task.id, 'completed')}
                      >
                        Completed
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="activity-section">
            <h2>📋 Real-Time Activity Log</h2>
            <div className="activity-list">
              {activities.length === 0 ? (
                <p className="no-activity">No recent activity.</p>
              ) : (
                activities.map((activity, idx) => (
                  <div key={idx} className="activity-item">
                    <span className="activity-time">{activity.timestamp}</span>
                    <span className="activity-desc">{activity.description}</span>
                    <span className={`activity-status ${activity.status}`}>
                      {activity.status}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
