#!/usr/bin/env python3
"""
Render the site headlessly and fail on any page error.

    python3 data/render_check.py                       # landing + every room's index.html
    python3 data/render_check.py index.html the-ledger/index.html
    python3 data/render_check.py --out /tmp/shots --widths 1440,400

Serves the repo root on a local port, opens each page in headless Chromium
(Playwright), bypasses the client-side gate, clicks every `.tab` button it
finds (the Ledger's views), forces reveal animations, takes a full-page
screenshot per page and width, and reports `pageerror` events. Exit 1 if any
page raised. Look at the screenshots — a page can be error-free and wrong.

Requires: pip install playwright && python -m playwright install chromium
(in the Cowork cloud container Playwright is preinstalled).
Set CC_BROWSER_CHANNEL=chrome to use an existing desktop Chrome installation. External fonts and
CDNs are not needed: every page loads Chart.js from shared/vendor/.
"""
import argparse
import os
import asyncio
import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"gary-dashboard", ".claude", ".codex", ".git", "data", "shared", "fonts", "wellness-analysis"}


def all_pages():
    # Threshold's route inventory includes nested chapters and standalone tools.
    routes = ROOT / "shared" / "threshold" / "routes.js"
    if routes.exists():
        records = json.loads(routes.read_text().split(" = ", 1)[1].strip().rstrip(";"))
        return ["index.html"] + [r["path"].lstrip("/") + ("index.html" if r["path"].endswith("/") else "") for r in records]
    pages = ["index.html"]
    for p in sorted(ROOT.iterdir()):
        if p.is_dir() and p.name not in SKIP and (p / "index.html").exists():
            pages.append(f"{p.name}/index.html")
    return pages


def serve():
    handler = http.server.SimpleHTTPRequestHandler

    class Quiet(handler):
        def log_message(self, *a):  # noqa: D401
            pass

        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(ROOT), **kw)

    srv = socketserver.TCPServer(("127.0.0.1", 0), Quiet)
    srv.allow_reuse_address = True
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, srv.server_address[1]


async def run(pages, widths, out):
    from playwright.async_api import async_playwright
    srv, port = serve()
    out.mkdir(parents=True, exist_ok=True)
    failures = 0
    async with async_playwright() as p:
        browser = await p.chromium.launch(**({"channel": os.environ["CC_BROWSER_CHANNEL"]} if os.environ.get("CC_BROWSER_CHANNEL") else {}))
        for path in pages:
            for w in widths:
                ctx = await browser.new_context(viewport={"width": w, "height": 1000})
                await ctx.add_init_script("try{sessionStorage.setItem('cc_gate_v2','ok')}catch(e){}")
                page = await ctx.new_page()
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)))
                try:
                    await page.goto(f"http://127.0.0.1:{port}/{path}", wait_until="networkidle", timeout=45000)
                except Exception as e:  # noqa: BLE001
                    errs.append(f"goto: {e}")
                await page.wait_for_timeout(1500)
                tabs = await page.eval_on_selector_all(".tab[data-view]", "els => els.map(e => e.dataset.view)")
                for t in tabs:
                    try:
                        await page.eval_on_selector(f'.tab[data-view="{t}"]', "el => { const d = el.closest('details'); if (d) d.open = true; }")
                        await page.click(f'.tab[data-view="{t}"]', timeout=5000)
                        await page.wait_for_timeout(900)
                    except Exception as e:  # noqa: BLE001
                        errs.append(f"tab {t}: {e}")
                if "overview" in tabs:
                    await page.click('.tab[data-view="overview"]')
                    await page.wait_for_timeout(300)
                    await page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
                await page.evaluate("() => document.querySelectorAll('[data-reveal]').forEach(e => { e.classList.add('in'); e.classList.add('revealed'); })")
                await page.wait_for_timeout(400)
                name = ("landing" if path == "index.html" else path.replace("/index.html", "").replace("/", "_")) + f"_{w}.png"
                await page.screenshot(path=str(out / name), full_page=True)
                status = "ok" if not errs else "FAIL"
                print(f"{status:4} {path:<45} {w:>4}px  tabs={len(tabs)}  → {out / name}")
                for e in errs:
                    print("      ", e[:300])
                failures += bool(errs)
                await ctx.close()
        await browser.close()
    srv.shutdown()
    return failures


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pages", nargs="*")
    ap.add_argument("--widths", default="1440,400")
    ap.add_argument("--out", default="/tmp/chaosconsole-shots")
    args = ap.parse_args()
    try:
        import playwright  # noqa: F401
    except ImportError:
        print("Playwright is not installed here: pip install playwright && python3 -m playwright install chromium", file=sys.stderr)
        return 2
    pages = args.pages or all_pages()
    widths = [int(x) for x in args.widths.split(",")]
    failures = asyncio.run(run(pages, widths, Path(args.out)))
    print(f"{len(pages)} pages × {len(widths)} widths · {failures} with errors")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
