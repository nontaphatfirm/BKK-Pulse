"""
OSM Overpass POI ingestion for BKK-Pulse Task 01.

One single bounding-box query covers all 100 cameras, then Haversine matching
is done locally. Do not issue per-camera `around:` queries -- the public
Overpass server throttles them with HTTP 429.
"""

from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# (south, west, north, east) -- verified to cover all 100 cameras
BBOX = (13.65, 100.35, 13.90, 100.65)
CACHE_PATH = PROJECT_ROOT / "data" / "raw_osm" / "bkk_pois.json"
RADIUS_M = 500.0
USER_AGENT = "bkk-pulse-course-project/1.0 (Chulalongkorn DSDE)"

OVERPASS_QUERY = """
[out:json][timeout:180];
(
  node["railway"="station"]({s},{w},{n},{e});
  node["station"~"subway|light_rail"]({s},{w},{n},{e});
  node["highway"="bus_stop"]({s},{w},{n},{e});
  node["public_transport"="platform"]({s},{w},{n},{e});
  node["amenity"~"school|university|college"]({s},{w},{n},{e});
  node["shop"~"mall|department_store|supermarket"]({s},{w},{n},{e});
  node["amenity"="marketplace"]({s},{w},{n},{e});
  node["amenity"~"hospital|clinic"]({s},{w},{n},{e});
);
out center tags;
"""


@dataclass(frozen=True)
class PoiCategory:
    name: str
    column: str


# Priority order: a node carrying two tags is counted in the first matching bucket.
CATEGORIES = (
    PoiCategory("transit", "nearby_transit_count"),
    PoiCategory("school", "nearby_school_count"),
    PoiCategory("mall", "nearby_mall_count"),
    PoiCategory("hospital", "nearby_hospital_count"),
)


def _classify(tags: dict) -> str | None:
    """Map an OSM tag set to one of the four contract POI categories."""
    if tags.get("railway") == "station" or tags.get("station") in {"subway", "light_rail"}:
        return "transit"
    if tags.get("highway") == "bus_stop" or tags.get("public_transport") == "platform":
        return "transit"
    if tags.get("amenity") in {"school", "university", "college"}:
        return "school"
    if tags.get("shop") in {"mall", "department_store", "supermarket"}:
        return "mall"
    if tags.get("amenity") == "marketplace":
        return "mall"
    if tags.get("amenity") in {"hospital", "clinic"}:
        return "hospital"
    return None


def _download_pois() -> dict:
    query = OVERPASS_QUERY.format(s=BBOX[0], w=BBOX[1], n=BBOX[2], e=BBOX[3])
    body = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(
        OVERPASS_URL,
        data=body,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    print("[overpass] one bbox query (21-40s expected) ...")
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=200) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    print(f"[overpass] {len(payload.get('elements', []))} elements in {time.perf_counter() - t0:.1f}s")
    return payload


def load_poi_payload(refresh: bool = False) -> dict:
    """Return cached raw Overpass JSON, downloading it once if needed."""
    if CACHE_PATH.exists() and not refresh:
        print(f"[overpass] using cache {CACHE_PATH.relative_to(PROJECT_ROOT)}")
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            payload = _download_pois()
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            return payload
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            wait = 5 * (attempt + 1)
            print(f"[overpass] attempt {attempt + 1} failed ({exc}); retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Overpass download failed after 3 attempts: {last_error}")


def haversine_m(lat1: float, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    radius = 6_371_000.0
    p1, p2 = math.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlambda = np.radians(lon2 - lon1)
    h = np.sin(dphi / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlambda / 2.0) ** 2
    return 2.0 * radius * np.arcsin(np.sqrt(h))


def build_poi_counts(cameras: pd.DataFrame, payload: dict | None = None, refresh: bool = False) -> pd.DataFrame:
    """Return one row per camera with 500m POI counts for the four categories."""
    payload = payload or load_poi_payload(refresh=refresh)

    rows: list[tuple[float, float, str]] = []
    seen: set[tuple[str, int]] = set()
    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        category = _classify(tags)
        if category is None:
            continue
        key = (element.get("type", "node"), int(element.get("id", 0)))
        if key in seen:
            continue
        seen.add(key)
        lat = element.get("lat", element.get("center", {}).get("lat"))
        lon = element.get("lon", element.get("center", {}).get("lon"))
        if lat is None or lon is None:
            continue
        rows.append((float(lat), float(lon), category))

    if not rows:
        raise RuntimeError("Overpass payload contained no usable POI elements")

    poi_lat = np.array([r[0] for r in rows])
    poi_lon = np.array([r[1] for r in rows])
    poi_cat = np.array([r[2] for r in rows])

    result = cameras[["cam_id", "lat", "lon"]].copy()
    for category in CATEGORIES:
        result[category.column] = 0
    result["poi_total_count"] = 0

    for cam in result.itertuples(index=False):
        distances = haversine_m(cam.lat, cam.lon, poi_lat, poi_lon)
        within = distances <= RADIUS_M
        counts = {c.name: int(np.count_nonzero(within & (poi_cat == c.name))) for c in CATEGORIES}
        for category in CATEGORIES:
            result.loc[result["cam_id"] == cam.cam_id, category.column] = counts[category.name]
        result.loc[result["cam_id"] == cam.cam_id, "poi_total_count"] = sum(counts.values())

    for category in CATEGORIES:
        result[category.column] = result[category.column].astype("int64")
    result["poi_total_count"] = result["poi_total_count"].astype("int64")
    return result[["cam_id", *[c.column for c in CATEGORIES], "poi_total_count"]]


if __name__ == "__main__":
    cams = pd.read_parquet(PROJECT_ROOT / "Dataset_Clean_V1" / "cctv_info_cleaned.parquet")
    counts = build_poi_counts(cams[["cam_id", "lat", "lon"]])
    print(counts.describe().T)
