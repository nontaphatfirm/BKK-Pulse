# Task 05: Short-Term Spatio-Temporal Traffic Forecasting (`GOAL.md`)

> **Assigned Role:** Member 5 — Data Science: Supervised Machine Learning & Model Explainability  
> **Source Directory:** [`src/`](src/README.md)  
> **Input Tables:**  
> - [`Dataset_Clean_V1/cctv_info_cleaned.parquet`](../Dataset_Clean_V1/cctv_info_cleaned.parquet)  
> - [`Dataset_Clean_V1/image_quality_manifest.parquet`](../Dataset_Clean_V1/image_quality_manifest.parquet)  
> - `data/vehicle_counts_sample.parquet` (Phase 0 Pilot) → `data/vehicle_counts.parquet` (Full Table 3 from Task 03)  
> - `data/external_weather_poi.parquet` (Full Table 4 from Tasks 01 & 02)  
> **Primary Output Artifacts:**  
> 1. `data/ml_forecast_predictions.parquet` *(test-set predictions comparing `y_true`, `y_pred_lgbm`, `y_pred_naive`, `delta_30m_pred`, and `traffic_alert_level`)*  
> 2. `data/ml_model_metrics.json` *(MAE, RMSE, and R² evaluation metrics overall and during rush-hour/rain transitions)*  
> 3. `data/ml_shap_importance.parquet` *(mean absolute SHAP values across features for dashboard visualization)*  
> 4. `models/lgbm_congestion_forecaster.txt` *(serialized LightGBM Booster enabling live **What-If Scenario Simulation** in Streamlit)*

---

## 1. Objective & Problem Formulation

Observing current congestion is reactive; urban traffic management requires **proactive short-term forecasting**. This module trains a **LightGBM Gradient Boosted Decision Tree Regressor** to predict each camera's **Normalized Congestion Index 30 minutes into the future (`t + 30 min`, i.e., 3 frames ahead)** by fusing autoregressive traffic lags, temporal cycles, spatial land-use POIs, and real-time weather/visibility indicators.

---

## 2. Strict Anti-Leakage & Discontinuity Rules

> [!CAUTION]
> **Mandatory Engineering Safeguard for Time-Series Lags:**  
> Because the CCTV dataset records frames at **10-minute intervals** with two major structural discontinuities, naive `.shift(k)` operations across `groupby("cam_id")` will introduce severe temporal corruption:
> 1. **Overnight Recording Gap (`21:00–06:00` daily):** No frames exist overnight. Shifting across midnight causes the `06:00` morning frame to use the previous night's `20:50` frame as its `10-minute lag`.
> 2. **Central Acquisition Outage (`2026-08-27 06:00–08:50`) & Filtered Error Frames:** All 100 cameras dropped offline until `08:51` on August 27, and 1,109 defective frames were removed by Task 00.

### Required Gap-Safe Lag Construction Protocol:
1. Sort strictly by `["cam_id", "timestamp"]` and extract `date = df["timestamp"].dt.date`.
2. Perform all `.shift()` and rolling window operations inside **`df.groupby(["cam_id", "date"])`** so no feature ever crosses midnight.
3. Explicitly validate elapsed wall-clock minutes (`delta_min = (timestamp - timestamp.shift(k)).dt.total_seconds() / 60.0`) before accepting any lag or lead value:
   - **`lag_1` (`t - 10m`):** Valid only if `7.0 <= delta_min <= 14.0 min` (else `NaN`).
   - **`lag_2` (`t - 20m`):** Valid only if `16.0 <= delta_min <= 25.0 min` (else `NaN`).
   - **`lag_3` (`t - 30m`):** Valid only if `25.0 <= delta_min <= 36.0 min` (else `NaN`).
   - **Target `y_target_t_plus_30m` (`t + 30m`, `shift(-3)`):** Valid only if `25.0 <= (t_plus3 - t_0) <= 36.0 min` (drop rows where target is `NaN`).

---

## 3. Feature Engineering & Model Architecture

### 3.1 Feature Groups (`X`)
1. **Autoregressive Traffic Dynamics:**
   - `congestion_t0`, `congestion_lag_10m`, `congestion_lag_20m`, `congestion_lag_30m`
   - `congestion_velocity_10m` (`congestion_t0 - congestion_lag_10m`)
   - `congestion_roll_mean_60m`, `congestion_roll_std_60m` (6-frame trailing window)
   - `pcu_t0`, `motorcycle_share_t0`, `foreground_ratio_t0`
2. **Cyclical & Calendar Temporal Features:**
   - `hour`, `minute`, `day_of_week`, `is_weekend`
   - Cyclical time encoding: `sin(2π * minute_of_day / 1440)`, `cos(2π * minute_of_day / 1440)`
3. **Spatial & Land-Use Context (from `cctv_info_cleaned` + Tasks 01 & 02):**
   - Categorical features: `cam_id`, `corridor`, `district`, `direction`
   - Spatial POI counts: `nearby_transit_count`, `nearby_school_count`, `nearby_mall_count`, `poi_total_count`
   - Incident hotspot counts: `traffy_complaint_count`, `traffy_flood_count`
4. **Meteorological & Visual Environment Indicators:**
   - `rain_mm`, `temp_c`, `humidity_pct`, `pm25`
   - Camera-level optical indicators: `brightness_mean`, `contrast_std`, `glare_ratio`

---

### 3.2 Chronological Train / Validation / Test Split
Never use random row shuffling (`shuffle=True`) on time-series data. Partition chronologically:
- **Training Set (Days 1–5):** `2026-08-25` through `2026-08-29`
- **Validation / Test Set (Days 6–7):** `2026-08-30` (captures weekend + heavy afternoon storm) and `2026-08-31` (full Monday commuter rush hours)

---

### 3.3 Benchmarking, Actionable Alert Tiers, What-If Model Export & SHAP Explainability
1. **Baseline Comparison (Naive Persistence Model):**
   - Define the Naive Persistence baseline as `y_naive(t + 30m) = y(t0)`.
   - Evaluate both **LightGBM** and **Naive Persistence** using **MAE**, **RMSE**, and **R²** across (a) the full test set, (b) rush-hour ramp-up transitions, and (c) active rainfall periods.
2. **Actionable Early-Warning Alert Tiers (`traffic_alert_level`):**
   - In `data/ml_forecast_predictions.parquet`, include `congestion_t0`, `delta_30m_pred` (`y_pred_lgbm - congestion_t0`), and categorical `traffic_alert_level` based on `y_pred_lgbm`:
     - `"Free Flow (<40)"`: `y_pred_lgbm < 40`
     - `"Moderate (40-74)"`: `40 <= y_pred_lgbm < 75`
     - `"Gridlock Warning (>=75)"`: `y_pred_lgbm >= 75` (triggers proactive 30-minute early warnings in Tab 1).
3. **Interactive What-If Model Serialization (`models/lgbm_congestion_forecaster.txt`):**
   - Save the trained LightGBM Booster (`model.booster_.save_model("models/lgbm_congestion_forecaster.txt")`) so the Streamlit dashboard (Task 06, Tab 3) can execute live interactive **What-If simulations** (allowing users to adjust `rain_mm`, `contrast_std`, and time-of-day sliders to see real-time 30-minute congestion shifts).
4. **Model Explainability via SHAP (`shap.TreeExplainer`):**
   - Compute SHAP values on the test set to quantify how lag features, time-of-day, rainfall (`rain_mm`), optical visibility (`contrast_std`), and surrounding POIs drive 30-minute congestion forecasts.
   - Export feature-level mean `|SHAP|` importance to `data/ml_shap_importance.parquet`.

---

## 4. Definition of Done Checklist

- [ ] Complete Batch 5 camera verification (17 cameras) in [`CAMERA_AUDIT_CHECKLIST.md`](../00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md).
- [ ] Implement gap-safe lag feature engineering and verify zero cross-day or cross-outage leakage on `data/vehicle_counts_sample.parquet`.
- [ ] Train LightGBM Regressor on the full dataset, benchmark against Naive Persistence, and save `models/lgbm_congestion_forecaster.txt`.
- [ ] Export `data/ml_forecast_predictions.parquet`, `data/ml_model_metrics.json`, and `data/ml_shap_importance.parquet`.
