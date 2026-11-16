# Data Cleaning Version History & Change Log (`CLEANING_CHANGELOG.md`)

> **Purpose:** Single audit trail recording every data-cleaning rule, manual metadata fix, image exclusion, and version transition from `V1.0` onward. This log keeps team collaboration transparent across Google Drive / GitHub and provides exact **Before -> After** statistics for the final project report.

---

## How to Log a Cleaning Change (Mandatory for Every Editor)

> **GitHub-Only Workflow:** Google Drive (`Dataset_Clean_V1/`) is **READ-ONLY** for visual inspection. Do **not** edit/delete/re-upload files on Drive, and do **not** commit directly to `main`. Create your own branch (`chore/00-qa-<your-name>`) and open a **Pull Request (PR)** into `main`.

Whenever you verify a batch, flag broken/corrupted frames to exclude, or edit any camera metadata field:
1. Add **one row** to the **Modification Ledger** below (so we can scan all edits at a glance).
2. Add or append a detailed subsection under **Detailed Version Log** using the copy-paste template at the bottom of this file.
3. Include **exact numbers / `cam_id` / filenames** (Before vs. After) and the **reason** so we can cite it directly in the Data Cleaning & Preparation section of the final report.
4. Apply the fix in `00_data_cleaning_and_qa/src/clean_dataset_v1.py` (`CAMERA_CURATION` for metadata or `MANUAL_EXCLUDED_IMAGES` for broken/corrupted filenames), mark `[x]` in `00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md`, and open a **PR into `main`**. *(Team members do not need to re-upload `Dataset_Clean_V1/` to Drive—the maintainer will run `clean_dataset_v1.py` and `python run_pipeline.py --check-contract` once after all 6 PRs are merged, then sync `V2.0` to Google Drive.)*

---

## Version Summary Overview

| Version | Date | Status | Raw -> Valid Images | Major Milestone |
| :--- | :---: | :---: | :---: | :--- |
| [`V1.0`](#v10----2026-11-11-initial-automated-quality-gate--metadata-cleansing) | `2026-11-11` | **Active Baseline** | `61,319 -> 60,210` (`98.19%`) | 5-Gate Image Filter, ASCII filenames, full 100-camera `CAMERA_CURATION` repair |
| `V1.1` *(Draft)* | *Pending* | Peer QA In Progress | *TBD* | Batch 1-6 peer audit corrections + decision on `32` `quality_warning` frames & Cam `370/371` |
| `V2.0` *(Planned)* | *Pending* | Planned Final Lock | *TBD* | Final locked clean dataset for production YOLO inference & final report |

---

## Modification Ledger (Team Peer-Audit & Cleaning Fixes)

*(Add a new row below every time anyone modifies or flags data during cleaning!)*

| Log ID | Date (`YYYY-MM-DD`) | Target Version | Editor (Name / GitHub) | Target `cam_id` / Scope | Issue Identified | Cleaning Action Taken | Before -> After Impact | Synced in Script? |
| :--- | :---: | :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| `CHG-001` | `2026-11-11` | `V1.0` | Automated Baseline | All `100` cams / `61,319` imgs | Blank white, rainbow, gray P-frame, green screen, frozen streams, Thai Unicode paths, `1970` OSD dates, corrupted `cctv_info.csv` | Executed 5-Gate pipeline + `CAMERA_CURATION` in `clean_dataset_v1.py` | `61,319 -> 60,210` valid images (`1,109` filtered); `100/100` metadata repaired | Yes (`clean_dataset_v1.py`) |
| `CHG-002` | *YYYY-MM-DD* | `V1.1` | *Example: ปลื้ม (@siravidthongsook)* | *e.g., `cam_id=126` or `quality_warning`* | *Describe issue observed in Drive image or CSV* | *Describe exact fix / rule / label update* | *e.g., `direction`: Inbound -> Outbound* | *No / Pending / Yes* |
| `CHG-B5-01` | `2026-11-16` | `V1.1` | นิว (`@Pranithi-New`) | `cam_id=169` (Batch 5) | `19` `partial_gray_pframe` frames (`gray128_ratio` `0.483–0.717`) plus `169_20260829_195620.jpg` (`gray128_ratio=0.348`) show massive gray P-frame blocks occluding >50–80% of road ROI | Added all `20` corrupted filenames to `MANUAL_EXCLUDED_IMAGES` in `clean_dataset_v1.py` | `cam_id=169`: `598 -> 578` valid images (`-20` `corrupt_artifact`); `direction`: `Inbound` confirmed | Yes (`clean_dataset_v1.py`) |
| `CHG-B5-02` | `2026-11-16` | `V1.1` | นิว (`@Pranithi-New`) | Batch 5 two-way / multi-directional cams (`18`, `70`, `1361`, `150`, `230`, `233`, `1063`, `301`, `332`, `363`, `370`, `371`) | Visual & Google Maps/Street View audit showed both opposing flows (incl. undivided roads, contraflow lanes) or multi-directional intersection views in single frames | Updated `CAMERA_CURATION` `direction` -> `"None"` and clarified `location_detail_th`/`en` for those `12` cameras in `clean_dataset_v1.py` | `12` cameras updated to `direction="None"` (`18`, `150`, `301`, `1063`, `1361` `Outbound -> None`; `70`, `230`, `233`, `332`, `363`, `370`, `371` `Inbound -> None`) | Yes (`clean_dataset_v1.py`) |
| `CHG-B5-03` | `2026-11-16` | `V1.1` | นิว (`@Pranithi-New`) | Batch 5 visual checks (`370`, `371`, `546`, `1368`, `915`, `1028`) | Verified `370/371` low `contrast_std < 20` (`7,103–9,481 B` small JPEGs) and `546/1368` nighttime wet-road glare (`glare_ratio > 0.15`) + verified `(lat, lon)` & Aug 25 vs Aug 31 angle stability | Confirmed `370/371` sensors healthy (low contrast from uniform grey asphalt) & `546/1368` wet-road glare needed for Task 04; kept all frames; `1028` unchanged | `0` images removed; `0` angle shifts detected across Batch 5 | Yes (`clean_dataset_v1.py`) |
| `CHG-B5-04` | `2026-11-17` | `V1.1` | นิว (`@Pranithi-New`) | Batch 5 Street View & OSM audit (`915`, `301`, `370`, `546`, `1368`) | `915` raw pin (`13.72639, 100.49213`) sat ~95 m NW on Intharaphithak Rd footbridge instead of SW roundabout corner; `301` looks along Nakhon Ratchasima Rd (not U Thong Nok Rd); `370` looks SE along Krung Kasem Rd (not bridge crossing) | Added `"lat": 13.72572, "lon": 100.49268` for `cam_id=915` and updated `location_detail_th/en` for `915`, `301`, `370`, `546`, `1368` in `clean_dataset_v1.py` | `cam_id=915` pin moved ~95 m SE to SW roundabout quadrant; road/landmark descriptions aligned to Street View & OSM | Yes (`clean_dataset_v1.py`) |
| `CHG-B5-05` | `2026-11-17` | `V1.1` | นิว (`@Pranithi-New`) | `cam_id=332` (Batch 5 full pixel scan across `10,217` valid frames) | `5` frames (`20260825_163054`, `164054`, `165052`, `20260826_064052`, `20260828_112105`) exhibit severe vertical `scanline_smear` / `stretched_frame` corruption occluding >50%–90% of the Ratchawat intersection | Added all `5` filenames with `"scanline_smear"` to `MANUAL_EXCLUDED_IMAGES` in `clean_dataset_v1.py` (total `25` Batch 5 manual exclusions) | `cam_id=332`: `611 -> 606` valid images (`-5` `scanline_smear`) | Yes (`clean_dataset_v1.py`) |

---

## Detailed Version Log

### `V1.0` -- `2026-11-11` (Initial Automated Quality Gate & Metadata Cleansing)

- **Generated By:** `00_data_cleaning_and_qa/src/clean_dataset_v1.py` (`elapsed_seconds = 129.42s`)
- **Input Baseline (`Dataset/` Raw):** `100` cameras, `61,319` raw images (`2026-08-25 06:00:00` to `2026-08-31 21:01:19`), `cctv_info.csv`.
- **Output (`Dataset_Clean_V1/`):** `60,210` valid ASCII-named images (`98.1914%`), `image_quality_manifest.parquet/.csv` (`61,319 x 35`), `cctv_info_cleaned.parquet/.csv` (`100 x 25`), `cleaning_summary.json`.

#### 1. Image Cleaning Operations Applied (`61,319 -> 60,210`)
1. **Gate 1 -- Blank White HTTP Timeouts (`504` removed):**
   - **Rule:** `file_size < 2,000` bytes OR `brightness_mean == 255.0`.
   - **Observation:** Primarily `1,402-1,403` byte completely blank frames (`std = 0.0`) clustered during `07:15-08:45` morning ingestion load spikes.
2. **Gate 2 -- Rainbow No-Signal Color Bars (`33` removed):**
   - **Rule:** `file_size == 8,782` bytes OR (`8,700 <= file_size <= 8,900` AND `127.5 <= brightness_mean <= 128.5` AND `contrast_std >= 111.0`).
   - **Observation:** Captured all `gst-launch-0.10` test patterns on `2026-08-27` morning outage across both Camera `432` (`8,782 B`, `17` frames) and Camera `1804` (`8,783 B`, `16` frames), preventing `1804`'s `15` repeated Rainbow frames from distorting frozen statistics or leaking into valid frames.
3. **Gate 3 -- Stream / Codec Color Corruption (`19` removed, `32` mild warnings retained):**
   - **Gray P-Frame Rule (`11` removed):** `127.0 <= brightness_mean <= 132.0` AND `contrast_std < 16.0` (I-frame dropped during transmission, e.g., `169`: 7 frames, `206`: 4 frames).
   - **Green Screen Rule (`8` removed):** `(g_mean - r_mean > 40.0)` AND `(g_mean - b_mean > 40.0)` (YUV channel drop, e.g., `500`: 6 frames, `32`: 1 frame, etc., calibrated specifically to avoid false positives on cool blue-lit nighttime frames).
   - **Non-Destructive Partial Artifact Tagging (`32` valid frames preserved & flagged):** Frames passing Gate 3 with localized bottom-strip gray/green artifacts (`gray128_ratio > 0.45` or `neon_green_ratio > 0.08`) remain in `cctv_images/` with `quality_warning`:
     - `partial_gray_pframe` (`24`): `cam_id=169` (`19`), `cam_id=206` (`5`).
     - `partial_green_screen` (`8`): `cam_id=500` (`7`), `cam_id=630` (`1`).
4. **Gate 4 -- Frozen Stream Deduplication (`553` removed):**
   - **Rule:** Pixel-wise `MAD == 0.0` compared against the most recent non-error valid frame of the same `cam_id`.
   - **Observation:** Eliminated identical cached/frozen frames even when JPEG headers/MD5 hashes differed slightly. Highest frozen counts: Cam `150` (`124`), `938` (`98`), `939` (`95`), `206` (`95`), `395` (`72`), plus synchronized subnet freezes (e.g., `10.116.x.x` on `2026-08-28 13:06-13:35`).
5. **Gate 5 -- Timestamp Reliability & ASCII Filename Standardization (`60,210` valid):**
   - Parsed timestamps strictly from filenames `_YYYYMMDD_HHMMSS.jpg` to bypass CMOS battery reset `1970-01-01` OSD text overlays.
   - Standardized valid filenames to `<cam_id>_<YYYYMMDD_HHMMSS>.jpg` to resolve Windows OpenCV (`cv2.imread`) failures on Thai Unicode paths.
   - Extracted `glare_ratio`, `brightness_mean`, `contrast_std`, and channel means for downstream night/rain visibility weighting.

#### 2. Metadata Cleaning Operations Applied (`100` cameras)
- **Removed Corrupt Strings / Placeholders:** Replaced `NULL` (`1589`, `572`), `'0'` (`576`, `1368`, `546`), `'connect BMAcctv'` (`913`, `915`, `938`, `939`), `'17/5000'` (`1103`), and `'(See Yellow)'` (`556`).
- **Fixed Row-Shifted English Location Names:** Verified `(lat, lon)` against Thai street labels to correct severe cross-district mismatches (e.g., `529`, `1188`, `572`, `126/127`, `432/619`, `500`, `1368`).
- **Repaired Truncated Thai Labels:** Completed `53` camera entries whose `location` / `location_detail` strings were cut off around ~28 characters in the raw CSV.
- **Spatial & Network Enrichment:** Assigned BMA `district`, `7` arterial `corridor` zones, traffic `direction` (`Inbound`: 51, `Outbound`: 29, `"None"`: 20), `ip_subnet` (`18` subnets), `img_width`/`img_height` (preserving `348x261` exception on `cam_id=395`), and `pair_id` / `pair_type` (identifying `6` true bidirectional footbridge pairs among `21` proximity pairs `<= 100m`).

#### 3. Open Items & Decisions Deferred to `V1.1` / `V2.0`
- **Team Batch Verification (100 Cameras):** Distributed physical location, direction, and pair verification across Batch 1-6 (ปลื้ม, กร, เฟิร์ม, สอง, นิว, โม่).
- **Low-Contrast Night / Foggy Camera Check (`321` valid frames with `contrast_std < 20`):** Heavy concentration at Cam `370` (`169` frames) and `371` (`140` frames) requires visual check to separate lens blur/hardware darkness from real weather conditions.
- **High-Glare Headlight Check (`78` valid frames with `glare_ratio > 0.15`):** Concentrated at `cam_id=546` (`44` frames) and `cam_id=1368` (`31` frames).
- **`quality_warning` (`32` frames):** Team decision required on whether `partial_gray_pframe` (`169`, `206`) and `partial_green_screen` (`500`, `630`) affect vehicle ROI or can stay flagged without removal.

---

### `V1.1` -- `TBD` *(In Progress: Peer QA & Refinement)*

#### Batch 5 -- นิว (`@Pranithi-New`): Dusit - Rama 5 - Samsen Corridor (`17` Cameras)

- **Date:** `2026-11-16`
- **Editor:** นิว (`@Pranithi-New`)
- **Batch / Scope:** Batch 5 (`17` cameras: `915`, `18`, `1028`, `70`, `1361`, `150`, `169`, `230`, `233`, `1063`, `301`, `332`, `363`, `370`, `371`, `546`, `1368`) — Google Drive visual inspection + Google Maps/Street View verification + Aug 25 vs Aug 31 angle stability check.
- **Problems & Findings Observed:**
  1. **Severe Gray P-Frame Corruption (`cam_id=169`) & Vertical Scanline Smear (`cam_id=332`):**
     - `cam_id=169`: All `19` frames tagged `partial_gray_pframe` (`gray128_ratio` `0.483–0.717`) plus `169_20260829_195620.jpg` (`gray128_ratio=0.348`) show massive gray P-frame corruption blocks covering `>50–80%` of the frame and obscuring the road ROI (far exceeding the team's `>30%` exclusion threshold). Divided Wong Sawang Road `Inbound` direction and `(lat, lon)` confirmed accurate.
     - `cam_id=332`: Full pixel scan across all `10,217` valid Batch 5 frames uncovered `5` frames (`332_20260825_163054.jpg`, `332_20260825_164054.jpg`, `332_20260825_165052.jpg`, `332_20260826_064052.jpg`, `332_20260828_112105.jpg`) with severe vertical `scanline_smear` / stretched-frame corruption occluding >50%–90% of the Ratchawat intersection.
  2. **Two-Way / Contraflow / Multi-Directional Views (`direction` -> `"None"`):** Per team rule (*if opposing flows are clearly visible in one frame, set `direction` to `"None"`*):
     - Undivided two-way / contraflow streets (`70`, `1361` Sam Sen Rd BOT contraflow lane; `150` Rama 6 Rd double-yellow line; `230`, `233`, `1063` Rama 5 Rd; `301` Nakhon Ratchasima Rd one-way + contraflow bus lane): both opposing directions are clearly visible in the same frame.
     - Multi-directional bridge / intersection views (`18` Saphan Daeng Bridge showing both outbound bridge flow & inbound red-light queue; `332` Ratchawat Intersection; `363` Khet Dusit Intersection; `370` Krung Kasem Rd two-way along Khlong Phadung Krung Kasem & `371` Thewet Intersection): cross-traffic or opposing flows occupy the frame.
  3. **Street View & OSM Coordinate / Road Name Corrections (`915`, `301`, `370`, `546`, `1368`):**
     - **`cam_id=915` (Wongwian Yai):** Raw CSV pin (`13.72639, 100.49213`) was offset ~95 m NW on the Intharaphithak Rd footbridge; corrected to **`13.72572, 100.49268`** (SW roundabout quadrant looking NNE across the roundabout).
     - **`cam_id=301` (U Thong Nok Intersection):** Corrected road name in detail from U Thong Nok Rd to **Nakhon Ratchasima Rd** (4 one-way NE lanes + 1 contraflow bus lane visible on road stencils & OSM).
     - **`cam_id=370` (Thewet Intersection):** Corrected description from bridge approach to **Krung Kasem Rd** heading SE towards Pracha Kasem along Khlong Phadung Krung Kasem (two-way traffic).
     - **`cam_id=546` & `1368` (Panichayakarn Intersection):** Clarified Phitsanulok Rd view towards Chamai Maruchet Bridge / Government House (`546`) and Rama 5 Rd view past RMUTP (`1368`).
  4. **Open `V1.0` Items Verified Healthy (Keep All Frames):**
     - **`cam_id=370` & `371` (`contrast_std < 20`):** Visual check of daytime, dawn, and smallest-file nighttime frames (`370_20260829_190537.jpg` `7,103 B`, `370_20260830_070536.jpg` `7,748 B`, `370_20260829_202540.jpg` `7,869 B`, `371_20260830_060042.jpg` `9,481 B`) confirms camera optics are healthy; low contrast is caused by steep downward framing onto uniform grey asphalt. All frames kept.
     - **`cam_id=546` & `1368` (`glare_ratio > 0.15`):** Nighttime glare comes from wet asphalt reflections and vehicle headlights needed for Task 04 CV rain/wet-road detection. All frames kept.
     - **Verified Unchanged (`V1.0` direction/coords confirmed):** `1028`, `546`, `1368` (`direction="None"` and coordinates accurate); no mid-week camera rotation found comparing Aug 25 vs Aug 31 frames.
- **Fix / Decision Applied:**
  - Added `25` corrupted filenames (`20` `cam_id=169` `"corrupt_artifact"` + `5` `cam_id=332` `"scanline_smear"`) to `MANUAL_EXCLUDED_IMAGES` in `00_data_cleaning_and_qa/src/clean_dataset_v1.py`.
  - Updated `CAMERA_CURATION` `direction` to `"None"` and clarified `location_detail_th` / `location_detail_en` for `12` cameras (`18`, `70`, `1361`, `150`, `230`, `233`, `1063`, `301`, `332`, `363`, `370`, `371`), plus refined `546`, `1368`, and corrected `cam_id=915` coordinates (`13.72572, 100.49268`).
  - Added `meta.get("lat", ...)` / `meta.get("lon", ...)` support in `build_cleaned_metadata()` for clean compatibility across team PRs.
  - Checked `[x]` all `17/17` Batch 5 cameras in `00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md`.
- **Quantitative Impact (Before -> After):**
  - `cam_id=169` valid images: `598 -> 578` (`-20` `corrupt_artifact` frames).
  - `cam_id=332` valid images: `611 -> 606` (`-5` `scanline_smear` frames).
  - Total Batch 5 manual exclusions: `25` frames.
  - Batch 5 `direction` changes: `12` cameras moved from `Inbound`/`Outbound` to `"None"`; `1` remains `"Inbound"` (`169`); `4` remain `"None"` (`915`, `1028`, `546`, `1368`).
- **Verification:** Bytecode compile (`py_compile.compile` to temp `.pyc`), `ast.parse`, and `CAMERA_CURATION` / `MANUAL_EXCLUDED_IMAGES` check against `image_quality_manifest.parquet` (`100` cameras, `25` excluded filenames) `[PASS]`; PR (`chore/00-qa-new` -> `main`) `[Pending Maintainer Merge & Final Run]`.

---

> **Instructions for Contributors:** When adding `V1.1` or `V2.0` updates, copy the template below, fill in exact details, and add a summary row to the **Modification Ledger** above.

```markdown
#### Change Entry Template (Copy & Paste for Each Audit / Fix Session)
- **Date:** YYYY-MM-DD
- **Editor:** <Name> (<GitHub handle>)
- **Batch / Scope:** <e.g., Batch 2 (16 cameras) / Extra Gate 4 check / partial_green_screen review>
- **Problem Found:**
  - `cam_id=XXX`: <describe exact issue in metadata or specific images>
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION` / exclusion list / threshold in `clean_dataset_v1.py` (or requested update)
- **Quantitative Impact (Before -> After):**
  - Metadata fields changed: <list exact fields & old -> new values>
  - Images affected: `<N>` valid images (`<before>` -> `<after>`)
- **Verification:** PR opened (`chore/00-qa-<name>` -> `main`) -> Final `clean_dataset_v1.py` + `run_pipeline.py --check-contract` `[Pending Maintainer Run / PASS]`
```

