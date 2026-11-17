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
| `CHG-003` | `2026-11-15` | `V1.1` | กร (@kkooAAA) | Batch 2 (16 cams): `1815, 136, 137, 139, 141, 170, 176, 177, 178, 179, 1070, 1071, 1112, 938, 939, 1804` | District mismatch on `938`, `1815`; no defective frames missed by automated gates | Updated `district` in `CAMERA_CURATION`; no `MANUAL_EXCLUDED_IMAGES` added; open items logged for maintainer (see V1.1 Batch 2 entry) | `938` district: Suan Luang -> Bang Kapi; `1815` district: Huai Khwang -> Din Daeng; images `9,535 -> 9,535` (0 excluded) | Yes (`clean_dataset_v1.py`) |
| `CHG-004` | `2026-11-15` | `V1.1` | กร (@kkooAAA) | `cam_id=1815` / `18` images | Camera view changed (~180° reverse pan) from `2026-08-31 18:10:44` to end of capture; frames no longer match `location_detail` / `direction` | **Following the PM's instruction**, added the `18` changed-view filenames to `MANUAL_EXCLUDED_IMAGES` (reason `camera_view_changed`); original-view frames kept | `1815` valid images: `611 -> 593`; Batch 2: `9,535 -> 9,517`; no other camera affected | Yes (`clean_dataset_v1.py`) |
| `CHG-005` | `2026-11-16` | `V1.1` | กร (@kkooAAA) | Batch 2 location audit: `1112` (changed); `939`, `170`, `1071`, `1804`, `1815`, `178`, `179` (verified) | `1112` labelled with the wrong road (Vibhavadi Rangsit) although it views Sutthisan Winitchai Road; `1815` road recorded as Asok-Din Daeng in `CHG-003` | Updated `location_en` / `location_th` (`1112`) in `CAMERA_CURATION`; `1815` road clarified as Rama 9 Road (documentation only); other cameras verified unchanged | `1112` road: Vibhavadi Rangsit -> Sutthisan Winitchai; images unchanged (`9,517`) | Yes (`clean_dataset_v1.py`) |
| `CHG-006` | `2026-11-17` | `V1.1` | กร (@kkooAAA) | `939`, `1112`, `1804` | `939` detail named Ramkhamhaeng Road instead of Ramkhamhaeng Bridge; `1112` / `1804` detail and `direction` did not match the camera view | Updated `location_detail_th/en` (`939`, `1112`, `1804`), `location_th/en` (`1112`, back to Vibhavadi Rangsit Road, supersedes `CHG-005`) and `direction` (`1112`, `1804`) in `CAMERA_CURATION` | `1112` direction: Inbound -> None; `1804` direction: Outbound -> None; direction totals `51/29/20 -> 50/28/22` (Inbound/Outbound/None); images unchanged | Yes (`clean_dataset_v1.py`) |
| `CHG-007` | `2026-11-17` | `V1.1` | กร (@kkooAAA) | `cam_id=1112` | Road name: camera views Sutthisan Winitchai Road, not Vibhavadi Rangsit Road | Updated `location_th/en` and `location_detail_th/en` in `CAMERA_CURATION` to Sutthisan Winitchai Road (supersedes the `CHG-006` road revert); `direction` unchanged (`None`) | `location_th`: `แยกสุทธิสาร (ถนนวิภาวดีรังสิต)` -> `แยกสุทธิสาร (ถนนสุทธิสารวินิจฉัย)`; `location_en`: `Sutthisan Intersection (Vibhavadi Rangsit Road)` -> `Sutthisan Intersection (Sutthisan Winitchai Road)` (same for `location_detail_th/en`) | Yes (`clean_dataset_v1.py`) |

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

#### Batch 2 Peer Audit (`CHG-003`)
- **Date:** 2026-11-15
- **Editor:** กร (@kkooAAA)
- **Batch / Scope:** Batch 2 (16 cameras): `1815, 136, 137, 139, 141, 170, 176, 177, 178, 179, 1070, 1071, 1112, 938, 939, 1804` -- image sweep of all valid frames + metadata check.
- **Problem Found:**
  - `cam_id=938`: `district` was `Suan Luang`; coordinates `(13.74761, 100.60591)` fall in **Bang Kapi** district (verified on Google Maps).
  - `cam_id=1815`: `district` was `Huai Khwang`; coordinates `(13.75599, 100.56481)` fall on Asok-Din Daeng Road, **Din Daeng** (verified on Google Maps). **-> Road clarified by `CHG-005`:** the camera views **Rama 9 Road** (final documented road); the district fix (`Din Daeng`) stands.
  - `cam_id=1112`: `district` `Din Daeng` confirmed on Google Maps (intersection lies on the Phaya Thai / Din Daeng boundary) -- no change.
  - Direction check: `direction` of all `16` cameras manually verified by comparing CCTV images with Google Maps -- all match existing values (e.g., `141`: `Outbound` verified; `170`: `Outbound` verified; `1815`: `Inbound` verified for the original view).
  - Image sweep: all `9,535` valid frames inspected (contact sheets of every frame, day and night, plus full-size checks of suspicious frames). `0` unreadable, `0` pitch-black, `0` blocked, `0` corrupted frames found beyond what Gates 1-5 already removed.
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION` in `clean_dataset_v1.py`: `938` and `1815` `district`.
  - No entries added to `MANUAL_EXCLUDED_IMAGES`. Rainy, wet-road, and headlight-glare frames preserved (e.g., rain-smeared lens frame `938_20260829_151005.jpg` kept intentionally).
  - All `direction` values verified and left unchanged.
- **Quantitative Impact (Before -> After):**
  - Metadata fields changed: `938` `district`: Suan Luang -> Bang Kapi; `1815` `district`: Huai Khwang -> Din Daeng.
  - Images affected: `0` valid images (`9,535` -> `9,535`).
- **Open Items for Maintainer (not changed in this PR):**
  - `cam_id=1815` **view change:** camera view changed between `1815_20260831_180044.jpg` (last original view) and `1815_20260831_181044.jpg` (first new view) -- likely a ~180° pan at the same site (same noise-barrier style on the elevated road, which flips from left to right; the same grey dome fixture moves from the left to the right frame edge; same `352x288` resolution and `:x0:44` capture cadence). `18` valid frames (`2026-08-31 18:10:44` to `21:00:44`) show the reverse view; the other `597` frames (`593` valid) show the original view. `location_detail_th/en` and `direction` do not describe these `18` frames. Not excluded -- maintainer / Task 03 owner to decide (e.g., exclude, or handle as a separate view for median background / ROI). **-> Resolved by `CHG-004`** (excluded following the PM's instruction).
  - `cam_id=1112` road name: frames suggest the camera faces east along **Sutthisan Winitchai Road** (sunrise straight ahead on 28 Aug 06:45), not Vibhavadi Rangsit. Possible fix: `location_en` -> `Sutthisan Intersection (Sutthisan Winitchai Road)`, `location_th` -> `แยกสุทธิสาร (ถนนสุทธิสารวินิจฉัย)`. Not applied -- needs Street View confirmation. **-> Resolved by `CHG-005`** (confirmed and applied).
  - `Inbound` / `Outbound` definition is not documented in `DATA_CONTRACT.md`; existing labels imply "towards / away from central Bangkok". Suggest documenting it.
  - **Google Drive duplicates (informational only):** `28` duplicate files exist in `Dataset_Clean_V1/cctv_images/` on Drive -- `18` in `136/` (e.g., `136_20260825_111611.jpg`) and `10` in `176/` (e.g., `176_20260829_085616.jpg`); each filename appears twice with identical size, and downloaded copies are byte-for-byte identical. They do **not** affect the dataset (each image appears once in `image_quality_manifest.parquet`). They must **NOT** be added to `MANUAL_EXCLUDED_IMAGES` (that would exclude the valid original frame). Suggest removing the extra copies during the `V2.0` Drive sync.
- **Verification:** PR (`chore/00-qa-kkooAAA` -> `main`) -> Final `clean_dataset_v1.py` + `run_pipeline.py --check-contract` `[Pending Maintainer Run]`

#### Camera 1815 View-Change Exclusion (`CHG-004`)
- **Date:** 2026-11-15
- **Editor:** กร (@kkooAAA)
- **Batch / Scope:** `cam_id=1815` only -- follow-up to the Batch 2 open item (`CHG-003`).
- **Problem Found:**
  - `cam_id=1815`: camera view changed (~180° reverse pan at the same site) between `1815_20260831_180044.jpg` (last original-view frame) and `1815_20260831_181044.jpg` (first changed-view frame). The changed view lasts until the camera's last capture, `1815_20260831_210044.jpg`. These frames do not match the camera's `location_detail_th/en` or `direction` (`Inbound`).
- **Fix / Decision Applied:**
  - **Following the PM's instruction**, added the `18` changed-view frames to `MANUAL_EXCLUDED_IMAGES` in `clean_dataset_v1.py` with reason `camera_view_changed`:
    - `1815_20260831_181044.jpg`, `1815_20260831_182046.jpg`, `1815_20260831_183044.jpg`, `1815_20260831_184044.jpg`, `1815_20260831_185044.jpg`, `1815_20260831_190044.jpg`,
    - `1815_20260831_191044.jpg`, `1815_20260831_192044.jpg`, `1815_20260831_193044.jpg`, `1815_20260831_194046.jpg`, `1815_20260831_195044.jpg`, `1815_20260831_200044.jpg`,
    - `1815_20260831_201046.jpg`, `1815_20260831_202044.jpg`, `1815_20260831_203044.jpg`, `1815_20260831_204044.jpg`, `1815_20260831_205044.jpg`, `1815_20260831_210044.jpg`.
  - All original-view frames (up to and including `1815_20260831_180044.jpg`) are kept.
  - Existing `CAMERA_CURATION` values (including the `CHG-003` `district` fix and the `direction` values) are unchanged.
  - No CSV / Parquet files and no Google Drive files were modified in this PR.
- **Quantitative Impact (Before -> After):**
  - Metadata fields changed: none.
  - Images affected: `18` valid images excluded -- `cam_id=1815`: `611 -> 593` valid (`615` raw); Batch 2: `9,535 -> 9,517`. No other camera affected.
- **Verification:** All `18` filenames exist in `image_quality_manifest.parquet` as `is_valid=True`, `cam_id=1815`, timestamps `2026-08-31 18:10:44` to `21:00:44` (the camera's last frame); boundary frames checked visually. PR (`chore/00-qa-kkooAAA` -> `main`) -> Final `clean_dataset_v1.py` + `run_pipeline.py --check-contract` `[Pending Maintainer Run]`

#### Batch 2 Location Metadata Audit (`CHG-005`)
- **Date:** 2026-11-16
- **Editor:** กร (@kkooAAA)
- **Batch / Scope:** Batch 2 location check of road name, intersection, camera facing, and traffic direction -- `1112`, `939`, `170`, `1071`, `1804`, `1815`, `178`, `179` (manual check on Google Maps / Street View + CCTV frames, with an OpenStreetMap POI cross-check).
- **Problem Found:**
  - `cam_id=1112`: `location_en` / `location_th` named **Vibhavadi Rangsit Road**, but the camera faces east along **Sutthisan Winitchai Road** (OSD `TF-DD-S10-04`; two-way shophouse street, no Vibhavadi frontage road or Don Mueang Tollway in view). Traffic in view is westbound, coming from Ratchada-Sutthisan Intersection (`Inbound`).
  - `cam_id=1815`: `CHG-003` recorded the camera as being on **Asok-Din Daeng Road**; the manually confirmed road is **Rama 9 Road**.
- **Fix / Decision Applied:**
  - `1112` **(superseded by `CHG-006`: road set back to Vibhavadi Rangsit Road)**: `location_en`: `Sutthisan Intersection (Vibhavadi Rangsit Road)` -> `Sutthisan Intersection (Sutthisan Winitchai Road)`; `location_th`: `แยกสุทธิสาร (ถนนวิภาวดีรังสิต)` -> `แยกสุทธิสาร (ถนนสุทธิสารวินิจฉัย)`. `location_detail_th/en` (`From Ratchada-Sutthisan Intersection`), `direction` (`Inbound`), and `district` (`Din Daeng`) already correct -- unchanged. The district is kept as `Din Daeng` even though the raw coordinate falls about `30 m` inside Phaya Thai on an OSM boundary lookup; it is not changed on coordinate-based boundary ambiguity alone.
  - `939`: name kept as `Mahadthai Intersection` / `Mahadthai Intersection (Ramkhamhaeng Road)` to match the Dashboard, which is the source of truth for naming. The camera OSD spells it `Mahatthai`; that spelling is **not** adopted. No change.
  - `1815` road clarification: the final documented road is **Rama 9 Road** (Rama 9 Intersection). This supersedes the `Asok-Din Daeng Road` wording in `CHG-003`, which is kept for history. No metadata value depends on it, so nothing in `CAMERA_CURATION` changed.
  - Verified, no change needed:
    - `170`: faces south, northbound traffic, `Outbound` (Nawutti Somdet Ya Hospital reference kept).
    - `1071`: Kamphaeng Phet Intersection, faces south, southbound traffic, `Inbound`.
    - `1804`: entrance to Soi On Nut 33, faces east, eastbound traffic, `Outbound`.
    - `1815`: Rama 9 Road / Rama 9 Intersection, `Din Daeng`, faces east, westbound (into the city) = `Inbound`. The `18` `camera_view_changed` exclusions from `CHG-004` are kept.
    - `1815` `location_detail`: manually confirmed that traffic travels from Phang Mueang Intersection toward Rama 9 Intersection. The existing `From Phang Mueang Intersection` / `หน้ารถมาจากแยกผังเมือง` is correct and retained -- no metadata change needed.
  - `178` / `179`: extra location references (approx. `180 m` / `120 m` after turning right from Phyathai 2 Hospital, accepted as approximate references) recorded as code comments in `CAMERA_CURATION` -- there is no schema field for them, so no metadata value changed.
  - No `MANUAL_EXCLUDED_IMAGES` changes. No CSV / Parquet or Google Drive files modified.
- **Quantitative Impact (Before -> After):**
  - Metadata fields changed: `1112` `location_en`, `location_th` (`2` fields, `1` camera).
  - Images affected: `0` (Batch 2 valid images stay `9,517`).
- **Open Items for Maintainer:**
  - Regenerated outputs will also pick up the `CHG-003` district fixes for `938` / `1815`, which are not yet in the current CSV / Parquet.
- **Verification:** `clean_dataset_v1.py` syntax check passed; `CAMERA_CURATION` still holds all `100` cameras and only the `2` fields above differ from the previous commit; `1815` exclusions = `18`. PR (`chore/00-qa-kkooAAA` -> `main`) -> Final `clean_dataset_v1.py` + `run_pipeline.py --check-contract` `[Pending Maintainer Run]`

#### Batch 2 Location Detail & Direction Fix (`CHG-006`)
- **Date:** 2026-11-17
- **Editor:** กร (@kkooAAA)
- **Batch / Scope:** `939`, `1112`, `1804` (metadata only).
- **Fix / Decision Applied:**
  - `939`: `location_detail_th`: `บริเวณแยกมหาดไทย (ถนนรามคำแหง)` -> `บริเวณแยกมหาดไทย (สะพานรามคำแหง)`; `location_detail_en`: `Mahadthai Intersection (Ramkhamhaeng Road)` -> `Mahadthai Intersection (Ramkhamhaeng Bridge)`. `direction` stays `None`.
  - `1112`: `location_detail_th`: `รถมาจากแยกรัชดา-สุทธิสาร` -> `แยกสุทธิสาร (ถนนวิภาวดีรังสิต)`; `location_detail_en`: `From Ratchada-Sutthisan Intersection` -> `Sutthisan Intersection (Vibhavadi Rangsit Road)`; `direction`: `Inbound` -> `None`; `location_th`: `แยกสุทธิสาร (ถนนสุทธิสารวินิจฉัย)` -> `แยกสุทธิสาร (ถนนวิภาวดีรังสิต)`; `location_en`: `Sutthisan Intersection (Sutthisan Winitchai Road)` -> `Sutthisan Intersection (Vibhavadi Rangsit Road)`, so name and detail name the same road. This supersedes the `CHG-005` road change (kept for history).
  - `1804`: `location_detail_th`: `ท้ายรถมุ่งหน้าแยกสวนหลวง` -> `ปากซอยอ่อนนุช 33 ถนนอ่อนนุช`; `location_detail_en`: `Towards Suan Luang Intersection` -> `Entrance to Soi On Nut 33 on On Nut Road`; `direction`: `Outbound` -> `None`.
  - No `MANUAL_EXCLUDED_IMAGES` changes. No CSV / Parquet files modified (regenerate with `clean_dataset_v1.py`).
- **Quantitative Impact (Before -> After):**
  - Metadata fields changed: `10` fields across `3` cameras.
  - `direction` totals: `Inbound 51 -> 50`, `Outbound 29 -> 28`, `None 20 -> 22`. Images affected: `0`.
- **Open Items for Maintainer:**
  - Direction totals `51 / 29 / 20` are still quoted in `DATA_CONTRACT.md`, `00_data_cleaning_and_qa/GOAL.md`, `04_ds_traffic_analytics/GOAL.md`, `06_bi_dashboard/GOAL.md`, `Dataset_Clean_V1/README.md`, `Info/Project Ideas.md`, and `BKK_Pulse_Team_Guide.html`.
  - `cctv_info_cleaned.csv` / `.parquet` not yet regenerated -- rerun `clean_dataset_v1.py` with the raw `Dataset/` folder.

#### Batch 2 Location Road Fix (`CHG-007`)
- **Date:** 2026-11-17
- **Editor:** กร (@kkooAAA)
- **Batch / Scope:** `1112` (metadata only).
- **Fix / Decision Applied:**
  - `location_th` / `location_detail_th`: `แยกสุทธิสาร (ถนนวิภาวดีรังสิต)` -> `แยกสุทธิสาร (ถนนสุทธิสารวินิจฉัย)`.
  - `location_en` / `location_detail_en`: `Sutthisan Intersection (Vibhavadi Rangsit Road)` -> `Sutthisan Intersection (Sutthisan Winitchai Road)`.
  - Supersedes the `CHG-006` road revert for `1112` (kept for history). `direction` stays `None`. No `MANUAL_EXCLUDED_IMAGES` changes; no CSV / Parquet modified.
- **Quantitative Impact (Before -> After):**
  - Metadata fields changed: `4` fields, `1` camera. Images affected: `0`. Direction totals unchanged.
