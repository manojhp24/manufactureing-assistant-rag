/**
 * manual_list.js - Technical Manual Registry Interactive Controls
 * Instant search, status filtering, and copy utilities
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', initManualList);

  function initManualList() {
    const searchInput = document.getElementById('manualSearchInput');
    const tableBody = document.getElementById('manualTableBody');
    const statusPills = document.querySelectorAll('.filter-pill-btn[data-status]');
    const copyCodes = document.querySelectorAll('.copyable-code');

    let currentStatus = 'all';
    let searchQuery = '';

    // Keyboard shortcut: '/' to focus search
    document.addEventListener('keydown', e => {
      if (e.key === '/' && document.activeElement !== searchInput && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
        e.preventDefault();
        if (searchInput) {
          searchInput.focus();
          searchInput.select();
        }
      }
    });

    if (searchInput) {
      searchInput.addEventListener('input', e => {
        searchQuery = e.target.value.toLowerCase().trim();
        filterTableRows();
      });
    }

    statusPills.forEach(pill => {
      pill.addEventListener('click', e => {
        e.preventDefault();
        statusPills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        currentStatus = pill.getAttribute('data-status') || 'all';
        filterTableRows();
      });
    });

    function filterTableRows() {
      if (!tableBody) return;
      const rows = tableBody.querySelectorAll('tr[data-status]');
      let visibleCount = 0;

      rows.forEach(row => {
        const rowStatus = row.getAttribute('data-status') || '';
        const rowText = row.textContent.toLowerCase();

        const matchesStatus = currentStatus === 'all' || rowStatus === currentStatus;
        const matchesQuery = !searchQuery || rowText.includes(searchQuery);

        if (matchesStatus && matchesQuery) {
          row.style.display = '';
          visibleCount++;
        } else {
          row.style.display = 'none';
        }
      });

      // Handle empty filter message
      let emptyMsg = document.getElementById('filterEmptyRow');
      if (visibleCount === 0 && rows.length > 0) {
        if (!emptyMsg) {
          emptyMsg = document.createElement('tr');
          emptyMsg.id = 'filterEmptyRow';
          emptyMsg.className = 'table-empty-row';
          emptyMsg.innerHTML = `
            <td colspan="9" style="text-align: center; padding: var(--space-6); color: var(--text-muted);">
              No manuals found matching criteria "${searchQuery || currentStatus}".
              <button type="button" class="btn btn-ghost btn-sm" id="resetFilterBtn" style="color: var(--accent); margin-left: 8px;">
                Reset Filters
              </button>
            </td>
          `;
          tableBody.appendChild(emptyMsg);
          document.getElementById('resetFilterBtn')?.addEventListener('click', resetFilters);
        } else {
          emptyMsg.style.display = '';
        }
      } else if (emptyMsg) {
        emptyMsg.style.display = 'none';
      }
    }

    function resetFilters() {
      if (searchInput) searchInput.value = '';
      searchQuery = '';
      currentStatus = 'all';
      statusPills.forEach(p => {
        if (p.getAttribute('data-status') === 'all') {
          p.classList.add('active');
        } else {
          p.classList.remove('active');
        }
      });
      filterTableRows();
    }

    // Click-to-copy functionality for Doc IDs
    copyCodes.forEach(el => {
      el.style.cursor = 'pointer';
      el.setAttribute('title', 'Click to copy document code');

      el.addEventListener('click', async () => {
        const textToCopy = el.textContent.trim();
        try {
          await navigator.clipboard.writeText(textToCopy);
          const originalText = el.textContent;
          el.textContent = 'Copied!';
          el.style.color = 'var(--status-indexed-text)';
          setTimeout(() => {
            el.textContent = originalText;
            el.style.color = '';
          }, 1400);
        } catch (err) {
          console.warn('Clipboard write failed:', err);
        }
      });
    });
  }
})();
