#!/usr/bin/env python3
"""
Landing-page manifest: validate data/console-status.json and re-inline it as
the FALLBACK blob in index.html.

    python3 data/status_build.py            # validate, then re-inline
    python3 data/status_build.py --check    # validate only (exit 1 on errors)
    python3 data/status_build.py --touch    # also set generated = today

The landing renderer (index.html) reads schema v2:
  attention[]  {severity: red|amber|info, label, detail, href}   — first four render, the rest sit behind "+ more"
  kpis[]       {label, value, delta, tone, note, color, href, spark?, live?}  — six render; live:"hearing" shows computed days
  next[]       {label, date, sub, href, color}                    — the entry whose label matches /hearing/ drives the countdown
  rooms[]      {href, label, cluster, color, metric, updated, dataThrough, cadenceDays, stats[], series[], links[], ...}
               — landing shows label, freshness, metric, stats[0], series[0]; rooms keep the rest
  clusters[]   {key, title, blurb}
  annex[], quotes[], quote_stats, generated, version

readwise_status.py (run monthly by GitHub Actions) edits the same file and
re-inlines from the same `var FALLBACK = ` marker, so keep the marker and the
href-keyed entries it looks for (/readwise-highlights/).
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS = ROOT / "data" / "console-status.json"
LANDING = ROOT / "index.html"
MARKER = "var FALLBACK = "


def validate(m):
    errs, warns = [], []
    if m.get("version") != 2:
        errs.append("version must be 2")
    for k in ["generated", "attention", "kpis", "next", "rooms", "clusters", "annex", "quotes"]:
        if k not in m:
            errs.append(f"missing top-level key {k}")
    if errs:
        return errs, warns
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", m["generated"]):
        errs.append("generated must be YYYY-MM-DD")
    for i, a in enumerate(m["attention"]):
        if a.get("severity") not in ("red", "amber", "info"):
            errs.append(f"attention[{i}] severity {a.get('severity')!r}")
        for k in ("label", "detail", "href"):
            if not a.get(k):
                errs.append(f"attention[{i}] missing {k}")
    if len(m["attention"]) > 8:
        warns.append(f"{len(m['attention'])} flags — the landing shows four; consider trimming")
    if len(m["kpis"]) != 6:
        warns.append(f"{len(m['kpis'])} kpis — the landing renders exactly six")
    for i, k in enumerate(m["kpis"]):
        for f in ("label", "value", "delta", "href", "color"):
            if not k.get(f):
                errs.append(f"kpis[{i}] missing {f}")
        if k.get("spark") and len(k["spark"]) < 2:
            warns.append(f"kpis[{i}] spark has <2 points")
    if not any(re.search(r"hearing", x.get("label", ""), re.I) for x in m["next"]):
        warns.append("no next[] entry labelled 'Hearing' — the countdown card will be empty")
    for i, x in enumerate(m["next"]):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", x.get("date", "")):
            errs.append(f"next[{i}] bad date {x.get('date')!r}")
        if x.get("date", "9999") < m["generated"] and not re.search(r"hearing", x.get("label", ""), re.I):
            warns.append(f"next[{i}] '{x.get('label')}' is in the past ({x.get('date')}) — drop it or move it to attention")
    keys = {c["key"] for c in m["clusters"]}
    hrefs = set()
    for i, r in enumerate(m["rooms"]):
        for f in ("href", "label", "cluster", "color"):
            if not r.get(f):
                errs.append(f"rooms[{i}] missing {f}")
        if r.get("cluster") not in keys:
            errs.append(f"rooms[{i}] cluster {r.get('cluster')!r} not in clusters")
        if r.get("href") in hrefs:
            errs.append(f"duplicate room href {r.get('href')}")
        hrefs.add(r.get("href"))
        for f in ("updated", "dataThrough"):
            if r.get(f) and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r[f]):
                errs.append(f"rooms[{i}] {f} not YYYY-MM-DD")
        if r.get("series"):
            pts = r["series"][0].get("points", [])
            if pts and pts != sorted(pts, key=lambda p: p[0]):
                warns.append(f"rooms[{i}] series points not in date order")
    # every href should resolve to a folder in the repo (ignore the hash)
    for coll in ("attention", "kpis", "next", "rooms", "annex"):
        for x in m.get(coll, []):
            h = (x.get("href") or "").split("#")[0]
            if h.startswith("/") and h.endswith("/") and not (ROOT / h.strip("/") / "index.html").exists():
                warns.append(f"{coll}: {x.get('href')} does not resolve to a page in the repo")
            elif h.startswith("/") and not h.endswith("/") and not (ROOT / h.strip("/")).exists():
                warns.append(f"{coll}: {x.get('href')} does not resolve to a file in the repo")
    return errs, warns


def reinline(m):
    s = LANDING.read_text(encoding="utf-8")
    i = s.index(MARKER) + len(MARKER)
    _, end = json.JSONDecoder().raw_decode(s[i:])
    s = s[:i] + json.dumps(m, indent=1, ensure_ascii=False) + s[i + end:]
    LANDING.write_text(s, encoding="utf-8")
    # round-trip
    s2 = LANDING.read_text(encoding="utf-8")
    j = s2.index(MARKER) + len(MARKER)
    obj, _ = json.JSONDecoder().raw_decode(s2[j:])
    assert obj == m, "FALLBACK round-trip mismatch"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--touch", action="store_true")
    args = ap.parse_args()
    m = json.loads(STATUS.read_text(encoding="utf-8"))
    if args.touch:
        m["generated"] = date.today().isoformat()
        STATUS.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    errs, warns = validate(m)
    for w in warns:
        print("warn:", w)
    for e in errs:
        print("ERROR:", e)
    if errs:
        return 1
    if not args.check:
        reinline(m)
    print(f"status {m['generated']} · {len(m['attention'])} flags · {len(m['kpis'])} kpis · {len(m['rooms'])} rooms · {'validated' if args.check else 'FALLBACK re-inlined'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
