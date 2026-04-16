#!/usr/bin/env python3
"""
Readwise highlights loader for Chaos Console.

Fetches all highlights + book metadata from Readwise API v2,
normalizes into a flat cache file for the frontend.

Setup:
    1. Get your token from https://readwise.io/access_token
    2. Create data/.env with: READWISE_TOKEN=your_token_here
    3. Run: python3 data/readwise_loader.py

Usage:
    python3 data/readwise_loader.py              # fetch if stale (>7 days)
    python3 data/readwise_loader.py --force      # force re-fetch
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_PATH = SCRIPT_DIR / "readwise_cache.json"
MANIFEST_PATH = SCRIPT_DIR / ".readwise_manifest.json"
ENV_PATH = SCRIPT_DIR / ".env"

API_BASE = "https://readwise.io/api/v2"
STALE_SECONDS = 7 * 86400  # 7 days

# ---------------------------------------------------------------------------
# .env loader (minimal, no dependency)
# ---------------------------------------------------------------------------

def load_env():
    """Read key=value pairs from data/.env into os.environ."""
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def get_token() -> str:
    load_env()
    token = os.environ.get("READWISE_TOKEN", "")
    if not token:
        print(
            "Missing READWISE_TOKEN.\n"
            "  1. Get your token: https://readwise.io/access_token\n"
            "  2. Create data/.env with: READWISE_TOKEN=<your token>",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_get(path: str, token: str, params: dict | None = None) -> dict:
    """GET a Readwise API endpoint, handle rate limits."""
    url = f"{API_BASE}/{path.lstrip('/')}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        if qs:
            url += f"?{qs}"

    req = Request(url, headers={"Authorization": f"Token {token}"})

    for attempt in range(5):
        try:
            with urlopen(req) as resp:
                return json.loads(resp.read())
        except HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After", 30))
                print(f"  rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("Exceeded retry limit on rate-limited endpoint")


def fetch_all_pages(path: str, token: str, page_size: int = 1000) -> list[dict]:
    """Paginate through a Readwise list endpoint."""
    results: list[dict] = []
    page = 1
    while True:
        data = api_get(path, token, {"page_size": page_size, "page": page})
        batch = data.get("results", [])
        results.extend(batch)
        print(f"  page {page}: {len(batch)} items (total: {len(results)})")
        if not data.get("next"):
            break
        page += 1
    return results


# ---------------------------------------------------------------------------
# Cache freshness
# ---------------------------------------------------------------------------

def cache_is_fresh() -> bool:
    if not CACHE_PATH.exists() or not MANIFEST_PATH.exists():
        return False
    try:
        manifest = json.loads(MANIFEST_PATH.read_text())
        fetched_at = datetime.fromisoformat(manifest["fetched_at"])
        age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
        return age < STALE_SECONDS
    except (json.JSONDecodeError, KeyError, OSError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Core loader
# ---------------------------------------------------------------------------

def run(force: bool = False) -> dict:
    if not force and cache_is_fresh():
        print("Cache is fresh (<7 days) — loading from disk.")
        return json.loads(CACHE_PATH.read_text())

    token = get_token()

    # Validate token
    try:
        req = Request(f"{API_BASE}/auth/", headers={"Authorization": f"Token {token}"})
        with urlopen(req) as resp:
            if resp.status != 204:
                print(f"Auth check returned {resp.status}", file=sys.stderr)
                sys.exit(1)
    except HTTPError as e:
        print(f"Auth failed: {e.code} — check your READWISE_TOKEN", file=sys.stderr)
        sys.exit(1)
    print("Token validated.")

    # Fetch books (for title/author metadata)
    print("Fetching books...")
    raw_books = fetch_all_pages("books/", token)
    book_map: dict[int, dict] = {}
    for b in raw_books:
        book_map[b["id"]] = {
            "title": b.get("title", ""),
            "author": b.get("author", ""),
            "category": b.get("category", ""),
            "source_url": b.get("source_url", ""),
            "cover_image_url": b.get("cover_image_url", ""),
        }
    print(f"  {len(book_map)} books indexed.")

    # Fetch highlights
    print("Fetching highlights...")
    raw_highlights = fetch_all_pages("highlights/", token)
    print(f"  {len(raw_highlights)} highlights fetched.")

    # Normalize
    highlights: list[dict] = []
    for h in raw_highlights:
        text = (h.get("text") or "").strip()
        if not text:
            continue

        book = book_map.get(h.get("book_id", 0), {})

        highlights.append({
            "text": text,
            "note": (h.get("note") or "").strip(),
            "book_title": book.get("title", ""),
            "author": book.get("author", ""),
            "category": book.get("category", ""),
            "source_url": book.get("source_url", ""),
            "highlighted_at": h.get("highlighted_at", ""),
            "color": h.get("color", ""),
            "readwise_url": h.get("readwise_url") or h.get("url", ""),
        })

    # Sort by highlight date (newest first)
    highlights.sort(key=lambda h: h["highlighted_at"] or "", reverse=True)

    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total_highlights": len(highlights),
            "total_books": len(book_map),
            "categories": sorted(set(h["category"] for h in highlights if h["category"])),
        },
        "data": highlights,
    }

    print(f"Writing cache ({len(highlights)} highlights)...")
    CACHE_PATH.write_text(json.dumps(output, ensure_ascii=False))
    MANIFEST_PATH.write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }))

    return output


def main():
    parser = argparse.ArgumentParser(description="Fetch Readwise highlights")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if cache is fresh")
    args = parser.parse_args()

    output = run(force=args.force)
    stats = output["stats"]

    print("\n=== Summary ===")
    print(f"  Highlights: {stats['total_highlights']}")
    print(f"  Books:      {stats['total_books']}")
    print(f"  Categories: {', '.join(stats['categories'])}")
    print(f"  Cache:      {CACHE_PATH}")


if __name__ == "__main__":
    main()
