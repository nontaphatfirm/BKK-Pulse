# Shared Canonical Data Directory (`data/`)

This directory stores the intermediate and production `.parquet` and `.json` artifacts exchanged across modules `01` through `06`. All files placed here must conform to the schemas defined in [`DATA_CONTRACT.md`](../DATA_CONTRACT.md).

---

## Artifact Catalog & Ownership

### 1. Phase 0 Baseline Artifacts (Located in [`Dataset_Clean_V1/`](../Dataset_Clean_V1/README.md))
- [`Dataset_Clean_V1/cctv_info_cleaned.parquet`](../Dataset_Clean_V1/cctv_info_cleaned.parquet) -- Canonical Table 1: Cleaned & enriched metadata for all 100 cameras.
- [`Dataset_Clean_V1/image_quality_manifest.parquet`](../Dataset_Clean_V1/image_quality_manifest.parquet) -- Canonical Table 2: Quality gate status and optical metrics for all 61,319 frames.

### 2. Phase 1 Module Artifacts (Stored in `data/`)

| File Path | Producer Module | Description |
| :--- | :---: | :--- |
| `data/weather_air_poi.parquet` | `01_scraping_apis` | Hourly Open-Meteo weather, air quality (`PM2.5`, `NO2`, `CO`), and 500m OSM POI counts |
| `data/traffy_complaints_near_cctv.parquet` | `02_scraping_traffy_playwright` | Incident-level BMA Traffy Fondue reports matched within 500m-1km of cameras |
| `data/external_weather_poi.parquet` | `01` & `02` | **Canonical Table 4:** Merged hourly weather, air quality, OSM POIs, and Traffy hotspot counts |
| `data/vehicle_counts_sample.parquet` | `03_cv_yolo_pipeline` | **Priority 1 Pilot Table:** 5-camera subset (~3,000 rows) for immediate DS/BI development |
| `data/vehicle_counts.parquet` | `03_cv_yolo_pipeline` | **Canonical Table 3:** Full 60,210-frame vehicle counts, PCU, and road occupancy ratios |
| `data/median_backgrounds/<cam_id>_bg.jpg` | `03_cv_yolo_pipeline` | Clean-road median background plates for all 100 cameras |
| `data/analytics_traffic_metrics.parquet` | `04_ds_traffic_analytics` | Frame-level adaptive composite density, `low_visibility_flag`, CV weather states (`visual_rain_flag`, `wet_road_flag`, `rain_severity_score`), and per-camera `P95` `congestion_index` (`0-100`) |
| `data/footbridge_tidal_flow.parquet` | `04_ds_traffic_analytics` | Inbound vs. Outbound profiles and 6-footbridge-pair Tidal Imbalance metrics |
| `data/rain_resilience_ranking.parquet` | `04_ds_traffic_analytics` | Pre/during/post-rain congestion deltas and recovery durations in minutes |
| `data/camera_clusters_pca.parquet` | `04_ds_traffic_analytics` | K-Means (`k=4`) camera behavioral archetypes and 2D PCA coordinates |
| `data/ml_forecast_predictions.parquet` | `05_ds_ml_forecasting` | Test-set 30-minute ahead predictions (`y_true`, `y_pred_lgbm`, `y_pred_naive`, `delta_30m_pred`, `traffic_alert_level`) |
| `data/ml_model_metrics.json` | `05_ds_ml_forecasting` | Evaluation scorecard (`MAE`, `RMSE`, `R2`) comparing LightGBM vs. Naive Persistence |
| `data/ml_shap_importance.parquet` | `05_ds_ml_forecasting` | Mean absolute SHAP feature importance table |
| `models/lgbm_congestion_forecaster.txt` | `05_ds_ml_forecasting` | Serialized LightGBM model artifact powering interactive What-If simulations in Tab 3 |
