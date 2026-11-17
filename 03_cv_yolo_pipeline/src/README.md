# Task 03 Source Directory (`03_cv_yolo_pipeline/src/`)

See full technical specification in [`../GOAL.md`](../GOAL.md).

## Scripts

- [`robust_detector.py`](robust_detector.py): Multi-expert edge-case-resilient ensemble (`RobustTrafficDetector`) combining **5 locally cached pretrained checkpoints** (`iisc-aim/UVH-26`, `dronefreak/visdrone-yolo11x`, `dronefreak/visdrone-yolo26l`, `yolo26x.pt`, and `yolo11x.pt`) with:
  1. Lazy per-camera day/night median background (`data/median_backgrounds/<cam_id>_bg[_night].jpg`) and adjacent-frame (`<= 30 min`, `MAD >= 2.5`) context (`CameraSceneProvider`).
  2. Optical condition profiling + highlight-compressed CLAHE/gamma enhancement (`build_optical_views`) for night glare, dark scenes, and low-contrast rain/haze.
  3. Precision horizontal-row OSD timestamp inpainting (`build_osd_mask` + `_filter_osd_text_rows` + `inpaint_osd_text` strictly in verified collinear text rows inside `y < 0.12*H` / `y > 0.84*H`), keeping the raw un-inpainted `full` frame intact alongside OSD-cleaned zoomed sub-crops (`full_osd`, `far_mid`, `lower_road`, `lower_left`, `lower_right`) so closer/lower-frame vehicles on high/distant cameras are never erased or cropped out, plus OSD-row FP veto (`_is_osd_text_box`).
  4. Batched 5-model inference with model-family-aware enhanced crop routing, VisDrone oblique-sedan `truck` corroboration, and UVH-26 sub-crop `bus`/`truck` filtering.
  5. Rider + overlapping two-wheeler boosting (`_promote_riders_to_motorcycles`, without promoting standalone pedestrians).
  6. Perspective geometric bounds + Sobel edge NCC / foreground / parked-car & adjacent-frame stationary sign suppression (`_is_static_or_parked`), plus glare-streak, featureless wet/blurry spot, 4W/2W perspective-scale, and large-box low-raw-confidence (`area >= 1,200` with `max_raw_conf < 0.20`, or upper-zone `area >= 2,000` with `max_raw_conf < 0.30`) LED-billboard filtering (`_passes_quality_and_glare_gates`).
  7. Model-family-independent weighted box fusion (`_model_family`: `visdrone_fam`, `coco_fam`, `uvh26_fam` across `GROUP_4W` and `GROUP_2W`) with `IoU` + `IoMin` + normalized center-distance clustering, multi-model giant heavy-vehicle consolidation (`_consolidate_giant_heavy_vehicles`), multi-child wrapper pruning, within-group/cross-group duplicate pruning, and bus/truck sub-part suppression (`_suppress_heavy_vehicle_subparts`).
- [`predict_yolo26x.py`](predict_yolo26x.py): Interactive GUI and CLI single-image detector supporting `--model ensemble` (aliases: `multi`, `robust`), `yolo26x.pt`, `dronefreak/visdrone-yolo11x`, `dronefreak/visdrone-yolo26l`, `iisc-aim/UVH-26`, `iisc-aim/UVH-26-s`, canonical grouped NMS, and SAHI sliced inference.
- [`evaluate_edge_cases.py`](evaluate_edge_cases.py): Stratified 100-camera edge-case benchmark (**`203` valid frames covering `100 / 100` unique cameras** across `rain_wet_road`, `night_glare`, `dense_mixed_rush`, `blurry_degraded`, and `static_traps` — with visual contrast-drop filtering for true rain/storm scenes), saving annotated images, 2x2 single-model vs. ensemble comparison grids (`runs/detect/edge_case_eval/comparisons/`), category montages (`runs/detect/edge_case_eval/montages/`), and summary metrics (`edge_case_eval_summary.json`).

```bash
# List supported model presets (including 5-expert `ensemble`)
python 03_cv_yolo_pipeline/src/predict_yolo26x.py --list-models

# Run the recommended 5-expert ensemble on a challenging OSD-occluded glare or dense frame
python 03_cv_yolo_pipeline/src/predict_yolo26x.py Dataset_Clean_V1/cctv_images/18/18_20260831_200055.jpg --model ensemble --no-show
python 03_cv_yolo_pipeline/src/predict_yolo26x.py Dataset_Clean_V1/cctv_images/26/26_20260825_074041.jpg --model ensemble --no-show

# Run stratified 100-camera (203-frame) edge-case benchmark & generate visual comparisons
python 03_cv_yolo_pipeline/src/evaluate_edge_cases.py
```

## Latest Verified 100-Camera Edge-Case Evaluation (`evaluate_edge_cases.py`)

- **Coverage:** `203` valid frames across `100 / 100` unique cameras (`318.45s` total, `1,562.6 ms` mean/frame on RTX 3050 Ti Laptop GPU).
- **Aggregate Metrics:** `2,013` detected vehicles, `6,546` suppressed static/noise/glare/OSD/sub-part/billboard boxes, `0.981` mean multi-model agreement.
- **Breakdown (`runs/detect/edge_case_eval/edge_case_eval_summary.json`):**
  - `night_glare` (74 frames / 74 cams): mean `6.89` vehicles/frame, `2,456` suppressed, `0.99` agreement
  - `dense_mixed_rush` (56 frames / 56 cams): mean `14.77` vehicles/frame, `2,005` suppressed, `0.96` agreement
  - `rain_wet_road` (38 frames / 38 cams): mean `7.61` vehicles/frame, `1,060` suppressed, `0.99` agreement
  - `static_traps` (19 frames / 19 cams): mean `16.79` vehicles/frame, `398` suppressed, `0.99` agreement
  - `blurry_degraded` (16 frames / 14 cams): mean `4.25` vehicles/frame, `627` suppressed, `1.0` agreement

## Proposed Fine-Tuning / Knowledge Distillation (If Faster Batch Throughput Is Needed)

The pretrained 5-expert `ensemble` requires no training and runs at `1,562.6 ms/frame` mean inference time (`~26.1 hours` estimated if extrapolated across all `60,029` valid frames in `V2.0`, which works well for overnight/split batch execution). If faster single-pass batch inference is required without losing edge-case accuracy:
1. Generate pseudo-labels using `RobustTrafficDetector` across `4,000–6,000` stratified diverse frames (day/night/rain/glare/blur/all 100 cameras) + curate `~300–500` hand-corrected extreme-bloom night frames and hard-negative static traps (zebra crossings, billboards, shopfronts).
2. Train a single unified student model (e.g., `yolo11m` or `yolo26m`/`yolo26l` initialized from `VisDrone` or COCO) using strong mosaic/HSV/motion-blur/rain-glare augmentations + hard-negative tiles, keeping Stage 1/Stage 6 background/edge-NCC post-filtering enabled at inference time.

## Recommended Batch Pipeline Scripts for Full-Dataset Production Run

```text
03_cv_yolo_pipeline/src/
├── robust_detector.py              # Multi-expert ensemble + optical/background physics gates
├── predict_yolo26x.py              # Single-image detector & NMS/SAHI/Ensemble CLI + GUI
├── evaluate_edge_cases.py          # 100-camera stratified edge-case benchmark & visualizer
├── build_median_backgrounds.py     # Step 2: Precomputes clean-road median backgrounds for all 100 cameras
├── run_batch_detection.py          # Step 3: Batch GPU inference over Dataset_Clean_V1/cctv_images/
└── postprocess_static_and_roi.py   # Steps 4 & 5: IoU > 0.65 static filter, Auto ROI & Parquet export
```
