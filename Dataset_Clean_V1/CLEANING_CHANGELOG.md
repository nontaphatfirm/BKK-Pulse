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
| `CHG-002` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=26`, `cam_id=1195` (Batch 4) | Both `26` and `1195` watch Charoen Nakhon Rd from opposite sides of Bukkhalo Intersection (neither feed captures Mahai Sawan Rd); `1195` faces Outbound rather than Inbound | Updated `CAMERA_CURATION` in `clean_dataset_v1.py` and `CAMERA_AUDIT_CHECKLIST.md` (`pair_id`, `pair_type`, `1195` `location_*` & `direction`) | `pair_id`: `PAIR_JX_BUKKHALO` -> `PAIR_ARM_BUKKHALO`; `pair_type`: `perpendicular_junction` -> `opposite_intersection_arm`; `1195` `direction`: `Inbound` -> `Outbound`; `1195` Mahai Sawan labels -> Charoen Nakhon Rd | Yes (`clean_dataset_v1.py`) |
| `CHG-003` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=500`, `cam_id=1188` (Batch 4) | `500` contains a significant proportion (`>10%`) of unusable artifact images; `1188` is a wide-angle view whose nighttime frames are completely unusable due to tiny vehicles and severe glare | Logged recommendation to remove `500` and `1188` from the downstream dataset (kept `clean_dataset_v1.py`, `CAMERA_AUDIT_CHECKLIST.md`, and 100-cam contract unchanged pending team/maintainer decision & location detail verification) | Pending exclusion decision (`100 -> 98` cameras or `0` valid images retained for `500`/`1188`) | No (Pending decision) |
| `CHG-004` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=32` (Batch 4) | Location labels are accurate, but the camera view clearly captures traffic flowing in both directions along Thoet Thai Rd | Updated `direction` to `"None"` in `CAMERA_CURATION` (`clean_dataset_v1.py`) and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=32` `direction`: `Inbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-005` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=36` (Batch 4) | Wide view of Ratchada-Ratchaphruek intersection with traffic going in multiple directions; camera is on the Ratchadaphisek Rd side with traffic approaching from Mahai Sawan Intersection (not Ratchaphruek Rd / Taksin) | Updated `location_*`, `location_detail_*`, and `direction` in `CAMERA_CURATION` (`clean_dataset_v1.py`) and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=36`: `location_*` Ratchaphruek Rd -> Ratchadaphisek Rd; `location_detail_*` Taksin -> Mahai Sawan Intersection; `direction`: `Outbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-006` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=158` (Batch 4) | Dominant 3-lane foreground carriageway flows Outbound (towards Bukkhalo Intersection); `location_detail_th` also said `ขาเข้า` | Updated `direction` to `"Outbound"` and aligned `location_detail_th` (`ขาเข้า` -> `ขาออก`) in `CAMERA_CURATION` (`clean_dataset_v1.py`), and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=158`: `direction`: `Inbound` -> `Outbound`; `location_detail_th`: `ขาเข้า` -> `ขาออก` | Yes (`clean_dataset_v1.py`) |
| `CHG-007` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=251` (Batch 4) | English temple spelling mismatch vs. Google Maps (`Wat Dishongsaram` -> `Wat Ditsahongsaram (Wat Makkasan)`) and flow direction is Outbound (away from CBD towards Mit Samphan) | Updated `location_en` and `direction` in `CAMERA_CURATION` (`clean_dataset_v1.py`), and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=251`: `location_en` `Wat Dishongsaram` -> `Wat Ditsahongsaram (Wat Makkasan)`; `direction`: `Inbound` -> `Outbound` | Yes (`clean_dataset_v1.py`) |
| `CHG-008` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=256` (Batch 4) | Centered two-way view over undivided Phetchaburi Rd (2 left lanes often congested vs. 4-5 opposing lanes free-flowing, plus tidal contraflow); expressway destination is Chalerm Maha Nakhon Expressway (`ใต้ทางด่วนเฉลิมมหานคร`) | Updated `direction` to `"None"` and refined `location_detail_th` / `location_detail_en` in `CAMERA_CURATION` (`clean_dataset_v1.py`), and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=256`: `direction`: `Outbound` -> `None`; `location_detail_*`: `Phetchaburi Expressway Intersection` -> `Chalerm Maha Nakhon Expressway` (`ใต้ทางด่วนเฉลิมมหานคร`) | Yes (`clean_dataset_v1.py`) |
| `CHG-009` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=500` (Batch 4) | Coordinates `(13.75001, 100.54103)` and map view confirm `500` is actually Pratu Nam Intersection (not Mit Samphan Intersection), with traffic from Ratchathewi heading towards `cam_id=256` and multi-directional intersection flow | Updated `location_*`, `location_detail_*`, and `direction` (`"None"`) in `CAMERA_CURATION` (`clean_dataset_v1.py`), and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` (`CHG-003` removal proposal remains open) | `cam_id=500`: `location_*` Mit Samphan -> Pratu Nam Intersection (`แยกประตูน้ำ`); `direction`: `Inbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-010` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=529` (Batch 4) | Crossing interchange view split ~50/50 across roads with neither direction heading directly into central Bangkok | Updated `direction` to `"None"`, dropped `(Inbound)` / `(ฝั่งขาเข้า)` from `location_*` and `location_detail_*` in `CAMERA_CURATION` (`clean_dataset_v1.py`), and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=529`: `direction`: `Inbound` -> `None`; removed `(Inbound)` / `(ฝั่งขาเข้า)` from location labels | Yes (`clean_dataset_v1.py`) |
| `CHG-011` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=572` (Batch 4) | Ramp traffic flows Inbound onto the elevated highway and is strictly ascending (not ascending/descending) | Updated `direction` to `"Inbound"` and `location_detail_en` (`Taling Chan ascending/descending ramp` -> `Taling Chan ascending ramp`) in `CAMERA_CURATION` (`clean_dataset_v1.py`), and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=572`: `direction`: `None` -> `Inbound`; `location_detail_en`: `ascending/descending` -> `ascending` | Yes (`clean_dataset_v1.py`) |
| `CHG-012` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=595` (Batch 4) | Wide fisheye view of Ban Khaek Intersection covering crossing traffic on both Itsaraphap and Prajadhipok (`ประชาธิปก`) Roads (with left leg barriered off) | Added Prajadhipok Rd (`ประชาธิปก`) to `location_detail_*` and set `direction` to `"None"` in `CAMERA_CURATION` (`clean_dataset_v1.py`), and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=595`: `direction`: `Inbound` -> `None`; `location_detail_*` updated to include `ประชาธิปก` / `Prajadhipok Roads` | Yes (`clean_dataset_v1.py`) |
| `CHG-013` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=1188` (Batch 4) | Camera overlooks Kanchanaphisek Road (Motorway 9 / Western Outer Ring Rd) facing towards Bang Chueak Nang Interchange (`ทางแยกต่างระดับบางเชือกหนัง`) in both directions, rather than Borommaratchachonnani / Phutthamonthon Sai 2 | Updated `location_*` and `location_detail_*` in `CAMERA_CURATION` (`clean_dataset_v1.py`), kept `direction="None"`, and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` (`CHG-003` removal proposal remains open) | `cam_id=1188`: `location_*` Borommaratchachonnani / Phutthamonthon Sai 2 -> Kanchanaphisek Road (Chimphli Interchange) towards Bang Chueak Nang Interchange | Yes (`clean_dataset_v1.py`) |
| `CHG-014` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=32, 158, 529, 595, 1076` (Batch 4) | Visual sweep flagged `22` unusable frames slipping past automated gates (`2` `scanline_smear`, `17` `corrupt_artifact`, `1` `frozen_visual`, `2` `blocked_lens` rainwater) | Added all `22` filenames to `MANUAL_EXCLUDED_IMAGES` in `clean_dataset_v1.py` | `-22` broken images queued for exclusion (`32`: 2, `158`: 8, `529`: 9, `595`: 1, `1076`: 2) | Yes (`clean_dataset_v1.py`) |
| `CHG-00X` | *YYYY-MM-DD* | `V1.1` | *Example: ปลื้ม (@siravidthongsook)* | *e.g., `cam_id=126` or `quality_warning`* | *Describe issue observed in Drive image or CSV* | *Describe exact fix / rule / label update* | *e.g., `direction`: Inbound -> Outbound* | *No / Pending / Yes* |

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

> **Instructions for Contributors:** When adding `V1.1` or `V2.0` updates, copy the template below, fill in exact details, and add a summary row to the **Modification Ledger** above.

#### `CHG-002` -- Batch 4 Peer Audit: Bukkhalo Intersection Pair (`cam_id=26`, `cam_id=1195`)
- **Date:** `2026-11-15`
- **Editor:** สอง (`@theme222`)
- **Batch / Scope:** Batch 4 (`cam_id=26`, `cam_id=1195`)
- **Problem Found:**
  - `cam_id=26` & `cam_id=1195`: Visual audit confirmed both cameras sit on opposite sides of Bukkhalo Intersection watching Charoen Nakhon Road (`26` Inbound, `1195` Outbound), and neither camera captures Mahai Sawan Road.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION` in `00_data_cleaning_and_qa/src/clean_dataset_v1.py` and checked off `[x]` in `00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md`.
- **Quantitative Impact (Before -> After):**
  - `cam_id=26`: `pair_id` `PAIR_JX_BUKKHALO` -> `PAIR_ARM_BUKKHALO`; `pair_type` `perpendicular_junction` -> `opposite_intersection_arm`.
  - `cam_id=1195`: `pair_id` `PAIR_JX_BUKKHALO` -> `PAIR_ARM_BUKKHALO`; `pair_type` `perpendicular_junction` -> `opposite_intersection_arm`; `direction` `Inbound` -> `Outbound`; `location_th` `แยกบุคคโล (ถนนมไหสวรรย์ ขาเข้า)` -> `แยกบุคคโล (ด้านถนนเจริญนคร)`; `location_en` `Bukkhalo Intersection (Mahai Sawan Road Inbound)` -> `Bukkhalo Intersection (Charoen Nakhon Road)`; `location_detail_th` `รถมาจากถนนเจริญนคร` -> `ถนนเจริญนคร ขาออก`; `location_detail_en` `From Charoen Nakhon Road` -> `Charoen Nakhon Road (Outbound)`.
  - Images affected: `0` valid images (`60,210` unchanged; metadata-only update).
- **Verification:** Branch `chore/00-qa-song` `[Pending final maintainer clean_dataset_v1.py + run_pipeline.py --check-contract]`

#### `CHG-003` -- Batch 4 Peer Audit: Proposed Exclusion of `cam_id=500` & `cam_id=1188`
- **Date:** `2026-11-15`
- **Editor:** สอง (`@theme222`)
- **Batch / Scope:** Batch 4 (`cam_id=500`, `cam_id=1188`)
- **Problem Found:**
  - `cam_id=500` (Mit Samphan Intersection): Visual sweep shows a significant proportion (`>10%`) of unusable artifact images.
  - `cam_id=1188` (Borommaratchachonnani - Kanchanaphisek Interchange): Wide-angle view where nighttime frames are completely unusable because vehicles are too tiny and headlight glare is severe.
- **Fix / Decision Applied:**
  - Logged recommendation to remove `cam_id=500` and `cam_id=1188` from the downstream dataset.
  - Kept `clean_dataset_v1.py`, `CAMERA_AUDIT_CHECKLIST.md` (location verification still pending), `run_pipeline.py`, and `DATA_CONTRACT.md` unchanged for now because `clean_dataset_v1.py` and downstream contracts currently enforce all `100` camera IDs (`expected_min_rows=100`).
- **Quantitative Impact (Before -> After):**
  - Pending team/maintainer decision (`100 -> 98` cameras or marking all frames of `500` & `1188` invalid in `clean_dataset_v1.py` / downstream filtering).
  - Images affected: `0` changed in script so far (`V1.0` counts unchanged).
- **Verification:** Branch `chore/00-qa-song` `[Pending team/maintainer decision & location detail verification]`

#### `CHG-004` -- Batch 4 Peer Audit: Bang Yi Ruea Intersection (`cam_id=32`)
- **Date:** `2026-11-15`
- **Editor:** สอง (`@theme222`)
- **Batch / Scope:** Batch 4 (`cam_id=32`)
- **Problem Found:**
  - `cam_id=32`: Location names are accurate, but visual inspection confirms the camera clearly captures both opposing traffic directions on Thoet Thai Road rather than a single `Inbound` stream.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[32]["direction"]` to `"None"` in `00_data_cleaning_and_qa/src/clean_dataset_v1.py` and checked off `[x]` in `00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md`.
- **Quantitative Impact (Before -> After):**
  - `cam_id=32`: `direction` `Inbound` -> `None`.
  - Images affected: `0` valid images from this metadata edit (note: `2` `scanline_smear` frames on `cam_id=32` are tracked in `MANUAL_EXCLUDED_IMAGES`).
- **Verification:** Branch `chore/00-qa-song` `[Pending final maintainer clean_dataset_v1.py + run_pipeline.py --check-contract]`

#### `CHG-005` -- Batch 4 Peer Audit: Ratchada-Ratchaphruek Intersection (`cam_id=36`)
- **Date:** `2026-11-15`
- **Editor:** สอง (`@theme222`)
- **Batch / Scope:** Batch 4 (`cam_id=36`)
- **Problem Found:**
  - `cam_id=36`: Camera overlooks a large multi-directional intersection view (no single dominant direction), and is actually positioned on the Ratchadaphisek Road side with traffic arriving from Mahai Sawan Intersection rather than the Ratchaphruek Road / Taksin side.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[36]` in `00_data_cleaning_and_qa/src/clean_dataset_v1.py` and checked off `[x]` in `00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md`.
- **Quantitative Impact (Before -> After):**
  - `cam_id=36`: `location_th` `แยกรัชดา-ราชพฤกษ์ (ด้านถนนราชพฤกษ์)` -> `แยกรัชดา-ราชพฤกษ์ (ด้านถนนรัชดาภิเษก)`; `location_en` `Ratchada-Ratchaphruek Intersection (Ratchaphruek Road)` -> `Ratchada-Ratchaphruek Intersection (Ratchadaphisek Road)`; `location_detail_th` `รถมาจากแยกตากสิน` -> `รถมาจากแยกมไหสวรรย์`; `location_detail_en` `From Taksin / Mahai Sawan Intersection` -> `From Mahai Sawan Intersection`; `direction` `Outbound` -> `None`.
  - Images affected: `0` valid images (`metadata-only` update).
- **Verification:** Branch `chore/00-qa-song` `[Pending final maintainer clean_dataset_v1.py + run_pipeline.py --check-contract]`

#### `CHG-006` -- Batch 4 Peer Audit: Soi Charoen Nakhon 46 Footbridge (`cam_id=158`)
- **Date:** `2026-11-15`
- **Editor:** สอง (`@theme222`)
- **Batch / Scope:** Batch 4 (`cam_id=158`)
- **Problem Found:**
  - `cam_id=158`: Visual inspection confirms the camera is centered over the 3-lane carriageway flowing Outbound (towards Bukkhalo Intersection), while the opposing 2 lanes across the median are oblique/secondary; `location_detail_th` also labeled the flow `ขาเข้า`.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[158]["direction"]` to `"Outbound"` and `location_detail_th` (`ขาเข้า` -> `ขาออก`) in `00_data_cleaning_and_qa/src/clean_dataset_v1.py`, and checked off `[x]` in `00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md`.
- **Quantitative Impact (Before -> After):**
  - `cam_id=158`: `direction` `Inbound` -> `Outbound`; `location_detail_th` `ถนนเจริญนคร ขาเข้า มุ่งหน้าแยกบุคคโล` -> `ถนนเจริญนคร ขาออก มุ่งหน้าแยกบุคคโล`.
  - Images affected: `0` valid images from this metadata edit (note: `8` `corrupt_artifact` frames on `cam_id=158` are tracked in `MANUAL_EXCLUDED_IMAGES`).
- **Verification:** Branch `chore/00-qa-song` `[Pending final maintainer clean_dataset_v1.py + run_pipeline.py --check-contract]`

#### `CHG-007` -- Batch 4 Peer Audit: Wat Ditsahongsaram Footbridge (`cam_id=251`)
- **Date:** `2026-11-15`
- **Editor:** สอง (`@theme222`)
- **Batch / Scope:** Batch 4 (`cam_id=251`)
- **Problem Found:**
  - `cam_id=251`: Google Maps lists the temple name as `Wat Ditsahongsaram (Wat Makkasan)` (rather than `Wat Dishongsaram`), and traffic moving from Phetchaburi Expressway Intersection towards Mit Samphan Intersection is heading `Outbound` (away from CBD).
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[251]` (`location_en` and `direction`) in `00_data_cleaning_and_qa/src/clean_dataset_v1.py` and checked off `[x]` in `00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md`.
- **Quantitative Impact (Before -> After):**
  - `cam_id=251`: `location_en` `Footbridge near Wat Dishongsaram on Phetchaburi Road` -> `Footbridge near Wat Ditsahongsaram (Wat Makkasan) on Phetchaburi Road`; `direction` `Inbound` -> `Outbound`.
  - Images affected: `0` valid images (`metadata-only` update).
- **Verification:** Branch `chore/00-qa-song` `[Pending final maintainer clean_dataset_v1.py + run_pipeline.py --check-contract]`

#### `CHG-008` -- Batch 4 Peer Audit: Soi Phetchaburi 27 Footbridge (`cam_id=256`)
- **Date:** `2026-11-15`
- **Editor:** สอง (`@theme222`)
- **Batch / Scope:** Batch 4 (`cam_id=256`)
- **Problem Found:**
  - `cam_id=256`: Camera is centered over an undivided multi-lane tidal/contraflow stretch of Phetchaburi Road showing both opposing directions prominently (2 crowded lanes on the left vs. 4-5 free-flowing opposing lanes on the right), so labeling a single direction would misattribute congestion in whole-frame YOLO analytics. The expressway landmark is also more accurately `ใต้ทางด่วนเฉลิมมหานคร` (`Chalerm Maha Nakhon Expressway`).
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[256]` (`direction` -> `"None"`, `location_detail_th`, `location_detail_en`) in `00_data_cleaning_and_qa/src/clean_dataset_v1.py` and checked off `[x]` in `00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md`.
- **Quantitative Impact (Before -> After):**
  - `cam_id=256`: `direction` `Outbound` -> `None`; `location_detail_th` `หน้ารถมาจากแยกประตูน้ำ มุ่งหน้าแยกใต้ด่วนเพชรบุรี` -> `หน้ารถมาจากแยกประตูน้ำ มุ่งหน้าไปใต้ทางด่วนเฉลิมมหานคร`; `location_detail_en` `From Pratu Nam Intersection towards Phetchaburi Expressway Intersection` -> `From Pratu Nam Intersection towards Chalerm Maha Nakhon Expressway`.
  - Images affected: `0` valid images (`metadata-only` update).
- **Verification:** Branch `chore/00-qa-song` `[Pending final maintainer clean_dataset_v1.py + run_pipeline.py --check-contract]`

#### `CHG-009` -- Batch 4 Peer Audit: Pratu Nam Intersection Correction (`cam_id=500`)
- **Date:** `2026-11-15`
- **Editor:** สอง (`@theme222`)
- **Batch / Scope:** Batch 4 (`cam_id=500`)
- **Problem Found:**
  - `cam_id=500`: Map verification at `(13.75001, 100.54103)` confirms `500` is actually at **Pratu Nam Intersection (`แยกประตูน้ำ`)** rather than Mit Samphan Intersection (`V1.0` corrected the shifted English label to match the erroneous Thai label `ทางแยกมิตรสัมพันธ์` instead of vice versa). Traffic along Phetchaburi Road flows from Ratchathewi Intersection towards `cam_id=256` (Soi Phetchaburi 27), and the wide intersection view captures heavy traffic in every direction (`None`).
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[500]` (`location_th`, `location_detail_th`, `location_en`, `location_detail_en`, `direction` -> `"None"`) in `00_data_cleaning_and_qa/src/clean_dataset_v1.py` and checked off `[x]` in `00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md`. *(Note: the `CHG-003` recommendation to exclude `cam_id=500` downstream due to `>10%` unusable artifacts remains pending team/maintainer decision.)*
- **Quantitative Impact (Before -> After):**
  - `cam_id=500`: `location_th` `ทางแยกมิตรสัมพันธ์` -> `แยกประตูน้ำ`; `location_en` `Mit Samphan Intersection` -> `Pratu Nam Intersection`; `location_detail_th` `รถมุ่งหน้าไปแยกราชประสงค์` -> `บริเวณแยกประตูน้ำ (รถมาจากแยกราชเทวี มุ่งหน้าซอยเพชรบุรี 27)`; `location_detail_en` `Towards Ratchaprasong Intersection` -> `Pratu Nam Intersection (from Ratchathewi Intersection towards Soi Phetchaburi 27)`; `direction` `Inbound` -> `None`.
  - Images affected: `0` valid images (`metadata-only` update).
- **Verification:** Branch `chore/00-qa-song` `[Pending final maintainer clean_dataset_v1.py + run_pipeline.py --check-contract]`

#### `CHG-010` -- Batch 4 Peer Audit: Phutthamonthon Sai 2 - Borommaratchachonnani Interchange (`cam_id=529`)
- **Date:** `2026-11-15`
- **Editor:** สอง (`@theme222`)
- **Batch / Scope:** Batch 4 (`cam_id=529`)
- **Problem Found:**
  - `cam_id=529`: Crossing interchange roads are split ~50/50 in the frame and neither road leads directly into central Bangkok, so `"Inbound"` does not reflect the overall camera view.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[529]` (`direction` -> `"None"` and removed `(Inbound)` / `(ฝั่งขาเข้า)` / `Inbound` / `ขาเข้า` from `location_*` and `location_detail_*`) in `00_data_cleaning_and_qa/src/clean_dataset_v1.py`, and checked off `[x]` in `00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md`.
- **Quantitative Impact (Before -> After):**
  - `cam_id=529`: `location_th` `จุดตัดถนนพุทธมณฑลสาย 2 (ฝั่งขาเข้า)` -> `จุดตัดถนนพุทธมณฑลสาย 2`; `location_detail_th` `ถนนบรมราชชนนี-พุทธมณฑลสาย 2 ขาเข้า` -> `ถนนบรมราชชนนี-พุทธมณฑลสาย 2`; `location_en` `Phutthamonthon Sai 2 - Borommaratchachonnani Interchange (Inbound)` -> `Phutthamonthon Sai 2 - Borommaratchachonnani Interchange`; `location_detail_en` `Phutthamonthon Sai 2 / Borommaratchachonnani Inbound` -> `Phutthamonthon Sai 2 / Borommaratchachonnani`; `direction` `Inbound` -> `None`.
  - Images affected: `0` valid images from this metadata edit (note: `9` `corrupt_artifact` frames on `cam_id=529` are tracked in `MANUAL_EXCLUDED_IMAGES`).
- **Verification:** Branch `chore/00-qa-song` `[Pending final maintainer clean_dataset_v1.py + run_pipeline.py --check-contract]`

#### `CHG-011` -- Batch 4 Peer Audit: Borommaratchachonnani Elevated Highway Taling Chan Ramp (`cam_id=572`)
- **Date:** `2026-11-15`
- **Editor:** สอง (`@theme222`)
- **Batch / Scope:** Batch 4 (`cam_id=572`)
- **Problem Found:**
  - `cam_id=572`: Visual audit confirms traffic on the Taling Chan ramp is strictly ascending (matching Thai `ทางขึ้นตลิ่งชัน`) and heading `Inbound` towards central Bangkok, rather than bidirectional `ascending/descending` (`None`).
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[572]` (`location_detail_en` and `direction`) in `00_data_cleaning_and_qa/src/clean_dataset_v1.py` and checked off `[x]` in `00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md`.
- **Quantitative Impact (Before -> After):**
  - `cam_id=572`: `location_detail_en` `Taling Chan ascending/descending ramp` -> `Taling Chan ascending ramp`; `direction` `None` -> `Inbound`.
  - Images affected: `0` valid images (`metadata-only` update).
- **Verification:** Branch `chore/00-qa-song` `[Pending final maintainer clean_dataset_v1.py + run_pipeline.py --check-contract]`

#### `CHG-012` -- Batch 4 Peer Audit: Ban Khaek Intersection (`cam_id=595`)
- **Date:** `2026-11-15`
- **Editor:** สอง (`@theme222`)
- **Batch / Scope:** Batch 4 (`cam_id=595`)
- **Problem Found:**
  - `cam_id=595`: Wide-angle fisheye view of Ban Khaek Intersection captures multi-leg crossing/queuing traffic across both Itsaraphap Road and Prajadhipok Road (`ถนนประชาธิปก`, with the left leg barriered off), so `"None"` keeps directional analytics cleaner than `"Inbound"`; `location_detail_*` also omitted Prajadhipok Road.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[595]` (`location_detail_th`, `location_detail_en`, `direction` -> `"None"`) in `00_data_cleaning_and_qa/src/clean_dataset_v1.py` and checked off `[x]` in `00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md`.
- **Quantitative Impact (Before -> After):**
  - `cam_id=595`: `location_detail_th` `ถนนอิสรภาพ รถมาจากแยกโพธิ์สามต้น` -> `ถนนอิสรภาพ-ประชาธิปก (รถมาจากแยกโพธิ์สามต้น)`; `location_detail_en` `Itsaraphap Road, from Pho Sam Ton Intersection` -> `Itsaraphap & Prajadhipok Roads (from Pho Sam Ton Intersection)`; `direction` `Inbound` -> `None`.
  - Images affected: `0` valid images from this metadata edit (note: `1` `frozen_visual` frame on `cam_id=595` is tracked in `MANUAL_EXCLUDED_IMAGES`).
- **Verification:** Branch `chore/00-qa-song` `[Pending final maintainer clean_dataset_v1.py + run_pipeline.py --check-contract]`

#### `CHG-013` -- Batch 4 Peer Audit: Kanchanaphisek Road / Chimphli Interchange (`cam_id=1188`)
- **Date:** `2026-11-15`
- **Editor:** สอง (`@theme222`)
- **Batch / Scope:** Batch 4 (`cam_id=1188`)
- **Problem Found:**
  - `cam_id=1188`: Street View and camera framing confirm the camera overlooks Kanchanaphisek Road (Motorway 9 / Bangkok Western Outer Ring Rd) facing towards Bang Chueak Nang Interchange (`ทางแยกต่างระดับบางเชือกหนัง`) with both incoming and outgoing lanes visible (`None`), rather than Borommaratchachonnani Rd / Phutthamonthon Sai 2.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[1188]` (`location_th`, `location_detail_th`, `location_en`, `location_detail_en`) in `00_data_cleaning_and_qa/src/clean_dataset_v1.py`, kept `direction="None"`, and checked off `[x]` in `00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md`. *(Note: the `CHG-003` recommendation to exclude `cam_id=1188` downstream due to unusable nighttime glare/tiny vehicles remains pending team/maintainer decision.)*
- **Quantitative Impact (Before -> After):**
  - `cam_id=1188`: `location_th` `ต่างระดับฉิมพลี-พุทธมณฑลสาย 2 (ถนนบรมราชชนนี)` -> `ถนนกาญจนาภิเษก (ต่างระดับฉิมพลี)`; `location_detail_th` `จุดตัดถนนบรมราชชนนี-กาญจนาภิเษก ฝั่งพุทธมณฑลสาย 2` -> `ถนนกาญจนาภิเษก มุ่งหน้าทางแยกต่างระดับบางเชือกหนัง (เห็นทั้งขาเข้าและขาออก)`; `location_en` `Borommaratchachonnani - Kanchanaphisek Interchange (Phutthamonthon Sai 2 Side)` -> `Kanchanaphisek Road (Chimphli Interchange)`; `location_detail_en` `Borommaratchachonnani Road near Phutthamonthon Sai 2` -> `Overlooking Kanchanaphisek Road (Motorway 9) towards Bang Chueak Nang Interchange (both directions)`.
  - Images affected: `0` valid images (`metadata-only` update).
- **Verification:** Branch `chore/00-qa-song` `[Pending final maintainer clean_dataset_v1.py + run_pipeline.py --check-contract]`

#### `CHG-014` -- Batch 4 Peer Audit: Manual Frame Exclusions (`22` Frames Across `cam_id=32, 158, 529, 595, 1076`)
- **Date:** `2026-11-15`
- **Editor:** สอง (`@theme222`)
- **Batch / Scope:** Batch 4 (`MANUAL_EXCLUDED_IMAGES` in `clean_dataset_v1.py`)
- **Problem Found:**
  - `cam_id=32` (`2` `scanline_smear`): `32_20260828_100545.jpg`, `32_20260830_124541.jpg`
  - `cam_id=158` (`8` `corrupt_artifact`): `158_20260827_183605.jpg`, `158_20260827_191605.jpg`, `158_20260828_185607.jpg`, `158_20260829_114604.jpg`, `158_20260830_075603.jpg`, `158_20260830_110607.jpg`, `158_20260831_161604.jpg`, `158_20260831_201605.jpg`
  - `cam_id=529` (`9` `corrupt_artifact`): `529_20260825_081011.jpg`, `529_20260825_142011.jpg`, `529_20260827_123022.jpg`, `529_20260827_155011.jpg`, `529_20260827_161011.jpg`, `529_20260827_193511.jpg`, `529_20260828_145011.jpg`, `529_20260828_155011.jpg`, `529_20260828_200011.jpg`
  - `cam_id=595` (`1` `frozen_visual`): `595_20260826_154043.jpg`
  - `cam_id=1076` (`2` `blocked_lens` — rainwater): `1076_20260831_163105.jpg`, `1076_20260831_164105.jpg`
- **Fix / Decision Applied:**
  - Added all `22` filenames to `MANUAL_EXCLUDED_IMAGES` in `00_data_cleaning_and_qa/src/clean_dataset_v1.py`. *(Note: `cam_id=500` frames are intentionally omitted here pending `CHG-003` whole-camera removal decision.)*
- **Quantitative Impact (Before -> After):**
  - Images queued for exclusion (`MANUAL_EXCLUDED_IMAGES`): `22` images (`2` `scanline_smear`, `17` `corrupt_artifact`, `1` `frozen_visual`, `2` `blocked_lens`).
- **Verification:** Branch `chore/00-qa-song` `[Pending final maintainer clean_dataset_v1.py + run_pipeline.py --check-contract]`

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

