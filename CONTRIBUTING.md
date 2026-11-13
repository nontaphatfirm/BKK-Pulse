# Team Contribution & Engineering Guidelines (`CONTRIBUTING.md`)

> This document establishes the Git workflow, module boundaries, and code quality standards for our 6-person team working on **BKK-Pulse**.

---

## 1. Module Ownership & Workspace Isolation

To prevent merge conflicts, each team member works inside their assigned module directories (`01_` through `06_`, with **นิว (`@Pranithi-New`)** supporting across modules as needed) and writes shared outputs to `data/` according to [`DATA_CONTRACT.md`](DATA_CONTRACT.md):

| Primary Owner(s) | GitHub | Module Folder | Dedicated Feature Branch | Primary Output Artifact(s) |
| :--- | :--- | :--- | :--- | :--- |
| **All 6 Members** | Team-wide | `00_data_cleaning_and_qa/` | `chore/00-qa-<member>` *(1 branch per member)* | `Dataset_Clean_V1/cctv_info_cleaned.parquet` |
| **ปลื้ม, กร** | [@siravidthongsook](https://github.com/siravidthongsook), [@kkooAAA](https://github.com/kkooAAA) | `01_scraping_apis/` | `feat/01-scraping-apis` | `data/weather_air_poi.parquet` |
| **ปลื้ม, กร** | [@siravidthongsook](https://github.com/siravidthongsook), [@kkooAAA](https://github.com/kkooAAA) | `02_scraping_traffy_playwright/` | `feat/02-scraping-playwright` | `data/external_weather_poi.parquet`, `data/traffy_complaints_near_cctv.parquet` |
| **เฟิร์ม** | [@nontaphatfirm](https://github.com/nontaphatfirm) | `03_cv_yolo_pipeline/` | `feat/03-cv-yolo-pipeline` | `data/vehicle_counts_sample.parquet`, `data/vehicle_counts.parquet` |
| **สอง** | [@theme222](https://github.com/theme222) | `04_ds_traffic_analytics/` | `feat/04-ds-traffic-analytics` | `data/analytics_traffic_metrics.parquet`, `data/camera_clusters_pca.parquet` |
| **สอง, เฟิร์ม** | [@theme222](https://github.com/theme222), [@nontaphatfirm](https://github.com/nontaphatfirm) | `05_ds_ml_forecasting/` | `feat/05-ds-ml-forecasting` | `data/ml_forecast_predictions.parquet`, `data/ml_shap_importance.parquet`, `models/lgbm_congestion_forecaster.txt` |
| **โม่** | [@moaqilo](https://github.com/moaqilo) | `06_bi_dashboard/` | `feat/06-bi-dashboard` | `06_bi_dashboard/src/app.py` (Streamlit 4-Tab Application) |
| **นิว (Flex Support)** | [@Pranithi-New](https://github.com/Pranithi-New) | Any module (`01_`-`06_`) | `feat/<module>-support` | Co-develops, fills gaps, and joins priority modules |

---

## 2. Git Branching & Pull Request Workflow

> [!IMPORTANT]
> **Never edit, commit, or push directly to `main`.** Every team member must create their own branch (e.g., `chore/00-qa-<your-name>` or `feat/<module>`) and open a **Pull Request (PR)** into `main` to avoid merge conflicts and overwriting teammates' work.

1. **Create Your Feature / QA Branch from `main`:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b chore/00-qa-<your-name>   # or feat/01-scraping-apis, etc.
   ```
2. **Task 00 (`00_data_cleaning_and_qa`) -- GitHub-Only Edits & Read-Only Google Drive:**
   - **Google Drive (`Dataset_Clean_V1/`) is READ-ONLY** for visual inspection only. Do **not** edit, delete, or re-upload files on Google Drive.
   - Commit fixes **only on GitHub** (via your branch & PR): update `00_data_cleaning_and_qa/src/clean_dataset_v1.py`, log in `Dataset_Clean_V1/CLEANING_CHANGELOG.md`, and check `[x]` in `00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md`.
   - Once all 6 PRs are merged into `main`, the repository maintainer runs `clean_dataset_v1.py` once and syncs the final `V2.0` dataset to Google Drive.
3. **Keep Large Binary Files Out of Git:**
   - Never commit raw images (`Dataset/`, `Dataset_Clean_V1/cctv_images/`) or heavy model checkpoints (`models/`, `runs/`, `*.pt`).
   - Compact tabular metadata (`Dataset_Clean_V1/cctv_info_cleaned.parquet`) and summary manifests can be shared via Git or team cloud storage.
4. **Validate Against `DATA_CONTRACT.md` Before Opening a PR:**
   - Run `python run_pipeline.py --check-contract` from the repository root (when updating pipeline outputs).
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
