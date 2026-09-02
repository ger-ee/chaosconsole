#!/usr/bin/env python3
"""
Incremental health cache refresh for Chaos Console.

health_loader.py --force re-reads every Daily export (≈1 GB of JSON) into
memory and swap-thrashes a 16 GB machine. This script keeps the existing
data/health_cache.json and only appends AutoSync (.hae) rows dated AFTER each
dashboard metric's current coverage — the same gap-fill rule the full loader
uses, minus the re-read.

Usage:
    python3 data/health_refresh.py            # append new AutoSync days
    python3 data/health_refresh.py --dry-run  # report what would be added

Run the full loader only when a new Daily export batch lands.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_loader as hl  # noqa: E402  (reuses paths, decoders, constants)


def existing_cutoffs(rows):
    cut = {}
    for r in rows:
        day = r["timestamp"][:10]
        if day > cut.get(r["metric"], "0000-00-00"):
            cut[r["metric"]] = day
    return cut


def load_autosync_after(cutoffs):
    """Same as hl.load_autosync but skips .hae files whose filename date is
    on/before the metric cutoff, so we decode only what can add rows."""
    if not hl.AUTOSYNC_DIR.exists():
        return [], {}
    rows, day_buckets, day_units, scanned = [], defaultdict(float), {}, {}
    for metric in hl.AUTOSYNC_METRICS:
        cutoff = cutoffs.get(metric, "0000-00-00")
        folder = hl.AUTOSYNC_DIR / metric
        if not folder.exists():
            continue
        files = sorted(folder.glob("*.hae"))
        # filename is yyyymmdd.hae — keep files dated >= cutoff (a day's
        # file can contain rows for the day before, so keep the boundary)
        keep = [f for f in files if f.stem >= cutoff.replace("-", "")]
        scanned[metric] = (len(keep), keep[-1].stem if keep else None)
        for f in keep:
            doc = hl._decode_hae(f)
            if not doc or not doc.get("data"):
                continue
            for p in doc["data"]:
                start = p.get("start") or p.get("end")
                if start is None:
                    continue
                dt = hl._apple_ts(start)
                day = dt.strftime("%Y-%m-%d")
                if day <= cutoff:
                    continue
                if metric == "sleep_analysis":
                    src = "AutoSync"
                    if p.get("sources"):
                        src = p["sources"][0].get("name", "AutoSync")
                    stage_rows = []
                    for key, label in hl.SLEEP_STAGE_LABELS.items():
                        val = p.get(key)
                        if isinstance(val, (int, float)) and val > 0:
                            stage_rows.append((label, val))
                    if not stage_rows and isinstance(p.get("totalSleep"), (int, float)) and p["totalSleep"] > 0:
                        stage_rows.append(("Asleep", p["totalSleep"]))
                    for label, val in stage_rows:
                        rows.append({"timestamp": dt.isoformat(), "metric": metric, "value": round(val, 4),
                                     "unit": p.get("unit", "hr"), "source": src, "extra": {"label": label}})
                    continue
                qty = p.get("qty", p.get("Avg"))
                if not isinstance(qty, (int, float)):
                    continue
                # AutoSync emits the same body reading in kg / lb / st; the
                # dashboards read pounds, and the Daily export only ever wrote lb.
                unit = p.get("unit", "")
                if metric in ("weight_body_mass", "lean_body_mass") and unit != "lb":
                    continue
                if metric in hl.DAILY_AGG_METRICS:
                    day_buckets[(day, metric)] += qty
                    day_units[(day, metric)] = p.get("unit", "")
                else:
                    rows.append({"timestamp": dt.isoformat(), "metric": metric, "value": round(qty, 4),
                                 "unit": p.get("unit", ""), "source": "AutoSync", "extra": None})
    for (day, metric), total in sorted(day_buckets.items()):
        rows.append({"timestamp": f"{day}T00:00:00", "metric": metric, "value": round(total, 2),
                     "unit": day_units[(day, metric)], "source": "AutoSync", "extra": {"aggregation": "daily_sum"}})
    return deoverlap_sleep(rows), scanned


def deoverlap_sleep(rows):
    """Oura re-syncs write the same night several times with shifted segment
    boundaries, so raw AutoSync sleep segments sum to 20-30 h/day. Clip each
    segment to start after the previous one ends (per day + source) so the
    stage totals equal the union of covered time instead of the sum."""
    from datetime import datetime as _dt
    sleep = [r for r in rows if r["metric"] == "sleep_analysis"]
    other = [r for r in rows if r["metric"] != "sleep_analysis"]
    groups = defaultdict(list)
    for r in sleep:
        groups[(r["timestamp"][:10], r["source"], r["extra"]["label"] == "InBed")].append(r)
    out = []
    for (_, _, is_inbed), segs in groups.items():
        if is_inbed:
            out.extend(segs)
            continue
        segs.sort(key=lambda r: r["timestamp"])
        cursor = None
        for r in segs:
            s = _dt.fromisoformat(r["timestamp"]).timestamp()
            e = s + r["value"] * 3600
            s2 = s if cursor is None else max(s, cursor)
            if e - s2 > 1:
                if s2 != s:
                    r = dict(r, timestamp=_dt.fromtimestamp(s2).astimezone().isoformat())
                out.append(dict(r, value=round((e - s2) / 3600, 4)))
            cursor = e if cursor is None else max(cursor, e)
    return other + out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cache = json.loads(hl.CACHE_PATH.read_text())
    rows = cache["data"]
    cutoffs = existing_cutoffs(rows)
    print("Existing coverage:")
    for m in hl.AUTOSYNC_METRICS:
        print(f"  {m:28s} {cutoffs.get(m, '—')}")

    new_rows, scanned = load_autosync_after(cutoffs)
    seen = {(r["timestamp"], r["metric"], r["source"]) for r in rows}
    new_rows = [r for r in new_rows if (r["timestamp"], r["metric"], r["source"]) not in seen]

    added = defaultdict(int)
    newest = {}
    for r in new_rows:
        added[r["metric"]] += 1
        d = r["timestamp"][:10]
        if d > newest.get(r["metric"], ""):
            newest[r["metric"]] = d
    print("\nAutoSync scan (files kept, newest file) and rows added:")
    for m in hl.AUTOSYNC_METRICS:
        print(f"  {m:28s} files={scanned.get(m, (0, None))[0]:3d} newest={scanned.get(m, (0, None))[1]} +{added.get(m, 0)} rows → {newest.get(m, cutoffs.get(m, '—'))}")

    if args.dry_run or not new_rows:
        print("\nNothing written." if not new_rows else "\nDry run — nothing written.")
        return

    rows.extend(new_rows)
    rows.sort(key=lambda r: (r["timestamp"], r["metric"]))
    cache["data"] = rows
    cache["generated"] = datetime.now(timezone.utc).isoformat()
    src = cache.get("source_files", [])
    tag = f"AutoSync/HealthMetrics (.hae incremental refresh {datetime.now().strftime('%Y-%m-%d')})"
    if tag not in src:
        src.append(tag)
    cache["source_files"] = src
    st = cache.setdefault("stats", {})
    st["rows_after_aggregation"] = len(rows)
    st["metrics"] = sorted(set(r["metric"] for r in rows))
    st["date_range"] = {"min": rows[0]["timestamp"], "max": rows[-1]["timestamp"]}
    st["sources"] = sorted(set(r["source"] for r in rows))
    hl.CACHE_PATH.write_text(json.dumps(cache))
    print(f"\nWrote {hl.CACHE_PATH} — {len(rows):,} rows, +{len(new_rows):,} new, through {st['date_range']['max']}")


if __name__ == "__main__":
    main()
