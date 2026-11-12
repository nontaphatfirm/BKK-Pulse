# Team Contribution & Engineering Guidelines (`CONTRIBUTING.md`)

> This document establishes the Git workflow, module boundaries, and code quality standards for our 6-person team working on **BKK-Pulse**.

---

## 1. Module Ownership & Workspace Isolation

To prevent merge conflicts, each team member works inside their assigned module directories (`01_` through `06_`, with **นิว (`@Pranithi-New`)** supporting across modules as needed) and writes shared outputs to `data/` according to [`DATA_CONTRACT.md`](DATA_CONTRACT.md):

| Primary Owner(s) | GitHub | Module Folder | Dedicated Feature Branch | Primary Output Artifact(s) |
| :--- | :--- | :--- | :--- | :--- |
| **All 6 Members** | Team-wide | `00_data_cleaning_and_qa/` | `chore/00-camera-metadata-qa` | `Dataset_Clean_V1/cctv_info_cleaned.parquet` |
| **ปลื้ม, กร** | [@siravidthongsook](https://github.com/siravidthongsook), [@kkooAAA](https://github.com/kkooAAA) | `01_scraping_apis/` | `feat/01-scraping-apis` | `data/weather_air_poi.parquet` |
| **ปลื้ม, กร** | [@siravidthongsook](https://github.com/siravidthongsook), [@kkooAAA](https://github.com/kkooAAA) | `02_scraping_traffy_playwright/` | `feat/02-scraping-playwright` | `data/external_weather_poi.parquet`, `data/traffy_complaints_near_cctv.parquet` |
| **เฟิร์ม** | [@nontaphatfirm](https://github.com/nontaphatfirm) | `03_cv_yolo_pipeline/` | `feat/03-cv-yolo-pipeline` | `data/vehicle_counts_sample.parquet`, `data/vehicle_counts.parquet` |
| **สอง** | [@theme222](https://github.com/theme222) | `04_ds_traffic_analytics/` | `feat/04-ds-traffic-analytics` | `data/analytics_traffic_metrics.parquet`, `data/camera_clusters_pca.parquet` |
| **สอง, เฟิร์ม** | [@theme222](https://github.com/theme222), [@nontaphatfirm](https://github.com/nontaphatfirm) | `05_ds_ml_forecasting/` | `feat/05-ds-ml-forecasting` | `data/ml_forecast_predictions.parquet`, `data/ml_shap_importance.parquet`, `models/lgbm_congestion_forecaster.txt` |
| **โม่** | [@moaqilo](https://github.com/moaqilo) | `06_bi_dashboard/` | `feat/06-bi-dashboard` | `06_bi_dashboard/src/app.py` (Streamlit 4-Tab Application) |
| **นิว (Flex Support)** | [@Pranithi-New](https://github.com/Pranithi-New) | Any module (`01_`-`06_`) | `feat/<module>-support` | Co-develops, fills gaps, and joins priority modules |

---

## 2. Git Branching & Pull Request Workflow

1. **Create Your Feature Branch:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feat/01-scraping-apis
   ```
2. **Keep Large Binary Files Out of Git:**
   - Never commit raw images (`Dataset/`, `Dataset_Clean_V1/cctv_images/`) or heavy model checkpoints (`models/`, `runs/`, `*.pt`).
   - Compact tabular metadata (`Dataset_Clean_V1/cctv_info_cleaned.parquet`) and summary manifests can be shared via Git or team cloud storage.
3. **Validate Against `DATA_CONTRACT.md` Before Opening a PR:**
   - Run `python run_pipeline.py --check-contract` from the repository root.
   - Verify `cam_id` is `int64`.
   - Verify `timestamp` is timezone-naive `datetime64` (`datetime64[us]` or `datetime64[ns]`).
   - Confirm no unexpected `NaN` values exist in primary or join keys.

---

## 3. Coding Conventions

- **Path Resolution:** Always resolve paths relative to the repository root using `pathlib.Path`:
  ```python
  from pathlib import Path
  PROJECT_ROOT = Path(__file__).resolve().parents[2]
  ```
- **Reproducibility:** Fix random seeds (`random_state=42`) in all K-Means, PCA, and LightGBM experiments.
- **Idempotency:** Scripts inside `<module>/src/` should be runnable from the repository root via `python <module>/src/<script_name>.py` and overwrite their target output cleanly.
