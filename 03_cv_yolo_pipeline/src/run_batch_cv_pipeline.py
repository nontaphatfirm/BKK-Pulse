"""
Batch Computer Vision Pipeline (`Stage 03` -> `vehicle_counts.parquet`).

Processes all valid frames in `Dataset_Clean_V1/image_quality_manifest.parquet`
(or the 5 pilot cameras under `--sample`) camera-by-camera in timestamp order using
`RobustTrafficDetector.predict_batch()`, writes per-camera resume checkpoints,
optionally renders & archives annotated bounding-box images, and emits canonical
Parquet files conforming strictly to `DATA_CONTRACT.md`.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import zipfile

import cv2
import numpy as np
import pandas as pd
import torch


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from robust_detector import (  # noqa: E402
    DEFAULT_BG_DIR,
    DEFAULT_CLEAN_DIR,
    DEFAULT_ROIS_PATH,
    DetectionResult,
    RobustTrafficDetector,
    draw_detections,
)


PILOT_CAMERAS: tuple[int, ...] = (26, 136, 137, 150, 546)

CONTRACT_COLUMNS: tuple[str, ...] = (
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
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Stage 03 batched multi-expert CV detection pipeline to generate vehicle_counts.parquet."
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--sample",
        action="store_true",
        help="Run only the 5 pilot cameras (26, 136, 137, 150, 546) -> data/vehicle_counts_sample.parquet.",
    )
    mode_group.add_argument(
        "--all",
        action="store_true",
        help="Run all 100 valid cameras -> data/vehicle_counts.parquet (default when --cam-ids omitted).",
    )
    parser.add_argument(
        "--cam-ids",
        type=int,
        nargs="+",
        default=None,
        help="Optional explicit camera IDs to process instead of --all/--sample.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of frames to process (for quick smoke tests; disables partial-camera checkpoints).",
    )
    parser.add_argument(
        "--clean-dir",
        type=Path,
        default=DEFAULT_CLEAN_DIR,
        help="Path to Dataset_Clean_V1 directory.",
    )
    parser.add_argument(
        "--bg-dir",
        type=Path,
        default=DEFAULT_BG_DIR,
        help="Path to cached median background plates directory.",
    )
    parser.add_argument(
        "--rois-path",
        type=Path,
        default=DEFAULT_ROIS_PATH,
        help="Path to camera_rois.json.",
    )
    parser.add_argument(
        "--output-parquet",
        type=Path,
        default=None,
        help="Custom output Parquet path (overrides default data/vehicle_counts[_sample].parquet).",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "checkpoints" / "batch_cv",
        help="Directory for per-camera resumable Parquet checkpoints.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Recompute cameras even if valid checkpoint files exist.",
    )
    parser.add_argument(
        "--batch-frames",
        type=int,
        default=None,
        help="Frames per CPU+GPU micro-batch (default: auto by GPU VRAM: A100=24, L4=16, T4=12, 4GB=6).",
    )
    parser.add_argument(
        "--yolo-batch",
        type=int,
        default=None,
        help="Max crops per YOLO forward pass inside predict_batch (default: auto by GPU VRAM: A100=64, L4=48, T4=32, 4GB=16).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=min(12, os.cpu_count() or 4),
        help="CPU threads for OpenCV prep, post-processing & annotated JPEG writes.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Final fused vehicle confidence threshold (default: 0.25).",
    )
    parser.add_argument(
        "--no-roi",
        action="store_true",
        help="Disable camera Road ROI polygon filtering.",
    )
    parser.add_argument(
        "--no-temporal-gate",
        action="store_true",
        help="Disable adjacent-frame stationary vehicle suppression.",
    )
    parser.add_argument(
        "--save-images",
        action="store_true",
        help="Render annotated bounding-box JPEGs via draw_detections().",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=PROJECT_ROOT / "runs" / "detect" / "batch_annotated",
        help="Output folder for annotated JPEGs (<images_dir>/<cam_id>/<filename>).",
    )
    parser.add_argument(
        "--images-zip-dir",
        type=Path,
        default=None,
        help="Optional persistent directory for per-camera image zip checkpoints (<images_zip_dir>/cam_<id>.zip).",
    )
    parser.add_argument(
        "--save-scale",
        type=float,
        default=1.5,
        help="Upscale factor when saving annotated JPEGs (default: 1.5).",
    )
    parser.add_argument(
        "--zip-images",
        action="store_true",
        help="Package saved annotated JPEGs into fast ZIP_STORED archive(s) after batch inference.",
    )
    parser.add_argument(
        "--zip-path",
        type=Path,
        default=None,
        help="Output path for annotated images zip (default: <images_dir>.zip).",
    )
    return parser.parse_args()


def load_target_manifest(
    clean_dir: Path,
    cam_ids: list[int] | None = None,
    sample_only: bool = False,
    limit: int | None = None,
) -> pd.DataFrame:
    """Load valid clean frames sorted by `(cam_id, timestamp)` for deterministic sequential context."""
    manifest_path = clean_dir / "image_quality_manifest.parquet"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing quality manifest: {manifest_path}")

    cols = ["cam_id", "timestamp", "hour", "clean_filename", "clean_rel_path", "is_valid", "quality_warning"]
    df = pd.read_parquet(manifest_path, columns=cols)
    df = df[df["is_valid"] & (df["quality_warning"] == "none")].copy()
    df["cam_id"] = df["cam_id"].astype("int64")
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None).astype("datetime64[us]")
    df["hour"] = df["hour"].astype("int64")

    if cam_ids is not None:
        target_set = {int(c) for c in cam_ids}
        df = df[df["cam_id"].isin(target_set)].copy()
    elif sample_only:
        df = df[df["cam_id"].isin(PILOT_CAMERAS)].copy()

    df.sort_values(["cam_id", "timestamp"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    if limit is not None and limit > 0:
        df = df.iloc[: int(limit)].copy()
        df.reset_index(drop=True, inplace=True)

    return df


def enforce_contract_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Reorder columns and enforce exact DATA_CONTRACT.md numeric & datetime types."""
    out = df.loc[:, list(CONTRACT_COLUMNS)].copy()
    int_cols = (
        "cam_id",
        "car_count",
        "motorcycle_count",
        "bus_count",
        "truck_count",
        "total_vehicle_count",
        "filtered_static_boxes",
    )
    float_cols = (
        "pcu_score",
        "bbox_total_area",
        "road_roi_area",
        "road_occupancy_ratio",
        "foreground_ratio",
    )
    for c in int_cols:
        out[c] = out[c].astype("int64")
    for c in float_cols:
        out[c] = out[c].astype("float64")
    out["timestamp"] = pd.to_datetime(out["timestamp"]).dt.tz_localize(None).astype("datetime64[us]")
    out.sort_values(["cam_id", "timestamp"], inplace=True)
    out.reset_index(drop=True, inplace=True)
    return out


def write_parquet_atomic(df: pd.DataFrame, target_path: Path) -> None:
    """Write a Parquet file via a temporary sibling file so crashes never corrupt checkpoints."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_suffix(".parquet.tmp")
    df.to_parquet(tmp_path, index=False, compression="snappy")
    os.replace(tmp_path, target_path)


def is_valid_camera_checkpoint(
    ckpt_path: Path,
    expected_cam_df: pd.DataFrame,
    save_images: bool = False,
    images_dir: Path | None = None,
    images_zip_dir: Path | None = None,
) -> bool:
    """Return True iff `ckpt_path` matches expected timestamps (and images/zip exist when `--save-images` is on)."""
    if not ckpt_path.is_file():
        return False
    try:
        saved = pd.read_parquet(ckpt_path)
    except Exception:
        return False
    if any(col not in saved.columns for col in CONTRACT_COLUMNS):
        return False
    if len(saved) != len(expected_cam_df):
        return False
    saved_ts = pd.to_datetime(saved["timestamp"]).dt.tz_localize(None).astype("datetime64[us]")
    exp_ts = pd.to_datetime(expected_cam_df["timestamp"]).dt.tz_localize(None).astype("datetime64[us]")
    if set(saved_ts.tolist()) != set(exp_ts.tolist()):
        return False
    if save_images:
        cam_id = int(expected_cam_df["cam_id"].iloc[0])
        expected_names = expected_cam_df["clean_filename"].astype(str).tolist()
        if images_zip_dir is not None:
            cam_zip = images_zip_dir / f"cam_{cam_id}.zip"
            if not cam_zip.is_file():
                return False
            try:
                with zipfile.ZipFile(cam_zip, "r") as zf:
                    archived = set(zf.namelist())
            except Exception:
                return False
            expected_arcs = {f"{cam_id}/{fn}" for fn in expected_names}
            if not expected_arcs.issubset(archived):
                return False
        elif images_dir is not None:
            cam_img_dir = images_dir / str(cam_id)
            if not cam_img_dir.is_dir():
                return False
            if not all((cam_img_dir / fn).is_file() for fn in expected_names):
                return False
    return True


def write_camera_images_zip_atomic(
    cam_id: int,
    cam_img_dir: Path,
    expected_names: list[str],
    target_zip: Path,
) -> Path:
    """Pack one camera's annotated JPEGs into a per-camera ZIP_STORED archive and commit atomically."""
    target_zip.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f"cam_{cam_id}_", suffix=".zip.tmp", delete=False) as tf:
        local_tmp = Path(tf.name)
    remote_tmp = target_zip.with_suffix(".zip.tmp")
    try:
        with zipfile.ZipFile(local_tmp, mode="w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
            for fn in expected_names:
                fpath = cam_img_dir / fn
                if not fpath.is_file():
                    raise FileNotFoundError(f"Missing annotated image for cam_{cam_id}: {fpath}")
                zf.write(fpath, arcname=f"{cam_id}/{fn}")
        shutil.copy2(local_tmp, remote_tmp)
        os.replace(remote_tmp, target_zip)
    finally:
        local_tmp.unlink(missing_ok=True)
        if remote_tmp.exists() and target_zip.exists():
            remote_tmp.unlink(missing_ok=True)
    return target_zip


def result_to_contract_row(cam_id: int, timestamp: pd.Timestamp, res: DetectionResult) -> dict:
    """Convert a `DetectionResult` into one contract-compliant record."""
    car_c = int(res.counts.get("car", 0))
    moto_c = int(res.counts.get("motorcycle", 0))
    bus_c = int(res.counts.get("bus", 0))
    truck_c = int(res.counts.get("truck", 0))
    total_c = car_c + moto_c + bus_c + truck_c
    pcu = 1.0 * car_c + 0.33 * moto_c + 2.5 * bus_c + 2.5 * truck_c
    return {
        "cam_id": int(cam_id),
        "timestamp": timestamp,
        "car_count": car_c,
        "motorcycle_count": moto_c,
        "bus_count": bus_c,
        "truck_count": truck_c,
        "total_vehicle_count": total_c,
        "pcu_score": round(float(pcu), 4),
        "bbox_total_area": float(res.bbox_total_area),
        "road_roi_area": float(res.road_roi_area),
        "road_occupancy_ratio": float(res.road_occupancy_ratio),
        "foreground_ratio": float(res.foreground_ratio),
        "filtered_static_boxes": int(res.suppressed_static_count),
    }


def _save_annotated_batch(
    save_tasks: list[tuple[np.ndarray, DetectionResult, str, Path]],
    scale: float,
    workers: int,
) -> None:
    """Render & write annotated JPEGs concurrently using OpenCV."""
    if not save_tasks:
        return

    def _write_one(task: tuple[np.ndarray, DetectionResult, str, Path]) -> None:
        img_bgr, det_res, title, out_path = task
        vis = draw_detections(img_bgr, det_res, title=title, scale=scale, show_roi=True)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_path), vis, [cv2.IMWRITE_JPEG_QUALITY, 90])

    if workers > 1 and len(save_tasks) > 1:
        with ThreadPoolExecutor(max_workers=min(workers, len(save_tasks))) as pool:
            list(pool.map(_write_one, save_tasks))
    else:
        for t in save_tasks:
            _write_one(t)


def package_images_zip(images_dir: Path, zip_path: Path) -> Path:
    """Archive generated annotated JPEGs quickly using ZIP_STORED (no redundant JPEG re-compression)."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_zip = zip_path.with_suffix(".zip.tmp")
    img_files = sorted(p for p in images_dir.rglob("*.jpg") if p.is_file())
    with zipfile.ZipFile(tmp_zip, mode="w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
        for fpath in img_files:
            zf.write(fpath, arcname=fpath.relative_to(images_dir).as_posix())
    os.replace(tmp_zip, zip_path)
    return zip_path


def process_camera(
    detector: RobustTrafficDetector,
    cam_id: int,
    cam_df: pd.DataFrame,
    clean_dir: Path,
    batch_frames: int,
    yolo_batch: int,
    workers: int,
    conf: float,
    use_temporal_gate: bool,
    save_images: bool,
    images_dir: Path,
    save_scale: float,
) -> pd.DataFrame:
    """Run batched inference over one camera's time-sorted frames."""
    rows: list[dict] = []
    n_cam = len(cam_df)
    paths = [clean_dir / str(p) for p in cam_df["clean_rel_path"].tolist()]
    timestamps = cam_df["timestamp"].tolist()
    hours = [int(h) for h in cam_df["hour"].tolist()]
    filenames = [str(fn) for fn in cam_df["clean_filename"].tolist()]

    for start in range(0, n_cam, max(1, batch_frames)):
        end = min(n_cam, start + max(1, batch_frames))
        chunk_paths = paths[start:end]
        chunk_hours = hours[start:end]
        chunk_cams = [cam_id] * (end - start)

        batch_out = detector.predict_batch(
            image_sources=chunk_paths,
            conf=conf,
            cam_ids=chunk_cams,
            hours=chunk_hours,
            use_temporal_gate=use_temporal_gate,
            yolo_batch=yolo_batch,
            num_workers=workers,
            return_images=save_images,
        )

        save_tasks: list[tuple[np.ndarray, DetectionResult, str, Path]] = []
        for offset, item in enumerate(batch_out):
            idx = start + offset
            if save_images:
                det_res, img_bgr = item  # type: ignore[misc]
                ts_str = pd.Timestamp(timestamps[idx]).strftime("%Y-%m-%d %H:%M")
                out_jpg = images_dir / str(cam_id) / filenames[idx]
                save_tasks.append((img_bgr, det_res, f"cam_{cam_id} {ts_str}", out_jpg))
            else:
                det_res = item  # type: ignore[assignment]
            rows.append(result_to_contract_row(cam_id, timestamps[idx], det_res))

        if save_images and save_tasks:
            _save_annotated_batch(save_tasks, scale=save_scale, workers=workers)

    return enforce_contract_dtypes(pd.DataFrame(rows))


def resolve_batch_defaults(batch_frames: int | None, yolo_batch: int | None) -> tuple[int, int, str]:
    """Select GPU-VRAM-safe default `(batch_frames, yolo_batch)` while honoring explicit CLI overrides."""
    if not torch.cuda.is_available():
        rec_frames, rec_yolo, hw_desc = 4, 8, "CPU"
    else:
        props = torch.cuda.get_device_properties(0)
        vram_gb = props.total_memory / (1024 ** 3)
        hw_desc = f"{props.name} ({vram_gb:.1f} GB)"
        if vram_gb >= 35.0:
            rec_frames, rec_yolo = 24, 64
        elif vram_gb >= 18.0:
            rec_frames, rec_yolo = 16, 48
        elif vram_gb >= 8.0:
            rec_frames, rec_yolo = 12, 32
        else:
            rec_frames, rec_yolo = 6, 16
    return (
        rec_frames if batch_frames is None else int(batch_frames),
        rec_yolo if yolo_batch is None else int(yolo_batch),
        hw_desc,
    )


def main() -> int:
    args = parse_args()
    batch_frames, yolo_batch, hw_desc = resolve_batch_defaults(args.batch_frames, args.yolo_batch)

    is_full_all_mode = (not args.sample) and (args.cam_ids is None) and (args.limit is None)
    if args.output_parquet is not None:
        output_parquet = args.output_parquet
    elif args.sample:
        output_parquet = PROJECT_ROOT / "data" / "vehicle_counts_sample.parquet"
    else:
        output_parquet = PROJECT_ROOT / "data" / "vehicle_counts.parquet"

    target_df = load_target_manifest(
        clean_dir=args.clean_dir,
        cam_ids=args.cam_ids,
        sample_only=bool(args.sample),
        limit=args.limit,
    )
    if target_df.empty:
        raise RuntimeError("No valid frames matched the requested filters.")

    cam_groups = [(int(cid), grp.reset_index(drop=True)) for cid, grp in target_df.groupby("cam_id", sort=True)]
    total_target_frames = len(target_df)
    total_cams = len(cam_groups)

    # Identify which cameras would be incomplete under --limit vs full manifest counts
    full_cam_counts: dict[int, int] = {}
    if args.limit is not None:
        full_df = load_target_manifest(clean_dir=args.clean_dir, cam_ids=args.cam_ids, sample_only=bool(args.sample), limit=None)
        full_cam_counts = {int(cid): int(len(grp)) for cid, grp in full_df.groupby("cam_id", sort=False)}
    else:
        full_cam_counts = {cid: len(grp) for cid, grp in cam_groups}

    print("=" * 76)
    print("Stage 03: Batched Multi-Expert YOLO Vehicle Detection Pipeline")
    print("=" * 76)
    print(f"Compute device : {hw_desc}")
    print(f"Target cameras : {total_cams} ({'sample 5 cams' if args.sample else 'custom/all'})")
    print(f"Target frames  : {total_target_frames:,}")
    print(f"Output parquet : {output_parquet}")
    print(f"Checkpoints    : {args.checkpoint_dir} (resume={'OFF' if args.no_resume else 'ON'})")
    print(f"Batch settings : batch_frames={batch_frames}, yolo_batch={yolo_batch}, workers={args.workers}, conf={args.conf}")
    print(f"Annotated JPGs : {'ON -> ' + str(args.images_dir) + f' (scale={args.save_scale})' if args.save_images else 'OFF'}")
    if args.save_images and args.images_zip_dir is not None:
        print(f"Per-cam zip ckpt: {args.images_zip_dir}")

    detector = RobustTrafficDetector(
        clean_dir=args.clean_dir,
        bg_dir=args.bg_dir,
        roi_path=None if args.no_roi else args.rois_path,
        use_roi=not args.no_roi,
    )

    t0 = time.perf_counter()
    completed_frames = 0
    inferred_frames = 0
    resumed_cams = 0
    cam_dfs: list[pd.DataFrame] = []

    for cam_idx, (cam_id, cam_df) in enumerate(cam_groups, start=1):
        n_cam = len(cam_df)
        is_complete_cam = n_cam == full_cam_counts.get(cam_id, n_cam)
        ckpt_path = args.checkpoint_dir / f"cam_{cam_id}.parquet"

        if (
            not args.no_resume
            and is_complete_cam
            and is_valid_camera_checkpoint(
                ckpt_path,
                cam_df,
                save_images=args.save_images,
                images_dir=args.images_dir,
                images_zip_dir=args.images_zip_dir,
            )
        ):
            cached_df = enforce_contract_dtypes(pd.read_parquet(ckpt_path))
            cam_dfs.append(cached_df)
            completed_frames += n_cam
            resumed_cams += 1
            print(
                f"[RESUME {cam_idx:>3}/{total_cams}] cam_{cam_id:<4} -> skipped ({n_cam:,} frames cached) | "
                f"Progress {completed_frames:,}/{total_target_frames:,}"
            )
            continue

        cam_t0 = time.perf_counter()
        cam_res_df = process_camera(
            detector=detector,
            cam_id=cam_id,
            cam_df=cam_df,
            clean_dir=args.clean_dir,
            batch_frames=batch_frames,
            yolo_batch=yolo_batch,
            workers=args.workers,
            conf=args.conf,
            use_temporal_gate=not args.no_temporal_gate,
            save_images=args.save_images,
            images_dir=args.images_dir,
            save_scale=args.save_scale,
        )
        cam_dt = max(time.perf_counter() - cam_t0, 1e-6)
        if is_complete_cam:
            if args.save_images and args.images_zip_dir is not None:
                expected_names = cam_df["clean_filename"].astype(str).tolist()
                write_camera_images_zip_atomic(
                    cam_id=cam_id,
                    cam_img_dir=args.images_dir / str(cam_id),
                    expected_names=expected_names,
                    target_zip=args.images_zip_dir / f"cam_{cam_id}.zip",
                )
            write_parquet_atomic(cam_res_df, ckpt_path)

        cam_dfs.append(cam_res_df)
        completed_frames += n_cam
        inferred_frames += n_cam
        total_dt = max(time.perf_counter() - t0, 1e-6)
        inf_fps = inferred_frames / total_dt
        rem_frames = max(0, total_target_frames - completed_frames)
        eta_min = (rem_frames / inf_fps) / 60.0 if inf_fps > 0 else 0.0
        tot_vehicles = int(cam_res_df["total_vehicle_count"].sum())
        print(
            f"[CAM {cam_idx:>3}/{total_cams}] cam_{cam_id:<4} | {n_cam:>4} frames in {cam_dt:5.1f}s "
            f"({n_cam / cam_dt:4.1f} img/s) | Veh={tot_vehicles:>5,} | "
            f"Done {completed_frames:,}/{total_target_frames:,} ({100.0 * completed_frames / total_target_frames:5.1f}%) | "
            f"ETA {eta_min:5.1f}m"
        )

    final_df = enforce_contract_dtypes(pd.concat(cam_dfs, ignore_index=True))
    null_pk = int(final_df[["cam_id", "timestamp"]].isna().any(axis=1).sum())
    dup_pk = int(final_df.duplicated(subset=["cam_id", "timestamp"]).sum())
    if null_pk > 0 or dup_pk > 0:
        raise RuntimeError(f"Primary key violation: {null_pk} nulls, {dup_pk} duplicates.")

    write_parquet_atomic(final_df, output_parquet)
    print(f"[OK] Wrote {output_parquet} ({len(final_df):,} rows, {final_df['cam_id'].nunique()} cameras)")

    # Auto-derive vehicle_counts_sample.parquet whenever a complete 100-camera full run finishes.
    if is_full_all_mode and args.output_parquet is None:
        sample_df = enforce_contract_dtypes(final_df[final_df["cam_id"].isin(PILOT_CAMERAS)].copy())
        if len(sample_df) > 0:
            sample_out = PROJECT_ROOT / "data" / "vehicle_counts_sample.parquet"
            write_parquet_atomic(sample_df, sample_out)
            print(f"[OK] Derived {sample_out} ({len(sample_df):,} pilot rows)")

    if args.save_images and args.zip_images:
        zip_target = args.zip_path if args.zip_path is not None else args.images_dir.with_suffix(".zip")
        z_t0 = time.perf_counter()
        archived = package_images_zip(args.images_dir, zip_target)
        size_mb = archived.stat().st_size / (1024 ** 2)
        print(f"[OK] Packaged annotated images zip -> {archived} ({size_mb:.1f} MB in {time.perf_counter() - z_t0:.1f}s)")

    summary = {
        "total_rows": int(len(final_df)),
        "cameras": int(final_df["cam_id"].nunique()),
        "resumed_cameras": int(resumed_cams),
        "inferred_frames": int(inferred_frames),
        "total_elapsed_sec": round(time.perf_counter() - t0, 2),
        "car_sum": int(final_df["car_count"].sum()),
        "motorcycle_sum": int(final_df["motorcycle_count"].sum()),
        "bus_sum": int(final_df["bus_count"].sum()),
        "truck_sum": int(final_df["truck_count"].sum()),
        "total_vehicle_sum": int(final_df["total_vehicle_count"].sum()),
        "output_parquet": str(output_parquet),
    }
    print("Summary:", json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
