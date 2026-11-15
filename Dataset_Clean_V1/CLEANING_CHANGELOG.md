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
| `CHG-002` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=75` (Batch 3) | `location_detail_th`/`en` in raw metadata misstated incoming approach as Sathu Pradit Expressway (Ratchadaphisek Rd), whereas daylight/night images show BRT median lane on Naradhiwas Rd inbound from Naradhiwas–Rama 3 Intersection | Updated `CAMERA_CURATION[75]` (`location_detail_th` & `location_detail_en`) in `clean_dataset_v1.py` | `location_detail_th`: `รถมาจากแยกด่วนสาธุประดิษฐ์` -> `รถมาจากแยกนราธิวาส-พระราม 3`; `location_detail_en`: `From Sathu Pradit Expressway Intersection` -> `From Naradhiwas-Rama 3 Intersection` | Yes (`clean_dataset_v1.py`) |
| `CHG-003` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=88` (Batch 3) | Two-way road with no median (`Chan Rd` near Soi `18/6`); YOLO counts both inbound (right lane towards Chan-Naradhiwas) and outbound (left lane towards camera) vehicles together in one frame | Changed `CAMERA_CURATION[88]["direction"]` from `"Inbound"` to `"None"` in `clean_dataset_v1.py` to avoid polluting Macro Directional Flow (`04`) | `direction`: `Inbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-004` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=186` (Batch 3) | Peer QA verification of `cctv_images/186/` and metadata (`location_*`, `district`, `corridor`, `direction`) | Verified all images and metadata against Google Maps; no broken frames or metadata errors found | No changes (`V1.0` baseline confirmed) | Yes (`clean_dataset_v1.py` unchanged) |
| `CHG-005` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=188` (Batch 3) | Peer QA verification of `cctv_images/188/` and metadata (`location_*`, `district`, `corridor`, `direction`) | Verified all images and metadata against Google Maps; no broken frames or metadata errors found | No changes (`V1.0` baseline confirmed) | Yes (`clean_dataset_v1.py` unchanged) |
| `CHG-006` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=194` (Batch 3) | Metadata listed South Sathon Rd (`Inbound`, towards Witthayu), whereas night/day imagery shows primary foreground traffic on North Sathon Rd coming from Witthayu towards Sathon-Naradhiwas (`Outbound`) | Updated `CAMERA_CURATION[194]` (`location_th`, `location_detail_th`, `location_en`, `location_detail_en`, `direction`) in `clean_dataset_v1.py` | `ถนนสาทรใต้` -> `ถนนสาทรเหนือ`; `รถมาจากแยกสาทร-นราธิวาส มุ่งหน้าแยกวิทยุ` -> `รถมาจากแยกวิทยุ มุ่งหน้าแยกสาทร-นราธิวาส`; `direction`: `Inbound` -> `Outbound` | Yes (`clean_dataset_v1.py`) |
| `CHG-007` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=196` (Batch 3) | Peer QA verification of `cctv_images/196/` and metadata (`location_*`, `district`, `corridor`, `direction`) | Verified all images and metadata against Google Maps; no broken frames or metadata errors found | No changes (`V1.0` baseline confirmed) | Yes (`clean_dataset_v1.py` unchanged) |
| `CHG-008` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=206` (Batch 3) | Metadata listed `ใกล้ซอยนราธิวาสราชนครินทร์ 20`, `รถมาจากแยกรัชดา-นราธิวาส มุ่งหน้าแยกจันทน์-นราธิวาส` (`Inbound`), and raw coordinates (`13.70545, 100.53835`) on the opposite side; also 6 frames (`5` severe gray P-frame corruptions, `1` heavy lens blur/smear) slipped past baseline thresholds | Updated `CAMERA_CURATION[206]` (`location_*`, `direction`, `lat`, `lon`), added optional `lat`/`lon` override in `build_cleaned_metadata()`, and added 6 filenames to `MANUAL_EXCLUDED_IMAGES` in `clean_dataset_v1.py` | `ใกล้ซอย...` -> `ตรงข้ามซอยนราธิวาสราชนครินทร์ 20`; `รถมาจากแยกรัชดา...` -> `รถมาจากแยกจันทน์-นราธิวาส มุ่งหน้าแยกรัชดา-นราธิวาส`; `Inbound` -> `Outbound`; `13.70545, 100.53835` -> `13.70555, 100.53865`; `-6` broken images queued | Yes (`clean_dataset_v1.py`) |
| `CHG-009` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=211` (Batch 1) | Peer QA verification of `cctv_images/211/` and metadata (`location_*`, `district`, `corridor`, `direction`) | Verified all images and metadata; no broken frames or metadata errors found | No changes (`V1.0` baseline confirmed) | Yes (`clean_dataset_v1.py` unchanged) |
| `CHG-010` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=599` (Batch 3) | Wide intersection-box view at Surasak Intersection (`สีลม–สุรศักดิ์–มเหสักข์`) where YOLO counts cross-traffic across the junction box and both sides of the median simultaneously | Changed `CAMERA_CURATION[599]["direction"]` from `"Inbound"` to `None` in `clean_dataset_v1.py` | `direction`: `Inbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-011` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=603` (Batch 3) | `location_detail_th`/`en` stated `From Surasak Intersection` (only the side stop-line on Silom Rd left edge), whereas the main corridor stretching ahead is Naradhiwas Rd Northbound (`no BTS viaduct`, `tree-lined median`) fed from Sathon-Naradhiwas Intersection | Updated `CAMERA_CURATION[603]` (`location_detail_th`, `location_detail_en`) in `clean_dataset_v1.py` | `location_detail_th`: `รถมาจากแยกสุรศักดิ์` -> `รถมาจากแยกสาทร-นราธิวาส`; `location_detail_en`: `From Surasak Intersection` -> `From Sathon-Naradhiwas Intersection` | Yes (`clean_dataset_v1.py`) |
| `CHG-012` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=604` (Batch 3) | Full 4-way Silom–Naradhiwas junction view capturing both southbound (`Outbound`) & northbound (`Inbound`) carriageways on Naradhiwas Rd under the BTS viaduct plus Silom Rd cross-traffic; old label also referenced `แยกศาลาแดง` which is off-axis on Silom Rd | Updated `CAMERA_CURATION[604]` (`location_detail_th`, `location_detail_en`, `direction`) in `clean_dataset_v1.py` | `location_detail_th`: `ท้ายรถมุ่งหน้าแยกศาลาแดง / แยกสาทร-นราธิวาส` -> `บริเวณแยกสีลม-นราธิวาส (ด้านถนนนราธิวาสฯ มุ่งหน้าแยกสาทร-นราธิวาส)`; `direction`: `Inbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-013` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=11` (Batch 3) | Divided 5-lane Ratchawithi Rd view near Soi Ratchawithi 6 showing both eastbound (`Outbound`, left 1 lane + center 2 lanes from Victory Monument) and westbound (`Inbound`, right 2 lanes towards Victory Monument) simultaneously; description also mentioned only Victory Monument | Updated `CAMERA_CURATION[11]` (`location_detail_th`, `location_detail_en`, `direction`) in `clean_dataset_v1.py` | `location_detail_th`: `รถมาจากอนุสาวรีย์ชัยสมรภูมิ` -> `ช่วงอนุสาวรีย์ชัยสมรภูมิ – แยกสามเหลี่ยมดินแดง (ทั้งสองทิศทาง)`; `direction`: `Outbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-014` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=82` (Batch 3) | `V1.0` metadata stated `From Mo Leng towards Pratu Nam` (`Inbound`), describing only the 1 leftmost contraflow bus lane; time-sliced imagery (`06:01`–`20:51`) confirms the 4 main right lanes flow northbound (`Pratu Nam -> Mo Leng`, `Outbound`) all day while the 1 left lane runs southbound contraflow traffic (`Inbound`, active mainly in morning hours) | Updated `CAMERA_CURATION[82]` (`location_detail_th`, `location_detail_en`, `direction`) in `clean_dataset_v1.py` | `location_detail_th`: `รถมาจากแยกหมอเหล็ง มุ่งหน้าแยกประตูน้ำ` -> `ช่วงแยกประตูน้ำ – แยกหมอเหล็ง (ทั้งสองทิศทาง: 4 เลนไปหมอเหล็ง / 1 เลนไปประตูน้ำ)`; `direction`: `Inbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-015` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=239` (Batch 3) | Peer QA verification of `cctv_images/239/` and metadata (`location_*`, `district`, `corridor`, `direction`) | Verified imagery (`From Pathum Wan towards Sam Yan`, 4 main southbound `Inbound` lanes in front of Triam Udom Suksa School; only a small fringe of the opposite northbound carriageway appears at far top-left); no metadata errors found | No changes (`V1.0` baseline confirmed) | Yes (`clean_dataset_v1.py` unchanged) |
| `CHG-016` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=432` (Batch 3) | `V1.0` listed generic `Sam Yan Intersection` with `direction="None"`, whereas imagery shows a single clear westbound approach on Rama 4 Rd (`4` straight lanes + `1` left-turn slip lane onto Si Phraya Rd, looking East under the Thai-Japanese Flyover towards Henri Dunant / Silom) | Updated `CAMERA_CURATION[432]` (`location_detail_th`, `location_detail_en`, `direction`) in `clean_dataset_v1.py` | `location_detail_th`: `บริเวณแยกสามย่าน (ถนนพญาไท-พระรามที่ 4)` -> `รถมาจากสีลม มุ่งหน้าไปหัวลำโพง (บริเวณแยกสามย่าน ถนนพระรามที่ 4)`; `direction`: `None` -> `Inbound` | Yes (`clean_dataset_v1.py`) |
| `CHG-017` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=542` (Batch 3) | Peer QA verification of `cctv_images/542/` and metadata (`location_*`, `district`, `corridor`, `direction`) | Verified bidirectional Sarasin–Lang Suan junction view beside Lumphini Park (`3` eastbound lanes left + `3` westbound lanes right, `direction="None"`) across day/night samples; no broken images or metadata errors found | No changes (`V1.0` baseline confirmed) | Yes (`clean_dataset_v1.py` unchanged) |
| `CHG-018` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=619` (Batch 3) | Peer QA verification of `cctv_images/619/` and metadata (`location_*`, `district`, `corridor`, `direction`) | Verified multi-direction Henri Dunant Intersection box view under the Thai-Japanese Flyover (`PT-06-CH2`, cross-traffic across Henri Dunant Rd & Rama 4 Rd, `direction="None"`); no broken images or metadata errors found | No changes (`V1.0` baseline confirmed) | Yes (`clean_dataset_v1.py` unchanged) |
| `CHG-019` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=277` (Batch 3) | `V1.0` listed `Footbridge near Soi Rang Nam on Phayathai Road (Victory Monument)` / `รถมุ่งหน้าไปแยกพญาไท (ซอยรางน้ำ)` with `direction="Inbound"`, whereas `RW-3-3-CAM2` (`13.76429, 100.53867`) captures the Victory Monument Roundabout (`Phayathai Island` corner under the BTS Skywalk) with traffic circulating clockwise around the roundabout and splitting/entering across multiple directions | Updated `CAMERA_CURATION[277]` (`location_th`, `location_detail_th`, `location_en`, `location_detail_en`, `direction`) in `clean_dataset_v1.py` | `location_en`: `Footbridge near Soi Rang Nam...` -> `Victory Monument Roundabout`; `location_detail_th`: `รถมุ่งหน้าไปแยกพญาไท (ซอยรางน้ำ)` -> `บริเวณวงเวียนอนุสาวรีย์ชัยสมรภูมิ (มุมเกาะพญาไท เห็นรถวนรอบวงเวียนและแยกออกหลายทิศทาง)`; `direction`: `Inbound` -> `None` | Yes (`clean_dataset_v1.py`) |

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

#### `CHG-002` -- `2026-11-15` (`cam_id=75` Approach Origin Correction)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=75`)
- **Problem Found:**
  - `cam_id=75` (`แยกรัชดา-นราธิวาส (ด้านถนนนราธิวาสฯ)`): raw metadata stated `รถมาจากแยกด่วนสาธุประดิษฐ์` / `From Sathu Pradit Expressway Intersection` (which lies on Ratchadaphisek Rd), whereas camera images show the BRT median lane and inbound Naradhiwas Ratchanakharin traffic approaching from Naradhiwas–Rama 3 Intersection.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[75]` in `00_data_cleaning_and_qa/src/clean_dataset_v1.py` (`lat`/`lon` `13.70057, 100.54130` confirmed accurate).
- **Quantitative Impact (Before -> After):**
  - `location_detail_th`: `รถมาจากแยกด่วนสาธุประดิษฐ์` -> `รถมาจากแยกนราธิวาส-พระราม 3`
  - `location_detail_en`: `From Sathu Pradit Expressway Intersection` -> `From Naradhiwas-Rama 3 Intersection`
  - Images affected: `0` (metadata-only update)
- **Verification:** Pending final `clean_dataset_v1.py --skip-copy` + `run_pipeline.py --check-contract` after Batch 1–6 PRs merge.

#### `CHG-003` -- `2026-11-15` (`cam_id=88` Bidirectional No-Median Direction Adjustment)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=88`)
- **Problem Found:**
  - `cam_id=88` (`แยกจันทน์-สาธุประดิษฐ์`): road has no median and clearly captures both opposing traffic directions in the same frame (inbound towards Chan-Naradhiwas on the right lane and outbound towards Charoen Krung on the left lane). Since Task 03 YOLO counts all vehicles across the full road ROI, labeling this camera `Inbound` would mix outbound congestion into Macro Directional Flow (`04`).
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[88]["direction"]` from `"Inbound"` to `"None"` in `00_data_cleaning_and_qa/src/clean_dataset_v1.py`.
- **Quantitative Impact (Before -> After):**
  - `direction`: `Inbound` -> `None`
  - Images affected: `0` (metadata-only update)
- **Verification:** Pending final `clean_dataset_v1.py --skip-copy` + `run_pipeline.py --check-contract` after Batch 1–6 PRs merge.

#### `CHG-004` -- `2026-11-15` (`cam_id=186` Peer QA Verification — No Changes Needed)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=186`)
- **Findings:** Verified `cctv_images/186/` and metadata (`โครงสร้างป้ายบอกทางขึ้นสะพานพระราม 3 ถนนรัชดาภิเษก`, `Outbound`); all images and metadata match `V1.0` baseline with no corrections needed.
- **Quantitative Impact (Before -> After):** None (`0` metadata / `0` image changes).

#### `CHG-005` -- `2026-11-15` (`cam_id=188` Peer QA Verification — No Changes Needed)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=188`)
- **Findings:** Verified `cctv_images/188/` and metadata (`สะพานลอยใกล้ซอยพระรามที่ 3 ซอย 68 ถนนพระรามที่ 3`, `Outbound`); all images and metadata match `V1.0` baseline with no corrections needed.
- **Quantitative Impact (Before -> After):** None (`0` metadata / `0` image changes).

#### `CHG-006` -- `2026-11-15` (`cam_id=194` North/South Sathon Side & Direction Correction)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=194`)
- **Problem Found:**
  - `cam_id=194`: raw metadata stated South Sathon Rd (`รถมาจากแยกสาทร-นราธิวาส มุ่งหน้าแยกวิทยุ`, `Inbound`), whereas CCTV imagery shows the primary foreground carriageway on North Sathon Rd with vehicles approaching from Witthayu Intersection towards Sathon-Naradhiwas Intersection (leaving the Witthayu/Silom core westbound, `Outbound`).
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[194]` (`location_th`, `location_detail_th`, `location_en`, `location_detail_en`, `direction`) in `00_data_cleaning_and_qa/src/clean_dataset_v1.py`.
- **Quantitative Impact (Before -> After):**
  - `location_th`: `สะพานลอยใกล้ปากซอยคอนแวนต์ ถนนสาทรใต้` -> `สะพานลอยใกล้ปากซอยคอนแวนต์ ถนนสาทรเหนือ`
  - `location_detail_th`: `รถมาจากแยกสาทร-นราธิวาส มุ่งหน้าแยกวิทยุ` -> `รถมาจากแยกวิทยุ มุ่งหน้าแยกสาทร-นราธิวาส`
  - `location_en`: `Footbridge near Soi Convent on South Sathon Road` -> `Footbridge near Soi Convent on North Sathon Road`
  - `location_detail_en`: `From Sathon-Naradhiwas Intersection towards Witthayu Intersection` -> `From Witthayu Intersection towards Sathon-Naradhiwas Intersection`
  - `direction`: `Inbound` -> `Outbound`
  - Images affected: `0` (metadata-only update)
- **Verification:** Pending final `clean_dataset_v1.py --skip-copy` + `run_pipeline.py --check-contract` after Batch 1–6 PRs merge.

#### `CHG-007` -- `2026-11-15` (`cam_id=196` Peer QA Verification — No Changes Needed)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=196`)
- **Findings:** Verified `cctv_images/196/` and metadata (`สะพานลอยหน้าแม็คโคร ถนนนราธิวาสราชนครินทร์`, `Outbound`); all images and metadata match `V1.0` baseline with no corrections needed.
- **Quantitative Impact (Before -> After):** None (`0` metadata / `0` image changes).

#### `CHG-008` -- `2026-11-15` (`cam_id=206` Road Side, Direction, Coordinates & Manual Image Exclusions)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=206`)
- **Problem Found:**
  - `cam_id=206` metadata: raw metadata stated `ใกล้ซอยนราธิวาสราชนครินทร์ 20`, traffic from Ratchada-Naradhiwas towards Chan-Naradhiwas (`Inbound`), and coordinates `13.70545, 100.53835`, whereas daytime/nighttime imagery (`206_20260825_120109.jpg`, `206_20260825_190105.jpg`) shows Khlong Chong Nonsi canal and the BRT busway on the left looking north toward the Sathon/Silom skyscrapers, with all foreground vehicles driving southbound towards the camera (`Outbound`) on the east carriageway (opposite Soi 20).
  - `cam_id=206` imagery: visual sweep found `6` unusable frames in `Dataset_Clean_V1/cctv_images/206/` — `5` with severe partial gray-128 P-frame corruption (`206_20260825_183106.jpg`, `206_20260827_120106.jpg`, `206_20260828_130705.jpg`, `206_20260828_171605.jpg`, `206_20260831_104606.jpg`) and `1` with heavy central lens condensation/water smear occluding the road (`206_20260831_164105.jpg`).
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[206]` (`location_th`, `location_detail_th`, `location_en`, `location_detail_en`, `direction`, `lat`, `lon`), added optional `meta.get("lat")` / `meta.get("lon")` override support in `build_cleaned_metadata()`, and added the `6` filenames to `MANUAL_EXCLUDED_IMAGES` inside `00_data_cleaning_and_qa/src/clean_dataset_v1.py`.
- **Quantitative Impact (Before -> After):**
  - `location_th`: `สะพานลอยใกล้ซอยนราธิวาสราชนครินทร์ 20 ถนนนราธิวาสราชนครินทร์` -> `สะพานลอยตรงข้ามซอยนราธิวาสราชนครินทร์ 20 ถนนนราธิวาสราชนครินทร์`
  - `location_detail_th`: `รถมาจากแยกรัชดา-นราธิวาส มุ่งหน้าแยกจันทน์-นราธิวาส` -> `รถมาจากแยกจันทน์-นราธิวาส มุ่งหน้าแยกรัชดา-นราธิวาส`
  - `location_en`: `Footbridge near Soi Naradhiwas 20 on Naradhiwas Ratchanakharin Road` -> `Footbridge opposite Soi Naradhiwas 20 on Naradhiwas Ratchanakharin Road`
  - `location_detail_en`: `From Ratchada-Naradhiwas Intersection towards Chan-Naradhiwas Intersection` -> `From Chan-Naradhiwas Intersection towards Ratchada-Naradhiwas Intersection`
  - `direction`: `Inbound` -> `Outbound`
  - `lat, lon`: `13.70545, 100.53835` -> `13.70555, 100.53865` (~34 m east to the east carriageway footbridge)
  - Images excluded (`MANUAL_EXCLUDED_IMAGES`): `6` images (`5` `corrupt_artifact`, `1` `blocked_lens`)
- **Verification:** Pending final `clean_dataset_v1.py` regeneration + `run_pipeline.py --check-contract` after Batch 1–6 PRs merge.

#### `CHG-009` -- `2026-11-15` (`cam_id=211` Peer QA Verification — No Changes Needed)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 1 (`cam_id=211`)
- **Findings:** Verified `cctv_images/211/` and metadata (`สะพานลอยใกล้ซอยรัชดาภิเษก 3 ถนนรัชดาภิเษก`, `Outbound`); all images and metadata match `V1.0` baseline with no corrections needed.
- **Quantitative Impact (Before -> After):** None (`0` metadata / `0` image changes).

#### `CHG-010` -- `2026-11-15` (`cam_id=599` Multi-Directional Intersection `direction` Correction)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=599`)
- **Problem Found:**
  - `cam_id=599`: labeled `Inbound` despite showing the full Surasak Intersection box (cross-traffic across the junction plus both sides of the Surasak Road median in the background), causing YOLO detections to mix multiple flow directions.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[599]["direction"]` from `"Inbound"` to `None` in `00_data_cleaning_and_qa/src/clean_dataset_v1.py`.
- **Quantitative Impact (Before -> After):**
  - `direction`: `Inbound` -> `None`
  - Images affected: `0` (metadata-only update)
- **Verification:** Pending final `clean_dataset_v1.py` regeneration + `run_pipeline.py --check-contract` after Batch 1–6 PRs merge.

#### `CHG-011` -- `2026-11-15` (`cam_id=603` Approach Origin Correction)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=603`)
- **Problem Found:**
  - `cam_id=603`: raw metadata stated `From Surasak Intersection` (`รถมาจากแยกสุรศักดิ์`), whereas looking NNW from the SE corner (`13.72620, 100.52797`) shows Naradhiwas Ratchanakharin Rd Northbound (tree-lined median, no BTS viaduct) as the primary corridor stretching ahead—fed from Sathon-Naradhiwas Intersection—while the Surasak/Silom West approach is only the side stop-line at the left red crosswalk.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[603]` (`location_detail_th`, `location_detail_en`) in `00_data_cleaning_and_qa/src/clean_dataset_v1.py`.
- **Quantitative Impact (Before -> After):**
  - `location_detail_th`: `รถมาจากแยกสุรศักดิ์` -> `รถมาจากแยกสาทร-นราธิวาส`
  - `location_detail_en`: `From Surasak Intersection` -> `From Sathon-Naradhiwas Intersection`
  - Images affected: `0` (metadata-only update)
- **Verification:** Pending final `clean_dataset_v1.py` regeneration + `run_pipeline.py --check-contract` after Batch 1–6 PRs merge.

#### `CHG-012` -- `2026-11-15` (`cam_id=604` Multi-Directional Intersection `direction` & Description Correction)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=604`)
- **Problem Found:**
  - `cam_id=604`: labeled `Inbound` and `ท้ายรถมุ่งหน้าแยกศาลาแดง / แยกสาทร-นราธิวาส`, whereas the camera faces straight south along Naradhiwas Rd under the BTS viaduct towards Sathon-Naradhiwas (Sala Daeng is off-axis on Silom Rd to the left) and captures the full junction box—Naradhiwas southbound (`Outbound`), northbound (`Inbound`), and Silom cross-traffic simultaneously.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[604]` (`location_detail_th`, `location_detail_en`, `direction`) in `00_data_cleaning_and_qa/src/clean_dataset_v1.py`.
- **Quantitative Impact (Before -> After):**
  - `location_detail_th`: `ท้ายรถมุ่งหน้าแยกศาลาแดง / แยกสาทร-นราธิวาส` -> `บริเวณแยกสีลม-นราธิวาส (ด้านถนนนราธิวาสฯ มุ่งหน้าแยกสาทร-นราธิวาส)`
  - `location_detail_en`: `Towards Sala Daeng / Sathon-Naradhiwas Intersection` -> `Silom-Naradhiwas Intersection (Naradhiwas Rd towards Sathon-Naradhiwas Intersection)`
  - `direction`: `Inbound` -> `None`
  - Images affected: `0` (metadata-only update)
- **Verification:** Pending final `clean_dataset_v1.py` regeneration + `run_pipeline.py --check-contract` after Batch 1–6 PRs merge.

#### `CHG-013` -- `2026-11-15` (`cam_id=11` Bidirectional Road `direction` & Description Correction)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=11`)
- **Problem Found:**
  - `cam_id=11`: labeled `Outbound` and `รถมาจากอนุสาวรีย์ชัยสมรภูมิ`, whereas daylight/night imagery (`11_20260828_152008.jpg`, `11_20260831_205509.jpg`) shows all 5 lanes of Ratchawithi Rd simultaneously—3 eastbound lanes (`Outbound` away from Victory Monument on the left/center) and 2 westbound lanes (`Inbound` from Din Daeng Intersection on the right)—causing YOLO counts to mix both directions.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[11]` (`location_detail_th`, `location_detail_en`, `direction`) in `00_data_cleaning_and_qa/src/clean_dataset_v1.py`.
- **Quantitative Impact (Before -> After):**
  - `location_detail_th`: `รถมาจากอนุสาวรีย์ชัยสมรภูมิ` -> `ช่วงอนุสาวรีย์ชัยสมรภูมิ – แยกสามเหลี่ยมดินแดง (ทั้งสองทิศทาง)`
  - `location_detail_en`: `From Victory Monument` -> `Between Victory Monument and Din Daeng Intersection (both directions)`
  - `direction`: `Outbound` -> `None`
  - Images affected: `0` (metadata-only update)
- **Verification:** Pending final `clean_dataset_v1.py` regeneration + `run_pipeline.py --check-contract` after Batch 1–6 PRs merge.

#### `CHG-014` -- `2026-11-15` (`cam_id=82` Main Corridor Direction, Contraflow Bus Lane & `None` Correction)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=82`)
- **Problem Found:**
  - `cam_id=82`: metadata stated `From Mo Leng Intersection towards Pratu Nam Intersection` (`Inbound`), which only matches the 1 leftmost contraflow bus lane (separated by a yellow dashed line, especially busy southbound in early morning frames `82_20260825_060116.jpg`, `82_20260825_070609.jpg`). Across all inspected timestamps (`06:01`–`20:51`), the 4 main lanes in front of Indra Square flow northbound towards the camera (`Pratu Nam -> Mo Leng`, `Outbound`). Because YOLO counts all 5 lanes across opposing flows, keeping `Inbound` (or `Outbound`) mixes bidirectional counts.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[82]` (`location_detail_th`, `location_detail_en`, `direction`) in `00_data_cleaning_and_qa/src/clean_dataset_v1.py`.
- **Quantitative Impact (Before -> After):**
  - `location_detail_th`: `รถมาจากแยกหมอเหล็ง มุ่งหน้าแยกประตูน้ำ` -> `ช่วงแยกประตูน้ำ – แยกหมอเหล็ง (ทั้งสองทิศทาง: 4 เลนไปหมอเหล็ง / 1 เลนไปประตูน้ำ)`
  - `location_detail_en`: `From Mo Leng Intersection towards Pratu Nam Intersection` -> `Between Pratu Nam and Mo Leng Intersections (both directions: 4 northbound / 1 southbound contraflow lane)`
  - `direction`: `Inbound` -> `None`
  - Images affected: `0` (metadata-only update)
- **Verification:** Pending final `clean_dataset_v1.py` regeneration + `run_pipeline.py --check-contract` after Batch 1–6 PRs merge.

#### `CHG-015` -- `2026-11-15` (`cam_id=239` Peer QA Verification — No Changes Needed)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=239`)
- **Findings:** Verified `cctv_images/239/` (`239_20260828_151102.jpg`, `239_20260831_205604.jpg`, `239_20260825_062108.jpg`) and metadata (`สะพานลอยใกล้โรงเรียนเตรียมอุดมศึกษา ถนนพญาไท`, `รถมาจากแยกปทุมวัน มุ่งหน้าแยกสามย่าน`, `Inbound`). The 4 primary foreground lanes on the Triam Udom Suksa School side flow southbound from Pathum Wan towards Sam Yan (`Inbound`); only a minor strip of the opposite northbound carriageway is visible at the far top-left. `V1.0` baseline confirmed with no changes needed.
- **Quantitative Impact (Before -> After):** None (`0` metadata / `0` image changes).

#### `CHG-016` -- `2026-11-15` (`cam_id=432` Peer QA Metadata & Direction Update)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=432`)
- **Problem Found:**
  - `V1.0` metadata used a generic label (`บริเวณแยกสามย่าน (ถนนพญาไท-พระรามที่ 4)` / `Sam Yan Intersection (Phayathai-Rama 4 Road)`) with `direction="None"`.
  - Visual inspection of `cctv_images/432/` (`432_20260828_150521.jpg`, `432_20260825_060937.jpg`, `432_20260825_091020.jpg`, `432_20260831_205021.jpg`) and solar shadow / left-hand-traffic geometry at `(13.73258, 100.52896)` confirm the camera faces East along Rama 4 Road under the Thai-Japanese Flyover, capturing a single clear westbound incoming carriageway (`4` main straight lanes stopping at the `MC` box + `1` left-turn slip lane onto Si Phraya Road) carrying traffic from the Silom / Sala Daeng / Henri Dunant side towards Saphan Lueang / Hua Lamphong (`Inbound`). The opposing eastbound carriageway sits behind the median shrubs and flyover piers, mostly occluded.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[432]` in `00_data_cleaning_and_qa/src/clean_dataset_v1.py`:
    - `location_detail_th` -> `"รถมาจากสีลม มุ่งหน้าไปหัวลำโพง (บริเวณแยกสามย่าน ถนนพระรามที่ 4)"`
    - `location_detail_en` -> `"From Silom towards Hua Lamphong (Sam Yan Intersection, Rama 4 Road)"`
    - `direction` -> `"Inbound"`
- **Quantitative Impact (Before -> After):**
  - `location_detail_th`: `บริเวณแยกสามย่าน (ถนนพญาไท-พระรามที่ 4)` -> `รถมาจากสีลม มุ่งหน้าไปหัวลำโพง (บริเวณแยกสามย่าน ถนนพระรามที่ 4)`
  - `location_detail_en`: `Sam Yan Intersection (Phayathai-Rama 4 Road)` -> `From Silom towards Hua Lamphong (Sam Yan Intersection, Rama 4 Road)`
  - `direction`: `"None"` -> `"Inbound"`
  - Images affected: `0` (`604` clean images retained).
- **Verification:** `python -m py_compile 00_data_cleaning_and_qa/src/clean_dataset_v1.py` & module import passed; awaiting final dataset regeneration.

#### `CHG-017` -- `2026-11-15` (`cam_id=542` Peer QA Verification — No Changes Needed)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=542`)
- **Findings:** Verified `cctv_images/542/` (`608` clean images, min size `15,778` bytes; inspected `542_20260825_060939.jpg`, `542_20260828_150523.jpg`, `542_20260831_210021.jpg`) and `CAMERA_CURATION[542]` (`ทางแยกหลังสวน (สารสิน-หลังสวน)`, `แยกสารสิน-หลังสวน ริมสวนลุมพินี`, `Pathum Wan`, `direction="None"`). View clearly shows Sarasin Rd (`3` eastbound lanes on the left, `3` westbound lanes on the right) beside Lumphini Park with Lang Suan Rd joining at the bottom-left (`PT-11-C1`). `V1.0` baseline confirmed with no changes needed.
- **Quantitative Impact (Before -> After):** None (`0` metadata / `0` image changes).

#### `CHG-018` -- `2026-11-15` (`cam_id=619` Peer QA Verification — No Changes Needed)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=619`)
- **Findings:** Verified `cctv_images/619/` (`607` clean images, min size `11,591` bytes; inspected `619_20260825_060940.jpg`, `619_20260828_150524.jpg`, `619_20260825_173024.jpg`, `619_20260831_205524.jpg`) and `CAMERA_CURATION[619]` (`ทางแยกอังรีดูนังต์`, `บริเวณแยกอังรีดูนังต์`, `Pathum Wan`, `direction="None"`). Camera `PT-06-CH2` captures multi-directional junction traffic at Henri Dunant Intersection under the Thai-Japanese Flyover across Henri Dunant Rd and Rama 4 Rd. `V1.0` baseline confirmed with no changes needed.
- **Quantitative Impact (Before -> After):** None (`0` metadata / `0` image changes).

#### `CHG-019` -- `2026-11-15` (`cam_id=277` Peer QA Roundabout & Direction Correction)
- **Editor:** เฟิร์ม (`@nontaphatfirm`)
- **Batch / Scope:** Batch 3 (`cam_id=277`)
- **Problem Found:**
  - `V1.0` carried over the raw CSV mislabeling `"Footbridge near Soi Rang Nam on Phayathai Road (Victory Monument)"` / `"รถมุ่งหน้าไปแยกพญาไท (ซอยรางน้ำ)"` and `"Inbound"`, even though coordinates `(13.76429, 100.53867)` (`26 m` from Phayathai Island bus stop) and camera `RW-3-3-CAM2` (`277_20260825_060939.jpg`, `277_20260828_151024.jpg`, `277_20260831_205524.jpg`) actually look across the **Victory Monument Roundabout** (central roundabout grass island on the far left, BTS viaduct & skywalk over the Phayathai Island bus bays at top). Traffic circulates around the roundabout and splits/enters across multiple branches (Phayathai Rd, Ratchawithi Rd, Phahon Yothin Rd, Din Daeng Rd), not a single `Inbound` stream towards Phayathai Intersection.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION[277]` in `00_data_cleaning_and_qa/src/clean_dataset_v1.py`:
    - `location_th` -> `"วงเวียนอนุสาวรีย์ชัยสมรภูมิ"`
    - `location_detail_th` -> `"บริเวณวงเวียนอนุสาวรีย์ชัยสมรภูมิ (มุมเกาะพญาไท เห็นรถวนรอบวงเวียนและแยกออกหลายทิศทาง)"`
    - `location_en` -> `"Victory Monument Roundabout"`
    - `location_detail_en` -> `"Victory Monument Roundabout (Phayathai Island side, multi-directional roundabout traffic)"`
    - `direction` -> `None`
- **Quantitative Impact (Before -> After):**
  - `location_th`: `ทางแยกอนุสาวรีย์ชัยสมรภูมิ` -> `วงเวียนอนุสาวรีย์ชัยสมรภูมิ`
  - `location_en`: `Footbridge near Soi Rang Nam on Phayathai Road (Victory Monument)` -> `Victory Monument Roundabout`
  - `location_detail_th`: `รถมุ่งหน้าไปแยกพญาไท (ซอยรางน้ำ)` -> `บริเวณวงเวียนอนุสาวรีย์ชัยสมรภูมิ (มุมเกาะพญาไท เห็นรถวนรอบวงเวียนและแยกออกหลายทิศทาง)`
  - `location_detail_en`: `From Victory Monument towards Phayathai Intersection` -> `Victory Monument Roundabout (Phayathai Island side, multi-directional roundabout traffic)`
  - `direction`: `"Inbound"` -> `None`
  - Images affected: `0` (`606` clean images retained).
- **Verification:** `python -m py_compile 00_data_cleaning_and_qa/src/clean_dataset_v1.py` & module import passed; awaiting final dataset regeneration.

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

