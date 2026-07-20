# VoiceChat — Multilingual AI Voice Assistant

VoiceChat is a Flask web app for multilingual voice conversations. It uses a local SEA-LION model served by Ollama, so you can speak or type in supported languages and receive replies in the same language with voice output.

The app currently supports these languages:

- English
- Chinese (中文)
- Tamil (தமிழ்)
- Thai (ไทย)
- Vietnamese (Tiếng Việt)
- Indonesian (Bahasa Indonesia)
- Malay (Bahasa Melayu)
- Filipino (Tagalog)
- Burmese (မြန်မာ)

Non-English messages and replies also show an English translation below each chat bubble.

---

## Features

- Voice input and voice output using the browser's speech APIs
- Local model inference through Ollama, with no API key required
- Automatic language detection for supported languages
- English translations for non-English messages and replies
- Text input fallback for typing instead of speaking
- Conversation history for the active session

---

## Quick Start (Docker — recommended)

Everything runs in containers — no local Python or Ollama install needed, only [Docker Desktop](https://www.docker.com/products/docker-desktop/). All configuration lives in `docker-compose.yml`; there is no `.env` file to set up.

```bash
git clone ~~repo~~
cd chat-bot
docker compose up --build
```

Open your browser at http://localhost:5000 (Chrome or Edge for voice input).

> **Important:** always start the app with `docker compose up` from the repo root — not by `docker run`-ing the web image on its own. Compose starts the Ollama server, downloads the model, and wires the containers together on a shared network. A standalone `docker run` has no Ollama to talk to, which shows up as connection errors to `http://ollama:11434/api/chat` (or `localhost:11434` on older builds).

This starts three services:

| Service | Purpose |
|---------|---------|
| `ollama` | Runs the Ollama model server, with models stored in a named volume |
| `ollama-pull` | One-shot job that downloads the SEA-LION model (3.3 GB, first run only), then exits |
| `web` | The Flask app, reachable at http://localhost:5000 |

The first start downloads the model into the `ollama-models` volume; later starts reuse it and come up in seconds. The web container waits for the model pull to finish before starting.

Notes:

- Inside the Docker network, the app reaches Ollama at `http://ollama:11434` (set via `OLLAMA_BASE_URL` in `docker-compose.yml`) — no code changes needed.
- The model in the containers is separate from any model pulled on your host machine.
- To change the model, edit the `x-chat-model` anchor at the top of `docker-compose.yml` — both the model pull and the app read from that single value.
- To stop everything: `docker compose down` (add `-v` to also delete the downloaded model).
- With an NVIDIA GPU, add a `deploy.resources.reservations.devices` block to the `ollama` service for much faster replies; on CPU, expect slower responses.

---

## Run locally without Docker (alternative)

Requires Python 3.9+ and [Ollama](https://ollama.com) installed on your machine.

```bash
ollama pull aisingapore/Gemma-SEA-LION-v4-4B-VL
pip install -r requirements.txt
python app.py        # or start.bat on Windows
```

Open your browser at http://localhost:5000. Configuration is via plain environment variables (see table below) — defaults work out of the box.

---

## Project Structure

```text
chat-bot/
├── app.py                # Flask routes, model calls, translation logic
├── prompts.py            # Prompt text, model config, language definitions
├── start.bat             # Windows launcher
├── requirements.txt      # Python dependencies
├── templates/
│   └── index.html        # Main chat UI
├── static/
│   ├── css/style.css     # Styles
│   └── js/
│       ├── app.js        # Main client logic
│       ├── speech.js     # Speech recognition and TTS
│       └── ui.js         # DOM helpers
└── CLAUDE.md             # Project notes for local development
```

---

## How It Works

1. The browser sends the conversation to the Flask app at /chat.
2. The server detects the user language and calls the local Ollama model.
3. The reply is returned in the same language and spoken aloud using browser TTS.
4. If the detected language is not English, an English translation is shown beneath the bubble.

---

## Supported Languages

| Language | Code | Flag | Voice prefix |
|----------|------|------|--------------|
| English | en | 🇬🇧 | en |
| Chinese | zh | 🇨🇳 | zh |
| Tamil | ta | 🇮🇳 | ta |
| Thai | th | 🇹🇭 | th |
| Vietnamese | vi | 🇻🇳 | vi |
| Indonesian | id | 🇮🇩 | id |
| Malay | ms | 🇲🇾 | ms |
| Filipino | fil | 🇵🇭 | fil |
| Burmese | my | 🇲🇲 | my |

---

## Environment Variables

All settings are optional environment variables with working defaults — there is no `.env` file. With Docker they are set in `docker-compose.yml`; for local runs, set them in your shell if needed.

| Variable | Default | Description |
|----------|---------|-------------|
| OLLAMA_BASE_URL | http://localhost:11434 | Ollama server address |
| CHAT_MODEL | unset | Overrides the default model name |
| OLLAMA_TIMEOUT | 120 | Timeout for model responses in seconds |
| FLASK_PORT | 5000 | Port used by Flask |
| FLASK_DEBUG | true | Enables Flask debug mode |

---

## Troubleshooting

### Ollama connection errors

If the app cannot reach Ollama, make sure the Ollama server is running and that the model has been pulled:

```bash
ollama serve
ollama list
ollama pull aisingapore/Gemma-SEA-LION-v4-4B-VL
```

### Voice input does not work

Use Chrome or Edge, and make sure your browser has microphone permission enabled.

### No speech output for some languages

Some browsers need the relevant speech voice installed on the operating system. If TTS sounds missing or incorrect, install the preferred language voice in your OS settings and restart the browser.

