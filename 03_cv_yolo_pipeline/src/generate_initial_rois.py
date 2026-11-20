"""
Automated Initial Per-Camera Road ROI Generator V3 (`03_cv_yolo_pipeline`).

Discovers active traffic carriageways across all 100 BMA CCTV cameras using a
two-pass memory-safe GPU pipeline combining empirical multi-frame traffic cues
with Segment Anything 2.1 (`sam2.1_b.pt`) physical boundary segmentation:

  Pass 1 (Dynamic Traffic & Motion Evidence):
    - Samples up to 128 daytime/shoulder frames for pixel motion and 48 frames for
      batched YOLO inference (`yolo26x.pt` + `dronefreak/visdrone-yolo26l`).
    - Filters boxes against clean daytime median background (`fg15 >= 0.22`,
      `Sobel NCC < 0.62`), upper low-conf billboards, and long-horizon static
      parked cars (`IoU >= 0.65` in >= 50% frames).
    - Frees YOLO models from VRAM before Pass 2 to stay comfortably within 4 GB VRAM.

  Pass 2 (Traffic-Guided SAM 2.1 Segmentation):
    - Uses 5x4 spatially stratified positive traffic seeds + automatic negative
      anchors (above-horizon sky, chlorophyll-verified green foliage/medians,
      static parked bays, zero-motion dead zones) to prompt `SAM2Predictor` once
      per camera on clean `bg_day`.
    - Evaluates every candidate SAM mask with a dilated track-corridor purity vs.
      dead-sidewalk leakage score, preserves physical bridge/parapet separations
      (without giant closing kernels or filling >1.2% gore islands), and outputs
      4-14 clickable vertices per separated carriageway polygon.

Usage:
    python 03_cv_yolo_pipeline/src/generate_initial_rois.py
    python 03_cv_yolo_pipeline/src/generate_initial_rois.py --cams 332 572 1028
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
from scipy import ndimage
from ultralytics import YOLO
from ultralytics.cfg import DEFAULT_CFG_DICT
from ultralytics.models.sam import SAM2Predictor

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from robust_detector import (
    CANONICAL_CLASS_MAP,
    _box_iou_single,
    _compute_grad_mag,
    _safe_ncc,
    build_osd_mask,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLEAN_DIR = PROJECT_ROOT / "Dataset_Clean_V1"
BG_DIR = PROJECT_ROOT / "data" / "median_backgrounds"
MANIFEST_PATH = CLEAN_DIR / "image_quality_manifest.parquet"
DEFAULT_OUT_JSON = PROJECT_ROOT / "data" / "camera_rois.json"
DEFAULT_PREVIEW_DIR = PROJECT_ROOT / "runs" / "detect" / "roi_previews"
DEFAULT_SAM_WEIGHTS = PROJECT_ROOT / "models" / "sam2.1_b.pt"

POLY_COLORS_BGR: tuple[tuple[int, int, int], ...] = (
    (0, 230, 120),   # green
    (255, 190, 0),   # cyan-blue
    (0, 170, 255),   # orange
    (230, 80, 240),  # magenta
    (80, 255, 255),  # yellow
    (255, 110, 120), # light blue
)


def simplify_contour_clean(cnt: np.ndarray, img_w: int, img_h: int) -> list[list[int]]:
    """Simplify a contour into 4-14 clean vertices suitable for fast interactive click-editing."""
    peri = float(cv2.arcLength(cnt, True))
    if peri <= 1.0:
        return []
    eps_frac = 0.012
    pts = cv2.approxPolyDP(cnt, eps_frac * peri, True)
    while len(pts) > 14 and eps_frac < 0.042:
        eps_frac *= 1.18
        pts = cv2.approxPolyDP(cnt, eps_frac * peri, True)
    if len(pts) < 3:
        return []
    poly = pts.reshape(-1, 2)
    poly[:, 0] = np.clip(poly[:, 0], 0, img_w - 1)
    poly[:, 1] = np.clip(poly[:, 1], 0, img_h - 1)
    return [[int(x), int(y)] for x, y in poly]


def sample_camera_frames(cam_df: pd.DataFrame, max_frames: int) -> pd.DataFrame:
    """Sample valid daytime/shoulder frames evenly across days and hours."""
    day_df = cam_df[cam_df["hour"].between(6, 17)].copy()
    if len(day_df) < 12:
        day_df = cam_df.copy()
    if "brightness_mean" in day_df.columns:
        bright_df = day_df[day_df["brightness_mean"] >= 45.0]
        if len(bright_df) >= 12:
            day_df = bright_df
    day_df = day_df.sort_values("timestamp")
    if len(day_df) <= max_frames:
        return day_df.reset_index(drop=True)
    indices = np.linspace(0, len(day_df) - 1, max_frames, dtype=int)
    return day_df.iloc[indices].reset_index(drop=True)


def split_dynamic_and_static_boxes(
    per_frame_boxes: list[list[tuple[float, float, float, float, float, str]]],
) -> tuple[
    list[list[tuple[float, float, float, float, float, str]]],
    list[tuple[float, float, float, float]],
]:
    """Identify boxes frozen at the exact same coordinates in >= 50% of sampled frames."""
    n_frames = len(per_frame_boxes)
    if n_frames < 8:
        return per_frame_boxes, []

    kept_per_frame: list[list[tuple[float, float, float, float, float, str]]] = [[] for _ in range(n_frames)]
    static_boxes: list[tuple[float, float, float, float]] = []
    static_thresh = max(8, int(0.50 * n_frames))

    for f_idx, boxes in enumerate(per_frame_boxes):
        for b in boxes:
            b_xyxy = b[:4]
            same_spot = sum(
                1 for o_boxes in per_frame_boxes if any(_box_iou_single(b_xyxy, ob[:4]) >= 0.65 for ob in o_boxes)
            )
            if same_spot >= static_thresh:
                static_boxes.append(b_xyxy)
            else:
                kept_per_frame[f_idx].append(b)
    return kept_per_frame, static_boxes


def compute_green_mask(bg_day: np.ndarray) -> np.ndarray:
    """Detect green medians/foliage via chlorophyll excess + HSV (never triggers on cool-tinted asphalt)."""
    b_ch, g_ch, r_ch = cv2.split(bg_day)
    excess_green = (g_ch.astype(np.int16) - r_ch.astype(np.int16) >= 10) & (
        g_ch.astype(np.int16) - b_ch.astype(np.int16) >= 6
    )
    hsv = cv2.cvtColor(bg_day, cv2.COLOR_BGR2HSV)
    h_ch, s_ch, v_ch = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    green = excess_green & (h_ch >= 30) & (h_ch <= 94) & (s_ch >= 42) & (v_ch >= 25)
    return cv2.morphologyEx(green.astype(np.uint8) * 255, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0


def sample_spaced_points(
    mask: np.ndarray,
    score_map: np.ndarray,
    max_pts: int = 20,
    min_dist: int = 22,
) -> list[list[int]]:
    """Greedily pick highest-scoring spatially separated pixel coordinates inside a boolean mask."""
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return []
    vals = score_map[ys, xs]
    pts: list[list[int]] = []
    for idx in np.argsort(-vals):
        y, x = int(ys[idx]), int(xs[idx])
        if all((x - px) ** 2 + (y - py) ** 2 >= min_dist**2 for px, py in pts):
            pts.append([x, y])
            if len(pts) >= max_pts:
                break
    return pts


def extract_traffic_evidence_for_camera(
    cam_id: int,
    cam_df: pd.DataFrame,
    coco_model: YOLO,
    visdrone_model: YOLO,
    max_motion_frames: int = 128,
    max_yolo_frames: int = 48,
) -> dict:
    """Pass 1: compute pixel motion frequency and background-filtered dynamic vehicle footprints."""
    sampled_motion = sample_camera_frames(cam_df, max_frames=max_motion_frames)
    motion_imgs: list[np.ndarray] = []
    for rel in sampled_motion["clean_rel_path"]:
        im = cv2.imread(str(CLEAN_DIR / str(rel)))
        if im is not None:
            motion_imgs.append(im)

    bg_path = BG_DIR / f"{cam_id}_bg.jpg"
    bg_day = cv2.imread(str(bg_path)) if bg_path.is_file() else None
    ref_img = bg_day if bg_day is not None else motion_imgs[0]
    h, w = ref_img.shape[:2]
    if bg_day is None or bg_day.shape[:2] != (h, w):
        bg_day = np.median(np.stack([cv2.resize(x, (w, h)) for x in motion_imgs[:25]], axis=0), axis=0).astype(
            np.uint8
        )

    motion_resized = [x if x.shape[:2] == (h, w) else cv2.resize(x, (w, h)) for x in motion_imgs]
    n_motion = len(motion_resized)
    yolo_idx = np.linspace(0, n_motion - 1, min(max_yolo_frames, n_motion), dtype=int)
    yolo_imgs = [motion_resized[i] for i in yolo_idx]
    n_yolo = len(yolo_imgs)

    gray_bg = cv2.cvtColor(bg_day, cv2.COLOR_BGR2GRAY)
    edge_bg = _compute_grad_mag(bg_day)
    osd_mask = build_osd_mask(bg_day, bg_day=bg_day)
    valid_mask = ~(osd_mask > 0)
    if (osd_mask > 0).any():
        edge_bg[osd_mask > 0] = 0.0

    green_mask = compute_green_mask(bg_day)

    motion_grays = [cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) for im in motion_resized]
    fg_motion_sum = np.zeros((h, w), dtype=np.float32)
    for k in range(n_motion):
        g_cur = motion_grays[k]
        g_nbr = motion_grays[k - 1] if k > 0 else motion_grays[min(1, n_motion - 1)]
        d_bg = cv2.absdiff(g_cur, gray_bg) > 14
        d_nb = cv2.absdiff(g_cur, g_nbr) > 12
        fg_motion_sum += (d_bg & d_nb).astype(np.float32)
    motion_freq = fg_motion_sum / max(float(n_motion), 1.0)
    if (osd_mask > 0).any():
        motion_freq[osd_mask > 0] = 0.0

    use_half = torch.cuda.is_available()
    precision_kwargs: dict[str, object] = (
        ({"quantize": 16} if use_half else {})
        if "quantize" in DEFAULT_CFG_DICT
        else {"half": use_half}
    )
    res_coco = coco_model.predict(
        yolo_imgs, imgsz=448, conf=0.22, iou=0.55, batch=16, verbose=False, **precision_kwargs
    )
    res_vd = visdrone_model.predict(
        yolo_imgs, imgsz=448, conf=0.26, iou=0.55, batch=16, verbose=False, **precision_kwargs
    )

    yolo_grays = [motion_grays[i] for i in yolo_idx]
    yolo_edges = [_compute_grad_mag(im) for im in yolo_imgs]
    per_frame_boxes: list[list[tuple[float, float, float, float, float, str]]] = []
    for im_g, im_e, rc, rv in zip(yolo_grays, yolo_edges, res_coco, res_vd):
        if (osd_mask > 0).any():
            im_e[osd_mask > 0] = 0.0
        cands: list[tuple[float, float, float, float, float, str]] = []
        for src_res in (rc, rv):
            if src_res.boxes is None or len(src_res.boxes) == 0:
                continue
            xyxy = src_res.boxes.xyxy.cpu().numpy()
            confs = src_res.boxes.conf.cpu().numpy()
            cids = src_res.boxes.cls.cpu().numpy().astype(int)
            for (x1, y1, x2, y2), cf, cid in zip(xyxy, confs, cids):
                raw_n = str(src_res.names[int(cid)]).strip().lower()
                can = CANONICAL_CLASS_MAP.get(raw_n)
                if can is None:
                    continue
                bw, bh = float(x2 - x1), float(y2 - y1)
                area = bw * bh
                if bw < 4.0 or bh < 5.0 or area > 0.35 * w * h:
                    continue
                ix1, iy1 = max(0, min(w - 1, int(round(x1)))), max(0, min(h - 1, int(round(y1))))
                ix2, iy2 = max(ix1 + 1, min(w, int(round(x2)))), max(iy1 + 1, min(h, int(round(y2))))
                vm = valid_mask[iy1:iy2, ix1:ix2]
                diff = cv2.absdiff(im_g[iy1:iy2, ix1:ix2], gray_bg[iy1:iy2, ix1:ix2])
                fg15 = float(((diff[vm] if vm.any() else diff) > 15).mean())
                ncc = _safe_ncc(im_e[iy1:iy2, ix1:ix2], edge_bg[iy1:iy2, ix1:ix2])
                if fg15 < 0.22 or ncc >= 0.62:
                    continue
                yc = 0.5 * (y1 + y2)
                if area >= 1200.0 and yc < 0.45 * h and cf < 0.40:
                    continue
                cands.append((float(x1), float(y1), float(x2), float(y2), float(cf), can))
        per_frame_boxes.append(cands)

    dynamic_per_frame, static_boxes = split_dynamic_and_static_boxes(per_frame_boxes)
    static_parked_mask = np.zeros((h, w), dtype=bool)
    for sx1, sy1, sx2, sy2 in static_boxes:
        static_parked_mask[
            max(0, int(round(sy1))) : min(h, int(round(sy2))),
            max(0, int(round(sx1))) : min(w, int(round(sx2))),
        ] = True

    footprint_heat = np.zeros((h, w), dtype=np.float32)
    box_count = 0
    for d_boxes in dynamic_per_frame:
        frame_mask = np.zeros((h, w), dtype=np.float32)
        for x1, y1, x2, y2, cf, _can in d_boxes:
            box_count += 1
            bw, bh = x2 - x1, y2 - y1
            trim_x = 0.08 * bw
            top_frac = 0.25 if bh <= 14.0 else 0.48
            fx1 = max(0, int(round(x1 + trim_x)))
            fx2 = min(w, max(fx1 + 2, int(round(x2 - trim_x))))
            fy1 = max(0, int(round(y1 + top_frac * bh)))
            fy2 = min(h, max(fy1 + 2, int(round(y2))))
            weight = 1.0 if cf >= 0.42 else 0.7
            frame_mask[fy1:fy2, fx1:fx2] = np.maximum(frame_mask[fy1:fy2, fx1:fx2], weight)
        footprint_heat += frame_mask

    footprint_freq = footprint_heat / max(float(n_yolo), 1.0)
    near_yolo = (
        cv2.dilate((footprint_heat >= 0.7).astype(np.uint8), np.ones((15, 17), np.uint8)) > 0
    ).astype(np.float32)
    motion_gated = motion_freq * near_yolo
    motion_gated[static_parked_mask & (footprint_freq < 0.12)] = 0.0
    combined = 0.62 * footprint_freq + 0.38 * motion_gated
    combined = cv2.GaussianBlur(combined, (5, 5), 0)
    combined[green_mask & (footprint_freq < 0.08)] = 0.0
    combined[static_parked_mask & (footprint_freq < 0.12)] = 0.0

    return {
        "cam_id": cam_id,
        "bg_day": bg_day,
        "h": h,
        "w": w,
        "n_motion": n_motion,
        "n_yolo": n_yolo,
        "box_count": box_count,
        "valid_mask": valid_mask,
        "green_mask": green_mask,
        "static_parked_mask": static_parked_mask,
        "footprint_heat": footprint_heat,
        "footprint_freq": footprint_freq,
        "motion_freq": motion_freq,
        "near_yolo": near_yolo,
        "combined": combined,
    }


def _collect_sam_candidate_masks(
    sam_pred: SAM2Predictor,
    bg_day: np.ndarray,
    h: int,
    w: int,
    pos_pts: list[list[int]],
    neg_pts: list[list[int]],
    min_traffic_y: int,
    green_mask: np.ndarray,
    static_parked_mask: np.ndarray,
    footprint_heat: np.ndarray,
    motion_freq: np.ndarray,
    track_corridor: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Query SAM 2.1 with isolated, negative-anchored, and tight local stroke prompts."""
    yy = np.arange(h)[:, None]
    sam_pred.features = None
    sam_pred.set_image(bg_day)

    sam_vote = np.zeros((h, w), dtype=np.float32)
    sam_best = np.zeros((h, w), dtype=np.float32)
    kept_count = 0

    for px, py in pos_pts:
        far_negs = [np_pt for np_pt in neg_pts if (np_pt[0] - px) ** 2 + (np_pt[1] - py) ** 2 >= 26**2]
        near_pos = sorted(
            [op for op in pos_pts if op != [px, py] and (op[0] - px) ** 2 + (op[1] - py) ** 2 <= 55**2],
            key=lambda op: (op[0] - px) ** 2 + (op[1] - py) ** 2,
        )[:2]
        prompt_variants = [
            ([[px, py]], [1]),
            ([[px, py]] + far_negs[:8], [1] + [0] * len(far_negs[:8])),
        ]
        if near_pos:
            prompt_variants.append(([[px, py]] + near_pos, [1] * (1 + len(near_pos))))

        for pts, lbls in prompt_variants:
            pred_masks, pred_bboxes = sam_pred.inference_features(
                sam_pred.features,
                (h, w),
                points=[pts],
                labels=[lbls],
                multimask_output=True,
            )
            if pred_masks is None:
                continue
            ms = pred_masks.detach().cpu().numpy()
            confs = pred_bboxes[:, 4].detach().cpu().numpy() if len(pred_bboxes) else np.ones(len(ms))
            for m_bool, sam_cf in zip(ms, confs):
                area = int(m_bool.sum())
                area_frac = area / float(h * w)
                if area_frac < 0.005 or area_frac > 0.86 or float(sam_cf) < 0.25:
                    continue
                green_frac = float(green_mask[m_bool].mean())
                static_frac = float(static_parked_mask[m_bool].mean())
                above_frac = float(((yy < max(4, min_traffic_y - 6)) & m_bool).sum()) / max(area, 1)
                if green_frac > 0.14 or static_frac > 0.28 or above_frac > 0.14:
                    continue
                cov_yolo = float((footprint_heat[m_bool] >= 0.65).mean())
                cov_corr = float(track_corridor[m_bool].mean())
                motion_cov = float((motion_freq[m_bool] >= 0.022).mean())
                sum_hits = float(footprint_heat[m_bool].sum())
                if float(sam_cf) < 0.42 and cov_corr < 0.65:
                    continue
                if sum_hits < 4.5 or (cov_yolo < 0.06 and motion_cov < 0.18) or max(cov_corr, motion_cov) < 0.24:
                    continue
                dead_leak = float((~track_corridor & (motion_freq < 0.014))[m_bool].mean())
                quality = max(cov_corr, 0.90 * motion_cov) + 0.70 * cov_yolo - 0.85 * dead_leak
                if quality < 0.22:
                    continue
                kept_count += 1
                sam_vote[m_bool] += max(0.2, quality)
                sam_best[m_bool] = np.maximum(sam_best[m_bool], quality)

    sam_pred.reset_image()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return sam_vote, sam_best, kept_count


def _extract_clean_polygons(
    road_bin: np.ndarray,
    footprint_heat: np.ndarray,
    footprint_freq: np.ndarray,
    green_mask: np.ndarray,
    static_parked_mask: np.ndarray,
    min_comp_area: float,
    min_peak_hits: float,
    min_sum_hits: float,
    min_mean_hits: float,
    w: int,
    h: int,
) -> tuple[list[list[list[int]]], np.ndarray]:
    """Convert thresholded road mask into clean separated polygons without bridging gore islands."""
    n_lbl, labels, stats, _ = cv2.connectedComponentsWithStats(road_bin, connectivity=8)
    comp_ids = [lbl for lbl in range(1, n_lbl) if int(stats[lbl, cv2.CC_STAT_AREA]) >= int(min_comp_area)]
    comp_ids.sort(key=lambda lbl: int(stats[lbl, cv2.CC_STAT_AREA]), reverse=True)

    polygons_px: list[list[list[int]]] = []
    final_mask = np.zeros((h, w), dtype=np.uint8)
    for lbl in comp_ids:
        raw_comp = (labels == lbl).astype(np.uint8) * 255
        comp_bool = raw_comp > 0
        static_comp_frac = float(static_parked_mask[comp_bool].mean())
        mean_hits_comp = float(footprint_heat[comp_bool].mean())
        if (
            float(footprint_heat[comp_bool].max()) < min_peak_hits
            or float(footprint_heat[comp_bool].sum()) < min_sum_hits
            or (static_comp_frac > 0.18 and mean_hits_comp < 1.2)
            or mean_hits_comp < min_mean_hits
        ):
            continue

        # Fill ONLY small internal holes (< 1.2% frame) so real concrete gore islands (Cam 542) remain cut out.
        filled_full = ndimage.binary_fill_holes(comp_bool)
        holes = filled_full & (~comp_bool)
        n_h, h_lbl, h_stats, _ = cv2.connectedComponentsWithStats(holes.astype(np.uint8), connectivity=8)
        small_holes = np.zeros_like(holes)
        for hl in range(1, n_h):
            if int(h_stats[hl, cv2.CC_STAT_AREA]) < int(0.012 * w * h):
                small_holes |= h_lbl == hl

        comp_fixed = (comp_bool | small_holes).astype(np.uint8) * 255
        comp_closed = cv2.morphologyEx(comp_fixed, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        bot_start = int(0.86 * h)
        bot_cols = comp_closed[bot_start : int(0.96 * h), :].any(axis=0)
        if bot_cols.any():
            comp_closed[bot_start:, bot_cols] = 255
        comp_closed[green_mask & (footprint_freq < 0.08)] = 0
        comp_closed[final_mask > 0] = 0
        if int((comp_closed > 0).sum()) < int(min_comp_area):
            continue
        cnts, _ = cv2.findContours(comp_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in cnts:
            if cv2.contourArea(cnt) < min_comp_area:
                continue
            poly = simplify_contour_clean(cnt, w, h)
            if len(poly) >= 3:
                polygons_px.append(poly)
                cv2.fillPoly(final_mask, [np.array(poly, dtype=np.int32)], 255)

    polygons_px.sort(key=lambda p: (min(pt[0] for pt in p), min(pt[1] for pt in p)))
    return polygons_px, final_mask


def build_roi_and_preview(ev: dict, sam_pred: SAM2Predictor | None) -> tuple[dict, np.ndarray]:
    """Pass 2: run Traffic-Guided SAM 2.1 segmentation, assemble polygons, and render 3-panel preview."""
    cam_id = ev["cam_id"]
    bg_day = ev["bg_day"]
    h, w = ev["h"], ev["w"]
    n_motion, n_yolo, box_count = ev["n_motion"], ev["n_yolo"], ev["box_count"]
    valid_mask = ev["valid_mask"]
    green_mask = ev["green_mask"]
    static_parked_mask = ev["static_parked_mask"]
    footprint_heat = ev["footprint_heat"]
    footprint_freq = ev["footprint_freq"]
    motion_freq = ev["motion_freq"]
    near_yolo = ev["near_yolo"]
    combined = ev["combined"]

    active_traffic = (footprint_heat >= 0.7) | ((motion_freq >= 0.032) & (near_yolo > 0))
    track_corridor = cv2.dilate(active_traffic.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0

    seed_pool = (footprint_heat >= 2.0) & (~green_mask) & (~static_parked_mask) & valid_mask
    if seed_pool.sum() < 25:
        seed_pool = ((footprint_heat >= 1.0) | (combined >= 0.014)) & (~green_mask) & (~static_parked_mask) & valid_mask

    seed_score = np.sqrt(np.maximum(footprint_heat, 0.0)) + 2.5 * motion_freq
    pos_pts: list[list[int]] = []
    grid_mask = (
        ((footprint_heat >= 1.0) | ((footprint_heat >= 0.65) & (motion_freq >= 0.025)))
        & (~green_mask)
        & (~static_parked_mask)
        & valid_mask
    )
    for gy in range(4):
        y0, y1 = int(gy * h / 4), int((gy + 1) * h / 4)
        for gx in range(5):
            x0, x1 = int(gx * w / 5), int((gx + 1) * w / 5)
            cell = grid_mask[y0:y1, x0:x1]
            if cell.sum() < 6:
                continue
            ys_c, xs_c = np.where(cell)
            vals_c = seed_score[y0:y1, x0:x1][ys_c, xs_c]
            best_i = int(np.argmax(vals_c))
            px, py = int(x0 + xs_c[best_i]), int(y0 + ys_c[best_i])
            if all((px - ox) ** 2 + (py - oy) ** 2 >= 18**2 for ox, oy in pos_pts):
                pos_pts.append([px, py])
    if len(pos_pts) < 16:
        for pt in sample_spaced_points(seed_pool, seed_score, max_pts=18, min_dist=24):
            if all((pt[0] - ox) ** 2 + (pt[1] - oy) ** 2 >= 18**2 for ox, oy in pos_pts):
                pos_pts.append(pt)
                if len(pos_pts) >= 18:
                    break

    min_traffic_y = max(0, int(np.where(seed_pool)[0].min()) - 6) if seed_pool.any() else int(0.15 * h)
    any_motion = (footprint_heat > 0) | (motion_freq >= 0.018)
    near_any_motion = cv2.dilate(any_motion.astype(np.uint8), np.ones((21, 21), np.uint8)) > 0
    yy = np.arange(h)[:, None]
    neg_candidates = (yy < max(8, min_traffic_y - 4)) | green_mask | static_parked_mask | (~near_any_motion)
    neg_pts = sample_spaced_points(neg_candidates, (~any_motion).astype(np.float32), max_pts=14, min_dist=34)

    pos_vals = combined[combined > 0.01]
    p95 = float(np.percentile(pos_vals, 95)) if pos_vals.size > 50 else 0.15
    dyn_core = (combined >= float(np.clip(0.11 * p95, 0.020, 0.048))) & (~green_mask) & (~static_parked_mask)

    sam_kept = 0
    if sam_pred is not None and pos_pts:
        sam_vote, sam_best, sam_kept = _collect_sam_candidate_masks(
            sam_pred=sam_pred,
            bg_day=bg_day,
            h=h,
            w=w,
            pos_pts=pos_pts,
            neg_pts=neg_pts,
            min_traffic_y=min_traffic_y,
            green_mask=green_mask,
            static_parked_mask=static_parked_mask,
            footprint_heat=footprint_heat,
            motion_freq=motion_freq,
            track_corridor=track_corridor,
        )
        pos_votes = sam_vote[sam_vote > 0]
        vote_p90 = float(np.percentile(pos_votes, 90)) if pos_votes.size > 20 else 1.0
        vote_cut = max(0.32, 0.05 * vote_p90)
        sam_accepted = (sam_best >= 0.30) & (sam_vote >= vote_cut)
        sam_accepted[green_mask & (footprint_freq < 0.08)] = False
        sam_accepted[static_parked_mask & (footprint_freq < 0.12)] = False
        sam_accepted[:min_traffic_y, :] = False
        road_bool = sam_accepted if sam_accepted.sum() >= 0.06 * w * h else (sam_accepted | dyn_core)
    else:
        sam_vote = combined.copy()
        road_bool = dyn_core

    pinch_close = (cv2.morphologyEx(road_bool.astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((7, 3), np.uint8)) > 0) & (
        (footprint_heat >= 0.7) | (motion_freq >= 0.035)
    )
    road_bin = (road_bool | pinch_close).astype(np.uint8) * 255
    road_bin[green_mask & (footprint_freq < 0.08)] = 0
    road_bin[static_parked_mask & (footprint_freq < 0.12)] = 0
    road_bin[:min_traffic_y, :] = 0
    road_bin = cv2.morphologyEx(road_bin, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    polygons_px, final_mask = _extract_clean_polygons(
        road_bin=road_bin,
        footprint_heat=footprint_heat,
        footprint_freq=footprint_freq,
        green_mask=green_mask,
        static_parked_mask=static_parked_mask,
        min_comp_area=0.008 * w * h,
        min_peak_hits=2.2,
        min_sum_hits=28.0,
        min_mean_hits=0.35,
        w=w,
        h=h,
    )

    used_fallback = False
    if not polygons_px:
        quiet_bin = ((combined >= 0.012) & (~green_mask) & (~static_parked_mask)).astype(np.uint8) * 255
        quiet_bin = cv2.morphologyEx(quiet_bin, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        polygons_px, final_mask = _extract_clean_polygons(
            road_bin=quiet_bin,
            footprint_heat=footprint_heat,
            footprint_freq=footprint_freq,
            green_mask=green_mask,
            static_parked_mask=static_parked_mask,
            min_comp_area=0.005 * w * h,
            min_peak_hits=0.7,
            min_sum_hits=4.0,
            min_mean_hits=0.05,
            w=w,
            h=h,
        )
    if not polygons_px:
        used_fallback = True
        polygons_px = [
            [
                [int(0.10 * w), int(0.35 * h)],
                [int(0.90 * w), int(0.35 * h)],
                [int(0.98 * w), int(0.98 * h)],
                [int(0.02 * w), int(0.98 * h)],
            ]
        ]
        cv2.fillPoly(final_mask, [np.array(polygons_px[0], dtype=np.int32)], 255)

    polygons_norm = [[[round(x / float(w), 4), round(y / float(h), 4)] for x, y in poly] for poly in polygons_px]
    road_area_px = int((final_mask > 0).sum())
    road_ratio = road_area_px / float(w * h)

    # Render clean 3-panel preview: [bg_day | SAM vote heatmap + seeds | numbered polygons]
    heat_vis = cv2.applyColorMap(
        np.clip(sam_vote / max(float(sam_vote.max()), 1e-4) * 255.0, 0, 255).astype(np.uint8),
        cv2.COLORMAP_JET,
    )
    heat_blend = cv2.addWeighted(bg_day, 0.45, heat_vis, 0.55, 0)
    for px, py in pos_pts:
        cv2.circle(heat_blend, (px, py), 3, (0, 255, 0), -1)
    for nx, ny in neg_pts:
        cv2.drawMarker(heat_blend, (nx, ny), (0, 0, 255), cv2.MARKER_CROSS, 6, 1)

    roi_vis = bg_day.copy()
    overlay = roi_vis.copy()
    for i, poly in enumerate(polygons_px):
        cv2.fillPoly(overlay, [np.array(poly, dtype=np.int32)], POLY_COLORS_BGR[i % len(POLY_COLORS_BGR)])
    roi_vis = cv2.addWeighted(overlay, 0.30, roi_vis, 0.70, 0)
    for i, poly in enumerate(polygons_px):
        col = POLY_COLORS_BGR[i % len(POLY_COLORS_BGR)]
        cv2.polylines(roi_vis, [np.array(poly, dtype=np.int32)], True, col, 2)
        for x, y in poly:
            cv2.circle(roi_vis, (x, y), 3, (255, 255, 255), -1)
            cv2.circle(roi_vis, (x, y), 2, col, -1)
        cx, cy = int(np.mean([pt[0] for pt in poly])), int(np.mean([pt[1] for pt in poly]))
        tag = f"R{i+1}({len(poly)}v)"
        cv2.putText(roi_vis, tag, (max(4, cx - 22), max(14, cy)), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 2)
        cv2.putText(roi_vis, tag, (max(4, cx - 22), max(14, cy)), cv2.FONT_HERSHEY_SIMPLEX, 0.40, col, 1)

    header = np.full((24, w * 3, 3), 24, dtype=np.uint8)
    fb_str = " | FALLBACK" if used_fallback else ""
    cv2.putText(
        header,
        f"Cam {cam_id} | {n_motion}m/{n_yolo}y | sam={sam_kept} | ROIs={len(polygons_px)} | area={road_ratio*100:.1f}%{fb_str}",
        (8, 17),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.46,
        (240, 240, 240),
        1,
    )
    panel = np.vstack([header, np.hstack([bg_day, heat_blend, roi_vis])])
    panel_2x = cv2.resize(panel, (panel.shape[1] * 2, panel.shape[0] * 2), interpolation=cv2.INTER_LINEAR)

    entry = {
        "cam_id": int(cam_id),
        "img_size": [int(w), int(h)],
        "polygons_norm": polygons_norm,
        "polygons_px": polygons_px,
        "num_polygons": len(polygons_px),
        "vertex_counts": [len(p) for p in polygons_px],
        "road_area_px": road_area_px,
        "road_area_ratio": round(road_ratio, 4),
        "sampled_motion_frames": n_motion,
        "sampled_yolo_frames": n_yolo,
        "dynamic_boxes_used": box_count,
        "sam_masks_used": sam_kept,
        "fallback": used_fallback,
        "reviewed": False,
    }
    return entry, panel_2x


def save_roi_montages(preview_tiles: list[tuple[int, np.ndarray]], montage_dir: Path, per_page: int = 10) -> None:
    """Save paginated 2x5 grids (each showing bg_day | SAM heatmap | ROI overlay) for easy human QA."""
    montage_dir.mkdir(parents=True, exist_ok=True)
    target_w, target_h = 1056, 300
    for page_idx in range(0, len(preview_tiles), per_page):
        chunk = preview_tiles[page_idx : page_idx + per_page]
        rows_imgs: list[np.ndarray] = []
        for idx in range(0, per_page, 2):
            pair: list[np.ndarray] = []
            for sub_i in (idx, idx + 1):
                if sub_i < len(chunk):
                    _, im = chunk[sub_i]
                    pair.append(cv2.resize(im, (target_w, target_h), interpolation=cv2.INTER_AREA))
                else:
                    pair.append(np.full((target_h, target_w, 3), 24, dtype=np.uint8))
            rows_imgs.append(np.hstack(pair))
        grid = np.vstack(rows_imgs)
        page_num = (page_idx // per_page) + 1
        cv2.imwrite(str(montage_dir / f"montage_roi_p{page_num:02d}.jpg"), grid)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate V3 SAM 2.1 + Traffic Road ROI polygons across BMA cameras")
    parser.add_argument("--cams", type=int, nargs="*", default=None, help="Optional subset of camera IDs")
    parser.add_argument("--max-motion-frames", type=int, default=128)
    parser.add_argument("--max-yolo-frames", type=int, default=48)
    parser.add_argument("--sam-weights", type=Path, default=DEFAULT_SAM_WEIGHTS)
    parser.add_argument("--no-sam", action="store_true", help="Disable SAM 2.1 refinement and use motion+YOLO only")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--preview-dir", type=Path, default=DEFAULT_PREVIEW_DIR)
    args = parser.parse_args()

    t0 = time.perf_counter()
    df = pd.read_parquet(
        MANIFEST_PATH,
        columns=["cam_id", "timestamp", "hour", "clean_rel_path", "is_valid", "quality_warning", "brightness_mean"],
    )
    df = df[df["is_valid"] & (df["quality_warning"] == "none")].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    all_cams = sorted(int(c) for c in df["cam_id"].unique())
    target_cams = sorted(args.cams) if args.cams else all_cams

    cam_dir = args.preview_dir / "cams"
    montage_dir = args.preview_dir / "montages"
    cam_dir.mkdir(parents=True, exist_ok=True)
    montage_dir.mkdir(parents=True, exist_ok=True)

    existing_rois: dict[str, dict] = {}
    if args.cams and args.output.is_file():
        existing_payload = json.loads(args.output.read_text(encoding="utf-8"))
        existing_rois = existing_payload.get("cameras", {})

    print(f"Pass 1/2: Extracting traffic & motion evidence for {len(target_cams)} cameras ({args.max_motion_frames}m/{args.max_yolo_frames}y)...")
    coco_model = YOLO(str(PROJECT_ROOT / "models" / "yolo26x.pt"))
    visdrone_model = YOLO(str(PROJECT_ROOT / "models" / "dronefreak--visdrone-yolo26l" / "best.pt"))

    evidences: list[dict] = []
    for idx, cam_id in enumerate(target_cams, start=1):
        sub = df[df["cam_id"] == cam_id]
        evidences.append(
            extract_traffic_evidence_for_camera(
                cam_id=cam_id,
                cam_df=sub,
                coco_model=coco_model,
                visdrone_model=visdrone_model,
                max_motion_frames=args.max_motion_frames,
                max_yolo_frames=args.max_yolo_frames,
            )
        )
        if idx % 20 == 0 or idx == len(target_cams):
            print(f"  [Pass 1] {idx:03d}/{len(target_cams)} done | elapsed={time.perf_counter() - t0:.1f}s")

    del coco_model, visdrone_model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    sam_pred = None
    if not args.no_sam:
        print(f"Pass 2/2: Segmenting road surfaces with SAM 2.1 ({args.sam_weights.name})...")
        sam_pred = SAM2Predictor(
            overrides=dict(model=str(args.sam_weights), imgsz=1024, conf=0.25, save=False, verbose=False)
        )

    rois_by_cam: dict[str, dict] = dict(existing_rois)
    preview_tiles: list[tuple[int, np.ndarray]] = []
    for idx, ev in enumerate(evidences, start=1):
        cam_id = ev["cam_id"]
        entry, strip = build_roi_and_preview(ev, sam_pred)
        rois_by_cam[str(cam_id)] = entry
        preview_tiles.append((cam_id, strip))
        cv2.imwrite(str(cam_dir / f"cam_{cam_id:04d}_roi.jpg"), strip)
        ev.clear()
        if idx % 10 == 0 or idx == len(target_cams):
            print(
                f"  [Pass 2] [{idx:03d}/{len(target_cams)}] Cam {cam_id:>4} | polys={entry['num_polygons']} "
                f"verts={entry['vertex_counts']} area={entry['road_area_ratio']*100:.1f}% sam={entry['sam_masks_used']} "
                f"| elapsed={time.perf_counter() - t0:.1f}s"
            )

    save_roi_montages(preview_tiles, montage_dir, per_page=10)

    n_polys_list = [v["num_polygons"] for v in rois_by_cam.values()]
    verts_list = [vc for v in rois_by_cam.values() for vc in v["vertex_counts"]]
    areas_list = [v["road_area_ratio"] * 100.0 for v in rois_by_cam.values()]
    n_fallbacks = sum(1 for v in rois_by_cam.values() if v.get("fallback"))
    multi_road_cams = sum(1 for v in rois_by_cam.values() if v["num_polygons"] >= 2)

    payload = {
        "schema_version": 2,
        "generator": "v3_sam2.1_traffic_guided" if sam_pred is not None else "v3_motion_yolo",
        "total_cameras": len(rois_by_cam),
        "multi_road_cameras": multi_road_cams,
        "fallback_cameras": n_fallbacks,
        "mean_road_area_pct": round(float(np.mean(areas_list)), 2) if areas_list else 0.0,
        "median_polygons_per_cam": float(np.median(n_polys_list)) if n_polys_list else 0.0,
        "median_vertices_per_polygon": float(np.median(verts_list)) if verts_list else 0.0,
        "max_vertices_per_polygon": int(max(verts_list)) if verts_list else 0,
        "cameras": {k: rois_by_cam[k] for k in sorted(rois_by_cam, key=lambda s: int(s))},
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    elapsed = time.perf_counter() - t0
    print("\n=== Auto ROI V3 (SAM 2.1 + Traffic) Summary ===")
    print(f"Cameras saved: {len(rois_by_cam)} | Multi-road separated: {multi_road_cams} | Fallbacks: {n_fallbacks}")
    print(
        f"Mean ROI area: {payload['mean_road_area_pct']:.1f}% | Median polys/cam: {payload['median_polygons_per_cam']:.1f} "
        f"| Median verts/poly: {payload['median_vertices_per_polygon']:.1f} (max={payload['max_vertices_per_polygon']})"
    )
    print(f"Elapsed: {elapsed:.1f}s | JSON: {args.output} | Previews: {args.preview_dir}")


if __name__ == "__main__":
    main()
