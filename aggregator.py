import sqlite3
import re
import html
import feedparser
import requests
import time
import yfinance as yf
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import i18n

DB_PATH = "news.db"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PersonalNewsAggregator/1.0)"}


# ---------- Database ----------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT NOT NULL,
            category    TEXT,
            region      TEXT,
            title       TEXT NOT NULL,
            link        TEXT NOT NULL UNIQUE,
            summary     TEXT,
            image       TEXT,
            image_tried INTEGER DEFAULT 0,
            published   TEXT,
            pub_ts      INTEGER DEFAULT 0,
            lang        TEXT DEFAULT 'en',
            fetched_at  TEXT NOT NULL,
            read        INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_pub_ts ON articles(pub_ts DESC);
    """)
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(articles)")]
    if "image" not in cols:
        conn.execute("ALTER TABLE articles ADD COLUMN image TEXT")
    if "image_tried" not in cols:
        conn.execute("ALTER TABLE articles ADD COLUMN image_tried INTEGER DEFAULT 0")
    if "pub_ts" not in cols:
        conn.execute("ALTER TABLE articles ADD COLUMN pub_ts INTEGER DEFAULT 0")
        rows = conn.execute("SELECT id, published FROM articles").fetchall()
        for r in rows:
            try:
                dt = parsedate_to_datetime(r["published"])
                conn.execute("UPDATE articles SET pub_ts = ? WHERE id = ?",
                             (int(dt.timestamp()), r["id"]))
            except Exception:
                pass
    if "lang" not in cols:
        conn.execute("ALTER TABLE articles ADD COLUMN lang TEXT DEFAULT 'en'")
        rows = conn.execute("SELECT id, title, summary FROM articles").fetchall()
        for r in rows:
            detected = i18n.detect_lang(r["title"], r["summary"])
            conn.execute("UPDATE articles SET lang = ? WHERE id = ?",
                         (detected, r["id"]))
    conn.commit()
    conn.close()


# ---------- Helpers ----------
def clean_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def normalize(title):
    return re.sub(r"[^a-z0-9]", "", title.lower())


def parse_published(entry):
    raw = entry.get("published") or entry.get("updated") or ""
    if not raw:
        return "", 0
    try:
        dt = parsedate_to_datetime(raw)
        return dt.strftime("%b %d, %H:%M"), int(dt.timestamp())
    except Exception:
        pass
    try:
        struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if struct:
            dt = datetime(*struct[:6], tzinfo=timezone.utc)
            return dt.strftime("%b %d, %H:%M"), int(dt.timestamp())
    except Exception:
        pass
    return str(raw)[:20], 0


def is_duplicate(conn, title, link):
    if conn.execute("SELECT 1 FROM articles WHERE link = ?", (link,)).fetchone():
        return True
    cutoff = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    rows = conn.execute(
        "SELECT title FROM articles WHERE fetched_at > ?", (cutoff,)
    ).fetchall()
    norm_new = normalize(title)
    for row in rows:
        if SequenceMatcher(None, norm_new, normalize(row["title"])).ratio() > 0.9:
            return True
    return False


def extract_image_from_entry(entry):
    thumbs = entry.get("media_thumbnail", [])
    if thumbs:
        url = thumbs[0].get("url")
        if url:
            return url
    for m in entry.get("media_content", []):
        if m.get("medium") == "image" or m.get("type", "").startswith("image"):
            url = m.get("url")
            if url:
                return url
    for e in entry.get("enclosures", []):
        if e.get("type", "").startswith("image"):
            return e.get("href") or e.get("url")
    html_blob = entry.get("summary", "") or ""
    contents = entry.get("content") or []
    if contents and isinstance(contents, list):
        html_blob += contents[0].get("value", "")
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_blob)
    return m.group(1) if m else None


def scrape_og_image(url):
    try:
        r = requests.get(url, timeout=6, headers=HEADERS, stream=True,
                         allow_redirects=True, verify=False)
        buf = b""
        for chunk in r.iter_content(8192):
            buf += chunk
            if len(buf) > 120_000 or b"</head>" in buf.lower():
                break
        r.close()
        text = buf.decode("utf-8", errors="ignore")
        for p in (
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
        ):
            m = re.search(p, text, re.I)
            if m:
                return m.group(1)
        return None
    except Exception:
        return None


def fetch_missing_images(conn, limit=120, workers=10):
    rows = conn.execute(
        "SELECT id, link FROM articles WHERE image IS NULL AND image_tried = 0 "
        "ORDER BY pub_ts DESC LIMIT ?", (limit,)
    ).fetchall()
    if not rows:
        return 0

    def _worker(row):
        return row["id"], scrape_og_image(row["link"])

    found = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_worker, r) for r in rows]
        for fut in as_completed(futures):
            try:
                aid, img = fut.result()
                if img:
                    conn.execute(
                        "UPDATE articles SET image = ?, image_tried = 1 WHERE id = ?",
                        (img, aid))
                    found += 1
                else:
                    conn.execute(
                        "UPDATE articles SET image_tried = 1 WHERE id = ?", (aid,))
            except Exception:
                pass
    conn.commit()
    return found


def _fetch_url(url):
    try:
        resp = requests.get(url, timeout=12, headers=HEADERS, verify=False)
        resp.raise_for_status()
        return feedparser.parse(resp.content)
    except Exception as e:
        print(f"    feed error [{url}]: {e}")
        return feedparser.parse(b"")


def fetch_feed(feed):
    parsed = _fetch_url(feed["url"])
    if not parsed.entries and feed.get("fallback"):
        parsed = _fetch_url(feed["fallback"])

    out = []
    for entry in parsed.entries:
        title = clean_html(entry.get("title", ""))
        link = entry.get("link", "").strip()
        if not title or not link:
            continue
        summary = clean_html(entry.get("summary", entry.get("description", "")))[:600]
        display_date, pub_ts = parse_published(entry)
        out.append({
            "source": feed["name"],
            "category": feed.get("category", "General"),
            "region": feed.get("region", "Global"),
            "title": title,
            "link": link,
            "summary": summary,
            "image": extract_image_from_entry(entry),
            "published": display_date,
            "pub_ts": pub_ts,
            "lang": i18n.detect_lang(title, summary),
        })
    out.sort(key=lambda a: a["pub_ts"], reverse=True)
    return out


def fetch_all(feeds):
    conn = get_conn()
    total_new = 0
    print(f"[{datetime.now():%H:%M:%S}] Fetching {len(feeds)} feeds...")
    for feed in feeds:
        articles = fetch_feed(feed)
        added = 0
        for a in articles:
            if is_duplicate(conn, a["title"], a["link"]):
                continue
            cur = conn.execute("""
                INSERT OR IGNORE INTO articles
                (source, category, region, title, link, summary, image,
                 image_tried, published, pub_ts, lang, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                a["source"], a["category"], a["region"], a["title"], a["link"],
                a["summary"], a["image"], 1 if a["image"] else 0,
                a["published"], a["pub_ts"], a["lang"],
                datetime.now(timezone.utc).isoformat(),
            ))
            if cur.rowcount > 0:
                added += 1
        conn.commit()
        print(f"    {feed['name']}: +{added} new")
        total_new += added
    print("    Scraping missing thumbnails...")
    got = fetch_missing_images(conn)
    print(f"    => {got} thumbnail(s) scraped")
    conn.close()
    print(f"    => {total_new} new article(s) total.")
    return total_new


# ---------- Queries ----------
def get_articles(category=None, region=None, source=None,
                 unread_only=False, search=None, content_lang=None, limit=300):
    conn = get_conn()
    q = "SELECT * FROM articles WHERE 1=1"
    params = []
    if category:
        q += " AND category = ?"; params.append(category)
    if region:
        q += " AND region = ?"; params.append(region)
    if source:
        q += " AND source = ?"; params.append(source)
    if unread_only:
        q += " AND read = 0"
    if search:
        q += " AND (title LIKE ? OR summary LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if content_lang in ("en", "id"):
        q += " AND lang = ?"; params.append(content_lang)
    q += " ORDER BY pub_ts DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_filter_options():
    conn = get_conn()
    cats = [r["category"] for r in conn.execute(
        "SELECT DISTINCT category FROM articles WHERE category IS NOT NULL ORDER BY category")]
    regs = [r["region"] for r in conn.execute(
        "SELECT DISTINCT region FROM articles WHERE region IS NOT NULL ORDER BY region")]
    srcs = [r["source"] for r in conn.execute(
        "SELECT DISTINCT source FROM articles ORDER BY source")]
    conn.close()
    return cats, regs, srcs


def get_stats():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) AS c FROM articles").fetchone()["c"]
    unread = conn.execute("SELECT COUNT(*) AS c FROM articles WHERE read = 0").fetchone()["c"]
    conn.close()
    return {"total": total, "unread": unread}


def get_watchlist_counts(watchlist):
    if not watchlist:
        return {}
    conn = get_conn()
    like_clause = " OR ".join(["title LIKE ? OR summary LIKE ?"] * len(watchlist))
    params = []
    for w in watchlist:
        params.extend([f"%{w}%", f"%{w}%"])
    rows = conn.execute(
        f"SELECT title, summary FROM articles WHERE read = 0 AND ({like_clause})",
        params,
    ).fetchall()
    conn.close()
    counts = {}
    for w in watchlist:
        wl = w.lower()
        counts[w] = sum(
            1 for r in rows
            if wl in (r["title"] + " " + (r["summary"] or "")).lower()
        )
    return counts


def mark_read(article_id, read=True):
    conn = get_conn()
    conn.execute("UPDATE articles SET read = ? WHERE id = ?",
                 (1 if read else 0, article_id))
    conn.commit()
    conn.close()


def mark_all_read():
    conn = get_conn()
    conn.execute("UPDATE articles SET read = 1")
    conn.commit()
    conn.close()


# ---------- Ticker Prices ----------
_ticker_cache = {}
_ticker_cache_time = 0

def get_ticker_prices(tickers_dict, cache_ttl=300):
    global _ticker_cache, _ticker_cache_time
    now = time.time()
    
    if now - _ticker_cache_time < cache_ttl and _ticker_cache:
        return _ticker_cache

    prices = {}
    try:
        symbols = list(tickers_dict.values())
        df = yf.download(symbols, period="5d", interval="1d", progress=False)
        
        if len(symbols) == 1:
            closes = df['Close'].dropna()
            name = list(tickers_dict.keys())[0]
            if len(closes) >= 2:
                prev, curr = closes.iloc[-2], closes.iloc[-1]
                prices[name] = {"price": round(curr, 2), "change": round(((curr - prev) / prev) * 100, 2)}
        else:
            if 'Close' in df:
                close_df = df['Close']
                for name, symbol in tickers_dict.items():
                    if symbol in close_df:
                        closes = close_df[symbol].dropna()
                        if len(closes) >= 2:
                            prev, curr = closes.iloc[-2], closes.iloc[-1]
                            prices[name] = {"price": round(curr, 2), "change": round(((curr - prev) / prev) * 100, 2)}
                        elif len(closes) == 1:
                            curr = closes.iloc[-1]
                            prices[name] = {"price": round(curr, 2), "change": 0.0}
    except Exception as e:
        print(f"Ticker fetch error: {e}")
        return _ticker_cache

    if prices:
        _ticker_cache = prices
        _ticker_cache_time = now
        
    return prices