# Task 03 Source Directory (`03_cv_yolo_pipeline/src/`)

See full technical specification in [`../GOAL.md`](../GOAL.md).

## Existing Scripts

- [`predict_yolo26x.py`](predict_yolo26x.py): Interactive and CLI single-image vehicle detection script supporting `yolo26x.pt`, `dronefreak/visdrone-yolo11x`, `dronefreak/visdrone-yolo26l`, `iisc-aim/UVH-26`, `iisc-aim/UVH-26-s`, canonical class-remapped NMS (`grouped`), and SAHI sliced inference.

```bash
# List supported model presets
python 03_cv_yolo_pipeline/src/predict_yolo26x.py --list-models

# Run inference on a single cleaned image with UVH-26
python 03_cv_yolo_pipeline/src/predict_yolo26x.py Dataset_Clean_V1/cctv_images/26/26_20260825_074041.jpg --model iisc-aim/UVH-26 --no-show
```

## Recommended Batch Pipeline Scripts to Add

```text
03_cv_yolo_pipeline/src/
├── predict_yolo26x.py              # Existing single-image detector & NMS/SAHI utility module
├── build_median_backgrounds.py     # Step 2: Extracts clean-road median backgrounds for 100 cameras
├── run_batch_detection.py          # Step 3: Single-pass batch GPU inference over Dataset_Clean_V1/cctv_images/
└── postprocess_static_and_roi.py   # Steps 4 & 5: IoU > 0.65 static filter, Auto ROI & Parquet export
```
