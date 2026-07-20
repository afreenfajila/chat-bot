# CLAUDE.md — VoiceChat Project Guide

## What this project is

A Flask web app for multilingual voice chat, powered by a local SEA-LION model served by Ollama.
Users speak or type in English, Chinese, Tamil, Thai, Vietnamese, Indonesian, Malay, Filipino, or Burmese (SEA-LION's focus languages); the model replies in the same language (text + TTS). Non-English messages and replies show an English translation below each chat bubble.

---

## How to run

```bash
# Docker (recommended — starts Ollama, pulls the model, runs the app)
docker compose up --build

# Windows local run (installs deps + starts server)
start.bat

# Mac / Linux local run
pip install -r requirements.txt && python app.py
```

Server runs at **http://localhost:5000**. Requires Chrome or Edge for voice input.

Local (non-Docker) runs require [Ollama](https://ollama.com) running locally with the model pulled (`ollama pull aisingapore/Gemma-SEA-LION-v4-4B-VL`). No API key needed. There is **no `.env` file** — configuration is plain environment variables with working defaults; Docker values are set in `docker-compose.yml`.

---

## Project layout

```
app.py          Flask server — routes, Ollama model calls, translation logic
prompts.py      SYSTEM_PROMPT, MODEL, MAX_TOKENS, LANGUAGES, detect_language()
templates/
  index.html    Single-page chat UI (rendered by Flask)
static/
  css/style.css All styles including .translation bubble styling
  js/app.js     Main controller: history, fetch /chat, wires UI + Speech
  js/speech.js  Web Speech API — STT (mic) and TTS (voice output)
  js/ui.js      Pure DOM layer: addBubble(), addTranslation(), status bar
requirements.txt
start.bat       Windows one-command launcher
Dockerfile      Web app image (env defaults for running on the compose network)
docker-compose.yml  ollama + ollama-pull + web; model name set once via x-chat-model anchor
```

---

## Key architecture decisions

- **All model calls happen server-side in `app.py`**, via `ollama_chat()` against the local Ollama server's `/api/chat` endpoint. No cloud API, no API key.
- **Language config is defined once** in `prompts.py → LANGUAGES` and served to the frontend via `GET /languages`. Do not duplicate language data in JS.
- **Language detection runs server-side** in `detect_language()`. The client-side `guessLangInfoFromText()` in `app.js` is only used to show the user bubble immediately (before the server responds) and mirrors the same logic.
- **Translation is a second model call** inside `_translate_to_english()` in `app.py`. It only fires when the detected language is not English.
- **IRAS scraping is cached and parallel.** Extracted page text is cached in-process per URL (`_page_texts_cache`), candidate pages are fetched concurrently, and scraping is skipped entirely when no sitemap URL matches the query (e.g. greetings). The sitemap and model are pre-warmed at startup, and Ollama keeps the model loaded for 30 minutes between requests.
- **User bubble is shown immediately**, then updated with `userTranslation` after the server responds via `UI.addTranslation()`.
- **Welcome flow is fully static and client-driven.** On load (and on 🔄 New chat), `app.js → startWelcomeFlow()` renders guide bubbles from `prompts.py → UI_STRINGS`/`SERVICES` (served by `GET /services`): language picker → localized greeting + service topics → tap-to-ask guiding questions. No model call, so it is instant; guide bubbles are never added to `conversationHistory`. Picking a language also sets the input-language dropdown, which pins STT and reply language.

---

## API endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Serves the chat page |
| GET | `/languages` | Returns `LANGUAGES` dict as JSON |
| GET | `/services` | Returns `{ ui, services }` — localized greeting + topic/guiding-question config for the welcome flow |
| POST | `/chat` | Accepts `{ messages }`, returns reply + translations |

### POST /chat response shape

```json
{
  "reply":           "Xin chào! Tôi có thể giúp gì cho bạn?",
  "lang":            "vi",
  "langInfo":        { "label": "VI", "flag": "🇻🇳", "name": "Tiếng Việt", "bcp47": "vi-VN", "voicePrefix": "vi" },
  "translation":     "Hello! How can I help you?",
  "userTranslation": "Hello, how are you today?"
}
```

`translation` and `userTranslation` are `null` when the detected language is English.

---

## Language detection

Defined in `prompts.py → DETECTION_RULES`. Rules are checked in order; first match wins. Falls back to `"en"`.

Each rule has:
- `char_pattern` — Unicode character range regex (primary signal)
- `word_pattern` — common-word regex (secondary signal, only applied when non-empty)

The `detect_language()` function checks `char_pattern` first, then only checks `word_pattern` if `rule["word_pattern"].pattern` is non-empty. This avoids the Chinese rule's empty `word_pattern` matching every string.

The client-side `guessLangInfoFromText()` in `app.js` mirrors the same two-step logic (char check → word check).

---

## How to add a new language

1. **`prompts.py → LANGUAGES`** — add an entry with `label`, `flag`, `name`, `bcp47`, `voicePrefix`.
2. **`prompts.py → DETECTION_RULES`** — add a rule with `lang`, `char_pattern`, `word_pattern`. Insert it before the most general rules.
3. **`prompts.py → SYSTEM_PROMPT`** — mention the new language in rule 1 so the model knows to detect and reply in it.
4. **`app.js → guessLangInfoFromText()`** — add a matching client-side pattern so the user bubble flag shows immediately.

No frontend changes needed for the badge list or language config — those are loaded dynamically from `/languages`.

---

## Common commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server (debug mode on by default)
python app.py

# Check server is up
curl http://localhost:5000/languages

# Change port or disable debug
FLASK_PORT=8080 FLASK_DEBUG=false python app.py
```

---

## Environment variables

Set as plain environment variables (no `.env` file). In Docker they are set in `docker-compose.yml` / the `Dockerfile`.

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Where the Ollama server listens (`http://ollama:11434` in Docker) |
| `CHAT_MODEL` | unset | Overrides `MODEL` from `prompts.py` (must be in `ollama list`) |
| `OLLAMA_TIMEOUT` | `120` | Seconds to wait for a model reply |
| `FLASK_PORT` | `5000` | Port the server listens on |
| `FLASK_DEBUG` | `true` | Flask debug/reload mode |

---

## Model settings (`prompts.py`)

| Variable | Current value | Notes |
|----------|--------------|-------|
| `MODEL` | `aisingapore/Gemma-SEA-LION-v4-4B-VL` | Local SEA-LION model, tuned for Southeast Asian languages |
| `MAX_TOKENS` | `768` | Max tokens for chat replies |
| `COMPLETION_MAX_TOKENS` | `256` | Max tokens when finishing a truncated reply |

Translation calls use the same `MODEL` with `max_tokens=256`.
