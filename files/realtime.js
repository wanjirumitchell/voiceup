// ─── VoiceUp Real-Time Features ───────────────────────────────────────────────

// ─── 1. LIVE NOTIFICATION BELL ───────────────────────────────────────────────
function startNotificationPolling() {
  const badge = document.querySelector('.notif-badge');
  const btn   = document.querySelector('.notif-btn');
  if (!btn) return;

  setInterval(async () => {
    try {
      const res  = await fetch('/notifications/count');
      const data = await res.json();
      const count = data.count;
      if (count > 0) {
        if (!badge) {
          const b = document.createElement('span');
          b.className = 'notif-badge';
          b.id = 'notifBadge';
          b.textContent = count;
          btn.appendChild(b);
        } else {
          badge.textContent = count;
          badge.style.display = 'flex';
        }
        // Pulse animation
        btn.classList.add('notif-pulse');
        setTimeout(() => btn.classList.remove('notif-pulse'), 1000);
      } else {
        if (badge) badge.style.display = 'none';
      }
    } catch(e) {}
  }, 15000); // every 15 seconds
}

// ─── 2. LIVE ADMIN STATS ─────────────────────────────────────────────────────
function startAdminStatsPolling() {
  const statEls = {
    total:        document.getElementById('stat-total'),
    pending:      document.getElementById('stat-pending'),
    under_review: document.getElementById('stat-reviewing'),
    resolved:     document.getElementById('stat-resolved'),
    overdue:      document.getElementById('stat-overdue'),
  };

  if (!statEls.total) return;

  setInterval(async () => {
    try {
      const res  = await fetch('/admin/api/stats');
      const data = await res.json();
      Object.entries(statEls).forEach(([key, el]) => {
        if (el && data[key] !== undefined) {
          const old = parseInt(el.textContent);
          const nw  = data[key];
          if (old !== nw) {
            el.textContent = nw;
            el.classList.add('stat-updated');
            setTimeout(() => el.classList.remove('stat-updated'), 1000);
          }
        }
      });
    } catch(e) {}
  }, 20000); // every 20 seconds
}

// ─── 3. LIVE SUGGESTION STATUS (on detail page) ──────────────────────────────
function startStatusPolling(suggestionId) {
  const statusBadge = document.getElementById('live-status');
  if (!statusBadge || !suggestionId) return;

  let lastStatus = statusBadge.textContent.trim();

  setInterval(async () => {
    try {
      const res  = await fetch(`/api/suggestion-status/${suggestionId}`);
      const data = await res.json();
      if (data.status && data.status !== lastStatus) {
        lastStatus = data.status;
        statusBadge.textContent = data.status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        statusBadge.className = `badge badge-status-${data.status}`;

        // Show toast notification
        showToast(`Status updated to: ${lastStatus}`, 'success');
      }
    } catch(e) {}
  }, 10000); // every 10 seconds
}

// ─── 4. TOAST NOTIFICATIONS ──────────────────────────────────────────────────
function showToast(message, type='info') {
  const container = document.getElementById('toastContainer') || createToastContainer();
  const toast = document.createElement('div');
  toast.className = `toast-item toast-${type}`;
  toast.innerHTML = `
    <div class="d-flex align-items-center gap-2">
      <i class="fas ${type==='success'?'fa-check-circle':type==='danger'?'fa-exclamation-circle':'fa-info-circle'}"></i>
      <span>${message}</span>
    </div>`;
  container.appendChild(toast);
  setTimeout(() => toast.classList.add('toast-show'), 10);
  setTimeout(() => {
    toast.classList.remove('toast-show');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function createToastContainer() {
  const div = document.createElement('div');
  div.id = 'toastContainer';
  div.className = 'toast-container';
  document.body.appendChild(div);
  return div;
}

// ─── 5. LIVE VOTE COUNT ON PUBLIC BOARD ──────────────────────────────────────
function startVotePolling() {
  const voteButtons = document.querySelectorAll('.btn-vote[data-id]');
  if (!voteButtons.length) return;

  const ids = Array.from(voteButtons).map(b => b.dataset.id);

  setInterval(async () => {
    try {
      const res  = await fetch(`/api/vote-counts?ids=${ids.join(',')}`);
      const data = await res.json();
      if (data.counts) {
        data.counts.forEach(item => {
          const btn = document.querySelector(`.btn-vote[data-id="${item.id}"]`);
          if (btn) {
            const countEl = btn.querySelector('.vote-count');
            if (countEl && parseInt(countEl.textContent) !== item.count) {
              countEl.textContent = item.count;
              countEl.classList.add('vote-updated');
              setTimeout(() => countEl.classList.remove('vote-updated'), 500);
            }
          }
        });
      }
    } catch(e) {}
  }, 30000); // every 30 seconds
}

// ─── 6. REAL-TIME CLOCK ──────────────────────────────────────────────────────
function startLiveClock() {
  const el = document.getElementById('liveClock');
  if (!el) return;
  setInterval(() => {
    const now = new Date();
    el.textContent = now.toLocaleTimeString();
  }, 1000);
}

// ─── 7. AUTO-REFRESH ADMIN DASHBOARD TABLE ───────────────────────────────────
function startDashboardAutoRefresh() {
  const indicator = document.getElementById('refreshIndicator');
  if (!indicator) return;

  let countdown = 60;
  setInterval(() => {
    countdown--;
    if (indicator) indicator.textContent = `Auto-refresh in ${countdown}s`;
    if (countdown <= 0) {
      countdown = 60;
      // Only refresh if user hasn't typed in search
      const search = document.querySelector('input[name="search"]');
      if (!search || !search.value) {
        location.reload();
      }
    }
  }, 1000);
}

// ─── START ALL POLLING ON PAGE LOAD ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  startNotificationPolling();
  startAdminStatsPolling();
  startVotePolling();
  startLiveClock();
  startDashboardAutoRefresh();

  // Start status polling if on suggestion detail page
  const statusEl = document.getElementById('live-status');
  if (statusEl) {
    const suggId = statusEl.dataset.suggestionId;
    if (suggId) startStatusPolling(suggId);
  }
});
