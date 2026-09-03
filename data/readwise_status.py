#!/usr/bin/env python3
"""
Refresh the Readwise entries on the Chaos Console landing page.

Reads data/readwise_cache.json + data/reading_atlas.json, rewrites the
Readwise room, KPI tile and attention item in data/console-status.json, and
re-inlines that JSON into the FALLBACK blob in index.html (the landing page
renders from the fallback when the fetch fails).

    python3 data/readwise_status.py
"""

import json
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "data" / "readwise_cache.json"
ATLAS_PATH = ROOT / "data" / "reading_atlas.json"
STATUS_PATH = ROOT / "data" / "console-status.json"
LANDING_PATH = ROOT / "index.html"

ROOM_HREF = "/readwise-highlights/"
STALE_DAYS = 45
SERIES_MONTHS = 24


def month_key(iso: str) -> str:
    return iso[:7] if iso and len(iso) >= 7 else ""


def fmt_day(iso: str) -> str:
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return iso
    return f"{d.strftime('%b')} {d.day}"


def main():
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    atlas = json.loads(ATLAS_PATH.read_text(encoding="utf-8"))
    status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    today = date.today()
    today_iso = today.isoformat()

    hl = cache.get("data", [])
    total = len(hl)
    books = int(cache.get("stats", {}).get("total_books") or len({h.get("book_title") for h in hl}))
    generated = cache.get("generated", "")
    try:
        fetched = datetime.fromisoformat(generated).astimezone(timezone.utc).date()
    except ValueError:
        fetched = today
    age_days = (today - fetched).days
    dated = sorted(h.get("highlighted_at", "") for h in hl if h.get("highlighted_at"))
    newest = dated[-1][:10] if dated else ""

    # per-month counts for the last SERIES_MONTHS months (inclusive of the current month)
    months = []
    y, m = today.year, today.month
    for _ in range(SERIES_MONTHS):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months.reverse()
    per_month = Counter(month_key(h.get("highlighted_at", "")) for h in hl)
    series = [[mo, per_month.get(mo, 0)] for mo in months]
    spark = [n for _, n in series]

    excluded = set(atlas.get("meta", {}).get("excluded_titles", []))
    by_book = Counter(h.get("book_title") or "" for h in hl if (h.get("book_title") or "") not in excluded)
    cat = Counter(h.get("category") or "" for h in hl)
    top = by_book.most_common(2)
    meta = atlas.get("meta", {})
    themed = int(meta.get("themed", 0))
    corpus = int(meta.get("total_highlights", 0))
    n_links = int(meta.get("n_links", 0))
    n_themes = int(meta.get("n_themes", 16))
    stale = age_days > STALE_DAYS
    age_label = "pulled today" if age_days == 0 else f"{age_days} day{'s' if age_days != 1 else ''} old"

    # ---- KPI tile ----
    for k in status.get("kpis", []):
        if k.get("href") == ROOM_HREF:
            k["value"] = f"{total:,}"
            k["delta"] = f"{themed:,} themed" if not stale else f"cache {age_days}d old"
            k["tone"] = "warn" if stale else "good"
            k["note"] = f"{books} sources · {n_themes} themes · newest highlight {fmt_day(newest)}"
            k["spark"] = spark

    # ---- room card ----
    for r in status.get("rooms", []):
        if r.get("href") != ROOM_HREF:
            continue
        r["label"] = "Reading Atlas"
        r["metric"] = f"{total:,} highlights · {books} sources · {n_themes} themes"
        r["updated"] = today_iso
        r["dataThrough"] = fetched.isoformat()
        r["cadenceDays"] = 31
        r["tagline"] = "Every highlight sorted into the ideas it belongs to — sixteen themes, the books behind them, and where they meet"
        r["stats"] = [
            {"label": "Atlas", "value": f"{themed:,} themed",
             "sub": f"of {corpus:,} passages · {n_links} theme links · {meta.get('unthemed', 0):,} outside the lexicon"},
            {"label": "Most-highlighted",
             "value": f"{top[0][0][:34]} · {top[0][1]}" if top else "—",
             "sub": f"{top[1][0][:34]} · {top[1][1]} next" if len(top) > 1 else ""},
            {"label": "Library pull", "value": age_label,
             "sub": f"{fetched.strftime('%b %-d')} · {cat.get('books', 0)} book · {cat.get('supplementals', 0)} supp · "
                    f"{cat.get('articles', 0)} article · {cat.get('tweets', 0)} tweet · refreshed monthly by GitHub Action"},
        ]
        r["series"] = [{"label": "dated highlights per month", "unit": "highlights", "points": series}]
        r["links"] = [
            {"href": "/readwise-highlights/", "label": "Open the atlas"},
            {"href": "/readwise-highlights/deck/", "label": "Shuffle deck"},
        ]

    # ---- attention item ----
    att = [a for a in status.get("attention", []) if a.get("href") != ROOM_HREF]
    if stale:
        att.insert(1, {
            "severity": "amber",
            "label": f"Readwise cache is {age_days} days old",
            "detail": f"Library pulled {fetched.strftime('%b %-d')}, newest highlight {fmt_day(newest)} — "
                      "the monthly readwise-refresh workflow has not run; trigger it from the Actions tab "
                      "or run data/readwise_loader.py --force && data/atlas_build.py && data/readwise_status.py",
            "href": ROOM_HREF,
        })
    status["attention"] = att
    status["generated"] = today_iso

    out = json.dumps(status, indent=1, ensure_ascii=False) + "\n"
    STATUS_PATH.write_text(out, encoding="utf-8")

    # ---- re-inline FALLBACK in the landing page ----
    landing = LANDING_PATH.read_text(encoding="utf-8")
    marker = "var FALLBACK = "
    i = landing.index(marker) + len(marker)
    _, end = json.JSONDecoder().raw_decode(landing[i:])
    landing = landing[:i] + json.dumps(status, indent=1, ensure_ascii=False) + landing[i + end:]
    LANDING_PATH.write_text(landing, encoding="utf-8")

    print(f"status: {total:,} highlights · {books} sources · {themed:,} themed · pull {age_label}"
          f"{' · STALE' if stale else ''} → console-status.json + index.html FALLBACK")


if __name__ == "__main__":
    sys.exit(main())
