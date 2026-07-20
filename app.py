"""
app.py
──────
Flask backend for the multilingual voice chat app.

Routes:
  GET  /           → serves the main HTML page
  GET  /languages  → returns supported language config (for frontend)
  POST /chat       → sends a message to the local Ollama model, returns the reply

Run:
  pip install -r requirements.txt
  python app.py
"""

import truststore
truststore.inject_into_ssl()

import os
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
from functools import lru_cache

import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, render_template
from prompts import (
    SYSTEM_PROMPT, MODEL, MAX_TOKENS, COMPLETION_MAX_TOKENS,
    LANGUAGES, UI_STRINGS, SERVICES, detect_language,
)

# ── Flask app setup ────────────────────────────────────────────────────────
app = Flask(__name__)

# ── Ollama (local model) setup ─────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# CHAT_MODEL env var overrides the default model from prompts.py
# (must be a model available in `ollama list`).
MODEL = os.getenv("CHAT_MODEL", MODEL)

# Local inference can be slow on CPU, so allow a generous timeout.
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", 120))


def ollama_chat(messages: list[dict], system: str, max_tokens: int) -> str:
    """Send a chat request to the local Ollama server and return the reply text."""
    response = requests.post(
        urljoin(OLLAMA_BASE_URL, "/api/chat"),
        json={
            "model": MODEL,
            "messages": [{"role": "system", "content": system}] + messages,
            "stream": False,
            # Keep the model loaded between requests so replies don't pay
            # the model-load cost after idle periods (Ollama default is 5m).
            "keep_alive": "30m",
            "options": {"num_predict": max_tokens},
        },
        timeout=OLLAMA_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]

IRAS_ROOT_URL = "https://www.iras.gov.sg"
IRAS_SITEMAP_URL = urljoin(IRAS_ROOT_URL, "/sitemap")

USER_AGENT_HEADER = {
    "User-Agent": "Mozilla/5.0 (compatible; IRAS-Scraper/1.0; +https://github.com)"
}


def fetch_url_html(url: str, timeout: int = 8) -> str | None:
    try:
        response = requests.get(url, headers=USER_AGENT_HEADER, timeout=timeout)
        response.raise_for_status()
        return response.text
    except Exception:
        return None


@lru_cache(maxsize=1)
def get_iras_sitemap_links() -> list[str]:
    html = fetch_url_html(IRAS_SITEMAP_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for anchor in soup.select("a[href]"):
        href = anchor["href"].strip()
        if not href:
            continue
        if href.startswith("/"):
            full_url = urljoin(IRAS_ROOT_URL, href)
        elif href.startswith(IRAS_ROOT_URL):
            full_url = href
        else:
            continue

        parsed = urlparse(full_url)
        if parsed.netloc.endswith("iras.gov.sg"):
            links.add(parsed._replace(fragment="").geturl())

    return sorted(links)


# Function words and domain tokens are excluded from matching. Domain tokens
# ("iras", "gov", …) appear in every URL, so counting them ranks all pages
# equally and lets alphabetically-early pages (careers/…) win the tie.
STOPWORDS = {
    "how", "do", "does", "did", "what", "when", "where", "which", "who", "why",
    "is", "are", "was", "were", "be", "been", "can", "could", "should",
    "would", "will", "shall", "may", "might", "must", "have", "has", "had",
    "the", "an", "my", "me", "we", "our", "us", "you", "your", "they",
    "their", "he", "she", "it", "its", "to", "for", "of", "in", "on", "at",
    "by", "with", "from", "through", "into", "and", "or", "not", "no", "yes",
    "if", "any", "some", "much", "many", "more", "need", "want", "get",
    "please", "about", "there", "here", "this", "that", "these", "those",
    "iras", "www", "gov", "sg", "https", "http", "com",
}


def tokenize(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"\w+", text)
        if len(token) > 1 and token.lower() not in STOPWORDS
    }


def find_best_iras_pages(query: str, max_results: int = 5) -> list[str]:
    links = get_iras_sitemap_links()
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    scored = []
    for url in links:
        # Match only against the URL path, never the domain.
        path = urlparse(url).path.lower()
        slug_words = set(re.findall(r"[a-z0-9]+", path))

        score = 0
        for token in query_tokens:
            if token in slug_words:
                score += 3                    # exact slug word ("property")
            elif len(token) >= 3 and token in path:
                score += 1                    # partial ("pay" in "payments")
        if score:
            scored.append((score, url))

    # No link matches the query (greetings, non-tax questions, non-English
    # tokens): unrelated pages never yield evidence, so skip scraping entirely.
    if not scored:
        return []

    # Highest score first; shorter (more general) pages win ties.
    scored.sort(key=lambda item: (-item[0], len(item[1])))
    return [url for _, url in scored[:max_results]]


# Extracted page text is cached per URL so repeat questions on the same topic
# skip both the network fetch and the HTML parse. Failed fetches are not
# cached, so a temporarily unreachable page is retried on a later request.
_page_texts_cache: dict[str, tuple[str, ...]] = {}


def get_page_texts(url: str) -> tuple[str, ...]:
    """Return the visible section texts of a page, cached per URL."""
    cached = _page_texts_cache.get(url)
    if cached is not None:
        return cached

    html = fetch_url_html(url)
    if not html:
        return ()

    soup = BeautifulSoup(html, "html.parser")
    for bad in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        bad.decompose()

    texts = tuple(
        text
        for node in soup.select("h1, h2, h3, p, li")
        if (text := node.get_text(" ", strip=True))
    )
    _page_texts_cache[url] = texts
    return texts


def extract_relevant_sections(query: str, url: str, max_sections: int = 2) -> list[tuple[int, str]]:
    query_tokens = tokenize(query)
    sections = []
    for text in get_page_texts(url):
        lower = text.lower()
        matches = sum(1 for token in query_tokens if token in lower)
        if matches:
            sections.append((matches, text))

    sections.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    return sections[:max_sections]


def get_iras_evidence(query: str) -> tuple[str | None, list[str]]:
    urls = find_best_iras_pages(query, max_results=6)
    if not urls:
        return None, []

    # Fetch all candidate pages concurrently: wall time is the slowest single
    # fetch instead of the sum of up to six sequential ones.
    with ThreadPoolExecutor(max_workers=len(urls)) as pool:
        list(pool.map(get_page_texts, urls))

    evidence = []
    source_urls: list[str] = []
    for url in urls:
        sections = extract_relevant_sections(query, url)
        if not sections:
            continue
        source_urls.append(url)
        for _, text in sections:
            snippet = text.strip()
            if snippet and snippet not in evidence:
                evidence.append(snippet)
        if len(evidence) >= 4:
            break

    if not evidence:
        return None, []

    source_text = "\n\n".join(f"{i+1}. {snippet}" for i, snippet in enumerate(evidence[:4]))
    return source_text, source_urls


def _complete_reply(reply: str, lang_code: str) -> str:
    """
    Ensure the assistant reply is a complete, well-formed set of sentences.
    If the reply appears truncated (unfinished parenthesis, trailing ellipsis,
    or missing terminal punctuation), ask the model to finish the text in the
    same language without adding new facts. Returns the original reply on
    failure or when no completion is needed.
    """
    if not reply or not isinstance(reply, str):
        return reply

    text = reply.strip()
    if not text:
        return reply

    # Quick heuristics for truncation / incompleteness.
    incomplete = False

    if text.endswith(('...', '…')):
        incomplete = True

    # Unmatched parentheses/brackets often indicate truncation.
    if text.count('(') != text.count(')') or text.count('[') != text.count(']'):
        incomplete = True

    # A trailing comma, colon, dash or opening quote often means the model stopped early.
    if text.endswith((',', ':', ';', '-', '—', '–', '“', '‘', '"', "'")):
        incomplete = True

    # If the response ends in a letter/digit without terminal punctuation, ask the model to finish.
    if text and text[-1].isalnum() and not re.search(r"[.!?。！？]$", text):
        incomplete = True

    if not incomplete:
        return reply

    try:
        lang_name = LANGUAGES.get(lang_code, {}).get('name', 'the user\'s language')
        system = (
            f"You are a concise assistant that only finishes partially-written replies. "
            f"Complete the following reply in {lang_name} without adding new information. "
            "Close any unfinished sentences or parentheses and ensure the text ends with proper punctuation. "
            "Reply ONLY with the completed text."
        )

        completed = ollama_chat(
            [{"role": "user", "content": reply}],
            system=system,
            max_tokens=COMPLETION_MAX_TOKENS,
        )
        return completed.strip() or reply
    except Exception:
        return reply


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main chat page."""
    return render_template("index.html")


@app.route("/languages")
def get_languages():
    """
    Return supported language config to the frontend.
    Keeps language data in one place (prompts.py) rather than duplicating it in JS.
    """
    return jsonify(LANGUAGES)


# Markdown-style links: keep the link text, drop the URL.
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(\s*https?://[^)]*\)")
# Bare URLs, optionally wrapped in brackets/parentheses.
_URL_RE = re.compile(r"[\(\[<]?\bhttps?://[^\s\)\]>]+[\)\]>]?")


def _strip_urls(text: str) -> str:
    """Remove inline URLs from a model reply (sources are sent separately)."""
    text = _MD_LINK_RE.sub(r"\1", text)
    text = _URL_RE.sub("", text)
    # Tidy whitespace left behind by removed links.
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +([.,;:!?])", r"\1", text)
    return text.strip()


def _format_reply_structure(text: str) -> str:
    """Put numbered points and the closing question on their own lines.

    The system prompt asks for this layout, but the small model often runs
    everything together inline ("intro. 1. point. 2. point. Question?"), so
    the line breaks are inserted deterministically here. The frontend bubble
    renders newlines via `white-space: pre-line`.
    """
    # Break before each inline enumerator ("1.", "2)", "3、") that follows the
    # end of a sentence or an introductory colon. `\s*` (not `+`) also catches
    # CJK text, which has no space after 。！？：
    text = re.sub(r"(?<=[.!?。！？:：])\s*(?=\d{1,2}[.)、]\s*\S)", "\n", text)
    # Break before the final follow-up question when it trails another
    # sentence on the same line. The lookahead requires the remainder to be a
    # single sentence (no other sentence-ending punctuation) ending in ?
    text = re.sub(r"(?<=[.!?。！？])[ \t]*(?=[^\n.!?。！？]+[?？]\s*$)", "\n", text)
    return text


@app.route("/services")
def get_services():
    """
    Return the guided-conversation config (localized greeting, service topics
    and tap-to-ask guiding questions) used by the frontend welcome flow.
    """
    return jsonify({"ui": UI_STRINGS, "services": SERVICES})


@app.route("/chat", methods=["POST"])
def chat():
    """
    Accept a conversation history from the frontend,
    send it to the local Ollama model, and return the AI reply.

    Expected JSON body:
    {
      "messages": [
        { "role": "user",      "content": "Hello!" },
        { "role": "assistant", "content": "Hi there!" },
        ...
      ]
    }

    Response JSON:
    {
      "reply":      "The AI's response text",
      "lang":       "en",    ← detected language code
      "langInfo":   { "label": "EN", "flag": "🇬🇧", ... },
    }
    """
    data = request.get_json(silent=True)

    # ── Validate input ──
    if not data or "messages" not in data:
        return jsonify({"error": "Request body must include a 'messages' array."}), 400

    messages = data["messages"]
    input_lang = data.get("inputLang", "auto")

    if not isinstance(messages, list) or len(messages) == 0:
        return jsonify({"error": "'messages' must be a non-empty array."}), 400

    if input_lang != "auto" and input_lang not in LANGUAGES:
        return jsonify({"error": "'inputLang' must be either 'auto' or a supported language code."}), 400

    last_user_msg = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), None
    )

    iras_source_text, iras_source_urls = (None, [])
    if last_user_msg:
        iras_source_text, iras_source_urls = get_iras_evidence(last_user_msg)

    effective_system_prompt = SYSTEM_PROMPT
    detected_lang = input_lang
    if input_lang == "auto" and last_user_msg:
        detected_lang = detect_language(last_user_msg)

    if detected_lang != "auto":
        selected_lang = LANGUAGES[detected_lang]
        effective_system_prompt += (
            f"\n\nThe user message appears to be in {selected_lang['name']}. "
            f"Always reply in {selected_lang['name']} in the same language as the user. "
            f"Do not reply in any other language."
        )

        if detected_lang in {"ta", "th", "my"}:
            effective_system_prompt += (
                "\n\nWhen replying in Tamil, Thai, or Burmese, use the native script only. "
                "Do not mix scripts, transliterations, or Roman letters."
            )
        elif detected_lang in {"id", "ms"}:
            effective_system_prompt += (
                "\n\nDo not mix Indonesian and Malay. Reply strictly in "
                f"{selected_lang['name']} vocabulary and spelling."
            )

    if iras_source_text:
        effective_system_prompt += (
            "\n\nUse the following content from the official IRAS website to answer the user. "
            "Keep the answer factual. Do not copy URLs or web addresses into your reply — "
            "the source links are shown to the user separately.\n\n"
            f"IRAS source content:\n{iras_source_text}"
        )

    # ── Call the local model ──
    try:
        reply = ollama_chat(
            messages,
            system=effective_system_prompt,
            max_tokens=MAX_TOKENS,
        ) or "…"
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    # Ensure the reply is not truncated; finish it if necessary.
    reply = _complete_reply(reply, detect_language(reply))

    # The model is told not to include URLs, but small models don't always
    # comply (and sometimes hallucinate links) — strip them defensively.
    # Real source links are returned separately in "sources".
    reply = _strip_urls(reply)

    # Likewise, enforce the scannable layout (numbered points and the
    # follow-up question on their own lines) that the model often skips.
    reply = _format_reply_structure(reply)

    # Detect the final language for the frontend after completion.
    lang_code = detect_language(reply)
    lang_info = LANGUAGES.get(lang_code, LANGUAGES["en"])

    return jsonify({
        "reply":      reply,
        "lang":       lang_code,
        "langInfo":   lang_info,
        "sources":    iras_source_urls,
    })


def _warm_up():
    """Preload the sitemap and the model so the first request is fast."""
    try:
        get_iras_sitemap_links()
    except Exception:
        pass
    try:
        # A generate request without a prompt just loads the model into memory.
        requests.post(
            urljoin(OLLAMA_BASE_URL, "/api/generate"),
            json={"model": MODEL, "keep_alive": "30m"},
            timeout=OLLAMA_TIMEOUT,
        )
    except Exception:
        pass


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port  = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    # In debug mode the reloader runs this module twice; only warm up in the
    # process that actually serves requests.
    if not debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=_warm_up, daemon=True).start()

    print(f"\n  VoiceChat is running -> http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
