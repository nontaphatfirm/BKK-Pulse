"""
Merge Task 01 (weather, air quality, POIs) with Task 02 (Traffy counts) into
the canonical data/external_weather_poi.parquet required by DATA_CONTRACT.md.

Shapes: 100 cameras x 168 hourly timestamps = 16,800 rows, 17 columns, no nulls.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEATHER_PATH = PROJECT_ROOT / "data" / "weather_air_poi.parquet"
INCIDENTS_PATH = PROJECT_ROOT / "data" / "traffy_complaints_near_cctv.parquet"
PROVENANCE_PATH = PROJECT_ROOT / "data" / "traffy_provenance.json"
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


def trailing_counts(
    incidents: pd.DataFrame,
    hours: pd.DataFrame,
    window: pd.Timedelta = pd.Timedelta(days=7),
) -> pd.DataFrame:
    """Count each camera's complaints in the window ending at every hourly grid point."""
    incidents = incidents[["nearest_cam_id", "timestamp", "problem_type"]].copy()
    incidents["timestamp"] = pd.to_datetime(incidents["timestamp"]).astype("datetime64[us]")
    hours = hours[["cam_id", "timestamp"]].copy()
    hours["timestamp"] = pd.to_datetime(hours["timestamp"]).astype("datetime64[us]")
    step = window.to_timedelta64()

    parts: list[pd.DataFrame] = []
    for cam_id, group in hours.groupby("cam_id", sort=False):
        stamps = group["timestamp"].to_numpy(dtype="datetime64[us]")
        camera = incidents[incidents["nearest_cam_id"] == cam_id]
        frame = pd.DataFrame({"cam_id": cam_id, "timestamp": stamps})
        for label, column in (
            (None, "traffy_complaint_count"),
            ("flood", "traffy_flood_count"),
            ("traffic", "traffy_traffic_count"),
        ):
            subset = camera if label is None else camera[camera["problem_type"] == label]
            values = np.sort(subset["timestamp"].to_numpy(dtype="datetime64[us]"))
            frame[column] = np.searchsorted(values, stamps, side="right") - np.searchsorted(
                values, stamps - step, side="right"
            )
        parts.append(frame)

    counts = pd.concat(parts, ignore_index=True)
    for column in TRAFFY_COLUMNS:
        counts[column] = counts[column].astype("int64")
    return counts


def _read_provenance() -> dict | None:
    if INCIDENTS_PATH.exists():
        stamp = (pq.read_schema(INCIDENTS_PATH).metadata or {}).get(b"bkk_pulse_provenance")
        if stamp is not None:
            return json.loads(stamp)
    if PROVENANCE_PATH.exists():
        block = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
        block.pop("outputs", None)
        return block
    return None


def _write_parquet(frame: pd.DataFrame, provenance: dict | None) -> None:
    table = pa.Table.from_pandas(frame, preserve_index=False)
    if provenance is not None:
        metadata = dict(table.schema.metadata or {})
        metadata[b"bkk_pulse_provenance"] = json.dumps(
            provenance, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        table = table.replace_schema_metadata(metadata)
    pq.write_table(table, OUTPUT_PATH)


def main() -> None:
    weather = pd.read_parquet(WEATHER_PATH)
    weather["cam_id"] = weather["cam_id"].astype("int64")
    weather["timestamp"] = pd.to_datetime(weather["timestamp"]).astype("datetime64[us]")
    incidents = pd.read_parquet(INCIDENTS_PATH)
    counts = trailing_counts(incidents, weather[["cam_id", "timestamp"]])

    frame = weather.merge(
        counts, on=["cam_id", "timestamp"], how="left", validate="many_to_one"
    )
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

    _write_parquet(frame, _read_provenance())

    summary = {
        "output": OUTPUT_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "rows": int(len(frame)),
        "columns": len(frame.columns),
        "cameras": int(frame["cam_id"].nunique()),
        "timestamps": int(frame["timestamp"].nunique()),
        "nulls": int(frame.isna().sum().sum()),
        "traffy_cameras_with_reports": int((frame.groupby("cam_id")["traffy_complaint_count"].max() > 0).sum()),
        "max_trailing7d_complaints": int(frame["traffy_complaint_count"].max()),
        "max_trailing7d_flood": int(frame["traffy_flood_count"].max()),
    }
    (PROJECT_ROOT / "data" / "scraping_summary_merged.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
