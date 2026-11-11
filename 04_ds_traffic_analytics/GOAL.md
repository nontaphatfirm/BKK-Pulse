# Task 04: Spatio-Temporal Traffic Analytics, Weather Resilience & Road Clustering (`GOAL.md`)

> **Assigned Role:** Member 4 — Data Science: Traffic Engineering Analytics & Unsupervised Learning  
> **Source Directory:** [`src/`](src/README.md)  
> **Input Tables:**  
> - [`Dataset_Clean_V1/cctv_info_cleaned.parquet`](../Dataset_Clean_V1/cctv_info_cleaned.parquet)  
> - [`Dataset_Clean_V1/image_quality_manifest.parquet`](../Dataset_Clean_V1/image_quality_manifest.parquet)  
> - `data/vehicle_counts_sample.parquet` (Phase 0 Pilot) → `data/vehicle_counts.parquet` (Full Table 3 from Task 03)  
> - `data/external_weather_poi.parquet` (Full Table 4 from Tasks 01 & 02)  
> **Primary Output Artifacts (Consumed by Task 06 BI Dashboard):**  
> 1. `data/analytics_traffic_metrics.parquet` *(frame-level normalized `congestion_index` 0–100, `low_visibility_flag`, `visual_rain_flag` & composite scores)*  
> 2. `data/footbridge_tidal_flow.parquet` *(macro 80-camera & micro 6-footbridge-pair tidal imbalance metrics)*  
> 3. `data/rain_resilience_ranking.parquet` *(pre/during/post-rain congestion deltas & recovery times in minutes)*  
> 4. `data/camera_clusters_pca.parquet` *(K-Means `k=4` behavioral archetypes, PCA 2D coordinates & cluster profiles)*

---

## 1. Objective & Analytical Scope

This module translates raw computer vision outputs and urban context variables into **four rigorous Data Science & Traffic Engineering analyses**:

1. **Per-Camera P95 Normalized Congestion Index (`0–100`):** Eliminates camera mounting height and focal-length bias—while adapting to nighttime headlight glare and heavy rain—so all 100 intersections can be compared on a unified congestion scale.
2. **Corridor Shockwave Propagation & Tidal Flow Analysis:** Visualizes congestion waves along Bangkok's major arterial corridors and evaluates directional asymmetry (`Inbound` vs. `Outbound`) to recommend **Reversible Lane (Contraflow)** operations.
3. **Rainfall Vulnerability & Recovery Time Quantification:** Uses camera-level optical confirmation alongside meteorological grids to measure how severely heavy monsoon rainfall degrades traffic flow and how many minutes each location requires to recover.
4. **Unsupervised Urban Traffic Archetype Clustering (K-Means + PCA):** Groups the 100 cameras into **4 distinct behavioral archetypes** and correlates cluster membership with surrounding 500m land-use POIs.

---

## 2. Technical Specifications & Mathematical Formulations

### Module 2.1: Standardized PCU, Adaptive Low-Light/Glare Density & Per-Camera P95 Congestion Index

1. **Passenger Car Unit (`PCU`):**

   $$
   \text{PCU}_{i, t} = 1.0(\text{Car}_{i, t}) + 0.33(\text{Motorcycle}_{i, t}) + 2.5(\text{Bus}_{i, t}) + 2.5(\text{Truck}_{i, t})
   $$

2. **Optical Low-Visibility & Glare Detection (`low_visibility_flag`):**  
   As highlighted in the course project specification ([`Info/2110403_2026s1_Project_CEDT.pdf`](../Info/2110403_2026s1_Project_CEDT.pdf), Slide 5), nighttime headlight bloom (`glare_ratio > 0.05`), low light (`hour >= 18` or `brightness_mean < 60`), and heavy rain/wet-road blur (`contrast_std < 30`) reduce YOLO bounding-box recall while pixel foreground differences (`foreground_ratio`) remain sensitive to vehicle queues and headlight beams:
   ```python
   low_visibility_flag = (
       (df["hour"] >= 18)
       | (df["brightness_mean"] < 60.0)
       | (df["glare_ratio"] > 0.05)
       | (df["contrast_std"] < 30.0)
   )
   ```

3. **Adaptive Composite Spatial Density (`composite_density`):**  
   Combine YOLO `road_occupancy_ratio` (`ρ_bbox`) with Median Background `foreground_ratio` (`ρ_fg`) using visibility-aware weights:

   $$
   \tilde{\rho}_{i, t} = \begin{cases} 0.7 \cdot \rho^{\text{bbox}}_{i, t} + 0.3 \cdot \rho^{\text{fg}}_{i, t} & \text{if } \text{low\_visibility\_flag}_{i, t} = \text{False} \quad (\text{Clear Daytime}) \\ 0.4 \cdot \rho^{\text{bbox}}_{i, t} + 0.6 \cdot \rho^{\text{fg}}_{i, t} & \text{if } \text{low\_visibility\_flag}_{i, t} = \text{True} \quad (\text{Night / Glare / Heavy Rain}) \end{cases}
   $$

4. **Per-Camera P95 Normalization (`congestion_index` in `0–100`):**  
   Normalize each camera's composite density by its own 95th percentile (`P95`) across the 7-day observation window:

   $$
   \text{CongestionIndex}_{i, t} = \text{clip}\left(\frac{\tilde{\rho}_{i, t}}{P_{95}(\tilde{\rho}_i)} \times 100,\; 0,\; 100\right)
   $$

Export `pcu_score`, `composite_density`, `congestion_index`, `low_visibility_flag`, and `visual_rain_flag` to `data/analytics_traffic_metrics.parquet`.

---

### Module 2.2: Corridor Shockwaves & Bidirectional Tidal Flow Analysis

1. **Corridor Space-Time Heatmaps:**
   - Order cameras geographically along major corridors defined in `cctv_info_cleaned.parquet` (e.g., `Ratchadaphisek` ordered South-to-North from Rama 9 `1815` → Thiam Ruam Mit `112` → Huai Khwang `215` → Sutthisan `118/119` → Lat Phrao `123/125` → Criminal Court `224/225`).
   - Construct space-time matrices (`X`: 10-min intervals `06:00–21:00`; `Y`: ordered corridor cameras; `Value`: `CongestionIndex`) to reveal backward-propagating traffic shockwaves.
2. **Macro Directional Flow (80 Directional Cameras):**
   - Compare aggregate hourly profiles of all **51 `Inbound`** vs. **29 `Outbound`** cameras across weekdays vs. weekends.
3. **Micro Spotlight on the 6 True Bidirectional Footbridge Pairs (`footbridge_bidirectional`):**
   - Analyze the 6 opposite-facing footbridge camera pairs:
     1. `FB_01_LatPhrao_BigC` (`137` Inbound vs. `136` Outbound — Big C Extra Lat Phrao)
     2. `FB_02_Phyathai2` (`178` Inbound vs. `179` Outbound — Phyathai 2 Hospital, Phahon Yothin)
     3. `FB_03_Ratchada30` (`126` Inbound vs. `127` Outbound — Soi Ratchadaphisek 30)
     4. `FB_04_CriminalCourt` (`224` Inbound vs. `225` Outbound — Criminal Court, Ratchadaphisek)
     5. `FB_05_ChatuchakPark` (`176` Inbound vs. `177` Outbound — Chatuchak Park, Phahon Yothin)
     6. `FB_06_WatSuwan` (`1132` Inbound vs. `1078` Outbound — Wat Suwan, Charoen Nakhon)
   - Compute the **Tidal Imbalance Index**:

     $$
     \text{TidalImbalance}_{p, t} = \frac{\text{Congestion}_{\text{Inbound}, t} - \text{Congestion}_{\text{Outbound}, t}}{\text{Congestion}_{\text{Inbound}, t} + \text{Congestion}_{\text{Outbound}, t} + \epsilon}
     $$

   - Identify candidate time windows where `|TidalImbalance| > 0.40` (severe congestion in one direction while the opposing direction remains under-utilized) to formulate **Reversible Lane policy recommendations**.

---

### Module 2.3: Camera-Level Visual Rain Detection & Recovery Time Analysis

- **Camera-Level Visual Rain & Wet-Road Indicator (`visual_rain_flag`):**
  - Because Open-Meteo operates on a ~9–11 km grid (`5` unique `0.1°` cells across Bangkok), localized tropical downpours (such as Camera `529` on August 30 at `16:05`, where `contrast_std` drops to `~25.0` while city-center grid cells show only `1.5 mm`) require optical confirmation.
  - For each camera `i`, compute its dry daytime median contrast `median_dry_contrast` and flag `visual_rain_flag = True` when `rain_mm >= 0.5` OR (`contrast_std < 0.75 * median_dry_contrast` AND `7 <= hour <= 18`).
- Identify major rainfall events using `visual_rain_flag` and `rain_mm` (from Task 01), cross-referenced with structural flood hotspot counts `traffy_flood_count` (from Task 02).
- For each camera `i` during major rain events (e.g., August 30, 2026 afternoon storm):
  1. **Dry Baseline (`mu_dry`):** Mean `CongestionIndex` at the same time-of-day on dry days.
  2. **Rain Surge (`delta_congestion_rain`):** Peak/mean `CongestionIndex` increase during active rainfall relative to `mu_dry`.
  3. **Recovery Duration (`tau_recovery_min` in minutes):** Elapsed time (in 10-minute frame increments) after rainfall stops (`rain_mm == 0`) until `CongestionIndex` returns within `±10%` of `mu_dry`.
- Export the ranked **Top 10 Rain-Vulnerable Intersections** to `data/rain_resilience_ranking.parquet`.

---

### Module 2.4: Unsupervised Camera Behavioral Clustering (K-Means + PCA)

1. **Camera-Level Feature Matrix (`100 × 6`):**
   - `morning_rush_score`: Mean weekday congestion (`07:00–09:30`)
   - `midday_score`: Mean weekday congestion (`11:00–15:00`)
   - `evening_rush_score`: Mean weekday congestion (`16:30–19:30`)
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
- [ ] Implement and test all 4 analytical modules against `data/vehicle_counts_sample.parquet`.
- [ ] Re-run on full `data/vehicle_counts.parquet` and `data/external_weather_poi.parquet`.
- [ ] Export `analytics_traffic_metrics.parquet`, `footbridge_tidal_flow.parquet`, `rain_resilience_ranking.parquet`, and `camera_clusters_pca.parquet` to `data/`.
