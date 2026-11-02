/**
 * assistant_chat.js - Industrial AI Maintenance Assistant Terminal Controller
 * Features:
 * - Technical response formatting (steps, warnings, specs, units)
 * - Auto-expanding textarea & keyboard shortcuts (Enter to send, / to focus)
 * - Interactive prompt chips & quick suggestion launchers
 * - Live pipeline thinking state animation
 * - Citation hover & scroll-to-evidence cross-linking
 * - One-click clipboard answer copying
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', initAssistantChat);

  function initAssistantChat() {
    const chatScroll = document.getElementById('chatMessagesScroll');
    const chatForm = document.getElementById('chatForm');
    const textarea = document.getElementById('chatQuestionInput');
    const sendBtn = document.getElementById('chatSendBtn');
    const machineSelect = document.getElementById('machineSelector');
    const promptButtons = document.querySelectorAll('[data-prompt]');
    const rawAnswerElements = document.querySelectorAll('.ai-answer-raw');

    // 1. Format all existing raw AI answers for technician readability
    rawAnswerElements.forEach(rawEl => {
      const rawText = rawEl.value || rawEl.textContent || '';
      const formattedContainer = rawEl.nextElementSibling;
      if (formattedContainer && formattedContainer.classList.contains('tech-answer-formatted')) {
        formattedContainer.innerHTML = formatTechnicalResponse(rawText);
      }
    });

    // 2. Setup Copy Answer buttons
    setupCopyButtons();

    // 3. Setup Citation Cross-Linking with Evidence Cards
    setupCitationHover();

    // 4. Scroll to bottom of conversation
    if (chatScroll) {
      chatScroll.scrollTop = chatScroll.scrollHeight;
    }

    // 5. Auto-expanding Textarea
    if (textarea) {
      textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        const newHeight = Math.min(Math.max(textarea.scrollHeight, 44), 140);
        textarea.style.height = `${newHeight}px`;
      });

      // Submit on Enter (Shift+Enter for newline)
      textarea.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          if (textarea.value.trim() && !sendBtn?.disabled) {
            chatForm?.requestSubmit ? chatForm.requestSubmit() : chatForm?.submit();
          }
        }
      });
    }

    // 6. Global keyboard shortcut '/' to focus question box
    document.addEventListener('keydown', e => {
      if (e.key === '/' && document.activeElement !== textarea && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
        e.preventDefault();
        if (textarea && !textarea.disabled) {
          textarea.focus();
        }
      }
    });

    // 7. Interactive Prompt Chips
    promptButtons.forEach(btn => {
      btn.addEventListener('click', e => {
        e.preventDefault();
        const promptText = btn.getAttribute('data-prompt');
        if (promptText && textarea) {
          textarea.value = promptText;
          textarea.style.height = 'auto';
          const newHeight = Math.min(Math.max(textarea.scrollHeight, 44), 140);
          textarea.style.height = `${newHeight}px`;
          textarea.focus();

          // If auto-send is flagged or if prompt is clicked directly
          if (btn.hasAttribute('data-autosend') && chatForm) {
            chatForm.requestSubmit ? chatForm.requestSubmit() : chatForm.submit();
          }
        }
      });
    });

    // 8. Form Submission Feedback & Live Retrieval Animation
    if (chatForm) {
      chatForm.addEventListener('submit', () => {
        if (!textarea || !textarea.value.trim()) return;

        // Disable input & button
        if (sendBtn) {
          sendBtn.disabled = true;
          sendBtn.innerHTML = `
            <svg class="animate-spin" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="margin-right: 6px; animation: spin 1s linear infinite;">
              <circle cx="12" cy="12" r="10" stroke-opacity="0.25" stroke="currentColor"></circle>
              <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor"></path>
            </svg>
            Generating Answer...
          `;
        }

        // Append temporary live thinking indicator in chat
        if (chatScroll) {
          const thinkingBubble = document.createElement('div');
          thinkingBubble.className = 'chat-entry live-thinking-entry';
          thinkingBubble.innerHTML = `
            <div class="ai-answer-block" style="border-left: 3px solid var(--accent); background-color: var(--surface);">
              <div class="chat-avatar-icon chat-avatar-ai">AI</div>
              <div class="chat-entry-body">
                <div class="chat-entry-meta">
                  <span class="chat-speaker-name">Maintenance Assistant</span>
                  <span class="badge badge-neutral" style="font-size: 10px; font-family: var(--font-mono);">RAG Retrieval Live</span>
                </div>
                <div style="display: flex; align-items: center; gap: 10px; margin-top: 8px;">
                  <span class="spinner-icon"></span>
                  <span id="thinkingStatusText" style="font-size: 13px; color: var(--text-muted); font-weight: 500;">
                    Searching ChromaDB vector store for equipment corpus...
                  </span>
                </div>
              </div>
            </div>
          `;
          chatScroll.appendChild(thinkingBubble);
          chatScroll.scrollTop = chatScroll.scrollHeight;

          setTimeout(() => {
            const stText = document.getElementById('thinkingStatusText');
            if (stText) stText.textContent = 'Synthesizing verified answer with Gemini and grounding citations...';
            chatScroll.scrollTop = chatScroll.scrollHeight;
          }, 1800);
        }
      });
    }

    // -------------------------------------------------------------
    // Core Engine: Technical Response Formatter
    // -------------------------------------------------------------
    function formatTechnicalResponse(text) {
      if (!text) return '';

      // Normalize line breaks
      const lines = text.split('\n');
      let html = '';
      let inStepList = false;
      let inBulletList = false;
      let stepCounter = 1;

      for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();

        if (!line) {
          if (inBulletList) {
            html += '</ul>';
            inBulletList = false;
          }
          continue;
        }

        // A. Hazard / Safety / Warning Callout
        const alertMatch = line.match(/^(WARNING|DANGER|CAUTION|SAFETY|NOTE|IMPORTANT|NOTICE):\s*(.*)$/i);
        if (alertMatch) {
          if (inBulletList) { html += '</ul>'; inBulletList = false; }
          const alertType = alertMatch[1].toUpperCase();
          const alertBody = alertMatch[2] || '';

          let alertClass = 'tech-alert-warning';
          let alertIcon = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0; margin-top: 2px;">
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path>
              <line x1="12" y1="9" x2="12" y2="13"></line>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
          `;

          if (alertType === 'DANGER') {
            alertClass = 'tech-alert-danger';
            alertIcon = `
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0; margin-top: 2px;">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
            `;
          } else if (alertType === 'NOTE' || alertType === 'NOTICE' || alertType === 'IMPORTANT') {
            alertClass = 'tech-alert-note';
            alertIcon = `
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0; margin-top: 2px;">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
            `;
          }

          html += `
            <div class="tech-alert-box ${alertClass}">
              ${alertIcon}
              <div>
                <strong>${alertType}:</strong> ${highlightSpecs(parseMarkdownInline(alertBody))}
              </div>
            </div>
          `;
          continue;
        }

        // B. Section Headings (e.g. ### Heading or "Procedure:")
        const headingMatch = line.match(/^#{1,4}\s+(.*)$/) || (line.endsWith(':') && line.length < 50 && !line.match(/^\d+\./) && !line.startsWith('-'));
        if (headingMatch) {
          if (inBulletList) { html += '</ul>'; inBulletList = false; }
          const titleText = typeof headingMatch === 'object' && headingMatch[1] ? headingMatch[1] : line.replace(/:$/, '');
          html += `
            <div class="tech-heading">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
              <span>${titleText}</span>
            </div>
          `;
          continue;
        }

        // C. Numbered Operational Steps (e.g. "1. Step description" or "Step 1: ...")
        const stepMatch = line.match(/^(?:(?:Step\s*)?(\d+)[\.\)]\s*)(.*)$/i);
        if (stepMatch) {
          if (inBulletList) { html += '</ul>'; inBulletList = false; }
          const num = stepMatch[1];
          const content = stepMatch[2];
          html += `
            <div class="tech-step-item">
              <div class="tech-step-num">${num}</div>
              <div class="tech-step-content">${highlightSpecs(parseMarkdownInline(content))}</div>
            </div>
          `;
          continue;
        }

        // D. Bullet Lists (e.g. "- Item" or "* Item")
        const bulletMatch = line.match(/^[\*\-]\s+(.*)$/);
        if (bulletMatch) {
          if (!inBulletList) {
            html += '<ul class="tech-bullet-list">';
            inBulletList = true;
          }
          html += `
            <li class="tech-bullet-item">
              <span class="tech-bullet-dot"></span>
              <span>${highlightSpecs(parseMarkdownInline(bulletMatch[1]))}</span>
            </li>
          `;
          continue;
        }

        // E. Normal Paragraph
        if (inBulletList) { html += '</ul>'; inBulletList = false; }
        html += `<p style="margin: 0; line-height: 1.6;">${highlightSpecs(parseMarkdownInline(line))}</p>`;
      }

      if (inBulletList) html += '</ul>';

      return html;
    }

    // Helper: parse inline markdown (**bold**, `code`)
    function parseMarkdownInline(str) {
      if (!str) return '';
      return str
        .replace(/\*\*(.*?)\*\*/g, '<strong style="color: var(--text-main); font-weight: 600;">$1</strong>')
        .replace(/`([^`]+)`/g, '<code class="tech-code-pill">$1</code>');
    }

    // Helper: auto-highlight units, specs, torques, pressures, temperatures, and alarm codes
    function highlightSpecs(str) {
      if (!str) return '';

      // Match measurement specs: e.g. 50 Nm, 120 bar, 65°C, 24 VDC, 1500 RPM, 0.05 mm, 480 V
      const specRegex = /\b(\d+(?:\.\d+)?\s*(?:Nm|bar|psi|rpm|RPM|°C|°F|VDC|VAC|V|A|mA|mm|cm|kg|Hz|kHz|kVA|μm))\b/g;
      str = str.replace(specRegex, '<span class="tech-spec-pill">$1</span>');

      // Match alarm and error codes: e.g. ALARM-01, ERR 104, AL-302, E-405
      const alarmRegex = /\b((?:ALARM|ERR|CODE|AL|FAULT)[-\s]?[A-Z0-9]+)\b/gi;
      str = str.replace(alarmRegex, '<span class="tech-code-pill">$1</span>');

      return str;
    }

    // -------------------------------------------------------------
    // Helper: Clipboard Copy Utility for Answers
    // -------------------------------------------------------------
    function setupCopyButtons() {
      document.querySelectorAll('.btn-copy-answer').forEach(btn => {
        btn.addEventListener('click', async e => {
          e.preventDefault();
          const targetId = btn.getAttribute('data-target');
          const targetEl = document.getElementById(targetId);
          if (!targetEl) return;

          const textToCopy = targetEl.value || targetEl.innerText || '';
          try {
            await navigator.clipboard.writeText(textToCopy);
            const origHtml = btn.innerHTML;
            btn.innerHTML = `
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--status-indexed-text)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              <span style="color: var(--status-indexed-text); font-weight: 600;">Copied!</span>
            `;
            setTimeout(() => {
              btn.innerHTML = origHtml;
            }, 1800);
          } catch (err) {
            console.warn('Copy failed:', err);
          }
        });
      });
    }

    // -------------------------------------------------------------
    // Helper: Citation Hover & Evidence Highlighting
    // -------------------------------------------------------------
    function setupCitationHover() {
      const citationBadges = document.querySelectorAll('.citation-badge-interactive');
      const evidenceCards = document.querySelectorAll('.evidence-card');

      citationBadges.forEach(badge => {
        const docId = badge.getAttribute('data-doc-id');
        const pageNum = badge.getAttribute('data-page');

        badge.addEventListener('mouseenter', () => {
          evidenceCards.forEach(card => {
            const cardDoc = card.getAttribute('data-doc-id');
            const cardPage = card.getAttribute('data-page');
            if (cardDoc === docId && cardPage === pageNum) {
              card.classList.add('highlighted');
              card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
          });
        });

        badge.addEventListener('mouseleave', () => {
          evidenceCards.forEach(card => card.classList.remove('highlighted'));
        });

        badge.addEventListener('click', () => {
          evidenceCards.forEach(card => {
            const cardDoc = card.getAttribute('data-doc-id');
            const cardPage = card.getAttribute('data-page');
            if (cardDoc === docId && cardPage === pageNum) {
              card.classList.add('highlighted');
              card.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
          });
        });
      });
    }
  }
})();

