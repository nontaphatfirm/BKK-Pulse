"""
Task 01 entrypoint: hourly weather + air quality + 500m OSM POI context.

Produces data/weather_air_poi.parquet (168 hours x 100 cameras) which Task 02
merges with Traffy Fondue counts into data/external_weather_poi.parquet.

Open-Meteo accepts comma-separated coordinates, so the whole city is fetched in
two requests (weather, air quality) instead of 55 per-camera calls.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from fetch_pois_overpass import build_poi_counts

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMERA_PATH = PROJECT_ROOT / "Dataset_Clean_V1" / "cctv_info_cleaned.parquet"
CACHE_DIR = PROJECT_ROOT / "data" / "raw_weather_air"
OUTPUT_PATH = PROJECT_ROOT / "data" / "weather_air_poi.parquet"

START_DATE = "2026-08-25"
END_DATE = "2026-08-31"
USER_AGENT = "bkk-pulse-course-project/1.0 (Chulalongkorn DSDE)"

WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

WEATHER_FIELDS = (
    "precipitation",
    "rain",
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
)
AIR_FIELDS = ("pm2_5", "nitrogen_dioxide", "carbon_monoxide")


def _fetch_json(url: str, params: dict[str, str]) -> list[dict] | dict:
    full_url = f"{url}?{urllib.parse.urlencode(params, safe=',')}"
    for attempt in range(4):
        try:
            req = urllib.request.Request(full_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:
            wait = 3 * (attempt + 1)
            print(f"[http] attempt {attempt + 1} failed ({exc}); retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Request failed: {url}")


def _cached_fetch(name: str, url: str, params: dict[str, str], refresh: bool) -> list[dict]:
    path = CACHE_DIR / f"{name}.json"
    if path.exists() and not refresh:
        print(f"[cache] {path.relative_to(PROJECT_ROOT)}")
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        print(f"[http] {name}: one batched request for all grid cells")
        payload = _fetch_json(url, params)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list) or not payload:
        raise RuntimeError(f"Unexpected Open-Meteo payload for {name}")
    return payload


def _grid_coordinates(cameras: pd.DataFrame) -> tuple[list[tuple[float, float]], pd.DataFrame]:
    """Deduplicate cameras onto the ~0.01 degree grid used by the weather request."""
    grid = cameras[["cam_id", "lat", "lon"]].copy()
    grid["grid_lat"] = grid["lat"].round(2)
    grid["grid_lon"] = grid["lon"].round(2)
    coords = sorted({(float(r.grid_lat), float(r.grid_lon)) for r in grid.itertuples(index=False)})
    return coords, grid


def _hourly_frame(payload: list[dict], coords: list[tuple[float, float]], value_map: dict[str, str]) -> pd.DataFrame:
    """Flatten N coordinate responses into long (grid_lat, grid_lon, timestamp) rows."""
    frames = []
    if len(payload) != len(coords):
        raise RuntimeError(f"Expected {len(coords)} grid responses, got {len(payload)}")
    for (grid_lat, grid_lon), block in zip(coords, payload):
        hourly = block.get("hourly", {})
        if "time" not in hourly:
            raise RuntimeError(f"Missing hourly.time for grid cell {grid_lat},{grid_lon}")
        frame = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(hourly["time"]),
                "grid_lat": grid_lat,
                "grid_lon": grid_lon,
            }
        )
        for source, target in value_map.items():
            frame[target] = hourly.get(source)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def build_weather_air(cameras: pd.DataFrame, refresh: bool = False) -> pd.DataFrame:
    coords, grid = _grid_coordinates(cameras)
    lat_csv = ",".join(str(lat) for lat, _ in coords)
    lon_csv = ",".join(str(lon) for _, lon in coords)
    print(f"[grid] {len(coords)} unique coordinate cells for {len(cameras)} cameras")

    base_params = {
        "latitude": lat_csv,
        "longitude": lon_csv,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "timezone": "Asia/Bangkok",
    }
    weather = _cached_fetch(
        "weather",
        WEATHER_URL,
        {**base_params, "hourly": ",".join(WEATHER_FIELDS)},
        refresh,
    )
    air = _cached_fetch(
        "air_quality",
        AIR_QUALITY_URL,
        {**base_params, "hourly": ",".join(AIR_FIELDS)},
        refresh,
    )

    weather_long = _hourly_frame(
        weather,
        coords,
        {
            "precipitation": "rain_mm",
            "temperature_2m": "temp_c",
            "relative_humidity_2m": "humidity_pct",
            "wind_speed_10m": "wind_speed_kmh",
        },
    )
    air_long = _hourly_frame(
        air,
        coords,
        {"pm2_5": "pm25", "nitrogen_dioxide": "no2", "carbon_monoxide": "co"},
    )

    grid_frame = grid[["cam_id", "grid_lat", "grid_lon"]].merge(
        weather_long, on=["grid_lat", "grid_lon"], how="left"
    ).merge(air_long, on=["grid_lat", "grid_lon", "timestamp"], how="left")

    poi_counts = build_poi_counts(cameras[["cam_id", "lat", "lon"]], refresh=refresh)
    frame = grid_frame.merge(poi_counts, on="cam_id", how="left")

    frame["timestamp"] = pd.to_datetime(frame["timestamp"]).astype("datetime64[us]")
    numeric_cols = [
        "rain_mm",
        "temp_c",
        "humidity_pct",
        "wind_speed_kmh",
        "pm25",
        "no2",
        "co",
    ]
    for column in numeric_cols:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("float64")
        if frame[column].isna().any():
            # Keep the contract's "zero NaN" promise; report before filling.
            missing = int(frame[column].isna().sum())
            print(f"[warn] {column}: {missing} missing values -> forward/back fill")
            frame[column] = frame[column].ffill().bfill()

    for column in [
        "nearby_transit_count",
        "nearby_school_count",
        "nearby_mall_count",
        "nearby_hospital_count",
        "poi_total_count",
    ]:
        frame[column] = frame[column].fillna(0).astype("int64")

    frame = frame.sort_values(["cam_id", "timestamp"]).reset_index(drop=True)
    frame["cam_id"] = frame["cam_id"].astype("int64")
    return frame[
        [
            "cam_id",
            "timestamp",
            *numeric_cols,
            "nearby_transit_count",
            "nearby_school_count",
            "nearby_mall_count",
            "nearby_hospital_count",
            "poi_total_count",
        ]
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Open-Meteo weather/air + 500m OSM POIs")
    parser.add_argument("--refresh", action="store_true", help="Ignore cached API responses")
    args = parser.parse_args()

    cameras = pd.read_parquet(CAMERA_PATH)
    frame = build_weather_air(cameras[["cam_id", "lat", "lon"]], refresh=args.refresh)

    expected_rows = 168 * len(cameras)
    if len(frame) != expected_rows:
        raise RuntimeError(f"Expected {expected_rows} rows, got {len(frame)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(OUTPUT_PATH, index=False)

    summary = {
        "output": str(OUTPUT_PATH.relative_to(PROJECT_ROOT)),
        "rows": int(len(frame)),
        "cameras": int(frame["cam_id"].nunique()),
        "hours_per_camera": int(frame.groupby("cam_id").size().max()),
        "start": str(frame["timestamp"].min()),
        "end": str(frame["timestamp"].max()),
        "nulls": int(frame.isna().sum().sum()),
        "poi_columns": {
            "transit": int(frame["nearby_transit_count"].max()),
            "school": int(frame["nearby_school_count"].max()),
            "mall": int(frame["nearby_mall_count"].max()),
            "hospital": int(frame["nearby_hospital_count"].max()),
        },
    }
    (PROJECT_ROOT / "data" / "scraping_summary_01.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
