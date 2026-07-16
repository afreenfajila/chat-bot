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

## Requirements

- Python 3.9 or newer
- Chrome or Edge for the best voice input experience
- Ollama installed and running locally

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/afreenfajila/chat-bot.git
cd chat-bot
```

### 2. Pull the model

Install Ollama and pull the SEA-LION model:

```bash
ollama pull aisingapore/Gemma-SEA-LION-v4-4B-VL
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

Windows:

```bat
start.bat
```

Mac / Linux:

```bash
python app.py
```

Open your browser at http://localhost:5000

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

The app uses the following optional environment variables:

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

