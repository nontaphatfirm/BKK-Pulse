"""
BKK-Pulse: End-to-End Data Engineering & Analytics Pipeline Orchestrator
========================================================================
Satisfies Component 1 (Data Engineering — Workflow Management) from
2110403 DSDE Project Criteria by providing a unified CLI entrypoint to:
1. Validate all shared Parquet/JSON artifacts against DATA_CONTRACT.md (--check-contract)
2. Execute the modular pipeline end-to-end in dependency order (--sample or --all)
3. Run individual module stages (--stage 00 .. 05)

Usage:
    python run_pipeline.py --check-contract
    python run_pipeline.py --sample
    python run_pipeline.py --all
    python run_pipeline.py --stage 00
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import time
from typing import Sequence

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class ContractSpec:
    name: str
    rel_path: str
    required_for_phase0: bool
    primary_keys: tuple[str, ...]
    required_columns: tuple[str, ...]
    expected_min_rows: int


CONTRACT_TABLES: tuple[ContractSpec, ...] = (
    ContractSpec(
        name="Table 1: Cleaned Camera Metadata",
        rel_path="Dataset_Clean_V1/cctv_info_cleaned.parquet",
        required_for_phase0=True,
        primary_keys=("cam_id",),
        required_columns=(
            "cam_id",
            "location_th",
            "location_detail_th",
            "location_en",
            "location_detail_en",
            "lat",
            "lon",
            "district",
            "corridor",
            "pair_id",
            "pair_type",
            "direction",
            "ip_address",
            "ip_subnet",
            "img_width",
            "img_height",
            "actual_raw_image_count",
            "valid_image_count",
            "white_error_count",
            "no_signal_error_count",
            "corrupt_color_count",
            "frozen_image_count",
            "error_image_count",
            "valid_rate_pct",
        ),
        expected_min_rows=100,
    ),
    ContractSpec(
        name="Table 2: Frame Quality & Optical Manifest",
        rel_path="Dataset_Clean_V1/image_quality_manifest.parquet",
        required_for_phase0=True,
        primary_keys=("cam_id", "timestamp"),
        required_columns=(
            "cam_id",
            "timestamp",
            "date",
            "hour",
            "minute",
            "day_of_week",
            "is_weekend",
            "filename",
            "clean_filename",
            "clean_rel_path",
            "file_size",
            "status",
            "is_valid",
            "brightness_mean",
            "contrast_std",
            "glare_ratio",
            "mad_from_prev",
            "quality_warning",
        ),
        expected_min_rows=61319,
    ),
    ContractSpec(
        name="Table 3a: Pilot Vehicle Counts (5 Cameras)",
        rel_path="data/vehicle_counts_sample.parquet",
        required_for_phase0=False,
        primary_keys=("cam_id", "timestamp"),
        required_columns=(
            "cam_id",
            "timestamp",
            "car_count",
            "motorcycle_count",
            "bus_count",
            "truck_count",
            "total_vehicle_count",
            "pcu_score",
            "bbox_total_area",
            "road_roi_area",
            "road_occupancy_ratio",
            "foreground_ratio",
            "filtered_static_boxes",
        ),
        expected_min_rows=2500,
    ),
    ContractSpec(
        name="Table 3b: Full Vehicle Counts (100 Cameras)",
        rel_path="data/vehicle_counts.parquet",
        required_for_phase0=False,
        primary_keys=("cam_id", "timestamp"),
        required_columns=(
            "cam_id",
            "timestamp",
            "car_count",
            "motorcycle_count",
            "bus_count",
            "truck_count",
            "total_vehicle_count",
            "pcu_score",
            "bbox_total_area",
            "road_roi_area",
            "road_occupancy_ratio",
            "foreground_ratio",
            "filtered_static_boxes",
        ),
        expected_min_rows=60210,
    ),
    ContractSpec(
        name="Table 4: External Weather, Air Quality, POI & Traffy Context",
        rel_path="data/external_weather_poi.parquet",
        required_for_phase0=False,
        primary_keys=("cam_id", "timestamp"),
        required_columns=(
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
        ),
        expected_min_rows=16800,
    ),
)


@dataclass(frozen=True)
class PipelineStage:
    stage_id: str
    title: str
    module_dir: str
    candidate_scripts: tuple[str, ...]


PIPELINE_STAGES: tuple[PipelineStage, ...] = (
    PipelineStage(
        stage_id="00",
        title="Phase 0: Image Quality Gate & Metadata Cleansing",
        module_dir="00_data_cleaning_and_qa",
        candidate_scripts=("00_data_cleaning_and_qa/src/clean_dataset_v1.py",),
    ),
    PipelineStage(
        stage_id="01",
        title="Task 01: Weather, Air Quality & 500m OSM POI Scraping",
        module_dir="01_scraping_apis",
        candidate_scripts=(
            "01_scraping_apis/src/fetch_weather_air_poi.py",
            "01_scraping_apis/src/run_scraping_apis.py",
        ),
    ),
    PipelineStage(
        stage_id="02",
        title="Task 02: Playwright BMA Traffy Fondue Scraping & Spatial Join",
        module_dir="02_scraping_traffy_playwright",
        candidate_scripts=(
            "02_scraping_traffy_playwright/src/scrape_traffy_playwright.py",
            "02_scraping_traffy_playwright/src/fetch_traffy_geojson.py",
        ),
    ),
    PipelineStage(
        stage_id="03",
        title="Task 03: Batch YOLO Vehicle Detection, Median BG & Auto ROI",
        module_dir="03_cv_yolo_pipeline",
        candidate_scripts=(
            "03_cv_yolo_pipeline/src/run_batch_cv_pipeline.py",
        ),
    ),
    PipelineStage(
        stage_id="04",
        title="Task 04: Spatio-Temporal Traffic Analytics & K-Means Clustering",
        module_dir="04_ds_traffic_analytics",
        candidate_scripts=(
            "04_ds_traffic_analytics/src/run_traffic_analytics.py",
        ),
    ),
    PipelineStage(
        stage_id="05",
        title="Task 05: LightGBM 30-Min Traffic Forecasting & SHAP Attribution",
        module_dir="05_ds_ml_forecasting",
        candidate_scripts=(
            "05_ds_ml_forecasting/src/build_lag_dataset.py",
            "05_ds_ml_forecasting/src/train_lgbm_forecaster.py",
            "05_ds_ml_forecasting/src/compute_shap_explanations.py",
        ),
    ),
)


def validate_contract(strict_all: bool = False) -> bool:
    """Validate canonical Parquet tables against DATA_CONTRACT.md."""
    print("=" * 76)
    print("BKK-Pulse Data Contract Verification (DATA_CONTRACT.md)")
    print("=" * 76)
    all_passed = True

    for spec in CONTRACT_TABLES:
        path = PROJECT_ROOT / spec.rel_path
        if not path.exists():
            if spec.required_for_phase0 or strict_all:
                print(f"[FAIL] {spec.name} -> Missing required file: {spec.rel_path}")
                all_passed = False
            else:
                print(f"[PEND] {spec.name} -> Not yet generated ({spec.rel_path})")
            continue

        df = pd.read_parquet(path)
        missing_cols = [c for c in spec.required_columns if c not in df.columns]
        if missing_cols:
            print(f"[FAIL] {spec.name} -> Missing columns: {missing_cols}")
            all_passed = False
            continue

        # Validate cam_id is integer
        if "cam_id" in df.columns and not pd.api.types.is_integer_dtype(df["cam_id"].dtype):
            print(f"[FAIL] {spec.name} -> 'cam_id' must be int64, got {df['cam_id'].dtype}")
            all_passed = False
            continue

        # Validate timestamp is timezone-naive datetime64 (ns or us)
        if "timestamp" in df.columns:
            ts_dtype = df["timestamp"].dtype
            if not pd.api.types.is_datetime64_any_dtype(ts_dtype) or getattr(ts_dtype, "tz", None) is not None:
                print(
                    f"[FAIL] {spec.name} -> 'timestamp' must be timezone-naive datetime64, got {ts_dtype}"
                )
                all_passed = False
                continue

        # Validate row count and primary key uniqueness
        if len(df) < spec.expected_min_rows:
            print(
                f"[FAIL] {spec.name} -> Expected >= {spec.expected_min_rows:,} rows, got {len(df):,}"
            )
            all_passed = False
            continue

        null_pk = int(df[list(spec.primary_keys)].isna().any(axis=1).sum())
        dup_pk = int(df.duplicated(subset=list(spec.primary_keys)).sum())
        if null_pk > 0 or dup_pk > 0:
            print(
                f"[FAIL] {spec.name} -> Primary key {spec.primary_keys} has {null_pk} nulls and {dup_pk} duplicates"
            )
            all_passed = False
            continue

        print(
            f"[PASS] {spec.name} ({spec.rel_path}) -> {len(df):,} rows, {len(df.columns)} cols, PK {spec.primary_keys} valid"
        )

    print("=" * 76)
    return all_passed


def run_stage(stage: PipelineStage, sample_mode: bool = False) -> bool:
    """Execute implemented scripts in a pipeline stage."""
    print(f"\n>>> Stage {stage.stage_id}: {stage.title}")
    existing_scripts = [PROJECT_ROOT / s for s in stage.candidate_scripts if (PROJECT_ROOT / s).exists()]

    if not existing_scripts:
        print(f"    [SKIP] No production entrypoint implemented yet in {stage.module_dir}/src/")
        return True

    for script_path in existing_scripts:
        cmd: list[str] = [sys.executable, str(script_path)]
        if stage.stage_id == "00":
            cmd.append("--skip-copy")
        elif sample_mode and stage.stage_id in {"03", "04", "05"}:
            cmd.append("--sample")

        print(f"    [RUN]  {' '.join(cmd)}")
        t0 = time.perf_counter()
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, check=False)
        elapsed = time.perf_counter() - t0
        if result.returncode != 0:
            print(f"    [FAIL] {script_path.name} exited with code {result.returncode} ({elapsed:.1f}s)")
            return False
        print(f"    [DONE] {script_path.name} completed in {elapsed:.1f}s")

    return True


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BKK-Pulse End-to-End Pipeline Orchestrator & Data Contract Validator"
    )
    parser.add_argument(
        "--check-contract",
        action="store_true",
        help="Validate existing Parquet artifacts against DATA_CONTRACT.md and exit.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require all Phase 1 tables (01-05) to exist during --check-contract.",
    )
    parser.add_argument(
        "--stage",
        choices=[s.stage_id for s in PIPELINE_STAGES],
        help="Run a single pipeline stage (00 through 05).",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Run end-to-end pipeline in fast 5-camera pilot mode.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all implemented stages across the full 100-camera dataset.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if args.check_contract or not (args.stage or args.sample or args.all):
        ok = validate_contract(strict_all=args.strict)
        return 0 if ok else 1

    target_stages = (
        [s for s in PIPELINE_STAGES if s.stage_id == args.stage]
        if args.stage
        else list(PIPELINE_STAGES)
    )

    for stage in target_stages:
        if not run_stage(stage, sample_mode=args.sample):
            return 1

    ok = validate_contract(strict_all=False)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

