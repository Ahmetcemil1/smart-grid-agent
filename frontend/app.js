/**
 * ════════════════════════════════════════════════════════════
 *  Smart-Grid Agent — Dashboard Application Logic
 *  Real-time metrics, human-in-the-loop approval UI,
 *  savings charts, and audit log viewer.
 * ════════════════════════════════════════════════════════════
 */

const API_BASE = window.location.origin;
const REFRESH_INTERVAL_MS = 8000; // 8 seconds

// ─────────────────────────────────────────────
//  State
// ─────────────────────────────────────────────
const state = {
  cpuHistory: [],
  memHistory: [],
  labels: [],
  maxHistoryPoints: 30,
  currentActionId: null,
  currentActionData: null,
  savingsHistory: [],
  lastStatus: null,
};

// ─────────────────────────────────────────────
//  Chart Instances
// ─────────────────────────────────────────────
let cpuChart = null;
let savingsChart = null;
let donutChart = null;

// ─────────────────────────────────────────────
//  Navigation
// ─────────────────────────────────────────────
function showSection(name) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

  const section = document.getElementById(`section-${name}`);
  const btn = document.getElementById(`nav-${name}`);

  if (section) section.classList.add('active');
  if (btn) btn.classList.add('active');

  // Load section-specific data
  if (name === 'actions') refreshActions();
  if (name === 'savings') refreshSavings();
  if (name === 'logs') refreshLogs();
}

// ─────────────────────────────────────────────
//  API Helpers
// ─────────────────────────────────────────────
async function apiFetch(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.error(`API error [${endpoint}]:`, e);
    return null;
  }
}

// ─────────────────────────────────────────────
//  CPU Chart
// ─────────────────────────────────────────────
function initCpuChart() {
  const ctx = document.getElementById('chart-cpu').getContext('2d');
  const gradient = ctx.createLinearGradient(0, 0, 0, 200);
  gradient.addColorStop(0, 'rgba(99, 102, 241, 0.4)');
  gradient.addColorStop(1, 'rgba(99, 102, 241, 0.0)');

  cpuChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'CPU %',
          data: [],
          borderColor: '#6366f1',
          backgroundColor: gradient,
          borderWidth: 2,
          pointRadius: 2,
          pointHoverRadius: 5,
          fill: true,
          tension: 0.4,
        },
        {
          label: 'Memory %',
          data: [],
          borderColor: 'rgba(6, 182, 212, 0.6)',
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          pointRadius: 0,
          fill: false,
          tension: 0.4,
          borderDash: [4, 4],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(12, 20, 36, 0.95)',
          borderColor: 'rgba(99, 102, 241, 0.3)',
          borderWidth: 1,
          titleColor: '#f1f5f9',
          bodyColor: '#94a3b8',
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.raw.toFixed(1)}%`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.03)' },
          ticks: { color: '#475569', maxTicksLimit: 8, font: { size: 11 } },
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.03)' },
          ticks: { color: '#475569', font: { size: 11 }, callback: v => `${v}%` },
          min: 0,
          max: 100,
          suggestedMax: 100,
        },
      },
    },
  });
}

function updateCpuChart(cpu, mem) {
  if (!cpuChart) return;
  const now = new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  state.labels.push(now);
  state.cpuHistory.push(parseFloat(cpu.toFixed(2)));
  state.memHistory.push(parseFloat(mem.toFixed(2)));

  if (state.labels.length > state.maxHistoryPoints) {
    state.labels.shift();
    state.cpuHistory.shift();
    state.memHistory.shift();
  }

  cpuChart.data.labels = state.labels;
  cpuChart.data.datasets[0].data = state.cpuHistory;
  cpuChart.data.datasets[1].data = state.memHistory;
  cpuChart.update('none');
}

// ─────────────────────────────────────────────
//  Savings Chart
// ─────────────────────────────────────────────
function initSavingsChart() {
  const ctx = document.getElementById('chart-savings').getContext('2d');
  const gradCPU = ctx.createLinearGradient(0, 0, 0, 280);
  gradCPU.addColorStop(0, 'rgba(16, 185, 129, 0.3)');
  gradCPU.addColorStop(1, 'rgba(16, 185, 129, 0.0)');

  savingsChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'CPU Saved %',
          data: [],
          borderColor: '#10b981',
          backgroundColor: gradCPU,
          borderWidth: 2,
          pointRadius: 3,
          fill: true,
          tension: 0.4,
          yAxisID: 'yCPU',
        },
        {
          label: 'Cost Saved $',
          data: [],
          borderColor: '#6366f1',
          backgroundColor: 'transparent',
          borderWidth: 2,
          pointRadius: 3,
          fill: false,
          tension: 0.4,
          yAxisID: 'yCost',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 600 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(12, 20, 36, 0.95)',
          borderColor: 'rgba(99, 102, 241, 0.3)',
          borderWidth: 1,
        },
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#475569', font: { size: 11 } } },
        yCPU: { position: 'left', grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#10b981', font: { size: 11 } } },
        yCost: { position: 'right', grid: { display: false }, ticks: { color: '#6366f1', font: { size: 11 }, callback: v => `$${v.toFixed(4)}` } },
      },
    },
  });
}

function initDonutChart() {
  const ctx = document.getElementById('chart-donut').getContext('2d');
  donutChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Executed', 'Pending', 'Rejected', 'Failed'],
      datasets: [{
        data: [0, 0, 0, 0],
        backgroundColor: ['rgba(99,102,241,0.7)', 'rgba(245,158,11,0.7)', 'rgba(239,68,68,0.7)', 'rgba(100,100,100,0.5)'],
        borderColor: ['#6366f1', '#f59e0b', '#ef4444', '#666'],
        borderWidth: 2,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#94a3b8', font: { size: 11 }, padding: 16 },
        },
      },
    },
  });
}

// ─────────────────────────────────────────────
//  Metrics Update
// ─────────────────────────────────────────────
async function refreshMetrics() {
  const data = await apiFetch('/api/metrics');
  if (!data || !data.metrics) return;

  const m = data.metrics;
  const now = new Date().toLocaleTimeString('en-GB');
  document.getElementById('last-update-time').textContent = now;

  // CPU Card
  const cpu = m.cpu || 0;
  document.getElementById('metric-cpu').textContent = `${cpu.toFixed(1)}%`;
  const barCPU = document.getElementById('bar-cpu');
  barCPU.style.width = `${Math.min(cpu, 100)}%`;
  barCPU.setAttribute('aria-valuenow', cpu.toFixed(1));
  barCPU.className = 'metric-bar-fill' + (cpu > 80 ? ' critical' : cpu > 60 ? ' warning' : '');

  // Memory Card
  const mem = m.memory || 0;
  document.getElementById('metric-memory').textContent = `${mem.toFixed(1)}%`;
  const barMem = document.getElementById('bar-memory');
  barMem.style.width = `${Math.min(mem, 100)}%`;
  barMem.setAttribute('aria-valuenow', mem.toFixed(1));
  barMem.className = 'metric-bar-fill' + (mem > 85 ? ' critical' : mem > 70 ? ' warning' : '');

  // Disk I/O Card
  const diskRead = (m.disk_io_read || 0).toFixed(1);
  const diskWrite = (m.disk_io_write || 0).toFixed(1);
  document.getElementById('metric-disk').textContent = `${diskRead} MB/s`;
  document.getElementById('metric-disk-sub').textContent = `↑ Write: ${diskWrite} MB/s`;

  // Status Card
  const status = m.status || 'unknown';
  document.getElementById('metric-status').textContent = status.toUpperCase();
  const badge = document.getElementById('status-badge');
  badge.textContent = status;
  badge.className = `status-badge ${status}`;

  // Update CPU chart
  updateCpuChart(cpu, mem);

  // Services list
  renderServicesList(m.services || []);
}

function renderServicesList(services) {
  const container = document.getElementById('services-list');
  const badge = document.getElementById('services-count-badge');
  badge.textContent = `${services.length} service${services.length !== 1 ? 's' : ''}`;

  if (services.length === 0) {
    container.innerHTML = '<div class="log-placeholder">No non-critical services running.</div>';
    return;
  }

  container.innerHTML = services.map(s => `
    <div class="service-item" role="listitem">
      <span class="service-name">${escapeHtml(s.name)}</span>
      <span class="service-meta">
        <span class="service-cpu">⚡ ${(s.cpu || 0).toFixed(1)}%</span>
        <span class="service-mem">🧠 ${(s.memory_mb || 0).toFixed(0)} MB</span>
      </span>
    </div>
  `).join('');
}

// ─────────────────────────────────────────────
//  Brain Status Update
// ─────────────────────────────────────────────
async function refreshBrainStatus() {
  const status = await apiFetch('/api/status');
  if (!status) return;

  // Agent status pill
  const dot = document.getElementById('status-dot');
  const text = document.getElementById('agent-status-text');
  if (status.status === 'running') {
    dot.className = 'status-dot running';
    text.textContent = `Running • Tick #${status.tick}`;
  } else {
    dot.className = 'status-dot stopped';
    text.textContent = 'Stopped';
  }

  // Get last decision
  const metricsData = await apiFetch('/api/metrics');
  if (!metricsData) return;

  // Re-fetch for decision (from trigger cycle result)
  state.lastStatus = status;
}

function updateBrainDisplay(decision) {
  if (!decision) return;

  document.getElementById('brain-engine').textContent =
    `Engine: ${decision.brain || 'local-rule-engine'} • Confidence: ${((decision.confidence || 0) * 100).toFixed(0)}%`;

  document.getElementById('brain-confidence').textContent =
    `${((decision.confidence || 0) * 100).toFixed(0)}% confident`;

  document.getElementById('brain-analysis').textContent =
    decision.analysis || 'No analysis available.';

  const preview = document.getElementById('brain-actions-preview');
  const actions = decision.actions || [];
  if (actions.length > 0) {
    preview.innerHTML = actions.map(a =>
      `<div class="brain-action-chip">
        ${getActionEmoji(a.action)} ${escapeHtml(a.action?.toUpperCase())} ${escapeHtml(a.service)}
      </div>`
    ).join('');
  } else {
    preview.innerHTML = '<div class="brain-action-chip">✅ No actions recommended</div>';
  }
}

// ─────────────────────────────────────────────
//  Actions Panel
// ─────────────────────────────────────────────
async function refreshActions() {
  const [pendingData, allData] = await Promise.all([
    apiFetch('/api/actions/pending'),
    apiFetch('/api/actions?limit=20'),
  ]);

  if (!pendingData || !allData) return;

  const pending = pendingData.pending || [];
  const all = allData.actions || [];

  // Update count badge
  document.getElementById('pending-count').textContent = pending.length;
  const emptyEl = document.getElementById('empty-actions');

  // Render pending actions
  const container = document.getElementById('pending-actions-container');
  if (pending.length === 0) {
    container.innerHTML = '';
    if (emptyEl) emptyEl.style.display = 'block';
    // Re-append the empty state
    container.appendChild(emptyEl || createEmptyState());
    emptyEl && (emptyEl.style.display = 'block');
  } else {
    if (emptyEl) emptyEl.style.display = 'none';
    container.innerHTML = pending.map(a => renderActionCard(a, true)).join('');
  }

  // Render recent non-pending actions
  const recent = all.filter(a => a.status !== 'pending').slice(-10).reverse();
  const recentContainer = document.getElementById('recent-actions-container');
  if (recent.length === 0) {
    recentContainer.innerHTML = '<div class="log-placeholder" style="text-align:center;padding:2rem;color:var(--text-muted)">No completed actions yet.</div>';
  } else {
    recentContainer.innerHTML = recent.map(a => renderActionCard(a, false)).join('');
  }
}

function renderActionCard(action, isPending) {
  const statusIcons = {
    pending: '⏳',
    approved: '✅',
    executed: '✅',
    rejected: '❌',
    failed: '⚠️',
  };

  const icon = statusIcons[action.status] || '❓';
  const time = new Date(action.timestamp).toLocaleString('en-GB');

  return `
    <div class="action-card ${action.status}" id="action-card-${action.id}">
      <div class="action-icon">${getServiceEmoji(action.service)}</div>
      <div class="action-content">
        <div class="action-service">
          ${escapeHtml(action.service)}
          <span class="action-type-badge ${action.action_type}">${escapeHtml(action.action_type || 'stop')}</span>
        </div>
        <div class="action-reason">${escapeHtml(action.reason || 'AI recommendation')}</div>
        <div class="action-meta">
          <span>🕐 ${time}</span>
          <span>⚡ Save <strong>${(action.estimated_cpu_save || 0).toFixed(1)}%</strong> CPU</span>
          <span>🧠 Save <strong>${(action.estimated_memory_save_mb || 0).toFixed(0)}MB</strong> RAM</span>
          <span>Priority: <strong>${action.priority || 'medium'}</strong></span>
        </div>
      </div>
      <div class="action-buttons">
        ${isPending ? `
          <button class="btn-success" onclick="openApprovalModal('${action.id}')" id="btn-approve-${action.id}">
            ✓ Approve
          </button>
          <button class="btn-danger" onclick="rejectAction('${action.id}')" id="btn-reject-${action.id}">
            ✕ Reject
          </button>
        ` : `
          <span class="action-status-badge ${action.status}">
            ${icon} ${(action.status || '').toUpperCase()}
          </span>
        `}
      </div>
    </div>
  `;
}

// ─────────────────────────────────────────────
//  Approval Modal
// ─────────────────────────────────────────────
function openApprovalModal(actionId) {
  // Find action data
  apiFetch('/api/actions?limit=100').then(data => {
    if (!data) return;
    const action = (data.actions || []).find(a => a.id === actionId);
    if (!action) return;

    state.currentActionId = actionId;
    state.currentActionData = action;

    document.getElementById('modal-service-name').textContent = action.service;
    document.getElementById('modal-action-type').textContent = `Action: ${(action.action_type || 'stop').toUpperCase()}`;
    document.getElementById('modal-reason').textContent = action.reason || 'AI-driven recommendation';
    document.getElementById('modal-cpu-save').textContent = `${(action.estimated_cpu_save || 0).toFixed(2)}%`;
    document.getElementById('modal-mem-save').textContent = `${(action.estimated_memory_save_mb || 0).toFixed(0)} MB`;

    document.getElementById('approval-modal').removeAttribute('hidden');
    document.getElementById('modal-approve-btn').focus();
  });
}

function closeModal() {
  document.getElementById('approval-modal').setAttribute('hidden', '');
  state.currentActionId = null;
}

async function approveFromModal() {
  if (!state.currentActionId) return;
  const btn = document.getElementById('modal-approve-btn');
  btn.textContent = 'Executing...';
  btn.disabled = true;

  const result = await apiFetch('/api/actions/approve', {
    method: 'POST',
    body: JSON.stringify({ action_id: state.currentActionId, approved_by: 'human-dashboard' }),
  });

  closeModal();

  if (result?.success) {
    showToast('✅ Action approved and executed successfully!', 'success');
    refreshActions();
    refreshSavings();
  } else {
    showToast('❌ Failed to execute action.', 'error');
  }
}

async function rejectFromModal() {
  if (!state.currentActionId) return;
  const result = await apiFetch('/api/actions/reject', {
    method: 'POST',
    body: JSON.stringify({ action_id: state.currentActionId, reason: 'Rejected via dashboard' }),
  });
  closeModal();
  if (result?.success) {
    showToast('Action rejected.', 'info');
    refreshActions();
  }
}

async function rejectAction(actionId) {
  const result = await apiFetch('/api/actions/reject', {
    method: 'POST',
    body: JSON.stringify({ action_id: actionId, reason: 'Rejected by operator' }),
  });
  if (result?.success) {
    showToast('Action rejected.', 'info');
    refreshActions();
  }
}

// ─────────────────────────────────────────────
//  Savings Dashboard
// ─────────────────────────────────────────────
async function refreshSavings() {
  const [savings, history] = await Promise.all([
    apiFetch('/api/savings'),
    apiFetch('/api/savings/history'),
  ]);

  if (!savings) return;

  const cum = savings.cumulative_savings || {};
  const proj = savings.projections || {};
  const statusDist = savings.actions_by_status || {};

  // Hero stats
  setText('savings-cpu', `${(cum.cpu_percent_hours || 0).toFixed(2)}%`);
  setText('savings-mem', `${(cum.memory_mb_hours || 0).toFixed(0)} MB`);
  setText('savings-cost', `$${(cum.cost_usd || 0).toFixed(6)}`);
  setText('savings-executed', savings.total_executed || 0);

  // Projections
  setText('proj-daily', `$${(proj.daily_cost_save_usd || 0).toFixed(4)}`);
  setText('proj-monthly', `$${(proj.monthly_cost_save_usd || 0).toFixed(2)}`);
  setText('proj-approved', savings.total_approved || 0);
  setText('proj-rejected', savings.total_rejected || 0);

  // Donut chart
  if (donutChart) {
    donutChart.data.datasets[0].data = [
      statusDist.executed || 0,
      statusDist.pending || 0,
      statusDist.rejected || 0,
      statusDist.failed || 0,
    ];
    donutChart.update();
  }

  // Savings timeline chart
  if (history && savingsChart) {
    const timeline = history.timeline || [];
    savingsChart.data.labels = timeline.map(t =>
      t.timestamp ? new Date(t.timestamp).toLocaleTimeString('en-GB') : '?'
    );
    savingsChart.data.datasets[0].data = timeline.map(t => t.cumulative_cpu || 0);
    savingsChart.data.datasets[1].data = timeline.map(t => t.cumulative_cost || 0);
    savingsChart.update();

    // Savings by service
    const serviceMap = {};
    timeline.forEach(t => {
      if (!serviceMap[t.service]) serviceMap[t.service] = { cpu: 0, mem: 0 };
      serviceMap[t.service].cpu += t.cpu_saved || 0;
      serviceMap[t.service].mem += t.memory_saved_mb || 0;
    });

    const sbsContainer = document.getElementById('savings-by-service');
    const entries = Object.entries(serviceMap);
    if (entries.length === 0) {
      sbsContainer.innerHTML = '<div class="log-placeholder">No executed actions yet.</div>';
    } else {
      sbsContainer.innerHTML = entries.map(([name, vals]) => `
        <div class="service-item">
          <span class="service-name">${escapeHtml(name)}</span>
          <span class="service-meta">
            <span class="service-cpu">⚡ ${vals.cpu.toFixed(1)}%</span>
            <span class="service-mem">🧠 ${vals.mem.toFixed(0)}MB</span>
          </span>
        </div>
      `).join('');
    }
  }
}

// ─────────────────────────────────────────────
//  Logs
// ─────────────────────────────────────────────
async function refreshLogs() {
  const data = await apiFetch('/api/log');
  if (!data) return;

  const actions = (data.actions || []).reverse();
  const terminal = document.getElementById('log-terminal');

  if (actions.length === 0) {
    terminal.innerHTML = '<div class="log-placeholder">No actions logged yet.</div>';
    return;
  }

  terminal.innerHTML = actions.map(a => {
    const time = a.timestamp ? new Date(a.timestamp).toLocaleString('en-GB') : '?';
    return `
      <div class="log-entry">
        <span class="log-time">${time}</span>
        <span class="log-status ${a.status}">${(a.status || '').toUpperCase()}</span>
        <span class="log-service">${escapeHtml(a.service || '?')}</span>
        <span class="log-detail">${escapeHtml(a.reason?.substring(0, 100) || '')}...</span>
      </div>
    `;
  }).join('');
}

// ─────────────────────────────────────────────
//  Manual Cycle Trigger
// ─────────────────────────────────────────────
async function triggerCycle() {
  const btn = document.getElementById('btn-run-cycle');
  btn.textContent = '⏳ Running...';
  btn.disabled = true;

  const result = await apiFetch('/api/agent/cycle', { method: 'POST' });

  btn.textContent = '▶ Run Cycle';
  btn.disabled = false;

  if (result?.success) {
    showToast(`✅ Cycle complete: ${result.decision_actions} actions found, ${result.new_actions_queued} queued`, 'success');
    if (result.decision) updateBrainDisplay(result.decision);
    await refreshMetrics();
    await refreshActions();
    // Update pending badge in nav
    const pending = await apiFetch('/api/actions/pending');
    if (pending) {
      document.getElementById('pending-count').textContent = pending.count || 0;
    }
  } else {
    showToast('⚠️ Cycle failed. Is the backend running?', 'error');
  }
}

// ─────────────────────────────────────────────
//  Utility Functions
// ─────────────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  toast.setAttribute('role', 'status');
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function getServiceEmoji(service) {
  if (!service) return '⚙️';
  if (service.includes('baloo') || service.includes('tracker')) return '🔍';
  if (service.includes('package') || service.includes('apt')) return '📦';
  if (service.includes('evolution') || service.includes('calendar')) return '📅';
  if (service.includes('bluetooth')) return '📡';
  if (service.includes('cups') || service.includes('print')) return '🖨️';
  return '⚙️';
}

function getActionEmoji(action) {
  const map = { stop: '🛑', restart: '🔄', throttle: '⚡', monitor: '👁' };
  return map[action] || '⚙️';
}

// Close modal on overlay click
document.getElementById('approval-modal').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) closeModal();
});

// Keyboard: ESC closes modal
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});

// ─────────────────────────────────────────────
//  Initialization
// ─────────────────────────────────────────────
async function init() {
  console.log('🤖 Smart-Grid Agent Dashboard initializing...');

  // Initialize charts
  initCpuChart();
  initSavingsChart();
  initDonutChart();

  // Initial data load
  await refreshMetrics();
  await refreshBrainStatus();

  // Trigger first cycle to get brain data
  const result = await apiFetch('/api/agent/cycle', { method: 'POST' });
  if (result?.decision) updateBrainDisplay(result.decision);

  // Check pending actions
  const pending = await apiFetch('/api/actions/pending');
  if (pending?.count > 0) {
    document.getElementById('pending-count').textContent = pending.count;
    showToast(`⏳ ${pending.count} action(s) awaiting your approval!`, 'info', 6000);
  }

  // Start auto-refresh loop
  setInterval(async () => {
    await refreshMetrics();
    await refreshBrainStatus();

    // Update pending count indicator
    const pendingData = await apiFetch('/api/actions/pending');
    if (pendingData) {
      document.getElementById('pending-count').textContent = pendingData.count || 0;
    }
  }, REFRESH_INTERVAL_MS);

  // Auto-run cycle every 30 seconds
  setInterval(async () => {
    const cycleResult = await apiFetch('/api/agent/cycle', { method: 'POST' });
    if (cycleResult?.decision) updateBrainDisplay(cycleResult.decision);
  }, 30000);

  console.log('✅ Dashboard ready!');
}

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', init);
