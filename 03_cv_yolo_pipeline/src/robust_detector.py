"""
Multi-Expert Edge-Case-Resilient Vehicle Detection Pipeline (`03_cv_yolo_pipeline`).

Combines five locally cached pretrained specialist detectors:
  1. iisc-aim/UVH-26 (YOLOv11-X)         -- Asian two-wheelers, three-wheelers & compact cars
  2. dronefreak/visdrone-yolo11x         -- Dense/small far-field queued vehicles & riders
  3. dronefreak/visdrone-yolo26l         -- Complementary VisDrone architecture for tiny distant vehicles
  4. yolo26x.pt (COCO YOLOv26-X)         -- High-precision cars, buses, trucks & night/rain anchors
  5. yolo11x.pt (COCO YOLOv11-X)         -- Complementary COCO anchor for rain, glare & occlusion cross-voting

Augmented with physics-informed computer vision & scene gates:
  - Per-camera multi-regime Median Background (day + night) & edge NCC verification
  - Adjacent-frame temporal stationary filter (eliminates off-road parked cars)
  - Optical condition profiling + highlight-compressed CLAHE/gamma view for night glare & heavy rain
  - TELEA OSD text inpainting + OSD-excluded background matching + OSD-text box veto
  - Boundary-safe full-height sub-crops + rider+two-wheeler confidence boosting
  - Perspective-aware geometric gates, two-tier weighted fusion & IoMin/center-distance duplicate pruning
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import Counter, OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import threading
import urllib.request

import cv2
import numpy as np
import pandas as pd
import torch
import torchvision
from ultralytics import YOLO
from ultralytics.cfg import DEFAULT_CFG_DICT


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CLEAN_DIR = PROJECT_ROOT / "Dataset_Clean_V1"
DEFAULT_BG_DIR = PROJECT_ROOT / "data" / "median_backgrounds"
DEFAULT_ROIS_PATH = PROJECT_ROOT / "data" / "camera_rois.json"
MODELS_CACHE_DIR = PROJECT_ROOT / "models"

CANONICAL_ID_TO_NAME: dict[int, str] = {
    0: "car",
    1: "motorcycle",
    2: "bus",
    3: "truck",
}
CANONICAL_NAME_TO_ID: dict[str, int] = {v: k for k, v in CANONICAL_ID_TO_NAME.items()}

CANONICAL_CLASS_MAP: dict[str, str] = {
    "car": "car",
    "hatchback": "car",
    "sedan": "car",
    "suv": "car",
    "muv": "car",
    "van": "car",
    "motorcycle": "motorcycle",
    "motor": "motorcycle",
    "motorbike": "motorcycle",
    "two-wheeler": "motorcycle",
    "bus": "bus",
    "mini-bus": "bus",
    "tempo-traveller": "bus",
    "truck": "truck",
    "lcv": "truck",
    "tricycle": "car",
    "awning-tricycle": "car",
    "three-wheeler": "car",
}

RIDER_CLASSES_LOWER: set[str] = {"person", "pedestrian", "people", "rider"}

GROUP_4W: set[str] = {"car", "bus", "truck"}
GROUP_2W: set[str] = {"motorcycle"}
VISDRONE_KEYS: set[str] = {"visdrone", "visdrone26l"}
COCO_KEYS: set[str] = {"yolo26x", "yolo11x"}
UVH_KEYS: set[str] = {"uvh26"}
BDD_KEYS: set[str] = {"bdd100k"}

# Color palette (BGR) for readable OpenCV annotations.
CLASS_COLORS_BGR: dict[str, tuple[int, int, int]] = {
    "car": (255, 130, 30),           # bright blue
    "motorcycle": (230, 220, 0),     # cyan
    "bus": (220, 50, 230),           # magenta
    "truck": (0, 165, 255),          # orange
}


@dataclass(frozen=True)
class ExpertSpec:
    key: str
    local_rel_path: str
    hf_repo_id: str | None
    hf_filename: str | None


EXPERT_SPECS: tuple[ExpertSpec, ...] = (
    ExpertSpec(
        key="uvh26",
        local_rel_path="iisc-aim--UVH-26/UVH-26-MV-YOLOv11-X.pt",
        hf_repo_id="iisc-aim/UVH-26",
        hf_filename="weights/YOLOv11-X/UVH-26-MV-YOLOv11-X.pt",
    ),
    ExpertSpec(
        key="visdrone",
        local_rel_path="dronefreak--visdrone-yolo11x/best.pt",
        hf_repo_id="dronefreak/visdrone-yolo11x",
        hf_filename="best.pt",
    ),
    ExpertSpec(
        key="visdrone26l",
        local_rel_path="dronefreak--visdrone-yolo26l/best.pt",
        hf_repo_id="dronefreak/visdrone-yolo26l",
        hf_filename="best.pt",
    ),
    ExpertSpec(
        key="yolo26x",
        local_rel_path="yolo26x.pt",
        hf_repo_id=None,
        hf_filename=None,
    ),
    ExpertSpec(
        key="yolo11x",
        local_rel_path="yolo11x.pt",
        hf_repo_id=None,
        hf_filename=None,
    ),
    ExpertSpec(
        key="bdd100k",
        local_rel_path="dronefreak--bdd100k-yolo26m/best.pt",
        hf_repo_id="dronefreak/bdd100k-yolo26m",
        hf_filename="best.pt",
    ),
)


@dataclass
class RawDetection:
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float
    cls_name: str
    orig_cls_name: str
    model_key: str
    view_tag: str
    crop_tag: str
    is_weak_truck: bool = False
    from_three_wheeler: bool = False


@dataclass
class DetectionResult:
    boxes_xyxy: np.ndarray
    scores: np.ndarray
    class_ids: np.ndarray
    class_names: dict[int, str]
    support_counts: np.ndarray
    suppressed_static_count: int
    optical_profile: dict[str, float | bool | int | None]
    counts: dict[str, int]
    suppressed_roi_count: int = 0
    road_roi_area: float = 0.0
    bbox_total_area: float = 0.0
    road_occupancy_ratio: float = 0.0
    foreground_ratio: float = 0.0
    roi_polygons_px: list[list[list[int]]] = field(default_factory=list)


@dataclass
class CameraSceneContext:
    cam_id: int | None
    timestamp: pd.Timestamp | None
    hour: int | None
    bg_day: np.ndarray | None
    bg_night: np.ndarray | None
    prev_img: np.ndarray | None
    next_img: np.ndarray | None
    prev_mad: float | None
    next_mad: float | None


def _resolve_expert_weights(spec: ExpertSpec) -> str:
    """Resolve locally cached weights in `models/` before falling back to download."""
    local_path = MODELS_CACHE_DIR / spec.local_rel_path
    if local_path.is_file() and local_path.stat().st_size > 0:
        return str(local_path)

    if spec.hf_repo_id and spec.hf_filename:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://huggingface.co/{spec.hf_repo_id}/resolve/main/{spec.hf_filename}"
        part_path = local_path.with_suffix(local_path.suffix + ".part")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as resp, part_path.open("wb") as out:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        part_path.replace(local_path)
        return str(local_path)

    from ultralytics.utils.downloads import attempt_download_asset

    local_path.parent.mkdir(parents=True, exist_ok=True)
    return str(attempt_download_asset(local_path))


def _parse_cam_and_timestamp(image_path: Path) -> tuple[int | None, pd.Timestamp | None]:
    """Infer camera ID and timestamp from standard or EDA image filenames."""
    stem = image_path.stem
    m = re.match(r"^(\d+)_(\d{8})_(\d{6})", stem)
    if m:
        cam_id = int(m.group(1))
        ts = pd.to_datetime(f"{m.group(2)}_{m.group(3)}", format="%Y%m%d_%H%M%S", errors="coerce")
        return cam_id, (None if pd.isna(ts) else ts)

    m_cam = re.search(r"cam(\d+)", stem, flags=re.IGNORECASE)
    if m_cam:
        return int(m_cam.group(1)), None

    if image_path.parent.name.isdigit():
        return int(image_path.parent.name), None

    return None, None


def _compute_grad_mag(bgr: np.ndarray) -> np.ndarray:
    """Compute Sobel gradient magnitude from a BGR image."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    return np.hypot(gx, gy)


def _safe_ncc(patch_a: np.ndarray, patch_b: np.ndarray) -> float:
    """Compute normalized cross-correlation safely on small or flat patches."""
    if patch_a.size < 9 or patch_a.shape != patch_b.shape:
        return 0.0
    if float(patch_a.std()) < 1e-4 or float(patch_b.std()) < 1e-4:
        return 0.0
    val = float(cv2.matchTemplate(patch_a, patch_b, cv2.TM_CCOEFF_NORMED)[0, 0])
    if not np.isfinite(val):
        return 0.0
    return val


def _has_zebra_oscillation(g_patch: np.ndarray, ncc_edge_bg: float | None) -> bool:
    """Detect periodic bright-dark bar patterns typical of crosswalk stripes matched in clean bg."""
    if g_patch.shape[0] < 14 or g_patch.shape[1] < 18:
        return False
    if ncc_edge_bg is None or ncc_edge_bg < 0.28:
        return False

    resized = cv2.resize(g_patch.astype(np.float32), (24, 24), interpolation=cv2.INTER_AREA)

    def _mean_crossings(mat: np.ndarray) -> float:
        centered = mat - mat.mean(axis=1, keepdims=True)
        row_counts: list[float] = []
        for row in centered:
            nz = row[np.abs(row) >= 12.0]
            row_counts.append(float(np.diff(np.signbit(nz)).sum()) if len(nz) >= 2 else 0.0)
        return float(np.mean(row_counts)) if row_counts else 0.0

    return max(_mean_crossings(resized), _mean_crossings(resized.T)) >= 4.2


def _box_iomin_and_areas(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """Compute `(iou, iomin, area_a, area_b)` between two `[x1, y1, x2, y2]` boxes."""
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    min_area = min(area_a, area_b)
    if min_area <= 0.0:
        return 0.0, 0.0, area_a, area_b
    ix1 = max(a[0], b[0])
    iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2])
    iy2 = min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter <= 0.0:
        return 0.0, 0.0, area_a, area_b
    union = area_a + area_b - inter
    iou = inter / union if union > 0.0 else 0.0
    iomin = inter / min_area
    return iou, iomin, area_a, area_b


def _box_iou_single(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """Compute IoU between two [x1, y1, x2, y2] boxes."""
    return _box_iomin_and_areas(a, b)[0]


def _box_center_ratio(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """Return center distance normalized by the smaller box diagonal."""
    diag_a = float(np.hypot(max(0.0, a[2] - a[0]), max(0.0, a[3] - a[1])))
    diag_b = float(np.hypot(max(0.0, b[2] - b[0]), max(0.0, b[3] - b[1])))
    min_diag = min(diag_a, diag_b)
    if min_diag <= 1e-6:
        return 999.0
    cax, cay = 0.5 * (a[0] + a[2]), 0.5 * (a[1] + a[3])
    cbx, cby = 0.5 * (b[0] + b[2]), 0.5 * (b[1] + b[3])
    return float(np.hypot(cax - cbx, cay - cby)) / min_diag


class CameraSceneProvider:
    """Lazily builds and caches per-camera day/night median backgrounds and adjacent frames."""

    def __init__(
        self,
        clean_dir: Path = DEFAULT_CLEAN_DIR,
        bg_dir: Path = DEFAULT_BG_DIR,
    ) -> None:
        self.clean_dir = clean_dir
        self.bg_dir = bg_dir
        self._lock = threading.Lock()
        self._manifest_loaded = False
        self._manifest_by_cam: dict[int, pd.DataFrame] = {}
        self._cam_index: dict[int, tuple[np.ndarray, np.ndarray, list[str]]] = {}
        self._bg_cache: dict[tuple[int, str], np.ndarray | None] = {}
        self._frame_cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._frame_cache_max = 96

    def _read_bgr_cached(self, path: Path) -> np.ndarray | None:
        """Read an image with a bounded thread-safe LRU cache to avoid redundant adjacent JPEG decodes."""
        key = str(path)
        with self._lock:
            cached = self._frame_cache.get(key)
            if cached is not None:
                self._frame_cache.move_to_end(key)
                return cached
        img = cv2.imread(key)
        if img is None:
            return None
        with self._lock:
            self._frame_cache[key] = img
            self._frame_cache.move_to_end(key)
            while len(self._frame_cache) > self._frame_cache_max:
                self._frame_cache.popitem(last=False)
        return img

    def _ensure_manifest(self) -> None:
        if self._manifest_loaded:
            return
        with self._lock:
            if self._manifest_loaded:
                return
            manifest_path = self.clean_dir / "image_quality_manifest.parquet"
            if manifest_path.is_file():
                cols = ["cam_id", "timestamp", "date", "hour", "clean_filename", "clean_rel_path", "is_valid", "quality_warning", "brightness_mean"]
                df = pd.read_parquet(manifest_path, columns=cols)
                df = df[df["is_valid"] & (df["quality_warning"] == "none")].copy()
                df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
                df.sort_values(["cam_id", "timestamp"], inplace=True)
                for cid, grp in df.groupby("cam_id", sort=False):
                    grp_reset = grp.reset_index(drop=True)
                    cid_int = int(cid)
                    self._manifest_by_cam[cid_int] = grp_reset
                    ts_float = grp_reset["timestamp"].to_numpy(dtype="datetime64[us]").astype(np.int64) / 1e6
                    dates = grp_reset["timestamp"].to_numpy(dtype="datetime64[D]")
                    rel_paths = [str(p) for p in grp_reset["clean_rel_path"].tolist()]
                    self._cam_index[cid_int] = (ts_float, dates, rel_paths)
            self._manifest_loaded = True

    def _load_or_build_bg(self, cam_id: int, regime: str, target_shape: tuple[int, int]) -> np.ndarray | None:
        """Load cached `<cam_id>_bg[_night].jpg` or compute median background from manifest frames."""
        cache_key = (cam_id, regime)
        with self._lock:
            if cache_key in self._bg_cache:
                cached = self._bg_cache[cache_key]
                if cached is not None and cached.shape[:2] != target_shape:
                    return cv2.resize(cached, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_AREA)
                return cached

        self.bg_dir.mkdir(parents=True, exist_ok=True)
        bg_filename = f"{cam_id}_bg.jpg" if regime == "day" else f"{cam_id}_bg_night.jpg"
        bg_path = self.bg_dir / bg_filename
        if bg_path.is_file():
            loaded = cv2.imread(str(bg_path))
            if loaded is not None:
                with self._lock:
                    self._bg_cache[cache_key] = loaded
                if loaded.shape[:2] != target_shape:
                    return cv2.resize(loaded, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_AREA)
                return loaded

        self._ensure_manifest()
        cam_df = self._manifest_by_cam.get(cam_id)
        if cam_df is None or cam_df.empty:
            with self._lock:
                self._bg_cache[cache_key] = None
            return None

        if regime == "day":
            sub = cam_df[cam_df["hour"].between(9, 16)]
            max_samples = 35
            if len(sub) < 5:
                q_hi = cam_df["brightness_mean"].quantile(0.6)
                sub = cam_df[cam_df["brightness_mean"] >= q_hi]
        else:
            sub = cam_df[cam_df["hour"] >= 19]
            max_samples = 30
            if len(sub) < 5:
                q_lo = cam_df["brightness_mean"].quantile(0.35)
                sub = cam_df[cam_df["brightness_mean"] <= q_lo]

        if sub.empty:
            sub = cam_df

        if len(sub) > max_samples:
            sub = sub.sample(max_samples, random_state=42)

        frames: list[np.ndarray] = []
        th, tw = target_shape
        for rel_path in sub["clean_rel_path"]:
            fpath = self.clean_dir / str(rel_path)
            frame = cv2.imread(str(fpath))
            if frame is None:
                continue
            if frame.shape[:2] != (th, tw):
                frame = cv2.resize(frame, (tw, th), interpolation=cv2.INTER_AREA)
            frames.append(frame)

        if len(frames) < 3:
            with self._lock:
                self._bg_cache[cache_key] = None
            return None

        bg = np.median(np.stack(frames, axis=0), axis=0).astype(np.uint8)
        cv2.imwrite(str(bg_path), bg)
        with self._lock:
            self._bg_cache[cache_key] = bg
        return bg

    def get_context(
        self,
        image_path: Path | None,
        img_shape: tuple[int, int],
        img_bgr: np.ndarray,
        cam_id_override: int | None = None,
        hour_override: int | None = None,
    ) -> CameraSceneContext:
        """Resolve day/night median backgrounds and adjacent frames (`<= 30 min`) for an image."""
        parsed_cam_id, parsed_ts = _parse_cam_and_timestamp(image_path) if image_path is not None else (None, None)
        cam_id = cam_id_override if cam_id_override is not None else parsed_cam_id
        hour = hour_override if hour_override is not None else (int(parsed_ts.hour) if parsed_ts is not None else None)

        if cam_id is None:
            return CameraSceneContext(
                cam_id=None,
                timestamp=parsed_ts,
                hour=hour,
                bg_day=None,
                bg_night=None,
                prev_img=None,
                next_img=None,
                prev_mad=None,
                next_mad=None,
            )

        bg_day = self._load_or_build_bg(cam_id, "day", img_shape)
        bg_night = self._load_or_build_bg(cam_id, "night", img_shape)

        prev_img: np.ndarray | None = None
        next_img: np.ndarray | None = None
        prev_mad: float | None = None
        next_mad: float | None = None

        if parsed_ts is not None:
            self._ensure_manifest()
            cam_idx = self._cam_index.get(cam_id)
            if cam_idx is not None:
                ts_arr, dates_arr, rel_paths = cam_idx
                ts_naive = parsed_ts.tz_localize(None) if parsed_ts.tzinfo is not None else parsed_ts
                t0 = float(np.datetime64(ts_naive, "us").astype(np.int64)) / 1e6
                d0 = np.datetime64(ts_naive, "D")

                gray_cur = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
                i_prev = int(bisect_left(ts_arr, t0 - 60.0)) - 1
                if i_prev >= 0 and dates_arr[i_prev] == d0 and (t0 - float(ts_arr[i_prev])) <= 1800.0:
                    p_path = self.clean_dir / rel_paths[i_prev]
                    p_img = self._read_bgr_cached(p_path)
                    if p_img is not None and p_img.shape[:2] == img_shape:
                        prev_img = p_img
                        prev_mad = float(cv2.absdiff(gray_cur, cv2.cvtColor(p_img, cv2.COLOR_BGR2GRAY)).mean())

                i_next = int(bisect_right(ts_arr, t0 + 60.0))
                if i_next < len(ts_arr) and dates_arr[i_next] == d0 and (float(ts_arr[i_next]) - t0) <= 1800.0:
                    n_path = self.clean_dir / rel_paths[i_next]
                    n_img = self._read_bgr_cached(n_path)
                    if n_img is not None and n_img.shape[:2] == img_shape:
                        next_img = n_img
                        next_mad = float(cv2.absdiff(gray_cur, cv2.cvtColor(n_img, cv2.COLOR_BGR2GRAY)).mean())

        return CameraSceneContext(
            cam_id=cam_id,
            timestamp=parsed_ts,
            hour=hour,
            bg_day=bg_day,
            bg_night=bg_night,
            prev_img=prev_img,
            next_img=next_img,
            prev_mad=prev_mad,
            next_mad=next_mad,
        )


class RoadRoiProvider:
    """Loads per-camera Road ROI polygons (`data/camera_rois.json`) and rasterizes cached road masks."""

    def __init__(self, roi_path: Path | None = DEFAULT_ROIS_PATH) -> None:
        self.roi_path = roi_path
        self._lock = threading.Lock()
        self._cameras: dict[str, dict] = {}
        self._mask_cache: dict[tuple[int, int, int], tuple[np.ndarray, list[list[list[int]]], float]] = {}
        if roi_path is not None and roi_path.is_file():
            payload = json.loads(roi_path.read_text(encoding="utf-8"))
            self._cameras = payload.get("cameras", {})

    def has_roi(self, cam_id: int | None) -> bool:
        return cam_id is not None and str(cam_id) in self._cameras

    def get_roi(
        self,
        cam_id: int | None,
        img_shape: tuple[int, int],
    ) -> tuple[np.ndarray | None, list[list[list[int]]], float]:
        """Return `(roi_mask_uint8, polygons_px, road_roi_area)` with GOAL.md 15% safety floor."""
        img_h, img_w = img_shape
        fallback_area = 0.15 * float(img_w * img_h)
        if cam_id is None:
            return None, [], fallback_area

        key = (int(cam_id), img_h, img_w)
        with self._lock:
            if key in self._mask_cache:
                return self._mask_cache[key]

        cam_info = self._cameras.get(str(int(cam_id)))
        if not cam_info:
            return None, [], fallback_area

        polys_norm = cam_info.get("polygons_norm") or []
        polys_px: list[list[list[int]]] = []
        if polys_norm:
            for poly in polys_norm:
                pts = [[max(0, min(img_w - 1, int(round(px * img_w)))), max(0, min(img_h - 1, int(round(py * img_h))))] for px, py in poly]
                if len(pts) >= 3:
                    polys_px.append(pts)
        else:
            for poly in cam_info.get("polygons_px") or []:
                pts = [[max(0, min(img_w - 1, int(round(px)))), max(0, min(img_h - 1, int(round(py))))] for px, py in poly]
                if len(pts) >= 3:
                    polys_px.append(pts)

        if not polys_px:
            return None, [], fallback_area

        mask = np.zeros((img_h, img_w), dtype=np.uint8)
        for poly in polys_px:
            cv2.fillPoly(mask, [np.array(poly, dtype=np.int32)], 255)
        area_px = max(float((mask > 0).sum()), fallback_area)
        result = (mask, polys_px, area_px)
        with self._lock:
            self._mask_cache[key] = result
        return result

    @staticmethod
    def box_in_roi(box: tuple[float, float, float, float], roi_mask: np.ndarray) -> bool:
        """Retain detections whose tire ground-contact center or >=35% of box area lies inside the active road ROI."""
        img_h, img_w = roi_mask.shape[:2]
        x1, y1, x2, y2 = box
        bx = max(0, min(img_w - 1, int(round(0.5 * (x1 + x2)))))
        # 85% down from top places the check at wheel/bumper ground-contact height so tall buses still pass.
        by = max(0, min(img_h - 1, int(round(0.85 * y2 + 0.15 * y1))))
        if roi_mask[by, bx] > 0:
            return True
        ix1 = max(0, min(img_w - 1, int(round(x1))))
        iy1 = max(0, min(img_h - 1, int(round(y1))))
        ix2 = max(ix1 + 1, min(img_w, int(round(x2))))
        iy2 = max(iy1 + 1, min(img_h, int(round(y2))))
        return float((roi_mask[iy1:iy2, ix1:ix2] > 0).mean()) >= 0.35


def _compute_union_bbox_area(boxes_xyxy: list[list[float]] | np.ndarray, img_w: int, img_h: int) -> float:
    """Compute exact non-double-counted pixel union area across kept bounding boxes."""
    if len(boxes_xyxy) == 0:
        return 0.0
    canvas = np.zeros((img_h, img_w), dtype=np.uint8)
    for b in boxes_xyxy:
        x1 = max(0, min(img_w - 1, int(round(float(b[0])))))
        y1 = max(0, min(img_h - 1, int(round(float(b[1])))))
        x2 = max(x1 + 1, min(img_w, int(round(float(b[2])))))
        y2 = max(y1 + 1, min(img_h, int(round(float(b[3])))))
        canvas[y1:y2, x1:x2] = 255
    return float((canvas > 0).sum())


def build_optical_views(
    img_bgr: np.ndarray,
    hour: int | None = None,
) -> tuple[list[tuple[str, np.ndarray]], dict[str, float | bool | int | None]]:
    """Profile optical image quality and conditionally synthesize glare-suppressed CLAHE view."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    brightness_mean = float(gray.mean())
    contrast_std = float(gray.std())
    glare_ratio = float((gray > 240).mean())
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    is_night_or_glare = (
        (hour is not None and hour >= 18)
        or (brightness_mean < 90.0)
        or (glare_ratio > 0.045)
    )
    is_low_contrast_or_rain = contrast_std < 34.0

    profile: dict[str, float | bool | int | None] = {
        "brightness_mean": round(brightness_mean, 2),
        "contrast_std": round(contrast_std, 2),
        "glare_ratio": round(glare_ratio, 4),
        "laplacian_var": round(laplacian_var, 2),
        "is_night_or_glare": bool(is_night_or_glare),
        "is_low_contrast_or_rain": bool(is_low_contrast_or_rain),
        "hour": hour,
    }

    views: list[tuple[str, np.ndarray]] = [("orig", img_bgr)]
    if is_night_or_glare:
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)

        # Nighttime View 2 ("enh"): gentler shadow recovery & mild unsharp only on heavily blurred lenses.
        l_float = l_ch.astype(np.float32)
        hi_mask = l_float > 210.0
        l_float[hi_mask] = 210.0 + 0.30 * (l_float[hi_mask] - 210.0)
        l_comp = np.clip(l_float, 0, 255).astype(np.uint8)
        l_clahe = cv2.createCLAHE(clipLimit=2.3, tileGridSize=(8, 8)).apply(l_comp)
        gamma = 0.68 if brightness_mean < 90.0 else 0.76
        lut = np.clip(((np.arange(256, dtype=np.float32) / 255.0) ** gamma) * 255.0, 0, 255).astype(np.uint8)
        l_enh = cv2.LUT(l_clahe, lut)
        img_enh = cv2.cvtColor(cv2.merge([l_enh, a_ch, b_ch]), cv2.COLOR_LAB2BGR)
        if laplacian_var < 350.0:
            img_enh = cv2.addWeighted(img_enh, 1.18, cv2.GaussianBlur(img_enh, (0, 0), 1.2), -0.18, 0)
        views.append(("enh", img_enh))

        # Nighttime View 3 ("deglare"): headlight-bloom compression without unsharp edge hallucination.
        l_dg_f = l_ch.astype(np.float32)
        glare_mask = l_dg_f > 160.0
        l_dg_f[glare_mask] = 160.0 + 0.28 * (l_dg_f[glare_mask] - 160.0)
        l_dg_u8 = np.clip(l_dg_f, 0, 255).astype(np.uint8)
        l_dg_clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l_dg_u8)
        lut_dg = np.clip(((np.arange(256, dtype=np.float32) / 255.0) ** 0.88) * 255.0, 0, 255).astype(np.uint8)
        l_dg = cv2.LUT(l_dg_clahe, lut_dg)
        img_deglare = cv2.cvtColor(cv2.merge([l_dg, a_ch, b_ch]), cv2.COLOR_LAB2BGR)
        views.append(("deglare", img_deglare))
    elif is_low_contrast_or_rain:
        enh_f = img_bgr.astype(np.float32)
        hi_mask = enh_f > 215.0
        enh_f[hi_mask] = 215.0 + 0.35 * (enh_f[hi_mask] - 215.0)
        enh_u8 = np.clip(enh_f, 0, 255).astype(np.uint8)

        lab = cv2.cvtColor(enh_u8, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
        l_ch = clahe.apply(l_ch)

        gamma = 0.78 if brightness_mean < 95.0 else 0.90
        lut = np.clip(((np.arange(256, dtype=np.float32) / 255.0) ** gamma) * 255.0, 0, 255).astype(np.uint8)
        l_ch = cv2.LUT(l_ch, lut)
        img_enh = cv2.cvtColor(cv2.merge([l_ch, a_ch, b_ch]), cv2.COLOR_LAB2BGR)
        views.append(("enh", img_enh))

    return views, profile


def _high_contrast_text_strokes(img_bgr: np.ndarray, hi: int, lo: int, diff_thresh: int) -> np.ndarray:
    """Identify thin bright, dark, or green OSD glyph strokes relative to local 9x9 background."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    med9 = cv2.medianBlur(gray, 9)
    diff = np.abs(gray.astype(np.int16) - med9.astype(np.int16))
    return ((gray > hi) | (gray < lo)) & (diff > diff_thresh)


def _model_family(model_key: str) -> str:
    """Map an expert model key to its independent training-domain family."""
    if model_key in VISDRONE_KEYS:
        return "visdrone_fam"
    if model_key in COCO_KEYS:
        return "coco_fam"
    if model_key in BDD_KEYS:
        return "bdd_fam"
    return "uvh26_fam"


def _filter_osd_text_rows(
    raw_mask: np.ndarray,
    static_osd: np.ndarray,
    green_stroke: np.ndarray,
    has_bg: bool,
) -> np.ndarray:
    """Keep only horizontally collinear glyph components forming real camera OSD text rows."""
    h, w = raw_mask.shape[:2]
    clean = np.zeros((h, w), dtype=np.uint8)
    if not raw_mask.any():
        return clean

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(raw_mask, connectivity=8)
    half_split = h // 2
    candidates: list[dict[str, float | int]] = []
    for lbl in range(1, n_labels):
        area = int(stats[lbl, cv2.CC_STAT_AREA])
        bw = int(stats[lbl, cv2.CC_STAT_WIDTH])
        bh = int(stats[lbl, cv2.CC_STAT_HEIGHT])
        if not (3 <= area <= 220 and 1 <= bw <= 28 and 5 <= bh <= 24):
            continue
        if (bw / max(bh, 1)) > 2.2:
            continue
        x1 = int(stats[lbl, cv2.CC_STAT_LEFT])
        y1 = int(stats[lbl, cv2.CC_STAT_TOP])
        x2 = x1 + bw
        y2 = y1 + bh
        yc = 0.5 * (y1 + y2)
        candidates.append(
            {
                "lbl": lbl,
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "bh": bh,
                "yc": yc,
                "is_top": 1 if yc < half_split else 0,
            }
        )

    for c in candidates:
        row_group = [
            o
            for o in candidates
            if o["is_top"] == c["is_top"]
            and abs(o["yc"] - c["yc"]) <= 6.0
            and abs(o["bh"] - c["bh"]) <= 10.0
        ]
        if len(row_group) < 5:
            continue
        rx1 = min(int(o["x1"]) for o in row_group)
        ry1 = min(int(o["y1"]) for o in row_group)
        rx2 = max(int(o["x2"]) for o in row_group)
        ry2 = max(int(o["y2"]) for o in row_group)
        if (rx2 - rx1) < 45:
            continue

        px1 = max(0, rx1 - 4)
        py1 = max(0, ry1 - 2)
        px2 = min(w, rx2 + 4)
        py2 = min(h, ry2 + 2)
        has_green = int(green_stroke[py1:py2, px1:px2].sum()) >= 8
        if has_bg and not has_green:
            # Verify static median background also shows text contrast along the same row strip.
            if int(static_osd[py1:py2, px1:px2].sum()) < 10:
                continue

        clean[labels == int(c["lbl"])] = 255

    if not clean.any():
        return clean
    return cv2.dilate(clean, np.ones((3, 3), dtype=np.uint8), iterations=1)


def build_osd_mask(
    img_bgr: np.ndarray,
    bg_day: np.ndarray | None = None,
    bg_night: np.ndarray | None = None,
) -> np.ndarray:
    """Build binary mask (`0`/`255`) covering verified horizontal OSD glyph rows in top/bottom margins."""
    h, w = img_bgr.shape[:2]
    stroke = _high_contrast_text_strokes(img_bgr, hi=175, lo=40, diff_thresh=24)
    b, g, r = cv2.split(img_bgr)
    green_stroke = (g.astype(np.int16) - np.maximum(r, b).astype(np.int16) > 30) & (g > 110)

    static_osd = np.zeros((h, w), dtype=bool)
    has_bg = False
    for bg in (bg_day, bg_night):
        if bg is None:
            continue
        has_bg = True
        bg_resized = bg if bg.shape[:2] == (h, w) else cv2.resize(bg, (w, h), interpolation=cv2.INTER_AREA)
        static_osd |= _high_contrast_text_strokes(bg_resized, hi=170, lo=40, diff_thresh=22)

    band = np.zeros((h, w), dtype=bool)
    band[: int(0.12 * h), :] = True
    band[int(0.84 * h) :, :] = True
    raw_mask = ((stroke | green_stroke | static_osd) & band).astype(np.uint8)
    return _filter_osd_text_rows(raw_mask, static_osd=static_osd, green_stroke=green_stroke, has_bg=has_bg)


def inpaint_osd_text(img_bgr: np.ndarray, osd_mask: np.ndarray | None) -> np.ndarray:
    """Inpaint OSD timestamp glyphs using Navier-Stokes / TELEA so occluded vehicles remain visible."""
    if osd_mask is None or not osd_mask.any():
        return img_bgr.copy()
    return cv2.inpaint(img_bgr, osd_mask, 3, cv2.INPAINT_TELEA)


def build_smart_crops(
    img_bgr: np.ndarray,
    osd_mask: np.ndarray | None = None,
) -> list[tuple[str, tuple[int, int, int, int], np.ndarray]]:
    """Generate raw full-frame view plus TELEA OSD-inpainted far/lower multi-scale crops."""
    h, w = img_bgr.shape[:2]
    mask = osd_mask if osd_mask is not None else build_osd_mask(img_bgr)
    has_osd = bool(mask is not None and mask.any())
    osd_clean = inpaint_osd_text(img_bgr, mask) if has_osd else img_bgr

    specs: list[tuple[str, tuple[int, int, int, int], np.ndarray]] = [
        ("full", (0, 0, w, h), img_bgr),
    ]
    if has_osd:
        specs.append(("full_osd", (0, 0, w, h), osd_clean))
    specs.extend(
        [
            ("far_mid", (int(0.08 * w), int(0.02 * h), int(0.92 * w), int(0.65 * h)), osd_clean),
            ("lower_road", (int(0.04 * w), int(0.32 * h), int(0.96 * w), h), osd_clean),
            ("lower_left", (0, int(0.30 * h), int(0.62 * w), h), osd_clean),
            ("lower_right", (int(0.38 * w), int(0.30 * h), w, h), osd_clean),
        ]
    )
    return [(tag, (x0, y0, x1, y1), src[y0:y1, x0:x1]) for tag, (x0, y0, x1, y1), src in specs]


class RobustTrafficDetector:
    """Multi-expert ensemble + physics/background-gated urban traffic detector."""

    def __init__(
        self,
        clean_dir: Path = DEFAULT_CLEAN_DIR,
        bg_dir: Path = DEFAULT_BG_DIR,
        roi_path: Path | None = DEFAULT_ROIS_PATH,
        use_roi: bool = True,
        imgsz: int = 640,
        raw_conf: float = 0.14,
        use_half: bool | None = None,
    ) -> None:
        self.scene_provider = CameraSceneProvider(clean_dir=clean_dir, bg_dir=bg_dir)
        self.roi_provider = RoadRoiProvider(roi_path=roi_path)
        self.use_roi = bool(use_roi)
        self.imgsz = imgsz
        self.raw_conf = raw_conf
        self.use_half = torch.cuda.is_available() if use_half is None else bool(use_half)
        self._precision_kwargs: dict[str, object] = (
            ({"quantize": 16} if self.use_half else {})
            if "quantize" in DEFAULT_CFG_DICT
            else {"half": self.use_half}
        )
        self.models: dict[str, YOLO] = {}
        self._load_experts()

    def _load_experts(self) -> None:
        for spec in EXPERT_SPECS:
            weights = _resolve_expert_weights(spec)
            self.models[spec.key] = YOLO(weights)

    def _run_model_on_crops(
        self,
        model_key: str,
        crop_items: list[tuple[str, str, tuple[int, int, int, int], np.ndarray]],
        img_w: int,
        img_h: int,
        raw_conf_override: float | None = None,
    ) -> tuple[list[RawDetection], list[RawDetection]]:
        """Run one expert model in a batch across views/crops and apply interior border truncation guard."""
        model = self.models[model_key]
        imgs = [item[3] for item in crop_items]
        eff_conf = self.raw_conf if raw_conf_override is None else float(raw_conf_override)
        results = model.predict(
            source=imgs,
            imgsz=self.imgsz,
            conf=eff_conf,
            iou=0.75,
            max_det=500,
            verbose=False,
            **self._precision_kwargs,
        )
        return self._parse_model_results(model_key, crop_items, results, img_w, img_h)

    @staticmethod
    def _parse_model_results(
        model_key: str,
        crop_items: list[tuple[str, str, tuple[int, int, int, int], np.ndarray]],
        results: list,
        img_w: int,
        img_h: int,
    ) -> tuple[list[RawDetection], list[RawDetection]]:
        """Project Ultralytics crop predictions back to full-frame coordinates with crop-border filtering."""
        vehicle_dets: list[RawDetection] = []
        rider_dets: list[RawDetection] = []

        for (view_tag, crop_tag, (x0, y0, x1, y1), _), res in zip(crop_items, results):
            if res.boxes is None or len(res.boxes) == 0:
                continue
            cw = float(x1 - x0)
            ch = float(y1 - y0)
            xyxy_arr = res.boxes.xyxy.cpu().numpy()
            conf_arr = res.boxes.conf.cpu().numpy()
            cls_arr = res.boxes.cls.cpu().numpy().astype(int)

            for (lx1, ly1, lx2, ly2), cf, cid in zip(xyxy_arr, conf_arr, cls_arr):
                if crop_tag not in ("full", "full_osd"):
                    # Drop truncated partial vehicles touching an interior crop cut.
                    if x0 > 0 and lx1 < 3.0:
                        continue
                    if y0 > 0 and ly1 < 3.0:
                        continue
                    if x1 < img_w and (cw - lx2) < 3.0:
                        continue
                    if y1 < img_h and (ch - ly2) < 3.0:
                        continue

                gx1 = float(np.clip(lx1 + x0, 0.0, img_w))
                gy1 = float(np.clip(ly1 + y0, 0.0, img_h))
                gx2 = float(np.clip(lx2 + x0, 0.0, img_w))
                gy2 = float(np.clip(ly2 + y0, 0.0, img_h))
                if gx2 <= gx1 or gy2 <= gy1:
                    continue

                raw_name = str(res.names[int(cid)]).strip()
                raw_lower = raw_name.lower()

                if raw_lower in RIDER_CLASSES_LOWER:
                    include_rider = (model_key in (COCO_KEYS | VISDRONE_KEYS)) or (
                        model_key == "bdd100k" and raw_lower == "rider"
                    )
                    if include_rider:
                        rider_dets.append(
                            RawDetection(
                                x1=gx1,
                                y1=gy1,
                                x2=gx2,
                                y2=gy2,
                                conf=float(cf),
                                cls_name=raw_lower,
                                orig_cls_name=raw_name,
                                model_key=model_key,
                                view_tag=view_tag,
                                crop_tag=crop_tag,
                            )
                        )
                    continue

                canonical = CANONICAL_CLASS_MAP.get(raw_lower)
                if canonical is None:
                    continue

                # UVH-26 Bus/Truck detections on sub-crops are unreliable (stairs/zebra/signs).
                if model_key == "uvh26" and crop_tag not in ("full", "full_osd") and canonical in ("bus", "truck"):
                    continue

                is_weak_truck = False
                if model_key in VISDRONE_KEYS and canonical == "truck":
                    box_area = (gx2 - gx1) * (gy2 - gy1)
                    if box_area <= 0.08 * img_w * img_h:
                        # VisDrone calls oblique sedans/SUVs "truck"; treat as car unless corroborated.
                        is_weak_truck = True

                vehicle_dets.append(
                    RawDetection(
                        x1=gx1,
                        y1=gy1,
                        x2=gx2,
                        y2=gy2,
                        conf=float(cf),
                        cls_name=canonical,
                        orig_cls_name=raw_name,
                        model_key=model_key,
                        view_tag=view_tag,
                        crop_tag=crop_tag,
                        is_weak_truck=is_weak_truck,
                        from_three_wheeler=raw_lower in ("tricycle", "awning-tricycle", "three-wheeler"),
                    )
                )

        return vehicle_dets, rider_dets

    def _corroborate_classes(
        self,
        vehicle_dets: list[RawDetection],
        img_w: int,
        img_h: int,
    ) -> list[RawDetection]:
        """Resolve VisDrone weak trucks and check UVH-26 full-frame Bus/Truck corroboration."""
        strong_heavy = [
            d for d in vehicle_dets
            if (d.model_key in (COCO_KEYS | BDD_KEYS) and d.cls_name in ("truck", "bus"))
            or (d.model_key == "uvh26" and d.cls_name in ("truck", "bus") and d.conf >= 0.45)
        ]
        full_other_vehicles = [
            d for d in vehicle_dets
            if d.model_key in (COCO_KEYS | BDD_KEYS | VISDRONE_KEYS) and d.crop_tag in ("full", "full_osd") and d.cls_name in GROUP_4W
        ]

        refined: list[RawDetection] = []
        for det in vehicle_dets:
            box = (det.x1, det.y1, det.x2, det.y2)
            if det.is_weak_truck:
                corroborated = any(
                    _box_iou_single(box, (h.x1, h.y1, h.x2, h.y2)) >= 0.35 for h in strong_heavy
                )
                if not corroborated:
                    det.cls_name = "car"
                    det.is_weak_truck = False

            # Even on full-frame, UVH-26 low/mid-conf Bus/Truck hallucinations without heavy/vehicle
            # corroboration from YOLO26x or VisDrone should require stricter background scrutiny later.
            if det.model_key == "uvh26" and det.cls_name in ("bus", "truck") and det.conf < 0.45:
                corroborated = any(
                    _box_iou_single(box, (o.x1, o.y1, o.x2, o.y2)) >= 0.35 for o in full_other_vehicles
                )
                if not corroborated:
                    # Keep as low-priority candidate only if background gate passes strongly.
                    det.conf *= 0.85

            refined.append(det)
        return refined

    def _promote_riders_to_motorcycles(
        self,
        vehicle_dets: list[RawDetection],
        rider_dets: list[RawDetection],
        img_bgr: np.ndarray,
        scene: CameraSceneContext | None = None,
        is_night_or_glare: bool = False,
        roi_mask: np.ndarray | None = None,
    ) -> list[RawDetection]:
        """Boost/promote detected riders (`person`/`pedestrian`/`rider`) that overlap a two-wheeler."""
        del scene, roi_mask
        if not rider_dets:
            return vehicle_dets

        two_wheelers = [d for d in vehicle_dets if d.cls_name in GROUP_2W]
        if not two_wheelers:
            return vehicle_dets

        h, w = img_bgr.shape[:2]
        four_wheelers = [d for d in vehicle_dets if d.cls_name in GROUP_4W and d.conf >= 0.25]

        # Filter out people sitting inside 4-wheelers or oversized boxes.
        valid_riders: list[RawDetection] = []
        for r in rider_dets:
            rw = r.x2 - r.x1
            rh = r.y2 - r.y1
            r_area = rw * rh
            if r_area <= 35.0 or r_area > 0.04 * w * h or rw > 0.16 * w:
                continue
            r_box = (r.x1, r.y1, r.x2, r.y2)
            inside_4w = any(
                _box_iomin_and_areas(r_box, (fw.x1, fw.y1, fw.x2, fw.y2))[1] > 0.40
                for fw in four_wheelers
            )
            if not inside_4w:
                valid_riders.append(r)

        promoted: list[RawDetection] = []
        match_iou = 0.12 if is_night_or_glare else 0.15
        match_dist = 16.0 if is_night_or_glare else 14.0

        # Promote only when a rider overlaps an actual two-wheeler detection (never standalone pedestrians).
        for r in valid_riders:
            rcx, rcy = 0.5 * (r.x1 + r.x2), 0.5 * (r.y1 + r.y2)
            for m in two_wheelers:
                mcx, mcy = 0.5 * (m.x1 + m.x2), 0.5 * (m.y1 + m.y2)
                dist = float(np.hypot(rcx - mcx, rcy - mcy))
                iou = _box_iou_single((r.x1, r.y1, r.x2, r.y2), (m.x1, m.y1, m.x2, m.y2))
                if iou >= match_iou or dist < match_dist:
                    ux1 = min(r.x1, m.x1)
                    uy1 = min(r.y1, m.y1)
                    ux2 = max(r.x2, m.x2)
                    uy2 = max(r.y2, m.y2)
                    if (ux2 - ux1) <= 0.25 * w and (uy2 - uy1) <= 0.36 * h:
                        promoted.append(
                            RawDetection(
                                x1=ux1,
                                y1=uy1,
                                x2=ux2,
                                y2=uy2,
                                conf=min(0.92, max(m.conf, r.conf) + 0.12),
                                cls_name="motorcycle",
                                orig_cls_name="rider+motorcycle",
                                model_key=r.model_key,
                                view_tag=r.view_tag,
                                crop_tag=r.crop_tag,
                            )
                        )
                    break

        return vehicle_dets + promoted

    def _filter_by_geometry(
        self,
        dets: list[RawDetection],
        img_w: int,
        img_h: int,
    ) -> list[RawDetection]:
        """Apply perspective-aware size and aspect-ratio bounds per vehicle group."""
        kept: list[RawDetection] = []
        frame_area = float(img_w * img_h)
        for d in dets:
            bw = d.x2 - d.x1
            bh = d.y2 - d.y1
            area = bw * bh
            if bw <= 1.0 or bh <= 1.0:
                continue
            if (d.y1 <= 1.0 and bh < 7.0) or (d.y2 >= img_h - 1.0 and bh < 7.0):
                continue
            ar = bw / bh
            if ar > 4.2 or ar < 0.22:
                continue

            yc = 0.5 * (d.y1 + d.y2)
            if d.cls_name in GROUP_2W:
                if bw < 4.0 or bh < 6.0 or area < 28.0:
                    continue
                if bw > 0.25 * img_w or bh > 0.36 * img_h or area > 0.048 * frame_area:
                    continue
            else:
                if bw < 4.5 or bh < 5.0 or area < 24.0:
                    continue
                if d.cls_name == "car" and (
                    area > 0.24 * frame_area or (yc < 0.45 * img_h and area > 0.075 * frame_area)
                ):
                    continue
                if d.cls_name in ("bus", "truck") and area > 0.85 * frame_area:
                    continue

            kept.append(d)
        return kept

    def _is_osd_text_box(
        self,
        box: tuple[float, float, float, float],
        osd_mask: np.ndarray | None,
        img_h: int,
        is_night_or_glare: bool = False,
    ) -> bool:
        """Veto small false-positive boxes landing directly on verified top/bottom OSD glyph rows."""
        if osd_mask is None or not osd_mask.any():
            return False
        x1, y1, x2, y2 = box
        if is_night_or_glare:
            if not (y2 <= 0.14 * img_h or y1 >= 0.77 * img_h):
                return False
        elif not (y2 <= 0.13 * img_h or y1 >= 0.83 * img_h):
            return False
        bh = y2 - y1
        if bh > 28.0:
            return False

        h, w = osd_mask.shape[:2]
        ix1 = max(0, min(w - 1, int(round(x1))))
        iy1 = max(0, min(h - 1, int(round(y1))))
        ix2 = max(ix1 + 1, min(w, int(round(x2))))
        iy2 = max(iy1 + 1, min(h, int(round(y2))))
        patch = osd_mask[iy1:iy2, ix1:ix2] > 0
        if patch.size == 0:
            return False
        osd_ratio = float(patch.mean())
        return osd_ratio > (0.20 if is_night_or_glare else 0.28)

    def _compute_bg_and_motion_stats(
        self,
        box: tuple[float, float, float, float],
        gray_img: np.ndarray,
        edge_img: np.ndarray,
        gray_bg_active: np.ndarray | None,
        edge_bg_day: np.ndarray | None,
        edge_bg_night: np.ndarray | None,
        gray_prev: np.ndarray | None,
        edge_prev: np.ndarray | None,
        gray_next: np.ndarray | None,
        edge_next: np.ndarray | None,
        valid_mask: np.ndarray | None = None,
    ) -> dict[str, float | None]:
        """Compute clean-background foreground difference, edge NCC, and adjacent-frame motion."""
        h, w = gray_img.shape[:2]
        x1 = max(0, min(w - 1, int(round(box[0]))))
        y1 = max(0, min(h - 1, int(round(box[1]))))
        x2 = max(x1 + 1, min(w, int(round(box[2]))))
        y2 = max(y1 + 1, min(h, int(round(box[3]))))

        vm = valid_mask[y1:y2, x1:x2] if valid_mask is not None else None
        has_valid = vm is not None and bool(vm.any())

        fg_bg_15: float | None = None
        fg_bg_25: float | None = None
        if gray_bg_active is not None:
            diff = cv2.absdiff(gray_img[y1:y2, x1:x2], gray_bg_active[y1:y2, x1:x2])
            diff_vals = diff[vm] if has_valid else diff
            fg_bg_15 = float((diff_vals > 15).mean())
            fg_bg_25 = float((diff_vals > 25).mean())

        ncc_vals: list[float] = []
        e_patch = edge_img[y1:y2, x1:x2]
        ncc_edge_day = _safe_ncc(e_patch, edge_bg_day[y1:y2, x1:x2]) if edge_bg_day is not None else None
        ncc_edge_night = _safe_ncc(e_patch, edge_bg_night[y1:y2, x1:x2]) if edge_bg_night is not None else None
        if ncc_edge_day is not None:
            ncc_vals.append(ncc_edge_day)
        if ncc_edge_night is not None:
            ncc_vals.append(ncc_edge_night)
        ncc_edge_bg = max(ncc_vals) if ncc_vals else None

        adj_fg_vals: list[float] = []
        adj_ncc_vals: list[float] = []
        g_patch = gray_img[y1:y2, x1:x2]
        if gray_prev is not None and edge_prev is not None:
            p_diff = cv2.absdiff(g_patch, gray_prev[y1:y2, x1:x2])
            adj_fg_vals.append(float(((p_diff[vm] if has_valid else p_diff) > 15).mean()))
            adj_ncc_vals.append(_safe_ncc(e_patch, edge_prev[y1:y2, x1:x2]))
        if gray_next is not None and edge_next is not None:
            n_diff = cv2.absdiff(g_patch, gray_next[y1:y2, x1:x2])
            adj_fg_vals.append(float(((n_diff[vm] if has_valid else n_diff) > 15).mean()))
            adj_ncc_vals.append(_safe_ncc(e_patch, edge_next[y1:y2, x1:x2]))

        min_fg_adj = min(adj_fg_vals) if adj_fg_vals else None
        max_ncc_adj = max(adj_ncc_vals) if adj_ncc_vals else None
        patch_std = float(g_patch.std()) if g_patch.size > 0 else 0.0
        has_light_contrast = bool(
            g_patch.size > 0
            and (
                (float(np.percentile(g_patch, 95)) - float(np.percentile(g_patch, 20)) >= 48.0)
                or (float(g_patch.max()) >= 190.0 and patch_std >= 18.0)
            )
        )
        is_zebra_pattern = _has_zebra_oscillation(g_patch, ncc_edge_bg)

        return {
            "fg_bg_15": fg_bg_15,
            "fg_bg_25": fg_bg_25,
            "ncc_edge_bg": ncc_edge_bg,
            "ncc_edge_day": ncc_edge_day,
            "ncc_edge_night": ncc_edge_night,
            "min_fg_adj": min_fg_adj,
            "max_ncc_adj": max_ncc_adj,
            "has_light_contrast": 1.0 if has_light_contrast else 0.0,
            "is_zebra_pattern": 1.0 if is_zebra_pattern else 0.0,
        }

    def _is_static_or_parked(
        self,
        stats: dict[str, float | None],
        single_low_conf: bool,
        is_night_or_glare: bool = False,
        in_roi: bool = False,
        n_models: int = 1,
        n_families: int = 1,
        pre_cluster: bool = False,
    ) -> bool:
        """Check whether a box matches static background geometry or an unmoved parked vehicle."""
        fg15 = stats["fg_bg_15"]
        fg25 = stats["fg_bg_25"]
        ncc_bg = stats["ncc_edge_bg"]
        min_adj = stats["min_fg_adj"]
        max_ncc_adj = stats["max_ncc_adj"]

        if is_night_or_glare:
            has_light_contrast = (stats.get("has_light_contrast") or 0.0) > 0.5
            is_zebra = (stats.get("is_zebra_pattern") or 0.0) > 0.5

            if pre_cluster:
                if ncc_bg is not None and ncc_bg >= 0.60:
                    return True
                if not has_light_contrast and fg25 is not None and fg25 < 0.04 and (fg15 is None or fg15 < 0.15):
                    return True
                return False

            # Unconditional static edge & zebra crossing match
            if is_zebra and (n_families == 1 or (ncc_bg is not None and ncc_bg >= 0.35)):
                return True
            if ncc_bg is not None and ncc_bg >= 0.56:
                return True
            if (
                ncc_bg is not None
                and max_ncc_adj is not None
                and ncc_bg >= 0.46
                and max_ncc_adj >= 0.68
                and (min_adj is None or min_adj < 0.35 or n_models == 1)
            ):
                return True
            if max_ncc_adj is not None and max_ncc_adj >= 0.82 and (
                single_low_conf or n_models == 1 or (ncc_bg is not None and ncc_bg >= 0.30)
            ):
                return True

            # Dark-shadow / zero-change background rejection when no vehicle lights are present
            if not has_light_contrast:
                if fg25 is not None and fg25 < 0.05:
                    return True
                if fg15 is not None and fg15 < 0.16 and (fg25 is None or fg25 < 0.10):
                    return True
                if min_adj is not None and min_adj < 0.12 and max_ncc_adj is not None and max_ncc_adj >= 0.45:
                    return True

            # Outside active road ROI or weak/stationary boxes across frames
            if not in_roi:
                if fg15 is not None and fg15 < 0.16:
                    return True
                if ncc_bg is not None and fg25 is not None and ncc_bg > 0.45 and fg25 < 0.28:
                    return True

            if single_low_conf:
                if ncc_bg is not None and ncc_bg >= 0.36:
                    return True
                if fg15 is not None and fg15 < 0.18 and not has_light_contrast:
                    return True

            if min_adj is not None and max_ncc_adj is not None:
                if n_models == 1 and min_adj < 0.14 and max_ncc_adj > 0.58:
                    return True
                if min_adj < 0.10 and max_ncc_adj > 0.65:
                    return True

            return False

        # Rule 1: Static background structure (zebra crossing, painted stripes, billboards, bridge rails)
        if fg15 is not None and fg15 < 0.20:
            return True
        if ncc_bg is not None and ncc_bg >= 0.68:
            return True
        if ncc_bg is not None and max_ncc_adj is not None and ncc_bg >= 0.52 and max_ncc_adj >= 0.78:
            return True
        if ncc_bg is not None and fg25 is not None and ncc_bg > 0.50 and fg25 < 0.38:
            return True

        # Rule 2: Single-model low-confidence hallucination on background
        if single_low_conf:
            if fg15 is not None and fg15 < 0.35:
                return True
            if ncc_bg is not None and ncc_bg >= 0.38:
                return True

        # Rule 3: Temporarily parked off-road vehicle or static sign/board across adjacent frames
        if max_ncc_adj is not None and max_ncc_adj >= 0.75 and (
            single_low_conf or (ncc_bg is not None and ncc_bg >= 0.35)
        ):
            return True
        if min_adj is not None and max_ncc_adj is not None:
            if min_adj < 0.16 and max_ncc_adj > 0.55:
                return True

        return False

    def _cluster_group(
        self,
        dets: list[RawDetection],
        iou_thresh: float,
        is_night_or_glare: bool = False,
        frame_area: float = 0.0,
    ) -> list[dict]:
        """Cluster overlapping detections in one physical group and compute fused box/class/score."""
        if not dets:
            return []

        # Sort descending by reliability-weighted confidence so anchors lead clusters.
        model_prior = {
            "yolo26x": 1.06,
            "bdd100k": 1.05,
            "yolo11x": 1.04,
            "uvh26": 1.02,
            "rider_consensus": 1.00,
            "visdrone": 0.96,
            "visdrone26l": 0.95,
        }
        sorted_dets = sorted(
            dets,
            key=lambda d: d.conf * model_prior.get(d.model_key, 1.0),
            reverse=True,
        )

        clusters: list[list[RawDetection]] = []
        cluster_anchors: list[tuple[float, float, float, float]] = []

        for d in sorted_dets:
            d_box = (d.x1, d.y1, d.x2, d.y2)
            best_idx = -1
            best_score = (-1.0, -1.0)
            for idx, anc in enumerate(cluster_anchors):
                iou, iomin, area_d, area_a = _box_iomin_and_areas(d_box, anc)
                area_ratio = min(area_d, area_a) / max(area_d, area_a, 1e-6)
                center_ratio = _box_center_ratio(d_box, anc)
                matched = (
                    (iou >= iou_thresh)
                    or (iomin >= 0.66 and area_ratio >= 0.28)
                    or (iou >= 0.24 and center_ratio <= 0.28 and area_ratio >= 0.38)
                )
                if matched and (iou, iomin) > best_score:
                    best_score = (iou, iomin)
                    best_idx = idx
            if best_idx >= 0:
                clusters[best_idx].append(d)
            else:
                clusters.append([d])
                cluster_anchors.append(d_box)

        fused_items: list[dict] = []
        cls_model_weight = {
            "yolo26x": 1.35,
            "yolo11x": 1.25,
            "bdd100k": 1.25,
            "uvh26": 1.25,
            "rider_consensus": 1.15,
            "visdrone": 0.90,
            "visdrone26l": 0.90,
        }

        for grp in clusters:
            # Top detections per model/view vote cleanly without letting tiny noise skew the box.
            top_k = sorted(grp, key=lambda d: d.conf, reverse=True)[:6]
            weights = np.array([max(d.conf, 0.05) * cls_model_weight.get(d.model_key, 1.0) for d in top_k], dtype=np.float32)
            w_sum = float(weights.sum())
            coords = np.array([[d.x1, d.y1, d.x2, d.y2] for d in top_k], dtype=np.float32)
            fused_xyxy = (coords * weights[:, None]).sum(axis=0) / max(w_sum, 1e-6)

            distinct_models = {
                "uvh26" if d.model_key == "rider_consensus" else d.model_key for d in grp
            }
            families = {_model_family(m) for m in distinct_models}
            n_families = len(families)
            max_raw_conf = max(d.conf for d in grp)
            n_models = len(distinct_models)

            # Consensus confidence boost only reaches full strength across independent model families.
            if n_families >= 3 or (n_families >= 2 and n_models >= 3):
                fused_conf = min(0.98, max_raw_conf + 0.16)
            elif n_families >= 2:
                fused_conf = min(0.96, max_raw_conf + 0.10)
            elif n_models >= 2:
                fused_conf = min(0.94, max_raw_conf + 0.06)
            else:
                fused_conf = max_raw_conf

            # Weighted class voting across experts.
            cls_votes: dict[str, float] = defaultdict(float)
            for d in grp:
                cls_votes[d.cls_name] += d.conf * cls_model_weight.get(d.model_key, 1.0)

            # Heavy-vehicle gate: `bus` or `truck` requires either COCO agreement or
            # strong UVH-26/multi-view support so VisDrone cannot force sedans into trucks.
            best_cls = max(cls_votes.items(), key=lambda kv: kv[1])[0]
            if best_cls in ("bus", "truck"):
                has_coco_heavy = any(d.model_key in (COCO_KEYS | BDD_KEYS) and d.cls_name in ("bus", "truck") for d in grp)
                max_uvh_heavy = max(
                    (d.conf for d in grp if d.model_key == "uvh26" and d.cls_name in ("bus", "truck")),
                    default=0.0,
                )
                if is_night_or_glare:
                    fused_area = max(0.0, float(fused_xyxy[2] - fused_xyxy[0])) * max(0.0, float(fused_xyxy[3] - fused_xyxy[1]))
                    allow_heavy = (
                        has_coco_heavy
                        or max_uvh_heavy >= 0.50
                        or (
                            frame_area > 0.0
                            and fused_area >= 0.06 * frame_area
                            and max_raw_conf >= 0.32
                            and (has_coco_heavy or max_uvh_heavy >= 0.35)
                        )
                    )
                else:
                    allow_heavy = has_coco_heavy or max_uvh_heavy >= 0.50
                if not allow_heavy:
                    if "car" in cls_votes or any(d.cls_name in ("car", "truck", "bus") for d in grp):
                        best_cls = "car"

            fused_items.append(
                {
                    "xyxy": fused_xyxy,
                    "conf": float(fused_conf),
                    "max_raw_conf": float(max_raw_conf),
                    "cls_name": best_cls,
                    "n_models": n_models,
                    "n_families": n_families,
                    "families": families,
                    "models": sorted(distinct_models),
                    "has_3w_vote": any(d.from_three_wheeler for d in grp),
                }
            )

        return fused_items

    def _consolidate_giant_heavy_vehicles(
        self,
        dynamic_candidates: list[RawDetection],
        kept_4w: list[dict],
        all_clusters: list[dict],
        img_w: int,
        img_h: int,
        is_night_or_glare: bool = False,
    ) -> list[dict]:
        """Recover giant close-up bus/truck boxes supported by raw heavy overlap or child enclosures."""
        frame_area = float(img_w * img_h)
        raw_heavy = [
            d
            for d in dynamic_candidates
            if d.cls_name in ("bus", "truck")
            and not d.is_weak_truck
            and (d.x2 - d.x1) * (d.y2 - d.y1) >= 0.08 * frame_area
        ]
        if not raw_heavy:
            return kept_4w

        raw_heavy.sort(key=lambda d: (d.conf, (d.x2 - d.x1) * (d.y2 - d.y1)), reverse=True)
        child_boxes = [tuple(float(v) for v in it["xyxy"]) for it in all_clusters]
        child_areas = [max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1]) for b in child_boxes]

        promoted = list(kept_4w)
        for d in raw_heavy:
            d_box = (d.x1, d.y1, d.x2, d.y2)
            d_area = (d.x2 - d.x1) * (d.y2 - d.y1)

            already_kept = False
            for existing in promoted:
                if existing["cls_name"] in ("bus", "truck") and _box_iou_single(
                    d_box, tuple(float(v) for v in existing["xyxy"])
                ) >= 0.40:
                    existing["is_giant_heavy"] = True
                    already_kept = True
                    break
            if already_kept:
                continue

            overlap_group = [
                h for h in raw_heavy if _box_iou_single(d_box, (h.x1, h.y1, h.x2, h.y2)) >= 0.35
            ]
            models = {"uvh26" if x.model_key == "rider_consensus" else x.model_key for x in overlap_group}
            if is_night_or_glare:
                n_views = len({x.view_tag for x in overlap_group})
                max_raw_grp = max(x.conf for x in overlap_group)
                has_coco_uvh = any(x.model_key in (COCO_KEYS | BDD_KEYS | UVH_KEYS) for x in overlap_group)
                if not (
                    len(models) >= 2
                    or (n_views >= 2 and max_raw_grp >= 0.28)
                    or (has_coco_uvh and max_raw_grp >= 0.34)
                ):
                    continue
            elif len(models) < 2:
                continue

            grp = overlap_group
            top_grp = sorted(grp, key=lambda x: x.conf, reverse=True)[:4]
            w_arr = np.array([max(x.conf, 0.05) for x in top_grp], dtype=np.float32)
            coords = np.array([[x.x1, x.y1, x.x2, x.y2] for x in top_grp], dtype=np.float32)
            fused_xyxy = (coords * w_arr[:, None]).sum(axis=0) / max(float(w_arr.sum()), 1e-6)
            families = {_model_family(m) for m in models}
            max_raw = max(x.conf for x in grp)
            cls_scores: dict[str, float] = defaultdict(float)
            for x in grp:
                cls_scores[x.cls_name] += x.conf
            best_cls = max(cls_scores.items(), key=lambda kv: kv[1])[0]

            promoted.append(
                {
                    "xyxy": fused_xyxy,
                    "conf": float(max(0.75, max_raw)),
                    "max_raw_conf": float(max_raw),
                    "cls_name": best_cls,
                    "n_models": len(models),
                    "n_families": len(families),
                    "families": families,
                    "models": sorted(models),
                    "is_giant_heavy": True,
                }
            )
        return promoted

    def _prune_4w_wrappers(self, items: list[dict]) -> list[dict]:
        """Drop giant 4-wheeler boxes that enclose two or more smaller 4-wheeler detections."""
        if len(items) < 3:
            return items
        drop: set[int] = set()
        for i, item_a in enumerate(items):
            if item_a["cls_name"] in ("bus", "truck") and (
                item_a.get("is_giant_heavy")
                or (item_a.get("n_families", 1) >= 2 and item_a["conf"] >= 0.72)
                or (item_a["n_models"] >= 2 and item_a["conf"] >= 0.80)
            ):
                continue
            ba = tuple(float(v) for v in item_a["xyxy"])
            children = 0
            for j, item_b in enumerate(items):
                if i == j:
                    continue
                bb = tuple(float(v) for v in item_b["xyxy"])
                _iou, iomin, area_a, area_b = _box_iomin_and_areas(ba, bb)
                if area_b < 0.45 * area_a and iomin >= 0.72:
                    children += 1
                    if children >= 2:
                        drop.add(i)
                        break
        return [it for idx, it in enumerate(items) if idx not in drop]

    def _is_distinct_foreground_before_heavy(
        self,
        small_item: dict,
        small_box: tuple[float, float, float, float],
        heavy_box: tuple[float, float, float, float],
        iomin: float,
    ) -> bool:
        """Preserve a genuinely distinct multi-family foreground vehicle positioned ahead of a bus/truck."""
        return (
            small_item.get("n_families", 1) >= 2
            and small_item["conf"] >= 0.82
            and small_box[3] > heavy_box[3] + 6.0
            and iomin < 0.45
        )

    def _prune_within_group_nested(self, items: list[dict], is_4w: bool) -> list[dict]:
        """Suppress nested part-level sub-boxes and overlapping duplicate boxes inside one group."""
        if len(items) < 2:
            return items
        order = sorted(
            range(len(items)),
            key=lambda idx: (items[idx].get("n_families", 1), items[idx]["n_models"], items[idx]["conf"]),
            reverse=True,
        )
        iou_gate = 0.33 if is_4w else 0.30
        dropped: set[int] = set()
        for pos_i, i in enumerate(order):
            if i in dropped:
                continue
            bi = tuple(float(v) for v in items[i]["xyxy"])
            for j in order[pos_i + 1 :]:
                if j in dropped:
                    continue
                bj = tuple(float(v) for v in items[j]["xyxy"])
                iou, iomin, area_i, area_j = _box_iomin_and_areas(bi, bj)
                center_ratio = _box_center_ratio(bi, bj)
                if not (iou >= iou_gate or iomin >= 0.56 or (iou >= 0.22 and center_ratio <= 0.30)):
                    continue

                if area_i >= area_j:
                    small_item, large_item, small_box, large_box, area_s, area_l = (
                        items[j],
                        items[i],
                        bj,
                        bi,
                        area_j,
                        area_i,
                    )
                else:
                    small_item, large_item, small_box, large_box, area_s, area_l = (
                        items[i],
                        items[j],
                        bi,
                        bj,
                        area_i,
                        area_j,
                    )

                if (
                    is_4w
                    and large_item["cls_name"] in ("bus", "truck")
                    and self._is_distinct_foreground_before_heavy(small_item, small_box, large_box, iomin)
                    and area_s < 0.25 * area_l
                    and iou < 0.25
                ):
                    continue

                dropped.add(j)
        return [it for idx, it in enumerate(items) if idx not in dropped]

    def _suppress_heavy_vehicle_subparts(
        self,
        kept_4w: list[dict],
        kept_2w: list[dict],
    ) -> tuple[list[dict], list[dict]]:
        """Suppress smaller 4W/2W sub-part hallucinations on bumpers, wheels, windows, or roofs of buses/trucks."""
        heavy_boxes = [
            (idx, tuple(float(v) for v in it["xyxy"]), max(0.0, float(it["xyxy"][2] - it["xyxy"][0])) * max(0.0, float(it["xyxy"][3] - it["xyxy"][1])))
            for idx, it in enumerate(kept_4w)
            if it["cls_name"] in ("bus", "truck")
        ]
        heavy_boxes = [(idx, b, a) for idx, b, a in heavy_boxes if a >= 900.0]
        if not heavy_boxes:
            return kept_4w, kept_2w

        drop_4w: set[int] = set()
        drop_2w: set[int] = set()

        for target_list, drop_set, is_four_w in ((kept_4w, drop_4w, True), (kept_2w, drop_2w, False)):
            for s_idx, s_item in enumerate(target_list):
                s_box = tuple(float(v) for v in s_item["xyxy"])
                s_area = max(0.0, s_box[2] - s_box[0]) * max(0.0, s_box[3] - s_box[1])
                s_xc = 0.5 * (s_box[0] + s_box[2])
                s_yc = 0.5 * (s_box[1] + s_box[3])

                for h_idx, h_box, h_area in heavy_boxes:
                    if is_four_w and s_idx == h_idx:
                        continue
                    if s_area >= 0.50 * h_area:
                        continue
                    _iou, iomin, _sa, _ha = _box_iomin_and_areas(s_box, h_box)
                    if self._is_distinct_foreground_before_heavy(s_item, s_box, h_box, iomin):
                        continue
                    center_inside = (h_box[0] - 6.0 <= s_xc <= h_box[2] + 6.0) and (
                        h_box[1] - 6.0 <= s_yc <= h_box[3] + 6.0
                    )
                    perimeter_touch = iomin >= 0.12 and (
                        s_item.get("n_families", 1) == 1 or s_item["conf"] < 0.78
                    )
                    if iomin >= 0.22 or center_inside or perimeter_touch:
                        drop_set.add(s_idx)
                        break

        return (
            [it for idx, it in enumerate(kept_4w) if idx not in drop_4w],
            [it for idx, it in enumerate(kept_2w) if idx not in drop_2w],
        )

    def _resolve_cross_group_conflicts(
        self,
        kept_4w: list[dict],
        kept_2w: list[dict],
    ) -> list[dict]:
        """Resolve same-box conflicts and nested part-box hallucinations between 4W and 2W groups."""
        drop_2w: set[int] = set()
        drop_4w: set[int] = set()

        for i4, item4 in enumerate(kept_4w):
            b4 = tuple(float(v) for v in item4["xyxy"])
            for i2, item2 in enumerate(kept_2w):
                if i2 in drop_2w:
                    continue
                b2 = tuple(float(v) for v in item2["xyxy"])
                iou, iomin, area4, area2 = _box_iomin_and_areas(b4, b2)
                center_ratio = _box_center_ratio(b4, b2)
                score4 = (item4["n_models"], item4["conf"])
                score2 = (item2["n_models"], item2["conf"])

                # Case A: Same-box or same-object conflict
                if iou >= 0.34 or (iou >= 0.24 and center_ratio <= 0.30):
                    if score4 >= score2:
                        drop_2w.add(i2)
                    else:
                        drop_4w.add(i4)
                        break
                # Case B: Small 4W inside 2W (e.g., weak car box on motorcycle wheel/shadow)
                elif area4 < area2 and iomin >= 0.55:
                    if item4["n_models"] <= item2["n_models"] or item4["conf"] < 0.75:
                        drop_4w.add(i4)
                        break
                # Case C: Small 2W inside 4W (e.g., taillight/wheel/window/roof false moto/3W on sedan)
                elif area2 < area4 and iomin >= 0.58:
                    strong_multi_moto = item2["n_models"] >= 3 and item2["conf"] >= 0.90
                    if (iomin >= 0.75 and item4["conf"] >= 0.68 and not strong_multi_moto) or (
                        score4 > score2 and (item2["n_models"] == 1 or item2["conf"] < 0.78)
                    ):
                        drop_2w.add(i2)

        final_items: list[dict] = []
        for i4, item4 in enumerate(kept_4w):
            if i4 not in drop_4w:
                final_items.append(item4)
        for i2, item2 in enumerate(kept_2w):
            if i2 not in drop_2w:
                final_items.append(item2)
        return final_items

    def _passes_quality_and_glare_gates(
        self,
        item: dict,
        box: tuple[float, float, float, float],
        gray_img: np.ndarray,
        edge_img: np.ndarray,
        gray_bg_active: np.ndarray | None,
        stats: dict[str, float | None],
        img_w: int,
        img_h: int,
        is_night_or_glare: bool,
        is_low_contrast_or_rain: bool,
        is_blurry: bool,
    ) -> bool:
        """Filter spurious VisDrone-only tiny detections, glare streaks, blurry blobs, and unphysical sub-scales."""
        bw = max(0.0, box[2] - box[0])
        bh = max(0.0, box[3] - box[1])
        ar = bw / max(bh, 1e-6)
        box_area = bw * bh
        yc = 0.5 * (box[1] + box[3])
        n_families = int(item.get("n_families", 1))
        families = item.get("families", set())
        is_visdrone_only = families == {"visdrone_fam"}

        ix1 = max(0, min(img_w - 1, int(round(box[0]))))
        iy1 = max(0, min(img_h - 1, int(round(box[1]))))
        ix2 = max(ix1 + 1, min(img_w, int(round(box[2]))))
        iy2 = max(iy1 + 1, min(img_h, int(round(box[3]))))
        g_patch = gray_img[iy1:iy2, ix1:ix2]
        e_patch = edge_img[iy1:iy2, ix1:ix2]
        diff_90 = (
            float(np.percentile(cv2.absdiff(g_patch, gray_bg_active[iy1:iy2, ix1:ix2]), 90))
            if gray_bg_active is not None and g_patch.size > 0
            else 0.0
        )

        fg15 = stats["fg_bg_15"]
        strong_fg_motion = fg15 is not None and fg15 > 0.35 and diff_90 > 28.0
        is_aerial_moto = (
            not is_night_or_glare
            and item["cls_name"] == "motorcycle"
            and yc > 0.65 * img_h
            and box_area >= 40.0
            and item["max_raw_conf"] >= 0.45
            and (n_families >= 2 or strong_fg_motion)
        )

        if is_visdrone_only:
            min_vd_conf = (0.42 if item["n_models"] == 1 else 0.38) if is_night_or_glare else (0.45 if item["n_models"] == 1 else 0.40)
            if item["max_raw_conf"] < min_vd_conf:
                return False
            if is_night_or_glare:
                if item["cls_name"] in GROUP_2W and (item["max_raw_conf"] < 0.48 or yc > 0.60 * img_h):
                    return False
                if ar < 0.56 or (item["cls_name"] in GROUP_2W and ar > 1.65):
                    return False
                if g_patch.size > 0 and (
                    (
                        (float((g_patch > 220).mean()) > 0.60 or float(g_patch.mean()) > 180.0)
                        and item["n_models"] == 1
                        and item["max_raw_conf"] < 0.38
                        and float(g_patch.std()) < 8.0
                    )
                    or (item["n_models"] == 1 and item["max_raw_conf"] < 0.42 and (ar < 0.48 or ar > 2.3))
                ):
                    return False
                if yc > 0.52 * img_h and box_area < 220.0 and item["max_raw_conf"] < 0.35:
                    return False
            elif is_low_contrast_or_rain or is_blurry:
                if box_area < 320.0 and g_patch.size > 0:
                    if float(e_patch.mean()) < 13.5 or float(g_patch.std()) < 15.0 or item["max_raw_conf"] < 0.48:
                        return False
            else:
                if not is_aerial_moto and item["cls_name"] in GROUP_4W and yc > 0.48 * img_h and box_area < 180.0 and item["max_raw_conf"] < 0.55:
                    return False

        if box_area >= 1200.0 and item["max_raw_conf"] < 0.20:
            return False
        if box_area >= 2000.0 and yc < 0.45 * img_h and item["max_raw_conf"] < 0.30:
            return False

        if is_night_or_glare:
            if (iy1 <= 2 or iy2 >= img_h - 2) and bh <= 10.0 and item["max_raw_conf"] < 0.70:
                return False
            if item["cls_name"] in GROUP_2W:
                if ar < 0.32 or ar > 1.65:
                    return False
                if (
                    (ix1 <= 2 or ix2 >= img_w - 2 or iy1 <= 2)
                    and (box_area < 450.0 or item["n_families"] == 1)
                    and item["max_raw_conf"] < 0.50
                ):
                    return False

        if item["n_models"] == 1:
            if is_night_or_glare:
                if box_area >= 2200.0 and item["max_raw_conf"] < 0.56:
                    return False
                if 600.0 <= box_area < 2200.0 and item["max_raw_conf"] < 0.34:
                    return False
                if box_area < 600.0:
                    item_models_set = set(item.get("models", ()))
                    has_street_expert = bool(item_models_set & (COCO_KEYS | BDD_KEYS | UVH_KEYS))
                    if item["cls_name"] in GROUP_2W:
                        min_2w_s = 0.34 if has_street_expert else 0.46
                        if item["max_raw_conf"] < min_2w_s or ar < 0.36 or ar > 1.55:
                            return False
                    else:
                        min_4w_s = 0.28 if has_street_expert else 0.40
                        if item["max_raw_conf"] < min_4w_s:
                            return False
            else:
                if box_area >= 450.0 and item["max_raw_conf"] < 0.58:
                    return False
                if box_area < 450.0 and item["max_raw_conf"] < 0.35:
                    return False

        if box_area < 500.0 and (n_families == 1 or item["max_raw_conf"] < 0.62) and g_patch.size > 0:
            if is_night_or_glare and box_area < 420.0 and n_families == 1:
                patch_std = float(g_patch.std())
                if (
                    (float((g_patch > 220).mean()) > 0.60 or float(g_patch.mean()) > 180.0)
                    and item["n_models"] == 1
                    and item["max_raw_conf"] < 0.38
                    and patch_std < 8.0
                ):
                    return False
                if (item["cls_name"] in GROUP_4W and ar < 0.56) or (item["cls_name"] in GROUP_2W and ar > 1.65):
                    return False
                if (
                    item["n_models"] == 1
                    and float((g_patch < 50).mean()) > 0.78
                    and item["max_raw_conf"] < 0.26
                    and patch_std < 8.5
                ):
                    return False
            if (is_low_contrast_or_rain or is_blurry) and not is_night_or_glare and box_area < 360.0 and n_families == 1:
                if float(e_patch.mean()) < 13.5 or float(g_patch.std()) < 16.0 or item["max_raw_conf"] < 0.58:
                    return False

        if yc > 0.50 * img_h:
            if item["cls_name"] in GROUP_4W:
                if item.get("has_3w_vote"):
                    if box_area < 42.0 or bw < 4.5 or bh < 8.5:
                        return False
                elif box_area < 125.0 or bw < 9.5 or bh < 9.5:
                    return False
            else:
                if box_area < 42.0 or bw < 4.5 or bh < 8.5:
                    return False
                if is_night_or_glare and n_families == 1 and box_area < 95.0 and item["max_raw_conf"] < 0.38:
                    return False
                if is_night_or_glare and yc > 0.65 * img_h and box_area < 110.0:
                    return False

        return True

    @staticmethod
    def _route_crops_for_frame(
        orig_crops: list[tuple[str, str, tuple[int, int, int, int], np.ndarray]],
        enh_crops: list[tuple[str, str, tuple[int, int, int, int], np.ndarray]],
        deglare_crops: list[tuple[str, str, tuple[int, int, int, int], np.ndarray]],
        is_night_or_glare: bool,
    ) -> list[tuple[str, float | None, list[tuple[str, str, tuple[int, int, int, int], np.ndarray]]]]:
        """Select active day/night experts, per-model raw confidence threshold, and routed crops."""
        enh_primary_tags = {"full", "full_osd", "far_mid", "lower_left", "lower_right"}
        enh_coco_tags = (
            {"full", "full_osd", "far_mid", "lower_road", "lower_left", "lower_right"}
            if is_night_or_glare
            else {"full", "full_osd", "far_mid", "lower_road"}
        )
        active_models = (
            ("uvh26", "visdrone", "bdd100k", "yolo26x", "yolo11x")
            if is_night_or_glare
            else ("uvh26", "visdrone", "visdrone26l", "yolo26x", "yolo11x")
        )
        routed: list[tuple[str, float | None, list[tuple[str, str, tuple[int, int, int, int], np.ndarray]]]] = []
        for model_key in active_models:
            if is_night_or_glare:
                eff_raw_conf: float | None = 0.16 if model_key == "visdrone" else 0.12
                if model_key == "visdrone":
                    # Restrict aerial VisDrone at night to upper/full crops to suppress wet-road stripe hallucinations.
                    model_crops = [c for c in orig_crops if c[1] in ("full", "full_osd", "far_mid")] + [
                        c for c in enh_crops if c[1] in ("full", "far_mid")
                    ]
                else:
                    model_crops = list(orig_crops)
                    if enh_crops:
                        allowed_enh = enh_coco_tags if model_key in (COCO_KEYS | BDD_KEYS) else enh_primary_tags
                        model_crops.extend(c for c in enh_crops if c[1] in allowed_enh)
                    if deglare_crops:
                        dg_tags = {"full"}
                        if model_key in (COCO_KEYS | BDD_KEYS):
                            dg_tags.update({"far_mid", "lower_road"})
                        elif model_key in UVH_KEYS:
                            dg_tags.add("lower_road")
                        model_crops.extend(c for c in deglare_crops if c[1] in dg_tags)
            else:
                eff_raw_conf = None
                if enh_crops:
                    allowed_enh = enh_coco_tags if model_key in COCO_KEYS else enh_primary_tags
                    model_crops = orig_crops + [c for c in enh_crops if c[1] in allowed_enh]
                else:
                    model_crops = orig_crops
            routed.append((model_key, eff_raw_conf, model_crops))
        return routed

    def _prepare_frame(
        self,
        image_source: str | Path | np.ndarray,
        cam_id: int | None = None,
        hour: int | None = None,
        use_roi: bool | None = None,
    ) -> dict:
        """Execute CPU-bound Stages 1-3 (scene context, optical views, OSD inpaint, smart crops & routing)."""
        if isinstance(image_source, np.ndarray):
            img_bgr = image_source
            image_path = None
        else:
            image_path = Path(image_source)
            img_bgr = self.scene_provider._read_bgr_cached(image_path)
            if img_bgr is None:
                raise FileNotFoundError(f"Failed to read image with OpenCV: {image_path}")

        img_h, img_w = img_bgr.shape[:2]

        # Stage 1: Camera multi-regime clean background & adjacent-frame context
        scene = self.scene_provider.get_context(
            image_path=image_path,
            img_shape=(img_h, img_w),
            img_bgr=img_bgr,
            cam_id_override=cam_id,
            hour_override=hour,
        )
        osd_mask = build_osd_mask(img_bgr, bg_day=scene.bg_day, bg_night=scene.bg_night)

        # Stage 2: Optical profiling & conditional glare/rain/low-light view
        views, optical_profile = build_optical_views(img_bgr, hour=scene.hour)
        optical_profile["cam_id"] = scene.cam_id
        is_night_or_glare = bool(optical_profile["is_night_or_glare"])

        # Stage 3: TELEA OSD inpainting & full-height boundary-safe multi-scale crops
        orig_crops: list[tuple[str, str, tuple[int, int, int, int], np.ndarray]] = []
        enh_crops: list[tuple[str, str, tuple[int, int, int, int], np.ndarray]] = []
        deglare_crops: list[tuple[str, str, tuple[int, int, int, int], np.ndarray]] = []
        for view_tag, view_img in views:
            crops = build_smart_crops(view_img, osd_mask=osd_mask)
            for crop_tag, rect, crop_img in crops:
                item = (view_tag, crop_tag, rect, crop_img)
                if view_tag == "orig":
                    orig_crops.append(item)
                elif view_tag == "deglare":
                    deglare_crops.append(item)
                else:
                    enh_crops.append(item)

        # Resolve camera Road ROI early so Stages 5, 6b, 7, and 8 can share the road mask.
        apply_roi = self.use_roi if use_roi is None else bool(use_roi)
        roi_mask, roi_polygons_px, road_roi_area = (
            self.roi_provider.get_roi(scene.cam_id, (img_h, img_w))
            if apply_roi
            else (None, [], 0.15 * float(img_w * img_h))
        )

        routed_models = self._route_crops_for_frame(
            orig_crops=orig_crops,
            enh_crops=enh_crops,
            deglare_crops=deglare_crops,
            is_night_or_glare=is_night_or_glare,
        )
        return {
            "img_bgr": img_bgr,
            "img_w": img_w,
            "img_h": img_h,
            "scene": scene,
            "osd_mask": osd_mask,
            "optical_profile": optical_profile,
            "roi_mask": roi_mask,
            "roi_polygons_px": roi_polygons_px,
            "road_roi_area": road_roi_area,
            "routed_models": routed_models,
        }

    def _finalize_frame_detections(
        self,
        prep: dict,
        all_vehicles: list[RawDetection],
        all_riders: list[RawDetection],
        conf: float,
        use_temporal_gate: bool,
    ) -> DetectionResult:
        """Execute Stages 5-8 (class corroboration, rider promotion, scene/BG/ROI gates, fusion)."""
        img_bgr: np.ndarray = prep["img_bgr"]
        img_w: int = prep["img_w"]
        img_h: int = prep["img_h"]
        scene: CameraSceneContext = prep["scene"]
        osd_mask: np.ndarray = prep["osd_mask"]
        optical_profile: dict = prep["optical_profile"]
        roi_mask: np.ndarray | None = prep["roi_mask"]
        roi_polygons_px: list[list[list[int]]] = prep["roi_polygons_px"]
        road_roi_area: float = prep["road_roi_area"]
        is_night_or_glare = bool(optical_profile["is_night_or_glare"])

        all_vehicles = self._corroborate_classes(all_vehicles, img_w, img_h)

        # Stage 5: Rider-on-road promotion to motorcycle
        all_vehicles = self._promote_riders_to_motorcycles(
            vehicle_dets=all_vehicles,
            rider_dets=all_riders,
            img_bgr=img_bgr,
            scene=scene,
            is_night_or_glare=is_night_or_glare,
            roi_mask=roi_mask,
        )

        # Stage 6a: Perspective-aware geometric gate
        geom_vehicles = self._filter_by_geometry(all_vehicles, img_w, img_h)

        # Prepare background & adjacent-frame grayscale/Sobel maps once per image (excluding OSD glyphs)
        gray_img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        edge_img = _compute_grad_mag(img_bgr)
        bg_active = scene.bg_night if (is_night_or_glare and scene.bg_night is not None) else scene.bg_day
        gray_bg_active = cv2.cvtColor(bg_active, cv2.COLOR_BGR2GRAY) if bg_active is not None else None
        edge_bg_day = _compute_grad_mag(scene.bg_day) if scene.bg_day is not None else None
        edge_bg_night = _compute_grad_mag(scene.bg_night) if scene.bg_night is not None else None

        # Only apply adjacent-frame parked filter against neighbors with real scene change (MAD >= 2.5)
        use_prev = use_temporal_gate and scene.prev_img is not None and (scene.prev_mad or 0.0) >= 2.5
        use_next = use_temporal_gate and scene.next_img is not None and (scene.next_mad or 0.0) >= 2.5
        gray_prev = cv2.cvtColor(scene.prev_img, cv2.COLOR_BGR2GRAY) if use_prev else None
        edge_prev = _compute_grad_mag(scene.prev_img) if use_prev else None
        gray_next = cv2.cvtColor(scene.next_img, cv2.COLOR_BGR2GRAY) if use_next else None
        edge_next = _compute_grad_mag(scene.next_img) if use_next else None

        osd_bool = osd_mask > 0
        valid_mask = ~osd_bool
        if osd_bool.any():
            for em in (edge_img, edge_bg_day, edge_bg_night, edge_prev, edge_next):
                if em is not None:
                    em[osd_bool] = 0.0

        # Stage 6b (pre-clustering): eliminate OSD FPs, definite static structures & parked boxes
        suppressed_static_count = 0
        dynamic_candidates: list[RawDetection] = []
        for det in geom_vehicles:
            d_box = (det.x1, det.y1, det.x2, det.y2)
            if self._is_osd_text_box(d_box, osd_mask, img_h, is_night_or_glare=is_night_or_glare):
                suppressed_static_count += 1
                continue
            in_roi_det = RoadRoiProvider.box_in_roi(d_box, roi_mask) if roi_mask is not None else False
            stats = self._compute_bg_and_motion_stats(
                box=d_box,
                gray_img=gray_img,
                edge_img=edge_img,
                gray_bg_active=gray_bg_active,
                edge_bg_day=edge_bg_day,
                edge_bg_night=edge_bg_night,
                gray_prev=gray_prev,
                edge_prev=edge_prev,
                gray_next=gray_next,
                edge_next=edge_next,
                valid_mask=valid_mask,
            )
            if self._is_static_or_parked(
                stats,
                single_low_conf=False,
                is_night_or_glare=is_night_or_glare,
                in_roi=in_roi_det,
                n_models=(2 if is_night_or_glare else 1),
                n_families=(2 if is_night_or_glare else 1),
                pre_cluster=True,
            ):
                suppressed_static_count += 1
                continue
            dynamic_candidates.append(det)

        # Stage 7: Two-tier cross-class weighted fusion
        group_4w_dets = [d for d in dynamic_candidates if d.cls_name in GROUP_4W]
        group_2w_dets = [d for d in dynamic_candidates if d.cls_name in GROUP_2W]

        frame_area = float(img_w * img_h)
        fused_4w = self._cluster_group(
            group_4w_dets,
            iou_thresh=0.38,
            is_night_or_glare=is_night_or_glare,
            frame_area=frame_area,
        )
        fused_2w = self._cluster_group(
            group_2w_dets,
            iou_thresh=0.34,
            is_night_or_glare=is_night_or_glare,
            frame_area=frame_area,
        )

        # Apply single-model/family scrutiny, optical glare/blur checks, OSD veto, and background gate
        laplacian_var = float(optical_profile.get("laplacian_var") or 0.0)
        is_blurry = laplacian_var < 420.0
        is_low_contrast_or_rain = bool(optical_profile["is_low_contrast_or_rain"])

        kept_4w: list[dict] = []
        kept_2w: list[dict] = []
        for target_list, pool in ((kept_4w, fused_4w), (kept_2w, fused_2w)):
            for item in pool:
                f_box = tuple(float(v) for v in item["xyxy"])
                if self._is_osd_text_box(f_box, osd_mask, img_h, is_night_or_glare=is_night_or_glare):
                    suppressed_static_count += 1
                    continue
                single_low = (item["n_families"] == 1) and (item["max_raw_conf"] < 0.55)
                in_roi_item = RoadRoiProvider.box_in_roi(f_box, roi_mask) if roi_mask is not None else False
                stats = self._compute_bg_and_motion_stats(
                    box=f_box,
                    gray_img=gray_img,
                    edge_img=edge_img,
                    gray_bg_active=gray_bg_active,
                    edge_bg_day=edge_bg_day,
                    edge_bg_night=edge_bg_night,
                    gray_prev=gray_prev,
                    edge_prev=edge_prev,
                    gray_next=gray_next,
                    edge_next=edge_next,
                    valid_mask=valid_mask,
                )
                if not self._passes_quality_and_glare_gates(
                    item=item,
                    box=f_box,
                    gray_img=gray_img,
                    edge_img=edge_img,
                    gray_bg_active=gray_bg_active,
                    stats=stats,
                    img_w=img_w,
                    img_h=img_h,
                    is_night_or_glare=is_night_or_glare,
                    is_low_contrast_or_rain=is_low_contrast_or_rain,
                    is_blurry=is_blurry,
                ):
                    suppressed_static_count += 1
                    continue
                if self._is_static_or_parked(
                    stats,
                    single_low_conf=single_low,
                    is_night_or_glare=is_night_or_glare,
                    in_roi=in_roi_item,
                    n_models=int(item["n_models"]),
                    n_families=int(item["n_families"]),
                ):
                    suppressed_static_count += 1
                    continue
                if item["conf"] >= conf:
                    target_list.append(item)

        # Recover giant close-up buses/trucks before suppressing interior/bumper/wheel sub-parts.
        pre_heavy_ids = {id(it) for it in kept_4w}
        consolidated_4w = self._consolidate_giant_heavy_vehicles(
            dynamic_candidates=dynamic_candidates,
            kept_4w=kept_4w,
            all_clusters=fused_4w + fused_2w,
            img_w=img_w,
            img_h=img_h,
            is_night_or_glare=is_night_or_glare,
        )
        kept_4w = []
        for it in consolidated_4w:
            if id(it) not in pre_heavy_ids:
                h_box = tuple(float(v) for v in it["xyxy"])
                h_stats = self._compute_bg_and_motion_stats(
                    box=h_box,
                    gray_img=gray_img,
                    edge_img=edge_img,
                    gray_bg_active=gray_bg_active,
                    edge_bg_day=edge_bg_day,
                    edge_bg_night=edge_bg_night,
                    gray_prev=gray_prev,
                    edge_prev=edge_prev,
                    gray_next=gray_next,
                    edge_next=edge_next,
                    valid_mask=valid_mask,
                )
                if self._is_static_or_parked(
                    h_stats,
                    single_low_conf=False,
                    is_night_or_glare=is_night_or_glare,
                    in_roi=True,
                    n_models=int(it["n_models"]),
                    n_families=int(it["n_families"]),
                ):
                    suppressed_static_count += 1
                    continue
            kept_4w.append(it)

        # Prune multi-child wrapper boxes, nested duplicates, and heavy-vehicle sub-part hallucinations.
        kept_4w = self._prune_4w_wrappers(kept_4w)
        kept_4w = self._prune_within_group_nested(kept_4w, is_4w=True)
        kept_2w = self._prune_within_group_nested(kept_2w, is_4w=False)
        kept_4w, kept_2w = self._suppress_heavy_vehicle_subparts(kept_4w, kept_2w)

        # Cross-group conflict resolution & nested sub-box suppression (4W vs 2W)
        final_items = self._resolve_cross_group_conflicts(kept_4w, kept_2w)

        # Stage 8: Camera Road ROI ground-contact filtering & active road occupancy/foreground metrics
        suppressed_roi_count = 0
        if roi_mask is not None:
            on_road_items: list[dict] = []
            for it in final_items:
                f_box = tuple(float(v) for v in it["xyxy"])
                if RoadRoiProvider.box_in_roi(f_box, roi_mask):
                    on_road_items.append(it)
                else:
                    suppressed_roi_count += 1
            final_items = on_road_items

        if gray_bg_active is not None:
            fg_diff_mask = cv2.absdiff(gray_img, gray_bg_active) > 25
            fg_region = ((roi_mask > 0) & valid_mask) if roi_mask is not None else valid_mask
            fg_denom = road_roi_area if roi_mask is not None else max(float(fg_region.sum()), 1.0)
            foreground_ratio = round(float((fg_diff_mask & fg_region).sum()) / max(fg_denom, 1.0), 4)
        else:
            foreground_ratio = 0.0

        final_items.sort(key=lambda it: it["conf"], reverse=True)

        if not final_items:
            return DetectionResult(
                boxes_xyxy=np.zeros((0, 4), dtype=np.float32),
                scores=np.zeros((0,), dtype=np.float32),
                class_ids=np.zeros((0,), dtype=np.int64),
                class_names=dict(CANONICAL_ID_TO_NAME),
                support_counts=np.zeros((0,), dtype=np.int64),
                suppressed_static_count=suppressed_static_count,
                optical_profile=optical_profile,
                counts={},
                suppressed_roi_count=suppressed_roi_count,
                road_roi_area=round(road_roi_area, 1),
                bbox_total_area=0.0,
                road_occupancy_ratio=0.0,
                foreground_ratio=foreground_ratio,
                roi_polygons_px=roi_polygons_px,
            )

        boxes_xyxy = np.stack([it["xyxy"] for it in final_items], axis=0).astype(np.float32)
        scores = np.array([it["conf"] for it in final_items], dtype=np.float32)
        class_ids = np.array([CANONICAL_NAME_TO_ID[it["cls_name"]] for it in final_items], dtype=np.int64)
        support_counts = np.array([it["n_models"] for it in final_items], dtype=np.int64)
        counts = dict(Counter(CANONICAL_ID_TO_NAME[int(cid)] for cid in class_ids))
        bbox_total_area = _compute_union_bbox_area(boxes_xyxy, img_w, img_h)
        road_occupancy_ratio = round(bbox_total_area / max(road_roi_area, 1.0), 4)

        return DetectionResult(
            boxes_xyxy=boxes_xyxy,
            scores=scores,
            class_ids=class_ids,
            class_names=dict(CANONICAL_ID_TO_NAME),
            support_counts=support_counts,
            suppressed_static_count=suppressed_static_count,
            optical_profile=optical_profile,
            counts=counts,
            suppressed_roi_count=suppressed_roi_count,
            road_roi_area=round(road_roi_area, 1),
            bbox_total_area=round(bbox_total_area, 1),
            road_occupancy_ratio=road_occupancy_ratio,
            foreground_ratio=foreground_ratio,
            roi_polygons_px=roi_polygons_px,
        )

    def predict(
        self,
        image_source: str | Path | np.ndarray,
        conf: float = 0.25,
        cam_id: int | None = None,
        hour: int | None = None,
        use_temporal_gate: bool = True,
        use_roi: bool | None = None,
    ) -> DetectionResult:
        """Run the full 7-stage ensemble detection pipeline on one image."""
        prep = self._prepare_frame(
            image_source=image_source,
            cam_id=cam_id,
            hour=hour,
            use_roi=use_roi,
        )
        img_w, img_h = prep["img_w"], prep["img_h"]
        all_vehicles: list[RawDetection] = []
        all_riders: list[RawDetection] = []
        for model_key, eff_raw_conf, model_crops in prep["routed_models"]:
            v_dets, r_dets = self._run_model_on_crops(
                model_key,
                model_crops,
                img_w,
                img_h,
                raw_conf_override=eff_raw_conf,
            )
            all_vehicles.extend(v_dets)
            all_riders.extend(r_dets)
        return self._finalize_frame_detections(
            prep=prep,
            all_vehicles=all_vehicles,
            all_riders=all_riders,
            conf=conf,
            use_temporal_gate=use_temporal_gate,
        )

    def predict_batch(
        self,
        image_sources: list[str | Path | np.ndarray],
        conf: float = 0.25,
        cam_ids: list[int | None] | None = None,
        hours: list[int | None] | None = None,
        use_temporal_gate: bool = True,
        use_roi: bool | None = None,
        yolo_batch: int = 64,
        num_workers: int = 8,
        return_images: bool = False,
    ) -> list[DetectionResult] | list[tuple[DetectionResult, np.ndarray]]:
        """Run the full pipeline across a batch of images with parallel CPU prep and batched GPU inference."""
        n = len(image_sources)
        if n == 0:
            return []

        self.scene_provider._ensure_manifest()
        cam_list = cam_ids if cam_ids is not None else [None] * n
        hour_list = hours if hours is not None else [None] * n

        def _prep_one(idx: int) -> dict:
            return self._prepare_frame(
                image_source=image_sources[idx],
                cam_id=cam_list[idx],
                hour=hour_list[idx],
                use_roi=use_roi,
            )

        if num_workers > 1 and n > 1:
            with ThreadPoolExecutor(max_workers=min(num_workers, n)) as pool:
                preps = list(pool.map(_prep_one, range(n)))
        else:
            preps = [_prep_one(i) for i in range(n)]

        frame_vehicles: list[list[RawDetection]] = [[] for _ in range(n)]
        frame_riders: list[list[RawDetection]] = [[] for _ in range(n)]

        # Bucket by (model_key, eff_raw_conf, (img_w, img_h)) and dispatch frame-aligned GPU chunks
        # so every GPU forward call sees complete frame crop sets and identical letterbox dimensions.
        buckets: dict[tuple[str, float, tuple[int, int]], list[tuple[int, list[tuple[str, str, tuple[int, int, int, int], np.ndarray]]]]] = defaultdict(list)
        for idx, prep in enumerate(preps):
            img_shape_wh = (prep["img_w"], prep["img_h"])
            for model_key, eff_raw_conf, model_crops in prep["routed_models"]:
                eff_conf = self.raw_conf if eff_raw_conf is None else float(eff_raw_conf)
                buckets[(model_key, eff_conf, img_shape_wh)].append((idx, model_crops))

        max_crops = max(1, int(yolo_batch))
        for (model_key, eff_conf, (img_w, img_h)), entries in buckets.items():
            model = self.models[model_key]
            chunk: list[tuple[int, list[tuple[str, str, tuple[int, int, int, int], np.ndarray]]]] = []
            chunk_count = 0

            def _flush_chunk(items_chunk: list[tuple[int, list[tuple[str, str, tuple[int, int, int, int], np.ndarray]]]]) -> None:
                if not items_chunk:
                    return
                flat_imgs = [crop[3] for _, crops in items_chunk for crop in crops]
                results = model.predict(
                    source=flat_imgs,
                    imgsz=self.imgsz,
                    conf=eff_conf,
                    iou=0.75,
                    max_det=500,
                    verbose=False,
                    **self._precision_kwargs,
                )
                offset = 0
                for frame_idx, f_crops in items_chunk:
                    cnt = len(f_crops)
                    v_dets, r_dets = self._parse_model_results(
                        model_key=model_key,
                        crop_items=f_crops,
                        results=results[offset : offset + cnt],
                        img_w=img_w,
                        img_h=img_h,
                    )
                    frame_vehicles[frame_idx].extend(v_dets)
                    frame_riders[frame_idx].extend(r_dets)
                    offset += cnt

            for entry in entries:
                f_len = len(entry[1])
                if chunk and (chunk_count + f_len) > max_crops:
                    _flush_chunk(chunk)
                    chunk = []
                    chunk_count = 0
                chunk.append(entry)
                chunk_count += f_len
            _flush_chunk(chunk)

        # Free crop arrays before post-processing.
        for prep in preps:
            prep["routed_models"] = []

        def _finish_one(idx: int) -> DetectionResult:
            return self._finalize_frame_detections(
                prep=preps[idx],
                all_vehicles=frame_vehicles[idx],
                all_riders=frame_riders[idx],
                conf=conf,
                use_temporal_gate=use_temporal_gate,
            )

        if num_workers > 1 and n > 1:
            with ThreadPoolExecutor(max_workers=min(num_workers, n)) as pool:
                det_results = list(pool.map(_finish_one, range(n)))
        else:
            det_results = [_finish_one(i) for i in range(n)]

        if return_images:
            return [(det_results[i], preps[i]["img_bgr"]) for i in range(n)]
        return det_results


def draw_detections(
    img_bgr: np.ndarray,
    result: DetectionResult,
    title: str | None = None,
    scale: float = 2.0,
    show_roi: bool = True,
) -> np.ndarray:
    """Render clean, legible color-coded bounding boxes, optional ROI overlay, and summary header."""
    h, w = img_bgr.shape[:2]
    if scale != 1.0:
        canvas = cv2.resize(img_bgr, (int(round(w * scale)), int(round(h * scale))), interpolation=cv2.INTER_LINEAR)
    else:
        canvas = img_bgr.copy()

    if show_roi and result.roi_polygons_px:
        roi_vis_mask = np.zeros((canvas.shape[0], canvas.shape[1]), dtype=np.uint8)
        scaled_polys: list[np.ndarray] = []
        for poly in result.roi_polygons_px:
            if len(poly) >= 3:
                pts = np.array([[int(round(px * scale)), int(round(py * scale))] for px, py in poly], dtype=np.int32)
                scaled_polys.append(pts)
                cv2.fillPoly(roi_vis_mask, [pts], 255)
        if scaled_polys:
            # Subtle 22% dimming outside active ROI keeps the road crisp while clearly showing exclusion zones.
            outside = roi_vis_mask == 0
            if outside.any():
                dimmed = (canvas.astype(np.float32) * 0.78).astype(np.uint8)
                canvas[outside] = dimmed[outside]
            cv2.polylines(canvas, scaled_polys, True, (80, 235, 160), 1, cv2.LINE_AA)

    # Draw bounding boxes first, then labels cleanly so labels remain readable.
    label_specs: list[tuple[int, int, str, tuple[int, int, int]]] = []
    for box, score, cid in zip(result.boxes_xyxy, result.scores, result.class_ids):
        cls_name = result.class_names.get(int(cid), str(cid))
        color = CLASS_COLORS_BGR.get(cls_name, (200, 200, 200))
        x1, y1, x2, y2 = (int(round(v * scale)) for v in box)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
        short = {
            "car": "car",
            "motorcycle": "moto",
            "bus": "bus",
            "truck": "trk",
        }.get(cls_name, cls_name)
        label_specs.append((x1, max(14, y1 - 3), f"{short} {score:.2f}", color))

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.42 if scale >= 1.5 else 0.35
    for lx, ly, text, color in label_specs:
        (tw, th), _ = cv2.getTextSize(text, font, font_scale, 1)
        bx1 = max(0, min(canvas.shape[1] - tw - 4, lx))
        by1 = max(th + 4, ly)
        cv2.rectangle(canvas, (bx1, by1 - th - 4), (bx1 + tw + 4, by1 + 2), color, -1)
        cv2.putText(canvas, text, (bx1 + 2, by1 - 2), font, font_scale, (15, 15, 15), 1, cv2.LINE_AA)

    # Top header banner with total count breakdown
    banner_h = 26
    out = np.zeros((canvas.shape[0] + banner_h, canvas.shape[1], 3), dtype=np.uint8)
    out[:banner_h, :] = (28, 28, 32)
    out[banner_h:, :] = canvas

    cnt = result.counts
    roi_tag = f" ROI:{result.suppressed_roi_count}" if result.roi_polygons_px else ""
    summary = (
        f"{title + ' | ' if title else ''}"
        f"Tot:{int(len(result.scores))} "
        f"[C:{cnt.get('car', 0)} M:{cnt.get('motorcycle', 0)} "
        f"B:{cnt.get('bus', 0)} T:{cnt.get('truck', 0)}] "
        f"Sup:{result.suppressed_static_count}{roi_tag}"
    )
    font_banner = 0.43 if scale < 1.8 else 0.46
    cv2.putText(out, summary, (8, 18), font, font_banner, (240, 240, 240), 1, cv2.LINE_AA)
    return out
