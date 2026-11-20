# Task 03 Source Directory (`03_cv_yolo_pipeline/src/`)

See full technical specification in [`../GOAL.md`](../GOAL.md).

## Scripts & Notebooks

- [`robust_detector.py`](robust_detector.py): Multi-expert edge-case-resilient ensemble (`RobustTrafficDetector`) supporting both single-image (`predict`) and frame-aligned batched GPU inference (`predict_batch`, `quantize=16` / `half=` auto-compatibility) across **6 pretrained checkpoints**:
  - **Daytime (`not is_night_or_glare`):** `iisc-aim/UVH-26` (`YOLOv11-X`), `dronefreak/visdrone-yolo11x`, `dronefreak/visdrone-yolo26l`, `yolo26x.pt`, `yolo11x.pt`.
  - **Nighttime / Heavy Glare (`is_night_or_glare`):** swaps `visdrone26l` for `dronefreak/bdd100k-yolo26m` (`best.pt`), adds highlight-compressed CLAHE/gamma (`enh`, `deglare`) optical views, and enforces crosswalk oscillation suppression + illumination-invariant background NCC + phantom-motorcycle guards.
  - **4 Canonical Classes (`DATA_CONTRACT.md`):** `car` (includes `three-wheeler` / `tricycle` / `awning-tricycle`), `motorcycle`, `bus`, `truck`.
  - **Physics / Scene Gates:** Per-camera day & night Median Backgrounds (`data/median_backgrounds/`), adjacent-frame temporal stationary filter (`<= 30 min`, `MAD >= 2.5`), horizontal-row TELEA OSD timestamp inpainting, Sobel gradient/background NCC, heavy-vehicle consolidation, and user-reviewed Road ROI ground-contact filtering (`data/camera_rois.json`).
- [`run_batch_cv_pipeline.py`](run_batch_cv_pipeline.py): Production Stage 03 CLI entrypoint (wired into `run_pipeline.py --stage 03`), featuring VRAM-aware batch auto-tuning (`A100/L4/T4/4GB`), resumable per-camera Parquet checkpoints, `--images-zip-dir` per-camera annotated JPEG zip backups, atomic writes, and strict `DATA_CONTRACT.md` Parquet export (`data/vehicle_counts.parquet` & `data/vehicle_counts_sample.parquet`).
- [`../Colab_A100_Batch_Detection.ipynb`](../Colab_A100_Batch_Detection.ipynb): Google Colab (`A100/L4/T4`) notebook for full `60,029`-frame GPU inference with automatic Google Drive checkpointing and 20-camera `.zip` export.
- [`generate_initial_rois.py`](generate_initial_rois.py) & [`edit_camera_rois.py`](edit_camera_rois.py): Automated SAM2 / vehicle-footprint road polygon generator + interactive desktop GUI ROI editor producing `data/camera_rois.json` (`data/camera_rois.auto_v3_backup.json` snapshot).
- [`evaluate_edge_cases.py`](evaluate_edge_cases.py): Stratified 100-camera edge-case benchmark (`203` frames across `rain_wet_road`, `night_glare`, `dense_mixed_rush`, `blurry_degraded`, and `static_traps`).
- [`predict_yolo26x.py`](predict_yolo26x.py): Single-image GUI/CLI detector supporting `--model ensemble`, single weights, grouped canonical NMS, and SAHI slicing.

```bash
# Run Stage 03 via pipeline orchestrator (or --sample for 5 pilot cameras)
python run_pipeline.py --stage 03
python run_pipeline.py --stage 03 --sample

# Direct CLI run with optional annotated JPEG export
python 03_cv_yolo_pipeline/src/run_batch_cv_pipeline.py --all --save-images --zip-images

# Verify DATA_CONTRACT.md Parquet outputs
python run_pipeline.py --check-contract
```

## Production Run Results (Full `60,029` Frames on Google Colab A100)

- **Coverage (`data/vehicle_counts.parquet`):** `60,029` valid frames across `100 / 100` cameras (`501–613` frames/camera), `0` nulls, primary key `('cam_id', 'timestamp')` valid.
- **Pilot Subset (`data/vehicle_counts_sample.parquet`):** `2,929` rows across the `5` pilot cameras (`26, 136, 137, 150, 546`).
- **Aggregate Counts & Scene Metrics:**
  - **Total Dynamic Vehicles:** `631,524` (`car: 438,832`, `motorcycle: 146,695`, `bus: 9,444`, `truck: 36,553`)
  - **Per-Frame Means:** `10.52` vehicles/frame (`11.02` day vs. `8.67` night; max `69`), `10.03` PCU/frame, `0.1780` `road_occupancy_ratio`, `0.2888` `foreground_ratio`
  - **Static/Noise Filtering:** `1,993,934` static false-positive boxes suppressed across `60,029` frames (`2.50%` / `1,503` zero-vehicle frames)
  - **Visual Archive (`Google Drive` / local `.zip`):** `60,029` annotated bounding-box + ROI JPEGs (`scale=1.5`, `3,923.91 MB`, excluded from Git via `.gitignore`)
- **Contract Status:** `python run_pipeline.py --check-contract` → `[PASS]` on Tables `1`, `2`, `3a`, `3b`, and `4`.

## Completeness & Verification Checklist

| Check / Deliverable | Verified Result |
| :--- | :--- |
| **`data/vehicle_counts.parquet`** | `60,029` rows × `13` cols; exact 1-to-1 `(cam_id, timestamp)` match against `image_quality_manifest.parquet[is_valid]` (`0` missing, `0` extra); `0` nulls, `0` negatives, `0` `inf` |
| **`data/vehicle_counts_sample.parquet`** | `2,929` rows × `13` cols across pilot cameras `[26, 136, 137, 150, 546]`; exact subset of `vehicle_counts.parquet` |
| **Formula & ROI Floor Audit** | `total_vehicle_count == car + moto + bus + truck` (`True`); `max_pcu_diff = 0.0`, `max_occ_diff = 0.0`; `0` cameras below `15%` ROI floor (Cam `395` `348×261` → `road_roi_area = 28,646.0` ≥ `13,624.2`) |
| **`data/camera_rois.json` & Backgrounds** | `100 / 100` cameras with reviewed Road ROIs; `200 / 200` cached median plates (`100` `_bg.jpg` + `100` `_bg_night.jpg`) in `data/median_backgrounds/` |
| **Sanity Check (Busiest vs. Quietest Cams)** | Top avg vehicles/frame: `cam_277` (`32.34`), `cam_11` (`24.88`), `cam_75` (`23.23`), `cam_599` (`22.32`), `cam_124` (`21.62`); Quietest: `cam_179` (`2.47`), `cam_370` (`2.77`), `cam_170` (`3.48`), `cam_619` (`3.60`), `cam_1063` (`3.95`) |
| **Visual Inspection Archive (Non-Git)** | `60,029` annotated `.jpg` frames (`scale=1.5`, `3,923.91 MB`) archived externally (`.zip` & `data/annotated_frames/` excluded via `.gitignore`) |

## Module Structure

```text
03_cv_yolo_pipeline/
├── GOAL.md                             # Stage 03 technical spec & completed DoD checklist
├── Colab_A100_Batch_Detection.ipynb    # Resumable Colab A100/L4/T4 execution notebook
└── src/
    ├── README.md                       # This guide & production summary
    ├── robust_detector.py              # 6-weight day/night ensemble + optical/ROI/BG gates + predict_batch
    ├── run_batch_cv_pipeline.py        # Production Stage 03 CLI runner & DATA_CONTRACT Parquet exporter
    ├── generate_initial_rois.py        # Initial auto Road ROI polygon generator
    ├── edit_camera_rois.py             # Interactive GUI ROI editor (`data/camera_rois.json`)
    ├── evaluate_edge_cases.py          # 100-camera stratified edge-case benchmark (203 frames)
    └── predict_yolo26x.py              # Single-image CLI/GUI detector
```
