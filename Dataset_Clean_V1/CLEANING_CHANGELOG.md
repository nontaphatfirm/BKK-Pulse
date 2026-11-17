# Data Cleaning Version History & Change Log (`CLEANING_CHANGELOG.md`)

> **Purpose:** Single audit trail recording every data-cleaning rule, manual metadata fix, image exclusion, and version transition from `V1.0` onward. This log keeps team collaboration transparent across Google Drive / GitHub and provides exact **Before -> After** statistics for the final project report.

---

## How to Log a Cleaning Change (Mandatory for Every Editor)

> **GitHub-Only Workflow:** Google Drive (`Dataset_Clean_V1/`) is **READ-ONLY** for visual inspection. Do **not** edit/delete/re-upload files on Drive, and do **not** commit directly to `main`. Create your own branch (`chore/00-qa-<your-name>`) and open a **Pull Request (PR)** into `main`.

Whenever you verify a batch, flag broken/corrupted frames to exclude, or edit any camera metadata field:
1. Add **one row** to the **Modification Ledger** below (so we can scan all edits at a glance).
2. Add or append a detailed subsection under **Detailed Version Log** using the copy-paste template at the bottom of this file.
3. Include **exact numbers / `cam_id` / filenames** (Before vs. After) and the **reason** so we can cite it directly in the Data Cleaning & Preparation section of the final report.
4. Apply the fix in [`00_data_cleaning_and_qa/src/clean_dataset_v1.py`](../00_data_cleaning_and_qa/src/clean_dataset_v1.py) (`CAMERA_CURATION` for metadata or `MANUAL_EXCLUDED_IMAGES` for broken/corrupted filenames), mark `[x]` in [`00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md`](../00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md), and open a **PR into `main`**. *(Once all PRs merge, the maintainer runs `clean_dataset_v1.py` and `python run_pipeline.py --check-contract` and syncs the final output to Google Drive.)*

---

## Version Summary Overview

| Version | Date | Status | Raw -> Valid Images | Major Milestone |
| :--- | :---: | :---: | :---: | :--- |
| [`V1.0`](#v10----2026-11-11-initial-automated-quality-gate--metadata-cleansing) | `2026-11-11` | Baseline | `61,319 -> 60,210` (`98.19%`) | 5-Gate Image Filter, ASCII filenames, full 100-camera `CAMERA_CURATION` repair |
| [`V1.1`](#v11----2026-11-17-consolidated-team-peer-qa--batches-1-6) | `2026-11-17` | Superseded | `61,319 -> 60,107` (`98.02%`) | All 6 PRs (`#2, #4, #6, #7, #8, #9`) merged & rebuilt: `56` camera metadata updates, `8` `(lat, lon)` fixes, `103` `manual_excluded` frames; `99/100` visual sweeps complete |
| [`V2.0`](#v20----2026-11-17-final-data-lock--100100-peer-qa-verified--chg-b4-02-resolved) | `2026-11-17` | **Locked Final Data** | `61,319 -> 60,029` (`97.90%`) | `cam_id=225` visual sweep (`100/100` `[x]`); resolved `CHG-B4-02` (`1188` kept `607/607`; `500` `-78` severe corrupt/green frames -> `522`); `0` remaining `quality_warning`s; `DATA_CONTRACT` passed |

---

## Modification Ledger (Team Peer-Audit & Cleaning Fixes)

*(IDs follow `CHG-B<batch>-<seq>` after baseline `CHG-001` to avoid cross-branch numbering collisions.)*

| Log ID | Date (`YYYY-MM-DD`) | Target Version | Editor (Name / GitHub) | Target `cam_id` / Scope | Issue Identified | Cleaning Action Taken | Before -> After Impact | Synced in Script? |
| :--- | :---: | :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| `CHG-001` | `2026-11-11` | `V1.0` | Automated Baseline | All `100` cams / `61,319` imgs | Blank white, rainbow, gray P-frame, green screen, frozen streams, Thai Unicode paths, `1970` OSD dates, corrupted `cctv_info.csv` | Executed 5-Gate pipeline + `CAMERA_CURATION` in `clean_dataset_v1.py` | `61,319 -> 60,210` valid images (`1,109` filtered); `100/100` metadata repaired | Yes (`clean_dataset_v1.py`) |
| `CHG-B1-01` | `2026-11-15` | `V1.1` | ปลื้ม (`@siravidthongsook`) | Batch 1 (`17` cams, Ratchadaphisek — PR #6) | Pair cameras `119/120` & `224/225` swapped `(lat, lon)`; `127` pin on median; `120` labelled `Inbound` despite bidirectional side-arm view; `0` bad frames (`225` visual sweep pending) | Added optional `lat`/`lon` override support in `CAMERA_CURATION` / `build_cleaned_metadata()` + applied `5` coord fixes & `1` `direction` fix | `119/120`, `224/225` pins restored; `127` re-pinned `~25 m` to outbound span; `120`: `Inbound -> None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B2-01` | `2026-11-15` | `V1.1` | กร (`@kkooAAA`) | Batch 2 (`16` cams — PR #7) | District mismatch on `938`, `1815`; no defective frames missed by automated gates (`28` Drive duplicates in `136/176` noted as harmless) | Updated `district` in `CAMERA_CURATION` (`938`, `1815`); logged open items | `938` district: `Suan Luang -> Bang Kapi`; `1815` district: `Huai Khwang -> Din Daeng` | Yes (`clean_dataset_v1.py`) |
| `CHG-B2-02` | `2026-11-15` | `V1.1` | กร (`@kkooAAA`) | `cam_id=1815` (`18` frames — PR #7) | Camera panned ~180° from `2026-08-31 18:10:44` to end of capture; frames no longer match `location_detail` / `direction` | Added the `18` changed-view filenames (`18:10:44`–`21:00:44`) to `MANUAL_EXCLUDED_IMAGES` (`"camera_view_changed"`) | `cam_id=1815`: `611 -> 593` valid images (`-18`) | Yes (`clean_dataset_v1.py`) |
| `CHG-B2-03` | `2026-11-16` | `V1.1` | กร (`@kkooAAA`) | `1112` + Batch 2 location audit (PR #7) | `1112` labelled with Vibhavadi Rangsit Rd instead of Sutthisan Winitchai Rd; `1815` road clarified as Rama 9 Road; `178/179` distance notes verified | Updated `location_en`/`location_th` (`1112`) and added code comments (`178/179`) | `1112` road: `Vibhavadi Rangsit -> Sutthisan Winitchai` | Yes (`clean_dataset_v1.py`) |
| `CHG-B2-04` | `2026-11-17` | `V1.1` | กร (`@kkooAAA`) | `939`, `1112`, `1804` (PR #7) | `939` detail named Ramkhamhaeng Rd instead of Ramkhamhaeng Bridge; `1112`/`1804` detail & `direction` mismatched camera view | Updated `location_detail_th/en` (`939, 1112, 1804`) & `direction` (`1112, 1804`); `1112` temporarily reverted to Vibhavadi (superseded by `CHG-B2-05`) | `1112` `direction`: `Inbound -> None`; `1804` `direction`: `Outbound -> None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B2-05` | `2026-11-17` | `V1.1` | กร (`@kkooAAA`) | `cam_id=1112` (PR #7) | Final confirmation that `1112` views Sutthisan Winitchai Rd, not Vibhavadi Rangsit Rd | Set `location_th/en` & `location_detail_th/en` to Sutthisan Winitchai Rd (supersedes `CHG-B2-04` road revert); `direction="None"` kept | `1112`: `แยกสุทธิสาร (ถนนสุทธิสารวินิจฉัย)` / `Sutthisan Intersection (Sutthisan Winitchai Road)` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-01` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=75` (Batch 3 — PR #2) | `location_detail` misstated Sathu Pradit Expressway instead of BRT median lane inbound from Naradhiwas–Rama 3 Intersection | Updated `CAMERA_CURATION[75]` (`location_detail_th`, `location_detail_en`) | `รถมาจากแยกด่วนสาธุประดิษฐ์ -> รถมาจากแยกนราธิวาส-พระราม 3` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-02` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=88` (Batch 3 — PR #2) | Two-way road with no median (`Chan Rd` near Soi `18/6`); YOLO counts both opposing flows in one frame | Updated `CAMERA_CURATION[88]["direction"]` from `"Inbound"` to `"None"` | `direction`: `Inbound -> None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-03` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=186` (Batch 3 — PR #2) | Peer QA verification of `cctv_images/186/` & metadata | Verified against Google Maps; no broken frames or metadata errors found | No changes (`V1.0` confirmed) | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-04` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=188` (Batch 3 — PR #2) | Peer QA verification of `cctv_images/188/` & metadata | Verified against Google Maps; no broken frames or metadata errors found | No changes (`V1.0` confirmed) | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-05` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=194` (Batch 3 — PR #2) | Metadata listed South Sathon Rd (`Inbound`), whereas imagery shows North Sathon Rd from Witthayu towards Sathon-Naradhiwas (`Outbound`) | Updated `CAMERA_CURATION[194]` (`location_*`, `location_detail_*`, `direction`) | `สาทรใต้ -> สาทรเหนือ`; `Inbound -> Outbound` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-06` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=196` (Batch 3 — PR #2) | Peer QA verification of `cctv_images/196/` & metadata | Verified against Google Maps; no broken frames or metadata errors found | No changes (`V1.0` confirmed) | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-07` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=206` (Batch 3 — PR #2) | Camera sits opposite Soi Naradhiwas 20 (`Outbound`, east carriageway); `6` unusable frames (`5` severe gray P-frame, `1` central lens smear) slipped past Gates | Updated `CAMERA_CURATION[206]` (`location_*`, `direction`, `lat=13.70555`, `lon=100.53865`) + added `6` files to `MANUAL_EXCLUDED_IMAGES` | `ใกล้ซอย -> ตรงข้ามซอย`; `Inbound -> Outbound`; `-6` images (`5` `corrupt_artifact`, `1` `blocked_lens`) | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-08` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=211` (Batch 1 cross-check — PR #2) | Peer QA verification of `cctv_images/211/` & metadata | Verified all images & metadata; no broken frames or metadata errors found | No changes (`V1.0` confirmed) | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-09` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=599` (Batch 3 — PR #2) | Wide Surasak Intersection view capturing cross-traffic & both carriageways simultaneously | Changed `CAMERA_CURATION[599]["direction"]` from `"Inbound"` to `"None"` | `direction`: `Inbound -> None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-10` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=603` (Batch 3 — PR #2) | `location_detail` stated Surasak Intersection; main corridor ahead is Naradhiwas Rd Northbound fed from Sathon-Naradhiwas | Updated `CAMERA_CURATION[603]` (`location_detail_th`, `location_detail_en`) | `รถมาจากแยกสุรศักดิ์ -> รถมาจากแยกสาทร-นราธิวาส` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-11` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=604` (Batch 3 — PR #2) | Full 4-way Silom–Naradhiwas junction view capturing both Naradhiwas flows + Silom cross-traffic; old label cited off-axis `แยกศาลาแดง` | Updated `CAMERA_CURATION[604]` (`location_detail_*`, `direction="None"`) | Detail updated; `direction`: `Inbound -> None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-12` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=11` (Batch 3 — PR #2) | Divided 5-lane Ratchawithi Rd shows all 3 eastbound (`Outbound`) + 2 westbound (`Inbound`) lanes together | Updated `CAMERA_CURATION[11]` (`location_detail_*`, `direction="None"`) | Detail updated; `direction`: `Outbound -> None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-13` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=82` (Batch 3 — PR #2) | Old label only described the 1 southbound contraflow bus lane; 4 main lanes flow northbound (`Outbound`) | Updated `CAMERA_CURATION[82]` (`location_detail_*`, `direction="None"`) | Detail updated (4+1 lanes); `direction`: `Inbound -> None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-14` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=239` (Batch 3 — PR #2) | Peer QA verification of `cctv_images/239/` & metadata | Confirmed 4 primary southbound `Inbound` lanes in front of Triam Udom Suksa School | No changes (`V1.0` confirmed) | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-15` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=432` (Batch 3 — PR #2) | Generic label with `direction="None"`, whereas imagery shows clear westbound incoming approach on Rama 4 Rd from Silom towards Hua Lamphong (`Inbound`) | Updated `CAMERA_CURATION[432]` (`location_detail_*`, `direction="Inbound"`) | Detail clarified; `direction`: `None -> Inbound` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-16` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=542` (Batch 3 — PR #2) | Peer QA verification of `cctv_images/542/` & metadata | Confirmed bidirectional Sarasin–Lang Suan view (`direction="None"`); no bad frames | No changes (`V1.0` confirmed) | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-17` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=619` (Batch 3 — PR #2) | Peer QA verification of `cctv_images/619/` & metadata | Confirmed multi-directional Henri Dunant junction view (`direction="None"`); no bad frames | No changes (`V1.0` confirmed) | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-18` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=277` (Batch 3 — PR #2) | Mislabelled as footbridge near Soi Rang Nam (`Inbound`), whereas `(13.76429, 100.53867)` captures Victory Monument Roundabout (Phayathai Island side) | Updated `CAMERA_CURATION[277]` (`location_*`, `location_detail_*`, `direction="None"`) | `Victory Monument Roundabout`; `direction`: `Inbound -> None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-01` | `2026-11-15` | `V1.1` | สอง (`@theme222`) | `cam_id=26`, `cam_id=1195` (Batch 4 — PR #4) | Both cameras watch Charoen Nakhon Rd from opposite sides of Bukkhalo Intersection; `1195` faces `Outbound` rather than `Inbound` | Updated `pair_id`, `pair_type`, and `1195` `location_*` / `direction` | `PAIR_JX_BUKKHALO -> PAIR_ARM_BUKKHALO`; `perpendicular_junction -> opposite_intersection_arm`; `1195`: `Inbound -> Outbound` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-02` | `2026-11-15` | `V1.1` -> `V2.0` | สอง (`@theme222`) | `cam_id=500`, `cam_id=1188` (Batch 4 — PR #4) | `500` has `>10%` artifact images; `1188` wide-angle nighttime frames show tiny vehicles & heavy glare | Logged downstream exclusion proposal in `V1.1`; **resolved in `CHG-V2-02`** | Superseded/Resolved by `CHG-V2-02` (`100`-cam contract preserved) | Yes (`CHG-V2-02`) |
| `CHG-B4-03` | `2026-11-15` | `V1.1` | สอง (`@theme222`) | `cam_id=32` (Batch 4 — PR #4) | View clearly captures both opposing flows along Thoet Thai Rd | Set `CAMERA_CURATION[32]["direction"]` to `"None"` | `direction`: `Inbound -> None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-04` | `2026-11-15` | `V1.1` | สอง (`@theme222`) | `cam_id=36` (Batch 4 — PR #4) | Wide multi-directional view on Ratchadaphisek Rd side with traffic approaching from Mahai Sawan Intersection (not Ratchaphruek/Taksin) | Updated `location_*`, `location_detail_*`, `direction="None"` | `Ratchaphruek Rd -> Ratchadaphisek Rd`; `Taksin -> Mahai Sawan`; `Outbound -> None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-05` | `2026-11-15` | `V1.1` | สอง (`@theme222`) | `cam_id=158` (Batch 4 — PR #4) | Dominant 3-lane foreground flows `Outbound` towards Bukkhalo Intersection; `location_detail_th` also said `ขาเข้า` | Updated `direction="Outbound"` and `location_detail_th` (`ขาเข้า -> ขาออก`) | `direction`: `Inbound -> Outbound`; `ขาเข้า -> ขาออก` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-06` | `2026-11-15` | `V1.1` | สอง (`@theme222`) | `cam_id=251` (Batch 4 — PR #4) | English temple spelling mismatch (`Wat Dishongsaram`) and flow moves `Outbound` towards Mit Samphan | Updated `location_en` and `direction="Outbound"` | `Wat Ditsahongsaram (Wat Makkasan)`; `Inbound -> Outbound` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-07` | `2026-11-15` | `V1.1` | สอง (`@theme222`) | `cam_id=256` (Batch 4 — PR #4) | Centered two-way undivided view over Phetchaburi Rd; expressway is Chalerm Maha Nakhon Expressway (`ใต้ทางด่วนเฉลิมมหานคร`) | Updated `direction="None"` & `location_detail_*` | `Outbound -> None`; expressway name updated | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-08` | `2026-11-15` | `V1.1` | สอง (`@theme222`) | `cam_id=500` (Batch 4 — PR #4) | Coords `(13.75001, 100.54103)` confirm Pratu Nam Intersection (not Mit Samphan), multi-directional junction view | Updated `location_*`, `location_detail_*`, `direction="None"` | `แยกมิตรสัมพันธ์ -> แยกประตูน้ำ`; `Inbound -> None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-09` | `2026-11-15` | `V1.1` | สอง (`@theme222`) | `cam_id=529` (Batch 4 — PR #4) | Crossing interchange split ~50/50 across roads | Set `direction="None"` and dropped `(Inbound)` / `(ฝั่งขาเข้า)` from location labels | `Inbound -> None`; labels generalized | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-10` | `2026-11-15` | `V1.1` | สอง (`@theme222`) | `cam_id=572` (Batch 4 — PR #4) | Traffic is strictly ascending onto the elevated highway (`Inbound`) | Updated `direction="Inbound"` and `location_detail_en` (`ascending/descending -> ascending`) | `None -> Inbound`; `Taling Chan ascending ramp` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-11` | `2026-11-15` | `V1.1` | สอง (`@theme222`) | `cam_id=595` (Batch 4 — PR #4) | Wide fisheye view covering crossing flows on both Itsaraphap & Prajadhipok (`ประชาธิปก`) Roads | Added Prajadhipok Rd to `location_detail_*` and set `direction="None"` | `Inbound -> None`; added `ประชาธิปก` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-12` | `2026-11-15` | `V1.1` | สอง (`@theme222`) | `cam_id=1188` (Batch 4 — PR #4) | Camera overlooks Kanchanaphisek Rd (Motorway 9) towards Bang Chueak Nang Interchange in both directions | Updated `location_*` & `location_detail_*`; kept `direction="None"` | `Kanchanaphisek Road (Chimphli Interchange)` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-13` | `2026-11-15` | `V1.1` | สอง (`@theme222`) | `cam_id=32, 158, 529, 595, 1076` (Batch 4 — PR #4) | Visual sweep flagged `22` unusable frames (`2` `scanline_smear`, `17` `corrupt_artifact`, `1` `frozen_visual`, `2` `blocked_lens` rainwater) | Added all `22` filenames to `MANUAL_EXCLUDED_IMAGES` | `-22` images queued (`32`: 2, `158`: 8, `529`: 9, `595`: 1, `1076`: 2) | Yes (`clean_dataset_v1.py`) |
| `CHG-B5-01` | `2026-11-16` | `V1.1` | นิว (`@Pranithi-New`) | `cam_id=169` (Batch 5 — PR #9) | `19` `partial_gray_pframe` frames (`gray128_ratio` `0.483–0.717`) + `169_20260829_195620.jpg` (`0.348`) occlude >50–80% of road ROI | Added all `20` corrupted filenames to `MANUAL_EXCLUDED_IMAGES` | `cam_id=169`: `598 -> 578` valid images (`-20` `corrupt_artifact`) | Yes (`clean_dataset_v1.py`) |
| `CHG-B5-02` | `2026-11-16` | `V1.1` | นิว (`@Pranithi-New`) | Batch 5 two-way / multi-dir cams (`18, 70, 1361, 150, 230, 233, 1063, 301, 332, 363, 370, 371` — PR #9) | Visual & Street View audit confirmed opposing flows (undivided / contraflow lanes) or multi-directional intersections in single frames | Updated `direction="None"` and clarified `location_detail_th/en` for all `12` cameras | `12` cameras moved to `direction="None"` | Yes (`clean_dataset_v1.py`) |
| `CHG-B5-03` | `2026-11-16` | `V1.1` | นิว (`@Pranithi-New`) | `370, 371, 546, 1368, 915, 1028` (Batch 5 — PR #9) | Audited `370/371` low `contrast_std < 20` & `546/1368` night wet-road glare + Aug 25 vs Aug 31 angle stability | Confirmed optics healthy & glare needed for Task 04; kept all frames; `1028` unchanged | `0` frames removed; `0` camera rotations found | Yes (`clean_dataset_v1.py`) |
| `CHG-B5-04` | `2026-11-17` | `V1.1` | นิว (`@Pranithi-New`) | `915, 301, 370, 546, 1368` (Batch 5 — PR #9) | `915` raw pin sat ~95 m NW on Intharaphithak Rd; `301` looks along Nakhon Ratchasima Rd; `370` looks SE along Krung Kasem Rd | Added `"lat": 13.72572, "lon": 100.49268` for `915` + refined `location_detail_th/en` (`915, 301, 370, 546, 1368`) | `cam_id=915` re-pinned ~95 m SE; road details aligned to Street View & OSM | Yes (`clean_dataset_v1.py`) |
| `CHG-B5-05` | `2026-11-17` | `V1.1` | นิว (`@Pranithi-New`) | `cam_id=332` (Batch 5 — PR #9) | Full pixel scan across `10,217` Batch 5 frames uncovered `5` severe vertical `scanline_smear` / stretched frames (>50–90% occluded) | Added all `5` filenames to `MANUAL_EXCLUDED_IMAGES` (`"scanline_smear"`) | `cam_id=332`: `611 -> 606` valid images (`-5`) | Yes (`clean_dataset_v1.py`) |
| `CHG-B6-01` | `2026-11-16` | `V1.1` | โม่ (`@moaqilo`) | Batch 6 Old Town (`16` cams — PR #8) | Wrong/missing `direction` & `location_detail` (`68, 414, 556, 576, 630, 1039, 1060, 1362`); `1362` coords offset; `32` unusable frames (`68`: 1, `413`: 1, `630`: 25, `1039`: 5) | Updated `8` cameras in `CAMERA_CURATION` (incl. `1362` `lat=13.7746377, lon=100.5067094`) + added `32` filenames to `MANUAL_EXCLUDED_IMAGES` | `8` cams metadata updated; `-32` images queued; `16/16` ticked | Yes (`clean_dataset_v1.py`) |
| `CHG-V2-01` | `2026-11-17` | `V2.0` | Maintainer (`Batch 1 Finalize`) | `cam_id=225` (`607` valid frames) | `cam_id=225` metadata verified in `CHG-B1-01`, visual frame sweep left unchecked (`99/100`) | Ran full pixel & visual extremity scan across all `607` valid frames (`0` corruptions; rain/mist on `29_1511`, `29_1521`, `30_1641` kept for Task 04) + ticked `[x]` | Checklist completed: `99/100 -> 100/100` (`[x]`); `0` frames dropped | Yes (`CAMERA_AUDIT_CHECKLIST.md`) |
| `CHG-V2-02` | `2026-11-17` | `V2.0` | Maintainer (`CHG-B4-02 Resolution`) | `cam_id=500`, `cam_id=1188` | `1188` night glare (`128` night frames) vs. `500` H.264 macroblock/YUV corruptions (`>10%`, incl. remaining `7` warnings); whole-camera drops would break `100`-cam contract | Validated `RobustTrafficDetector` on `1188` (`8` cars night, `5` cars wet storm) -> kept `607/607`; audited all `600` frames of `500` & excluded `78` (`13.0%`) severe corruptions in `MANUAL_EXCLUDED_IMAGES` | `cam_id=1188`: `607` kept; `cam_id=500`: `600 -> 522` valid (`-78`); total valid `60,107 -> 60,029`; `quality_warning`: `7 -> 0` | Yes (`clean_dataset_v1.py`) |

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

#### 3. Open Items & Decisions Deferred from `V1.0` -> `V1.1`
- **Team Batch Verification (100 Cameras):** Distributed physical location, direction, and pair verification across Batch 1-6 (ปลื้ม, กร, เฟิร์ม, สอง, นิว, โม่). *(Completed in `V1.1`, `99/100` visual sweeps + `100/100` metadata)*
- **Low-Contrast Night / Foggy Camera Check (`370/371`):** Resolved in Batch 5 (`CHG-B5-03`) — sensors verified healthy, all frames retained.
- **High-Glare Headlight Check (`546/1368`):** Resolved in Batch 5 (`CHG-B5-03`) — wet-road glare needed for Task 04, all frames retained.
- **`quality_warning` (`32` frames):** Checked during Batches 3, 4, and 6: `cam_id=169` (`19` warnings + `1` extra = `20` frames) and `206` (`5` gray P-frames + `1` smear = `6` frames) excluded manually; remaining mild warnings kept or flagged under Batch 4 (`500`) proposal.

---

### `V1.1` -- `2026-11-17` *(Consolidated Team Peer QA -- Batches 1–6)*

#### Maintainer Merge & Post-QA Summary
- **PRs Merged into `main`:** `#6` (`chore/00-qa-siravid`), `#7` (`chore/00-qa-kkooAAA`), `#2` (`chore/00-qa-firm`), `#4` (`chore/00-qa-song`), `#9` (`chore/00-qa-new`), `#8` (`chore/00-qa-moag`).
- **Direction Distribution Shift (`V1.0 -> V1.1`):**
  - `Inbound`: `51 -> 32`
  - `Outbound`: `29 -> 23`
  - `"None"`: `20 -> 45` *(normalized 5 Python `None` values from Batch 3 `11, 82, 277, 599, 604` to literal `"None"`)*
- **Cameras Edited in `CAMERA_CURATION`:** `56 / 100` *(incl. `8` `(lat, lon)` coordinate overrides: `119, 120, 127, 206, 224, 225, 915, 1362`)*.
- **Manual Exclusions (`MANUAL_EXCLUDED_IMAGES`):** `103` frames excluded (`Batch 2`: `18`, `Batch 3`: `6`, `Batch 4`: `22`, `Batch 5`: `25`, `Batch 6`: `32`).
- **Rebuild Status (`clean_dataset_v1.py`, `2026-11-17`, `295.76s`):**
  - `total_raw_images`: `61,319` -> **`total_valid_images`: `60,107` (`98.0235%`)**, `total_filtered_images`: `1,212`
  - `status_counts`: `valid = 60,107`, `frozen = 553`, `white_error = 504`, `manual_excluded = 103`, `no_signal_error = 33`, `corrupt_color = 19`
  - `quality_warning` among valid frames dropped from `32` -> **`7`** (`partial_green_screen` on `cam_id=500` only; all `24` `partial_gray_pframe` on `169`/`206` and `1` `partial_green_screen` on `630` were excluded)
  - `run_pipeline.py --check-contract`: **PASS** on Tables 1, 2, 4 (`Table 1`: `100 x 25`, `Table 2`: `61,319 x 36`, `Table 4`: `16,800 x 17`)

---

#### Batch 1 -- ปลื้ม (`@siravidthongsook`): Ratchadaphisek Corridor (`17` Cameras, PR #6)

- **Scope:** `112, 118, 119, 120, 123, 124, 125, 126, 127, 135, 211, 212, 215, 219, 224, 225, 1408` (`CHG-B1-01`).
- **Problem Found:**
  - `cam_id=119` / `cam_id=120` (`PAIR_ARM_SUTTHISAN`): opposite arms carried each other's `(lat, lon)` (`~30-40 m` cross-arm swap).
  - `cam_id=224` / `cam_id=225` (`FB_04_CriminalCourt`): longitudes swapped between inbound and outbound spans.
  - `cam_id=127` (`FB_03_Ratchada30`): pin sat on the road median instead of the outbound footbridge span.
  - `cam_id=120`: labelled `Inbound`, but side-arm view captures traffic in both directions (`None`).
  - Image sweep: `0` unusable frames across `16` swept folders (`cam_id=211` also independently verified by `@nontaphatfirm`). `cam_id=225` metadata verified, **visual folder sweep still pending**.
- **Fix Applied & Quantitative Impact:**
  - Extended `CAMERA_CURATION` / `build_cleaned_metadata()` with optional `lat`/`lon` overrides:
    - `cam_id=119`: `lat 13.78971 -> 13.789680`, `lon 100.57410 -> 100.574437`
    - `cam_id=120`: `lat 13.78968 -> 13.789785`, `lon 100.57441 -> 100.574031`, `direction`: `Inbound -> None`
    - `cam_id=127`: `lat 13.81001 -> 13.810192`, `lon 100.57511 -> 100.575261`
    - `cam_id=224`: `lat 13.81524 -> 13.815228`, `lon 100.57553 -> 100.575355`
    - `cam_id=225`: `lat 13.81523 -> 13.815248`, `lon 100.57533 -> 100.575513`
  - Manual exclusions: `0`.

---

#### Batch 2 -- กร (`@kkooAAA`): Phahon Yothin - Lat Phrao & East Bangkok (`16` Cameras, PR #7)

- **Scope:** `1815, 136, 137, 139, 141, 170, 176, 177, 178, 179, 1070, 1071, 1112, 938, 939, 1804` (`CHG-B2-01` – `CHG-B2-05`).
- **Fixes Applied & Quantitative Impact:**
  - **`CHG-B2-01` (`2026-11-15` — District Fixes):**
    - `cam_id=938`: `district` `Suan Luang -> Bang Kapi`.
    - `cam_id=1815`: `district` `Huai Khwang -> Din Daeng` (final documented road: **Rama 9 Road**, `Inbound`).
  - **`CHG-B2-02` (`2026-11-15` — `cam_id=1815` View-Change Exclusion):**
    - Camera panned ~180° from `1815_20260831_181044.jpg` through `1815_20260831_210044.jpg` (original view ends at `1815_20260831_180044.jpg`).
    - Excluded `18` frames (`"camera_view_changed"`): `1815_20260831_181044.jpg`, `182046`, `183044`, `184044`, `185044`, `190044`, `191044`, `192044`, `193044`, `194046`, `195044`, `200044`, `201046`, `202044`, `203044`, `204044`, `205044`, `210044`. (`cam_id=1815`: `611 -> 593` valid frames).
  - **`CHG-B2-03` / `CHG-B2-04` / `CHG-B2-05` (`2026-11-16` to `2026-11-17` — Location & Direction Refinements):**
    - `cam_id=939`: `location_detail_th`: `บริเวณแยกมหาดไทย (ถนนรามคำแหง) -> บริเวณแยกมหาดไทย (สะพานรามคำแหง)`; `location_detail_en`: `Mahadthai Intersection (Ramkhamhaeng Road) -> Mahadthai Intersection (Ramkhamhaeng Bridge)`; `direction="None"` kept.
    - `cam_id=1112`: Final road set to Sutthisan Winitchai Road (`แยกสุทธิสาร (ถนนสุทธิสารวินิจฉัย)` / `Sutthisan Intersection (Sutthisan Winitchai Road)` in `location_*` & `location_detail_*`); `direction`: `Inbound -> None`.
    - `cam_id=1804`: `location_detail_th`: `ท้ายรถมุ่งหน้าแยกสวนหลวง -> ปากซอยอ่อนนุช 33 ถนนอ่อนนุช`; `location_detail_en`: `Towards Suan Luang Intersection -> Entrance to Soi On Nut 33 on On Nut Road`; `direction`: `Outbound -> None`.
    - `cam_id=178` / `179`: physical reference comments (~180 m / ~120 m after turning right from Phyathai 2 Hospital) added in `CAMERA_CURATION`.
- **Informational Note (Drive Deduplication for `V2.0`):** `28` byte-identical duplicate image copies exist on Google Drive (`18` in `136/`, e.g. `136_20260825_111611.jpg`; `10` in `176/`, e.g. `176_20260829_085616.jpg`). Do **not** add to `MANUAL_EXCLUDED_IMAGES`; remove duplicates during `V2.0` Drive sync.

---

#### Batch 3 -- เฟิร์ม (`@nontaphatfirm`): Sathon - Naradhiwas - Rama 3 & Pathum Wan (`17` Cameras + `211`, PR #2)

- **Scope:** `75, 88, 186, 188, 194, 196, 206, 599, 603, 604, 11, 82, 239, 432, 542, 619, 277` + Batch 1 `211` (`CHG-B3-01` – `CHG-B3-18`).
- **Confirmed Healthy (`V1.0` Baseline Unchanged — 7 Cameras):** `186`, `188`, `196`, `211` (Batch 1), `239` (4 main southbound `Inbound` lanes), `542` (Sarasin–Lang Suan bidirectional `None`), `619` (Henri Dunant multi-directional `None`).
- **Metadata Fixes Applied (11 Cameras):**
  - `cam_id=11`: `location_detail_*` updated to `ช่วงอนุสาวรีย์ชัยสมรภูมิ – แยกสามเหลี่ยมดินแดง (ทั้งสองทิศทาง)` / `Between Victory Monument and Din Daeng Intersection (both directions)`; `direction`: `Outbound -> None`.
  - `cam_id=75`: `location_detail_*`: `รถมาจากแยกด่วนสาธุประดิษฐ์ -> รถมาจากแยกนราธิวาส-พระราม 3` (`From Sathu Pradit Expressway Intersection -> From Naradhiwas-Rama 3 Intersection`).
  - `cam_id=82`: `location_detail_*` clarified (4 northbound lanes + 1 southbound contraflow bus lane); `direction`: `Inbound -> None`.
  - `cam_id=88`: Undivided two-way Chan Rd near Soi 18/6; `direction`: `Inbound -> None`.
  - `cam_id=194`: `ถนนสาทรใต้ -> ถนนสาทรเหนือ` (`South -> North Sathon Road`); `จากแยกสาทร-นราธิวาส มุ่งหน้าวิทยุ -> จากแยกวิทยุ มุ่งหน้าสาทร-นราธิวาส`; `direction`: `Inbound -> Outbound`.
  - `cam_id=206`: `ใกล้ซอย -> ตรงข้ามซอยนราธิวาสราชนครินทร์ 20` (`near -> opposite`); approach reversed (`Chan-Naradhiwas -> Ratchada-Naradhiwas`); `direction`: `Inbound -> Outbound`; `lat, lon`: `13.70545, 100.53835 -> 13.70555, 100.53865` (~34 m east carriageway).
  - `cam_id=277`: `ทางแยก -> วงเวียนอนุสาวรีย์ชัยสมรภูมิ` (`Footbridge near Soi Rang Nam -> Victory Monument Roundabout`); detail updated for Phayathai Island multi-directional roundabout view; `direction`: `Inbound -> None`.
  - `cam_id=432`: `location_detail_*` clarified (`รถมาจากสีลม มุ่งหน้าไปหัวลำโพง (บริเวณแยกสามย่าน ถนนพระรามที่ 4)`); `direction`: `None -> Inbound`.
  - `cam_id=599`: Full Surasak junction box; `direction`: `Inbound -> None`.
  - `cam_id=603`: `location_detail_*`: `รถมาจากแยกสุรศักดิ์ -> รถมาจากแยกสาทร-นราธิวาส` (main corridor ahead is Naradhiwas Rd Northbound).
  - `cam_id=604`: `location_detail_*` updated (full 4-way Silom–Naradhiwas junction under BTS viaduct; removed off-axis `ศาลาแดง`); `direction`: `Inbound -> None`.
- **Manual Frame Exclusions (`6` frames on `cam_id=206`):**
  - `corrupt_artifact` (`5`): `206_20260825_183106.jpg`, `206_20260827_120106.jpg`, `206_20260828_130705.jpg`, `206_20260828_171605.jpg`, `206_20260831_104606.jpg`.
  - `blocked_lens` (`1`, heavy condensation/water smear): `206_20260831_164105.jpg`.

---

#### Batch 4 -- สอง (`@theme222`): Phetchaburi & Thon Buri Corridors (`17` Cameras, PR #4)

- **Scope:** `250, 251, 256, 500, 26, 1195, 32, 36, 1103, 1076, 158, 1078, 1132, 529, 572, 1188, 595` (`CHG-B4-01` – `CHG-B4-13`).
- **Metadata Fixes Applied (12 Cameras):**
  - `cam_id=26` & `1195`: `pair_id`: `PAIR_JX_BUKKHALO -> PAIR_ARM_BUKKHALO`; `pair_type`: `perpendicular_junction -> opposite_intersection_arm`. `1195` updated to `แยกบุคคโล (ด้านถนนเจริญนคร)` / `Charoen Nakhon Road (Outbound)`, `direction`: `Inbound -> Outbound`.
  - `cam_id=32`: Bidirectional Thoet Thai Rd; `direction`: `Inbound -> None`.
  - `cam_id=36`: `location_*` `ราชพฤกษ์ -> รัชดาภิเษก`, `location_detail_*` `ตากสิน -> มไหสวรรย์`; `direction`: `Outbound -> None`.
  - `cam_id=158`: Dominant 3-lane foreground flows `Outbound` towards Bukkhalo; `location_detail_th`: `ขาเข้า -> ขาออก`; `direction`: `Inbound -> Outbound`.
  - `cam_id=251`: `Wat Dishongsaram -> Wat Ditsahongsaram (Wat Makkasan)`; `direction`: `Inbound -> Outbound`.
  - `cam_id=256`: Undivided multi-lane Phetchaburi Rd; `location_detail_*` updated to `ใต้ทางด่วนเฉลิมมหานคร` (`Chalerm Maha Nakhon Expressway`); `direction`: `Outbound -> None`.
  - `cam_id=500`: Relabelled from Mit Samphan to **Pratu Nam Intersection (`แยกประตูน้ำ`)** per `(13.75001, 100.54103)`; `direction`: `Inbound -> None`.
  - `cam_id=529`: Crossing interchange split ~50/50; removed `(Inbound)` / `(ฝั่งขาเข้า)` labels; `direction`: `Inbound -> None`.
  - `cam_id=572`: Strictly ascending ramp traffic; `location_detail_en`: `ascending/descending -> ascending`; `direction`: `None -> Inbound`.
  - `cam_id=595`: Added `ประชาธิปก` / `Prajadhipok Roads` to `location_detail_*`; `direction`: `Inbound -> None`.
  - `cam_id=1188`: Corrected location from Borommaratchachonnani to **Kanchanaphisek Road (Chimphli Interchange)** towards Bang Chueak Nang Interchange (`direction="None"` kept).
- **Manual Frame Exclusions (`22` frames):**
  - `cam_id=32` (`2` `scanline_smear`): `32_20260828_100545.jpg`, `32_20260830_124541.jpg`.
  - `cam_id=158` (`8` `corrupt_artifact`): `158_20260827_183605.jpg`, `158_20260827_191605.jpg`, `158_20260828_185607.jpg`, `158_20260829_114604.jpg`, `158_20260830_075603.jpg`, `158_20260830_110607.jpg`, `158_20260831_161604.jpg`, `158_20260831_201605.jpg`.
  - `cam_id=529` (`9` `corrupt_artifact`): `529_20260825_081011.jpg`, `529_20260825_142011.jpg`, `529_20260827_123022.jpg`, `529_20260827_155011.jpg`, `529_20260827_161011.jpg`, `529_20260827_193511.jpg`, `529_20260828_145011.jpg`, `529_20260828_155011.jpg`, `529_20260828_200011.jpg`.
  - `cam_id=595` (`1` `frozen_visual`): `595_20260826_154043.jpg`.
  - `cam_id=1076` (`2` `blocked_lens` — rainwater): `1076_20260831_163105.jpg`, `1076_20260831_164105.jpg`.
- **Open Proposal (`CHG-B4-02`):** Team/maintainer decision pending on whether to exclude `cam_id=500` (`>10%` artifacts) and `cam_id=1188` (tiny vehicles & severe nighttime glare) downstream (`run_pipeline.py` contract currently checks `100` rows in `cctv_info_cleaned`). *(Also added `**/workspace/` to `.gitignore`.)*

---

#### Batch 5 -- นิว (`@Pranithi-New`): Dusit - Rama 5 - Samsen (`17` Cameras, PR #9)

- **Scope:** `915, 18, 1028, 70, 1361, 150, 169, 230, 233, 1063, 301, 332, 363, 370, 371, 546, 1368` (`CHG-B5-01` – `CHG-B5-05`).
- **Metadata Fixes Applied (15 Cameras):**
  - **Two-Way / Multi-Directional (`direction -> "None"`, `12` cams):** `18, 150, 301, 1063, 1361` (`Outbound -> None`) and `70, 230, 233, 332, 363, 370, 371` (`Inbound -> None`), with `location_detail_th/en` updated for opposing/contraflow/cross-traffic framing (`301` road corrected to Nakhon Ratchasima Rd; `370` clarified along Krung Kasem Rd).
  - **Street View & OSM Fixes:** `cam_id=915` pin moved ~95 m SE to SW Wongwian Yai roundabout quadrant (`lat=13.72572, lon=100.49268`, detail refined); `546` & `1368` details clarified.
  - **V1.0 Open Edge Cases Verified Healthy (Keep All Frames):**
    - `cam_id=370` & `371` (`contrast_std < 20`): steep downward framing on dark uniform asphalt confirmed optically healthy (`370_20260829_190537.jpg`, `370_20260830_070536.jpg`, `370_20260829_202540.jpg`, `371_20260830_060042.jpg`).
    - `cam_id=546` & `1368` (`glare_ratio > 0.15`): wet asphalt reflections & headlight bloom preserved for Task 04 CV rain/wet-road detection.
    - `1028` & `169` directions/coords verified (`0` camera angle shifts across Batch 5).
- **Manual Frame Exclusions (`25` frames):**
  - `cam_id=169` (`20` `corrupt_artifact`, >35%–72% gray-128 blocks occluding road ROI): `169_20260825_093619.jpg`, `124618`, `155620`, `160618`, `20260826_100622`, `130619`, `144618`, `20260827_154118`, `20260828_124622`, `162627`, `164617`, `20260829_195620`, `20260830_100117`, `121118`, `125119`, `130117`, `20260831_080119`, `100120`, `145119`, `174119` (`598 -> 578` valid).
  - `cam_id=332` (`5` `scanline_smear`, vertical streak >50%–90% occluded): `332_20260825_163054.jpg`, `164054`, `165052`, `20260826_064052`, `20260828_112105` (`611 -> 606` valid).

---

#### Batch 6 -- โม่ (`@moaqilo`): Historic Old Town - Phra Nakhon - Pom Prap (`16` Cameras, PR #8)

- **Scope:** `68, 228, 395, 411, 412, 413, 414, 556, 569, 576, 630, 913, 1039, 1060, 1362, 1589` (`CHG-B6-01`).
- **Metadata Fixes Applied (8 Cameras):**
  - `cam_id=68`: `direction`: `Inbound -> None`.
  - `cam_id=414`: `location_detail_th`: `บริเวณใต้สะพานพระพุทธยอดฟ้า -> มุ่งเข้าสู่ย่านพระนครและสนามไชย`; `location_detail_en`: `Under Memorial Bridge -> Towards Phra Nakhon area and Sanam Chai`; `direction`: `None -> Inbound`.
  - `cam_id=556`: `location_detail_th`: `รถมาจากสะพานกรุงธน -> รถมาจากวัดประสาทบุญญาวาส`; `location_detail_en`: `From Krung Thon Bridge -> From Wat Prasat Bunyawat`.
  - `cam_id=576`: `location_detail_th`: `บริเวณแยกบางลำพู -> รถมุ่งหน้าไปถนนข้าวสาร / สนามหลวง`; `location_detail_en`: `Bang Lamphu Intersection -> Towards Khao San Road / Sanam Luang`; `direction`: `None -> Inbound`.
  - `cam_id=630`: `location_detail_th`: `รถมุ่งหน้าแยกสะพานแดง -> รถมาจากแยกสะพานแดง`; `location_detail_en`: `Towards Saphan Daeng Intersection -> From Saphan Daeng Intersection`; `direction`: `Outbound -> Inbound`.
  - `cam_id=1039`: `direction`: `Outbound -> None`.
  - `cam_id=1060`: `location_detail_th`: `รถมุ่งหน้าไปถนนพระรามที่ 1 -> รถมาจากถนนพระรามที่ 1`; `location_detail_en`: `Towards Rama 1 Road -> From Rama 1 Road`.
  - `cam_id=1362`: `location_th`: `แยกสามเสน -> ถนนสามเสน`; `location_en`: `Samsen Intersection -> Samsen Road`; `location_detail_th`: `บริเวณแยกสามเสน มุ่งหน้าแยกอภัยเจษฎุทิศ -> รถมุ่งหน้าท่าวาสุกรี`; `location_detail_en`: `Left side towards Uphai Chetsaduthit Intersection -> Towards Tha Wasukri Pier`; `lat=13.7746377`, `lon=100.5067094` (`Inbound` kept).
- **Manual Frame Exclusions (`32` frames):**
  - `cam_id=68` (`1` `blocked_by_crow`): `68_20260828_092625.jpg`.
  - `cam_id=413` (`1` `blocked_by_pickup`): `413_20260827_111525.jpg`.
  - `cam_id=630` (`25` total: `15` `corrupt_artifact`, `9` `stretched_frame`, `1` `blurry_frame`):
    - `corrupt_artifact`: `630_20260825_072031.jpg`, `074031`, `085033`, `170031`, `174034`, `175032`, `201032`, `20260826_085032`, `100032`, `20260827_092031`, `194035`, `203032`, `20260828_080531`, `20260830_115531`, `120533`.
    - `stretched_frame`: `630_20260825_202032.jpg`, `20260826_060531`, `061540`, `091031`, `20260827_162032`, `202032`, `20260829_083530`, `201532`, `20260831_170532`.
    - `blurry_frame`: `630_20260830_150531.jpg`.
  - `cam_id=1039` (`5` `overexposed_glare`): `1039_20260825_185509.jpg`, `20260826_195009.jpg`, `20260829_194509.jpg`, `20260830_185009.jpg`, `20260831_195511.jpg`.

---

#### Remaining Open Items Before Locking `V2.0` *(Addressed in `V2.0` Below)*
1. **Batch 1 `cam_id=225` visual sweep:** Metadata (`lat/lon`, `Outbound`) verified; complete the visual frame scan -> **Done in `CHG-V2-01`**.
2. **Batch 4 `CHG-B4-02` decision (`cam_id=500` & `1188`):** Decide downstream handling vs. contract -> **Resolved in `CHG-V2-02`**.
3. **Google Drive `V2.0` sync:** Local `136/` (`608` files) and `176/` (`609` files) have `0` duplicates; remember to remove the `28` extra Drive-only copies when syncing `V2.0` to Google Drive.
4. **Task 03 Median Backgrounds Refresh:** Locally cached `data/median_backgrounds/` generated prior to `V1.1`/`V2.0` should be regenerated for cameras with newly excluded frames (`1815`, `630`, `1039`, `169`, `158`, `529`, `206`, `332`, `500`).

---

### `V2.0` -- `2026-11-17` *(Final Data Lock -- `100/100` Peer QA Verified & `CHG-B4-02` Resolved)*

#### 1. Batch 1 Completion (`CHG-V2-01`: `cam_id=225` Visual Sweep)
- **Quantitative & Visual Audit (`607` valid / `611` raw; `4` `white_error` already removed by Gate 1):**
  - `warnings = none` across all `607` frames; `gray128 > 0.2 = 0`; `neon_green > 0.01 = 0`; minimum `mad_from_prev = 6.03` (zero frozen stalls); minimum `bot_std = 33.07`; `sharpness` min/p5/med = `10.74 / 24.80 / 28.17`.
  - Visually verified the `28` lowest-sharpness / highest-glare / row-jump extreme frames (`29_1511`, `29_1521`, `30_1641`, nighttime headlights): vehicles and roadway remain fully legible; mild lens rain droplets retained per Task 04 CV weather rules.
  - Marked `[x]` in `00_data_cleaning_and_qa/CAMERA_AUDIT_CHECKLIST.md` (**`100 / 100` audited**).

#### 2. Resolution of `CHG-B4-02` (`CHG-V2-02`: `cam_id=1188` & `cam_id=500`)
- **Contract Decision (`100` Cameras Preserved):** Dropping whole cameras (`100 -> 98`) would break `run_pipeline.py` (`expected_min_rows=100`), invalidate `16,800` hourly rows (`100 x 168`) in `data/external_weather_poi.parquet`, and drop Bangkok's sole **Pratu Nam Intersection (`500`)** and **Kanchanaphisek / Chimphli Interchange (`1188`)** coverage. Both cameras carry `direction="None"` and do not affect directional (`32/23`) or bidirectional footbridge (`6` pairs) metrics.
- **`cam_id=1188` (`607` valid: `479` day / `128` night; `42` frames `glare_ratio > 0.05`) -- Kept `607 / 607`:**
  - Daytime (`79%`) frames are sharp; nighttime (`21%`) headlight glare/wet storm scenes passed `RobustTrafficDetector` validation (`25_0800`: `11` vehicles; `25_1950` night glare: `8 cars`, `18` glare FPs suppressed; `28_1845` rainy night: `5 cars`, `23` FPs suppressed). Dropping `128` night frames would erase `18:00–19:30` from `evening_rush_score`, skew K-Means clustering, and eliminate evening storm recovery (`tau_recovery_min`).
- **`cam_id=500` (`600` valid -> `522` clean, `-78` or `13.0%` excluded; `181` total `MANUAL_EXCLUDED_IMAGES`):**
  - Full `600`-frame visual triage confirmed `@theme222`'s `>10%` finding: `7` `partial_green_screen` frames (removing roads in the lower foreground), `1` severe bottom-half vertical `scanline_smear` (`500_20260828_190519.jpg`), and `70` heavy H.264/P-frame macroblock smears causing Task 03 hallucinated/lost detections (e.g., phantom `car 0.64` / `bus 0.40` on `500_20260827_194519.jpg`).
  - Excluded filenames (`78`):
    - `partial_green_screen` (`7`): `500_20260825_073524.jpg`, `500_20260825_191519.jpg`, `500_20260826_191519.jpg`, `500_20260828_111524.jpg`, `500_20260829_130521.jpg`, `500_20260831_201519.jpg`, `500_20260831_203519.jpg`.
    - `scanline_smear` (`1`): `500_20260828_190519.jpg`.
    - `corrupt_artifact` (`70`): `500_20260825_060027.jpg`, `065518`, `091518`, `092518`, `093518`, `094518`, `100518`, `131519`, `141523`, `162522`, `163519`, `164519`, `173520`, `183519`, `184519`, `190519`, `200519`, `201519`, `20260826_060042`, `095518`, `102519`, `104523`, `113518`, `142523`, `165519`, `193519`, `195519`, `201519`, `202519`, `205519`, `20260827_092520`, `112518`, `122520`, `162519`, `183519`, `194519`, `195521`, `203519`, `205521`, `20260828_090521`, `092520`, `163519`, `174519`, `192519`, `20260829_131518`, `140518`, `142519`, `151521`, `152518`, `180519`, `182519`, `193519`, `195521`, `200519`, `205521`, `20260830_154022`, `163022`, `165020`, `174523`, `20260831_092518`, `103518`, `112518`, `113519`, `180519`, `182519`, `190519`, `191519`, `192521`, `195521`, `200519`.
  - **Time-Series Implementation Note (Task 05):** Scattered single-frame removals on `cam_id=500` reduce naive index-based `.shift(-3)` valid `(tgt+lag1)` rows (`528 -> 304`); Task 05 (`build_lag_dataset.py`) should use wall-clock timestamp matching (`merge_asof` on `timestamp +/- 30 min`) rather than rigid row-index shifts to avoid 3–4x gap amplification around isolated `manual_excluded` frames.

#### 3. Locked `V2.0` Rebuild & Contract Validation (`clean_dataset_v1.py`, `2026-11-17`, `188.57s`)
- **`total_raw_images`: `61,319`** -> **`total_valid_images`: `60,029` (`97.90%` / `97.8962%`)**, **`total_filtered_images`: `1,290` (`2.10%`)**
- **`status_counts`:** `valid = 60,029`, `frozen = 553`, `white_error = 504`, `manual_excluded = 181`, `no_signal_error = 33`, `corrupt_color = 19`
- **`quality_warning_counts_among_valid`:** `none = 60,029` (**`0` warnings remaining across all 100 cameras**)
- **Canonical Contract Updated (`DATA_CONTRACT.md` & `run_pipeline.py`):** Table 3 `expected_min_rows` aligned to `60,029` (`python run_pipeline.py --check-contract` `[PASS]` on Tables 1, 2, 4).
- **Drive Mirror Note:** Before/during Drive `V2.0` upload, remove the `28` Drive-only duplicates in `136/` (`18`) & `176/` (`10`) and unlink the `78` newly excluded `.jpg` files in `500/` (local disk already reflects `522` files in `500/` and `60,029` files total).

---

> **Instructions for Future Contributors:** When adding `V2.0+` updates, copy the template below, fill in exact details, and add a summary row to the **Modification Ledger** above.

```markdown
#### Change Entry Template (Copy & Paste for Each Audit / Fix Session)
- **Date:** YYYY-MM-DD
- **Editor:** <Name> (<GitHub handle>)
- **Batch / Scope:** <e.g., V2.0 Final Lock / extra exclusion check>
- **Problem Found:**
  - `cam_id=XXX`: <describe exact issue in metadata or specific images>
- **Fix / Decision Applied:**
  - Updated `CAMERA_CURATION` / exclusion list / threshold in `clean_dataset_v1.py`
- **Quantitative Impact (Before -> After):**
  - Metadata fields changed: <list exact fields & old -> new values>
  - Images affected: `<N>` valid images (`<before>` -> `<after>`)
- **Verification:** `clean_dataset_v1.py` + `run_pipeline.py --check-contract` `[PASS]`
```
