"""
Interactive Quick Click ROI Editor GUI (`03_cv_yolo_pipeline`).

Allows rapid manual inspection and editing of per-camera Road ROI polygons stored
in `data/camera_rois.json`:
  - Select ROI polygons by clicking directly on canvas or via the ROI selector list
  - Reshape polygons: drag vertices, drag midpoint `+` handles (or double-click edge)
    to insert vertices, or right-click a vertex to remove it
  - Add new ROI polygons: point-and-click polygon drawing (`N` key) + snap-to-close
  - Split one ROI into two: 2-click Knife Cut (`K` key) across a polygon
  - Delete selected ROI polygon (`Delete` key or button) with multi-step Undo (`Ctrl+Z`)
  - Peek at real daytime/rush-hour traffic frames (`V` key) underneath polygons to
    verify lane coverage, and save atomically back to `data/camera_rois.json`
    (preserving an automatic `data/camera_rois.auto_v3_backup.json` snapshot).

Usage:
    python 03_cv_yolo_pipeline/src/edit_camera_rois.py
    python 03_cv_yolo_pipeline/src/edit_camera_rois.py --cams 1815 411 301 112 1188
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageTk


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROIS_PATH = PROJECT_ROOT / "data" / "camera_rois.json"
DEFAULT_BG_DIR = PROJECT_ROOT / "data" / "median_backgrounds"
DEFAULT_CLEAN_DIR = PROJECT_ROOT / "Dataset_Clean_V1"
DEFAULT_MANIFEST_PATH = DEFAULT_CLEAN_DIR / "image_quality_manifest.parquet"
DEFAULT_PREVIEW_CAM_DIR = PROJECT_ROOT / "runs" / "detect" / "roi_previews" / "cams"

POLY_COLORS_BGR: tuple[tuple[int, int, int], ...] = (
    (0, 230, 120),   # green
    (255, 190, 0),   # cyan-blue
    (0, 170, 255),   # orange
    (230, 80, 240),  # magenta
    (80, 255, 255),  # yellow
    (255, 110, 120), # light blue
)

POLY_COLORS_HEX: tuple[str, ...] = (
    "#78e600",
    "#00beff",
    "#ffaa00",
    "#f050e6",
    "#ffff50",
    "#786eff",
)


def compute_mask_and_area(polygons_px: list[list[list[int]]], img_w: int, img_h: int) -> tuple[np.ndarray, int, float]:
    """Rasterize union road mask and return `(mask_uint8, road_area_px, road_area_ratio)`."""
    mask = np.zeros((img_h, img_w), dtype=np.uint8)
    for poly in polygons_px:
        if len(poly) >= 3:
            pts = np.array(poly, dtype=np.int32)
            cv2.fillPoly(mask, [pts], 255)
    area_px = int((mask > 0).sum())
    ratio = area_px / float(max(img_w * img_h, 1))
    return mask, area_px, round(ratio, 4)


def update_camera_entry_geometry(entry: dict, polygons_px: list[list[list[int]]], reviewed: bool) -> dict:
    """Recompute normalized coordinates and area metrics cleanly on a camera ROI dict."""
    w, h = int(entry["img_size"][0]), int(entry["img_size"][1])
    clean_polys: list[list[list[int]]] = []
    for poly in polygons_px:
        if len(poly) >= 3:
            clean_polys.append([[max(0, min(w - 1, int(round(x)))), max(0, min(h - 1, int(round(y))))] for x, y in poly])

    _, area_px, ratio = compute_mask_and_area(clean_polys, w, h)
    entry["polygons_px"] = clean_polys
    entry["polygons_norm"] = [[[round(x / float(w), 4), round(y / float(h), 4)] for x, y in p] for p in clean_polys]
    entry["num_polygons"] = len(clean_polys)
    entry["vertex_counts"] = [len(p) for p in clean_polys]
    entry["road_area_px"] = area_px
    entry["road_area_ratio"] = ratio
    entry["fallback"] = len(clean_polys) == 0
    entry["reviewed"] = bool(reviewed)
    return entry


def recompute_payload_summary(payload: dict) -> dict:
    """Update top-level dataset summary fields in `camera_rois.json` payload."""
    cams = payload["cameras"]
    n_polys = [int(v["num_polygons"]) for v in cams.values()]
    verts = [int(vc) for v in cams.values() for vc in v["vertex_counts"]]
    areas = [float(v["road_area_ratio"]) * 100.0 for v in cams.values()]
    payload["total_cameras"] = len(cams)
    payload["multi_road_cameras"] = sum(1 for v in cams.values() if int(v["num_polygons"]) >= 2)
    payload["fallback_cameras"] = sum(1 for v in cams.values() if bool(v.get("fallback")))
    payload["mean_road_area_pct"] = round(float(np.mean(areas)), 2) if areas else 0.0
    payload["median_polygons_per_cam"] = float(np.median(n_polys)) if n_polys else 0.0
    payload["median_vertices_per_polygon"] = float(np.median(verts)) if verts else 0.0
    payload["max_vertices_per_polygon"] = int(max(verts)) if verts else 0
    payload["reviewed_cameras"] = sum(1 for v in cams.values() if bool(v.get("reviewed")))
    return payload


def split_polygon_with_line(
    poly_px: list[list[int]],
    p1: tuple[float, float],
    p2: tuple[float, float],
    img_w: int,
    img_h: int,
) -> list[list[list[int]]]:
    """Slice one polygon along segment `(p1, p2)` into >= 2 simplified polygons if cut crosses cleanly."""
    if len(poly_px) < 3:
        return [poly_px]
    mask = np.zeros((img_h, img_w), dtype=np.uint8)
    cv2.fillPoly(mask, [np.array(poly_px, dtype=np.int32)], 255)
    # Draw crisp 3px cut extended well past both clicked endpoints so boundary edges open cleanly
    dx, dy = float(p2[0] - p1[0]), float(p2[1] - p1[1])
    norm = float(np.hypot(dx, dy))
    if norm < 4.0:
        return [poly_px]
    ux, uy = dx / norm, dy / norm
    ext = float(max(img_w, img_h))
    a = (int(round(p1[0] - ux * ext)), int(round(p1[1] - uy * ext)))
    b = (int(round(p2[0] + ux * ext)), int(round(p2[1] + uy * ext)))
    cv2.line(mask, a, b, 0, thickness=3)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    pieces: list[list[list[int]]] = []
    min_area = max(30.0, 0.0025 * img_w * img_h)
    for cnt in cnts:
        if cv2.contourArea(cnt) < min_area:
            continue
        peri = float(cv2.arcLength(cnt, True))
        eps_frac = 0.012
        approx = cv2.approxPolyDP(cnt, eps_frac * peri, True)
        while len(approx) > 14 and eps_frac < 0.045:
            eps_frac *= 1.18
            approx = cv2.approxPolyDP(cnt, eps_frac * peri, True)
        if len(approx) >= 3:
            pts = approx.reshape(-1, 2)
            pts[:, 0] = np.clip(pts[:, 0], 0, img_w - 1)
            pts[:, 1] = np.clip(pts[:, 1], 0, img_h - 1)
            pieces.append([[int(x), int(y)] for x, y in pts])
    if len(pieces) < 2:
        return [poly_px]
    pieces.sort(key=lambda p: (min(pt[0] for pt in p), min(pt[1] for pt in p)))
    return pieces


def point_to_segment_dist(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> tuple[float, float, float]:
    """Return `(dist, proj_x, proj_y)` from point `(px, py)` to segment `(a, b)`."""
    vx, vy = bx - ax, by - ay
    denom = vx * vx + vy * vy
    if denom <= 1e-6:
        return float(np.hypot(px - ax, py - ay)), ax, ay
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / denom))
    qx, qy = ax + t * vx, ay + t * vy
    return float(np.hypot(px - qx, py - qy)), qx, qy


def load_sample_traffic_frames(manifest_path: Path, clean_dir: Path, target_cids: set[int]) -> dict[int, list[Path]]:
    """Pre-index up to 4 clear daytime/rush-hour frame paths per camera for quick toggle inspection."""
    if not manifest_path.is_file():
        return {}
    df = pd.read_parquet(
        manifest_path,
        columns=["cam_id", "hour", "is_valid", "quality_warning", "brightness_mean", "clean_rel_path"],
    )
    df = df[df["is_valid"] & (df["quality_warning"] == "none") & df["cam_id"].isin(target_cids)].copy()
    if "brightness_mean" in df.columns:
        bright = df[df["brightness_mean"] >= 50.0]
        if len(bright) > 0:
            df = bright
    rush_hours = {7, 8, 9, 16, 17, 18}
    samples: dict[int, list[Path]] = {}
    for cid, sub in df.groupby("cam_id"):
        rush = sub[sub["hour"].isin(rush_hours)]
        pool = rush if len(rush) >= 4 else sub[sub["hour"].between(6, 18)]
        if pool.empty:
            pool = sub
        idxs = np.linspace(0, len(pool) - 1, min(4, len(pool)), dtype=int)
        paths = [clean_dir / str(rel) for rel in pool.iloc[idxs]["clean_rel_path"] if (clean_dir / str(rel)).is_file()]
        if paths:
            samples[int(cid)] = paths
    return samples


class QuickRoiEditorApp:
    """Interactive Tkinter + OpenCV Quick Click Road ROI Editor."""

    def __init__(
        self,
        root: tk.Tk,
        rois_path: Path,
        bg_dir: Path,
        clean_dir: Path,
        manifest_path: Path,
        filter_cams: list[int] | None = None,
        start_unreviewed: bool = False,
    ) -> None:
        self.root = root
        self.rois_path = rois_path
        self.backup_path = rois_path.with_name(f"{rois_path.stem}.auto_v3_backup{rois_path.suffix}")
        self.bg_dir = bg_dir
        self.clean_dir = clean_dir

        self.payload = json.loads(self.rois_path.read_text(encoding="utf-8"))
        self.cameras: dict[str, dict] = self.payload["cameras"]
        if self.backup_path.is_file():
            self.backup_cameras = json.loads(self.backup_path.read_text(encoding="utf-8")).get("cameras", {})
        else:
            self.backup_cameras = copy.deepcopy(self.cameras)

        all_cids = sorted((int(k) for k in self.cameras), key=int)
        if filter_cams:
            missing = [c for c in filter_cams if str(c) not in self.cameras]
            if missing:
                print(f"[warn] Camera IDs not found in JSON: {missing}")
            self.initial_cids = [c for c in filter_cams if str(c) in self.cameras] or all_cids
        else:
            self.initial_cids = all_cids

        self.sample_frames = load_sample_traffic_frames(manifest_path, clean_dir, set(all_cids))

        self.visible_cids: list[int] = list(self.initial_cids)
        self.current_cid: int = self.visible_cids[0]
        self.polygons: list[list[list[int]]] = []
        self.selected_poly_idx: int | None = None
        self.hover_vertex: tuple[int, int] | None = None
        self.hover_mid: tuple[int, int] | None = None
        self.undo_stack: list[tuple[list[list[list[int]]], int | None]] = []

        self.mode: str = "edit"  # "edit" | "add" | "split"
        self.drawing_pts: list[list[int]] = []
        self.split_pts: list[tuple[int, int]] = []
        self.cursor_img_xy: tuple[float, float] | None = None
        self.drag_state: dict | None = None
        self.view_idx: int = 0  # 0 = clean bg_day, 1..N = sample traffic frames
        self.dirty: bool = False

        self.base_bgr: np.ndarray | None = None
        self.tk_photo: ImageTk.PhotoImage | None = None
        self.canvas_w: int = 880
        self.canvas_h: int = 720
        self.scale_x: float = 2.5
        self.scale_y: float = 2.5

        self._setup_window_and_layout(start_unreviewed)
        self._apply_cam_filter()
        self._load_camera(self.current_cid)

    def _setup_window_and_layout(self, start_unreviewed: bool) -> None:
        self.root.title("Quick Click Road ROI Editor — BMA CCTV (Task 03)")
        self.root.configure(bg="#1b1e24")

        scr_h = self.root.winfo_screenheight()
        scr_w = self.root.winfo_screenwidth()
        # Size canvas comfortably inside Windows display DPI without clipping toolbars
        max_h = max(480, scr_h - 155)
        max_w = max(580, scr_w - 490)
        scale = min(max_w / 352.0, max_h / 288.0, 2.9)
        self.canvas_w = int(round(352 * scale))
        self.canvas_h = int(round(288 * scale))

        main = tk.Frame(self.root, bg="#1b1e24")
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # ---- Left Sidebar: Camera List & Filter ----
        left = tk.Frame(main, bg="#232730", width=220)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        left.pack_propagate(False)

        tk.Label(left, text="Cameras (100)", bg="#232730", fg="#e6edf3", font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=8, pady=(8, 4)
        )
        self.filter_var = tk.StringVar(value="unreviewed" if start_unreviewed else "all")
        filt_frame = tk.Frame(left, bg="#232730")
        filt_frame.pack(fill=tk.X, padx=6, pady=(0, 6))
        for val, lbl in [("all", "All"), ("unreviewed", "Unreviewed"), ("multi", "Multi-ROI")]:
            tk.Radiobutton(
                filt_frame,
                text=lbl,
                variable=self.filter_var,
                value=val,
                command=self._apply_cam_filter,
                bg="#232730",
                fg="#c9d1d9",
                selectcolor="#1b1e24",
                activebackground="#232730",
                activeforeground="#ffffff",
                font=("Segoe UI", 8),
            ).pack(side=tk.LEFT, padx=2)

        list_wrap = tk.Frame(left, bg="#232730")
        list_wrap.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        sb = tk.Scrollbar(list_wrap)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.cam_listbox = tk.Listbox(
            list_wrap,
            yscrollcommand=sb.set,
            bg="#161920",
            fg="#e6edf3",
            selectbackground="#2f6fed",
            selectforeground="#ffffff",
            font=("Consolas", 9),
            exportselection=False,
            bd=0,
            highlightthickness=0,
        )
        self.cam_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.cam_listbox.yview)
        self.cam_listbox.bind("<<ListboxSelect>>", self._on_cam_list_select)

        self.progress_lbl = tk.Label(left, text="Reviewed: 0/100", bg="#232730", fg="#8b949e", font=("Segoe UI", 8))
        self.progress_lbl.pack(anchor="w", padx=8, pady=(0, 6))

        # ---- Center: Top Action Bar + Interactive Canvas + Status Bar ----
        center = tk.Frame(main, bg="#1b1e24")
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        topbar = tk.Frame(center, bg="#232730", pady=5, padx=6)
        topbar.pack(fill=tk.X, pady=(0, 6))

        self.cam_title_lbl = tk.Label(
            topbar, text="Cam ---", bg="#232730", fg="#ffffff", font=("Segoe UI", 11, "bold")
        )
        self.cam_title_lbl.pack(side=tk.LEFT, padx=(4, 12))

        self.btn_mode_edit = tk.Button(
            topbar, text="Select / Reshape (E)", command=lambda: self.set_mode("edit"), width=17, relief=tk.FLAT
        )
        self.btn_mode_add = tk.Button(
            topbar, text="+ Add ROI (N)", command=lambda: self.set_mode("add"), width=13, relief=tk.FLAT
        )
        self.btn_mode_split = tk.Button(
            topbar, text="Knife Split (K)", command=lambda: self.set_mode("split"), width=13, relief=tk.FLAT
        )
        self.btn_del_roi = tk.Button(
            topbar,
            text="Delete ROI (Del)",
            command=self.delete_selected_polygon,
            bg="#8b2635",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=8,
        )
        self.btn_undo = tk.Button(
            topbar, text="Undo (Ctrl+Z)", command=self.undo, bg="#30363d", fg="#e6edf3", relief=tk.FLAT, padx=8
        )
        self.btn_view = tk.Button(
            topbar,
            text="View: Clean BG (V)",
            command=self.cycle_view_frame,
            bg="#2b4c7e",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=8,
        )
        for b in (self.btn_mode_edit, self.btn_mode_add, self.btn_mode_split, self.btn_del_roi, self.btn_undo, self.btn_view):
            b.pack(side=tk.LEFT, padx=3)

        self.canvas = tk.Canvas(
            center,
            width=self.canvas_w,
            height=self.canvas_h,
            bg="#0d1117",
            highlightthickness=1,
            highlightbackground="#3b4252",
            cursor="crosshair",
        )
        self.canvas.pack()

        botbar = tk.Frame(center, bg="#232730", pady=5, padx=8)
        botbar.pack(fill=tk.X, pady=(6, 0))
        self.status_lbl = tk.Label(
            botbar,
            text="Ready",
            bg="#232730",
            fg="#a5d6ff",
            font=("Segoe UI", 9),
            anchor="w",
        )
        self.status_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ---- Right Sidebar: Polygons in Camera, Nav & Save Controls, Cheatsheet ----
        right = tk.Frame(main, bg="#232730", width=230)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        right.pack_propagate(False)

        tk.Label(right, text="ROIs in Current Cam", bg="#232730", fg="#e6edf3", font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=10, pady=(8, 4)
        )
        self.roi_listbox = tk.Listbox(
            right,
            height=7,
            bg="#161920",
            fg="#e6edf3",
            selectbackground="#2f6fed",
            selectforeground="#ffffff",
            font=("Consolas", 9),
            exportselection=False,
            bd=0,
            highlightthickness=0,
        )
        self.roi_listbox.pack(fill=tk.X, padx=8, pady=(0, 6))
        self.roi_listbox.bind("<<ListboxSelect>>", self._on_roi_list_select)

        self.reviewed_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            right,
            text="Reviewed (verified)",
            variable=self.reviewed_var,
            command=self._on_toggle_reviewed,
            bg="#232730",
            fg="#c9d1d9",
            selectcolor="#1b1e24",
            activebackground="#232730",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=8, pady=(0, 4))

        self.autosave_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            right,
            text="Auto-save when switching cam",
            variable=self.autosave_var,
            bg="#232730",
            fg="#8b949e",
            selectcolor="#1b1e24",
            activebackground="#232730",
            activeforeground="#ffffff",
            font=("Segoe UI", 8),
        ).pack(anchor="w", padx=8, pady=(0, 8))

        nav_row = tk.Frame(right, bg="#232730")
        nav_row.pack(fill=tk.X, padx=8, pady=(0, 6))
        tk.Button(
            nav_row, text="← Prev (A)", command=self.prev_camera, bg="#30363d", fg="#ffffff", relief=tk.FLAT
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        tk.Button(
            nav_row, text="Next (D) →", command=self.next_camera, bg="#30363d", fg="#ffffff", relief=tk.FLAT
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))

        tk.Button(
            right,
            text="✓ Reviewed & Next (Space)",
            command=self.save_review_and_next,
            bg="#238636",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            pady=6,
        ).pack(fill=tk.X, padx=8, pady=(0, 6))

        tk.Button(
            right,
            text="Save JSON Now (S)",
            command=self.save_current_to_disk,
            bg="#1f6feb",
            fg="#ffffff",
            relief=tk.FLAT,
            pady=5,
        ).pack(fill=tk.X, padx=8, pady=(0, 6))

        tk.Button(
            right,
            text="Reset Cam to Auto V3",
            command=self.reset_camera_to_auto,
            bg="#443c2c",
            fg="#ffd580",
            relief=tk.FLAT,
            pady=4,
        ).pack(fill=tk.X, padx=8, pady=(0, 10))

        help_txt = (
            "Controls Cheat-Sheet:\n"
            "• Click inside ROI: Select\n"
            "• Drag circle: Move vertex\n"
            "• Drag '+' diamond: Add vertex\n"
            "• Double-click edge: Add vertex\n"
            "• Right-click vertex: Del vertex\n"
            "\n"
            "• N (+ Add ROI): Left-click pts,\n"
            "  Right-click / Enter / v1 = Close\n"
            "• K (Knife Split): Click 2 pts\n"
            "  across ROI to cut in half\n"
            "• Del: Delete selected ROI\n"
            "• V: Toggle Clean BG / Traffic\n"
            "• Space: Mark Reviewed & Next\n"
            "• Ctrl+Z: Undo | Esc: Cancel"
        )
        tk.Label(
            right,
            text=help_txt,
            justify=tk.LEFT,
            bg="#161920",
            fg="#adbac7",
            font=("Segoe UI", 8),
            padx=8,
            pady=8,
        ).pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Bind canvas mouse + keyboard events
        self.canvas.bind("<ButtonPress-1>", self._on_left_down)
        self.canvas.bind("<B1-Motion>", self._on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_up)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<ButtonPress-3>", self._on_right_down)
        self.canvas.bind("<Motion>", self._on_mouse_move)

        self.root.bind("<Control-z>", lambda _e: self.undo())
        self.root.bind("<Control-Z>", lambda _e: self.undo())
        self.root.bind("<Control-s>", lambda _e: self.save_current_to_disk())
        self.root.bind("<Control-S>", lambda _e: self.save_current_to_disk())
        self.root.bind("<Delete>", lambda _e: self.delete_selected_polygon())
        self.root.bind("<Return>", lambda _e: self._on_enter_key())
        self.root.bind("<Escape>", lambda _e: self._on_escape_key())
        self.root.bind("<BackSpace>", lambda _e: self._on_backspace_key())
        self.root.bind("<space>", lambda _e: self.save_review_and_next())
        self.root.bind("<Left>", lambda _e: self.prev_camera())
        self.root.bind("<Right>", lambda _e: self.next_camera())
        for ch, fn in [
            ("e", lambda: self.set_mode("edit")),
            ("n", lambda: self.set_mode("add")),
            ("k", lambda: self.set_mode("split")),
            ("v", self.cycle_view_frame),
            ("s", self.save_current_to_disk),
            ("a", self.prev_camera),
            ("d", self.next_camera),
        ]:
            self.root.bind(f"<{ch}>", lambda e, f=fn: None if (e.state & 0x4) else f())
            self.root.bind(f"<{ch.upper()}>", lambda e, f=fn: None if (e.state & 0x4) else f())

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._update_mode_buttons()

    def _apply_cam_filter(self) -> None:
        mode = self.filter_var.get()
        filtered: list[int] = []
        for cid in self.initial_cids:
            info = self.cameras[str(cid)]
            if mode == "unreviewed" and bool(info.get("reviewed")):
                continue
            if mode == "multi" and int(info.get("num_polygons", 0)) < 2:
                continue
            filtered.append(cid)
        if not filtered:
            filtered = list(self.initial_cids)
        self.visible_cids = filtered
        self._refresh_cam_listbox()
        if self.current_cid not in self.visible_cids and self.visible_cids:
            self._load_camera(self.visible_cids[0])

    def _refresh_cam_listbox(self) -> None:
        self.cam_listbox.delete(0, tk.END)
        sel_idx = None
        for idx, cid in enumerate(self.visible_cids):
            info = self.cameras[str(cid)]
            chk = "✓" if info.get("reviewed") else " "
            area = float(info.get("road_area_ratio", 0.0)) * 100.0
            n_p = int(info.get("num_polygons", 0))
            self.cam_listbox.insert(tk.END, f"[{chk}] {cid:>4} | {n_p}p {area:4.1f}%")
            if cid == self.current_cid:
                sel_idx = idx
        if sel_idx is not None:
            self.cam_listbox.selection_set(sel_idx)
            self.cam_listbox.see(sel_idx)
        rev_cnt = sum(1 for v in self.cameras.values() if bool(v.get("reviewed")))
        self.progress_lbl.config(text=f"Reviewed: {rev_cnt} / {len(self.cameras)}")

    def _on_cam_list_select(self, _evt: tk.Event) -> None:
        sel = self.cam_listbox.curselection()
        if not sel:
            return
        target_cid = self.visible_cids[int(sel[0])]
        if target_cid != self.current_cid:
            self._switch_camera(target_cid)

    def _on_roi_list_select(self, _evt: tk.Event) -> None:
        sel = self.roi_listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self.polygons):
            self.selected_poly_idx = idx
            self._render_canvas(full_composite=True)

    def _on_toggle_reviewed(self) -> None:
        self.cameras[str(self.current_cid)]["reviewed"] = bool(self.reviewed_var.get())
        self.dirty = True
        self._refresh_cam_listbox()

    def _load_camera(self, cid: int) -> None:
        self.current_cid = cid
        info = self.cameras[str(cid)]
        self.polygons = copy.deepcopy(info["polygons_px"])
        self.selected_poly_idx = 0 if self.polygons else None
        self.undo_stack.clear()
        self.drawing_pts.clear()
        self.split_pts.clear()
        self.drag_state = None
        self.hover_vertex = None
        self.hover_mid = None
        self.view_idx = 0
        self.set_mode("edit")

        img_w, img_h = int(info["img_size"][0]), int(info["img_size"][1])
        self.scale_x = self.canvas_w / float(img_w)
        self.scale_y = self.canvas_h / float(img_h)

        self._load_active_background_image()
        self.reviewed_var.set(bool(info.get("reviewed", False)))
        self._refresh_roi_listbox()
        self._refresh_cam_listbox()
        self._update_header_and_status()
        self._render_canvas(full_composite=True)
        self.canvas.focus_set()

    def _load_active_background_image(self) -> None:
        info = self.cameras[str(self.current_cid)]
        img_w, img_h = int(info["img_size"][0]), int(info["img_size"][1])
        frames = self.sample_frames.get(self.current_cid, [])
        if self.view_idx == 0 or self.view_idx > len(frames):
            self.view_idx = 0
            bg_p = self.bg_dir / f"{self.current_cid}_bg.jpg"
            im = cv2.imread(str(bg_p)) if bg_p.is_file() else None
            if im is None and frames:
                im = cv2.imread(str(frames[0]))
            self.btn_view.config(text="View: Clean BG (V)")
        else:
            im = cv2.imread(str(frames[self.view_idx - 1]))
            self.btn_view.config(text=f"View: Traffic #{self.view_idx} (V)")
        if im is None:
            im = np.full((img_h, img_w, 3), 40, dtype=np.uint8)
        elif im.shape[1] != img_w or im.shape[0] != img_h:
            im = cv2.resize(im, (img_w, img_h))
        self.base_bgr = im

    def cycle_view_frame(self) -> None:
        frames = self.sample_frames.get(self.current_cid, [])
        self.view_idx = (self.view_idx + 1) % (len(frames) + 1)
        self._load_active_background_image()
        self._render_canvas(full_composite=True)

    def _switch_camera(self, target_cid: int) -> None:
        self._commit_current_to_memory()
        if self.dirty and self.autosave_var.get():
            self._write_json_to_disk(refresh_preview_cids={self.current_cid})
        self._load_camera(target_cid)

    def prev_camera(self) -> None:
        if not self.visible_cids:
            return
        idx = self.visible_cids.index(self.current_cid) if self.current_cid in self.visible_cids else 0
        self._switch_camera(self.visible_cids[(idx - 1) % len(self.visible_cids)])

    def next_camera(self) -> None:
        if not self.visible_cids:
            return
        idx = self.visible_cids.index(self.current_cid) if self.current_cid in self.visible_cids else 0
        self._switch_camera(self.visible_cids[(idx + 1) % len(self.visible_cids)])

    def save_review_and_next(self) -> None:
        self.reviewed_var.set(True)
        self._commit_current_to_memory(force_reviewed=True)
        self._write_json_to_disk(refresh_preview_cids={self.current_cid})
        if self.filter_var.get() == "unreviewed":
            self._apply_cam_filter()
            if self.visible_cids:
                self._load_camera(self.visible_cids[0])
            return
        self.next_camera()

    def save_current_to_disk(self) -> None:
        self._commit_current_to_memory()
        self._write_json_to_disk(refresh_preview_cids={self.current_cid})
        self._refresh_cam_listbox()
        self._update_header_and_status(msg=f"Saved Cam {self.current_cid} to {self.rois_path.name}")

    def _commit_current_to_memory(self, force_reviewed: bool | None = None) -> None:
        entry = self.cameras[str(self.current_cid)]
        rev = force_reviewed if force_reviewed is not None else bool(self.reviewed_var.get())
        if entry["polygons_px"] != self.polygons or bool(entry.get("reviewed")) != rev:
            self.dirty = True
        update_camera_entry_geometry(entry, self.polygons, reviewed=rev)

    def _write_json_to_disk(self, refresh_preview_cids: set[int] | None = None) -> None:
        if not self.backup_path.is_file() and self.rois_path.is_file():
            shutil.copy2(self.rois_path, self.backup_path)
        recompute_payload_summary(self.payload)
        tmp_path = self.rois_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(self.payload, indent=2), encoding="utf-8")
        tmp_path.replace(self.rois_path)
        self.dirty = False

        if refresh_preview_cids and self.rois_path.resolve() == DEFAULT_ROIS_PATH.resolve() and DEFAULT_PREVIEW_CAM_DIR.is_dir():
            for cid in refresh_preview_cids:
                self._save_updated_cam_preview(cid)

    def _save_updated_cam_preview(self, cid: int) -> None:
        info = self.cameras.get(str(cid))
        if info is None:
            return
        bg = cv2.imread(str(self.bg_dir / f"{cid}_bg.jpg"))
        if bg is None:
            return
        h, w = bg.shape[:2]
        roi_vis = bg.copy()
        ov = roi_vis.copy()
        for i, poly in enumerate(info["polygons_px"]):
            cv2.fillPoly(ov, [np.array(poly, dtype=np.int32)], POLY_COLORS_BGR[i % len(POLY_COLORS_BGR)])
        roi_vis = cv2.addWeighted(ov, 0.30, roi_vis, 0.70, 0)
        for i, poly in enumerate(info["polygons_px"]):
            col = POLY_COLORS_BGR[i % len(POLY_COLORS_BGR)]
            cv2.polylines(roi_vis, [np.array(poly, dtype=np.int32)], True, col, 2)
            for x, y in poly:
                cv2.circle(roi_vis, (x, y), 3, (255, 255, 255), -1)
                cv2.circle(roi_vis, (x, y), 2, col, -1)
            cx, cy = int(np.mean([p[0] for p in poly])), int(np.mean([p[1] for p in poly]))
            tag = f"R{i+1}({len(poly)}v)"
            cv2.putText(roi_vis, tag, (max(4, cx - 22), max(14, cy)), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 2)
            cv2.putText(roi_vis, tag, (max(4, cx - 22), max(14, cy)), cv2.FONT_HERSHEY_SIMPLEX, 0.40, col, 1)

        cam_prev = DEFAULT_PREVIEW_CAM_DIR / f"cam_{cid:04d}_roi.jpg"
        if cam_prev.is_file():
            old = cv2.imread(str(cam_prev))
            if old is not None and old.shape[1] == w * 6 and old.shape[0] == (h + 24) * 2:
                # Replace rightmost ROI panel cleanly while keeping bg & heatmap panels intact
                roi_2x = cv2.resize(roi_vis, (w * 2, h * 2), interpolation=cv2.INTER_LINEAR)
                old[48 : 48 + h * 2, w * 4 : w * 6] = roi_2x
                old[:48, :] = 24
                cv2.putText(
                    old,
                    f"Cam {cid} | EDITED | ROIs={info['num_polygons']} | area={info['road_area_ratio']*100:.1f}%",
                    (16, 34),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (180, 255, 180),
                    2,
                )
                cv2.imwrite(str(cam_prev), old)

    def _push_undo(self) -> None:
        self.undo_stack.append((copy.deepcopy(self.polygons), self.selected_poly_idx))
        if len(self.undo_stack) > 35:
            self.undo_stack.pop(0)

    def undo(self) -> None:
        if self.mode == "add" and self.drawing_pts:
            self.drawing_pts.pop()
            self._render_canvas(full_composite=False)
            return
        if not self.undo_stack:
            self._update_header_and_status(msg="Nothing to undo for this camera")
            return
        self.polygons, self.selected_poly_idx = self.undo_stack.pop()
        self._commit_current_to_memory()
        self._refresh_roi_listbox()
        self._update_header_and_status(msg="Undid last ROI edit")
        self._render_canvas(full_composite=True)

    def reset_camera_to_auto(self) -> None:
        orig = self.backup_cameras.get(str(self.current_cid))
        if orig is None:
            return
        self._push_undo()
        self.polygons = copy.deepcopy(orig["polygons_px"])
        self.selected_poly_idx = 0 if self.polygons else None
        self.reviewed_var.set(False)
        self._commit_current_to_memory(force_reviewed=False)
        self._refresh_roi_listbox()
        self._refresh_cam_listbox()
        self._update_header_and_status(msg=f"Reset Cam {self.current_cid} to Auto V3 baseline")
        self._render_canvas(full_composite=True)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        if mode != "add":
            self.drawing_pts.clear()
        if mode != "split":
            self.split_pts.clear()
        self._update_mode_buttons()
        self._update_header_and_status()
        self._render_canvas(full_composite=False)

    def _update_mode_buttons(self) -> None:
        styles = {
            "edit": self.btn_mode_edit,
            "add": self.btn_mode_add,
            "split": self.btn_mode_split,
        }
        for k, btn in styles.items():
            if self.mode == k:
                btn.config(bg="#238636" if k == "add" else ("#d29922" if k == "split" else "#1f6feb"), fg="#ffffff")
            else:
                btn.config(bg="#30363d", fg="#c9d1d9")

    def delete_selected_polygon(self) -> None:
        if self.selected_poly_idx is None or not (0 <= self.selected_poly_idx < len(self.polygons)):
            return
        self._push_undo()
        removed_i = self.selected_poly_idx + 1
        self.polygons.pop(self.selected_poly_idx)
        self.selected_poly_idx = min(self.selected_poly_idx, len(self.polygons) - 1) if self.polygons else None
        self._commit_current_to_memory()
        self._refresh_roi_listbox()
        self._refresh_cam_listbox()
        self._update_header_and_status(msg=f"Deleted R{removed_i} (Ctrl+Z to undo)")
        self._render_canvas(full_composite=True)

    def _refresh_roi_listbox(self) -> None:
        self.roi_listbox.delete(0, tk.END)
        for i, poly in enumerate(self.polygons):
            self.roi_listbox.insert(tk.END, f"R{i+1} | {len(poly):2d} vertices")
        if self.selected_poly_idx is not None and 0 <= self.selected_poly_idx < len(self.polygons):
            self.roi_listbox.selection_set(self.selected_poly_idx)

    def _update_header_and_status(self, msg: str | None = None) -> None:
        info = self.cameras[str(self.current_cid)]
        w, h = int(info["img_size"][0]), int(info["img_size"][1])
        _, _, ratio = compute_mask_and_area(self.polygons, w, h)
        self.cam_title_lbl.config(
            text=f"Cam {self.current_cid}  |  ROIs: {len(self.polygons)}  |  Area: {ratio*100:.1f}%"
        )
        if msg is None:
            if self.mode == "add":
                msg = "ADD MODE: Left-click around road; Right-click / Enter / click v1 to finish; Esc to cancel"
            elif self.mode == "split":
                msg = (
                    "KNIFE SPLIT: Click 2 pts along the cut line to slice selected ROI in 2"
                    if not self.split_pts
                    else "KNIFE SPLIT: Click point #2 across the cut line to slice ROI in 2"
                )
            else:
                msg = "EDIT MODE: Drag circle=move vertex | Drag '+'=insert vertex | Right-click vertex=delete | Click ROI=select"
        self.status_lbl.config(text=msg)

    # ---- Coordinate Helpers ----
    def _c2i(self, cx: float, cy: float) -> tuple[float, float]:
        info = self.cameras[str(self.current_cid)]
        w, h = int(info["img_size"][0]), int(info["img_size"][1])
        return (
            max(0.0, min(float(w - 1), cx / self.scale_x)),
            max(0.0, min(float(h - 1), cy / self.scale_y)),
        )

    def _i2c(self, ix: float, iy: float) -> tuple[float, float]:
        return ix * self.scale_x, iy * self.scale_y

    def _hit_vertex(self, cx: float, cy: float, radius: float = 11.0) -> tuple[int, int] | None:
        order = ([self.selected_poly_idx] if self.selected_poly_idx is not None else []) + [
            i for i in range(len(self.polygons)) if i != self.selected_poly_idx
        ]
        best: tuple[float, tuple[int, int]] | None = None
        for pi in order:
            for vi, (vx, vy) in enumerate(self.polygons[pi]):
                sx, sy = self._i2c(vx, vy)
                d = float(np.hypot(cx - sx, cy - sy))
                if d <= radius and (best is None or d < best[0]):
                    best = (d, (pi, vi))
        return best[1] if best is not None else None

    def _hit_midpoint(self, cx: float, cy: float, radius: float = 10.0) -> tuple[int, int] | None:
        if self.selected_poly_idx is None or not (0 <= self.selected_poly_idx < len(self.polygons)):
            return None
        poly = self.polygons[self.selected_poly_idx]
        n = len(poly)
        if n < 3:
            return None
        best: tuple[float, int] | None = None
        for vi in range(n):
            ax, ay = self._i2c(*poly[vi])
            bx, by = self._i2c(*poly[(vi + 1) % n])
            mx, my = 0.5 * (ax + bx), 0.5 * (ay + by)
            d = float(np.hypot(cx - mx, cy - my))
            if d <= radius and (best is None or d < best[0]):
                best = (d, vi)
        return (self.selected_poly_idx, best[1]) if best is not None else None

    def _hit_edge(self, cx: float, cy: float, radius: float = 9.0) -> tuple[int, int, int, int] | None:
        if self.selected_poly_idx is None or not (0 <= self.selected_poly_idx < len(self.polygons)):
            return None
        poly = self.polygons[self.selected_poly_idx]
        n = len(poly)
        best: tuple[float, int, float, float] | None = None
        for vi in range(n):
            ax, ay = self._i2c(*poly[vi])
            bx, by = self._i2c(*poly[(vi + 1) % n])
            d, qx, qy = point_to_segment_dist(cx, cy, ax, ay, bx, by)
            if d <= radius and (best is None or d < best[0]):
                best = (d, vi, qx, qy)
        if best is None:
            return None
        ix, iy = self._c2i(best[2], best[3])
        return self.selected_poly_idx, best[1], int(round(ix)), int(round(iy))

    def _hit_polygon_interior(self, ix: float, iy: float) -> int | None:
        # Prefer non-selected smaller polygons if overlapping, or cycle cleanly
        hits = []
        for pi, poly in enumerate(self.polygons):
            if len(poly) >= 3:
                arr = np.array(poly, dtype=np.int32)
                if cv2.pointPolygonTest(arr, (float(ix), float(iy)), False) >= 0:
                    hits.append((cv2.contourArea(arr), pi))
        if not hits:
            return None
        hits.sort()
        return hits[0][1]

    # ---- Mouse & Keyboard Event Handlers ----
    def _on_left_down(self, evt: tk.Event) -> None:
        self.canvas.focus_set()
        cx, cy = float(evt.x), float(evt.y)
        ix, iy = self._c2i(cx, cy)

        if self.mode == "add":
            if len(self.drawing_pts) >= 3:
                sx, sy = self._i2c(*self.drawing_pts[0])
                if np.hypot(cx - sx, cy - sy) <= 13.0:
                    self._finish_add_polygon()
                    return
            self.drawing_pts.append([int(round(ix)), int(round(iy))])
            self._render_canvas(full_composite=False)
            return

        if self.mode == "split":
            pt = (int(round(ix)), int(round(iy)))
            if not self.split_pts:
                self.split_pts.append(pt)
                self._update_header_and_status()
                self._render_canvas(full_composite=False)
            else:
                self._execute_knife_split(self.split_pts[0], pt)
            return

        # Mode == "edit": check vertex -> midpoint '+' -> polygon body
        vhit = self._hit_vertex(cx, cy)
        if vhit is not None:
            self._push_undo()
            pi, vi = vhit
            self.selected_poly_idx = pi
            self._refresh_roi_listbox()
            self.drag_state = {"kind": "vertex", "poly_idx": pi, "vert_idx": vi}
            return

        mhit = self._hit_midpoint(cx, cy)
        if mhit is not None:
            self._push_undo()
            pi, ei = mhit
            new_pt = [int(round(ix)), int(round(iy))]
            self.polygons[pi].insert(ei + 1, new_pt)
            self.drag_state = {"kind": "vertex", "poly_idx": pi, "vert_idx": ei + 1}
            self._refresh_roi_listbox()
            self._render_canvas(full_composite=False)
            return

        phit = self._hit_polygon_interior(ix, iy)
        if phit is not None:
            self.selected_poly_idx = phit
            self._refresh_roi_listbox()
            self._render_canvas(full_composite=True)

    def _on_left_drag(self, evt: tk.Event) -> None:
        if self.drag_state is None:
            return
        ix, iy = self._c2i(float(evt.x), float(evt.y))
        pi, vi = self.drag_state["poly_idx"], self.drag_state["vert_idx"]
        self.polygons[pi][vi] = [int(round(ix)), int(round(iy))]
        self._render_canvas(full_composite=False)

    def _on_left_up(self, _evt: tk.Event) -> None:
        if self.drag_state is not None:
            self.drag_state = None
            if self.undo_stack and self.undo_stack[-1][0] == self.polygons:
                self.undo_stack.pop()
            self._commit_current_to_memory()
            self._refresh_roi_listbox()
            self._refresh_cam_listbox()
            self._update_header_and_status()
            self._render_canvas(full_composite=True)

    def _on_double_click(self, evt: tk.Event) -> None:
        if self.mode == "add":
            if len(self.drawing_pts) >= 3:
                self._finish_add_polygon()
            return
        if self.mode == "edit":
            ehit = self._hit_edge(float(evt.x), float(evt.y))
            if ehit is not None:
                self._push_undo()
                pi, ei, nx, ny = ehit
                self.polygons[pi].insert(ei + 1, [nx, ny])
                self._commit_current_to_memory()
                self._refresh_roi_listbox()
                self._render_canvas(full_composite=True)

    def _on_right_down(self, evt: tk.Event) -> None:
        cx, cy = float(evt.x), float(evt.y)
        if self.mode == "add":
            if len(self.drawing_pts) >= 3:
                self._finish_add_polygon()
            else:
                self.set_mode("edit")
            return
        if self.mode == "split":
            self.set_mode("edit")
            return
        vhit = self._hit_vertex(cx, cy)
        if vhit is not None:
            pi, vi = vhit
            if len(self.polygons[pi]) <= 3:
                self._update_header_and_status(msg="Polygon needs >= 3 vertices (use Del key to remove entire ROI)")
                return
            self._push_undo()
            self.selected_poly_idx = pi
            self.polygons[pi].pop(vi)
            self._commit_current_to_memory()
            self._refresh_roi_listbox()
            self._refresh_cam_listbox()
            self._update_header_and_status(msg=f"Removed vertex from R{pi+1}")
            self._render_canvas(full_composite=True)

    def _on_mouse_move(self, evt: tk.Event) -> None:
        cx, cy = float(evt.x), float(evt.y)
        self.cursor_img_xy = self._c2i(cx, cy)
        if self.mode in ("add", "split"):
            self._render_canvas(full_composite=False)
            return
        if self.drag_state is not None:
            return
        old_hv, old_hm = self.hover_vertex, self.hover_mid
        self.hover_vertex = self._hit_vertex(cx, cy)
        self.hover_mid = None if self.hover_vertex is not None else self._hit_midpoint(cx, cy)
        if old_hv != self.hover_vertex or old_hm != self.hover_mid:
            self._render_canvas(full_composite=False)

    def _finish_add_polygon(self) -> None:
        if len(self.drawing_pts) < 3:
            self.set_mode("edit")
            return
        self._push_undo()
        self.polygons.append(list(self.drawing_pts))
        self.selected_poly_idx = len(self.polygons) - 1
        self.drawing_pts.clear()
        self.mode = "edit"
        self._update_mode_buttons()
        self._commit_current_to_memory()
        self._refresh_roi_listbox()
        self._refresh_cam_listbox()
        self._update_header_and_status(msg=f"Added new R{len(self.polygons)}")
        self._render_canvas(full_composite=True)

    def _execute_knife_split(self, p1: tuple[int, int], p2: tuple[int, int]) -> None:
        info = self.cameras[str(self.current_cid)]
        w, h = int(info["img_size"][0]), int(info["img_size"][1])
        target_idx = self.selected_poly_idx
        if target_idx is None or not (0 <= target_idx < len(self.polygons)):
            target_idx = 0 if len(self.polygons) == 1 else None
        if target_idx is None:
            self._update_header_and_status(msg="Select a polygon first before Knife Split")
            self.set_mode("edit")
            return
        pieces = split_polygon_with_line(self.polygons[target_idx], p1, p2, w, h)
        if len(pieces) < 2:
            self.split_pts.clear()
            self.set_mode("edit")
            self._update_header_and_status(msg="Cut line did not split ROI across two sides — no change")
            return
        self._push_undo()
        self.polygons[target_idx : target_idx + 1] = pieces
        self.selected_poly_idx = target_idx
        self.split_pts.clear()
        self.mode = "edit"
        self._update_mode_buttons()
        self._commit_current_to_memory()
        self._refresh_roi_listbox()
        self._refresh_cam_listbox()
        self._update_header_and_status(msg=f"Split ROI into {len(pieces)} polygons")
        self._render_canvas(full_composite=True)

    def _on_enter_key(self) -> None:
        if self.mode == "add" and len(self.drawing_pts) >= 3:
            self._finish_add_polygon()

    def _on_escape_key(self) -> None:
        if self.mode in ("add", "split"):
            self.set_mode("edit")

    def _on_backspace_key(self) -> None:
        if self.mode == "add" and self.drawing_pts:
            self.drawing_pts.pop()
            self._render_canvas(full_composite=False)

    def _on_close(self) -> None:
        self._commit_current_to_memory()
        if self.dirty:
            if self.autosave_var.get():
                self._write_json_to_disk(refresh_preview_cids={self.current_cid})
            else:
                ans = messagebox.askyesnocancel("Save ROI Edits?", "Save changes to data/camera_rois.json before closing?")
                if ans is None:
                    return
                if ans:
                    self._write_json_to_disk(refresh_preview_cids={self.current_cid})
        self.root.destroy()

    # ---- Canvas Rendering ----
    def _render_canvas(self, full_composite: bool = True) -> None:
        if self.base_bgr is None:
            return
        if full_composite or self.tk_photo is None:
            vis = self.base_bgr.copy()
            ov = vis.copy()
            for i, poly in enumerate(self.polygons):
                if len(poly) >= 3:
                    col = POLY_COLORS_BGR[i % len(POLY_COLORS_BGR)]
                    cv2.fillPoly(ov, [np.array(poly, dtype=np.int32)], col)
            # While dragging, skip fill composite on non-final ticks; on full composite show smooth alpha!
            alpha = 0.28
            vis = cv2.addWeighted(ov, alpha, vis, 1.0 - alpha, 0)
            rgb = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)
            pil_im = Image.fromarray(rgb).resize((self.canvas_w, self.canvas_h), Image.Resampling.BILINEAR)
            self.tk_photo = ImageTk.PhotoImage(pil_im)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_photo)

        # Crisp vector borders, labels, vertices, and midpoint '+' handles
        for i, poly in enumerate(self.polygons):
            if len(poly) < 3:
                continue
            hex_col = POLY_COLORS_HEX[i % len(POLY_COLORS_HEX)]
            is_sel = i == self.selected_poly_idx
            flat_pts: list[float] = []
            c_pts: list[tuple[float, float]] = []
            for vx, vy in poly:
                sx, sy = self._i2c(vx, vy)
                flat_pts.extend([sx, sy])
                c_pts.append((sx, sy))
            self.canvas.create_polygon(
                flat_pts,
                outline="#ffffff" if is_sel else hex_col,
                width=3 if is_sel else 2,
                fill="",
            )
            if is_sel:
                self.canvas.create_polygon(flat_pts, outline=hex_col, width=1, dash=(6, 4), fill="")

            cx = sum(p[0] for p in c_pts) / len(c_pts)
            cy = sum(p[1] for p in c_pts) / len(c_pts)
            self.canvas.create_text(cx + 1, cy + 1, text=f"R{i+1} ({len(poly)}v)", fill="#000000", font=("Segoe UI", 10, "bold"))
            self.canvas.create_text(cx, cy, text=f"R{i+1} ({len(poly)}v)", fill="#ffffff" if is_sel else hex_col, font=("Segoe UI", 10, "bold"))

            if is_sel:
                n = len(c_pts)
                for vi in range(n):
                    ax, ay = c_pts[vi]
                    bx, by = c_pts[(vi + 1) % n]
                    mx, my = 0.5 * (ax + bx), 0.5 * (ay + by)
                    m_hov = self.hover_mid == (i, vi)
                    mr = 5 if m_hov else 3.5
                    self.canvas.create_rectangle(
                        mx - mr,
                        my - mr,
                        mx + mr,
                        my + mr,
                        fill="#ffd580" if m_hov else "#232730",
                        outline="#ffffff",
                        width=1,
                    )
                for vi, (vx, vy) in enumerate(c_pts):
                    v_hov = self.hover_vertex == (i, vi)
                    r = 7 if v_hov else 5
                    self.canvas.create_oval(
                        vx - r,
                        vy - r,
                        vx + r,
                        vy + r,
                        fill="#ff4444" if v_hov else hex_col,
                        outline="#ffffff",
                        width=2,
                    )
            else:
                for vx, vy in c_pts:
                    self.canvas.create_oval(vx - 3, vy - 3, vx + 3, vy + 3, fill=hex_col, outline="#ffffff", width=1)

        # In-progress Add Polygon stroke + rubber band
        if self.mode == "add" and self.drawing_pts:
            d_pts = [self._i2c(x, y) for x, y in self.drawing_pts]
            if len(d_pts) >= 2:
                self.canvas.create_line([c for p in d_pts for c in p], fill="#50ff78", width=2)
            if self.cursor_img_xy is not None:
                cx, cy = self._i2c(*self.cursor_img_xy)
                self.canvas.create_line(d_pts[-1][0], d_pts[-1][1], cx, cy, fill="#a5d6ff", width=2, dash=(4, 4))
            for idx, (px, py) in enumerate(d_pts):
                r = 7 if idx == 0 and len(d_pts) >= 3 else 4.5
                self.canvas.create_oval(
                    px - r, py - r, px + r, py + r, fill="#ffff50" if idx == 0 else "#50ff78", outline="#000000", width=1.5
                )

        # In-progress Knife Split preview line
        if self.mode == "split" and self.split_pts and self.cursor_img_xy is not None:
            ax, ay = self._i2c(*self.split_pts[0])
            bx, by = self._i2c(*self.cursor_img_xy)
            self.canvas.create_line(ax, ay, bx, by, fill="#ff5555", width=2, dash=(6, 4))
            self.canvas.create_oval(ax - 5, ay - 5, ax + 5, ay + 5, fill="#ff5555", outline="#ffffff", width=1.5)


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive Quick Click Road ROI Editor GUI")
    parser.add_argument("--rois", type=Path, default=DEFAULT_ROIS_PATH)
    parser.add_argument("--bg-dir", type=Path, default=DEFAULT_BG_DIR)
    parser.add_argument("--clean-dir", type=Path, default=DEFAULT_CLEAN_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--cams", type=int, nargs="*", default=None, help="Optional subset of camera IDs to edit")
    parser.add_argument("--unreviewed", action="store_true", help="Start with unreviewed cameras filter active")
    args = parser.parse_args()

    if not args.rois.is_file():
        raise FileNotFoundError(f"ROI file not found: {args.rois}")

    root = tk.Tk()
    QuickRoiEditorApp(
        root=root,
        rois_path=args.rois,
        bg_dir=args.bg_dir,
        clean_dir=args.clean_dir,
        manifest_path=args.manifest,
        filter_cams=args.cams,
        start_unreviewed=args.unreviewed,
    )
    root.mainloop()


if __name__ == "__main__":
    main()
