#!/usr/bin/env python3
"""Apply/check app metadata on the landing page, install guide and routed rooms.

Run after a room generator replaces its HTML. Does not modify room content.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEAD = '''<!-- ChaosConsole app -->
<link rel="manifest" href="/manifest.webmanifest">
<meta name="application-name" content="ChaosConsole">
<meta name="apple-mobile-web-app-title" content="ChaosConsole">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="#211018">
<link rel="apple-touch-icon" sizes="180x180" href="/shared/app/icons/monogram-v2-180.png">
<link rel="icon" type="image/png" sizes="192x192" href="/shared/app/icons/monogram-v2-192.png">
<link rel="stylesheet" href="/shared/app/app.css">
<script defer src="/shared/app/app.js"></script>
<!-- /ChaosConsole app -->
'''


def pages():
    routes = json.loads((ROOT / 'shared/threshold/routes.js').read_text().split(' = ', 1)[1].strip().rstrip(';'))
    return ['index.html', 'install/index.html'] + [r['path'].lstrip('/') + ('index.html' if r['path'].endswith('/') else '') for r in routes]


def transform(text, path):
    text = re.sub(r'<!-- ChaosConsole app -->.*?<!-- /ChaosConsole app -->\n?', '', text, flags=re.S)
    # One theme color per page; the app owns browser chrome.
    text = re.sub(r'<meta\s+name=["\x27]theme-color["\x27][^>]*>\s*', '', text, flags=re.I)
    text = text.replace('</head>', HEAD + '</head>', 1)
    if path == 'index.html':
        text = text.replace('<title>Chaos Console — Threshold</title>', '<title>ChaosConsole</title>')
        if 'class="cc-install-link"' not in text:
            text = text.replace('<footer class="footerbar">', '<footer class="footerbar"><a class="cc-install-link" data-browser-only href="/install/">Get the app ↗</a>', 1)
    # Opt into display cutout space; shared CSS provides the safe insets.
    text = re.sub(r'(<meta\s+name="viewport"\s+content=")([^"]+)(")', lambda m: m[1] + m[2] + ('' if 'viewport-fit=' in m[2] else ',viewport-fit=cover') + m[3], text, count=1)
    return text


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    stale = []
    for name in pages():
        p = ROOT / name
        before = p.read_text()
        after = transform(before, name)
        if before != after:
            stale.append(name)
            if not args.check:
                p.write_text(after)
    if args.check and stale:
        raise SystemExit('App metadata needs rebuilding: ' + ', '.join(stale))
    print(f'App metadata {"checked" if args.check else "applied"}: {len(pages())} pages')
