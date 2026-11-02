/**
 * manual_upload.js - Technical PDF Manual Ingestion & RAG Indexing Controller
 * MMA Industrial AI Maintenance Assistant
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', initManualUpload);

  function initManualUpload() {
    const form = document.getElementById('manualUploadForm');
    const dropzone = document.getElementById('manualDropzone');
    const fileInput = document.getElementById('id_pdf_file');
    const previewStrip = document.getElementById('pdfPreviewStrip');
    const fileNameEl = document.getElementById('previewFileName');
    const fileSizeEl = document.getElementById('previewFileSize');
    const removeBtn = document.getElementById('removeFileBtn');
    const submitBtn = document.getElementById('uploadSubmitBtn');
    const progressContainer = document.getElementById('uploadProgressContainer');
    const progressFill = document.getElementById('uploadProgressFill');
    const progressStatusText = document.getElementById('progressStatusText');

    // Form inputs for live preview
    const machineSelect = document.getElementById('id_machine');
    const docIdInput = document.getElementById('id_document_id');
    const revisionInput = document.getElementById('id_revision');
    const titleInput = document.getElementById('id_title');

    // Live preview elements
    const liveDocTitle = document.getElementById('liveDocTitle');
    const liveDocId = document.getElementById('liveDocId');
    const liveRevision = document.getElementById('liveRevision');
    const liveMachineTag = document.getElementById('liveMachineTag');
    const liveFileTag = document.getElementById('liveFileTag');
    const livePartition = document.getElementById('livePartition');

    // Setup Drag and Drop
    if (dropzone && fileInput) {
      ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, e => {
          e.preventDefault();
          e.stopPropagation();
          dropzone.classList.add('dragover');
        });
      });

      ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, e => {
          e.preventDefault();
          e.stopPropagation();
          dropzone.classList.remove('dragover');
        });
      });

      dropzone.addEventListener('drop', e => {
        const dt = e.dataTransfer;
        if (dt && dt.files && dt.files.length > 0) {
          fileInput.files = dt.files;
          handleFileSelection(dt.files[0]);
        }
      });

      dropzone.addEventListener('click', e => {
        if (e.target !== removeBtn && !removeBtn?.contains(e.target)) {
          fileInput.click();
        }
      });
    }

    if (fileInput) {
      fileInput.addEventListener('change', () => {
        if (fileInput.files && fileInput.files.length > 0) {
          handleFileSelection(fileInput.files[0]);
        }
      });
    }

    if (removeBtn) {
      removeBtn.addEventListener('click', e => {
        e.stopPropagation();
        resetFileInput();
      });
    }

    // Input Listeners for Live Reactive Preview & Auto-Formatting
    if (machineSelect) {
      machineSelect.addEventListener('change', updateLivePreview);
    }

    if (docIdInput) {
      docIdInput.addEventListener('input', () => {
        docIdInput.value = docIdInput.value.toUpperCase();
        updateLivePreview();
      });
    }

    if (revisionInput) {
      revisionInput.addEventListener('input', () => {
        revisionInput.value = revisionInput.value.toUpperCase();
        updateLivePreview();
      });
    }

    if (titleInput) {
      titleInput.addEventListener('input', updateLivePreview);
    }

    // Form Submission State & Progress Animation
    if (form) {
      form.addEventListener('submit', handleFormSubmit);
    }

    // Initialize initial state
    updateLivePreview();

    // -------------------------------------------------------------
    // Helper Functions
    // -------------------------------------------------------------

    function handleFileSelection(file) {
      if (!file) return;

      // Validate PDF extension
      const isPdf = file.name.toLowerCase().endsWith('.pdf') || file.type === 'application/pdf';
      if (!isPdf) {
        showFileError('Invalid file format. Only technical PDF manuals are supported.');
        resetFileInput();
        return;
      }

      // Validate 20 MB size limit
      const maxBytes = 20 * 1024 * 1024;
      if (file.size > maxBytes) {
        showFileError('File size exceeds the 20 MB operational threshold. Please select a compressed PDF.');
        resetFileInput();
        return;
      }

      clearFileError();

      // Format size
      const formattedSize = formatBytes(file.size);
      if (fileNameEl) fileNameEl.textContent = file.name;
      if (fileSizeEl) fileSizeEl.textContent = formattedSize;

      // Display preview strip, hide dropzone prompt interior
      if (previewStrip) previewStrip.style.display = 'flex';
      if (dropzone) dropzone.classList.add('has-file');

      // Smart Auto-Fill: Title and Document ID if currently blank
      smartAutoFill(file.name);

      updateLivePreview();
    }

    function smartAutoFill(fileName) {
      const baseName = fileName.replace(/\.[^/.]+$/, ''); // Remove extension

      // Auto-fill Title if empty
      if (titleInput && (!titleInput.value || titleInput.value.trim() === '')) {
        const cleanTitle = baseName
          .replace(/[-_]+/g, ' ')
          .replace(/\s+/g, ' ')
          .trim();
        titleInput.value = cleanTitle;
      }

      // Auto-fill Doc ID if empty
      if (docIdInput && (!docIdInput.value || docIdInput.value.trim() === '')) {
        let suggestedId = 'DOC-' + baseName
          .toUpperCase()
          .replace(/[^A-Z0-9]/g, '-')
          .replace(/-+/g, '-')
          .replace(/^-|-$/g, '');
        if (suggestedId.length > 30) suggestedId = suggestedId.slice(0, 30);
        docIdInput.value = suggestedId;
      }
    }

    function resetFileInput() {
      if (fileInput) fileInput.value = '';
      if (previewStrip) previewStrip.style.display = 'none';
      if (dropzone) dropzone.classList.remove('has-file');
      if (liveFileTag) liveFileTag.textContent = 'No PDF selected';
      updateLivePreview();
    }

    function updateLivePreview() {
      // Document Title
      if (liveDocTitle) {
        const titleVal = titleInput ? titleInput.value.trim() : '';
        liveDocTitle.textContent = titleVal || 'Service & Maintenance Manual Title';
      }

      // Doc ID
      if (liveDocId) {
        const idVal = docIdInput ? docIdInput.value.trim() : '';
        liveDocId.textContent = idVal || 'MAN-SPEC-001';
      }

      // Revision
      if (liveRevision) {
        const revVal = revisionInput ? revisionInput.value.trim() : '';
        liveRevision.textContent = revVal ? `Rev ${revVal}` : 'Rev 1.0';
      }

      // Target Machine
      if (liveMachineTag) {
        let machineText = 'Unassigned Fleet';
        if (machineSelect && machineSelect.selectedIndex > 0) {
          machineText = machineSelect.options[machineSelect.selectedIndex].text;
        }
        liveMachineTag.textContent = machineText;
      }

      // File tag
      if (liveFileTag) {
        if (fileInput && fileInput.files && fileInput.files[0]) {
          const file = fileInput.files[0];
          liveFileTag.textContent = `${file.name} (${formatBytes(file.size)})`;
        } else {
          liveFileTag.textContent = 'Awaiting PDF source upload...';
        }
      }

      // ChromaDB Partition Key
      if (livePartition) {
        let machineCode = 'MODEL';
        if (machineSelect && machineSelect.selectedIndex > 0) {
          const optText = machineSelect.options[machineSelect.selectedIndex].text;
          const match = optText.match(/\(([^)]+)\)/);
          if (match && match[1]) {
            machineCode = match[1];
          }
        }
        livePartition.textContent = `metadata.machine_id == "${machineCode}"`;
      }
    }

    function handleFormSubmit(e) {
      // Check if file is selected
      if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        e.preventDefault();
        showFileError('Please select a PDF document before submitting.');
        return;
      }

      if (!form.checkValidity()) {
        return; // Allow native validation tooltips
      }

      // Initiate Ingestion Feedback State
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `
          <svg class="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="margin-right: 8px; animation: spin 1s linear infinite;">
            <circle cx="12" cy="12" r="10" stroke-opacity="0.25" stroke="currentColor"></circle>
            <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor"></path>
          </svg>
          Ingesting &amp; Vectorizing...
        `;
      }

      // Display Progress Bar
      if (progressContainer) {
        progressContainer.style.display = 'block';
      }

      // Multi-stage progress simulation while server performs PyPDF extraction & Gemini embeddings
      let progress = 10;
      const stages = [
        { pct: 25, label: 'Stage 1/4: Extracting text & layout tables from PDF...' },
        { pct: 55, label: 'Stage 2/4: Chunking content & building semantic overlap windows...' },
        { pct: 80, label: 'Stage 3/4: Generating 1024-dim Gemini vector embeddings...' },
        { pct: 95, label: 'Stage 4/4: Committing vectors to ChromaDB isolated collection...' }
      ];

      let stageIdx = 0;
      const interval = setInterval(() => {
        if (stageIdx < stages.length) {
          progress = stages[stageIdx].pct;
          if (progressFill) progressFill.style.width = `${progress}%`;
          if (progressStatusText) progressStatusText.textContent = stages[stageIdx].label;
          stageIdx++;
        } else {
          clearInterval(interval);
        }
      }, 900);
    }

    function showFileError(msg) {
      let errEl = document.getElementById('fileUploadErrorMsg');
      if (!errEl) {
        errEl = document.createElement('div');
        errEl.id = 'fileUploadErrorMsg';
        errEl.className = 'form-error-msg';
        errEl.style.color = 'var(--status-danger-text)';
        errEl.style.fontSize = '12px';
        errEl.style.marginTop = '6px';
        if (dropzone && dropzone.parentNode) {
          dropzone.parentNode.appendChild(errEl);
        }
      }
      errEl.textContent = msg;
      errEl.style.display = 'block';
    }

    function clearFileError() {
      const errEl = document.getElementById('fileUploadErrorMsg');
      if (errEl) errEl.style.display = 'none';
    }

    function formatBytes(bytes, decimals = 2) {
      if (!bytes || bytes === 0) return '0 Bytes';
      const k = 1024;
      const dm = decimals < 0 ? 0 : decimals;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
  }
})();

