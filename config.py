# ============================================================
#  EDIT THIS FILE TO CUSTOMIZE YOUR FEED
# ============================================================

FETCH_INTERVAL_MINUTES = 15

# --- 1. Live Ticker Data (Yahoo Finance symbols) ---
# .JK = Jakarta Stock Exchange, ^JKSE = IHSG Index, IDR=X = USD/IDR Rate
TICKERS = {
    "IHSG": "^JKSE",
    "BBCA": "BBCA.JK",
    "BBRI": "BBRI.JK",
    "BMRI": "BMRI.JK",
    "TLKM": "TLKM.JK",
    "ASII": "ASII.JK",
    "GOTO": "GOTO.JK",
    "USD/IDR": "IDR=X",
    "Crude Oil": "CL=F",
    "Gold": "GC=F",
}

# --- 2. Keyword Highlighting (for articles) ---
# If an article title/summary contains these, it gets a yellow tag
WATCHLIST = [
    "BBCA", "BBRI", "BMRI", "TLKM", "ASII", "GOTO",
    "IHSG", "BI rate", "rupiah", "USD/IDR",
    "Fed", "inflation", "interest rate", "oil", "emas",
]

# --- 3. Source Priorities (for picking the Hero article) ---
SOURCE_PRIORITY = {
    "Bloomberg": 10,
    "Reuters": 9,
    "CNBC Indonesia — Market": 7,
    "Kontan — Investasi": 6,
    "CNBC Indonesia — News": 5,
    "Kontan — Keuangan": 5,
    "IDN Financials": 8,
}

# --- 4. News Feeds ---
FEEDS = [
    {
        "name": "Bloomberg",
        "url": "https://news.google.com/rss/search?q=when:24h+site:bloomberg.com+(markets+OR+stocks+OR+economy)&hl=en-US&gl=US&ceid=US:en",
        "category": "Global Markets",
        "region": "Global",
    },
    {
        "name": "Reuters",
        "url": "https://news.google.com/rss/search?q=when:24h+site:reuters.com+(business+OR+markets+OR+economy)&hl=en-US&gl=US&ceid=US:en",
        "category": "Global Business",
        "region": "Global",
    },
    {
        "name": "CNBC Indonesia — Market",
        "url": "https://www.cnbcindonesia.com/market/rss",
        "category": "IDX / Market",
        "region": "Indonesia",
    },
    {
        "name": "CNBC Indonesia — News",
        "url": "https://www.cnbcindonesia.com/news/rss",
        "category": "Indonesia News",
        "region": "Indonesia",
    },
    {
        "name": "Kontan — Investasi",
        "url": "https://investasi.kontan.co.id/rss",
        "category": "Indonesia Investment",
        "region": "Indonesia",
    },
    {
        "name": "Kontan — Keuangan",
        "url": "https://news.google.com/rss/search?q=when:24h+site:kontan.co.id+keuangan&hl=id&gl=ID&ceid=ID:id",
        "category": "Indonesia Finance",
        "region": "Indonesia",
    },
    {
        "name": "IDN Financials",
        "url": "https://news.google.com/rss/search?q=site:idnfinancials.com&hl=id&gl=ID&ceid=ID:id",
        "category": "IDX / Local",
        "region": "Indonesia",
    },
]