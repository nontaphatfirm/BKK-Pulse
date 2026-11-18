# Task 02: Interactive Web Scraping of BMA Traffy Fondue (`GOAL.md`)

> **Assigned Owners:** ปลื้ม ([@siravidthongsook](https://github.com/siravidthongsook)) & กร ([@kkooAAA](https://github.com/kkooAAA)) *(Optional Flex Support: นิว [@Pranithi-New](https://github.com/Pranithi-New))*  
> **Role:** Interactive Web Scraping & Spatial Incident Matching  
> **Source Directory:** [`src/`](src/README.md)  
> **Input Tables:** [`Dataset_Clean_V1/cctv_info_cleaned.parquet`](../Dataset_Clean_V1/cctv_info_cleaned.parquet) and `data/weather_air_poi.parquet` (from Task 01)  
> **Primary Output Artifacts:**  
> 1. `data/traffy_complaints_near_cctv.parquet` *(incident-level table for map overlays)*  
> 2. `data/external_weather_poi.parquet` *(canonical Table 4 combining Tasks 01 & 02 per [`DATA_CONTRACT.md`](../DATA_CONTRACT.md))*

---

## 1. Objective & Course Rubric Alignment

This module satisfies the **Interactive Web Scraping Requirement (>= 1 Interactive Website using Playwright/Selenium)** for **2110403 DSDE** by scraping citizen-reported urban infrastructure complaints from **BMA Traffy Fondue** (specifically **flooding/drainage failures**, **traffic signal malfunctions**, and **road obstructions/accidents**) and spatially linking them to our 100 CCTV cameras.

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
   - **Implementation note (verified 2026-11-12):** the GeoJSON URL now redirects to `https://api.traffy.in.th/postgrest/rpc/get_bkk_geojson_feed` (the same endpoint the Playwright scraper sees the dashboard call), which allows `p_limit` up to 2,000 with `p_offset` paging. The CSV dump URL returns 404, and `problem_type` combined with `start`/`end` returns zero features, so the backfill pages by date window and classifies categories client-side. Raw pages are cached under `data/raw_traffy_cache/pages/` (gitignored).
   - Filter complaints into two primary operational categories:
     - **Flood & Drainage (`flood`):** Flooding (`น้ำท่วม`), drainage blockage (`ท่อระบายน้ำ`), water retention.
     - **Traffic & Road Infrastructure (`traffic`):** any Traffy type containing `จราจร`, `ถนน`, `กีดขวาง` or `อุบัติเหตุ` (`classify()` in `fetch_traffy_geojson.py`; flood is checked first). *As implemented, this bucket is dominated by traffic violations / illegal parking (`ผิดกฎจราจร`) and road-surface reports (`ถนน`); obstructions and accidents are a small share. It is not a congestion measure.*

---

### 2.2 Spatial-Temporal Matching & Monsoon Hotspot Density Strategy
1. **Haversine Spatial Matching:**
   - Compute the Haversine distance between every scraped complaint coordinate `(lat, lon)` and the 100 camera coordinates in [`Dataset_Clean_V1/cctv_info_cleaned.parquet`](../Dataset_Clean_V1/cctv_info_cleaned.parquet).
   - *Implemented:* assign every complaint to its **single nearest camera** and keep it only if that distance is **`<= 1,000 m`** (`MATCH_RADIUS_M`). Each complaint is counted once; it is *not* counted for every camera within 1 km (~72% of matched complaints are within 1 km of two or more cameras).
2. **Dual Temporal Strategy (Solving 7-Day Sparsity):**
   - *Verified Sparsity Finding:* Across all of Bangkok, a single 7-day window (`2026-08-25` to `2026-08-31`) contains only ~50 flood reports city-wide, meaning naive 7-day filtering within 500m of our 100 cameras would leave >90% of cameras with `0` complaints.
   - **Required Implementation:** Scrape a **multi-month monsoon baseline (e.g., May-October 2026 / 6-month window)** within 500m-1,000m of each camera so every camera receives a meaningful **structural vulnerability hotspot count** (`traffy_complaint_count`, `traffy_flood_count`, `traffy_traffic_count`), modulated by hourly/daily profile during `2026-08-25` to `2026-08-31` when active reports exist. This makes cross-referencing against Task 04's **Top 10 Rain-Vulnerable Intersections** statistically informative and practically useful for BMA planners.

---

### 2.3 Implemented Playwright Interaction Flow
`scrape_traffy_playwright.py` drives `https://bangkok.traffy.in.th/`: it waits for the map to render, picks two districts from the district dropdown (`เขตจตุจักร`, `เขตดินแดง`), opens the advanced filter (`ตัวกรองขั้นสูง`), toggles the `น้ำท่วม`, `ถนน` and `ผิดกฎจราจร` categories, and opens the `สถิติ` tab. Each filter fires a filtered `get_bkk_geojson_feed` XHR, which the scraper intercepts and parses. Outputs in `artifacts/`: step screenshots (`01_initial.png`, `02_district_*.png`, `03_category_*.png`, `04_stats.png`), `playwright_filtered_complaints.json`, `network_capture.json`, and `playwright_scrape_log.json`.

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
| `type_raw` | `string` | Original Traffy problem type text (before normalization) |

Matching uses a `1,000 m` radius; each complaint is assigned to its single nearest camera (no double counting). Per-camera totals in Table 4 therefore sum to this table's row count. Rebuild after any camera re-pin in `cctv_info_cleaned.parquet`, because nearest-camera assignment depends on the coordinates.

### Deliverable 2: `data/external_weather_poi.parquet` (Merged Canonical Table 4)
Merge hourly aggregated counts (`traffy_complaint_count`, `traffy_flood_count`, `traffy_traffic_count`) into Task 01's `data/weather_air_poi.parquet` (**ปลื้ม** & **กร**) so that all 17 columns specified in [`DATA_CONTRACT.md`](../DATA_CONTRACT.md) are present and zero-filled (`0`) where no complaints occurred.

> [!NOTE]
> The three `traffy_*_count` columns in Table 4 are **6-month (May-Oct 2026) structural hotspot totals per camera** -- the same value in all 168 hours. Do not treat them as hourly features.

### Companion: `data/traffy_hourly_week.parquet` (In-Week Hourly Profile)
Hourly complaint activity during the CCTV week, on the same `(cam_id, timestamp)` key as Table 4 (`16,800` rows, zero-filled), for modules that need the temporal profile:

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `cam_id` | `int64` | Camera ID |
| `timestamp` | `datetime64[us]` | Hour (`2026-08-25 00:00` to `2026-08-31 23:00`) |
| `traffy_complaint_count_1h` | `int64` | Complaints assigned to this camera (nearest, `<= 1 km`) whose report timestamp falls in that hour (`timestamp.floor("h")`) |
| `traffy_flood_count_1h` | `int64` | Flood / drainage subset in that hour |
| `traffy_traffic_count_1h` | `int64` | `traffic` subset (mostly violations / road surface -- see Section 2.1) in that hour |

---

## 4. Definition of Done Checklist

- [x] Complete Batch 2 camera verification (16 cameras) in [`CAMERA_AUDIT_CHECKLIST.md`](../00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md).
- [x] Implement Playwright interactive scraper in `02_scraping_traffy_playwright/src/` and save execution screenshots.
- [x] Generate `data/traffy_complaints_near_cctv.parquet` with Haversine distance matching.
- [x] Merge with Task 01 output to produce the final `data/external_weather_poi.parquet` conforming to [`DATA_CONTRACT.md`](../DATA_CONTRACT.md).
