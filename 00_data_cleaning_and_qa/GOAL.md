# Task 00: Automated Image Quality Gate & Metadata Cleansing (`GOAL.md`)

> **Module Owner:** All 6 Team Members *(Initial Pipeline Executed; Distributed Peer QA in Progress)*  
> **Implementation Script:** [`src/clean_dataset_v1.py`](src/clean_dataset_v1.py)  
> **Output Directory:** [`Dataset_Clean_V1/`](../Dataset_Clean_V1/README.md)  
> **Audit Checklist:** [`CAMERA_AUDIT_CHECKLIST.md`](CAMERA_AUDIT_CHECKLIST.md)

---

## 1. Objective & Scope

Before running object detection or spatio-temporal traffic modeling, raw CCTV streams must be sanitized to prevent corrupted frames and misaligned metadata from biasing downstream models. This module implements:

1. **A 5-Stage Automated Image Quality Gate** inspecting all **61,319 raw images** across 100 cameras and isolating **1,109 defective frames (1.81%)**, leaving **60,210 valid frames (98.19%)**.
2. **ASCII Filename Standardization** (`<cam_id>_<YYYYMMDD_HHMMSS>.jpg`) to eliminate Windows OpenCV (`cv2.imread`) Unicode path failures caused by Thai characters in raw filenames.
3. **Metadata Cleansing & Spatial Enrichment** repairing misaligned `location_en` rows, stripping system noise (`connect BMAcctv`, `17/5000`, `(See Yellow)`), restoring 28-character truncated Thai location strings, and adding `district`, `corridor`, `pair_id`, `pair_type`, and `direction`.

---

## 2. The 5-Stage Automated Image Quality Gate

Executed via [`src/clean_dataset_v1.py`](src/clean_dataset_v1.py) and logged in [`Dataset_Clean_V1/image_quality_manifest.parquet`](../Dataset_Clean_V1/image_quality_manifest.parquet):

| Stage | Quality Status (`status`) | Detection Rule & Technical Fingerprint | Frames Filtered |
| :---: | :--- | :--- | :---: |
| **Gate 1** | `white_error` | `file_size < 2,000 bytes` OR `brightness_mean >= 254.5` (blank white HTTP placeholder images during stream timeouts) | **504** |
| **Gate 2** | `no_signal_error` | `file_size == 8,782 bytes` OR (`8,700 <= file_size <= 8,900` with `127.5 <= brightness_mean <= 128.5` and `contrast_std >= 111.0`), capturing `gst-launch-0.10` rainbow test bars on Cameras `432` (17 frames) and `1804` (16 frames) | **33** |
| **Gate 3** | `corrupt_color` | **Gray P-Frame:** `127.0 <= brightness_mean <= 132.0` and `contrast_std < 16.0` (11 frames); **Green Screen (YUV Drop):** `g_mean - r_mean > 40.0` and `g_mean - b_mean > 40.0` (8 frames). *(32 valid frames with mild bottom-strip artifacts are retained and tagged in `quality_warning`)* | **19** |
| **Gate 4** | `frozen` | Pixel-wise Mean Absolute Difference `mad_from_prev == 0.0` against the preceding valid frame of the same camera (e.g., Cam `150`: 124 frozen frames; Cam `938`: 98; Cam `939`: 95; Cam `206`: 95; Cam `395`: 72) | **553** |
| **Gate 5** | `valid` | Strict timestamp extraction from filename (`_YYYYMMDD_HHMMSS.jpg`), bypassing on-screen display (OSD) text due to `1970-01-01` CMOS battery resets | **60,210** *(Valid)* |

---

## 3. Metadata Cleansing & Spatial Enrichment (`cctv_info_cleaned`)

The raw `Dataset/cctv_info.csv` contained severe row-shift errors and truncated text. Version 1 cleansing in [`Dataset_Clean_V1/cctv_info_cleaned.parquet`](../Dataset_Clean_V1/cctv_info_cleaned.parquet) performs:

1. **English Location Realignment:** Reconciles shifted `location_en` entries against actual `(lat, lon)` coordinates and Thai camera labels (e.g., Cam `529` at Phutthamonthon Sai 2 was previously mislabeled as Henri Dunant; Cam `619` at Henri Dunant was mislabeled as Ratchathewi).
2. **Corridor Assignment (`corridor`):** Categorizes all 100 cameras into **7 major urban corridors** (verified in `cctv_info_cleaned.parquet`):
   - `Old Town - Dusit - Rama 5` (32 cameras)
   - `Ratchadaphisek` (18 cameras)
   - `Thon Buri - Charoen Nakhon - Borommaratchachonnani` (14 cameras)
   - `Phahon Yothin - Lat Phrao` (12 cameras)
   - `Pathum Wan - Phetchaburi - Victory Monument` (11 cameras)
   - `Sathon - Naradhiwas - Rama 3` (10 cameras)
   - `East Bangkok (Ramkhamhaeng - On Nut)` (3 cameras)
3. **Directional & Pair Classification (`pair_id`, `pair_type`, `direction`):**
   - Classifies flow orientation into `Inbound` (51 cameras), `Outbound` (29 cameras), and `None` (20 wide-angle intersection cameras).
   - Identifies **6 True Bidirectional Footbridge Pairs (`footbridge_bidirectional`)** (`136/137`, `178/179`, `126/127`, `224/225`, `176/177`, `1132/1078`) for reversible-lane tidal analysis in Task 04.

---

## 4. Team Peer-Review Protocol (Action Required by All 6 Members)

To ensure 100% metadata accuracy before locking the final tables:

1. Open [`CAMERA_AUDIT_CHECKLIST.md`](CAMERA_AUDIT_CHECKLIST.md), where the 100 cameras are divided into **6 batches (16-17 cameras per member)**: Batch 1 (**ปลื้ม**), Batch 2 (**กร**), Batch 3 (**เฟิร์ม**), Batch 4 (**สอง**), Batch 5 (**นิว**), Batch 6 (**โม่**).
2. Cross-check your assigned cameras against sample images in `Dataset_Clean_V1/cctv_images/<cam_id>/` and Google Maps `(lat, lon)`:
   - Verify `location_en` and `location_th` match the physical road/intersection.
   - Verify `district` and `corridor` assignments are geographically sound.
   - Verify `direction` (`Inbound` vs. `Outbound`) and `pair_id` groupings match the actual traffic flow direction.
3. If any correction is needed, update `CAMERA_CURATION` in [`src/clean_dataset_v1.py`](src/clean_dataset_v1.py), log the change with exact Before -> After impact in [`../Dataset_Clean_V1/CLEANING_CHANGELOG.md`](../Dataset_Clean_V1/CLEANING_CHANGELOG.md), and re-run:

   ```bash
   python 00_data_cleaning_and_qa/src/clean_dataset_v1.py --skip-copy
   ```

   *(Re-running `--skip-copy` preserves [`../Dataset_Clean_V1/README.md`](../Dataset_Clean_V1/README.md) and [`CLEANING_CHANGELOG.md`](../Dataset_Clean_V1/CLEANING_CHANGELOG.md) unless `--overwrite-readme` is explicitly passed.)*

---

## 5. Definition of Done

- [x] Execute 5-stage Automated Image Quality Gate across all 61,319 images (`Dataset_Clean_V1/`).
- [x] Generate `cctv_info_cleaned.parquet` and `image_quality_manifest.parquet`.
- [x] Document `V1.0` cleaning rules, team audit guide, and version changelog in [`Dataset_Clean_V1/README.md`](../Dataset_Clean_V1/README.md) and [`Dataset_Clean_V1/CLEANING_CHANGELOG.md`](../Dataset_Clean_V1/CLEANING_CHANGELOG.md).
- [ ] All 6 team members complete their assigned 16-17 camera verifications in [`CAMERA_AUDIT_CHECKLIST.md`](CAMERA_AUDIT_CHECKLIST.md) and log any data fixes in [`CLEANING_CHANGELOG.md`](../Dataset_Clean_V1/CLEANING_CHANGELOG.md).
