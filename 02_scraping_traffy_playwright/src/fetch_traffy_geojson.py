"""
Task 02 data backfill: BMA Traffy Fondue complaints via the public RPC feed.

The interactive Playwright scraper is rubric evidence; this script guarantees
complete spatial coverage. Verified API facts (2026-11-12):
  - old publicapi GeoJSON URL 308-redirects to api.traffy.in.th/postgrest/rpc
  - the CSV dump URL is 404
  - p_limit is capped at 2000; p_offset paginates successfully
  - `total` undercounts (7,085 vs 10,503 actual for 2026-08-25..31), so loop
    until an empty page instead of trusting `total`
  - `problem_type` combined with `start`/`end` returns zero features, so filter
    categories client-side
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMERA_PATH = PROJECT_ROOT / "Dataset_Clean_V1" / "cctv_info_cleaned.parquet"
CACHE_DIR = PROJECT_ROOT / "data" / "raw_traffy_cache" / "pages"
WINDOWS_PATH = PROJECT_ROOT / "data" / "raw_traffy_cache" / "windows.json"
INCIDENT_PATH = PROJECT_ROOT / "data" / "traffy_complaints_near_cctv.parquet"
COUNTS_PATH = PROJECT_ROOT / "data" / "traffy_camera_counts.parquet"
SUMMARY_PATH = PROJECT_ROOT / "data" / "scraping_summary_02.json"
PROVENANCE_PATH = PROJECT_ROOT / "data" / "traffy_provenance.json"
CATEGORY_MAP_PATH = Path(__file__).with_name("category_map.json")

API_URL = "https://api.traffy.in.th/postgrest/rpc/get_bkk_geojson_feed"
USER_AGENT = "bkk-pulse-course-project/1.0 (Chulalongkorn DSDE)"
PAGE_LIMIT = 2000
MAX_PAGES = 2000
MATCH_RADIUS_M = 1000.0

DEFAULT_START = "2026-05-01"
DEFAULT_END = "2026-10-31"
WEEK_START = "2026-08-25"
WEEK_END = "2026-08-31 23:59:59"

_TYPE_MAP = json.loads(CATEGORY_MAP_PATH.read_text(encoding="utf-8"))
_TAG_BUCKETS: dict[str, str] = _TYPE_MAP["tags"]
_DEFAULT_BUCKET: str = _TYPE_MAP["default"]

PAGE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})_(\d+)\.json\.gz$")

# Largest legitimate gap in the 2026-05..10 feed is 3.05 h (a quiet night); the
# 2026-09-25 truncation was 13.6 h. Anything longer means a fetch stopped early.
MAX_GAP_HOURS = 6.0


class IncompleteWindow(RuntimeError):
    """The crawl stopped before an empty page, so the data is a prefix of the window."""


@dataclass(frozen=True)
class Complaint:
    ticket_id: str
    lat: float
    lon: float
    timestamp: pd.Timestamp | None
    type_raw: str
    problem_type: str
    description: str
    status: str


def _tags(raw_type: str) -> list[str]:
    return [part.strip() for part in str(raw_type).split(",") if part.strip()]


def classify(raw_type: str) -> str:
    """Map a Traffy problem type onto flood / traffic / other."""
    buckets = {_TAG_BUCKETS.get(tag, _DEFAULT_BUCKET) for tag in _tags(raw_type)}
    if "flood" in buckets:
        return "flood"
    if "traffic" in buckets:
        return "traffic"
    return _DEFAULT_BUCKET


def unmatched_tags(raw_series: pd.Series) -> dict[str, int]:
    """Return the comma-split tags the map does not know, with their counts."""
    counts = Counter(tag for raw in raw_series for tag in _tags(raw))
    return {tag: count for tag, count in counts.items() if tag not in _TAG_BUCKETS}


def _page_path(start: str, end: str, offset: int) -> Path:
    return CACHE_DIR / f"{start}_{end}_{offset:07d}.json.gz"


def _request_page(start: str, end: str, offset: int, attempts: int = 15) -> list[dict]:
    params = {
        "output_format": "json",
        "start": start,
        "end": end,
        "p_limit": str(PAGE_LIMIT),
        "p_offset": str(offset),
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise RuntimeError(f"unexpected payload: {str(payload)[:200]}")
            if "features" not in payload:
                raise RuntimeError(
                    f"payload without features at offset {offset}: keys={sorted(payload)[:8]}"
                )
            # Sustained request bursts trigger 503s; pace successful pages too.
            time.sleep(10.0)
            return payload["features"] or []
        except urllib.error.HTTPError as exc:
            # 429/503 -> exponential backoff up to two minutes.
            wait = min(120, 5 * (2**min(attempt, 5))) + attempt
            print(f"[traffy] HTTP {exc.code} at offset {offset}; retry in {wait}s")
            time.sleep(wait)
        except (urllib.error.URLError, TimeoutError) as exc:
            wait = min(120, 5 * (2**min(attempt, 5))) + attempt
            print(f"[traffy] {type(exc).__name__} at offset {offset}; retry in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Traffy page failed after retries: offset={offset}")


def _compact(feature: dict) -> tuple[dict | None, str | None]:
    props = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates") or []
    ticket_id = str(props.get("ticket_id") or "").strip()
    if not ticket_id:
        return None, "no_id"
    if len(coords) < 2:
        return None, "no_coords"
    timestamp = props.get("timestamp")
    return {
        "ticket_id": ticket_id,
        "lon": float(coords[0]),
        "lat": float(coords[1]),
        "timestamp": timestamp,
        "type_raw": str(props.get("type") or ""),
        "description": str(props.get("description") or ""),
        "status": str(props.get("state") or ""),
    }, None


def load_page(
    start: str,
    end: str,
    offset: int,
    refresh: bool,
    dropped: dict[str, int],
    attempts: int = 15,
) -> list[dict]:
    path = _page_path(start, end, offset)
    if path.exists() and not refresh:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)

    features = _request_page(start, end, offset, attempts=attempts)
    compact = []
    for feature in features:
        record, reason = _compact(feature)
        if record is None:
            dropped[reason] += 1
        else:
            compact.append(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(path.name + ".tmp")
    with gzip.open(staging, "wt", encoding="utf-8") as handle:
        json.dump(compact, handle, ensure_ascii=False)
    os.replace(staging, path)
    return compact


def fetch_complaints(
    start: str,
    end: str,
    refresh: bool = False,
    max_pages: int = MAX_PAGES,
    fail_on_throttle: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """Page through the feed until an empty page, then dedupe by ticket id."""
    records: dict[str, dict] = {}
    dropped = {"no_id": 0, "no_coords": 0}
    offset = 0
    pages = 0
    termination = "max_pages"
    for page in range(max_pages):
        try:
            # Once a cached prefix exists, do not stall the whole pipeline on a throttled API.
            batch = load_page(
                start, end, offset, refresh, dropped, attempts=8 if records else 15
            )
        except RuntimeError as exc:
            if not records or fail_on_throttle:
                raise
            print(f"[traffy] {exc}; keeping cached prefix ({len(records):,} records)")
            termination = "error_prefix"
            break
        if not batch:
            print(f"[traffy] stopped at offset {offset} after {page} non-empty pages")
            termination = "empty_page"
            break
        for record in batch:
            records.setdefault(record["ticket_id"], record)
        print(f"[traffy] offset {offset:>6} +{len(batch):>4} = {len(records):>6} unique")
        offset += len(batch)
        pages += 1
        if len(batch) < PAGE_LIMIT:
            # Probe one more offset; `total` is unreliable so stop on empty only.
            continue
    else:
        # --max-pages cap reached: use the cached prefix instead of hammering a throttled API.
        print(f"[traffy] stopped at --max-pages={max_pages} with {len(records):,} cached records")

    frame = pd.DataFrame(records.values())
    if frame.empty:
        raise RuntimeError("Traffy fetch returned no records")

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    dropped["null_timestamp"] = int(frame["timestamp"].isna().sum())
    dropped["null_coords"] = int(frame[["lat", "lon"]].isna().any(axis=1).sum())
    frame = frame.dropna(subset=["timestamp", "lat", "lon"]).copy()
    frame["problem_type"] = frame["type_raw"].map(classify)
    frame["timestamp"] = frame["timestamp"].astype("datetime64[us]")
    report = {
        "termination": termination,
        "pages": pages,
        "terminal_offset": offset,
    }
    return frame, report, dropped


def coverage_report(frame: pd.DataFrame, start: str, end: str) -> dict:
    """Name the days and hours with no record, and the largest timestamp gap."""
    days = pd.date_range(start, end, freq="D")
    present = set(frame["timestamp"].dt.normalize())
    missing = [str(day.date()) for day in days if day not in present]
    gaps = frame["timestamp"].sort_values().diff()
    largest = gaps.max() if len(gaps) else pd.Timedelta(0)
    hours = pd.date_range(pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(hours=23), freq="h")
    covered = set(frame["timestamp"].dt.floor("h"))
    return {
        "days_in_window": len(days),
        "days_with_records": len(days) - len(missing),
        "days_missing": missing,
        "hours_in_window": len(hours),
        "empty_hours": sum(1 for hour in hours if hour not in covered),
        "largest_gap_hours": round(largest.total_seconds() / 3600.0, 2),
        "complete": not missing and largest <= pd.Timedelta(hours=MAX_GAP_HOURS),
    }


def _page_in_window(path: Path, start: str, end: str) -> bool:
    match = PAGE_RE.match(path.name)
    if not match:
        return False
    page_start, page_end = pd.Timestamp(match.group(1)), pd.Timestamp(match.group(2))
    return page_start <= pd.Timestamp(end) and page_end >= pd.Timestamp(start)


@dataclass(frozen=True)
class CacheSegment:
    window_start: str
    window_end: str
    pages: int
    offsets: tuple[int, ...]
    direction: str
    complete: bool
    first_ts: str | None
    last_ts: str | None
    sha256: dict[str, str]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _write_parquet(frame: pd.DataFrame, path: Path, provenance: dict) -> None:
    table = pa.Table.from_pandas(frame, preserve_index=False)
    metadata = dict(table.schema.metadata or {})
    metadata[b"bkk_pulse_provenance"] = json.dumps(
        provenance, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    pq.write_table(table.replace_schema_metadata(metadata), path)


def _read_page(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _page_offset(path: Path) -> int:
    return int(PAGE_RE.match(path.name).group(3))


def _page_timestamps(page: list[dict]) -> list[pd.Timestamp]:
    stamps = pd.to_datetime([record.get("timestamp") for record in page], errors="coerce")
    return [stamp for stamp in stamps if not pd.isna(stamp)]


def _first_timestamp(page: list[dict]) -> pd.Timestamp | None:
    stamps = _page_timestamps(page)
    return stamps[0] if stamps else None


def scan_cache(start: str, end: str) -> tuple[list[CacheSegment], list[str]]:
    """Group cached pages into crawl segments and verify each offset chain."""
    groups: dict[tuple[str, str], list[Path]] = {}
    for path in sorted(CACHE_DIR.glob("*.json.gz")):
        match = PAGE_RE.match(path.name)
        if match is None or not _page_in_window(path, start, end):
            continue
        groups.setdefault((match.group(1), match.group(2)), []).append(path)

    segments: list[CacheSegment] = []
    problems: list[str] = []
    for (window_start, window_end), paths in sorted(groups.items()):
        paths.sort(key=_page_offset)
        offsets = [_page_offset(path) for path in paths]
        pages = [_read_page(path) for path in paths]

        problem = None
        if offsets[0] != 0:
            problem = (
                f"{window_start}..{window_end}: chain starts at offset "
                f"{offsets[0]}, expected 0"
            )
        else:
            for previous_offset, previous_page, offset in zip(offsets, pages, offsets[1:]):
                expected = previous_offset + len(previous_page)
                if offset != expected:
                    problem = (
                        f"{window_start}..{window_end}: missing offset {expected} "
                        f"(chain jumps from {previous_offset} to {offset})"
                    )
                    break
        if problem is not None:
            problems.append(problem)
            continue

        first_records = [stamp for stamp in map(_first_timestamp, pages) if stamp is not None]
        direction = (
            "desc" if len(first_records) >= 2 and first_records[0] > first_records[-1] else "asc"
        )
        timestamps = [stamp for page in pages for stamp in _page_timestamps(page)]
        segments.append(
            CacheSegment(
                window_start=window_start,
                window_end=window_end,
                pages=len(paths),
                offsets=tuple(offsets),
                direction=direction,
                complete=not pages[-1],
                first_ts=min(timestamps).isoformat() if timestamps else None,
                last_ts=max(timestamps).isoformat() if timestamps else None,
                sha256={str(offset): _sha256(path) for offset, path in zip(offsets, paths)},
            )
        )
    return segments, problems


def covered_interval(segment: CacheSegment) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(segment.window_start)
    end = pd.Timestamp(segment.window_end) + pd.Timedelta(days=1)
    if segment.complete:
        return start, end
    if segment.direction == "asc":
        return start, pd.Timestamp(segment.last_ts) if segment.last_ts else start
    return (pd.Timestamp(segment.first_ts) if segment.first_ts else end), end


def _segment_report(segment: CacheSegment) -> dict:
    report = asdict(segment)
    report.pop("sha256")
    left, right = covered_interval(segment)
    report["covered"] = [left.isoformat(), right.isoformat()]
    return report


def coverage_gaps(
    segments: list[CacheSegment], start: str, end: str
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    lower = pd.Timestamp(start)
    upper = pd.Timestamp(end) + pd.Timedelta(days=1)
    merged: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for interval in sorted(covered_interval(segment) for segment in segments):
        if merged and interval[0] <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], interval[1]))
        else:
            merged.append(interval)

    gaps: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    cursor = lower
    for interval_start, interval_end in merged:
        interval_start = max(interval_start, lower)
        interval_end = min(interval_end, upper)
        if interval_end <= cursor:
            continue
        if interval_start > cursor:
            gaps.append((cursor, interval_start))
        cursor = max(cursor, interval_end)
    if cursor < upper:
        gaps.append((cursor, upper))
    return gaps


def load_cached_frame(start: str, end: str) -> tuple[pd.DataFrame, dict[str, int]]:
    """Load cached pages whose filename window intersects [start, end], then dedupe."""
    records: dict[str, dict] = {}
    paths = [p for p in sorted(CACHE_DIR.glob("*.json.gz")) if _page_in_window(p, start, end)]
    for path in paths:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for record in json.load(handle):
                records.setdefault(record["ticket_id"], record)
    frame = pd.DataFrame(records.values())
    if frame.empty:
        raise RuntimeError("No cached Traffy pages found")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    dropped = {
        "no_id": 0,
        "no_coords": 0,
        "null_timestamp": int(frame["timestamp"].isna().sum()),
        "null_coords": int(frame[["lat", "lon"]].isna().any(axis=1).sum()),
    }
    frame = frame.dropna(subset=["timestamp", "lat", "lon"]).copy()
    lower = pd.Timestamp(start)
    upper = pd.Timestamp(end) + pd.Timedelta(days=1)
    frame = frame[(frame["timestamp"] >= lower) & (frame["timestamp"] < upper)].copy()
    frame["problem_type"] = frame["type_raw"].map(classify)
    frame["timestamp"] = frame["timestamp"].astype("datetime64[us]")
    print(f"[traffy] combined {len(paths)} cached pages -> {len(frame):,} records in window")
    return frame, dropped


def _nearest_camera(frame: pd.DataFrame, cameras: pd.DataFrame) -> pd.DataFrame:
    """Attach nearest camera id and Haversine distance to every complaint."""
    cam_lat = cameras["lat"].to_numpy(dtype=float)
    cam_lon = cameras["lon"].to_numpy(dtype=float)
    cam_id = cameras["cam_id"].to_numpy(dtype=np.int64)

    nearest_id = np.empty(len(frame), dtype=np.int64)
    nearest_m = np.empty(len(frame), dtype=float)
    chunk = 20_000
    for begin in range(0, len(frame), chunk):
        part = frame.iloc[begin : begin + chunk]
        lat = part["lat"].to_numpy(dtype=float)[:, None]
        lon = part["lon"].to_numpy(dtype=float)[:, None]
        p1 = np.radians(lat)
        p2 = np.radians(cam_lat[None, :])
        dphi = p2 - p1
        dlambda = np.radians(cam_lon[None, :] - lon)
        h = np.sin(dphi / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlambda / 2.0) ** 2
        distances = 2.0 * 6_371_000.0 * np.arcsin(np.sqrt(h))
        best = distances.argmin(axis=1)
        nearest_id[begin : begin + len(part)] = cam_id[best]
        nearest_m[begin : begin + len(part)] = distances[np.arange(len(part)), best]

    result = frame.copy()
    result["nearest_cam_id"] = nearest_id
    result["distance_m"] = nearest_m
    return result


def build_outputs(
    start: str,
    end: str,
    refresh: bool = False,
    max_pages: int = MAX_PAGES,
    fail_on_throttle: bool = False,
    combine_cache: bool = False,
    allow_partial: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    cameras = pd.read_parquet(CAMERA_PATH)[["cam_id", "lat", "lon"]]
    if combine_cache:
        raw, dropped = load_cached_frame(start, end)
        fetch = {"termination": "cache", "pages": 0, "terminal_offset": 0}
    else:
        raw, fetch, dropped = fetch_complaints(
            start, end, refresh=refresh, max_pages=max_pages, fail_on_throttle=fail_on_throttle
        )
    coverage = coverage_report(raw, start, end)
    if coverage["days_missing"] or coverage["largest_gap_hours"] > MAX_GAP_HOURS:
        print(
            f"[WARN] coverage report (advisory only): "
            f"days_missing={coverage['days_missing'][:10]}, "
            f"largest_gap_hours={coverage['largest_gap_hours']}"
        )
    segments, problems = scan_cache(start, end)
    gaps = coverage_gaps(segments, start, end)
    complete = not problems and not gaps
    if not complete and not allow_partial:
        detail = "; ".join(problems) if problems else "offset chains intact"
        gap_text = ", ".join(f"{left} .. {right}" for left, right in gaps)
        raise IncompleteWindow(
            f"{start}..{end} is incomplete: {detail}; gaps=[{gap_text}]. "
            'Rerun with --allow-partial --reason "<text>" to build anyway.'
        )
    WINDOWS_PATH.write_text(
        json.dumps(
            {
                "generated_at": _now_iso(),
                "window": {"start": start, "end": end},
                "segments": [asdict(segment) for segment in segments],
                "covered": complete,
                "gaps": [[left.isoformat(), right.isoformat()] for left, right in gaps],
                "problems": problems,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    complaints = _nearest_camera(raw, cameras)

    matched = complaints[complaints["distance_m"] <= MATCH_RADIUS_M].copy()
    incidents = matched[
        [
            "ticket_id",
            "nearest_cam_id",
            "distance_m",
            "timestamp",
            "problem_type",
            "description",
            "status",
            "lat",
            "lon",
            "type_raw",
        ]
    ].rename(columns={"nearest_cam_id": "nearest_cam_id"})
    incidents = incidents.sort_values(["nearest_cam_id", "timestamp"]).reset_index(drop=True)

    def counts_for(subset: pd.DataFrame) -> pd.DataFrame:
        base = cameras[["cam_id"]].copy()
        if subset.empty:
            base["traffy_flood_count"] = 0
            base["traffy_traffic_count"] = 0
            base["traffy_complaint_count"] = 0
            return base
        pivot = (
            subset.pivot_table(
                index="nearest_cam_id",
                columns="problem_type",
                values="ticket_id",
                aggfunc="count",
                fill_value=0,
            )
            .reindex(columns=["flood", "traffic", "other"], fill_value=0)
            .rename(
                columns={
                    "flood": "traffy_flood_count",
                    "traffic": "traffy_traffic_count",
                    "other": "_other",
                }
            )
        )
        frame = base.merge(pivot, left_on="cam_id", right_index=True, how="left").fillna(0)
        frame["traffy_complaint_count"] = (
            frame["traffy_flood_count"] + frame["traffy_traffic_count"] + frame["_other"]
        )
        frame = frame.drop(columns="_other")
        for column in [
            "traffy_complaint_count",
            "traffy_flood_count",
            "traffy_traffic_count",
        ]:
            frame[column] = frame[column].astype("int64")
        return frame

    counts = counts_for(matched)
    week = matched[
        (matched["timestamp"] >= pd.Timestamp(WEEK_START))
        & (matched["timestamp"] <= pd.Timestamp(WEEK_END))
    ]
    week_counts = counts_for(week).rename(
        columns={
            "traffy_complaint_count": "traffy_complaint_count_7d",
            "traffy_flood_count": "traffy_flood_count_7d",
            "traffy_traffic_count": "traffy_traffic_count_7d",
        }
    )
    counts = counts.merge(week_counts, on="cam_id", how="left")

    summary = {
        "window_start": start,
        "window_end": end,
        "actual_first_timestamp": str(complaints["timestamp"].min()),
        "actual_last_timestamp": str(complaints["timestamp"].max()),
        "complaints_fetched": int(len(complaints)),
        "complaints_within_1000m": int(len(matched)),
        "category_counts_all": {k: int(v) for k, v in complaints["problem_type"].value_counts().items()},
        "category_counts_matched": {k: int(v) for k, v in matched["problem_type"].value_counts().items()},
        "unmatched_type_tags": unmatched_tags(raw["type_raw"]),
        "cameras_with_any_complaint": int((counts["traffy_complaint_count"] > 0).sum()),
        "cameras_with_flood_complaint": int((counts["traffy_flood_count"] > 0).sum()),
        "week_complaints_within_1000m": int(len(week)),
        "match_radius_m": MATCH_RADIUS_M,
        "complete": complete,
        "fetch": fetch,
        "coverage": coverage,
        "dropped": dropped,
        "cache_segments": [_segment_report(segment) for segment in segments],
        "coverage_gaps": [
            [left.isoformat(), right.isoformat()] for left, right in gaps
        ],
    }
    return incidents, counts, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch BMA Traffy Fondue complaints for BKK-Pulse")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--refresh", action="store_true", help="Ignore cached pages")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=int(os.environ.get("TRAFFY_MAX_PAGES", MAX_PAGES)),
        help="Stop after N pages (used to harvest a cached prefix when the API throttles)",
    )
    parser.add_argument(
        "--fail-on-throttle",
        action="store_true",
        help="Abort instead of keeping the cached prefix when the API keeps returning 503",
    )
    parser.add_argument(
        "--fetch-only",
        action="store_true",
        help="Only fill the page cache; do not build parquet outputs",
    )
    parser.add_argument(
        "--combine-cache",
        action="store_true",
        help="Build outputs from every cached page, ignoring the API",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Build even when the cache does not cover the whole window",
    )
    parser.add_argument(
        "--reason",
        default=None,
        help="Why the partial build is acceptable (required with --allow-partial)",
    )
    args = parser.parse_args()
    if args.allow_partial and not args.reason:
        parser.error('--allow-partial requires --reason "<text>"')
    if args.allow_partial:
        print(f"[partial] Build allowed by --reason: {args.reason}")

    if args.fetch_only:
        frame, report, dropped = fetch_complaints(
            args.start,
            args.end,
            refresh=args.refresh,
            max_pages=args.max_pages,
            fail_on_throttle=args.fail_on_throttle,
        )
        coverage = coverage_report(frame, args.start, args.end)
        segments, problems = scan_cache(args.start, args.end)
        gaps = coverage_gaps(segments, args.start, args.end)
        complete = not problems and not gaps
        progress = {
            "window_start": args.start,
            "window_end": args.end,
            "records": int(len(frame)),
            "first_timestamp": str(frame["timestamp"].min()),
            "last_timestamp": str(frame["timestamp"].max()),
            "complete": complete,
            "fetch": report,
            "coverage": coverage,
            "dropped": dropped,
            "cache_segments": [_segment_report(segment) for segment in segments],
            "coverage_gaps": [
                [left.isoformat(), right.isoformat()] for left, right in gaps
            ],
        }
        if not complete and not args.allow_partial:
            detail = "; ".join(problems) if problems else "offset chains intact"
            gap_text = ", ".join(f"{left} .. {right}" for left, right in gaps)
            raise IncompleteWindow(
                f"{args.start}..{args.end} is incomplete: {detail}; gaps=[{gap_text}]. "
                'Rerun with --allow-partial --reason "<text>" to keep the prefix.'
            )
        (PROJECT_ROOT / "data" / "traffy_fetch_progress.json").write_text(
            json.dumps(progress, indent=2), encoding="utf-8"
        )
        print(json.dumps(progress, indent=2))
        return

    incidents, counts, summary = build_outputs(
        args.start,
        args.end,
        refresh=args.refresh,
        max_pages=args.max_pages,
        fail_on_throttle=args.fail_on_throttle,
        combine_cache=args.combine_cache,
        allow_partial=args.allow_partial,
    )
    covered = [segment["covered"] for segment in summary["cache_segments"]]
    provenance = {
        "window": {"start": args.start, "end": args.end},
        "generated_at": _now_iso(),
        "git_commit": _git_commit(),
        "complete": summary["complete"],
        "termination": summary["fetch"]["termination"],
        "pages": sum(segment["pages"] for segment in summary["cache_segments"]),
        "segments": {"count": len(covered), "covered": covered},
        "coverage": summary["coverage"],
        "rows": int(len(incidents)),
        "dropped": summary["dropped"],
        "allow_partial_reason": args.reason if args.allow_partial else None,
    }
    _write_parquet(incidents, INCIDENT_PATH, provenance)
    pq.write_table(pa.Table.from_pandas(counts, preserve_index=False), COUNTS_PATH)
    provenance["outputs"] = {
        INCIDENT_PATH.name: {
            "rows": int(len(incidents)),
            "sha256": _sha256(INCIDENT_PATH),
        },
        COUNTS_PATH.name: {"rows": int(len(counts)), "sha256": _sha256(COUNTS_PATH)},
    }
    PROVENANCE_PATH.write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"[provenance] {PROVENANCE_PATH.relative_to(PROJECT_ROOT)}")
    print(f"[write] {INCIDENT_PATH.relative_to(PROJECT_ROOT)} ({len(incidents):,} rows)")
    print(f"[write] {COUNTS_PATH.relative_to(PROJECT_ROOT)} ({len(counts):,} rows)")


if __name__ == "__main__":
    main()
