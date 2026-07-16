/**
 * SIEM/SOAR Dashboard - Frontend Logic
 * Handles data fetching, chart rendering, and real-time updates
 */

const API_BASE = '/api/v1';
const REFRESH_INTERVAL = 5000; // 5 seconds
let charts = {};

document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    setInterval(loadDashboard, REFRESH_INTERVAL);
});

async function loadDashboard() {
    try {
        const [statsData, recentData] = await Promise.all([
            fetchJSON(`${API_BASE}/dashboard/stats`),
            fetchJSON(`${API_BASE}/dashboard/recent`)
        ]);

        if (statsData && statsData.status === 'success') {
            updateMetrics(statsData.data);
            updateCharts(statsData.data);
        }

        if (recentData && recentData.status === 'success') {
            updateTables(recentData.data);
        }

        setSystemStatus(true);
        clearErrorBanner();
    } catch (error) {
        console.error('Dashboard load error:', error);
        setSystemStatus(false);
        showErrorBanner(`Failed to load dashboard: ${error.message}`);
    }
}

async function fetchJSON(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
}

function updateMetrics(data) {
    document.getElementById('metric-logs').textContent = formatNumber(data.total_logs || 0);
    document.getElementById('metric-alerts').textContent = formatNumber(data.total_alerts || 0);
    document.getElementById('metric-high').textContent = formatNumber(data.alerts_by_severity?.HIGH || 0);
    document.getElementById('metric-medium').textContent = formatNumber(data.alerts_by_severity?.MEDIUM || 0);
    document.getElementById('metric-open').textContent = formatNumber(data.alerts_by_status?.Open || 0);
    document.getElementById('metric-resolved').textContent = formatNumber(data.alerts_by_status?.Resolved || 0);
}

function updateCharts(data) {
    // Logs by Level
    const logLevelCtx = document.getElementById('chart-logs-level');
    if (logLevelCtx) {
        const logLevels = Object.keys(data.logs_by_level || {});
        const logCounts = Object.values(data.logs_by_level || {});
        
        if (charts.logLevel) charts.logLevel.destroy();
        charts.logLevel = new Chart(logLevelCtx, {
            type: 'doughnut',
            data: {
                labels: logLevels,
                datasets: [{
                    data: logCounts,
                    backgroundColor: [
                        'rgba(0, 212, 255, 0.7)',
                        'rgba(46, 213, 115, 0.7)',
                        'rgba(255, 165, 2, 0.7)',
                        'rgba(255, 71, 87, 0.7)'
                    ],
                    borderColor: [
                        'rgba(0, 212, 255, 1)',
                        'rgba(46, 213, 115, 1)',
                        'rgba(255, 165, 2, 1)',
                        'rgba(255, 71, 87, 1)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        labels: {
                            color: '#e0e0e0',
                            font: { size: 12 }
                        }
                    }
                }
            }
        });
    }

    // Alerts by Severity
    const alertSevCtx = document.getElementById('chart-alerts-severity');
    if (alertSevCtx) {
        const severities = Object.keys(data.alerts_by_severity || {});
        const severityCounts = Object.values(data.alerts_by_severity || {});
        
        if (charts.alertSeverity) charts.alertSeverity.destroy();
        charts.alertSeverity = new Chart(alertSevCtx, {
            type: 'pie',
            data: {
                labels: severities,
                datasets: [{
                    data: severityCounts,
                    backgroundColor: [
                        'rgba(255, 71, 87, 0.7)',
                        'rgba(255, 165, 2, 0.7)',
                        'rgba(46, 213, 115, 0.7)'
                    ],
                    borderColor: [
                        'rgba(255, 71, 87, 1)',
                        'rgba(255, 165, 2, 1)',
                        'rgba(46, 213, 115, 1)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        labels: {
                            color: '#e0e0e0',
                            font: { size: 12 }
                        }
                    }
                }
            }
        });
    }

    // Alert Status Distribution
    const alertStatusCtx = document.getElementById('chart-alerts-status');
    if (alertStatusCtx) {
        const statuses = Object.keys(data.alerts_by_status || {});
        const statusCounts = Object.values(data.alerts_by_status || {});
        
        if (charts.alertStatus) charts.alertStatus.destroy();
        charts.alertStatus = new Chart(alertStatusCtx, {
            type: 'bar',
            data: {
                labels: statuses,
                datasets: [{
                    label: 'Count',
                    data: statusCounts,
                    backgroundColor: [
                        'rgba(255, 71, 87, 0.7)',
                        'rgba(255, 165, 2, 0.7)',
                        'rgba(46, 213, 115, 0.7)'
                    ],
                    borderColor: [
                        'rgba(255, 71, 87, 1)',
                        'rgba(255, 165, 2, 1)',
                        'rgba(46, 213, 115, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                indexAxis: 'y',
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        ticks: { color: '#a8a8a8' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    y: {
                        ticks: { color: '#a8a8a8' }
                    }
                }
            }
        });
    }

    // Logs by Host
    const logHostCtx = document.getElementById('chart-logs-host');
    if (logHostCtx) {
        const hosts = Object.keys(data.logs_by_host || {});
        const hostCounts = Object.values(data.logs_by_host || {});
        
        if (charts.logHost) charts.logHost.destroy();
        charts.logHost = new Chart(logHostCtx, {
            type: 'bar',
            data: {
                labels: hosts,
                datasets: [{
                    label: 'Log Count',
                    data: hostCounts,
                    backgroundColor: 'rgba(0, 212, 255, 0.7)',
                    borderColor: 'rgba(0, 212, 255, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { labels: { color: '#e0e0e0' } }
                },
                scales: {
                    x: {
                        ticks: { color: '#a8a8a8' },
                        grid: { display: false }
                    },
                    y: {
                        ticks: { color: '#a8a8a8' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    }
                }
            }
        });
    }
}

function updateTables(data) {
    // Recent Logs
    const logsContainer = document.getElementById('table-logs');
    if (data.recent_logs && data.recent_logs.length > 0) {
        logsContainer.innerHTML = data.recent_logs.map(log => `
            <div class="table-row">
                <div class="row-header">
                    <span class="row-timestamp">${formatTime(log.timestamp)}</span>
                    <span class="row-level level-${log.level}">${log.level}</span>
                    <span class="row-host">${truncate(log.host, 20)}</span>
                </div>
                <div class="row-message">${escapeHtml(log.message)}</div>
            </div>
        `).join('');
    } else {
        logsContainer.innerHTML = '<div class="no-data">No recent logs</div>';
    }

    // Recent Alerts
    const alertsContainer = document.getElementById('table-alerts');
    if (data.recent_alerts && data.recent_alerts.length > 0) {
        alertsContainer.innerHTML = data.recent_alerts.map(alert => `
            <div class="table-row alert-row">
                <div class="row-header">
                    <span class="row-timestamp">${formatTime(alert.timestamp)}</span>
                    <span class="row-severity severity-${alert.severity}">${alert.severity}</span>
                    <span class="row-status status-${alert.status}">${alert.status}</span>
                </div>
                <div class="row-host">${truncate(alert.host, 20)}</div>
                <div class="row-rule"><strong>${escapeHtml(alert.rule)}</strong></div>
                <div class="row-message">${escapeHtml(alert.log_message)}</div>
            </div>
        `).join('');
    } else {
        alertsContainer.innerHTML = '<div class="no-data">No recent alerts</div>';
    }
}

function setSystemStatus(healthy) {
    const badge = document.querySelector('.status-badge');
    const text = document.getElementById('status-text');
    if (healthy) {
        badge.classList.add('healthy');
        text.textContent = 'System Healthy';
    } else {
        badge.classList.remove('healthy');
        text.textContent = 'Connection Error';
    }
}

function showErrorBanner(message) {
    const banner = document.getElementById('error-banner');
    banner.innerHTML = `
        <div class="error-alert">
            <span>${escapeHtml(message)}</span>
            <button onclick="this.parentElement.style.display='none';">✕</button>
        </div>
    `;
}

function clearErrorBanner() {
    document.getElementById('error-banner').innerHTML = '';
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit'
    });
}

function truncate(str, len) {
    return str && str.length > len ? str.substring(0, len - 3) + '...' : str;
}

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}
