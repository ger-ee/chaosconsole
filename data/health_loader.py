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
import sys
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

# Metrics whose per-second rows get rolled up to daily sums.
DAILY_AGG_METRICS = {
    "active_energy",
    "basal_energy_burned",
    "apple_stand_time",
    "apple_exercise_time",
    "step_count",
    "walking_running_distance",
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
    """Map each JSON filename to (size, mtime) for cache invalidation."""
    manifest = {}
    for p in sorted(export_dir.glob("HealthAutoExport-*.json")):
        stat = p.stat()
        manifest[p.name] = {"size": stat.st_size, "mtime": stat.st_mtime}
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

def run(force: bool = False) -> dict:
    manifest = build_manifest(EXPORT_DIR)

    if not force and cache_is_fresh(manifest):
        print("Cache is fresh — loading from disk.")
        return json.loads(CACHE_PATH.read_text())

    print(f"Loading exports from {EXPORT_DIR}")
    raw = load_all_exports(EXPORT_DIR)

    print("Normalizing and deduplicating...")
    rows = normalize_and_dedupe(raw)
    before = len(rows)

    print("Aggregating high-frequency metrics to daily sums...")
    rows = aggregate_daily(rows)
    after = len(rows)

    # Sort by timestamp then metric
    rows.sort(key=lambda r: (r["timestamp"], r["metric"]))

    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "source_files": list(manifest.keys()),
        "stats": {
            "rows_before_aggregation": before,
            "rows_after_aggregation": after,
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
