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
3. Be conversational: acknowledge the user's question before answering, and answer like a friendly helpdesk officer, not a document. When IRAS source content is available, give a thorough explanation (3–8 sentences). Otherwise, answer helpfully and conversationally. Do not stop mid-sentence, leave an unfinished parenthetical, or cut the answer short.
   - If the user's question is vague or missing a key detail (for example which year, whether they are an individual or a company), ask ONE short clarifying question instead of guessing.
   - If the user greets you or asks what you can do, greet them back warmly and briefly list the topics you can help with: personal income tax, corporate income tax, GST, property tax, and stamp duty.
4. Use plain, natural language suitable for both reading and speaking.
5. Structure every answer so it is easy to scan:
   - Start with ONE short sentence that directly answers or acknowledges the question.
   - When the answer has more than one point, step, or condition, put each on its own line as a simple numbered list (1., 2., 3.).
   - Keep each point to one or two short sentences.
   - End with ONE short follow-up question on its own line to help the user move forward.
6. Never use markdown symbols such as *, #, backticks, or tables. Plain text with line breaks and simple numbers only.
7. Never include URLs, links, or web addresses in your reply. Source links are shown to the user separately.
8. Be warm, helpful, and clear.
9. When replying in Chinese, use Simplified Chinese characters.
10. When replying in Tamil, Thai, or Burmese, use the native script only and do not mix scripts, transliterations, or Roman letters.
11. Do not mix Indonesian and Malay: reply in Indonesian only to Indonesian messages and in Malay only to Malay messages.
12. If the user asks about something outside the scope of official IRAS guidance or not covered by the IRAS website, reply briefly that the question is out of scope and suggest they ask a Singapore tax or IRAS-related question.
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


# ── Guided conversation (welcome flow) ─────────────────────────────────────
# Shown by the frontend when the chat loads or a new session starts:
# 1. the user picks a language, 2. a localized greeting appears with the
# service topics below, 3. picking a topic shows tap-to-ask guiding questions.
# Served to the frontend via GET /services. All text is static (no model
# call) so the welcome flow is instant even on CPU.

UI_STRINGS = {
    "en": {
        "greeting":     "👋 Hello! I'm your IRAS tax assistant. I can answer questions about Singapore taxes in your language.",
        "choose_topic": "Choose a topic below, or just type your question:",
        "questions_intro": "Here are some questions you can tap to ask, or type your own:",
    },
    "zh": {
        "greeting":     "👋 您好！我是您的 IRAS 税务助手，可以用您的语言回答有关新加坡税务的问题。",
        "choose_topic": "请选择下面的一个主题，或直接输入您的问题：",
        "questions_intro": "您可以点击下面的问题提问，也可以输入自己的问题：",
    },
    "ta": {
        "greeting":     "👋 வணக்கம்! நான் உங்கள் IRAS வரி உதவியாளர். சிங்கப்பூர் வரிகள் பற்றிய கேள்விகளுக்கு உங்கள் மொழியில் பதிலளிப்பேன்.",
        "choose_topic": "கீழே ஒரு தலைப்பைத் தேர்ந்தெடுக்கவும், அல்லது உங்கள் கேள்வியைத் தட்டச்சு செய்யவும்:",
        "questions_intro": "கீழே உள்ள கேள்விகளைத் தொட்டுக் கேட்கலாம், அல்லது உங்கள் சொந்தக் கேள்வியைத் தட்டச்சு செய்யலாம்:",
    },
    "th": {
        "greeting":     "👋 สวัสดี! ฉันคือผู้ช่วยด้านภาษี IRAS ของคุณ ฉันตอบคำถามเกี่ยวกับภาษีของสิงคโปร์ในภาษาของคุณได้",
        "choose_topic": "เลือกหัวข้อด้านล่าง หรือพิมพ์คำถามของคุณ:",
        "questions_intro": "แตะคำถามด้านล่างเพื่อถาม หรือพิมพ์คำถามของคุณเอง:",
    },
    "vi": {
        "greeting":     "👋 Xin chào! Tôi là trợ lý thuế IRAS của bạn. Tôi có thể trả lời các câu hỏi về thuế ở Singapore bằng ngôn ngữ của bạn.",
        "choose_topic": "Chọn một chủ đề bên dưới, hoặc nhập câu hỏi của bạn:",
        "questions_intro": "Bạn có thể chạm vào câu hỏi bên dưới để hỏi, hoặc tự nhập câu hỏi:",
    },
    "id": {
        "greeting":     "👋 Halo! Saya asisten pajak IRAS Anda. Saya bisa menjawab pertanyaan tentang pajak Singapura dalam bahasa Anda.",
        "choose_topic": "Pilih topik di bawah ini, atau ketik pertanyaan Anda:",
        "questions_intro": "Ketuk salah satu pertanyaan di bawah untuk bertanya, atau ketik pertanyaan Anda sendiri:",
    },
    "ms": {
        "greeting":     "👋 Salam sejahtera! Saya pembantu cukai IRAS anda. Saya boleh menjawab soalan tentang cukai Singapura dalam bahasa anda.",
        "choose_topic": "Pilih topik di bawah, atau taip soalan anda:",
        "questions_intro": "Ketik soalan di bawah untuk bertanya, atau taip soalan anda sendiri:",
    },
    "fil": {
        "greeting":     "👋 Kumusta! Ako ang iyong IRAS tax assistant. Masasagot ko ang mga tanong tungkol sa buwis sa Singapore sa iyong wika.",
        "choose_topic": "Pumili ng paksa sa ibaba, o i-type ang iyong tanong:",
        "questions_intro": "I-tap ang isang tanong sa ibaba para magtanong, o i-type ang sarili mong tanong:",
    },
    "my": {
        "greeting":     "👋 မင်္ဂလာပါ! ကျွန်ုပ်သည် သင့် IRAS အခွန်လက်ထောက်ဖြစ်ပါသည်။ စင်္ကာပူအခွန်များအကြောင်း မေးခွန်းများကို သင့်ဘာသာစကားဖြင့် ဖြေကြားပေးနိုင်ပါသည်။",
        "choose_topic": "အောက်တွင် ခေါင်းစဉ်တစ်ခုကို ရွေးချယ်ပါ သို့မဟုတ် သင့်မေးခွန်းကို ရိုက်ထည့်ပါ:",
        "questions_intro": "မေးရန် အောက်ပါမေးခွန်းတစ်ခုကို နှိပ်ပါ သို့မဟုတ် ကိုယ်ပိုင်မေးခွန်း ရိုက်ထည့်ပါ:",
    },
}

SERVICES = {
    "income": {
        "icon": "💼",
        "name": {
            "en": "Personal Income Tax",   "zh": "个人所得税",
            "ta": "தனிநபர் வருமான வரி",     "th": "ภาษีเงินได้บุคคลธรรมดา",
            "vi": "Thuế thu nhập cá nhân",  "id": "Pajak Penghasilan Pribadi",
            "ms": "Cukai Pendapatan Individu", "fil": "Personal na Buwis sa Kita",
            "my": "တစ်ဦးချင်းဝင်ငွေခွန်",
        },
        "questions": {
            "en": ["How do I file my personal income tax?", "What tax reliefs can I claim?", "When is the tax filing deadline?"],
            "zh": ["如何申报个人所得税？", "我可以申请哪些税务减免？", "报税截止日期是什么时候？"],
            "ta": ["தனிநபர் வருமான வரியை எப்படி தாக்கல் செய்வது?", "நான் எந்த வரி நிவாரணங்களைக் கோரலாம்?", "வரி தாக்கல் கடைசி தேதி எப்போது?"],
            "th": ["ฉันจะยื่นภาษีเงินได้บุคคลธรรมดาอย่างไร?", "ฉันขอลดหย่อนภาษีอะไรได้บ้าง?", "กำหนดยื่นภาษีคือเมื่อไหร่?"],
            "vi": ["Làm thế nào để khai thuế thu nhập cá nhân?", "Tôi có thể yêu cầu những khoản giảm thuế nào?", "Hạn chót khai thuế là khi nào?"],
            "id": ["Bagaimana cara melaporkan pajak penghasilan pribadi?", "Keringanan pajak apa saja yang bisa saya klaim?", "Kapan batas waktu pelaporan pajak?"],
            "ms": ["Bagaimana cara memfailkan cukai pendapatan saya?", "Apakah pelepasan cukai yang boleh saya tuntut?", "Bilakah tarikh akhir memfailkan cukai?"],
            "fil": ["Paano mag-file ng personal income tax?", "Anong mga tax relief ang maaari kong i-claim?", "Kailan ang deadline ng pag-file ng buwis?"],
            "my": ["တစ်ဦးချင်းဝင်ငွေခွန်ကို ဘယ်လိုတင်သွင်းရမလဲ?", "ဘယ်အခွန်သက်သာခွင့်တွေ တောင်းဆိုနိုင်မလဲ?", "အခွန်တင်သွင်းရမည့် နောက်ဆုံးရက်က ဘယ်တော့လဲ?"],
        },
    },
    "corporate": {
        "icon": "🏢",
        "name": {
            "en": "Corporate Income Tax",  "zh": "企业所得税",
            "ta": "நிறுவன வருமான வரி",      "th": "ภาษีเงินได้นิติบุคคล",
            "vi": "Thuế doanh nghiệp",     "id": "Pajak Perusahaan",
            "ms": "Cukai Syarikat",        "fil": "Buwis ng Kumpanya",
            "my": "ကုမ္ပဏီဝင်ငွေခွန်",
        },
        "questions": {
            "en": ["What is the corporate income tax rate?", "How do I file my company's tax return?", "Are there tax exemptions for new companies?"],
            "zh": ["企业所得税税率是多少？", "如何为公司申报税务？", "新公司有哪些税务豁免？"],
            "ta": ["நிறுவன வருமான வரி விகிதம் என்ன?", "எனது நிறுவனத்தின் வரியை எப்படி தாக்கல் செய்வது?", "புதிய நிறுவனங்களுக்கு வரி விலக்குகள் உள்ளதா?"],
            "th": ["อัตราภาษีเงินได้นิติบุคคลคือเท่าไร?", "จะยื่นภาษีของบริษัทอย่างไร?", "บริษัทใหม่มีการยกเว้นภาษีหรือไม่?"],
            "vi": ["Thuế suất thuế doanh nghiệp là bao nhiêu?", "Làm thế nào để khai thuế cho công ty?", "Công ty mới có được miễn thuế không?"],
            "id": ["Berapa tarif pajak penghasilan perusahaan?", "Bagaimana cara melaporkan pajak perusahaan saya?", "Apakah ada pembebasan pajak untuk perusahaan baru?"],
            "ms": ["Berapakah kadar cukai pendapatan syarikat?", "Bagaimana memfailkan cukai syarikat saya?", "Adakah pengecualian cukai untuk syarikat baharu?"],
            "fil": ["Magkano ang corporate income tax rate?", "Paano mag-file ng buwis ng aking kumpanya?", "May tax exemption ba para sa mga bagong kumpanya?"],
            "my": ["ကုမ္ပဏီဝင်ငွေခွန်နှုန်းက ဘယ်လောက်လဲ?", "ကျွန်ုပ်ကုမ္ပဏီရဲ့ အခွန်ကို ဘယ်လိုတင်သွင်းရမလဲ?", "ကုမ္ပဏီအသစ်တွေအတွက် အခွန်ကင်းလွတ်ခွင့် ရှိပါသလား?"],
        },
    },
    "gst": {
        "icon": "🧾",
        "name": {
            "en": "GST",                   "zh": "消费税 (GST)",
            "ta": "GST (சரக்கு சேவை வரி)",  "th": "ภาษี GST",
            "vi": "Thuế GST",              "id": "GST",
            "ms": "GST",                   "fil": "GST",
            "my": "GST",
        },
        "questions": {
            "en": ["What is the current GST rate?", "Does my business need to register for GST?", "How can tourists claim GST refunds?"],
            "zh": ["目前的消费税税率是多少？", "我的公司需要注册消费税吗？", "游客如何申请消费税退税？"],
            "ta": ["தற்போதைய GST விகிதம் என்ன?", "எனது வணிகம் GST பதிவு செய்ய வேண்டுமா?", "சுற்றுலாப் பயணிகள் GST திரும்பப்பெறுவது எப்படி?"],
            "th": ["อัตราภาษี GST ปัจจุบันคือเท่าไร?", "ธุรกิจของฉันต้องจดทะเบียน GST หรือไม่?", "นักท่องเที่ยวขอคืนภาษี GST ได้อย่างไร?"],
            "vi": ["Thuế suất GST hiện tại là bao nhiêu?", "Doanh nghiệp của tôi có cần đăng ký GST không?", "Du khách hoàn thuế GST như thế nào?"],
            "id": ["Berapa tarif GST saat ini?", "Apakah bisnis saya perlu mendaftar GST?", "Bagaimana turis mengklaim pengembalian GST?"],
            "ms": ["Berapakah kadar GST sekarang?", "Adakah perniagaan saya perlu mendaftar GST?", "Bagaimana pelancong menuntut bayaran balik GST?"],
            "fil": ["Magkano ang kasalukuyang GST rate?", "Kailangan bang magparehistro ng GST ang negosyo ko?", "Paano makakakuha ng GST refund ang mga turista?"],
            "my": ["လက်ရှိ GST နှုန်းက ဘယ်လောက်လဲ?", "ကျွန်ုပ်လုပ်ငန်းက GST မှတ်ပုံတင်ဖို့ လိုပါသလား?", "ခရီးသွားတွေ GST ပြန်အမ်းငွေ ဘယ်လိုတောင်းနိုင်မလဲ?"],
        },
    },
    "property": {
        "icon": "🏠",
        "name": {
            "en": "Property Tax",          "zh": "房产税",
            "ta": "சொத்து வரி",             "th": "ภาษีทรัพย์สิน",
            "vi": "Thuế bất động sản",     "id": "Pajak Properti",
            "ms": "Cukai Harta",           "fil": "Buwis sa Ari-arian",
            "my": "အိမ်ခြံမြေခွန်",
        },
        "questions": {
            "en": ["How is property tax calculated?", "What are the rates for owner-occupied homes?", "How do I pay my property tax?"],
            "zh": ["房产税是如何计算的？", "自住房屋的房产税税率是多少？", "如何缴纳房产税？"],
            "ta": ["சொத்து வரி எப்படி கணக்கிடப்படுகிறது?", "சொந்த வீட்டில் வசிப்பவர்களுக்கான வரி விகிதம் என்ன?", "சொத்து வரியை எப்படி செலுத்துவது?"],
            "th": ["ภาษีทรัพย์สินคำนวณอย่างไร?", "อัตราภาษีสำหรับบ้านที่เจ้าของอยู่เองคือเท่าไร?", "จะจ่ายภาษีทรัพย์สินได้อย่างไร?"],
            "vi": ["Thuế bất động sản được tính như thế nào?", "Thuế suất cho nhà ở chính chủ là bao nhiêu?", "Làm thế nào để nộp thuế bất động sản?"],
            "id": ["Bagaimana pajak properti dihitung?", "Berapa tarif untuk rumah yang ditempati pemilik?", "Bagaimana cara membayar pajak properti?"],
            "ms": ["Bagaimana cukai harta dikira?", "Berapakah kadar untuk rumah yang diduduki pemilik?", "Bagaimana cara membayar cukai harta?"],
            "fil": ["Paano kinakalkula ang buwis sa ari-arian?", "Magkano ang rate para sa bahay na tinitirhan ng may-ari?", "Paano magbayad ng buwis sa ari-arian?"],
            "my": ["အိမ်ခြံမြေခွန်ကို ဘယ်လိုတွက်ချက်သလဲ?", "ပိုင်ရှင်ကိုယ်တိုင်နေထိုင်သော အိမ်အတွက် အခွန်နှုန်းက ဘယ်လောက်လဲ?", "အိမ်ခြံမြေခွန်ကို ဘယ်လိုပေးဆောင်ရမလဲ?"],
        },
    },
    "stamp": {
        "icon": "📄",
        "name": {
            "en": "Stamp Duty",            "zh": "印花税",
            "ta": "முத்திரை வரி",           "th": "อากรแสตมป์",
            "vi": "Thuế trước bạ",         "id": "Bea Meterai",
            "ms": "Duti Setem",            "fil": "Stamp Duty",
            "my": "တံဆိပ်ခေါင်းခွန်",
        },
        "questions": {
            "en": ["When do I need to pay stamp duty?", "How much stamp duty do I pay when buying a home?", "What is Additional Buyer's Stamp Duty?"],
            "zh": ["什么时候需要缴纳印花税？", "买房需要缴纳多少印花税？", "什么是额外买方印花税？"],
            "ta": ["முத்திரை வரி எப்போது செலுத்த வேண்டும்?", "வீடு வாங்கும் போது எவ்வளவு முத்திரை வரி?", "கூடுதல் வாங்குபவர் முத்திரை வரி என்றால் என்ன?"],
            "th": ["ต้องจ่ายอากรแสตมป์เมื่อไหร่?", "ซื้อบ้านต้องจ่ายอากรแสตมป์เท่าไร?", "อากรแสตมป์ผู้ซื้อเพิ่มเติมคืออะไร?"],
            "vi": ["Khi nào cần nộp thuế trước bạ?", "Mua nhà phải nộp bao nhiêu thuế trước bạ?", "Thuế trước bạ bổ sung cho người mua là gì?"],
            "id": ["Kapan saya perlu membayar bea meterai?", "Berapa bea meterai untuk membeli rumah?", "Apa itu Additional Buyer's Stamp Duty?"],
            "ms": ["Bilakah saya perlu membayar duti setem?", "Berapakah duti setem untuk membeli rumah?", "Apakah Duti Setem Pembeli Tambahan?"],
            "fil": ["Kailan kailangang magbayad ng stamp duty?", "Magkano ang stamp duty sa pagbili ng bahay?", "Ano ang Additional Buyer's Stamp Duty?"],
            "my": ["တံဆိပ်ခေါင်းခွန်ကို ဘယ်အချိန်မှာ ပေးဆောင်ရမလဲ?", "အိမ်ဝယ်တဲ့အခါ တံဆိပ်ခေါင်းခွန် ဘယ်လောက်ပေးရမလဲ?", "Additional Buyer's Stamp Duty ဆိုတာ ဘာလဲ?"],
        },
    },
}


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
