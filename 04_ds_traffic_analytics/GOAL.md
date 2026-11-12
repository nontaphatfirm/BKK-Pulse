# Task 04: Spatio-Temporal Traffic Analytics, Weather Resilience & Road Clustering (`GOAL.md`)

> **Assigned Owner:** สอง ([@theme222](https://github.com/theme222)) *(Optional Flex Support: นิว [@Pranithi-New](https://github.com/Pranithi-New))*  
> **Role:** Data Science -- Traffic Engineering Analytics & Unsupervised Learning  
> **Source Directory:** [`src/`](src/README.md)  
> **Input Tables & Images:**  
> - [`Dataset_Clean_V1/cctv_info_cleaned.parquet`](../Dataset_Clean_V1/cctv_info_cleaned.parquet)  
> - [`Dataset_Clean_V1/image_quality_manifest.parquet`](../Dataset_Clean_V1/image_quality_manifest.parquet)  
> - `Dataset_Clean_V1/cctv_images/` *(optional direct input if CV rain/wet-road extraction runs in Task 04)*  
> - `data/vehicle_counts_sample.parquet` *(Phase 0 Pilot)* -> `data/vehicle_counts.parquet` *(Full Table 3 from Task 03)*  
> - `data/external_weather_poi.parquet` *(Full Table 4 from Tasks 01 & 02)*  
> **Primary Output Artifacts (Consumed by Tasks 05 & 06):**  
> 1. `data/analytics_traffic_metrics.parquet` *(frame-level normalized `congestion_index` 0-100, `low_visibility_flag`, `visual_rain_flag`, `wet_road_flag`, and `rain_severity_score`)*  
> 2. `data/footbridge_tidal_flow.parquet` *(macro 80-camera & micro 6-footbridge-pair tidal imbalance metrics)*  
> 3. `data/rain_resilience_ranking.parquet` *(pre/during/post-rain congestion deltas & recovery durations in minutes)*  
> 4. `data/camera_clusters_pca.parquet` *(K-Means `k=4` behavioral archetypes, 2D PCA coordinates & cluster profiles)*

---

## 1. Objective & Analytical Scope

This module translates raw Computer Vision detections, cleaned CCTV imagery, and urban context variables into **four Data Science & Traffic Engineering deliverables**:

1. **Per-Camera P95 Normalized Congestion Index (0-100):** Eliminates camera mounting height and focal-length bias -- while adapting to nighttime headlight glare and heavy rain -- so all 100 intersections can be compared on a unified congestion scale.
2. **Corridor Shockwave Propagation & Tidal Flow Analysis:** Visualizes congestion waves along Bangkok's major arterial corridors and evaluates directional asymmetry (`Inbound` vs. `Outbound`) to recommend **Reversible Lane (Contraflow)** operations.
3. **Camera-Level Rain & Wet-Road Detection (CV Image Processing) & Recovery Analysis:** Derives weather and wet-pavement signals directly from CCTV imagery alongside coarse meteorological grids (`Open-Meteo`) so downstream analyses can separate active storms from post-rain wet/flooded road slowdowns, track localized rain events, and rank recovery times.
4. **Unsupervised Urban Traffic Archetype Clustering (K-Means + PCA):** Groups the 100 cameras into **4 distinct behavioral archetypes** and correlates cluster membership with surrounding 500m land-use POIs.

---

## 2. Technical Specifications & Formulations

### Module 2.1: Standardized PCU, Adaptive Low-Light/Glare Density & Per-Camera P95 Congestion Index

1. **Passenger Car Unit (`pcu_score`):**

   ```text
   PCU[i, t] = 1.0 * Car[i, t] + 0.33 * Motorcycle[i, t] + 2.5 * Bus[i, t] + 2.5 * Truck[i, t]
   ```

2. **Optical Low-Visibility & Glare Detection (`low_visibility_flag`):**  
   As highlighted in [`Info/2110403_2026s1_Project_CEDT.pdf`](../Info/2110403_2026s1_Project_CEDT.pdf) (Slide 5), nighttime headlight bloom (`glare_ratio > 0.05`), low light (`hour >= 18` or `brightness_mean < 60.0`), and heavy rain blur (`contrast_std < 30.0`) reduce YOLO bounding-box recall while pixel foreground differences (`foreground_ratio`) still capture vehicle queues and headlight beams:

   ```python
   low_visibility_flag = (
       (df["hour"] >= 18)
       | (df["brightness_mean"] < 60.0)
       | (df["glare_ratio"] > 0.05)
       | (df["contrast_std"] < 30.0)
   )
   ```

3. **Adaptive Composite Spatial Density (`composite_density`):**  
   Blend YOLO `road_occupancy_ratio` (`rho_bbox`) with Median Background `foreground_ratio` (`rho_fg`) using visibility-aware weights:

   ```text
   if low_visibility_flag[i, t] == False:   # Clear Daytime
       composite_density[i, t] = 0.7 * rho_bbox[i, t] + 0.3 * rho_fg[i, t]
   else:                                    # Night / Glare / Heavy Rain
       composite_density[i, t] = 0.4 * rho_bbox[i, t] + 0.6 * rho_fg[i, t]
   ```

4. **Per-Camera P95 Normalization (`congestion_index` in 0-100):**  
   Normalize each camera's `composite_density` against its own 95th percentile (`P95`) across the 7-day observation window:

   ```text
   congestion_index[i, t] = clip((composite_density[i, t] / P95(composite_density[i])) * 100.0, 0.0, 100.0)
   ```

Export `pcu_score`, `composite_density`, `congestion_index`, `low_visibility_flag`, `visual_rain_flag`, `wet_road_flag`, and `rain_severity_score` to `data/analytics_traffic_metrics.parquet`.

---

### Module 2.2: Corridor Shockwaves & Bidirectional Tidal Flow Analysis

1. **Corridor Space-Time Heatmaps:**
   - Order cameras geographically along major corridors defined in `cctv_info_cleaned.parquet` (e.g., `Ratchadaphisek` ordered South-to-North: Rama 9 `1815` -> Thiam Ruam Mit `112` -> Huai Khwang `215` -> Sutthisan `118/119` -> Lat Phrao `123/125` -> Criminal Court `224/225`).
   - Construct space-time matrices (`X`: 10-min intervals `06:00-21:00`; `Y`: ordered corridor cameras; `Value`: `congestion_index`) to reveal backward-propagating traffic shockwaves.
2. **Macro Directional Flow (80 Directional Cameras):**
   - Compare aggregate hourly profiles of all **51 `Inbound`** vs. **29 `Outbound`** cameras across weekdays vs. weekends.
3. **Micro Spotlight on the 6 True Bidirectional Footbridge Pairs (`footbridge_bidirectional`):**
   - Analyze the 6 opposite-facing footbridge camera pairs:
     1. `FB_01_LatPhrao_BigC` (`137` Inbound vs. `136` Outbound -- Big C Extra Lat Phrao)
     2. `FB_02_Phyathai2` (`178` Inbound vs. `179` Outbound -- Phyathai 2 Hospital, Phahon Yothin)
     3. `FB_03_Ratchada30` (`126` Inbound vs. `127` Outbound -- Soi Ratchadaphisek 30)
     4. `FB_04_CriminalCourt` (`224` Inbound vs. `225` Outbound -- Criminal Court, Ratchadaphisek)
     5. `FB_05_ChatuchakPark` (`176` Inbound vs. `177` Outbound -- Chatuchak Park, Phahon Yothin)
     6. `FB_06_WatSuwan` (`1132` Inbound vs. `1078` Outbound -- Wat Suwan, Charoen Nakhon)
   - Compute the **Tidal Imbalance Index** (range `-1.0` to `+1.0`):

     ```text
     tidal_imbalance[p, t] = (congestion_inbound[t] - congestion_outbound[t])
                             / (congestion_inbound[t] + congestion_outbound[t] + epsilon)
     ```

   - Identify candidate time windows where `abs(tidal_imbalance) > 0.40` (severe congestion in one direction while the opposing direction remains under-utilized) to formulate **Reversible Lane policy recommendations**.

---

### Module 2.3: CCTV Image-Processing Rain & Wet-Road Detection and Recovery Analysis

#### Why Image Processing Is Needed Alongside Weather APIs
- **Coarse Weather Grid Limitation:** Open-Meteo reanalysis operates on a ~9-11 km (`0.1 deg`) spatial grid (`5` cells across our 100 cameras), missing hyper-local tropical storms. For example, at Camera `529` on August 30 at `16:05`, heavy rain haze drops `contrast_std` to `~25.0` while city-center grid cells report only `1.5 mm`.
- **Daytime Contrast-Only Limitation:** Simple rules based only on global `contrast_std` during daytime (`07:00-18:00`) miss two critical conditions observed in the dataset:
  1. **Post-rain wet/flooded pavement:** Immediately after rain eases (e.g., Camera `529` at `16:25`), `contrast_std` rebounds to normal (`~48.7`) even though asphalt remains soaked with strong specular vehicle reflections.
  2. **Global sky glare & evening rain (`18:00-21:00`):** Bright overcast upper skies trigger high full-frame `glare_ratio` on dry afternoons (e.g., Camera `529` at `14:45`), while rain/wet roads after `18:00` require road-zone optical cues.

#### Goal & Required Outcomes (What Must Be Produced for Downstream Analysis)
Regardless of the specific algorithm chosen, the CCTV image-processing rain pipeline must inspect camera frames (combined optionally with `image_quality_manifest.parquet` and `rain_mm`) to produce **three camera-level analytical signals** at 10-minute frame resolution:

1. **`visual_rain_flag` (`bool`):** Optical evidence of active rainfall, rain haze, or storm-reduced visibility at camera `i` and timestamp `t` (extending beyond coarse API grid resolution and ideally covering both daytime and evening `18:00-21:00` frames).
2. **`wet_road_flag` (`bool`):** Detection of wet asphalt, standing water, or post-rain specular reflection on the road surface, enabling downstream separation of active storm chaos vs. lingering wet-road slowdown after rain stops.
3. **`rain_severity_score` (`float64`, `0-100`):** Continuous camera-level weather severity score (`0` = dry/clear, `100` = severe tropical downpour / wet-road hazard) usable for severity-weighted statistical analysis, LightGBM forecasting (Task 05), and BI visualization (Task 06).

**Target Analyses Enabled by These Outputs:**
- **Spatio-Temporal Rain Propagation & API Cross-Check:** Map which of the 100 camera locations experienced visual rain/wet roads at each 10-minute step, compare against coarse Open-Meteo `rain_mm` grids, and cross-reference with structural flood hotspots (`traffy_flood_count` from Task 02).
- **Pre / During / Post-Rain Congestion & Recovery Quantification (`data/rain_resilience_ranking.parquet`):**
  1. **Dry Baseline (`mu_dry`):** Mean `congestion_index` at the same time-of-day on dry frames.
  2. **Rain & Wet-Road Surge (`delta_congestion_rain`):** Peak and mean `congestion_index` increase during active rain (`visual_rain_flag`) and wet-road tail windows (`wet_road_flag`) relative to `mu_dry`.
  3. **Recovery Duration (`tau_recovery_min` in minutes):** Elapsed time (in 10-minute frame increments) after rainfall stops until `congestion_index` returns within `+/- 10%` of `mu_dry`, revealing whether wet/flooded road conditions keep intersections congested long after rain ceases.
  4. **Leaderboard Export:** Rank and export the **Top 10 Rain-Vulnerable Intersections** (including `traffy_flood_count`) to `data/rain_resilience_ranking.parquet`.

#### Illustrative Example Approaches *(Optional Reference -- Implementer May Use Alternative Methods)*
**สอง** (`04`, in collaboration with **เฟิร์ม** if sharing image passes in Task 03, or **นิว** if joining CV feature work) is free to choose any image-processing or ML method that satisfies the goal above. Examples include:
- **Example A -- Multi-Cue OpenCV Feature Pipeline (Fast, CPU-only on `Dataset_Clean_V1/cctv_images/`):**
  - *Road vs. Sky ROI Masking:* Measure reflection and surface cues in the lower ~`50-65%` road zone (or Task 03's `road_roi` mask) so bright upper-sky clouds do not create false positives.
  - *Same-Hour Camera Baseline:* Normalize cues against each camera's own dry median at a matching time window (daytime vs. dusk/night).
  - *Complementary Visual Features:* Combine **contrast & edge sharpness drops** (`contrast_std`, `cv2.Laplacian` variance for rain mist/blur), **color desaturation** (HSV `S` drop during overcast rain), and **road specular highlight anomalies** (lower-ROI glare / reflection uniformity for wet roads across both day and `18:00-21:00` night scenes).
- **Example B -- Background-Residual / Rain-Streak Texture Filtering:**
  - Compare current frames against clean Median Background plates (`data/median_backgrounds/<cam_id>_bg.jpg`) using high-pass, morphological Top-Hat, or Sobel/gradient filters to detect falling rain streaks or puddle ripples.
- **Example C -- Lightweight Optical Classifier or Spatial Consensus:**
  - Train a compact supervised classifier (e.g., Logistic Regression / Random Forest / lightweight CNN) using visually verified clear vs. rainy frames to output calibrated `0-100` probabilities, optionally smoothed across nearby cameras within `1-2 km` to filter isolated lens smudges.

---

### Module 2.4: Unsupervised Camera Behavioral Clustering (K-Means + PCA)

1. **Camera-Level Feature Matrix (`100 x 6`):**
   - `morning_rush_score`: Mean weekday congestion (`07:00-09:30`)
   - `midday_score`: Mean weekday congestion (`11:00-15:00`)
   - `evening_rush_score`: Mean weekday congestion (`16:30-19:30`)
   - `weekend_weekday_ratio`: Ratio of mean weekend congestion to mean weekday congestion
   - `motorcycle_share`: Mean fraction of motorcycles (`motorcycle_count / total_vehicle_count`)
   - `heavy_vehicle_share`: Mean fraction of buses and trucks (`(bus_count + truck_count) / total_vehicle_count`)
2. **Clustering & Dimensionality Reduction:**
   - Standardize features via `StandardScaler`.
   - Fit **K-Means (`n_clusters=4`, `random_state=42`)**, evaluate **Silhouette Score**, and project onto **2D Principal Components (`pca_1`, `pca_2`)**.
   - Assign interpretable urban archetype labels (e.g., *Commuter Arterial*, *Commercial/Retail Gridlock*, *High-Motorcycle Connector*, *Heavy-Transit Corridor*) and cross-tabulate against 500m OSM POI counts (`nearby_school_count`, `nearby_mall_count`, `nearby_transit_count`).

---

## 3. Definition of Done Checklist

- [ ] Complete Batch 4 camera verification (17 cameras) in [`CAMERA_AUDIT_CHECKLIST.md`](../00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md).
- [ ] Implement Module 2.1 (`pcu_score`, adaptive `composite_density`, `P95` `congestion_index`, `low_visibility_flag`) and Module 2.3 CCTV image-processing rain & wet-road detection (`visual_rain_flag`, `wet_road_flag`, `rain_severity_score`), exporting `data/analytics_traffic_metrics.parquet`.
- [ ] Implement Module 2.2 (Corridor Space-Time matrices + macro/6-footbridge tidal flow analysis) and export `data/footbridge_tidal_flow.parquet`.
- [ ] Quantify rain/wet-road congestion surge (`delta_congestion_rain`) and recovery time (`tau_recovery_min`), exporting `data/rain_resilience_ranking.parquet`.
- [ ] Fit K-Means (`k=4`) + PCA behavioral archetypes and export `data/camera_clusters_pca.parquet`.
