/**
 * ui.js
 * All DOM updates: chat bubbles, status bar, transcript box, inputs.
 * No API or speech logic here — pure UI layer.
 */

const UI = (() => {

  // ── Element helpers ────────────────────────────────────────────────────
  const el = (id) => document.getElementById(id);

  // ── Language badges (populated from /languages on load) ───────────────
  function renderLangBadges(languages) {
    const container  = el('lang-badges');
    const hint       = el('empty-hint');
    const namesList  = Object.values(languages).map(l => `<strong>${l.flag} ${l.name}</strong>`).join(', ');

    container.innerHTML = Object.values(languages)
      .map(l => `<span class="badge">${l.flag} ${l.name}</span>`)
      .join('');

    if (hint) {
      hint.innerHTML = `Press the mic or type in<br>${namesList}<br>— the AI replies in the same language.`;
    }
  }

  // ── Status Bar ─────────────────────────────────────────────────────────
  function setStatus(type, message) {
    const s = el('status-bar');
    s.className   = type;   // '' | 'thinking' | 'speaking' | 'error'
    s.textContent = message;
  }

  // ── Transcript Box ─────────────────────────────────────────────────────
  function setTranscript(text, state = '') {
    const t = el('transcript-box');
    t.textContent = text;
    t.className   = state;  // '' | 'active' | 'listening'
  }

  // ── Mic Button ─────────────────────────────────────────────────────────
  function setMicRecording(isRecording) {
    const btn = el('mic-btn');
    btn.classList.toggle('recording', isRecording);
    btn.textContent = isRecording ? '⏹️' : '🎤';
  }

  // ── Inputs ─────────────────────────────────────────────────────────────
  function setInputsDisabled(disabled) {
    el('mic-btn').disabled   = disabled;
    el('send-btn').disabled  = disabled;
    el('text-input').disabled = disabled;
    // Guide chips (welcome flow / guiding questions) also send messages,
    // so they must be blocked while a reply is pending too.
    document.querySelectorAll('.chip').forEach((c) => { c.disabled = disabled; });
  }

  // ── Stop-voice button (next to the status bar) ─────────────────────────
  function setStopVoiceVisible(visible) {
    el('stop-voice-btn').hidden = !visible;
  }

  function getTextInputValue()  { return el('text-input').value.trim(); }
  function clearTextInput()     { el('text-input').value = ''; }

  // ── Settings ───────────────────────────────────────────────────────────
  function renderInputLangOptions(languages) {
    const select = el('input-lang-select');
    if (!select) return;

    select.innerHTML = [
      '<option value="auto">Auto detect</option>',
      ...Object.entries(languages).map(([code, lang]) =>
        `<option value="${code}">${lang.flag} ${lang.name}</option>`
      ),
    ].join('');
  }

  function getTextInputLang() { return el('input-lang-select')?.value || 'auto'; }
  function getVoiceSpeed() { return parseFloat(el('speed-select').value); }
  function getAutoSpeak()  { return el('autospeak-select').value === 'yes'; }

  // ── Chat Bubbles ───────────────────────────────────────────────────────
  /**
   * Add a message bubble to the chat window.
   * @param {'user'|'ai'} role
   * @param {string}      text
   * @param {object}      langInfo    — { flag, label, ... } from /languages
   * @param {Function}    [onPlay]    — callback for play button (AI only)
   * @param {string}      [translation] — English translation shown below bubble
   * @returns {HTMLElement}
   */
  function addBubble(role, text, langInfo, onPlay, source) {
    // Remove empty state on first message
    el('empty-state')?.remove();

    const win = el('chat-window');

    const div = document.createElement('div');
    div.className = `msg ${role}`;

    const bubble = document.createElement('div');
    bubble.className   = 'bubble';
    bubble.textContent = text;

    const meta = document.createElement('div');
    meta.className = 'msg-meta';

    const tag = document.createElement('span');
    tag.className   = 'lang-tag';
    tag.textContent = `${langInfo.flag} ${langInfo.label}`;
    meta.appendChild(tag);

    if (role === 'ai' && typeof onPlay === 'function') {
      const pb = document.createElement('button');
      pb.className   = 'play-btn';
      pb.textContent = '▶ play';
      pb.addEventListener('click', () => onPlay(pb));
      meta.appendChild(pb);
    }

    div.appendChild(bubble);

    if (source && source.length) {
      const src = document.createElement('div');
      src.className = 'source';
      const urls = Array.isArray(source) ? source : [source];
      src.append('📎 ');
      urls.forEach((url, i) => {
        if (i > 0) src.append(' · ');
        const a = document.createElement('a');
        a.href   = url;
        a.target = '_blank';
        a.rel    = 'noopener';
        // Show the last URL path segment as a readable label
        try {
          a.textContent = decodeURIComponent(
            new URL(url).pathname.split('/').filter(Boolean).pop() || url
          ).replace(/[-_]/g, ' ');
        } catch {
          a.textContent = url;
        }
        src.appendChild(a);
      });
      div.appendChild(src);
    }

    div.appendChild(meta);
    win.appendChild(div);
    win.scrollTop = win.scrollHeight;

    return div;
  }

  function setPlayBtnState(pb, isPlaying) {
    if (pb) pb.textContent = isPlaying ? '⏸ stop' : '▶ play';
  }

  // ── Guide bubbles (welcome flow) ───────────────────────────────────────
  /**
   * Add an AI-styled bubble with tappable option chips below the text.
   * Used for the welcome flow: language picker, service topics, and
   * guiding questions. Not part of the conversation history.
   * @param {string} text                       — bubble text
   * @param {Array<{value:string,label:string}>} chips
   * @param {Function} onSelect(value, chipEl)  — called on chip click
   * @returns {HTMLElement} the .msg element
   */
  function addGuideBubble(text, chips, onSelect) {
    el('empty-state')?.remove();

    const win = el('chat-window');

    const div = document.createElement('div');
    div.className = 'msg ai guide';

    const bubble = document.createElement('div');
    bubble.className   = 'bubble';
    bubble.textContent = text;
    div.appendChild(bubble);

    const row = document.createElement('div');
    row.className = 'chip-row';
    chips.forEach(({ value, label }) => {
      const chip = document.createElement('button');
      chip.className     = 'chip';
      chip.textContent   = label;
      chip.dataset.value = value;
      chip.addEventListener('click', () => {
        if (row.classList.contains('chips-done')) return;
        row.classList.add('chips-done');
        chip.classList.add('chip-selected');
        onSelect(value, chip);
      });
      row.appendChild(chip);
    });
    div.appendChild(row);

    win.appendChild(div);
    win.scrollTop = win.scrollHeight;
    return div;
  }

  function clearChat() {
    el('chat-window').innerHTML = '';
  }

  return {
    renderLangBadges,
    renderInputLangOptions,
    setStatus,
    setTranscript,
    setMicRecording,
    setInputsDisabled,
    setStopVoiceVisible,
    getTextInputValue,
    getTextInputLang,
    clearTextInput,
    getVoiceSpeed,
    getAutoSpeak,
    addBubble,
    setPlayBtnState,
    addGuideBubble,
    clearChat,
  };

})();
