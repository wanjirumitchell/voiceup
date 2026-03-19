// ─── Dark Mode ───────────────────────────────────────────────────────────────
const html      = document.documentElement;
const themeBtn  = document.getElementById('themeToggle');
const themeIcon = document.getElementById('themeIcon');

function applyTheme(theme) {
  html.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
  if (themeIcon) {
    themeIcon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
  }
}

// Apply saved theme on load
const savedTheme = localStorage.getItem('theme') || 'light';
applyTheme(savedTheme);

if (themeBtn) {
  themeBtn.addEventListener('click', () => {
    const current = html.getAttribute('data-theme');
    applyTheme(current === 'dark' ? 'light' : 'dark');
  });
}

// ─── Auto-dismiss alerts ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    document.querySelectorAll('.alert').forEach(a => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(a);
      if (bsAlert) bsAlert.close();
    });
  }, 5000);
});

// ─── File Upload Preview ─────────────────────────────────────────────────────
function initFileUpload() {
  const input    = document.getElementById('fileInput');
  const list     = document.getElementById('fileList');
  const zone     = document.getElementById('uploadZone');
  if (!input || !list || !zone) return;

  input.addEventListener('change', updateFileList);

  zone.addEventListener('dragover', e => {
    e.preventDefault();
    zone.classList.add('drag-over');
  });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    input.files = e.dataTransfer.files;
    updateFileList();
  });

  function updateFileList() {
    list.innerHTML = '';
    Array.from(input.files).forEach(f => {
      const size = f.size > 1024*1024
        ? (f.size/1024/1024).toFixed(1) + ' MB'
        : (f.size/1024).toFixed(1) + ' KB';
      const icon = f.type.startsWith('image/') ? 'fa-image' : 'fa-file';
      list.innerHTML += `
        <div class="file-item d-flex align-items-center">
          <i class="fas ${icon} me-2 text-primary"></i>
          <span>${f.name}</span>
          <small class="text-muted ms-2">(${size})</small>
        </div>`;
    });
  }
}

document.addEventListener('DOMContentLoaded', initFileUpload);

// ─── Character Counter for Textarea ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('textarea[minlength]').forEach(ta => {
    const min = parseInt(ta.getAttribute('minlength'));
    const counter = document.createElement('small');
    counter.className = 'text-muted float-end';
    ta.parentNode.appendChild(counter);
    const update = () => {
      const len = ta.value.length;
      counter.textContent = `${len} chars ${len >= min ? '✓' : `(min ${min})`}`;
      counter.className = len >= min ? 'text-success float-end' : 'text-muted float-end';
    };
    ta.addEventListener('input', update);
    update();
  });
});

// ─── Confirm Dialogs ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => {
      if (!confirm(el.getAttribute('data-confirm'))) e.preventDefault();
    });
  });
});

// ─── Active nav link ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.getAttribute('href') === path) link.classList.add('active');
  });
});
