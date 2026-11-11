# Task 02: Interactive Web Scraping of BMA Traffy Fondue (`GOAL.md`)

> **Assigned Role:** Member 2 — Interactive Web Scraping & Spatial Incident Matching  
> **Source Directory:** [`src/`](src/README.md)  
> **Input Tables:** [`Dataset_Clean_V1/cctv_info_cleaned.parquet`](../Dataset_Clean_V1/cctv_info_cleaned.parquet) and `data/weather_air_poi.parquet` (from Task 01)  
> **Primary Output Artifacts:**  
> 1. `data/traffy_complaints_near_cctv.parquet` *(incident-level table for map overlays)*  
> 2. `data/external_weather_poi.parquet` *(canonical Table 4 combining Tasks 01 & 02 per [`DATA_CONTRACT.md`](../DATA_CONTRACT.md))*

---

## 1. Objective & Course Rubric Alignment

This module satisfies the **Interactive Web Scraping Requirement (≥ 1 Interactive Website using Playwright/Selenium)** for **2110403 DSDE** by scraping citizen-reported urban infrastructure complaints from **BMA Traffy Fondue** (specifically **flooding/drainage failures**, **traffic signal malfunctions**, and **road obstructions/accidents**) and spatially linking them to our 100 CCTV cameras.

---

## 2. Technical Specifications & Scraping Architecture

### 2.1 Dual-Mode Acquisition: Playwright Browser Automation + GeoJSON Public API
To guarantee both **full credit on the Playwright interactive scraping rubric** and **100% data completeness across all Bangkok districts**, implement a two-stage scraper:

1. **Interactive Playwright Scraper (`scrape_traffy_playwright.py`):**
   - Launch headless/headed Chromium via `playwright.sync_api` or `playwright.async_api`.
   - Navigate to the BMA Traffy Fondue interactive dashboard / search portal.
   - Automate DOM interactions: wait for dynamic JavaScript rendering (`page.wait_for_load_state("networkidle")`), apply category/district filters, intercept background XHR/fetch JSON payloads (`page.on("response", ...)`), and capture **automated browser screenshots** for the project presentation slide deck.
2. **Public GeoJSON / REST Endpoint Backfill (`fetch_traffy_geojson.py`):**
   - Query the BMA Traffy Fondue public GeoJSON API (`https://publicapi.traffy.in.th/teamchadchart-stat-api/geojson/v1?output_format=json`) or official CSV dump (`https://publicapi.traffy.in.th/dump-csv-chadchart/bangkok_traffy.csv`) to ensure complete spatial coverage across all 100 camera locations.
   - **Verified API Behavior & Anti-Truncation Rules:**
     - The GeoJSON endpoint redirects to `api.traffy.in.th`, enforces a **300-feature cap per response** (`len(features) <= 300`, sorted newest-first from `end`), and requires `timeout >= 30` seconds.
     - Query by problem category (`problem_type=น้ำท่วม`, `ท่อระบายน้ำ`, `จราจร`, `ถนน`) across date chunks (or stream-filter the official CSV dump) and cache raw responses locally in `data/raw_traffy_cache/`.
   - Filter complaints into two primary operational categories:
     - **Flood & Drainage (`flood`):** Flooding (`น้ำท่วม`), drainage blockage (`ท่อระบายน้ำ`), water retention.
     - **Traffic & Road Infrastructure (`traffic`):** Traffic congestion (`จราจร`), traffic light failure (`ไฟจราจร`), road surface hazards (`ถนน`), accidents/obstructions (`กีดขวาง`, `อุบัติเหตุ`).

---

### 2.2 Spatial-Temporal Matching & Monsoon Hotspot Density Strategy
1. **Haversine Spatial Matching:**
   - Compute the Haversine distance between every scraped complaint coordinate `(lat, lon)` and the 100 camera coordinates in [`Dataset_Clean_V1/cctv_info_cleaned.parquet`](../Dataset_Clean_V1/cctv_info_cleaned.parquet).
   - Retain complaints falling within **≤ 500 m** (or **≤ 1,000 m** for corridor-level flooding) of each camera.
2. **Dual Temporal Strategy (Solving 7-Day Sparsity):**
   - *Verified Sparsity Finding:* Across all of Bangkok, a single 7-day window (`2026-08-25` to `2026-08-31`) contains only ~50 flood reports city-wide, meaning naive 7-day filtering within 500m of our 100 cameras would leave >90% of cameras with `0` complaints.
   - **Required Implementation:** Scrape a **multi-month monsoon baseline (e.g., May–October 2026 / 6-month window)** within 500m–1,000m of each camera so every camera receives a meaningful **structural vulnerability hotspot count** (`traffy_complaint_count`, `traffy_flood_count`, `traffy_traffic_count`), modulated by hourly/daily profile during `2026-08-25` – `2026-08-31` when active reports exist. This makes cross-referencing against Task 04's **Top 10 Rain-Vulnerable Intersections** statistically informative and practically useful for BMA planners.

---

## 3. Deliverable Schemas

### Deliverable 1: `data/traffy_complaints_near_cctv.parquet` (Incident-Level Table for Dashboard Maps)

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `ticket_id` | `string` | Unique Traffy Fondue ticket identifier |
| `nearest_cam_id` | `int64` | Nearest CCTV camera ID (matching `cctv_info_cleaned.parquet`) |
| `distance_m` | `float64` | Haversine distance to the nearest camera in meters |
| `timestamp` | `datetime64[us]` | Incident report timestamp |
| `problem_type` | `string` | Normalized category (`"flood"`, `"traffic"`, `"other"`) |
| `description` | `string` | Raw citizen complaint text |
| `status` | `string` | Resolution status (e.g., `"เสร็จสิ้น"`, `"กำลังดำเนินการ"`) |
| `lat` | `float64` | Incident latitude (WGS84) |
| `lon` | `float64` | Incident longitude (WGS84) |

### Deliverable 2: `data/external_weather_poi.parquet` (Merged Canonical Table 4)
Merge hourly aggregated counts (`traffy_complaint_count`, `traffy_flood_count`, `traffy_traffic_count`) into Member 1's `data/weather_air_poi.parquet` so that all 17 columns specified in [`DATA_CONTRACT.md`](../DATA_CONTRACT.md) are present and zero-filled (`0`) where no complaints occurred.

---

## 4. Definition of Done Checklist

- [ ] Complete Batch 2 camera verification (16 cameras) in [`CAMERA_AUDIT_CHECKLIST.md`](../00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md).
- [ ] Implement Playwright interactive scraper in `02_scraping_traffy_playwright/src/` and save execution screenshots.
- [ ] Generate `data/traffy_complaints_near_cctv.parquet` with Haversine distance matching.
- [ ] Merge with Task 01 output to produce the final `data/external_weather_poi.parquet` conforming to [`DATA_CONTRACT.md`](../DATA_CONTRACT.md).
