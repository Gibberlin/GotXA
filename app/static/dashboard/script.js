/**
 * SIEM/SOAR Operations Center — Dashboard Frontend Logic
 * Handles data fetching, chart rendering, SOAR activity feed, and toast notifications
 */

const API_BASE = '/api/v1';
const REFRESH_INTERVAL = 5000;    // Main dashboard refresh (5s)
const SOAR_POLL_INTERVAL = 3000;  // SOAR notifications poll (3s)

let charts = {};
let lastSeenSoarId = 0;           // Track last SOAR notification for toast triggering
let toastQueue = [];

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    loadSoarFeed();

    setInterval(loadDashboard, REFRESH_INTERVAL);
    setInterval(loadSoarFeed, SOAR_POLL_INTERVAL);
});

// ============================================================================
// MAIN DASHBOARD DATA
// ============================================================================

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

// ============================================================================
// SOAR ACTIVITY FEED + TOAST NOTIFICATIONS
// ============================================================================

async function loadSoarFeed() {
    try {
        const data = await fetchJSON(`${API_BASE}/soar/notifications?limit=30`);

        if (data && data.status === 'success' && data.data) {
            renderSoarFeed(data.data);

            // Trigger toasts for new notifications
            if (lastSeenSoarId > 0) {
                const newActions = data.data.filter(n => n.id > lastSeenSoarId);
                newActions.reverse().forEach(action => {
                    showToast(action);
                });
            }

            // Update last seen ID
            if (data.data.length > 0) {
                lastSeenSoarId = Math.max(...data.data.map(n => n.id));
            }

            // Update SOAR engine status badge
            const badge = document.getElementById('soar-engine-status');
            if (badge) {
                badge.classList.add('active');
            }
        }
    } catch (error) {
        console.error('SOAR feed error:', error);
    }
}

function renderSoarFeed(notifications) {
    const container = document.getElementById('soar-feed');
    if (!container) return;

    if (!notifications || notifications.length === 0) {
        container.innerHTML = '<div class="no-data">🤖 SOAR engine active — waiting for threats...</div>';
        return;
    }

    container.innerHTML = notifications.map(n => {
        const statusClass = n.status || 'pending';
        const statusLabel = n.status === 'completed' ? '✅ RESOLVED' :
                           n.status === 'failed' ? '❌ FAILED' :
                           n.status === 'executing' ? '⏳ EXECUTING' : '⏳ PENDING';

        const time = n.created_at ? formatTime(n.created_at) : 'Unknown';

        return `
            <div class="soar-row ${n.status === 'failed' ? 'failed' : ''}">
                <div class="soar-row-header">
                    <span class="soar-action-icon">${n.action_icon || '⚡'}</span>
                    <span class="soar-action-label">${escapeHtml(n.action_label || n.action_type)}</span>
                    <span class="soar-status-badge ${statusClass}">${statusLabel}</span>
                </div>
                <div class="soar-row-description">${escapeHtml(n.description)}</div>
                <div class="soar-row-meta">
                    <span>${time}</span>
                    <span class="soar-target-badge">${escapeHtml(n.target)}</span>
                    <span>${escapeHtml(n.alert_rule)}</span>
                </div>
            </div>
        `;
    }).join('');
}

// ============================================================================
// TOAST NOTIFICATIONS
// ============================================================================

function showToast(action) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
        <div class="toast-header">
            <span class="toast-icon">${action.action_icon || '⚡'}</span>
            <span class="toast-title">Threat Auto-Resolved</span>
        </div>
        <div class="toast-body">
            ${escapeHtml(action.description)}
        </div>
        <div class="toast-meta">
            <span class="toast-badge completed">${escapeHtml(action.action_label || action.action_type)}</span>
            <span>Target: ${escapeHtml(action.target)}</span>
        </div>
    `;

    container.appendChild(toast);

    // Auto-dismiss after 8 seconds
    setTimeout(() => {
        toast.classList.add('toast-exit');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 8000);

    // Keep max 4 toasts visible
    const toasts = container.querySelectorAll('.toast:not(.toast-exit)');
    if (toasts.length > 4) {
        const oldest = toasts[0];
        oldest.classList.add('toast-exit');
        setTimeout(() => {
            if (oldest.parentNode) oldest.parentNode.removeChild(oldest);
        }, 300);
    }
}

// ============================================================================
// METRICS UPDATE
// ============================================================================

function updateMetrics(data) {
    setText('metric-logs', formatNumber(data.total_logs || 0));
    setText('metric-alerts', formatNumber(data.total_alerts || 0));
    setText('metric-high', formatNumber(data.alerts_by_severity?.HIGH || 0));
    setText('metric-medium', formatNumber(data.alerts_by_severity?.MEDIUM || 0));
    setText('metric-resolved', formatNumber(data.auto_resolved || 0));
    setText('metric-actions', formatNumber(data.total_soar_actions || 0));
    setText('metric-blocks', formatNumber(data.active_blocks || 0));
    setText('metric-open', formatNumber(data.alerts_by_status?.Open || 0));
}

// ============================================================================
// CHARTS
// ============================================================================

function updateCharts(data) {
    // Logs by Level — Doughnut
    renderDoughnutChart('chart-logs-level', 'logLevel', data.logs_by_level, [
        'rgba(0, 212, 255, 0.75)',
        'rgba(46, 213, 115, 0.75)',
        'rgba(245, 158, 11, 0.75)',
        'rgba(239, 68, 68, 0.75)'
    ]);

    // Alerts by Severity — Pie
    renderDoughnutChart('chart-alerts-severity', 'alertSeverity', data.alerts_by_severity, [
        'rgba(239, 68, 68, 0.75)',
        'rgba(245, 158, 11, 0.75)',
        'rgba(16, 185, 129, 0.75)'
    ]);

    // SOAR Actions by Type — Doughnut
    const soarColors = [
        'rgba(16, 185, 129, 0.75)',
        'rgba(0, 212, 255, 0.75)',
        'rgba(168, 85, 247, 0.75)',
        'rgba(59, 130, 246, 0.75)',
        'rgba(245, 158, 11, 0.75)',
        'rgba(239, 68, 68, 0.75)',
        'rgba(236, 72, 153, 0.75)',
    ];
    renderDoughnutChart('chart-soar-actions', 'soarActions', data.soar_actions_by_type, soarColors);

    // Logs by Host — Bar
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
                    backgroundColor: 'rgba(0, 212, 255, 0.6)',
                    borderColor: 'rgba(0, 212, 255, 1)',
                    borderWidth: 1,
                    borderRadius: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { labels: { color: '#e0e0e0', font: { family: 'Inter' } } }
                },
                scales: {
                    x: {
                        ticks: { color: '#9ca3af', font: { family: 'Inter', size: 11 } },
                        grid: { display: false }
                    },
                    y: {
                        ticks: { color: '#9ca3af', font: { family: 'Inter', size: 11 } },
                        grid: { color: 'rgba(255, 255, 255, 0.04)' }
                    }
                }
            }
        });
    }
}

function renderDoughnutChart(canvasId, chartKey, dataObj, colors) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const labels = Object.keys(dataObj || {});
    const values = Object.values(dataObj || {});

    if (charts[chartKey]) charts[chartKey].destroy();
    charts[chartKey] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderColor: colors.slice(0, labels.length).map(c => c.replace(/[\d.]+\)$/, '1)')),
                borderWidth: 2,
                hoverOffset: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '55%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#e0e0e0',
                        font: { family: 'Inter', size: 11 },
                        padding: 12,
                    }
                }
            }
        }
    });
}

// ============================================================================
// TABLES (Recent Logs + Alerts)
// ============================================================================

function updateTables(data) {
    // Recent Logs
    const logsContainer = document.getElementById('table-logs');
    if (logsContainer) {
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
    }

    // Recent Alerts
    const alertsContainer = document.getElementById('table-alerts');
    if (alertsContainer) {
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
}

// ============================================================================
// UTILITIES
// ============================================================================

async function fetchJSON(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
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
    if (!isoString) return 'Unknown';
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function truncate(str, len) {
    if (!str) return '';
    return str.length > len ? str.substring(0, len - 3) + '...' : str;
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
