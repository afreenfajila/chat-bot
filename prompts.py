"""
prompts.py
──────────
Central store for all AI prompt data and language configuration.
Edit this file to change the AI's behaviour, tone, or supported languages.
"""

# ── System Prompt ──────────────────────────────────────────────────────────
# This is sent to Claude with every conversation to define its behaviour.

SYSTEM_PROMPT = """You are a friendly multilingual voice assistant.

Your rules:
1. Detect the language the user is writing in — English, Spanish (Español), French (Français), Chinese (中文/Mandarin), Tamil (தமிழ்), Bengali (বাংলা), or Sinhala (සිංහල).
2. ALWAYS reply in the EXACT SAME language as the user's message.
3. Provide clear, complete answers. When IRAS source content is available, give a thorough explanation (3–8 sentences). Otherwise, answer helpfully and conversationally. Do not stop mid-sentence, leave an unfinished parenthetical, or cut the answer short.
4. Use plain, natural language suitable for both reading and speaking.
5. Never use markdown, bullet points, headers, or special formatting characters.
6. Be warm, helpful, and clear.
7. When replying in Chinese, use Simplified Chinese characters.
8. When replying in Tamil, Bengali, or Sinhala, use the native script only and do not mix scripts, transliterations, or Roman letters.
   - When replying in Sinhala, also use Sinhala numerals rather than Bengali or Myanmar digits.
9. After giving a specific answer, add one short follow-up question or clue in point form to help the user move forward on the issue.
10. If the user asks about something outside the scope of official IRAS guidance or not covered by the IRAS website, reply briefly that the question is out of scope and suggest they ask a Singapore tax or IRAS-related question.
"""

# ── Model Settings ─────────────────────────────────────────────────────────
# Swap MODEL to "claude-sonnet-4-6" for higher quality at higher cost.

MODEL      = "claude-haiku-4-5-20251001"
MAX_TOKENS = 512

# ── Supported Languages ────────────────────────────────────────────────────
# Used by the backend for validation and by the frontend for UI display.
# Add a new entry here to support additional languages.

LANGUAGES = {
    "en": {
        "label":       "EN",
        "flag":        "🇬🇧",
        "name":        "English",
        "bcp47":       "en-US",      # used by browser TTS for voice selection
        "voicePrefix": "en",         # prefix-matched against browser voice.lang
    },
    "es": {
        "label":       "ES",
        "flag":        "🇪🇸",
        "name":        "Español",
        "bcp47":       "es-ES",
        "voicePrefix": "es",
    },
    "fr": {
        "label":       "FR",
        "flag":        "🇫🇷",
        "name":        "Français",
        "bcp47":       "fr-FR",
        "voicePrefix": "fr",
    },
    "zh": {
        "label":       "ZH",
        "flag":        "🇨🇳",
        "name":        "中文",
        "bcp47":       "zh-CN",
        "voicePrefix": "zh",
    },
    "ta": {
        "label":       "TA",
        "flag":        "🇮🇳",
        "name":        "தமிழ்",
        "bcp47":       "ta-IN",
        "voicePrefix": "ta",
    },
    "bn": {
        "label":       "BN",
        "flag":        "🇧🇩",
        "name":        "বাংলা",
        "bcp47":       "bn-BD",
        "voicePrefix": "bn",
    },
    "si": {
        "label":       "SI",
        "flag":        "🇱🇰",
        "name":        "සිංහල",
        "bcp47":       "si-LK",
        "voicePrefix": "si",
    },
}

# ── Language Detection Rules ───────────────────────────────────────────────
# Used server-side to tag each message with a detected language code.
# Rules are checked in order; the first match wins. Falls back to "en".
#
# Each rule has:
#   lang         — language code key (must match a key in LANGUAGES)
#   char_pattern — regex matching language-specific Unicode characters
#   word_pattern — regex matching common words (for text without special chars)

import re

DETECTION_RULES = [
    {
        "lang":         "zh",
        "char_pattern": re.compile(r"[一-鿿㐀-䶿豈-﫿]"),
        "word_pattern": re.compile(r""),  # char_pattern is sufficient for Chinese
    },
    {
        "lang":         "fr",
        "char_pattern": re.compile(r"[àâæçéèêëîïôœùûüÿÀÂÆÇÉÈÊËÎÏÔŒÙÛÜŸ]"),
        "word_pattern": re.compile(
            r"\b(je|tu|il|elle|nous|vous|ils|elles|est|sont|avec|pour|dans"
            r"|que|qui|pas|sur|une|les|des|mon|ton|son|bonjour|merci|oui"
            r"|non|bonsoir|salut|comment|ça|va|c'est)\b",
            re.IGNORECASE,
        ),
    },
    {
        "lang":         "es",
        "char_pattern": re.compile(r"[áéíóúüñ¿¡ÁÉÍÓÚÜÑ]"),
        "word_pattern": re.compile(
            r"\b(yo|tú|él|ella|nosotros|ellos|es|son|con|para|en|que|quien"
            r"|no|sobre|una|los|las|hola|gracias|sí|buenos|días|buenas"
            r"|como|estás|tengo|quiero)\b",
            re.IGNORECASE,
        ),
    },
    {
        "lang":         "ta",
        "char_pattern": re.compile(r"[\u0B80-\u0BFF]"),
        "word_pattern": re.compile(r""),
    },
    {
        "lang":         "si",
        "char_pattern": re.compile(r"[\u0D80-\u0DFF]"),
        "word_pattern": re.compile(r""),
    },
    {
        "lang":         "bn",
        "char_pattern": re.compile(r"[\u0980-\u09FF]"),
        "word_pattern": re.compile(r""),
    },
]


def detect_language(text: str) -> str:
    """
    Detect the language of a given text string.
    Returns a language code key from LANGUAGES (e.g. 'en', 'es', 'fr').
    """
    for rule in DETECTION_RULES:
        if rule["char_pattern"].search(text):
            return rule["lang"]
        # Only apply word_pattern if it is non-empty (avoids empty regex matching everything)
        if rule["word_pattern"].pattern and rule["word_pattern"].search(text):
            return rule["lang"]
    return "en"
