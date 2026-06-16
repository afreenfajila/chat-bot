"""
app.py
──────
Flask backend for the multilingual voice chat app.

Routes:
  GET  /           → serves the main HTML page
  GET  /languages  → returns supported language config (for frontend)
  POST /chat       → sends a message to Claude, returns the reply

Run:
  pip install -r requirements.txt
  python app.py
"""

import truststore
truststore.inject_into_ssl()

import os
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from functools import lru_cache

import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, render_template
from anthropic import Anthropic
from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT, MODEL, MAX_TOKENS, LANGUAGES, detect_language

# ── Load environment variables from .env ───────────────────────────────────
load_dotenv(Path(__file__).parent / ".env", override=True)

# ── Flask app setup ────────────────────────────────────────────────────────
app = Flask(__name__)

# ── Anthropic client ───────────────────────────────────────────────────────
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key or api_key.startswith("sk-ant-api03-your"):
    raise EnvironmentError(
        "\n\n  ❌  ANTHROPIC_API_KEY is not set.\n"
        "  Open .env and replace the placeholder with your real API key.\n"
        "  Get one at: https://console.anthropic.com\n"
    )

client = Anthropic(api_key=api_key)

IRAS_ROOT_URL = "https://www.iras.gov.sg"
IRAS_SITEMAP_URL = urljoin(IRAS_ROOT_URL, "/sitemap")

USER_AGENT_HEADER = {
    "User-Agent": "Mozilla/5.0 (compatible; IRAS-Scraper/1.0; +https://github.com)"
}


def fetch_url_html(url: str, timeout: int = 12) -> str | None:
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


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"\w+", text) if len(token) > 1}


def score_iras_link(query: str, url: str) -> int:
    query_tokens = tokenize(query)
    score = 0
    lower_url = url.lower()
    for token in query_tokens:
        if token in lower_url:
            score += 2
    return score


def find_best_iras_pages(query: str, max_results: int = 5) -> list[str]:
    links = get_iras_sitemap_links()
    if not links:
        return [IRAS_ROOT_URL]

    scored = [(score_iras_link(query, url), url) for url in links]
    scored = [item for item in scored if item[0] > 0]
    if not scored:
        return links[:max_results]

    scored.sort(key=lambda item: item[0], reverse=True)
    return [url for _, url in scored[:max_results]]


def extract_relevant_sections(query: str, url: str, max_sections: int = 2) -> list[tuple[str, str]]:
    html = fetch_url_html(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    for bad in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        bad.decompose()

    query_tokens = tokenize(query)
    sections = []
    for node in soup.select("h1, h2, h3, p, li"):
        text = node.get_text(" ", strip=True)
        if not text:
            continue
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

    # Quick heuristics for truncation / incompleteness
    if text.endswith(('...', '…')):
        incomplete = True
    else:
        incomplete = False

    # Unmatched parentheses/brackets often indicate truncation
    if text.count('(') != text.count(')') or text.count('[') != text.count(']'):
        incomplete = True

    # If last character is a letter or digit and there's no terminal punctuation,
    # ask the model to finish (helps when the model stops mid-sentence).
    if text and text[-1].isalnum() and text[-1] not in '.!?।':
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

        response = client.messages.create(
            model=MODEL,
            max_tokens=128,
            system=system,
            messages=[{"role": "user", "content": reply}],
        )

        return response.content[0].text if response.content else reply
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


@app.route("/chat", methods=["POST"])
def chat():
    """
    Accept a conversation history from the frontend,
    send it to Claude, and return the AI reply.

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
            f"Always reply in {selected_lang['name']} in the same language as the user."
        )

        if detected_lang in {"ta", "bn", "si"}:
            effective_system_prompt += (
                "\n\nWhen replying in Tamil, Bengali, or Sinhala, use the native script only. "
                "Do not mix scripts, transliterations, or Roman letters."
            )
            if detected_lang == "si":
                effective_system_prompt += (
                    "\n\nWhen replying in Sinhala, use Sinhala script and Sinhala numerals only. "
                    "Do not use Bengali or Myanmar digits."
                )

    if iras_source_text:
        effective_system_prompt += (
            "\n\nUse the following content from the official IRAS website to answer the user. "
            "Cite the source URLs and keep the answer factual and concise.\n\n"
            f"IRAS source content:\n{iras_source_text}"
        )

    # ── Call Claude ──
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=effective_system_prompt,
            messages=messages,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    reply = response.content[0].text if response.content else "…"

    # ── Detect language of the reply for the frontend ──
    lang_code = detect_language(reply)
    lang_info = LANGUAGES.get(lang_code, LANGUAGES["en"])
    # Ensure the reply is not truncated; finish if necessary
    reply = _complete_reply(reply, lang_code)

    return jsonify({
        "reply":      reply,
        "lang":       lang_code,
        "langInfo":   lang_info,
    })


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port  = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    print(f"\n  VoiceChat is running -> http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
