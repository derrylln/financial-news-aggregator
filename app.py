import threading
import time

from flask import Flask, render_template, request, redirect, url_for, jsonify, g

import config
import aggregator
import i18n

app = Flask(__name__)
aggregator.init_db()


def background_fetcher():
    while True:
        try:
            aggregator.fetch_all(config.FEEDS)
        except Exception as e:
            print(f"[background] error: {e}")
        time.sleep(config.FETCH_INTERVAL_MINUTES * 60)


# ---------- Locale ----------
@app.before_request
def load_locale():
    lang = request.cookies.get("ui_lang", "en")
    g.lang = lang if lang in ("en", "id") else "en"


@app.route("/set_lang/<lang>")
def set_lang(lang):
    if lang not in ("en", "id"):
        lang = "en"
    # Preserve filters when returning
    target = request.referrer or url_for("index")
    resp = redirect(target)
    resp.set_cookie("ui_lang", lang, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return resp


@app.context_processor
def inject_i18n():
    lang = g.get("lang", "en")
    return {
        "t": lambda key: i18n.t(key, lang),
        "translate_category": lambda cat: i18n.translate_category(cat, lang),
        "format_date": lambda ts: i18n.format_date_ts(ts, lang),
        "lang": lang,
        "other_lang": "id" if lang == "en" else "en",
    }


# ---------- Routes ----------
@app.route("/")
def index():
    cat = request.args.get("category")
    region = request.args.get("region")
    source = request.args.get("source")
    unread = request.args.get("unread") == "1"
    search = request.args.get("q", "").strip()
    clang = request.args.get("clang")  # 'en', 'id', or None

    articles = aggregator.get_articles(
        category=cat, region=region, source=source,
        unread_only=unread, search=search or None, content_lang=clang,
    )

    for a in articles:
        blob = (a["title"] + " " + (a["summary"] or "")).lower()
        a["matches"] = [w for w in config.WATCHLIST if w.lower() in blob]
        a["priority"] = config.SOURCE_PRIORITY.get(a["source"], 0)

    with_img = [a for a in articles if a["image"]]
    without_img = [a for a in articles if not a["image"]]

    hero, side, grid = None, [], []
    if with_img:
        now_ts = int(time.time())
        fresh_cutoff = now_ts - 3 * 86400
        fresh = [a for a in with_img if a["pub_ts"] >= fresh_cutoff]
        pool = fresh if fresh else with_img
        hero = max(pool, key=lambda a: (a["pub_ts"], a["priority"]))
        side = [a for a in pool if a["id"] != hero["id"]][:2]
        side_ids = {s["id"] for s in side}
        remaining = [a for a in pool if a["id"] != hero["id"] and a["id"] not in side_ids]
        grid = remaining + [a for a in without_img if a["pub_ts"] >= fresh_cutoff]
    else:
        grid = articles

    cats, _, _ = aggregator.get_filter_options()
    stats = aggregator.get_stats()
    ticker_prices = aggregator.get_ticker_prices(config.TICKERS) 

    return render_template(
        "index.html",
        hero=hero, side=side, grid=grid, articles=articles,
        categories=cats, stats=stats, ticker_prices=ticker_prices, # <-- CHANGED
        current={"category": cat, "region": region, "source": source,
                 "unread": unread, "q": search, "clang": clang},
    )


@app.route("/refresh", methods=["POST", "GET"])
def refresh():
    new = aggregator.fetch_all(config.FEEDS)
    if request.headers.get("Accept") == "application/json":
        return jsonify({"new": new})
    return redirect(request.referrer or url_for("index"))


@app.route("/mark_read/<int:aid>", methods=["POST"])
def route_mark_read(aid):
    aggregator.mark_read(aid)
    return jsonify({"ok": True})


@app.route("/mark_all_read", methods=["POST"])
def route_mark_all_read():
    aggregator.mark_all_read()
    return redirect(request.referrer or url_for("index"))


if __name__ == "__main__":
    if aggregator.get_stats()["total"] == 0:
        print("First run — doing initial fetch...")
        aggregator.fetch_all(config.FEEDS)
    threading.Thread(target=background_fetcher, daemon=True).start()
    print("\n  ✅ Dashboard running at http://127.0.0.1:5000\n")
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)