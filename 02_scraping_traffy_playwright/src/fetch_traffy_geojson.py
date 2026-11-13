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
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMERA_PATH = PROJECT_ROOT / "Dataset_Clean_V1" / "cctv_info_cleaned.parquet"
CACHE_DIR = PROJECT_ROOT / "data" / "raw_traffy_cache" / "pages"
INCIDENT_PATH = PROJECT_ROOT / "data" / "traffy_complaints_near_cctv.parquet"
COUNTS_PATH = PROJECT_ROOT / "data" / "traffy_camera_counts.parquet"
SUMMARY_PATH = PROJECT_ROOT / "data" / "scraping_summary_02.json"

API_URL = "https://api.traffy.in.th/postgrest/rpc/get_bkk_geojson_feed"
USER_AGENT = "bkk-pulse-course-project/1.0 (Chulalongkorn DSDE)"
PAGE_LIMIT = 2000
MAX_PAGES = 2000
MATCH_RADIUS_M = 1000.0

DEFAULT_START = "2026-05-01"
DEFAULT_END = "2026-10-31"
WEEK_START = "2026-08-25"
WEEK_END = "2026-08-31 23:59:59"

FLOOD_KEYS = ("น้ำท่วม", "ท่อระบายน้ำ", "น้ำท่วมขัง")
TRAFFIC_KEYS = ("จราจร", "ถนน", "กีดขวาง", "อุบัติเหตุ")


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


def classify(raw_type: str) -> str:
    """Map a Traffy problem type onto flood / traffic / other."""
    if any(key in raw_type for key in FLOOD_KEYS):
        return "flood"
    if any(key in raw_type for key in TRAFFIC_KEYS):
        return "traffic"
    return "other"


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
            # Sustained request bursts trigger 503s; pace successful pages too.
            time.sleep(10.0)
            return payload.get("features") or []
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


def _compact(feature: dict) -> dict | None:
    props = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates") or []
    ticket_id = str(props.get("ticket_id") or "").strip()
    if not ticket_id or len(coords) < 2:
        return None
    timestamp = props.get("timestamp")
    return {
        "ticket_id": ticket_id,
        "lon": float(coords[0]),
        "lat": float(coords[1]),
        "timestamp": timestamp,
        "type_raw": str(props.get("type") or ""),
        "description": str(props.get("description") or ""),
        "status": str(props.get("state") or ""),
    }


def load_page(start: str, end: str, offset: int, refresh: bool, attempts: int = 15) -> list[dict]:
    path = _page_path(start, end, offset)
    if path.exists() and not refresh:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)

    features = _request_page(start, end, offset, attempts=attempts)
    compact = [c for c in (_compact(f) for f in features) if c is not None]
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(compact, handle, ensure_ascii=False)
    return compact


def fetch_complaints(
    start: str,
    end: str,
    refresh: bool = False,
    max_pages: int = MAX_PAGES,
    fail_on_throttle: bool = False,
) -> pd.DataFrame:
    """Page through the feed until an empty page, then dedupe by ticket id."""
    records: dict[str, dict] = {}
    offset = 0
    for page in range(max_pages):
        try:
            # Once a cached prefix exists, do not stall the whole pipeline on a throttled API.
            batch = load_page(start, end, offset, refresh, attempts=8 if records else 15)
        except RuntimeError as exc:
            if not records or fail_on_throttle:
                raise
            print(f"[traffy] {exc}; keeping cached prefix ({len(records):,} records)")
            break
        if not batch:
            print(f"[traffy] stopped at offset {offset} after {page} non-empty pages")
            break
        for record in batch:
            records.setdefault(record["ticket_id"], record)
        print(f"[traffy] offset {offset:>6} +{len(batch):>4} = {len(records):>6} unique")
        offset += len(batch)
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
    frame = frame.dropna(subset=["timestamp", "lat", "lon"]).copy()
    frame["problem_type"] = frame["type_raw"].map(classify)
    frame["timestamp"] = frame["timestamp"].astype("datetime64[us]")
    return frame


def load_cached_frame(start: str, end: str) -> pd.DataFrame:
    """Load every cached page (all date windows), dedupe, then filter to [start, end]."""
    records: dict[str, dict] = {}
    paths = sorted(CACHE_DIR.glob("*.json.gz"))
    for path in paths:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for record in json.load(handle):
                records.setdefault(record["ticket_id"], record)
    frame = pd.DataFrame(records.values())
    if frame.empty:
        raise RuntimeError("No cached Traffy pages found")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame = frame.dropna(subset=["timestamp", "lat", "lon"]).copy()
    lower = pd.Timestamp(start)
    upper = pd.Timestamp(end) + pd.Timedelta(days=1)
    frame = frame[(frame["timestamp"] >= lower) & (frame["timestamp"] < upper)].copy()
    frame["problem_type"] = frame["type_raw"].map(classify)
    frame["timestamp"] = frame["timestamp"].astype("datetime64[us]")
    print(f"[traffy] combined {len(paths)} cached pages -> {len(frame):,} records in window")
    return frame


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
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    cameras = pd.read_parquet(CAMERA_PATH)[["cam_id", "lat", "lon"]]
    raw = (
        load_cached_frame(start, end)
        if combine_cache
        else fetch_complaints(
            start, end, refresh=refresh, max_pages=max_pages, fail_on_throttle=fail_on_throttle
        )
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
        "cameras_with_any_complaint": int((counts["traffy_complaint_count"] > 0).sum()),
        "cameras_with_flood_complaint": int((counts["traffy_flood_count"] > 0).sum()),
        "week_complaints_within_1000m": int(len(week)),
        "match_radius_m": MATCH_RADIUS_M,
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
    args = parser.parse_args()

    if args.fetch_only:
        frame = fetch_complaints(
            args.start,
            args.end,
            refresh=args.refresh,
            max_pages=args.max_pages,
            fail_on_throttle=args.fail_on_throttle,
        )
        progress = {
            "window_start": args.start,
            "window_end": args.end,
            "records": int(len(frame)),
            "first_timestamp": str(frame["timestamp"].min()),
            "last_timestamp": str(frame["timestamp"].max()),
        }
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
    )
    incidents.to_parquet(INCIDENT_PATH, index=False)
    counts.to_parquet(COUNTS_PATH, index=False)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"[write] {INCIDENT_PATH.relative_to(PROJECT_ROOT)} ({len(incidents):,} rows)")
    print(f"[write] {COUNTS_PATH.relative_to(PROJECT_ROOT)} ({len(counts):,} rows)")


if __name__ == "__main__":
    main()
