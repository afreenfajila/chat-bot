/**
 * app.js
 * Main application controller.
 * - Fetches language config from the Python backend (/languages)
 * - Manages conversation history
 * - Sends messages to the Python backend (/chat)
 * - Wires UI and Speech together
 */

// ── State ──────────────────────────────────────────────────────────────────
let languages           = {};   // populated from /languages on load
let guideConfig          = null; // populated from /services on load
let conversationHistory  = [];  // [{ role, content }, ...]
let selectedInputLang    = 'auto';
const MAX_HISTORY        = 20;

// ── Boot ───────────────────────────────────────────────────────────────────
async function init() {
  await loadLanguages();
  await loadGuideConfig();
  bindEvents();
  startWelcomeFlow();
}

// ── Load language config from backend ─────────────────────────────────────
async function loadLanguages() {
  try {
    const res = await fetch('/languages');
    languages = await res.json();
    UI.renderLangBadges(languages);
    UI.renderInputLangOptions(languages);
  } catch (e) {
    UI.setStatus('error', '✗ Could not load language config. Is the server running?');
  }
}

async function loadGuideConfig() {
  try {
    const res = await fetch('/services');
    guideConfig = await res.json();   // { ui: {...}, services: {...} }
  } catch (e) {
    guideConfig = null;               // welcome flow is skipped; chat still works
  }
}

// ── Welcome flow: language → greeting → topics → guiding questions ────────
const WELCOME_TEXT = '👋 Welcome! Please select your language · 请选择语言:';

// Spoken or typed names that select each language while the picker is open.
const LANG_ALIASES = {
  en:  ['english'],
  zh:  ['chinese', 'mandarin', '中文', '华语', 'zhongwen', 'huayu'],
  ta:  ['tamil', 'தமிழ்'],
  th:  ['thai', 'ไทย'],
  vi:  ['vietnamese', 'viet', 'tiếng việt'],
  id:  ['indonesian', 'indonesia', 'bahasa indonesia'],
  ms:  ['malay', 'melayu', 'bahasa melayu'],
  fil: ['filipino', 'tagalog'],
  my:  ['burmese', 'myanmar', 'မြန်မာ'],
};

let pendingLangPicker = null;   // the picker bubble element while a choice is pending
let welcomeAnnounced  = false;  // true once the welcome has actually been spoken

const WELCOME_SPEECH = 'Welcome! Please select your language.';

function startWelcomeFlow() {
  if (!guideConfig || !Object.keys(languages).length) return;

  const chips = Object.entries(languages).map(([code, l]) => ({
    value: code,
    label: `${l.flag} ${l.name}`,
  }));

  pendingLangPicker = UI.addGuideBubble(WELCOME_TEXT, chips, (code) => {
    pendingLangPicker = null;
    setChatLanguage(code);
    showGreeting(code);
  });

  UI.setTranscript('Tap a language above — or tap the mic and say it (e.g. "Tamil")');

  // Read the welcome aloud. Browsers block TTS until the user's first
  // interaction with the page, so this first attempt may stay silent —
  // the fallback below retries on the first gesture.
  welcomeAnnounced = false;
  speakGuide(WELCOME_SPEECH, 'en', () => { welcomeAnnounced = true; });

  document.removeEventListener('pointerdown', retryWelcomeSpeech, true);
  document.removeEventListener('keydown', retryWelcomeSpeech, true);
  document.addEventListener('pointerdown', retryWelcomeSpeech, true);
  document.addEventListener('keydown', retryWelcomeSpeech, true);
}

// First user gesture unlocks TTS: speak the welcome if it was blocked on load.
function retryWelcomeSpeech(e) {
  document.removeEventListener('pointerdown', retryWelcomeSpeech, true);
  document.removeEventListener('keydown', retryWelcomeSpeech, true);

  if (welcomeAnnounced || !pendingLangPicker) return;
  // If this gesture is already a language choice, the localized greeting
  // will be spoken instead — don't talk over it.
  if (e.target?.closest?.('.chip')) return;

  speakGuide(WELCOME_SPEECH, 'en', () => { welcomeAnnounced = true; });
}

// Speak guide text aloud, respecting the auto-speak setting.
function speakGuide(text, langCode, onSpokenStart) {
  if (!UI.getAutoSpeak()) return;
  const langInfo = languages[langCode];
  if (!langInfo) return;

  // Strip emoji/flags and chip separators so TTS reads only the words.
  const clean = text.replace(/[\p{Extended_Pictographic}\u{1F1E6}-\u{1F1FF}·]/gu, '').replace(/\s+/g, ' ').trim();
  if (!clean) return;

  Speech.speak(clean, langInfo, UI.getVoiceSpeed(), {
    onStart: () => {
      onSpokenStart?.();
      UI.setStatus('speaking', '🔊 Speaking…');
    },
    onEnd:   () => UI.setStatus('', 'ready'),
    onNoVoice: () => {},   // welcome speech is optional — fail silently
  });
}

// Match spoken/typed text (e.g. "Tamil", "中文") to a language code.
function matchLanguageFromText(text) {
  const t = text.toLowerCase().trim();
  for (const [code, info] of Object.entries(languages)) {
    if (t.includes(info.name.toLowerCase())) return code;
  }
  for (const [code, aliases] of Object.entries(LANG_ALIASES)) {
    if (aliases.some((a) => t.includes(a))) return code;
  }
  return null;
}

function setChatLanguage(code) {
  selectedInputLang = code;
  const select = document.getElementById('input-lang-select');
  if (select) select.value = code;
}

// Localized string with English fallback
function uiText(lang, key) {
  const ui = guideConfig.ui;
  return (ui[lang] && ui[lang][key]) || ui.en[key];
}

function showGreeting(lang) {
  const topicChips = Object.entries(guideConfig.services).map(([key, svc]) => ({
    value: key,
    label: `${svc.icon} ${svc.name[lang] || svc.name.en}`,
  }));

  const text = `${uiText(lang, 'greeting')}\n\n${uiText(lang, 'choose_topic')}`;
  UI.addGuideBubble(text, topicChips, (topicKey) => {
    showGuidingQuestions(lang, topicKey);
  });

  // Read the localized greeting aloud (triggered by a user gesture, so TTS
  // is allowed even in browsers that block speech before interaction).
  speakGuide(text, lang);
}

function showGuidingQuestions(lang, topicKey) {
  const svc = guideConfig.services[topicKey];
  const questions = svc.questions[lang] || svc.questions.en;

  const chips = questions.map((q) => ({ value: q, label: q }));
  UI.addGuideBubble(uiText(lang, 'questions_intro'), chips, (question) => {
    handleUserMessage(question);
  });
}

// ── New chat: reset history and restart the welcome flow ──────────────────
function startNewChat() {
  if (Speech.getIsSpeaking()) Speech.stopSpeaking();
  conversationHistory = [];
  UI.clearChat();
  UI.setTranscript('Tap the mic to start speaking…');
  UI.setStatus('', 'ready');
  startWelcomeFlow();
}

// ── Event Binding ──────────────────────────────────────────────────────────
function bindEvents() {
  document.getElementById('mic-btn')
    .addEventListener('click', toggleMic);

  document.getElementById('send-btn')
    .addEventListener('click', sendTextMessage);

  document.getElementById('new-chat-btn')
    ?.addEventListener('click', startNewChat);

  document.getElementById('input-lang-select')
    .addEventListener('change', (e) => {
      selectedInputLang = e.target.value;
    });

  document.getElementById('text-input')
    .addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendTextMessage();
      }
    });
}

// ── Mic Toggle ─────────────────────────────────────────────────────────────
function toggleMic() {
  if (Speech.getIsSpeaking()) {
    Speech.stopSpeaking();
  }

  if (Speech.getIsRecording()) {
    Speech.stopRecognition();
    UI.setMicRecording(false);
    UI.setTranscript('Tap the mic to start speaking…');
    UI.setStatus('', 'ready');
  } else {
    startListening();
  }
}

function startListening() {
  if (!Speech.isSTTSupported()) {
    UI.setStatus('error', '✗ Voice input not supported — please use Chrome or Edge.');
    return;
  }

  Speech.startRecognition({
    lang: selectedInputLang !== 'auto' && languages[selectedInputLang]
      ? languages[selectedInputLang].bcp47
      : '',
    onStart: () => {
      UI.setMicRecording(true);
      UI.setTranscript('🔴 Listening — speak now…', 'listening');
      UI.setStatus('', '🎤 Recording');
    },
    onInterim: (text) => {
      UI.setTranscript(text, 'active');
    },
    onFinal: (text) => {
      UI.setMicRecording(false);
      UI.setTranscript(text, 'active');
      handleUserMessage(text);
    },
    onError: (message) => {
      UI.setMicRecording(false);
      UI.setTranscript('Tap the mic to start speaking…');
      UI.setStatus('error', `✗ ${message}`);
    },
    onEnd: () => {
      UI.setMicRecording(false);
    },
  });
}

// ── Text Input ─────────────────────────────────────────────────────────────
function sendTextMessage() {
  const text = UI.getTextInputValue();
  if (!text) return;
  UI.clearTextInput();
  handleUserMessage(text);
}

// ── Core Message Flow ──────────────────────────────────────────────────────
async function handleUserMessage(text) {
  if (!text.trim()) return;

  // While the language picker is open, spoken or typed input picks the
  // language ("Tamil", "中文", …) instead of being sent to the model.
  if (pendingLangPicker) {
    const code = matchLanguageFromText(text);
    if (code) {
      const chip = pendingLangPicker.querySelector(`.chip[data-value="${code}"]`);
      UI.setTranscript('Tap the mic to start speaking…');
      if (chip) { chip.click(); return; }
    }
    // Not a language name — treat it as a real question and dismiss the picker.
    pendingLangPicker.querySelector('.chip-row')?.classList.add('chips-done');
    pendingLangPicker = null;
  }

  selectedInputLang = UI.getTextInputLang();
  const effectiveInputLang = selectedInputLang !== 'auto' && languages[selectedInputLang]
    ? selectedInputLang
    : guessLangCodeFromText(text);

  // Add user message to history and show bubble
  conversationHistory.push({ role: 'user', content: text });
  const userLangInfo = languages[effectiveInputLang] || guessLangInfoFromText(text);
  const userBubbleEl = UI.addBubble('user', text, userLangInfo);

  UI.setInputsDisabled(true);
  UI.setStatus('thinking', '⟳ Thinking…');

  try {
    // Send full conversation history to Python backend
    const res = await fetch('/chat', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ messages: conversationHistory, inputLang: effectiveInputLang }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Server error ${res.status}`);
    }

    const data = await res.json();
    // data = { reply, lang, langInfo }

    conversationHistory.push({ role: 'assistant', content: data.reply });

    // Trim history to avoid growing token cost indefinitely
    if (conversationHistory.length > MAX_HISTORY) {
      conversationHistory = conversationHistory.slice(-MAX_HISTORY);
    }

    const msgEl = UI.addBubble('ai', data.reply, data.langInfo, (playBtn) => {
      handlePlayButton(data.reply, data.langInfo, playBtn);
    }, data.sources);

    UI.setTranscript('Tap the mic to speak again…');
    UI.setStatus('', 'ready');

    if (UI.getAutoSpeak()) {
      const playBtn = msgEl.querySelector('.play-btn');
      speakReply(data.reply, data.langInfo, playBtn);
    }

  } catch (error) {
    // Remove failed user message from history
    conversationHistory.pop();
    UI.setStatus('error', `✗ ${error.message}`);
    UI.setTranscript('Something went wrong. Check the terminal for details.');
  }

  UI.setInputsDisabled(false);
}

// ── TTS ────────────────────────────────────────────────────────────────────
function speakReply(text, langInfo, playBtn) {
  Speech.speak(text, langInfo, UI.getVoiceSpeed(), {
    onStart: () => {
      UI.setStatus('speaking', '🔊 Speaking…');
      UI.setPlayBtnState(playBtn, true);
    },
    onEnd: () => {
      UI.setStatus('', 'ready');
      UI.setPlayBtnState(playBtn, false);
    },
    onNoVoice: (msg) => {
      UI.setStatus('error', `✗ ${msg}`);
      UI.setPlayBtnState(playBtn, false);
    },
  });
}

function handlePlayButton(text, langInfo, playBtn) {
  if (Speech.getIsSpeaking()) {
    Speech.stopSpeaking();
    UI.setPlayBtnState(playBtn, false);
    UI.setStatus('', 'ready');
  } else {
    speakReply(text, langInfo, playBtn);
  }
}

// ── Utility: best-guess lang info before server responds ───────────────────
// Used only for showing the user bubble immediately (before /chat returns).
function guessLangCodeFromText(text) {
  if (/[\u0B80-\u0BFF]/.test(text) ||
      /\b(vanakkam|eppadi|epdi|irukinga|irukeenga|irukku|iruku|nandri|enna|yenna|seri|sollunga|venum|vendam|panna|pannunga|ungalukku|unakku|enakku|romba|konjam)\b/i.test(text))
    return 'ta';

  if (/[\u0E00-\u0E7F]/.test(text))
    return 'th';

  if (/[\u1000-\u109F]/.test(text))
    return 'my';

  if (/[一-鿿㐀-䶿豈-﫿]/.test(text))
    return 'zh';

  if (/[ăâđêôơưẠ-ỹ]/i.test(text) ||
      /\b(và|của|là|có|không|tôi|bạn|anh|chị|em|này|được|cho|với|xin|chào|cảm|ơn|nhé|rồi|vâng|gì|sao)\b/i.test(text))
    return 'vi';

  if (/\b(ang|ng|mga|ako|ikaw|siya|kami|tayo|hindi|opo|po|salamat|kumusta|magandang|umaga|gabi|paano|ano|dito|naman|natin)\b/i.test(text))
    return 'fil';

  if (/\b(tak|nak|awak|korang|khabar|macam|boleh|kat|cakap|pukul|kenapa|mana|sini|tolong)\b/i.test(text))
    return 'ms';

  if (/\b(tidak|bisa|aku|kamu|kalian|anda|sudah|belum|sedang|gimana|banget|sekarang|kabar|bagaimana|apakah|selamat|pagi|malam)\b/i.test(text))
    return 'id';

  return 'en';
}

function guessLangInfoFromText(text) {
  // Mirrors server-side detection: special chars first, then common words.
  if (selectedInputLang !== 'auto' && languages[selectedInputLang]) {
    return languages[selectedInputLang];
  }

  const code = guessLangCodeFromText(text);
  return languages[code] || fallbackLang();
}

function fallbackLang() {
  return { flag: '🌐', label: '??' };
}

// ── Start ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
