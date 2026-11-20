# Task 06: Interactive BI Dashboard & Urban Intelligence Command Center (`GOAL.md`)

> **Assigned Owner:** โม่ ([@moaqilo](https://github.com/moaqilo)) *(Optional Flex Support: นิว [@Pranithi-New](https://github.com/Pranithi-New))*  
> **Role:** Business Intelligence Dashboard (Streamlit) & Data Storytelling  
> **Source Directory:** [`src/`](src/README.md)  
> **Ready Inputs on `main` Today (`V2.1`):**  
> - [`Dataset_Clean_V1/cctv_info_cleaned.parquet`](../Dataset_Clean_V1/cctv_info_cleaned.parquet), [`image_quality_manifest.parquet`](../Dataset_Clean_V1/image_quality_manifest.parquet), [`cleaning_summary.json`](../Dataset_Clean_V1/cleaning_summary.json)  
> - `data/vehicle_counts.parquet` (`60,029` rows) & `data/vehicle_counts_sample.parquet` (`2,929` rows)  
> - `data/external_weather_poi.parquet` (`16,800` rows) & `data/traffy_camera_counts.parquet` (`100` rows, 6-month structural counts)  
> - `data/camera_rois.json` (`100` ROIs) & `data/median_backgrounds/` (`200` day/night plates)  
> - `data/traffy_complaints_near_cctv.parquet` *(`70,886` rows; gitignored/Drive archive, reproducible via `fetch_traffy_geojson.py --combine-cache`)*  
> **Pending Analytical & ML Inputs (Tasks 04–05):**  
> - `data/analytics_traffic_metrics.parquet`, `data/footbridge_tidal_flow.parquet`, `data/rain_resilience_ranking.parquet`, `data/camera_clusters_pca.parquet`  
> - `data/ml_forecast_predictions.parquet`, `data/ml_model_metrics.json`, `data/ml_shap_importance.parquet`, `models/lgbm_congestion_forecaster.txt`

---

## 1. Objective & Immediate Execution Advantage

This module delivers the **4-Tab Streamlit Interactive BI Dashboard (`BKK-Pulse Command Center`)**.

> [!TIP]
> **Build Tabs 1 & 4 Against Real `V2.1` Production Data Today:**  
> **Tab 4 (BMA CCTV Network Health Audit)** and the **Tab 1 Interactive Map + Camera Inspector** can run directly on `Dataset_Clean_V1/`, `data/vehicle_counts.parquet` (`60,029` rows), `data/external_weather_poi.parquet`, and `data/median_backgrounds/` — all **100% ready on `main`**.  
> Implement a resilient `data_loader.py` layer that reads `data/vehicle_counts.parquet` (falling back to `data/vehicle_counts_sample.parquet` if missing) and gracefully awaits Task 04/05 artifacts.

---

## 2. Four-Tab Architecture & Wireframe Specification

### Tab 1: Bangkok Live Pulse Map, 30-Min Early Warning & Camera Inspector
- **Top KPI Ribbon & 30-Min Early Warning Feed:**
  - Displays Active Cameras (`100`), City-Wide Mean Congestion Index (`0-100`), Current Peak Bottleneck Camera, and an automated **Proactive 30-Minute Gridlock Alert Banner** listing intersections predicted to cross `y_pred_lgbm >= 75` (`"Gridlock Warning (>=75)"`) within the next 30 minutes.
- **Interactive Geospatial Map (`pydeck` / `plotly.express.scatter_map`):**
  - Plots all 100 cameras using `(lat, lon)` colored by `congestion_index` (`Green`: 0-39 Free Flow, `Amber`: 40-74 Moderate, `Red`: 75-100 Gridlock) with a time-of-day / date selector.
  - Optional overlay toggles for **500m OSM POIs**, **Traffy Fondue flood/traffic hotspots**, and **Camera Weather / Visibility Flags** (`low_visibility_flag`, `visual_rain_flag`, `wet_road_flag`, `rain_severity_score`).
- **Camera Drill-Down Drawer & Live YOLO Snapshot Tester:**
  - Displays bilingual metadata (`location_en`, `location_th`, `district`, `corridor`, `direction`), selected CCTV snapshot alongside its clean **Median Background plate** (plus optional live single-frame YOLO inference via [`03_cv_yolo_pipeline/src/predict_yolo26x.py`](../03_cv_yolo_pipeline/src/predict_yolo26x.py)), visual weather indicators (`visual_rain_flag`, `wet_road_flag`, `rain_severity_score`), and a time-series chart showing actual traffic vs. **LightGBM `t + 30m` forecast**.

---

### Tab 2: Corridor Shockwaves, Tidal Flow & Urban Archetypes
- **Corridor Space-Time Heatmap:**
  - Interactive corridor selector (`Ratchadaphisek`, `Phahon Yothin - Lat Phrao`, `Sathon - Naradhiwas - Rama 3`, etc.) rendering a Plotly 2D Heatmap (`X`: Time `06:00-21:00`, `Y`: Ordered Cameras along Corridor, `Color`: `congestion_index`) to visualize congestion shockwave propagation.
- **Macro & Micro Tidal Flow Analyzer (Reversible Lane Advisor + CSV Policy Export):**
  - Macro comparison curve of **24 `Inbound`** vs. **18 `Outbound`** directional cameras across the week *(`V2.1` counts after excluding `58` `"None"` cameras — always filter `direction.isin(["Inbound", "Outbound"])` dynamically)*.
  - Micro spotlight on the **6 Bidirectional Footbridge Pairs (`footbridge_bidirectional`)** (`136/137`, `178/179`, `126/127`, `224/225`, `176/177`, `1132/1078`), displaying the **Tidal Imbalance Index**, automated policy callouts indicating exact time windows (`abs(tidal_imbalance) > 0.40`) to deploy a **Reversible Lane**, and a downloadable **BMA Reversible Lane Schedule (`.csv`)**.
- **Unsupervised Road Archetype Explorer (K-Means + PCA):**
  - Interactive 2D PCA scatter plot and cluster profile **Radar Chart** comparing the 4 behavioral archetypes against surrounding 500m OSM POI densities.

---

### Tab 3: Weather Vulnerability, Interactive What-If Simulator & ML Explainability
- **CV Rain / Wet-Road Detection & Recovery Time Leaderboard:**
  - Event timeline comparing dry baseline (`mu_dry`) vs. storm/wet-road congestion alongside Open-Meteo `rain_mm` and camera-level CV weather indicators (`visual_rain_flag`, `wet_road_flag`, `rain_severity_score`, plus side-by-side CCTV evidence frames showing dry vs. active storm haze vs. wet-road reflection).
  - Ranked table of the **Top 10 Rain-Vulnerable Intersections** with recovery duration in minutes (`tau_recovery_min`) and nearby **6-month Traffy Fondue flood hotspot counts** (from `data/traffy_camera_counts.parquet` / `data/rain_resilience_ranking.parquet`).
- **Interactive LightGBM What-If Scenario Simulator (`models/lgbm_congestion_forecaster.txt`):**
  - Allows city planners to select any camera and adjust interactive sliders for **Rainfall Intensity (`rain_mm`: 0-30 mm/hr)**, **Optical Visibility / Rain Severity (`contrast_std`, `rain_severity_score`)**, **Current Congestion (`congestion_t0`)**, and **Time of Day** to simulate in real time how the **30-minute ahead congestion forecast (`t + 30m`)** responds compared to dry baseline conditions.
- **LightGBM `t + 30m` Evaluation Scorecard, SHAP Attribution & City-Wide Air Quality Context:**
  - Scorecard comparing **LightGBM vs. Naive Persistence Baseline** (`MAE`, `RMSE`, `R2` overall, during rush hours, and during rainfall/wet-road events), interactive **SHAP Feature Importance** bar/dependence charts, and city-wide hourly temporal comparison of heavy vehicles (`bus_count + truck_count`) against regional `NO2`/`PM2.5` cycles.

---

### Tab 4: BMA CCTV Network Health & Infrastructure Audit *(Data 100% Ready on `main`!)*
- **Network Quality Gate KPIs (`61,319` Total Inspected Frames — `V2.1` Final Lock):**
  - Valid Operational Frames (`valid`): **`60,029` (`97.90%`)** *(`0` remaining `quality_warning` frames across all 100 cameras)*
  - Frozen Stream Buffers (`frozen`): **`553` (`0.90%`)**
  - Blank White Sensor Drops (`white_error`): **`504` (`0.82%`)**
  - Peer QA Manual Exclusions (`manual_excluded`): **`181` (`0.30%`)**
  - RTSP Pipeline Crashes (`no_signal_error` Rainbow): **`33` (`0.05%`)**
  - Codec / YUV Corruptions (`corrupt_color` -- 11 Gray P-Frame, 8 Green Screen): **`19` (`0.03%`)**
- **System-Wide Outage Timeline:**
  - Hourly stacked bar/heatmap of frame availability highlighting the **August 27, 2026 (`06:00-08:50`) central acquisition blackout** across all 100 cameras (and exposing Camera `150`'s frozen overnight buffer).
- **Priority Maintenance Dispatch Table & Exportable Ticket List:**
  - Ranks cameras by `error_image_count` and `valid_rate_pct` from `cctv_info_cleaned.parquet`:
    - **Cam `150` (Samsenwittayalai School):** 124 frozen + 4 white = 128 errors (`79.71%` valid rate)
    - **Cam `206` (Soi Naradhiwas 20):** 95 frozen + 4 corrupt + 4 white + 6 manual = 109 errors (`82.13%` valid rate)
    - **Cam `938` (Ramkhamhaeng - Rama 9):** 98 frozen + 7 white = 105 errors (`82.84%` valid rate)
    - **Cam `939` (Mahadthai Intersection):** 95 frozen + 10 white = 105 errors (`82.87%` valid rate)
    - **Cam `500` (Pratu Nam Intersection):** 78 manual + 7 white + 6 corrupt = 91 errors (`85.15%` valid rate)
    - **Cam `395` (Sao Chingcha):** 72 frozen + 6 white = 78 errors + non-standard `348 x 261` resolution (`87.30%` valid rate)
    - **Cams `432` & `1804`:** 17 and 16 rainbow `gst-launch-0.10` signal-loss frames
  - Includes **IP Subnet (`ip_subnet`) failure rate breakdown**, a visual gallery of the 4 anomaly classes, and a one-click **"Download BMA Maintenance Dispatch Ticket (`.csv`)"** button.

---

## 3. Definition of Done Checklist

- [x] Complete Batch 6 camera verification (16 cameras) in [`CAMERA_AUDIT_CHECKLIST.md`](../00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md).
- [ ] Build the Streamlit multi-tab application shell, **Tab 4 (Network Health Audit)**, and **Tab 1 (Live Map + Camera Inspector)** against `V2.1` `Dataset_Clean_V1/`, `data/vehicle_counts.parquet`, and `data/external_weather_poi.parquet`.
- [ ] Implement `data_loader.py` with DuckDB / Parquet caching (`@st.cache_data`) and automatic fallback to `vehicle_counts_sample.parquet`.
- [ ] Integrate downstream analytical and ML artifacts (`data/analytics_traffic_metrics.parquet`, `footbridge_tidal_flow.parquet`, `rain_resilience_ranking.parquet`, `camera_clusters_pca.parquet`, `ml_forecast_predictions.parquet`, `ml_shap_importance.parquet`, `models/lgbm_congestion_forecaster.txt`) from Tasks 04–05 into Tabs 1, 2, and 3.
