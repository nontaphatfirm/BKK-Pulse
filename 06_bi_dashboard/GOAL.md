# Task 06: Interactive BI Dashboard & Urban Intelligence Command Center (`GOAL.md`)

> **Assigned Owner:** โม่ ([@moaqilo](https://github.com/moaqilo)) *(Optional Flex Support: นิว [@Pranithi-New](https://github.com/Pranithi-New))*  
> **Role:** Business Intelligence Dashboard (Streamlit) & Data Storytelling  
> **Source Directory:** [`src/`](src/README.md)  
> **Day-1 Ready Inputs (Available Right Now):**  
> - [`Dataset_Clean_V1/cctv_info_cleaned.parquet`](../Dataset_Clean_V1/cctv_info_cleaned.parquet)  
> - [`Dataset_Clean_V1/image_quality_manifest.parquet`](../Dataset_Clean_V1/image_quality_manifest.parquet)  
> - [`Dataset_Clean_V1/cleaning_summary.json`](../Dataset_Clean_V1/cleaning_summary.json)  
> **Downstream Analytical Inputs (From Tasks 01-05):**  
> - `data/vehicle_counts_sample.parquet` -> `data/vehicle_counts.parquet`  
> - `data/external_weather_poi.parquet` & `data/traffy_complaints_near_cctv.parquet`  
> - `data/analytics_traffic_metrics.parquet`, `data/footbridge_tidal_flow.parquet`, `data/rain_resilience_ranking.parquet`, `data/camera_clusters_pca.parquet`  
> - `data/ml_forecast_predictions.parquet`, `data/ml_model_metrics.json`, `data/ml_shap_importance.parquet`, `models/lgbm_congestion_forecaster.txt`

---

## 1. Objective & Immediate Day-1 Execution Advantage

This module delivers the **4-Tab Streamlit Interactive BI Dashboard (`BKK-Pulse Command Center`)**.

> [!TIP]
> **Start on Day 1 without waiting for YOLO or scraping:**  
> **Tab 4 (BMA CCTV Network Health Audit)** and the **Tab 1 Interactive Map Shell** rely on [`Dataset_Clean_V1/cctv_info_cleaned.parquet`](../Dataset_Clean_V1/cctv_info_cleaned.parquet) and [`Dataset_Clean_V1/image_quality_manifest.parquet`](../Dataset_Clean_V1/image_quality_manifest.parquet), which are **100% complete today**.  
> Implement a resilient `data_loader.py` layer that automatically falls back to `data/vehicle_counts_sample.parquet` (5-camera pilot) until the full 100-camera `data/vehicle_counts.parquet` arrives.

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
  - Macro comparison curve of **51 `Inbound`** vs. **29 `Outbound`** cameras across the week.
  - Micro spotlight on the **6 Bidirectional Footbridge Pairs (`footbridge_bidirectional`)** (`136/137`, `178/179`, `126/127`, `224/225`, `176/177`, `1132/1078`), displaying the **Tidal Imbalance Index**, automated policy callouts indicating exact time windows (`abs(tidal_imbalance) > 0.40`) to deploy a **Reversible Lane**, and a downloadable **BMA Reversible Lane Schedule (`.csv`)**.
- **Unsupervised Road Archetype Explorer (K-Means + PCA):**
  - Interactive 2D PCA scatter plot and cluster profile **Radar Chart** comparing the 4 behavioral archetypes against surrounding 500m OSM POI densities.

---

### Tab 3: Weather Vulnerability, Interactive What-If Simulator & ML Explainability
- **CV Rain / Wet-Road Detection & Recovery Time Leaderboard:**
  - Event timeline comparing dry baseline (`mu_dry`) vs. storm/wet-road congestion alongside Open-Meteo `rain_mm` and camera-level CV weather indicators (`visual_rain_flag`, `wet_road_flag`, `rain_severity_score`, plus side-by-side CCTV evidence frames showing dry vs. active storm haze vs. wet-road reflection).
  - Ranked table of the **Top 10 Rain-Vulnerable Intersections** with recovery duration in minutes (`tau_recovery_min`) and nearby **Traffy Fondue flood hotspot counts**.
- **Interactive LightGBM What-If Scenario Simulator (`models/lgbm_congestion_forecaster.txt`):**
  - Allows city planners to select any camera and adjust interactive sliders for **Rainfall Intensity (`rain_mm`: 0-30 mm/hr)**, **Optical Visibility / Rain Severity (`contrast_std`, `rain_severity_score`)**, **Current Congestion (`congestion_t0`)**, and **Time of Day** to simulate in real time how the **30-minute ahead congestion forecast (`t + 30m`)** responds compared to dry baseline conditions.
- **LightGBM `t + 30m` Evaluation Scorecard, SHAP Attribution & City-Wide Air Quality Context:**
  - Scorecard comparing **LightGBM vs. Naive Persistence Baseline** (`MAE`, `RMSE`, `R2` overall, during rush hours, and during rainfall/wet-road events), interactive **SHAP Feature Importance** bar/dependence charts, and city-wide hourly temporal comparison of heavy vehicles (`bus_count + truck_count`) against regional `NO2`/`PM2.5` cycles.

---

### Tab 4: BMA CCTV Network Health & Infrastructure Audit *(Build Immediately on Day 1!)*
- **Network Quality Gate KPIs (`61,319` Total Inspected Frames):**
  - Valid Operational Frames (`valid`): **`60,210` (`98.19%`)** *(plus `32` frames tagged with non-destructive `quality_warning`)*
  - Frozen Stream Buffers (`frozen`): **`553` (`0.90%`)**
  - Blank White Sensor Drops (`white_error`): **`504` (`0.82%`)**
  - RTSP Pipeline Crashes (`no_signal_error` Rainbow): **`33` (`0.05%`)**
  - Codec / YUV Corruptions (`corrupt_color` -- 11 Gray P-Frame, 8 Green Screen): **`19` (`0.03%`)**
- **System-Wide Outage Timeline:**
  - Hourly stacked bar/heatmap of frame availability highlighting the **August 27, 2026 (`06:00-08:50`) central acquisition blackout** across all 100 cameras (and exposing Camera `150`'s frozen overnight buffer).
- **Priority Maintenance Dispatch Table & Exportable Ticket List:**
  - Ranks cameras by `error_image_count` and `valid_rate_pct` from `cctv_info_cleaned.parquet`:
    - **Cam `150` (Samsenwittayalai School):** 124 frozen frames (`79.71%` valid rate)
    - **Cam `938` (Ramkhamhaeng - Rama 9):** 98 frozen frames (`82.84%`)
    - **Cam `939` (Mahadthai Intersection):** 95 frozen frames (`82.87%`)
    - **Cam `206` (Soi Naradhiwas 20):** 95 frozen + 4 corrupt color frames (`83.11%`)
    - **Cam `395` (Sao Chingcha):** 72 frozen frames + non-standard `348 x 261` resolution (`87.30%`)
    - **Cams `432` & `1804`:** 17 and 16 rainbow `gst-launch-0.10` signal-loss frames
  - Includes **IP Subnet (`ip_subnet`) failure rate breakdown**, a visual gallery of the 4 anomaly classes, and a one-click **"Download BMA Maintenance Dispatch Ticket (`.csv`)"** button.

---

## 3. Definition of Done Checklist

- [ ] Complete Batch 6 camera verification (16 cameras) in [`CAMERA_AUDIT_CHECKLIST.md`](../00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md).
- [ ] **Day 1:** Build the Streamlit multi-tab application shell, **Tab 4 (Network Health Audit)**, and the **Tab 1 Base Map** using `Dataset_Clean_V1/`.
- [ ] Implement `data_loader.py` with DuckDB / Parquet caching (`@st.cache_data`) and automatic fallback to `vehicle_counts_sample.parquet`.
- [ ] Integrate final Parquet artifacts and `models/lgbm_congestion_forecaster.txt` from Tasks 01-05 into Tabs 1, 2, and 3.
