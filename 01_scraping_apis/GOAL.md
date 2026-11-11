# Task 01: Multi-Source Urban Context Acquisition via Simple APIs (`GOAL.md`)

> **Assigned Role:** Member 1 — Web Scraping & Spatial API Engineering  
> **Source Directory:** [`src/`](src/README.md)  
> **Input Table:** [`Dataset_Clean_V1/cctv_info_cleaned.parquet`](../Dataset_Clean_V1/cctv_info_cleaned.parquet) (`cam_id`, `lat`, `lon`, `district`, `corridor`)  
> **Primary Output Artifact:** `data/weather_air_poi.parquet` *(merged with Task 02 to form `data/external_weather_poi.parquet` per [`DATA_CONTRACT.md`](../DATA_CONTRACT.md))*

---

## 1. Objective & Course Rubric Alignment

This module fulfills the **Required Web Scraping Task (≥ 3 Simple APIs)** for **2110403 DSDE** by programmatically extracting environmental and spatial context across all 100 CCTV locations from **three distinct public APIs** (requiring no paid keys or credit cards):

1. **Source 1 — Open-Meteo Historical Weather API:** Hourly precipitation, rainfall, air temperature, relative humidity, and wind speed (`2026-08-25` to `2026-08-31`).
2. **Source 2 — OpenStreetMap (OSM) Overpass API:** Land-use Points of Interest (POIs) within a **500m Haversine radius** of each camera (public transit stations/stops, schools/universities, shopping malls/markets, and hospitals).
3. **Source 3 — Open-Meteo Air Quality API:** Hourly city-wide pollutant concentrations (`PM2.5`, `NO2`, and `CO`) to compare diurnal rush-hour heavy diesel traffic (`bus_count + truck_count`) against regional emission cycles.

---

## 2. Technical Specifications & Engineering Constraints

### 2.1 Source 1: Open-Meteo Historical Weather API
- **Endpoint:** `https://archive-api.open-meteo.com/v1/archive`
- **Query Parameters:**
  - `start_date=2026-08-25`, `end_date=2026-08-31`
  - `hourly=precipitation,rain,temperature_2m,relative_humidity_2m,wind_speed_10m`
  - `timezone=Asia/Bangkok`
- **Spatial Grid Resolution Note (~9–11 km, Verified):**
  - Open-Meteo reanalysis models operate at a ~9–11 km (`0.1°`) spatial grid resolution. Across our 100 cameras (`lat: 13.698–13.824`, `lon: 100.395–100.630`), rounding to `(round(lat, 1), round(lon, 1))` maps onto **5 distinct grid cells**, whereas `(round(lat, 2), round(lon, 2))` maps onto **55 coordinate pairs**.
  - Deduplicate coordinate queries by `(round(lat, 2), round(lon, 2))` (or pass comma-separated coordinates in batched requests) with a `0.3s` polite delay to avoid HTTP rate limits, then map results back to all 100 `cam_id`s.
  - Because `0.1°` (~11 km) meteorological grids cannot resolve hyper-local tropical convective rain cells on their own, downstream analyses in Task 04 fuse API `rain_mm` with camera-level optical drops (`contrast_std` and wet-road `glare_ratio` from `image_quality_manifest.parquet`) for pinpoint intersection-level rain detection.

---

### 2.2 Source 2: OpenStreetMap Overpass API (Single-BBox Query Strategy)
- **Endpoint:** `https://overpass-api.de/api/interpreter`
- **Target POI Categories (within 500m Haversine radius of each camera):**
  1. `nearby_transit_count`: BTS / MRT / ARL stations (`railway=station`, `station=subway`, `station=light_rail`) and major bus stops (`highway=bus_stop`, `public_transport=platform`).
  2. `nearby_school_count`: Schools, colleges, and universities (`amenity=school`, `amenity=university`, `amenity=college`).
  3. `nearby_mall_count`: Shopping malls, department stores, supermarkets, and markets (`shop=mall`, `shop=department_store`, `shop=supermarket`, `amenity=marketplace`).
  4. `nearby_hospital_count`: Hospitals and major clinics (`amenity=hospital`, `amenity=clinic`).

> [!IMPORTANT]
> **Anti-429 Rule (Single Bounding-Box Query):**  
> Never issue 100 separate `around:500` Overpass queries per camera—the public Overpass server will throttle and block your IP with `HTTP 429 Too Many Requests`.  
> Execute **one single Overpass QL query** covering the entire Bangkok bounding box (verified to cover 100/100 cameras):
> ```text
> BBox = (13.65, 100.35, 13.90, 100.65)   # (South, West, North, East)
> ```
> Cache the raw JSON response locally (`data/raw_osm_pois_bkk.json`), then compute vectorized **Haversine distances** in Python between all 100 cameras and extracted POI coordinates (`distance <= 500 m`).  
> Do **not** rely on OSM `lanes` tags as a road capacity denominator (>50% of Bangkok road segments lack accurate per-direction lane tags; Task 03 computes pixel-level `road_roi_area` instead).

---

### 2.3 Source 3: Open-Meteo Air Quality API
- **Endpoint:** `https://air-quality-api.open-meteo.com/v1/air-quality`
- **Query Parameters:**
  - `start_date=2026-08-25`, `end_date=2026-08-31`
  - `hourly=pm2_5,nitrogen_dioxide,carbon_monoxide`
  - `timezone=Asia/Bangkok`

> [!NOTE]
> **Regional Grid Scope (~11–40 km):**  
> Global atmospheric models (CAMS) operate on a coarse ~11–40 km grid, returning nearly identical values across Bangkok at any given hour. Do **not** use `pm25`, `no2`, or `co` to claim spatial pollution differences between individual intersections; use them strictly as **hourly city-wide temporal context** (comparing diurnal rush-hour heavy vehicle surges against regional `NO2`/`PM2.5` cycles).

---

## 3. Deliverable Schema (`data/weather_air_poi.parquet`)

Granularity: `168 hours (2026-08-25 00:00 to 2026-08-31 23:00) × 100 cameras = 16,800 rows`.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `cam_id` | `int64` | Camera ID (matching `cctv_info_cleaned.parquet`) |
| `timestamp` | `datetime64[us]` | Hourly timestamp (`YYYY-MM-DD HH:00:00`, timezone-naive) |
| `rain_mm` | `float64` | Hourly precipitation / rain (`mm`) |
| `temp_c` | `float64` | Temperature at 2m (`°C`) |
| `humidity_pct` | `float64` | Relative humidity (`%`) |
| `wind_speed_kmh` | `float64` | Wind speed at 10m (`km/h`) |
| `pm25` | `float64` | `PM2.5` concentration (`µg/m³`) |
| `no2` | `float64` | Nitrogen Dioxide `NO2` concentration (`µg/m³`) |
| `co` | `float64` | Carbon Monoxide `CO` concentration (`µg/m³`) |
| `nearby_transit_count` | `int64` | Transit nodes within 500m |
| `nearby_school_count` | `int64` | Educational institutions within 500m |
| `nearby_mall_count` | `int64` | Malls, supermarkets & markets within 500m |
| `nearby_hospital_count` | `int64` | Hospitals & clinics within 500m |
| `poi_total_count` | `int64` | Sum of all 4 POI categories within 500m |

---

## 4. Definition of Done Checklist

- [ ] Complete Batch 1 camera verification (17 cameras) in [`CAMERA_AUDIT_CHECKLIST.md`](../00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md).
- [ ] Implement weather ingestion script and cache raw API responses.
- [ ] Implement single-bbox Overpass QL ingestion script and Haversine 500m spatial join.
- [ ] Implement air quality ingestion script (`PM2.5`, `NO2`, `CO`).
- [ ] Export `data/weather_air_poi.parquet` (16,800 rows, zero `NaN` values) and coordinate with Member 2 to produce `data/external_weather_poi.parquet`.
