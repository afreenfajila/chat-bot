"""
prompts.py
──────────
Central store for all AI prompt data and language configuration.
Edit this file to change the AI's behaviour, tone, or supported languages.
"""

# ── System Prompt ──────────────────────────────────────────────────────────
# This is sent to the model with every conversation to define its behaviour.

SYSTEM_PROMPT = """You are a friendly multilingual voice assistant.

Your rules:
1. Detect the language the user is writing in — English, Chinese (中文/Mandarin), Tamil (தமிழ்), Thai (ไทย), Vietnamese (Tiếng Việt), Indonesian (Bahasa Indonesia), Malay (Bahasa Melayu), Filipino (Tagalog), or Burmese (မြန်မာ).
2. ALWAYS reply in the EXACT SAME language as the user's message. NEVER reply in any language outside the list above — never Korean, Japanese, Hindi, or any other language.
   - If the user writes a supported language in Roman letters (for example "eppadi irukinga" is Tamil), reply in that language using its native script.
   - If you are unsure what language the message is, reply in English.
3. Provide clear, complete answers. When IRAS source content is available, give a thorough explanation (3–8 sentences). Otherwise, answer helpfully and conversationally. Do not stop mid-sentence, leave an unfinished parenthetical, or cut the answer short.
4. Use plain, natural language suitable for both reading and speaking.
5. Never use markdown, bullet points, headers, or special formatting characters.
6. Be warm, helpful, and clear.
7. When replying in Chinese, use Simplified Chinese characters.
8. When replying in Tamil, Thai, or Burmese, use the native script only and do not mix scripts, transliterations, or Roman letters.
9. Do not mix Indonesian and Malay: reply in Indonesian only to Indonesian messages and in Malay only to Malay messages.
10. After giving a specific answer, add one short follow-up question or clue in point form to help the user move forward on the issue.
11. If the user asks about something outside the scope of official IRAS guidance or not covered by the IRAS website, reply briefly that the question is out of scope and suggest they ask a Singapore tax or IRAS-related question.
"""

# ── Model Settings ─────────────────────────────────────────────────────────
# MODEL must be available in `ollama list`.
# SEA-LION v4 is tuned for Southeast Asian languages; pull it with:
#   ollama pull aisingapore/Gemma-SEA-LION-v4-4B-VL

MODEL                  = "aisingapore/Gemma-SEA-LION-v4-4B-VL"
MAX_TOKENS             = 768
COMPLETION_MAX_TOKENS = 256

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
    "th": {
        "label":       "TH",
        "flag":        "🇹🇭",
        "name":        "ไทย",
        "bcp47":       "th-TH",
        "voicePrefix": "th",
    },
    "vi": {
        "label":       "VI",
        "flag":        "🇻🇳",
        "name":        "Tiếng Việt",
        "bcp47":       "vi-VN",
        "voicePrefix": "vi",
    },
    "id": {
        "label":       "ID",
        "flag":        "🇮🇩",
        "name":        "Bahasa Indonesia",
        "bcp47":       "id-ID",
        "voicePrefix": "id",
    },
    "ms": {
        "label":       "MS",
        "flag":        "🇲🇾",
        "name":        "Bahasa Melayu",
        "bcp47":       "ms-MY",
        "voicePrefix": "ms",
    },
    "fil": {
        "label":       "FIL",
        "flag":        "🇵🇭",
        "name":        "Filipino",
        "bcp47":       "fil-PH",
        "voicePrefix": "fil",
    },
    "my": {
        "label":       "MY",
        "flag":        "🇲🇲",
        "name":        "မြန်မာ",
        "bcp47":       "my-MM",
        "voicePrefix": "my",
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
        # word_pattern catches common romanized Tamil (e.g. "eppadi irukinga")
        "lang":         "ta",
        "char_pattern": re.compile(r"[\u0B80-\u0BFF]"),
        "word_pattern": re.compile(
            r"\b(vanakkam|eppadi|epdi|irukinga|irukeenga|irukku|iruku"
            r"|nandri|enna|yenna|seri|sollunga|venum|vendam|panna"
            r"|pannunga|ungalukku|unakku|enakku|romba|konjam)\b",
            re.IGNORECASE,
        ),
    },
    {
        "lang":         "th",
        "char_pattern": re.compile(r"[\u0E00-\u0E7F]"),
        "word_pattern": re.compile(r""),
    },
    {
        "lang":         "my",
        "char_pattern": re.compile(r"[\u1000-\u109F]"),
        "word_pattern": re.compile(r""),
    },
    {
        # Vietnamese: \u0103/\u0111/\u01A1/\u01B0 and the Latin Extended Additional block
        # (U+1EA0-U+1EF9) only occur in Vietnamese among the supported languages.
        "lang":         "vi",
        "char_pattern": re.compile(r"[\u0103\u00E2\u0111\u00EA\u00F4\u01A1\u01B0\u0102\u00C2\u0110\u00CA\u00D4\u01A0\u01AF\u1EA0-\u1EF9]"),
        "word_pattern": re.compile(
            r"\b(v\u00E0|c\u1EE7a|l\u00E0|c\u00F3|kh\u00F4ng|t\u00F4i|b\u1EA1n|anh|ch\u1ECB|em|n\u00E0y|\u0111\u01B0\u1EE3c|cho|v\u1EDBi"
            r"|xin|ch\u00E0o|c\u1EA3m|\u01A1n|nh\u00E9|r\u1ED3i|v\u00E2ng|g\u00EC|sao)\b",
            re.IGNORECASE,
        ),
    },
    # Filipino, Malay and Indonesian use plain Latin script, so they rely
    # on word patterns alone. Malay and Indonesian overlap heavily; the
    # lists below favour words distinctive to each. Ambiguous input falls
    # through to "en" \u2014 the model still replies in the user's language
    # via the system prompt.
    {
        "lang":         "fil",
        "char_pattern": re.compile(r"$^"),  # never matches
        "word_pattern": re.compile(
            r"\b(ang|ng|mga|ako|ikaw|siya|kami|tayo|hindi|opo|po|salamat"
            r"|kumusta|magandang|umaga|gabi|paano|ano|dito|naman|natin)\b",
            re.IGNORECASE,
        ),
    },
    {
        "lang":         "ms",
        "char_pattern": re.compile(r"$^"),
        "word_pattern": re.compile(
            r"\b(tak|nak|awak|korang|khabar|macam|boleh|kat|cakap|pukul"
            r"|kenapa|mana|sini|tolong)\b",
            re.IGNORECASE,
        ),
    },
    {
        "lang":         "id",
        "char_pattern": re.compile(r"$^"),
        "word_pattern": re.compile(
            r"\b(tidak|bisa|aku|kamu|kalian|anda|sudah|belum|sedang"
            r"|gimana|banget|sekarang|kabar|bagaimana|apakah|selamat"
            r"|pagi|malam)\b",
            re.IGNORECASE,
        ),
    },
]


def detect_language(text: str) -> str:
    """
    Detect the language of a given text string.
    Returns a language code key from LANGUAGES (e.g. 'en', 'th', 'vi').
    """
    for rule in DETECTION_RULES:
        if rule["char_pattern"].search(text):
            return rule["lang"]
        # Only apply word_pattern if it is non-empty (avoids empty regex matching everything)
        if rule["word_pattern"].pattern and rule["word_pattern"].search(text):
            return rule["lang"]
    return "en"
