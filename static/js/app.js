/**
 * Manufacturing Manual Assistant - Frontend UI Interaction Logic
 * Lightweight, zero-dependency vanilla JS for UI behaviors only:
 * - Responsive sidebar drawer toggle & backdrop
 * - User dropdown & action menus
 * - Password visibility toggle
 * - File upload drag-and-drop preview & progress indicator
 * - Assistant chat scroll & dynamic UI feedback
 * - Alert dismissal
 */

document.addEventListener('DOMContentLoaded', () => {
  initSidebar();
  initDropdowns();
  initPasswordToggles();
  initFileUploads();
  initChatUI();
  initAlertDismissal();
});

/**
 * 1. Mobile & Tablet Sidebar Drawer Toggle
 */
function initSidebar() {
  const sidebar = document.getElementById('appSidebar');
  const toggleBtn = document.getElementById('sidebarToggleBtn');
  const backdrop = document.getElementById('sidebarBackdrop');

  if (!sidebar || !toggleBtn) return;

  function openSidebar() {
    sidebar.classList.add('open');
    if (backdrop) backdrop.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    if (backdrop) backdrop.classList.remove('show');
    document.body.style.overflow = '';
  }

  toggleBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    if (sidebar.classList.contains('open')) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });

  if (backdrop) {
    backdrop.addEventListener('click', closeSidebar);
  }

  // Close drawer on ESC key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && sidebar.classList.contains('open')) {
      closeSidebar();
    }
  });
}

/**
 * 2. User Profile and Context Menus
 */
function initDropdowns() {
  const dropdownWrappers = document.querySelectorAll('.user-menu-wrapper, .dropdown-wrapper');

  dropdownWrappers.forEach((wrapper) => {
    const trigger = wrapper.querySelector('.dropdown-trigger, .user-profile-btn');
    const menu = wrapper.querySelector('.user-dropdown-menu, .dropdown-menu');

    if (!trigger || !menu) return;

    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = menu.classList.contains('show');
      closeAllDropdowns();
      if (!isOpen) {
        menu.classList.add('show');
      }
    });
  });

  // Close dropdowns on outside click
  document.addEventListener('click', () => {
    closeAllDropdowns();
  });

  function closeAllDropdowns() {
    document.querySelectorAll('.user-dropdown-menu.show, .dropdown-menu.show').forEach((menu) => {
      menu.classList.remove('show');
    });
  }
}

/**
 * 3. Password Show/Hide Toggle
 */
function initPasswordToggles() {
  const toggleButtons = document.querySelectorAll('[data-toggle="password"]');

  toggleButtons.forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = btn.getAttribute('data-target');
      const input = document.getElementById(targetId) || btn.previousElementSibling;

      if (!input || input.tagName !== 'INPUT') return;

      const isPassword = input.getAttribute('type') === 'password';
      input.setAttribute('type', isPassword ? 'text' : 'password');

      // Update button icon / state
      const eyeIcon = btn.querySelector('.icon-eye');
      const eyeOffIcon = btn.querySelector('.icon-eye-off');
      if (eyeIcon && eyeOffIcon) {
        eyeIcon.style.display = isPassword ? 'none' : 'block';
        eyeOffIcon.style.display = isPassword ? 'block' : 'none';
      }
    });
  });
}

/**
 * 4. File Upload Drag-and-Drop & Preview Presentation
 */
function initFileUploads() {
  const dropzones = document.querySelectorAll('.upload-dropzone');

  dropzones.forEach((dropzone) => {
    const fileInput = dropzone.querySelector('input[type="file"]') || document.getElementById(dropzone.getAttribute('data-input-id'));
    const previewStrip = document.getElementById(dropzone.getAttribute('data-preview-id'));
    const fileNameEl = previewStrip ? previewStrip.querySelector('.file-name-text') : null;
    const fileSizeEl = previewStrip ? previewStrip.querySelector('.file-size-tag') : null;
    const removeBtn = previewStrip ? previewStrip.querySelector('.file-remove-btn') : null;

    if (!fileInput) return;

    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      if (e.dataTransfer && e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        updatePreview(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files.length > 0) {
        updatePreview(fileInput.files[0]);
      }
    });

    function updatePreview(file) {
      if (!previewStrip || !file) return;

      if (fileNameEl) fileNameEl.textContent = file.name;
      if (fileSizeEl) {
        const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
        fileSizeEl.textContent = `${sizeMb} MB`;
      }

      previewStrip.style.display = 'flex';
      dropzone.style.display = 'none';
    }

    if (removeBtn) {
      removeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        fileInput.value = '';
        if (previewStrip) previewStrip.style.display = 'none';
        dropzone.style.display = 'flex';
      });
    }
  });

  // Upload Form Submission presentation (Simulate upload progress indication)
  const uploadForms = document.querySelectorAll('form.upload-form');
  uploadForms.forEach(form => {
    form.addEventListener('submit', () => {
      const progressBar = form.querySelector('.progress-bar-container');
      const progressFill = form.querySelector('.progress-bar-fill');
      const submitBtn = form.querySelector('button[type="submit"]');

      if (progressBar && progressFill) {
        progressBar.style.display = 'block';
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Uploading & Indexing...';
        }

        let width = 10;
        const interval = setInterval(() => {
          if (width >= 90) {
            clearInterval(interval);
          } else {
            width += 15;
            progressFill.style.width = width + '%';
          }
        }, 200);
      }
    });
  });
}

/**
 * 5. Assistant Chat Interface UI Enhancements
 */
function initChatUI() {
  const chatScroll = document.getElementById('chatMessagesScroll');
  const chatInput = document.getElementById('chatQuestionInput');
  const chatForm = document.getElementById('chatForm');
  const loadingIndicator = document.getElementById('chatLoadingSpinner');

  if (chatScroll) {
    // Scroll to bottom on initial load
    chatScroll.scrollTop = chatScroll.scrollHeight;
  }

  if (chatInput) {
    // Auto resize textarea height
    chatInput.addEventListener('input', () => {
      chatInput.style.height = 'auto';
      chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
    });

    // Enter to submit (Shift+Enter for newline)
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (chatForm && chatInput.value.trim().length > 0) {
          if (loadingIndicator) loadingIndicator.style.display = 'flex';
          chatForm.submit();
        }
      }
    });
  }

  // Quick prompt buttons (if present)
  document.querySelectorAll('[data-prompt]').forEach(btn => {
    btn.addEventListener('click', () => {
      const prompt = btn.getAttribute('data-prompt');
      if (chatInput) {
        chatInput.value = prompt;
        chatInput.focus();
        chatInput.dispatchEvent(new Event('input'));
      }
    });
  });
}

/**
 * 6. Alert Dismissal
 */
function initAlertDismissal() {
  document.querySelectorAll('.alert-close').forEach(btn => {
    btn.addEventListener('click', () => {
      const alert = btn.closest('.alert');
      if (alert) {
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-4px)';
        alert.style.transition = 'all 0.2s ease';
        setTimeout(() => alert.remove(), 200);
      }
    });
  });
}

