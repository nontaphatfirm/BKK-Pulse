# Task 03: Computer Vision & Spatio-Temporal Feature Engineering Pipeline (`GOAL.md`)

> **Assigned Role:** Member 3 — Computer Vision & Data Engineering Pipeline  
> **Source Directory:** [`src/`](src/README.md)  
> **Existing Detection Prototype:** [`src/predict_yolo26x.py`](src/predict_yolo26x.py)  
> **Input Data:**  
> - Valid ASCII-renamed images in `Dataset_Clean_V1/cctv_images/` (`60,210` images across 100 cameras)  
> - Frame manifest in [`Dataset_Clean_V1/image_quality_manifest.parquet`](../Dataset_Clean_V1/image_quality_manifest.parquet)  
> **Primary Output Artifacts:**  
> 1. **Priority 1 (Day-1 Fast Track):** `data/vehicle_counts_sample.parquet` *(5 representative cameras, ~3,000 frames, to unblock Tasks 04, 05, and 06 immediately)*  
> 2. **Full Production Dataset:** `data/vehicle_counts.parquet` *(all `60,210` valid frames across 100 cameras per [`DATA_CONTRACT.md`](../DATA_CONTRACT.md))*  
> 3. **Clean-Road Background Library:** `data/median_backgrounds/<cam_id>_bg.jpg` *(100 clean-road background plates for dashboard visual comparison)*

---

## 1. Objective & Engineering Motivation

Raw bounding-box counts on low-resolution (`352 × 288` px; `348 × 261` px for Camera `395`) urban CCTV streams suffer from three severe failure modes:

1. **Static Roadside False Positives:** Roadside advertisement billboards (e.g., ZONTES motorcycle billboards) and permanently parked cars are repeatedly detected as active traffic in every frame.
2. **Far-Field Perspective Occlusion:** Distant vehicle queues near the horizon are too small (`< 8 × 8` px) for standard object detectors to resolve individually.
3. **Camera Zoom & FOV Heterogeneity:** Counting 15 vehicles on a tightly zoomed intersection camera represents gridlock, whereas 15 vehicles on a wide-angle elevated footbridge camera represents free-flowing traffic.

This module resolves all three challenges by combining **Single-Pass Batch YOLO Inference** (building directly on [`src/predict_yolo26x.py`](src/predict_yolo26x.py)) with **Stationary Box Filtering (`IoU > 0.65`)**, **Automated Road ROI Masking (`15%` minimum floor)**, and **Clean-Road Median Background Subtraction (`foreground_ratio`)**.

---

## 2. Step-by-Step Pipeline Specification

### Step 1: Fast-Track 5-Camera Pilot Dataset (`data/vehicle_counts_sample.parquet`)
Before running inference on all 60,210 images, execute the full pipeline on **5 representative cameras** (~3,000 images total, taking only a few minutes on GPU):
- `136` & `137`: Bidirectional footbridge pair on Lat Phrao Road (Big C Extra).
- `26`: Bukkhalo Intersection (Thon Buri arterial).
- `150`: Samsenwittayalai School on Rama 6 Road (contains post-outage recovery segments).
- `546`: Panichayakarn Intersection (Dusit).

Export `data/vehicle_counts_sample.parquet` conforming strictly to [`DATA_CONTRACT.md`](../DATA_CONTRACT.md) and hand it off to **Members 4, 5, and 6**.

---

### Step 2: Clean-Road Median Background Extraction & `foreground_ratio`
For each of the 100 cameras (`i`):
1. Sample **50 valid daytime frames** (`09:00–15:00`, `is_valid == True`).
2. Compute the pixel-wise temporal median across the 50 sampled frames (because moving vehicles occupy any given pixel for only a fraction of the week, the temporal median erases transient traffic and produces a clean empty road plate):

   $$
   B_i(x, y) = \text{median}_{t \in T_{\text{sample}}} I_{i, t}(x, y)
   $$

3. Save the background image to `data/median_backgrounds/<cam_id>_bg.jpg`.
4. For every valid frame, convert both the frame and background to grayscale, compute the absolute pixel difference `|gray(I) - gray(B)| > 25` within the active road ROI mask, and divide by `road_roi_area` to obtain **`foreground_ratio`** (`0.0–1.0`).

---

### Step 3: Batch YOLO Vehicle Detection with Canonical Class-Remapped NMS
Reuse the model resolution and `apply_nms_and_remap` logic already implemented in [`src/predict_yolo26x.py`](src/predict_yolo26x.py#L457-L505):

- All 4 model checkpoints (`models/yolo26x.pt`, `models/dronefreak--visdrone-yolo11x/best.pt`, `models/dronefreak--visdrone-yolo26l/best.pt`, and `models/iisc-aim--UVH-26/UVH-26-MV-YOLOv11-X.pt`) are **already downloaded and cached locally in `models/`**.
- **Execution Speed Rule (Single-Pass Inference Only for Batch Runs):** Do **not** enable `--sahi` sliced tiling across all 60,210 images (multi-tile SAHI increases inference time by `5×–10×` with minimal gain on `352 × 288` frames when paired with `foreground_ratio`). Benchmark single-pass models on the 5-camera pilot, pick the best single-pass checkpoint (e.g., `iisc-aim/UVH-26` or `yolo26x.pt`), and run batched GPU inference (`batch=32` or `64`). Reserve `--sahi` strictly for single-image interactive inspection in the dashboard.
- Apply `CANONICAL_CLASS_MAP` in `grouped` NMS mode so fine-grained 4-wheeler subclasses (`sedan`, `hatchback`, `suv`, `muv`, `van`) merge into `car`, and 2-wheeler subclasses (`motor`, `motorbike`, `two-wheeler`) merge into `motorcycle` **before** class-aware NMS runs—preventing intra-4-wheeler boxes from suppressing adjacent motorcycles.
- Retain raw frame-level bounding box coordinates `[x1, y1, x2, y2]`, confidence scores, and canonical class IDs (`car`, `motorcycle`, `bus`, `truck`, `three-wheeler`) for Step 4.

---

### Step 4: Stationary Box Filter (Eliminating Roadside Billboards & Parked Cars)
Within each camera's time series:
1. Compare detected bounding boxes across daytime frames using pairwise **Intersection over Union (IoU)**.
2. Flag any bounding box cluster that appears at the same spatial coordinates with **`IoU > 0.65`** in **`> 30%` of daytime frames** (or across **`>= 6` consecutive frames = 1 full hour** without movement).
3. Remove these static boxes from dynamic vehicle counts (`car_count`, `motorcycle_count`, `bus_count`, `truck_count`) and record the number of suppressed boxes per frame in **`filtered_static_boxes`**.

---

### Step 5: Automated Road ROI Area (`road_roi_area`) & Occupancy Calculation
For each camera `i` with frame dimensions `(img_width, img_height)` *(note: `352 × 288` for 99 cameras; `348 × 261` for Camera `395`)*:
1. Initialize a binary 2D mask `M_i` of size `H × W` filled with zeros.
2. Mark `M_i(x, y) = 1` wherever any **dynamic vehicle bounding box** (post-Step 4 filtering) appeared across the 7-day dataset:

   $$
   M_i(x, y) = 1 \iff \exists (t, b \in \text{DynamicBoxes}_{i, t}) \text{ such that } (x, y) \in b
   $$

3. Compute the active road surface area with a **15% minimum frame area floor** to protect low-volume side streets from division-by-near-zero inflation:

   $$
   \text{road\_roi\_area}_i = \max\left(\sum_{x, y} M_i(x, y),\; 0.15 \times W_i \times H_i\right)
   $$

4. For each frame `t`, compute the union pixel area of dynamic bounding boxes (`bbox_total_area`), **Road Occupancy Ratio** (`road_occupancy_ratio = bbox_total_area / road_roi_area`), and **Passenger Car Unit score**:

   $$
   \text{pcu\_score} = 1.0(\text{car\_count}) + 0.33(\text{motorcycle\_count}) + 2.5(\text{bus\_count}) + 2.5(\text{truck\_count})
   $$

> [!NOTE]
> Fold `three-wheeler` detections into `motorcycle_count` or `car_count` consistently. Note that `brightness_mean`, `contrast_std`, and `glare_ratio` are already precomputed in `Dataset_Clean_V1/image_quality_manifest.parquet`.

---

## 3. Deliverable Schema (`data/vehicle_counts.parquet`)

Granularity: `60,210` rows (matching all `is_valid == True` rows in `image_quality_manifest.parquet`).

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `cam_id` | `int64` | Camera ID (matching `cctv_info_cleaned.parquet`) |
| `timestamp` | `datetime64[us]` | Frame capture timestamp |
| `car_count` | `int64` | Dynamic 4-wheel passenger vehicle count |
| `motorcycle_count` | `int64` | Dynamic 2-wheel/3-wheel vehicle count |
| `bus_count` | `int64` | Dynamic bus count |
| `truck_count` | `int64` | Dynamic commercial truck count |
| `total_vehicle_count` | `int64` | Sum of dynamic vehicles (`car + motorcycle + bus + truck`) |
| `pcu_score` | `float64` | `1.0*car + 0.33*motorcycle + 2.5*bus + 2.5*truck` |
| `bbox_total_area` | `float64` | Union pixel area of dynamic vehicle boxes in current frame |
| `road_roi_area` | `float64` | Camera road surface area in pixels (`>= 15%` of `W * H`) |
| `road_occupancy_ratio` | `float64` | `bbox_total_area / road_roi_area` |
| `foreground_ratio` | `float64` | Active foreground pixel ratio relative to Median Background |
| `filtered_static_boxes` | `int64` | Count of static roadside boxes removed in current frame |

---

## 4. Definition of Done Checklist

- [ ] Complete Batch 3 camera verification (17 cameras) in [`CAMERA_AUDIT_CHECKLIST.md`](../00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md).
- [ ] **Priority 1:** Generate 5-camera pilot dataset `data/vehicle_counts_sample.parquet` and notify Members 4, 5, and 6.
- [ ] Generate 100 clean-road background plates in `data/median_backgrounds/<cam_id>_bg.jpg`.
- [ ] Execute single-pass batch inference across all 60,210 valid frames with Stationary Box Filtering and Auto Road ROI masking to produce `data/vehicle_counts.parquet`.
