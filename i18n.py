import re
from datetime import datetime, timezone


# ---------- Language detection for article content ----------
ID_WORDS = {
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "ini", "itu",
    "tidak", "akan", "pada", "juga", "bisa", "ada", "saya", "kita",
    "kami", "mereka", "atau", "tetapi", "karena", "sudah", "belum",
    "masih", "hanya", "lebih", "sangat", "para", "oleh", "dalam",
    "terhadap", "antara", "sebagai", "tahun", "hari", "kata", "ujar",
    "menurut", "sebut", "jelas", "kepada", "setelah", "sebelum",
    "saat", "ketika", "bagi", "punya", "milik", "harus", "dapat",
    "ingin", "mau", "tahu", "lihat", "jadi", "atas", "bawah", "pun",
    "lah", "kah", "nya", "persen", "rupiah", "juta", "miliar", "triliun",
}

EN_WORDS = {
    "the", "and", "of", "to", "in", "for", "with", "this", "that",
    "not", "will", "on", "also", "can", "is", "are", "was", "were",
    "has", "have", "had", "but", "or", "from", "at", "by", "as",
    "an", "be", "it", "its", "their", "they", "we", "you", "he", "she",
    "which", "would", "could", "should", "may", "might", "must",
    "said", "says", "according", "after", "before", "when", "while",
    "percent", "million", "billion", "dollar", "market", "stock",
}


def detect_lang(title, summary=""):
    text = (title + " " + (summary or "")).lower()
    words = re.findall(r"\b[a-z]+\b", text)
    if not words:
        return "en"
    id_score = sum(1 for w in words if w in ID_WORDS)
    en_score = sum(1 for w in words if w in EN_WORDS)
    return "id" if id_score > en_score else "en"


# ---------- Translations ----------
TRANSLATIONS = {
    "en": {
        "brand_tag": "Global Markets · Indonesia · In One Place",
        "all": "All",
        "unread": "Unread",
        "refresh": "Refresh",
        "mark_all_read": "Mark All Read",
        "latest_news": "Latest News",
        "stories": "STORIES",
        "articles": "ARTICLES",
        "watchlist": "WATCHLIST",
        "search_placeholder": "Search…",
        "search_go": "GO",
        "empty_msg": "No stories match your filters yet.",
        "fetch_now": "Fetch news now",
        "footer_left": "MarketFeed · Personal financial news aggregator",
        "footer_total": "total",
        "footer_unread": "unread",
        "just_now": "just now",
        "min_ago": "{n}m ago",
        "hour_ago": "{n}h ago",
        "lang_toggle": "ID",
        "lang_toggle_title": "Switch to Indonesian",
        "translate": "Translate",
        "translate_title": "Open this article in Google Translate",
        "content_lang": "Content",
        "cat_global_markets": "Global Markets",
        "cat_global_business": "Global Business",
        "cat_idx_market": "IDX / Market",
        "cat_indonesia_news": "Indonesia News",
        "cat_indonesia_finance": "Indonesia Finance",
        "cat_indonesia_investment": "Indonesia Investment",
        "cat_idx_local": "IDX / Local",
    },
    "id": {
        "brand_tag": "Pasar Global · Indonesia · Dalam Satu Tempat",
        "all": "Semua",
        "unread": "Belum Dibaca",
        "refresh": "Muat Ulang",
        "mark_all_read": "Tandai Semua",
        "latest_news": "Berita Terbaru",
        "stories": "BERITA",
        "articles": "ARTIKEL",
        "watchlist": "PANTAUAN",
        "search_placeholder": "Cari…",
        "search_go": "CARI",
        "empty_msg": "Belum ada berita yang cocok dengan filter Anda.",
        "fetch_now": "Ambil berita sekarang",
        "footer_left": "MarketFeed · Agregator berita keuangan pribadi",
        "footer_total": "total",
        "footer_unread": "belum dibaca",
        "just_now": "baru saja",
        "min_ago": "{n}m lalu",
        "hour_ago": "{n}j lalu",
        "lang_toggle": "EN",
        "lang_toggle_title": "Ganti ke Bahasa Inggris",
        "translate": "Terjemahkan",
        "translate_title": "Buka artikel ini di Google Translate",
        "content_lang": "Konten",
        "cat_global_markets": "Pasar Global",
        "cat_global_business": "Bisnis Global",
        "cat_idx_market": "IDX / Pasar",
        "cat_indonesia_news": "Berita Indonesia",
        "cat_indonesia_finance": "Keuangan Indonesia",
        "cat_indonesia_investment": "Investasi Indonesia",
        "cat_idx_local": "IDX / Lokal",
    },
}


def t(key, lang="en"):
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)


# ---------- Category name translation ----------
CATEGORY_KEYS = {
    "Global Markets": "cat_global_markets",
    "Global Business": "cat_global_business",
    "IDX / Market": "cat_idx_market",
    "Indonesia News": "cat_indonesia_news",
    "Indonesia Finance": "cat_indonesia_finance",
    "Indonesia Investment": "cat_indonesia_investment",
    "IDX / Local": "cat_idx_local",
}


def translate_category(name, lang):
    key = CATEGORY_KEYS.get(name)
    return t(key, lang) if key else name


# ---------- Locale-aware date formatting ----------
EN_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ID_MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
             "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
EN_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ID_DAYS = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]


def format_date_ts(ts, lang="en"):
    if not ts:
        return ""
    try:
        now = datetime.now(timezone.utc)
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        delta = now - dt
    except Exception:
        return ""

    seconds = delta.total_seconds()
    if seconds < 60:
        return t("just_now", lang)
    if seconds < 3600:
        return t("min_ago", lang).format(n=int(seconds / 60))
    if seconds < 86400:
        return t("hour_ago", lang).format(n=int(seconds / 3600))

    days = EN_DAYS if lang == "en" else ID_DAYS
    if delta.days < 7:
        return f"{days[dt.weekday()]} {dt.strftime('%H:%M')}"

    months = EN_MONTHS if lang == "en" else ID_MONTHS
    if lang == "en":
        return f"{months[dt.month - 1]} {dt.day}"
    return f"{dt.day} {months[dt.month - 1]}"