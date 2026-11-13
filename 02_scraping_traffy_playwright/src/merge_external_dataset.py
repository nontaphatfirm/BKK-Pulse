"""
Merge Task 01 (weather, air quality, POIs) with Task 02 (Traffy counts) into
the canonical data/external_weather_poi.parquet required by DATA_CONTRACT.md.

Shapes: 100 cameras x 168 hourly timestamps = 16,800 rows, 17 columns, no nulls.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEATHER_PATH = PROJECT_ROOT / "data" / "weather_air_poi.parquet"
TRAFFY_COUNTS_PATH = PROJECT_ROOT / "data" / "traffy_camera_counts.parquet"
OUTPUT_PATH = PROJECT_ROOT / "data" / "external_weather_poi.parquet"

CONTRACT_COLUMNS = [
    "cam_id",
    "timestamp",
    "rain_mm",
    "temp_c",
    "humidity_pct",
    "wind_speed_kmh",
    "pm25",
    "no2",
    "co",
    "nearby_transit_count",
    "nearby_school_count",
    "nearby_mall_count",
    "nearby_hospital_count",
    "poi_total_count",
    "traffy_complaint_count",
    "traffy_flood_count",
    "traffy_traffic_count",
]

TRAFFY_COLUMNS = ["traffy_complaint_count", "traffy_flood_count", "traffy_traffic_count"]


def main() -> None:
    weather = pd.read_parquet(WEATHER_PATH)
    counts = pd.read_parquet(TRAFFY_COUNTS_PATH)[["cam_id", *TRAFFY_COLUMNS]]

    frame = weather.merge(counts, on="cam_id", how="left", validate="many_to_one")
    for column in TRAFFY_COLUMNS:
        frame[column] = frame[column].fillna(0).astype("int64")

    frame["cam_id"] = frame["cam_id"].astype("int64")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"]).astype("datetime64[us]")
    frame = frame[CONTRACT_COLUMNS].sort_values(["cam_id", "timestamp"]).reset_index(drop=True)

    if len(frame) != 16_800:
        raise RuntimeError(f"Expected 16,800 rows, got {len(frame)}")
    if frame[["cam_id", "timestamp"]].isna().any().any():
        raise RuntimeError("Null primary key detected")
    if frame.duplicated(["cam_id", "timestamp"]).any():
        raise RuntimeError("Duplicate (cam_id, timestamp) detected")
    if frame.isna().any().any():
        raise RuntimeError(f"Null values remain: {frame.isna().sum()[frame.isna().sum() > 0].to_dict()}")

    frame.to_parquet(OUTPUT_PATH, index=False)

    summary = {
        "output": str(OUTPUT_PATH.relative_to(PROJECT_ROOT)),
        "rows": int(len(frame)),
        "columns": len(frame.columns),
        "cameras": int(frame["cam_id"].nunique()),
        "timestamps": int(frame["timestamp"].nunique()),
        "nulls": int(frame.isna().sum().sum()),
        "traffy_cameras_with_reports": int((frame.groupby("cam_id")["traffy_complaint_count"].max() > 0).sum()),
        "max_complaints_per_camera": int(frame["traffy_complaint_count"].max()),
        "max_flood_per_camera": int(frame["traffy_flood_count"].max()),
    }
    (PROJECT_ROOT / "data" / "scraping_summary_merged.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
