"""
100-Camera Stratified Edge-Case Benchmark & Visual Evaluation Suite (`03_cv_yolo_pipeline`).

Samples clean, non-corrupted edge-case frames across ALL 100 BMA CCTV cameras:
  1. Nighttime & strong headlight glare (`night_glare`)
  2. Dense mixed car + motorcycle queues (`dense_mixed_rush`)
  3. Heavy rainfall & wet-road specular reflections (`rain_wet_road`)
  4. Blurry / low-contrast / non-standard resolution cameras (`blurry_degraded`)
  5. Static false-positive traps: zebra markings, billboards, parked lots, OSD (`static_traps`)
  6. Remaining camera angles across all 7 corridors (`all_cameras_coverage`)

Runs `RobustTrafficDetector` (`ensemble`) across the entire sampled set, benchmarks it
side-by-side against the individual cached models (`yolo26x.pt`, `visdrone-yolo11x`, `UVH-26`)
on showcase edge cases, and saves annotated images, 2x2 comparison grids, category montages,
and CSV/JSON summary metrics to `runs/detect/edge_case_eval/`.

Usage:
    python 03_cv_yolo_pipeline/src/evaluate_edge_cases.py
    python 03_cv_yolo_pipeline/src/evaluate_edge_cases.py --quick
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np
import pandas as pd
import torch
from ultralytics import YOLO

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from predict_yolo26x import (
    VEHICLE_CLASSES_LOWER,
    apply_nms_and_remap,
    collect_detections,
    resolve_model_source,
)
from robust_detector import (
    CLASS_COLORS_BGR,
    CANONICAL_ID_TO_NAME,
    DetectionResult,
    RobustTrafficDetector,
    draw_detections,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLEAN_DIR = PROJECT_ROOT / "Dataset_Clean_V1"
EXT_PATH = PROJECT_ROOT / "data" / "external_weather_poi.parquet"
OUT_DIR = PROJECT_ROOT / "runs" / "detect" / "edge_case_eval"


# Iconic showcase frames explicitly covering hard edge cases observed in EDA & user audit.
ICONIC_EDGE_CASES: list[tuple[str, int, str, str]] = [
    ("night_glare", 75, "75_20260831_200047.jpg", "Night wet-road glare + zebra marking trap"),
    ("night_glare", 1078, "1078_20260825_205117.jpg", "Night glare + ZONTES billboard + OSD text"),
    ("night_glare", 546, "546_20260825_200045.jpg", "Severe headlight bloom + wide intersection"),
    ("night_glare", 112, "112_20260831_192039.jpg", "Night intersection + off-road parked lane + OSD"),
    ("night_glare", 178, "178_20260831_205115.jpg", "Night rain reflection under BTS pillars"),
    ("night_glare", 250, "250_20260831_201109.jpg", "Night overhead + bus & headlights"),
    ("night_glare", 11, "11_20260831_201509.jpg", "Night wet road + bus + fast glare streaks"),
    ("night_glare", 18, "18_20260831_200055.jpg", "OSD-occluded foreground cars + intense night glare"),
    ("dense_mixed_rush", 26, "26_20260825_074041.jpg", "Extreme dense morning cars + motorcycles + OSD"),
    ("dense_mixed_rush", 75, "75_20260826_133548.jpg", "Oblique angle mixed cars + stop-line motos"),
    ("dense_mixed_rush", 136, "136_20260825_140614.jpg", "Footbridge view + off-road parking + stairs"),
    ("dense_mixed_rush", 395, "395_20260825_140105.jpg", "348x261 wide intersection + tuk-tuks + shopfronts"),
    ("dense_mixed_rush", 123, "123_20260829_145051.jpg", "Vehicles crossing top/bottom OSD timestamp bars"),
    ("blurry_degraded", 370, "370_20260825_140539.jpg", "Low-contrast hazy/blurry lens daytime"),
    ("blurry_degraded", 370, "370_20260825_200537.jpg", "Low-contrast hazy/blurry lens nighttime + zebra"),
    ("blurry_degraded", 371, "371_20260825_140539.jpg", "Low-contrast degraded lens daytime"),
    ("blurry_degraded", 371, "371_20260825_200537.jpg", "Low-contrast degraded lens nighttime"),
    ("rain_wet_road", 529, "529_20260830_160514.jpg", "Heavy monsoon rain fog (Cam 529 storm)"),
    ("rain_wet_road", 604, "604_20260830_150557.jpg", "Pouring rain intersection + spray & signs"),
    ("rain_wet_road", 599, "599_20260830_150059.jpg", "Pouring rain + water droplets on lens + crosswalk"),
    ("rain_wet_road", 141, "141_20260830_163638.jpg", "Afternoon thunderstorm mist + low contrast"),
    ("rain_wet_road", 68, "68_20260830_150122.jpg", "Pouring rain dense urban avenue"),
    ("rain_wet_road", 158, "158_20260829_145605.jpg", "Daytime rain mist + wet asphalt + far queue"),
]

KNOWN_BLURRY_CAMS: set[int] = {
    118, 119, 126, 170, 206, 233, 256, 370, 371, 395, 411, 556, 619, 915, 1060, 1063, 1132, 1362
}


def _is_usable_frame(rel_path: str) -> bool:
    """Verify the image file exists, decodes cleanly, and is not corrupted noise."""
    fpath = CLEAN_DIR / rel_path
    if not fpath.is_file():
        return False
    img = cv2.imread(str(fpath))
    if img is None or img.size == 0:
        return False
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mean_v = float(gray.mean())
    std_v = float(gray.std())
    # Reject completely blown-out or pitch-black/flat sensor drops if any slipped through.
    if std_v < 6.0 or mean_v < 8.0 or mean_v > 250.0:
        return False
    return True


def build_stratified_sample(quick: bool = False) -> pd.DataFrame:
    """Select >= 200 clean, accurately categorized edge-case frames across all 100 cameras."""
    man = pd.read_parquet(CLEAN_DIR / "image_quality_manifest.parquet")
    meta = pd.read_parquet(CLEAN_DIR / "cctv_info_cleaned.parquet")

    df = man[man["is_valid"] & (man["quality_warning"] == "none")].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour_ts"] = df["timestamp"].dt.floor("h")

    # Compute per-camera daytime baseline contrast so visual rain/fog drops are detected accurately.
    day_med = (
        df[df["hour"].between(10, 16)]
        .groupby("cam_id")["contrast_std"]
        .median()
        .rename("med_contrast")
    )
    df = df.merge(day_med, on="cam_id", how="left")
    df["med_contrast"] = df["med_contrast"].fillna(df["contrast_std"])
    df["contrast_drop"] = df["med_contrast"] - df["contrast_std"]
    df["contrast_ratio"] = df["contrast_std"] / df["med_contrast"].clip(lower=1.0)

    if EXT_PATH.is_file():
        ext = pd.read_parquet(EXT_PATH, columns=["cam_id", "timestamp", "rain_mm"])
        ext["timestamp"] = pd.to_datetime(ext["timestamp"])
        df = df.merge(
            ext,
            left_on=["cam_id", "hour_ts"],
            right_on=["cam_id", "timestamp"],
            how="left",
            suffixes=("", "_ext"),
        )
        df.drop(columns=["timestamp_ext"], errors="ignore", inplace=True)
    else:
        df["rain_mm"] = 0.0

    df["rain_mm"] = df["rain_mm"].fillna(0.0)
    df = df.merge(
        meta[["cam_id", "corridor", "district", "location_en", "pair_type"]],
        on="cam_id",
        how="left",
    )

    # Strict visual rain/wet-road masks (never select clear dry sunny daytime frames).
    storm_dates = ("2026-08-25", "2026-08-27", "2026-08-28", "2026-08-29", "2026-08-30", "2026-08-31")
    df["is_day_storm"] = df["date"].isin(storm_dates) & df["hour"].between(9, 17) & (
        (
            (df["contrast_drop"] >= 9.0)
            & (df["contrast_ratio"] <= 0.78)
            & ((df["rain_mm"] >= 0.2) | df["date"].isin(("2026-08-29", "2026-08-30")))
        )
        | ((df["date"] == "2026-08-30") & df["hour"].between(15, 17) & (df["contrast_drop"] >= 5.0))
    )
    df["is_night_wet"] = (df["date"] == "2026-08-31") & df["hour"].between(19, 21) & (df["glare_ratio"] >= 0.025)
    df["is_true_rain"] = df["is_day_storm"] | df["is_night_wet"]

    selected_rows: list[dict] = []
    used_filenames: set[str] = set()
    cam_cats: dict[int, list[str]] = {}
    cat_totals: Counter[str] = Counter()

    def _add_row(row: pd.Series, category: str, note: str, is_showcase: bool) -> bool:
        fname = str(row["clean_filename"])
        if fname in used_filenames:
            return False
        if not _is_usable_frame(str(row["clean_rel_path"])):
            return False
        cid = int(row["cam_id"])
        used_filenames.add(fname)
        cam_cats.setdefault(cid, []).append(category)
        cat_totals[category] += 1
        selected_rows.append(
            {
                "category": category,
                "note": note,
                "is_showcase": is_showcase,
                "cam_id": cid,
                "timestamp": row["timestamp"],
                "hour": int(row["hour"]),
                "corridor": str(row["corridor"]),
                "location_en": str(row["location_en"]),
                "clean_filename": fname,
                "clean_rel_path": str(row["clean_rel_path"]),
                "brightness_mean": float(row["brightness_mean"]),
                "contrast_std": float(row["contrast_std"]),
                "glare_ratio": float(row["glare_ratio"]),
                "mad_from_prev": float(row["mad_from_prev"]),
                "rain_mm": float(row["rain_mm"]),
            }
        )
        return True

    def _pick_first_usable(cand_df: pd.DataFrame, category: str, note: str) -> bool:
        for _, cand in cand_df.head(6).iterrows():
            if _add_row(cand, category, note, is_showcase=False):
                return True
        return False

    # 1. Iconic showcase frames first
    for cat, cid, fname, note in ICONIC_EDGE_CASES:
        match = df[(df["cam_id"] == cid) & (df["clean_filename"] == fname)]
        if not match.empty:
            _add_row(match.iloc[0], cat, note, is_showcase=True)

    # 2. True daytime storm/rain frames first across distinct cameras
    rain_day_pool = df[df["is_day_storm"]].sort_values(["contrast_drop", "mad_from_prev"], ascending=[False, False])
    rain_target = 6 if quick else 24
    rain_added = 0
    for _, r in rain_day_pool.iterrows():
        if rain_added >= rain_target:
            break
        cid = int(r["cam_id"])
        if cid in cam_cats:
            continue
        if _add_row(r, "rain_wet_road", f"Daytime storm/rain mist (contrast_drop={r['contrast_drop']:.1f})", is_showcase=False):
            rain_added += 1

    if quick:
        for cid in [18, 123, 137, 150, 186, 414, 572, 603, 938, 1188, 1368, 1804]:
            if cid in cam_cats:
                continue
            sub = df[df["cam_id"] == cid]
            if not sub.empty:
                cand = sub.sort_values(["glare_ratio", "mad_from_prev"], ascending=False).iloc[0]
                _add_row(cand, "static_traps", "Diverse angle / static trap check", is_showcase=False)
        return pd.DataFrame(selected_rows)

    # 3. Pass 1 (all 100 cameras): assign genuinely matched primary edge case per remaining camera
    all_cams = sorted(meta["cam_id"].unique().tolist())
    pass1_non_rain = ["night_glare", "dense_mixed_rush", "static_traps", "blurry_degraded"]
    cycle_idx = 0
    night_wet_added = 0
    night_wet_cap = 8
    rain_total_cap = 38

    for cid_raw in all_cams:
        cid = int(cid_raw)
        if cid in cam_cats:
            continue
        sub = df[df["cam_id"] == cid]
        if sub.empty:
            continue
        if cid in KNOWN_BLURRY_CAMS:
            blur_sub = sub[sub["hour"].between(9, 17)].sort_values("contrast_std", ascending=True)
            if _pick_first_usable(blur_sub, "blurry_degraded", "Blurry / low-contrast camera sample"):
                continue

        # Add at most `night_wet_cap` severe Aug 31 night wet-road reflection samples across Pass 1
        wet_sub = sub[sub["is_night_wet"]].sort_values("glare_ratio", ascending=False)
        if night_wet_added < night_wet_cap and cat_totals["rain_wet_road"] < rain_total_cap and cycle_idx % 5 == 0 and not wet_sub.empty:
            if _pick_first_usable(wet_sub, "rain_wet_road", "Night wet-road rain reflection"):
                night_wet_added += 1
                cycle_idx += 1
                continue

        cat_pref = pass1_non_rain[cycle_idx % len(pass1_non_rain)]
        cycle_idx += 1
        picked = False
        if cat_pref == "night_glare":
            picked = _pick_first_usable(
                sub[sub["hour"] >= 19].sort_values("glare_ratio", ascending=False),
                "night_glare",
                "100-cam Pass 1 night glare",
            )
        elif cat_pref == "dense_mixed_rush":
            picked = _pick_first_usable(
                sub[sub["hour"].isin([7, 8, 17, 18])].sort_values("mad_from_prev", ascending=False),
                "dense_mixed_rush",
                "100-cam Pass 1 rush-hour mixed flow",
            )
        elif cat_pref == "blurry_degraded":
            blur_cands = sub[sub["hour"].between(9, 17) & (sub["contrast_std"] <= 36.0)].sort_values("contrast_std", ascending=True)
            if not blur_cands.empty:
                picked = _pick_first_usable(blur_cands, "blurry_degraded", "100-cam Pass 1 low-contrast frame")
        if not picked:
            day_act = sub[sub["hour"].between(9, 16)].sort_values("mad_from_prev", ascending=False)
            picked = _pick_first_usable(day_act, "static_traps", "100-cam Pass 1 active static/crosswalk scene")
        if not picked:
            _pick_first_usable(sub.sort_values("mad_from_prev", ascending=False), "dense_mixed_rush", "100-cam fallback")

    # 4. Pass 2 (+100 complementary frames across ALL 100 cameras in a balanced DIFFERENT regime)
    for pass2_idx, cid_raw in enumerate(all_cams):
        cid = int(cid_raw)
        sub = df[df["cam_id"] == cid]
        if sub.empty:
            continue
        existing = set(cam_cats.get(cid, []))

        if "rain_wet_road" not in existing and cat_totals["rain_wet_road"] < rain_total_cap:
            r_day = sub[sub["is_day_storm"]].sort_values("contrast_drop", ascending=False)
            if not r_day.empty and _pick_first_usable(r_day, "rain_wet_road", "100-cam Pass 2 daytime rain mist"):
                continue

        candidates_order: list[str]
        if "night_glare" not in existing and (pass2_idx % 3 != 0 or "dense_mixed_rush" in existing):
            candidates_order = ["night_glare", "dense_mixed_rush", "blurry_degraded", "static_traps"]
        else:
            candidates_order = ["dense_mixed_rush", "static_traps", "blurry_degraded", "night_glare"]

        placed = False
        for target_cat in candidates_order:
            if target_cat in existing:
                continue
            if target_cat == "rain_wet_road" and cat_totals["rain_wet_road"] < rain_total_cap and night_wet_added < night_wet_cap:
                r_ngt = sub[sub["is_night_wet"]].sort_values(["glare_ratio", "mad_from_prev"], ascending=False)
                if not r_ngt.empty and _pick_first_usable(r_ngt, "rain_wet_road", "100-cam Pass 2 night wet-road reflection"):
                    night_wet_added += 1
                    placed = True
                    break
            elif target_cat == "night_glare":
                ngt_cands = sub[sub["hour"] >= 19].sort_values(["mad_from_prev", "glare_ratio"], ascending=False)
                if _pick_first_usable(ngt_cands, "night_glare", "100-cam Pass 2 night glare + OSD traffic"):
                    placed = True
                    break
            elif target_cat == "dense_mixed_rush":
                rush_cands = sub[sub["hour"].isin([7, 8, 17, 18])].sort_values("mad_from_prev", ascending=False)
                if _pick_first_usable(rush_cands, "dense_mixed_rush", "100-cam Pass 2 peak-hour dense queue"):
                    placed = True
                    break
            elif target_cat == "blurry_degraded":
                blur_cands = sub[sub["contrast_std"] <= 36.0].sort_values("contrast_std", ascending=True)
                if not blur_cands.empty and _pick_first_usable(blur_cands, "blurry_degraded", "100-cam Pass 2 low-contrast/hazy"):
                    placed = True
                    break
            elif target_cat == "static_traps":
                day_cands = sub[sub["hour"].between(9, 16)].sort_values("mad_from_prev", ascending=False)
                if _pick_first_usable(day_cands, "static_traps", "100-cam Pass 2 daytime active/OSD trap"):
                    placed = True
                    break

        if not placed:
            _pick_first_usable(sub.sort_values("mad_from_prev", ascending=False), "dense_mixed_rush", "100-cam Pass 2 fallback")

    return pd.DataFrame(selected_rows)


def _run_single_model_baseline(
    model: YOLO,
    model_label: str,
    image_path: Path,
    conf: float = 0.25,
) -> tuple[np.ndarray, dict[str, int]]:
    """Run a single pretrained YOLO checkpoint in grouped-NMS mode and render its boxes."""
    target_ids = [
        cid for cid, name in model.names.items() if str(name).strip().lower() in VEHICLE_CLASSES_LOWER
    ]
    res, raw = collect_detections(
        model=model,
        image_path=image_path,
        imgsz=640,
        conf=conf,
        iou=0.50,
        nms_mode="grouped",
        target_class_ids=target_ids,
        use_sahi=False,
        sahi_grid=2,
        sahi_overlap=0.25,
    )
    final_boxes, final_names = apply_nms_and_remap(
        detections=raw,
        orig_names=res.names,
        nms_mode="grouped",
        iou=0.50,
    )
    img_bgr = cv2.imread(str(image_path))
    if final_boxes.numel() == 0:
        det_res = DetectionResult(
            boxes_xyxy=np.zeros((0, 4), dtype=np.float32),
            scores=np.zeros((0,), dtype=np.float32),
            class_ids=np.zeros((0,), dtype=np.int64),
            class_names=final_names,
            support_counts=np.zeros((0,), dtype=np.int64),
            suppressed_static_count=0,
            optical_profile={},
            counts={},
        )
    else:
        arr = final_boxes.cpu().numpy()
        cls_ids = arr[:, 5].astype(np.int64)
        counts = dict(Counter(final_names[int(c)] for c in cls_ids))
        det_res = DetectionResult(
            boxes_xyxy=arr[:, :4].astype(np.float32),
            scores=arr[:, 4].astype(np.float32),
            class_ids=cls_ids,
            class_names=final_names,
            support_counts=np.ones((len(arr),), dtype=np.int64),
            suppressed_static_count=0,
            optical_profile={},
            counts=counts,
        )
    vis = draw_detections(img_bgr, det_res, title=model_label, scale=1.5)
    return vis, det_res.counts


def _build_grid(panels: list[np.ndarray], cols: int = 2, pad: int = 8) -> np.ndarray:
    """Arrange equal-height or padded BGR panels into a crisp visual contact sheet."""
    if not panels:
        return np.zeros((100, 100, 3), dtype=np.uint8)
    max_h = max(p.shape[0] for p in panels)
    max_w = max(p.shape[1] for p in panels)
    rows = (len(panels) + cols - 1) // cols
    grid_h = rows * max_h + (rows + 1) * pad
    grid_w = cols * max_w + (cols + 1) * pad
    canvas = np.full((grid_h, grid_w, 3), 20, dtype=np.uint8)
    for idx, panel in enumerate(panels):
        r = idx // cols
        c = idx % cols
        y0 = pad + r * (max_h + pad)
        x0 = pad + c * (max_w + pad)
        ph, pw = panel.shape[:2]
        canvas[y0 : y0 + ph, x0 : x0 + pw] = panel
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Robust Ensemble Detector across 100-camera edge cases")
    parser.add_argument("--quick", action="store_true", help="Run fast ~30-image showcase subset instead of all 100 cameras")
    parser.add_argument("--conf", type=float, default=0.25, help="Final confidence threshold (default: 0.25)")
    parser.add_argument("--no-roi", action="store_true", help="Disable per-camera Road ROI filtering")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img_out_dir = OUT_DIR / "images"
    cmp_out_dir = OUT_DIR / "comparisons"
    montage_out_dir = OUT_DIR / "montages"
    for d in (img_out_dir, cmp_out_dir, montage_out_dir):
        d.mkdir(parents=True, exist_ok=True)
        for stale in d.glob("*.jpg"):
            stale.unlink()

    sample_df = build_stratified_sample(quick=args.quick)
    print(f"Sampled {len(sample_df)} edge-case frames across {sample_df['cam_id'].nunique()} unique cameras.")
    print("Category breakdown:", sample_df["category"].value_counts().to_dict())

    detector = RobustTrafficDetector(use_roi=not args.no_roi)
    print(f"Road ROI filtering: {'ENABLED (' + str(detector.roi_provider.roi_path) + ')' if detector.use_roi else 'DISABLED'}")

    records: list[dict] = []
    showcase_panels: list[tuple[pd.Series, np.ndarray]] = []
    category_panels: dict[str, list[np.ndarray]] = {}

    t_start = time.perf_counter()
    for idx, row in sample_df.iterrows():
        img_path = CLEAN_DIR / str(row["clean_rel_path"])
        t0 = time.perf_counter()
        res = detector.predict(img_path, conf=args.conf)
        dt_ms = (time.perf_counter() - t0) * 1000.0

        img_bgr = cv2.imread(str(img_path))
        cat = str(row["category"])
        cid = int(row["cam_id"])
        title = f"{cat} | Cam {cid}"
        vis_full = draw_detections(img_bgr, res, title=f"{title} | {row['clean_filename']}", scale=2.0)
        out_name = f"{cat}_cam{cid}_{Path(row['clean_filename']).stem}.jpg"
        cv2.imwrite(str(img_out_dir / out_name), vis_full)

        vis_compact = draw_detections(img_bgr, res, title=title, scale=1.5)
        category_panels.setdefault(cat, []).append(vis_compact)
        if bool(row["is_showcase"]):
            showcase_panels.append((row, draw_detections(img_bgr, res, title="Ensemble (Ours)", scale=1.5)))

        cnt = res.counts
        total_v = int(len(res.scores))
        pcu = (
            1.0 * cnt.get("car", 0)
            + 0.33 * cnt.get("motorcycle", 0)
            + 2.5 * cnt.get("bus", 0)
            + 2.5 * cnt.get("truck", 0)
        )
        multi_model_rate = float((res.support_counts >= 2).mean()) if total_v > 0 else 1.0

        records.append(
            {
                "category": cat,
                "cam_id": cid,
                "corridor": row["corridor"],
                "clean_filename": row["clean_filename"],
                "note": row["note"],
                "hour": int(row["hour"]),
                "brightness_mean": row["brightness_mean"],
                "contrast_std": row["contrast_std"],
                "glare_ratio": row["glare_ratio"],
                "rain_mm": row["rain_mm"],
                "is_night_or_glare": bool(res.optical_profile.get("is_night_or_glare")),
                "is_low_contrast_or_rain": bool(res.optical_profile.get("is_low_contrast_or_rain")),
                "car_count": cnt.get("car", 0),
                "motorcycle_count": cnt.get("motorcycle", 0),
                "bus_count": cnt.get("bus", 0),
                "truck_count": cnt.get("truck", 0),
                "total_vehicles": total_v,
                "pcu_score": round(pcu, 2),
                "bbox_total_area": float(res.bbox_total_area),
                "road_roi_area": float(res.road_roi_area),
                "road_occupancy_ratio": float(res.road_occupancy_ratio),
                "foreground_ratio": float(res.foreground_ratio),
                "suppressed_static_boxes": int(res.suppressed_static_count),
                "suppressed_roi_boxes": int(res.suppressed_roi_count),
                "multi_model_agreement_rate": round(multi_model_rate, 3),
                "inference_ms": round(dt_ms, 1),
                "output_image": str((img_out_dir / out_name).relative_to(PROJECT_ROOT)),
            }
        )

        if (len(records) % 20 == 0) or (len(records) == len(sample_df)):
            print(
                f"  Processed {len(records)}/{len(sample_df)} frames "
                f"(last: Cam {cid}, {total_v} vehicles, roi_sup={res.suppressed_roi_count}, {dt_ms:.0f} ms)"
            )

    total_sec = time.perf_counter() - t_start
    res_df = pd.DataFrame(records)
    res_df.to_csv(OUT_DIR / "edge_case_eval_summary.csv", index=False)

    # Save 3x2 contact sheets per edge-case category for easy visual inspection.
    for cat, panels in category_panels.items():
        chunk_size = 6
        for page_idx in range(0, len(panels), chunk_size):
            chunk = panels[page_idx : page_idx + chunk_size]
            grid = _build_grid(chunk, cols=2, pad=8)
            cv2.imwrite(str(montage_out_dir / f"montage_{cat}_p{page_idx // chunk_size + 1}.jpg"), grid)

    # Build 2x2 side-by-side comparisons vs single pretrained models on showcase images.
    print("Generating side-by-side single-model vs ensemble comparison grids on showcase edge cases...")
    y26_model = detector.models["yolo26x"]
    vis_model = detector.models["visdrone"]
    uvh_model = detector.models["uvh26"]
    cmp_records: list[dict] = []

    for row, ens_panel in showcase_panels:
        img_path = CLEAN_DIR / str(row["clean_rel_path"])
        p_y26, c_y26 = _run_single_model_baseline(y26_model, "YOLO26x (COCO)", img_path, conf=args.conf)
        p_vis, c_vis = _run_single_model_baseline(vis_model, "VisDrone-YOLOv11x", img_path, conf=args.conf)
        p_uvh, c_uvh = _run_single_model_baseline(uvh_model, "UVH-26 (YOLOv11x)", img_path, conf=args.conf)

        grid = _build_grid([p_y26, p_vis, p_uvh, ens_panel], cols=2, pad=10)
        cmp_name = f"cmp_{row['category']}_cam{int(row['cam_id'])}_{Path(row['clean_filename']).stem}.jpg"
        cv2.imwrite(str(cmp_out_dir / cmp_name), grid)

        ens_row = res_df[res_df["clean_filename"] == row["clean_filename"]].iloc[0]
        cmp_records.append(
            {
                "clean_filename": row["clean_filename"],
                "category": row["category"],
                "note": row["note"],
                "yolo26x_total": int(sum(c_y26.values())),
                "yolo26x_counts": c_y26,
                "visdrone_total": int(sum(c_vis.values())),
                "visdrone_counts": c_vis,
                "uvh26_total": int(sum(c_uvh.values())),
                "uvh26_counts": c_uvh,
                "ensemble_total": int(ens_row["total_vehicles"]),
                "ensemble_suppressed_static": int(ens_row["suppressed_static_boxes"]),
                "ensemble_suppressed_roi": int(ens_row["suppressed_roi_boxes"]),
                "ensemble_road_occupancy_ratio": float(ens_row["road_occupancy_ratio"]),
                "ensemble_counts": {
                    "car": int(ens_row["car_count"]),
                    "motorcycle": int(ens_row["motorcycle_count"]),
                    "bus": int(ens_row["bus_count"]),
                    "truck": int(ens_row["truck_count"]),
                },
            }
        )

    summary_payload = {
        "roi_enabled": bool(detector.use_roi),
        "total_frames_evaluated": int(len(res_df)),
        "unique_cameras_covered": int(res_df["cam_id"].nunique()),
        "total_elapsed_sec": round(total_sec, 2),
        "mean_inference_ms": round(float(res_df["inference_ms"].mean()), 1),
        "total_vehicles_detected": int(res_df["total_vehicles"].sum()),
        "total_static_boxes_suppressed": int(res_df["suppressed_static_boxes"].sum()),
        "total_roi_boxes_suppressed": int(res_df["suppressed_roi_boxes"].sum()),
        "mean_road_occupancy_ratio": round(float(res_df["road_occupancy_ratio"].mean()), 4),
        "mean_foreground_ratio": round(float(res_df["foreground_ratio"].mean()), 4),
        "mean_multi_model_agreement": round(float(res_df["multi_model_agreement_rate"].mean()), 3),
        "by_category": res_df.groupby("category")
        .agg(
            frames=("cam_id", "count"),
            unique_cams=("cam_id", "nunique"),
            mean_cars=("car_count", "mean"),
            mean_motorcycles=("motorcycle_count", "mean"),
            mean_total=("total_vehicles", "mean"),
            total_suppressed=("suppressed_static_boxes", "sum"),
            total_roi_suppressed=("suppressed_roi_boxes", "sum"),
            mean_occupancy=("road_occupancy_ratio", "mean"),
            mean_agreement=("multi_model_agreement_rate", "mean"),
        )
        .round(3)
        .to_dict(orient="index"),
        "showcase_comparisons": cmp_records,
    }
    with (OUT_DIR / "edge_case_eval_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2, ensure_ascii=False)

    print("\n=== Edge-Case Evaluation Summary ===")
    print(f"Frames: {len(res_df)} | Unique Cameras: {res_df['cam_id'].nunique()} / 100 | Elapsed: {total_sec:.1f}s")
    print(
        f"Total Vehicles: {res_df['total_vehicles'].sum()} | Suppressed Static: {res_df['suppressed_static_boxes'].sum()} "
        f"| Suppressed Off-ROI: {res_df['suppressed_roi_boxes'].sum()}"
    )
    print(
        f"Mean Road Occupancy: {res_df['road_occupancy_ratio'].mean():.4f} | "
        f"Mean Foreground Ratio: {res_df['foreground_ratio'].mean():.4f} | "
        f"Mean Agreement: {res_df['multi_model_agreement_rate'].mean():.3f}"
    )
    print(f"Results saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
