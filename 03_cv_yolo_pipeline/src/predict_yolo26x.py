"""
Run YOLO object detection on a user-selected image with switchable models,
class-remapped NMS (safe 4-wheeler grouping), optional agnostic NMS, and SAHI tiling.

Supported model presets (--model):
    - yolo26x.pt (default, COCO pretrained)
    - dronefreak/visdrone-yolo11x
    - dronefreak/visdrone-yolo26l
    - iisc-aim/UVH-26 (YOLOv11-X; or iisc-aim/UVH-26-s for lightweight YOLOv11-S)

Usage:
    python 03_cv_yolo_pipeline/src/predict_yolo26x.py
    python 03_cv_yolo_pipeline/src/predict_yolo26x.py Dataset_Clean_V1/cctv_images/26/26_20260825_074041.jpg --model iisc-aim/UVH-26
    python 03_cv_yolo_pipeline/src/predict_yolo26x.py Dataset_Clean_V1/cctv_images/26/26_20260825_074041.jpg --model iisc-aim/UVH-26 --sahi
    python 03_cv_yolo_pipeline/src/predict_yolo26x.py Dataset_Clean_V1/cctv_images/26/26_20260825_074041.jpg --model iisc-aim/UVH-26 --imgsz 1280
    python 03_cv_yolo_pipeline/src/predict_yolo26x.py Dataset_Clean_V1/cctv_images/26/26_20260825_074041.jpg --model iisc-aim/UVH-26 --agnostic-nms
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, ttk
import urllib.request

import cv2
import torch
import torchvision


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IMAGE_DIR = PROJECT_ROOT / "Dataset_Clean_V1" / "cctv_images"
MODELS_CACHE_DIR = PROJECT_ROOT / "models"

# Default settings when omitted on CLI.
DEFAULT_MODEL = "yolo26x.pt"
DEFAULT_NMS_MODE = "grouped"
DEFAULT_IMGSZ = 640
DEFAULT_CONF = 0.25
DEFAULT_IOU = 0.50


@dataclass(frozen=True)
class HFModelSpec:
    repo_id: str
    filename: str
    description: str


MODEL_PRESETS: dict[str, HFModelSpec] = {
    "dronefreak/visdrone-yolo11x": HFModelSpec(
        repo_id="dronefreak/visdrone-yolo11x",
        filename="best.pt",
        description="VisDrone aerial dataset fine-tuned YOLOv11-X",
    ),
    "dronefreak/visdrone-yolo26l": HFModelSpec(
        repo_id="dronefreak/visdrone-yolo26l",
        filename="best.pt",
        description="VisDrone aerial dataset fine-tuned YOLOv26-L",
    ),
    "iisc-aim/uvh-26": HFModelSpec(
        repo_id="iisc-aim/UVH-26",
        filename="weights/YOLOv11-X/UVH-26-MV-YOLOv11-X.pt",
        description="UVH-26 Indian urban traffic YOLOv11-X",
    ),
    "iisc-aim/uvh-26-s": HFModelSpec(
        repo_id="iisc-aim/UVH-26",
        filename="weights/YOLOv11-S/UVH-26-MV-YOLOv11-S.pt",
        description="UVH-26 Indian urban traffic YOLOv11-S (lightweight)",
    ),
}

MODEL_ALIASES: dict[str, str] = {
    "coco": "yolo26x.pt",
    "yolo26x": "yolo26x.pt",
    "visdrone-yolo11x": "dronefreak/visdrone-yolo11x",
    "visdrone-yolo26l": "dronefreak/visdrone-yolo26l",
    "uvh-26": "iisc-aim/uvh-26",
    "uvh-26-x": "iisc-aim/uvh-26",
    "iisc-aim/uvh-26-x": "iisc-aim/uvh-26",
    "uvh-26-s": "iisc-aim/uvh-26-s",
}

SELECTABLE_MODELS: list[str] = [
    "yolo26x.pt",
    "dronefreak/visdrone-yolo11x",
    "dronefreak/visdrone-yolo26l",
    "iisc-aim/UVH-26",
    "iisc-aim/UVH-26-s",
]

# Motorized road-vehicle classes across COCO, VisDrone, and UVH-26 (matched case-insensitively).
VEHICLE_CLASSES_LOWER: set[str] = {
    "car",
    "motorcycle",
    "bus",
    "truck",
    "van",
    "motor",
    "motorbike",
    "tricycle",
    "awning-tricycle",
    "hatchback",
    "sedan",
    "suv",
    "muv",
    "three-wheeler",
    "two-wheeler",
    "lcv",
    "mini-bus",
    "tempo-traveller",
}

# Canonical remap for grouped NMS: merges fine-grained 4-wheeler subclasses into "car"
# and 2-wheeler subclasses into "motorcycle" so intra-car NMS never suppresses motorcycles.
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
    "tricycle": "three-wheeler",
    "awning-tricycle": "three-wheeler",
    "three-wheeler": "three-wheeler",
}

CANONICAL_ID_TO_NAME: dict[int, str] = {
    0: "car",
    1: "motorcycle",
    2: "bus",
    3: "truck",
    4: "three-wheeler",
}
CANONICAL_NAME_TO_ID: dict[str, int] = {name: cid for cid, name in CANONICAL_ID_TO_NAME.items()}
MAX_BOX_OFFSET = 7680.0


@dataclass
class InteractiveSelection:
    model: str
    nms_mode: str
    imgsz: int
    conf: float
    iou: float
    sahi: bool


def download_hf_weights(spec: HFModelSpec) -> Path:
    """Download Hugging Face weights to a local cache directory if not already present."""
    repo_dir = MODELS_CACHE_DIR / spec.repo_id.replace("/", "--")
    dest_path = repo_dir / Path(spec.filename).name
    if dest_path.is_file() and dest_path.stat().st_size > 0:
        return dest_path

    repo_dir.mkdir(parents=True, exist_ok=True)
    url = f"https://huggingface.co/{spec.repo_id}/resolve/main/{spec.filename}"
    part_path = dest_path.with_suffix(dest_path.suffix + ".part")
    print(f"Downloading {spec.repo_id} ({spec.filename}) -> {dest_path}")

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, part_path.open("wb") as out:
            total = resp.headers.get("Content-Length")
            total_bytes = int(total) if total and total.isdigit() else None
            downloaded = 0
            chunk_size = 1024 * 1024
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out.write(chunk)
                downloaded += len(chunk)
                if total_bytes:
                    pct = downloaded * 100.0 / total_bytes
                    print(
                        f"\r  {downloaded / (1024 * 1024):.1f} / {total_bytes / (1024 * 1024):.1f} MB ({pct:.1f}%)",
                        end="",
                        flush=True,
                    )
                else:
                    print(f"\r  {downloaded / (1024 * 1024):.1f} MB", end="", flush=True)
        print()
        part_path.replace(dest_path)
    except Exception:
        if part_path.exists():
            part_path.unlink()
        raise

    return dest_path


def resolve_model_source(model_arg: str) -> str:
    """Resolve a preset name, alias, or local path into a loadable YOLO weights path."""
    cleaned = model_arg.strip()
    normalized = MODEL_ALIASES.get(cleaned.lower(), cleaned)
    preset = MODEL_PRESETS.get(normalized.lower())
    if preset is not None:
        return str(download_hf_weights(preset))

    local_candidate = Path(normalized)
    if local_candidate.is_file():
        return str(local_candidate)
    project_candidate = PROJECT_ROOT / normalized
    if project_candidate.is_file():
        return str(project_candidate)
    return normalized


def print_available_models() -> None:
    """Print available model presets and aliases."""
    print("Available models:")
    print(f"  - {'yolo26x.pt':<30} COCO pretrained (aliases: coco, yolo26x)")
    for key, spec in MODEL_PRESETS.items():
        display = (
            "iisc-aim/UVH-26"
            if key == "iisc-aim/uvh-26"
            else ("iisc-aim/UVH-26-s" if key == "iisc-aim/uvh-26-s" else spec.repo_id)
        )
        print(f"  - {display:<30} {spec.description}")


def pick_options_gui(
    initial_model: str,
    initial_nms_mode: str,
    initial_imgsz: int,
    initial_conf: float,
    initial_iou: float,
    initial_sahi: bool,
) -> InteractiveSelection | None:
    """Open a lightweight Tkinter dialog to select model and inference options."""
    result_holder: dict[str, InteractiveSelection | None] = {"value": None}

    root = tk.Tk()
    root.title("Select Detection Model & Options")
    root.attributes("-topmost", True)
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=14)
    frame.grid(row=0, column=0, sticky="nsew")

    ttk.Label(frame, text="Model:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
    model_var = tk.StringVar(
        value=initial_model if initial_model in SELECTABLE_MODELS else SELECTABLE_MODELS[0]
    )
    for idx, model_name in enumerate(SELECTABLE_MODELS, start=1):
        ttk.Radiobutton(frame, text=model_name, value=model_name, variable=model_var).grid(
            row=idx, column=0, columnspan=2, sticky="w", padx=6, pady=2
        )

    row_offset = len(SELECTABLE_MODELS) + 1
    ttk.Label(frame, text="NMS Mode:", font=("Segoe UI", 10, "bold")).grid(
        row=row_offset, column=0, sticky="w", pady=(10, 2)
    )
    nms_var = tk.StringVar(value=initial_nms_mode)
    nms_combo = ttk.Combobox(
        frame,
        textvariable=nms_var,
        values=["grouped", "agnostic", "raw"],
        state="readonly",
        width=18,
    )
    nms_combo.grid(row=row_offset, column=1, sticky="w", pady=(10, 2))

    ttk.Label(frame, text="Image Size (imgsz):").grid(row=row_offset + 1, column=0, sticky="w", pady=2)
    imgsz_var = tk.StringVar(value=str(initial_imgsz))
    imgsz_combo = ttk.Combobox(
        frame,
        textvariable=imgsz_var,
        values=["640", "800", "960", "1280"],
        width=18,
    )
    imgsz_combo.grid(row=row_offset + 1, column=1, sticky="w", pady=2)

    ttk.Label(frame, text="Confidence (conf):").grid(row=row_offset + 2, column=0, sticky="w", pady=2)
    conf_var = tk.StringVar(value=str(initial_conf))
    ttk.Entry(frame, textvariable=conf_var, width=21).grid(row=row_offset + 2, column=1, sticky="w", pady=2)

    ttk.Label(frame, text="NMS IoU (iou):").grid(row=row_offset + 3, column=0, sticky="w", pady=2)
    iou_var = tk.StringVar(value=str(initial_iou))
    ttk.Entry(frame, textvariable=iou_var, width=21).grid(row=row_offset + 3, column=1, sticky="w", pady=2)

    sahi_var = tk.BooleanVar(value=initial_sahi)
    ttk.Checkbutton(frame, text="Enable SAHI sliced inference (2x2 + full)", variable=sahi_var).grid(
        row=row_offset + 4, column=0, columnspan=2, sticky="w", pady=(8, 4)
    )

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=row_offset + 5, column=0, columnspan=2, sticky="e", pady=(10, 0))

    def on_confirm() -> None:
        try:
            imgsz_val = int(imgsz_var.get())
            conf_val = float(conf_var.get())
            iou_val = float(iou_var.get())
        except ValueError:
            return
        result_holder["value"] = InteractiveSelection(
            model=model_var.get(),
            nms_mode=nms_var.get(),
            imgsz=imgsz_val,
            conf=conf_val,
            iou=iou_val,
            sahi=bool(sahi_var.get()),
        )
        root.destroy()

    def on_cancel() -> None:
        result_holder["value"] = None
        root.destroy()

    ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side="right", padx=(6, 0))
    ttk.Button(btn_frame, text="Next: Pick Image", command=on_confirm).pack(side="right")

    root.bind("<Return>", lambda _event: on_confirm())
    root.bind("<Escape>", lambda _event: on_cancel())
    root.mainloop()
    return result_holder["value"]


def pick_image() -> Path | None:
    """Open a file dialog so the user can choose an image file."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    initial_dir = DEFAULT_IMAGE_DIR if DEFAULT_IMAGE_DIR.exists() else PROJECT_ROOT
    selected = filedialog.askopenfilename(
        title="Select an image for object detection",
        initialdir=str(initial_dir),
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.webp"), ("All files", "*.*")],
    )
    root.destroy()
    return Path(selected) if selected else None


def build_slice_windows(width: int, height: int, grid_n: int, overlap: float) -> list[tuple[int, int, int, int]]:
    """Create full-image plus overlapping tile windows for SAHI-style inference."""
    windows: list[tuple[int, int, int, int]] = [(0, 0, width, height)]
    if grid_n <= 1:
        return windows

    clamped_overlap = min(max(overlap, 0.0), 0.75)
    denom = grid_n - (grid_n - 1) * clamped_overlap
    slice_w = max(1, int(round(width / denom)))
    slice_h = max(1, int(round(height / denom)))
    stride_x = max(1, int(round(slice_w * (1.0 - clamped_overlap))))
    stride_y = max(1, int(round(slice_h * (1.0 - clamped_overlap))))

    xs = sorted(set(list(range(0, max(1, width - slice_w + 1), stride_x)) + [max(0, width - slice_w)]))
    ys = sorted(set(list(range(0, max(1, height - slice_h + 1), stride_y)) + [max(0, height - slice_h)]))

    for y0 in ys:
        for x0 in xs:
            windows.append((x0, y0, min(width, x0 + slice_w), min(height, y0 + slice_h)))
    return windows


def collect_detections(
    model,
    image_path: Path,
    imgsz: int,
    conf: float,
    iou: float,
    nms_mode: str,
    target_class_ids: list[int] | None,
    use_sahi: bool,
    sahi_grid: int,
    sahi_overlap: float,
):
    """Run single-image or SAHI tiled inference and return base Result + raw detection tensor."""
    base_result = model.predict(
        source=str(image_path),
        conf=conf,
        iou=max(iou, 0.85) if nms_mode == "grouped" else iou,
        imgsz=imgsz,
        classes=target_class_ids,
        agnostic_nms=(nms_mode == "agnostic"),
        max_det=1000 if nms_mode == "grouped" else 300,
        save=False,
        verbose=False,
    )[0]

    if not use_sahi:
        boxes = base_result.boxes
        if boxes is None or len(boxes) == 0:
            return base_result, torch.zeros((0, 6), dtype=torch.float32)
        tensor = torch.cat(
            [boxes.xyxy.cpu(), boxes.conf.cpu().unsqueeze(1), boxes.cls.cpu().unsqueeze(1)],
            dim=1,
        )
        return base_result, tensor

    orig_img = cv2.imread(str(image_path))
    if orig_img is None:
        raise FileNotFoundError(f"Failed to read image with OpenCV: {image_path}")
    height, width = orig_img.shape[:2]
    windows = build_slice_windows(width, height, sahi_grid, sahi_overlap)

    all_xyxy: list[torch.Tensor] = []
    all_conf: list[torch.Tensor] = []
    all_cls: list[torch.Tensor] = []

    if base_result.boxes is not None and len(base_result.boxes) > 0:
        all_xyxy.append(base_result.boxes.xyxy.cpu())
        all_conf.append(base_result.boxes.conf.cpu())
        all_cls.append(base_result.boxes.cls.cpu())

    # Skip index 0 (full image already predicted above).
    for x0, y0, x1, y1 in windows[1:]:
        crop = orig_img[y0:y1, x0:x1]
        slice_res = model.predict(
            source=crop,
            conf=conf,
            iou=max(iou, 0.85) if nms_mode == "grouped" else iou,
            imgsz=imgsz,
            classes=target_class_ids,
            agnostic_nms=(nms_mode == "agnostic"),
            max_det=1000 if nms_mode == "grouped" else 300,
            save=False,
            verbose=False,
        )[0]
        if slice_res.boxes is not None and len(slice_res.boxes) > 0:
            xyxy = slice_res.boxes.xyxy.cpu().clone()
            xyxy[:, [0, 2]] += x0
            xyxy[:, [1, 3]] += y0
            all_xyxy.append(xyxy)
            all_conf.append(slice_res.boxes.conf.cpu())
            all_cls.append(slice_res.boxes.cls.cpu())

    if not all_xyxy:
        return base_result, torch.zeros((0, 6), dtype=torch.float32)

    combined = torch.cat(
        [
            torch.cat(all_xyxy, dim=0),
            torch.cat(all_conf, dim=0).unsqueeze(1),
            torch.cat(all_cls, dim=0).unsqueeze(1),
        ],
        dim=1,
    )
    return base_result, combined


def apply_nms_and_remap(
    detections: torch.Tensor,
    orig_names: dict[int, str],
    nms_mode: str,
    iou: float,
) -> tuple[torch.Tensor, dict[int, str]]:
    """Remap classes (in grouped mode) before running final NMS so 4-wheelers don't suppress motorcycles."""
    if detections.numel() == 0:
        if nms_mode == "grouped":
            return detections, dict(CANONICAL_ID_TO_NAME)
        return detections, dict(orig_names)

    boxes = detections[:, :4]
    scores = detections[:, 4]
    cls_ids = detections[:, 5].long()

    if nms_mode == "grouped":
        final_names: dict[int, str] = dict(CANONICAL_ID_TO_NAME)
        next_extra_id = len(final_names)
        extra_name_to_id: dict[str, int] = {}
        remapped_ids: list[int] = []

        for cid in cls_ids.tolist():
            raw_name = str(orig_names[int(cid)]).strip()
            canonical = CANONICAL_CLASS_MAP.get(raw_name.lower())
            if canonical is not None:
                remapped_ids.append(CANONICAL_NAME_TO_ID[canonical])
            else:
                key = raw_name.lower()
                if key not in extra_name_to_id:
                    extra_name_to_id[key] = next_extra_id
                    final_names[next_extra_id] = raw_name
                    next_extra_id += 1
                remapped_ids.append(extra_name_to_id[key])

        mapped_cls = torch.tensor(remapped_ids, dtype=torch.float32)
        offsets = mapped_cls.unsqueeze(1) * MAX_BOX_OFFSET
        keep = torchvision.ops.nms(boxes + offsets, scores, iou)
        final_boxes = torch.cat([boxes[keep], scores[keep].unsqueeze(1), mapped_cls[keep].unsqueeze(1)], dim=1)
        return final_boxes, final_names

    if nms_mode == "agnostic":
        keep = torchvision.ops.nms(boxes, scores, iou)
        return detections[keep], dict(orig_names)

    # raw mode (class-aware NMS using model's original class IDs)
    offsets = cls_ids.float().unsqueeze(1) * MAX_BOX_OFFSET
    keep = torchvision.ops.nms(boxes + offsets, scores, iou)
    return detections[keep], dict(orig_names)


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict vehicles in a selected image using switchable YOLO models")
    parser.add_argument("image", nargs="?", type=Path, help="Path to image (opens file picker if omitted)")
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model preset, Hugging Face repo ID, or .pt path "
            "(yolo26x.pt, dronefreak/visdrone-yolo11x, dronefreak/visdrone-yolo26l, "
            "iisc-aim/UVH-26, iisc-aim/UVH-26-s)"
        ),
    )
    parser.add_argument("--conf", type=float, default=DEFAULT_CONF, help=f"Confidence threshold (default: {DEFAULT_CONF})")
    parser.add_argument("--iou", type=float, default=DEFAULT_IOU, help=f"NMS IoU threshold (default: {DEFAULT_IOU})")
    parser.add_argument("--imgsz", type=int, default=DEFAULT_IMGSZ, help=f"Inference image size (default: {DEFAULT_IMGSZ})")
    parser.add_argument(
        "--nms-mode",
        choices=["grouped", "agnostic", "raw"],
        default=DEFAULT_NMS_MODE,
        help=(
            "NMS strategy: 'grouped' remaps 4-wheelers (Sedan/Hatchback/SUV->car) and Two-wheeler->motorcycle "
            "before running per-group NMS (default); 'agnostic' runs global agnostic_nms; 'raw' keeps original classes"
        ),
    )
    parser.add_argument(
        "--agnostic-nms",
        action="store_true",
        help="Shortcut for --nms-mode agnostic (enables class-agnostic NMS)",
    )
    parser.add_argument("--sahi", action="store_true", help="Enable SAHI-style overlapping slice inference")
    parser.add_argument("--sahi-grid", type=int, default=2, help="SAHI grid divisions per axis (default: 2 -> 2x2 + full)")
    parser.add_argument("--sahi-overlap", type=float, default=0.25, help="SAHI tile overlap ratio (default: 0.25)")
    parser.add_argument(
        "--all-classes",
        action="store_true",
        help="Detect all classes defined by the model instead of filtering to road vehicles",
    )
    parser.add_argument("--select-model", action="store_true", help="Open GUI dialog to pick model and options")
    parser.add_argument("--list-models", action="store_true", help="List available model presets and exit")
    parser.add_argument("--no-show", action="store_true", help="Do not open the result image window")
    args = parser.parse_args()

    if args.list_models:
        print_available_models()
        return

    nms_mode = "agnostic" if args.agnostic_nms else args.nms_mode
    model_arg = args.model or DEFAULT_MODEL
    imgsz = args.imgsz
    conf = args.conf
    iou = args.iou
    use_sahi = args.sahi

    # Show interactive picker if requested or if launched with zero CLI args (e.g. IDE Run button).
    no_cli_args = len(sys.argv) == 1
    if args.select_model or (no_cli_args and args.image is None and args.model is None):
        chosen = pick_options_gui(
            initial_model=model_arg,
            initial_nms_mode=nms_mode,
            initial_imgsz=imgsz,
            initial_conf=conf,
            initial_iou=iou,
            initial_sahi=use_sahi,
        )
        if chosen is None:
            print("Selection cancelled.")
            return
        model_arg = chosen.model
        nms_mode = chosen.nms_mode
        imgsz = chosen.imgsz
        conf = chosen.conf
        iou = chosen.iou
        use_sahi = chosen.sahi

    image_path = args.image or pick_image()
    if image_path is None:
        print("No image selected.")
        return
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    from ultralytics import YOLO
    from ultralytics.utils.files import increment_path

    weights_source = resolve_model_source(model_arg)
    model = YOLO(weights_source)

    target_class_ids: list[int] | None = None
    if not args.all_classes:
        target_class_ids = [
            cid for cid, name in model.names.items() if str(name).strip().lower() in VEHICLE_CLASSES_LOWER
        ]
        if not target_class_ids:
            raise ValueError(
                f"None of expected vehicle classes found in model classes {list(model.names.values())}. "
                "Try --all-classes."
            )

    result, raw_detections = collect_detections(
        model=model,
        image_path=image_path,
        imgsz=imgsz,
        conf=conf,
        iou=iou,
        nms_mode=nms_mode,
        target_class_ids=target_class_ids,
        use_sahi=use_sahi,
        sahi_grid=args.sahi_grid,
        sahi_overlap=args.sahi_overlap,
    )
    final_boxes, final_names = apply_nms_and_remap(
        detections=raw_detections,
        orig_names=result.names,
        nms_mode=nms_mode,
        iou=iou,
    )
    result.names = final_names
    result.update(boxes=final_boxes)

    save_dir = increment_path(PROJECT_ROOT / "runs" / "detect" / "predict", mkdir=True)
    saved_path = (save_dir / image_path.name).with_suffix(".jpg")
    result.save(filename=str(saved_path))

    boxes = result.boxes
    names = result.names
    counts = Counter(names[int(cls_id)] for cls_id in boxes.cls.tolist()) if boxes is not None else Counter()

    print(f"\nModel: {model_arg} ({weights_source})")
    print(f"Settings: imgsz={imgsz}, conf={conf}, iou={iou}, nms_mode={nms_mode}, sahi={use_sahi}")
    print(f"Image: {image_path}")
    print(f"Detections ({len(boxes) if boxes is not None else 0}): {dict(counts)}")
    if counts and any(k.lower() not in {"car", "motorcycle", "bus", "truck"} for k in counts):
        mapped_counts = Counter(
            CANONICAL_CLASS_MAP.get(names[int(cls_id)].strip().lower(), names[int(cls_id)])
            for cls_id in boxes.cls.tolist()
        )
        print(f"Grouped summary: {dict(mapped_counts)}")

    if boxes is not None:
        for box in boxes:
            cls_name = names[int(box.cls.item())]
            box_conf = float(box.conf.item())
            x1, y1, x2, y2 = (round(v, 1) for v in box.xyxy[0].tolist())
            print(f"  - {cls_name}: {box_conf:.2f} [{x1}, {y1}, {x2}, {y2}]")

    print(f"Saved result: {saved_path}")

    if not args.no_show:
        result.show()


if __name__ == "__main__":
    main()
