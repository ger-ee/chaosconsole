#!/usr/bin/env python3
"""
Health data loader for Chaos Console.

Reads Apple Health JSON exports from the HealthAutoExport app,
deduplicates overlapping windows, aggregates high-frequency metrics
to daily sums, and writes a normalized cache file.

Usage:
    python3 data/health_loader.py              # default paths
    python3 data/health_loader.py --force      # ignore cache, rebuild
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

EXPORT_DIR = Path(
    os.environ.get(
        "HEALTH_EXPORT_DIR",
        os.path.expanduser(
            "~/Library/Mobile Documents/"
            "iCloud~com~ifunography~HealthExport/"
            "Documents/Chaos Console - Daily"
        ),
    )
)

SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_PATH = SCRIPT_DIR / "health_cache.json"
MANIFEST_PATH = SCRIPT_DIR / ".health_manifest.json"
HISTORICAL_PATH = SCRIPT_DIR / "ringconn_historical.json"

# Metrics whose per-second rows get rolled up to daily sums.
DAILY_AGG_METRICS = {
    "active_energy",
    "basal_energy_burned",
    "apple_stand_time",
    "apple_exercise_time",
    "step_count",
    "walking_running_distance",
}

# Health Auto Export's second channel: LZFSE-compressed .hae files under
# AutoSync/HealthMetrics/<metric>/<yyyymmdd>.hae. Used as a gap-filler for
# dates past each metric's Daily-export coverage (the Daily automation stalls
# when the app isn't opened; AutoSync keeps running longer).
AUTOSYNC_DIR = Path(
    os.environ.get(
        "HEALTH_AUTOSYNC_DIR",
        os.path.expanduser(
            "~/Library/Mobile Documents/"
            "iCloud~com~ifunography~HealthExport/"
            "Documents/AutoSync/HealthMetrics"
        ),
    )
)

# Only the metrics the dashboards read.
AUTOSYNC_METRICS = [
    "weight_body_mass",
    "resting_heart_rate",
    "sleep_analysis",
    "heart_rate_variability",
    "step_count",
    "blood_oxygen_saturation",
    "body_fat_percentage",
    "lean_body_mass",
]

APPLE_EPOCH = 978307200  # 2001-01-01 UTC in unix seconds

SLEEP_STAGE_LABELS = {
    "awake": "Awake",
    "core": "Core",
    "deep": "Deep",
    "rem": "REM",
    "asleep": "Asleep",
    "inBed": "InBed",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_timestamp(ts_str: str) -> str:
    """Normalize 'YYYY-MM-DD HH:MM:SS -0700' to ISO-8601."""
    ts_str = ts_str.strip()
    try:
        dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        return ts_str  # pass through if unexpected format
    return dt.isoformat()


def extract_date(iso_ts: str) -> str:
    """Pull YYYY-MM-DD from an ISO timestamp."""
    return iso_ts[:10]


def build_manifest(export_dir: Path) -> dict:
    """Map each source filename to (size, mtime) for cache invalidation."""
    manifest = {}
    for p in sorted(export_dir.glob("HealthAutoExport-*.json")):
        stat = p.stat()
        manifest[p.name] = {"size": stat.st_size, "mtime": stat.st_mtime}
    if AUTOSYNC_DIR.exists():
        for metric in AUTOSYNC_METRICS:
            for p in sorted((AUTOSYNC_DIR / metric).glob("*.hae")):
                stat = p.stat()
                manifest[f"autosync/{metric}/{p.name}"] = {"size": stat.st_size, "mtime": stat.st_mtime}
    return manifest


def cache_is_fresh(manifest: dict) -> bool:
    """Return True if cached output matches current source files."""
    if not CACHE_PATH.exists() or not MANIFEST_PATH.exists():
        return False
    try:
        old = json.loads(MANIFEST_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return False
    return old == manifest


# ---------------------------------------------------------------------------
# Core loader
# ---------------------------------------------------------------------------

def load_all_exports(export_dir: Path) -> list[dict]:
    """Read every export file and return raw metric dicts."""
    files = sorted(export_dir.glob("HealthAutoExport-*.json"))
    if not files:
        print(f"No export files found in {export_dir}", file=sys.stderr)
        sys.exit(1)

    all_metrics: list[dict] = []
    for path in files:
        print(f"  reading {path.name} ({path.stat().st_size / 1024 / 1024:.1f} MB)")
        with open(path) as f:
            data = json.load(f)
        all_metrics.extend(data["data"]["metrics"])
    return all_metrics


def normalize_and_dedupe(raw_metrics: list[dict]) -> list[dict]:
    """
    Flatten all metric data points into a common schema and deduplicate
    on (timestamp, metric, source).

    Schema:
        timestamp  — ISO-8601 with timezone
        metric     — snake_case metric name
        value      — numeric value (float)
        unit       — unit string
        source     — device/app name
        extra      — dict of additional fields (e.g. Min/Max for heart_rate,
                     value label for sleep_analysis)
    """
    seen: set[tuple[str, str, str]] = set()
    rows: list[dict] = []

    for metric_block in raw_metrics:
        name = metric_block["name"]
        unit = metric_block.get("units", "")

        for dp in metric_block.get("data", []):
            ts = parse_timestamp(dp.get("date", ""))
            # Normalize non-breaking spaces in source strings
            source = dp.get("source", "unknown").replace("\xa0", " ")

            dedup_key = (ts, name, source)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            # Extract the primary value
            if "qty" in dp:
                value = dp["qty"]
            elif "Avg" in dp:
                value = dp["Avg"]
            else:
                value = None

            # Capture extra fields that vary by metric type
            extra = {}
            if "Min" in dp:
                extra["min"] = dp["Min"]
            if "Max" in dp:
                extra["max"] = dp["Max"]
            if "Avg" in dp:
                extra["avg"] = dp["Avg"]
            if "value" in dp:
                extra["label"] = dp["value"]  # e.g. "Awake", "Core", "REM"

            rows.append(
                {
                    "timestamp": ts,
                    "metric": name,
                    "value": value,
                    "unit": unit,
                    "source": source,
                    "extra": extra if extra else None,
                }
            )

    return rows


def aggregate_daily(rows: list[dict]) -> list[dict]:
    """
    Roll up high-frequency metrics to daily sums.
    Other metrics pass through unchanged.
    """
    passthrough: list[dict] = []
    buckets: dict[tuple[str, str, str], float] = defaultdict(float)
    bucket_meta: dict[tuple[str, str, str], dict] = {}

    for row in rows:
        if row["metric"] not in DAILY_AGG_METRICS:
            passthrough.append(row)
            continue

        day = extract_date(row["timestamp"])
        key = (day, row["metric"], row["source"])
        buckets[key] += row["value"] or 0

        if key not in bucket_meta:
            bucket_meta[key] = {"unit": row["unit"]}

    for (day, metric, source), total in sorted(buckets.items()):
        passthrough.append(
            {
                "timestamp": f"{day}T00:00:00",
                "metric": metric,
                "value": round(total, 2),
                "unit": bucket_meta[(day, metric, source)]["unit"],
                "source": source,
                "extra": {"aggregation": "daily_sum"},
            }
        )

    return passthrough


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _decode_hae(path: Path):
    """Decode one .hae file (LZFSE via compression_tool, plaintext bvx- fallback)."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        r = subprocess.run(
            ["compression_tool", "-decode", "-i", str(path), "-o", tmp_path],
            capture_output=True,
        )
        if r.returncode == 0:
            try:
                return json.loads(Path(tmp_path).read_text())
            except (json.JSONDecodeError, OSError):
                pass
        raw = path.read_bytes()
        if raw.startswith(b"bvx-"):
            try:
                return json.loads(raw[raw.index(b"{"): raw.rindex(b"}") + 1])
            except (ValueError, json.JSONDecodeError):
                return None
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _apple_ts(seconds: float) -> datetime:
    return datetime.fromtimestamp(APPLE_EPOCH + seconds).astimezone()


def load_autosync(cutoffs: dict) -> list[dict]:
    """
    Read AutoSync .hae files for dashboard metrics, keeping only rows dated
    strictly AFTER that metric's Daily-export coverage (cutoffs: metric -> 'YYYY-MM-DD').
    DAILY_AGG_METRICS are pre-aggregated to daily sums here to avoid emitting
    millions of per-second rows.
    """
    if not AUTOSYNC_DIR.exists():
        return []

    rows: list[dict] = []
    day_buckets: dict = defaultdict(float)
    day_units: dict = {}

    for metric in AUTOSYNC_METRICS:
        cutoff = cutoffs.get(metric, "0000-00-00")
        folder = AUTOSYNC_DIR / metric
        if not folder.exists():
            continue
        for f in sorted(folder.glob("*.hae")):
            doc = _decode_hae(f)
            if not doc or not doc.get("data"):
                continue
            for p in doc["data"]:
                start = p.get("start") or p.get("end")
                if start is None:
                    continue
                dt = _apple_ts(start)
                day = dt.strftime("%Y-%m-%d")
                if day <= cutoff:
                    continue

                if metric == "sleep_analysis":
                    src = "AutoSync"
                    if p.get("sources"):
                        src = p["sources"][0].get("name", "AutoSync")
                    stage_rows = []
                    for key, label in SLEEP_STAGE_LABELS.items():
                        val = p.get(key)
                        if key != "totalSleep" and isinstance(val, (int, float)) and val > 0:
                            stage_rows.append((label, val))
                    if not stage_rows and isinstance(p.get("totalSleep"), (int, float)) and p["totalSleep"] > 0:
                        stage_rows.append(("Asleep", p["totalSleep"]))
                    for label, val in stage_rows:
                        rows.append({
                            "timestamp": dt.isoformat(),
                            "metric": metric,
                            "value": round(val, 4),
                            "unit": p.get("unit", "hr"),
                            "source": src,
                            "extra": {"label": label},
                        })
                    continue

                qty = p.get("qty", p.get("Avg"))
                if not isinstance(qty, (int, float)):
                    continue
                if metric in DAILY_AGG_METRICS:
                    day_buckets[(day, metric)] += qty
                    day_units[(day, metric)] = p.get("unit", "")
                else:
                    rows.append({
                        "timestamp": dt.isoformat(),
                        "metric": metric,
                        "value": round(qty, 4),
                        "unit": p.get("unit", ""),
                        "source": "AutoSync",
                        "extra": None,
                    })

    for (day, metric), total in sorted(day_buckets.items()):
        rows.append({
            "timestamp": f"{day}T00:00:00",
            "metric": metric,
            "value": round(total, 2),
            "unit": day_units[(day, metric)],
            "source": "AutoSync",
            "extra": {"aggregation": "daily_sum"},
        })

    return rows


def load_historical() -> list[dict]:
    """Load pre-normalized RingConn/Oura historical data if available."""
    if not HISTORICAL_PATH.exists():
        return []
    print(f"  loading {HISTORICAL_PATH.name}")
    with open(HISTORICAL_PATH) as f:
        hist = json.load(f)
    return hist.get("data", [])


def run(force: bool = False) -> dict:
    manifest = build_manifest(EXPORT_DIR)

    if not force and cache_is_fresh(manifest):
        print("Cache is fresh — loading from disk.")
        return json.loads(CACHE_PATH.read_text())

    print(f"Loading exports from {EXPORT_DIR}")
    raw = load_all_exports(EXPORT_DIR)

    print("Normalizing and deduplicating...")
    rows = normalize_and_dedupe(raw)

    # Merge historical RingConn data (already normalized)
    historical = load_historical()
    if historical:
        print(f"  merged {len(historical):,} historical rows")
        rows.extend(historical)

    # AutoSync gap-fill: only dates past each metric's existing coverage
    cutoffs: dict = {}
    for r in rows:
        day = r["timestamp"][:10]
        if day > cutoffs.get(r["metric"], "0000-00-00"):
            cutoffs[r["metric"]] = day
    print("Scanning AutoSync .hae channel for gap-fill...")
    autosync = load_autosync(cutoffs)
    if autosync:
        print(f"  merged {len(autosync):,} AutoSync rows past Daily-export coverage")
        rows.extend(autosync)

    before = len(rows)

    print("Aggregating high-frequency metrics to daily sums...")
    rows = aggregate_daily(rows)
    after = len(rows)

    # Deduplicate again after merge (historical rows are pre-deduped but
    # there could be overlap at the boundary)
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict] = []
    for r in rows:
        key = (r["timestamp"], r["metric"], r["source"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    rows = deduped

    # Sort by timestamp then metric
    rows.sort(key=lambda r: (r["timestamp"], r["metric"]))

    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "source_files": [k for k in manifest.keys() if not k.startswith("autosync/")]
        + (["ringconn_historical.json"] if historical else [])
        + (["AutoSync/HealthMetrics (.hae gap-fill)"] if autosync else []),
        "stats": {
            "rows_before_aggregation": before,
            "rows_after_aggregation": len(rows),
            "metrics": sorted(set(r["metric"] for r in rows)),
            "date_range": {
                "min": rows[0]["timestamp"] if rows else None,
                "max": rows[-1]["timestamp"] if rows else None,
            },
            "sources": sorted(set(r["source"] for r in rows)),
        },
        "data": rows,
    }

    print(f"Writing cache ({len(rows):,} rows)...")
    CACHE_PATH.write_text(json.dumps(output))
    MANIFEST_PATH.write_text(json.dumps(manifest))

    return output


def main():
    parser = argparse.ArgumentParser(description="Load and normalize Apple Health exports")
    parser.add_argument("--force", action="store_true", help="Rebuild even if cache is fresh")
    args = parser.parse_args()

    output = run(force=args.force)
    stats = output["stats"]

    print("\n=== Summary ===")
    print(f"  Rows:       {stats['rows_after_aggregation']:,}")
    print(f"  Metrics:    {len(stats['metrics'])}")
    print(f"  Sources:    {len(stats['sources'])}")
    print(f"  Date range: {stats['date_range']['min']}")
    print(f"              {stats['date_range']['max']}")
    print(f"  Cache:      {CACHE_PATH}")


if __name__ == "__main__":
    main()
