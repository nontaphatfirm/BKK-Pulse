# Shared Canonical Data Directory (`data/`)

This directory stores the intermediate and production `.parquet` and `.json` artifacts exchanged across modules `01` through `06`. All files placed here must conform to the schemas defined in [`DATA_CONTRACT.md`](../DATA_CONTRACT.md).

---

## Artifact Catalog & Ownership

### 1. Phase 0 Baseline Artifacts (Located in [`Dataset_Clean_V1/`](../Dataset_Clean_V1/README.md))
- [`Dataset_Clean_V1/cctv_info_cleaned.parquet`](../Dataset_Clean_V1/cctv_info_cleaned.parquet) -- Canonical Table 1: Cleaned & enriched metadata for all 100 cameras.
- [`Dataset_Clean_V1/image_quality_manifest.parquet`](../Dataset_Clean_V1/image_quality_manifest.parquet) -- Canonical Table 2: Quality gate status and optical metrics for all 61,319 frames.

### 2. Phase 1 Module Artifacts (Stored in `data/`)

| File Path | Producer Module | Status | Description |
| :--- | :---: | :---: | :--- |
| `data/weather_air_poi.parquet` | `01_scraping_apis` | `Ready` | Hourly Open-Meteo weather, air quality (`PM2.5`, `NO2`, `CO`), and 500m OSM POI counts (`16,800 x 14`, `V2.1`) |
| `data/traffy_complaints_near_cctv.parquet` | `02_scraping_traffy_playwright` | `Ready (Gitignored)` | Incident-level BMA Traffy Fondue reports matched within 1 km (`70,886` rows on `V2.1`, reproducible offline via `--combine-cache`) |
| `data/traffy_camera_counts.parquet` | `02_scraping_traffy_playwright` | `Ready` | Per-camera 6-month lifetime and 7-day Traffy complaint totals (`100 x 7`, structural flood baseline for Tasks `04`/`05`/`06`) |
| `data/traffy_provenance.json` | `02_scraping_traffy_playwright` | `Ready` | Crawl completeness (`190` pages, `complete: true`) and SHA-256 provenance manifest validated by `run_pipeline.py --check-contract` |
| `data/external_weather_poi.parquet` | `01` & `02` | `Ready` | **Canonical Table 4:** Merged hourly weather, air quality, OSM POIs, and trailing 7-day as-of Traffy counts (`16,800 x 17`, `V2.1`) |
| `data/vehicle_counts_sample.parquet` | `03_cv_yolo_pipeline` | `Ready` | **Priority 1 Pilot Table:** 5-camera subset (`2,929` rows) for rapid DS/BI prototyping |
| `data/vehicle_counts.parquet` | `03_cv_yolo_pipeline` | `Ready` | **Canonical Table 3:** Full `60,029`-frame vehicle counts, PCU, and road occupancy ratios (`V2.1`) |
| `data/camera_rois.json` | `03_cv_yolo_pipeline` | `Ready` | Manually reviewed active Road ROI polygons across all `100` cameras (`camera_rois.auto_v3_backup.json` holds pre-edit auto snapshot) |
| `data/median_backgrounds/<cam_id>_bg*.jpg` | `03_cv_yolo_pipeline` | `Ready` | `200` day (`_bg.jpg`) and night (`_bg_night.jpg`) clean-road median background plates across all 100 cameras |
| `data/analytics_traffic_metrics.parquet` | `04_ds_traffic_analytics` | `Planned` | Frame-level adaptive composite density, `low_visibility_flag`, CV weather states (`visual_rain_flag`, `wet_road_flag`, `rain_severity_score`), and per-camera `P95` `congestion_index` (`0-100`) |
| `data/footbridge_tidal_flow.parquet` | `04_ds_traffic_analytics` | `Planned` | Inbound vs. Outbound profiles and 6-footbridge-pair Tidal Imbalance metrics |
| `data/rain_resilience_ranking.parquet` | `04_ds_traffic_analytics` | `Planned` | Pre/during/post-rain congestion deltas and recovery durations in minutes |
| `data/camera_clusters_pca.parquet` | `04_ds_traffic_analytics` | `Planned` | K-Means (`k=4`) camera behavioral archetypes and 2D PCA coordinates |
| `data/ml_forecast_predictions.parquet` | `05_ds_ml_forecasting` | `Planned` | Test-set 30-minute ahead predictions (`y_true`, `y_pred_lgbm`, `y_pred_naive`, `delta_30m_pred`, `traffic_alert_level`) |
| `data/ml_model_metrics.json` | `05_ds_ml_forecasting` | `Planned` | Evaluation scorecard (`MAE`, `RMSE`, `R2`) comparing LightGBM vs. Naive Persistence |
| `data/ml_shap_importance.parquet` | `05_ds_ml_forecasting` | `Planned` | Mean absolute SHAP feature importance table |
| `models/lgbm_congestion_forecaster.txt` | `05_ds_ml_forecasting` | `Planned` | Serialized LightGBM model artifact powering interactive What-If simulations in Tab 3 |
