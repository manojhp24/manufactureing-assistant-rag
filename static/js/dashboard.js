/**
 * Manufacturing Manual Assistant - Dashboard UI & UX Engine
 * Separate module dedicated to dashboard interactivity:
 * - Live client-side instant search & filtering
 * - Asynchronous partial page updates via fetch()
 * - Telemetry sync & live timestamp updates
 * - Quick copy-to-clipboard for industrial codes & identifiers
 * - Keyboard navigation (press '/' to filter equipment)
 */

document.addEventListener('DOMContentLoaded', () => {
  initDashboardSearch();
  initDashboardStatusFilters();
  initPartialTelemetrySync();
  initClickToCopy();
  initQuickPromptNavigation();
});

/**
 * 1. Live Instant Search & Equipment Filtering
 */
function initDashboardSearch() {
  const searchInput = document.getElementById('dashboardSearchInput');
  if (!searchInput) return;

  // Keyboard shortcut: '/' focuses search input unless already focused in an input/textarea
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== searchInput && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
      e.preventDefault();
      searchInput.focus();
      searchInput.select();
    }
    if (e.key === 'Escape' && document.activeElement === searchInput) {
      searchInput.value = '';
      searchInput.dispatchEvent(new Event('input'));
      searchInput.blur();
    }
  });

  searchInput.addEventListener('input', () => {
    const query = searchInput.value.toLowerCase().trim();
    filterDashboardContent(query);
  });
}

function filterDashboardContent(query) {
  // Filter machine fleet cards (Engineer Dashboard)
  const machineCards = document.querySelectorAll('.machine-fleet-card');
  let visibleCards = 0;

  machineCards.forEach((card) => {
    const title = (card.querySelector('.machine-card-title')?.textContent || '').toLowerCase();
    const model = (card.querySelector('.table-code')?.textContent || '').toLowerCase();
    const desc = (card.querySelector('.machine-card-desc')?.textContent || '').toLowerCase();

    const matches = !query || title.includes(query) || model.includes(query) || desc.includes(query);
    card.style.display = matches ? 'flex' : 'none';
    if (matches) visibleCards++;
  });

  const emptyCardNotice = document.getElementById('fleetSearchEmptyNotice');
  if (emptyCardNotice) {
    emptyCardNotice.style.display = (visibleCards === 0 && machineCards.length > 0) ? 'block' : 'none';
  }

  // Filter table rows (Admin & Supervisor Dashboards)
  const filterableTables = document.querySelectorAll('[data-filterable-table]');
  filterableTables.forEach((table) => {
    const rows = table.querySelectorAll('tbody tr:not(.table-empty-row)');
    let visibleRows = 0;

    rows.forEach((row) => {
      const text = row.textContent.toLowerCase();
      const matches = !query || text.includes(query);
      row.style.display = matches ? '' : 'none';
      if (matches) visibleRows++;
    });

    const emptyRow = table.querySelector('.table-search-empty-row');
    if (emptyRow) {
      emptyRow.style.display = (visibleRows === 0 && rows.length > 0) ? '' : 'none';
    }
  });
}

/**
 * 2. Status Filter Pills
 */
function initDashboardStatusFilters() {
  const filterPills = document.querySelectorAll('.filter-pill-btn');
  if (!filterPills.length) return;

  filterPills.forEach((btn) => {
    btn.addEventListener('click', () => {
      filterPills.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');

      const statusFilter = btn.getAttribute('data-status-filter');
      const rows = document.querySelectorAll('tbody tr[data-status]');

      rows.forEach((row) => {
        const rowStatus = row.getAttribute('data-status');
        if (statusFilter === 'all' || rowStatus === statusFilter) {
          row.style.display = '';
        } else {
          row.style.display = 'none';
        }
      });
    });
  });
}

/**
 * 3. Asynchronous Partial Page Updates via fetch()
 * Pulls latest KPI counts, uploads, and telemetry without full-page reloads
 */
function initPartialTelemetrySync() {
  const syncBtn = document.getElementById('syncTelemetryBtn');
  const syncTimeEl = document.getElementById('telemetrySyncTime');
  if (!syncBtn) return;

  let isSyncing = false;

  async function performPartialSync() {
    if (isSyncing) return;
    isSyncing = true;
    syncBtn.classList.add('syncing');
    syncBtn.disabled = true;

    try {
      const response = await fetch(window.location.href, {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Cache-Control': 'no-cache',
        },
      });

      if (!response.ok) throw new Error(`HTTP error ${response.status}`);

      const htmlText = await response.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(htmlText, 'text/html');

      // 1. Update KPI Strip with smooth subtle highlight
      const newKpiStrip = doc.querySelector('.kpi-strip');
      const currentKpiStrip = document.querySelector('.kpi-strip');
      if (newKpiStrip && currentKpiStrip) {
        currentKpiStrip.innerHTML = newKpiStrip.innerHTML;
        currentKpiStrip.classList.add('kpi-updated-pulse');
        setTimeout(() => currentKpiStrip.classList.remove('kpi-updated-pulse'), 1000);
      }

      // 2. Update Dynamic Panels / Tables
      ['adminRecentUploads', 'adminActivityStream', 'supervisorMachineActivity', 'engineerRecentQueries'].forEach((containerId) => {
        const newEl = doc.getElementById(containerId);
        const currentEl = document.getElementById(containerId);
        if (newEl && currentEl) {
          currentEl.innerHTML = newEl.innerHTML;
        }
      });

      // 3. Update Sync Timestamp
      if (syncTimeEl) {
        const now = new Date();
        syncTimeEl.textContent = `Synced ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
      }

      // Re-apply any active search filters to newly injected markup
      const searchInput = document.getElementById('dashboardSearchInput');
      if (searchInput && searchInput.value.trim()) {
        filterDashboardContent(searchInput.value.toLowerCase().trim());
      }

      // Re-attach copy handlers
      initClickToCopy();

    } catch (err) {
      console.warn('Dashboard telemetry partial sync failed:', err);
      if (syncTimeEl) {
        syncTimeEl.textContent = 'Sync retry available';
      }
    } finally {
      isSyncing = false;
      syncBtn.classList.remove('syncing');
      syncBtn.disabled = false;
    }
  }

  syncBtn.addEventListener('click', (e) => {
    e.preventDefault();
    performPartialSync();
  });
}

/**
 * 4. Click to Copy Identifier Utility (Models, Doc IDs)
 */
function initClickToCopy() {
  const codeTags = document.querySelectorAll('.table-code:not([data-copy-bound])');

  codeTags.forEach((tag) => {
    tag.setAttribute('data-copy-bound', 'true');
    tag.setAttribute('title', 'Click to copy to clipboard');
    tag.style.cursor = 'pointer';

    tag.addEventListener('click', async (e) => {
      e.stopPropagation();
      const textToCopy = tag.textContent.trim();
      if (!textToCopy) return;

      try {
        await navigator.clipboard.writeText(textToCopy);
        const originalText = tag.textContent;
        tag.textContent = 'Copied!';
        tag.classList.add('copy-success');

        setTimeout(() => {
          tag.textContent = originalText;
          tag.classList.remove('copy-success');
        }, 1200);
      } catch (err) {
        console.warn('Failed to copy text:', err);
      }
    });
  });
}

/**
 * 5. Quick Prompt Navigation for Field Engineers
 */
function initQuickPromptNavigation() {
  document.querySelectorAll('[data-prompt]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const promptText = btn.getAttribute('data-prompt');
      if (!promptText) return;

      const chatUrl = btn.getAttribute('data-chat-url') || '/assistant/chat/';
      const url = new URL(chatUrl, window.location.origin);
      url.searchParams.set('question', promptText);
      window.location.href = url.toString();
    });
  });
}

