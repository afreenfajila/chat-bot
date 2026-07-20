/**
 * speech.js
 * Wraps the Web Speech API.
 *  - Speech-to-Text  via SpeechRecognition  (mic input, free, browser-native)
 *  - Text-to-Speech  via SpeechSynthesis     (voice output, free, browser-native)
 */

const Speech = (() => {

  let recognition = null;
  let isRecording = false;
  let isSpeaking  = false;

  const synth = window.speechSynthesis;

  // Voices load asynchronously on Chrome — return a Promise that resolves once ready.
  function getVoices() {
    return new Promise(resolve => {
      const v = synth.getVoices();
      if (v.length) { resolve(v); return; }

      let resolved = false;
      const finish = () => {
        if (resolved) return;
        resolved = true;
        resolve(synth.getVoices());
      };
      synth.onvoiceschanged = finish;
      // Fallback: onvoiceschanged doesn't always fire (or already fired) —
      // resolve with whatever is available rather than hanging forever.
      setTimeout(finish, 1000);
    });
  }

  function selectBestVoice(voices, langInfo) {
    const prefix  = langInfo.voicePrefix.toLowerCase();
    const bcp47lc = langInfo.bcp47.toLowerCase();

    const matches = voices
      .map(v => ({
        voice: v,
        lang: v.lang.toLowerCase(),
        name: v.name.toLowerCase(),
      }))
      .filter(({ lang }) => lang === bcp47lc || lang.startsWith(prefix));

    if (!matches.length) {
      return null;
    }

    const preferredTerms = [
      'google', 'microsoft', 'premium', 'narrator', 'alloy',
      'nora', 'samantha', 'daniel', 'emma', 'joanna', 'amy', 'zira',
      'felix', 'olivia', 'matthew', 'salli', 'jonathan', 'kendra',
      'wave', 'breeze', 'aria', 'angel', 'alloy', 'premium', 'natural',
      'zira desktop', 'microsoft david', 'microsoft zira', 'google us english',
      'english (united states)', 'english (united kingdom)', 'us english',
      'uk english', 'british english', 'american english', 'premium english',
    ];

    return matches
      .map(({ voice, lang, name }) => {
        let score = 0;
        if (lang === bcp47lc) score += 30;
        if (voice.default) score += 5;
        if (lang.startsWith(prefix) && lang !== bcp47lc) score += 10;
        if (langInfo.voicePrefix === 'en' && (name.includes('english') || voice.lang.toLowerCase().startsWith('en'))) score += 10;
        if (voice.localService) score += 3;
        if (voice.voiceURI && voice.voiceURI.toLowerCase().includes('english')) score += 2;
        if (name.includes('premium') || name.includes('alloy') || name.includes('natural')) score += 6;
        preferredTerms.forEach(term => {
          if (name.includes(term)) score += 3;
        });
        return { voice, score };
      })
      .sort((a, b) => b.score - a.score)[0].voice;
  }

  // ── Getters ────────────────────────────────────────────────────────────
  const getIsRecording = () => isRecording;
  // Ask the synthesiser for its real state rather than trusting our flag:
  // Chrome can kill an utterance without firing onend, which would leave a
  // local flag stuck at true and make the play button unresponsive.
  const getIsSpeaking  = () => synth.speaking || synth.pending;
  const isSTTSupported = () => !!(window.SpeechRecognition || window.webkitSpeechRecognition);

  // ── Speech Recognition (STT) ───────────────────────────────────────────
  /**
   * Start recording from the microphone.
   * @param {Object} callbacks — onStart, onInterim, onFinal, onError, onEnd
   */
  function startRecognition({ onStart, onInterim, onFinal, onError, onEnd, lang } = {}) {
    if (!isSTTSupported()) {
      onError?.('Voice input not supported. Please use Chrome or Edge.');
      return;
    }

    const SR  = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SR();
    recognition.continuous     = false;
    recognition.interimResults = true;
    recognition.lang           = lang || '';   // empty = browser auto-detects

    recognition.lang           = lang || '';

    recognition.onstart = () => {
      isRecording = true;
      onStart?.();
    };

    recognition.onresult = (e) => {
      const transcript = Array.from(e.results).map(r => r[0].transcript).join('');
      const isFinal    = e.results[e.results.length - 1].isFinal;

      if (isFinal) {
        stopRecognition();
        onFinal?.(transcript);
      } else {
        onInterim?.(transcript);
      }
    };

    recognition.onerror = (e) => {
      stopRecognition();
      const msgs = {
        'not-allowed': 'Microphone access denied. Please allow mic permissions.',
        'no-speech':   'No speech detected. Please try again.',
        'network':     'Network error during speech recognition.',
        'aborted':     'Recording stopped.',
      };
      onError?.(msgs[e.error] || `Recognition error: ${e.error}`);
    };

    recognition.onend = () => {
      if (isRecording) stopRecognition();
      onEnd?.();
    };

    recognition.start();
  }

  function stopRecognition() {
    isRecording = false;
    if (!recognition) return;
    // Detach result/error handlers before aborting: a plain stop() can still
    // deliver a pending final transcript, which would send the discarded
    // recording as a message (e.g. into a freshly started chat).
    recognition.onresult = null;
    recognition.onerror  = null;
    try { recognition.abort(); } catch (_) {}
  }

  // ── Text-to-Speech (TTS) ───────────────────────────────────────────────
  /**
   * Speak text aloud using the browser's built-in TTS.
   * @param {string}  text       — text to speak
   * @param {object}  langInfo   — { bcp47, voicePrefix } from /languages
   * @param {number}  rate       — speech rate (0.8 slow / 1 normal / 1.25 fast)
   * @param {object}  callbacks  — onStart, onEnd
   */
  // Chrome silently kills utterances that run longer than ~15 seconds, so
  // long replies are spoken as a queue of sentence-sized chunks instead.
  function splitIntoChunks(text, maxLen = 180) {
    const sentences = text.replace(/\s+/g, ' ').match(/[^.!?。！？]+[.!?。！？]*/g) || [text];
    const chunks = [];
    let current = '';
    for (const s of sentences) {
      if (current && (current + s).length > maxLen) {
        chunks.push(current.trim());
        current = s;
      } else {
        current += s;
      }
    }
    if (current.trim()) chunks.push(current.trim());
    return chunks;
  }

  async function speak(text, langInfo, rate, { onStart, onEnd, onNoVoice } = {}) {
    // Clear any queued or stuck speech first. Chrome needs a short pause
    // between cancel() and speak(), or the new utterance never starts.
    if (synth.speaking || synth.pending || synth.paused) {
      synth.cancel();
      await new Promise(r => setTimeout(r, 60));
    }
    isSpeaking = false;

    const voices = await getVoices();

    const matched = selectBestVoice(voices, langInfo);
    if (!matched) {
      onNoVoice?.(`No ${langInfo.name} (${langInfo.bcp47}) voice found. Install one via your OS settings.`);
      onEnd?.();
      return;
    }

    const defaultRate = langInfo.voicePrefix === 'en' ? 0.85 : 0.92;
    const finalRate   = Math.max(0.75, Math.min(rate || defaultRate, 1.0));

    const chunks = splitIntoChunks(text);
    let ended = false;
    const done = () => {
      if (ended) return;
      ended = true;
      isSpeaking = false;
      onEnd?.();
    };

    chunks.forEach((chunk, i) => {
      const utter  = new SpeechSynthesisUtterance(chunk);
      utter.rate   = finalRate;
      utter.pitch  = 1.0;
      utter.volume = 1;
      utter.lang   = langInfo.bcp47;
      utter.voice  = matched;

      if (i === 0) {
        utter.onstart = () => { isSpeaking = true; onStart?.(); };
      }
      if (i === chunks.length - 1) {
        utter.onend = done;
      }
      // Any error (including cancellation) stops the rest of the queue and
      // resets the play button via onEnd.
      utter.onerror = () => { synth.cancel(); done(); };

      synth.speak(utter);
    });

    // Chrome can leave the synthesiser paused after a cancel; nudge it.
    synth.resume();
  }

  function stopSpeaking() {
    synth.cancel();
    isSpeaking = false;
  }

  return {
    isSTTSupported,
    startRecognition,
    stopRecognition,
    speak,
    stopSpeaking,
    getIsRecording,
    getIsSpeaking,
  };

})();
