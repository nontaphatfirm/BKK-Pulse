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
| `V1.1` *(Draft)* | `2026-11-15` | Peer QA In Progress | `61,319 -> 60,210` (unchanged) | Batch 1 (`17` cams) audited: `5` coordinate fixes, `1` direction fix, `0` bad frames; Batches 2-6 pending |
| `V2.0` *(Planned)* | *Pending* | Planned Final Lock | *TBD* | Final locked clean dataset for production YOLO inference & final report |

---

## Modification Ledger (Team Peer-Audit & Cleaning Fixes)

*(Add a new row below every time anyone modifies or flags data during cleaning!)*

| Log ID | Date (`YYYY-MM-DD`) | Target Version | Editor (Name / GitHub) | Target `cam_id` / Scope | Issue Identified | Cleaning Action Taken | Before -> After Impact | Synced in Script? |
| :--- | :---: | :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| `CHG-001` | `2026-11-11` | `V1.0` | Automated Baseline | All `100` cams / `61,319` imgs | Blank white, rainbow, gray P-frame, green screen, frozen streams, Thai Unicode paths, `1970` OSD dates, corrupted `cctv_info.csv` | Executed 5-Gate pipeline + `CAMERA_CURATION` in `clean_dataset_v1.py` | `61,319 -> 60,210` valid images (`1,109` filtered); `100/100` metadata repaired | Yes (`clean_dataset_v1.py`) |
| `CHG-003` | `2026-11-15` | `V1.1` | ปลื้ม (@siravidthongsook) | Batch 1 (`17` cameras, Ratchadaphisek) | Pair cameras `119/120` and `224/225` reported each other's `(lat, lon)`; `127` pin sat on the road median instead of the outbound footbridge span; `120` labelled `Inbound` although both directions pass the side-arm view; `0` broken frames found in the visual sweep | Added optional `lat`/`lon` override support to `CAMERA_CURATION` (`clean_dataset_v1.py`) and applied `5` camera corrections + `1` `direction` fix; no image exclusions needed | `119/120`, `224/225` swapped longitudes restored to the correct side; `127` re-pinned `~25 m` onto the outbound span; `120`: `Inbound` -> `None`; valid images unchanged at `60,210` | Yes (`clean_dataset_v1.py`) |
| `CHG-B2-01` | `2026-11-15` | `V1.1` | กร (@kkooAAA) | Batch 2 (16 cams): `1815, 136, 137, 139, 141, 170, 176, 177, 178, 179, 1070, 1071, 1112, 938, 939, 1804` | District mismatch on `938`, `1815`; no defective frames missed by automated gates | Updated `district` in `CAMERA_CURATION`; no `MANUAL_EXCLUDED_IMAGES` added; open items logged for maintainer (see V1.1 Batch 2 entry) | `938` district: Suan Luang -> Bang Kapi; `1815` district: Huai Khwang -> Din Daeng; images `9,535 -> 9,535` (0 excluded) | Yes (`clean_dataset_v1.py`) |
| `CHG-B2-02` | `2026-11-15` | `V1.1` | กร (@kkooAAA) | `cam_id=1815` / `18` images | Camera view changed (~180° reverse pan) from `2026-08-31 18:10:44` to end of capture; frames no longer match `location_detail` / `direction` | **Following the PM's instruction**, added the `18` changed-view filenames to `MANUAL_EXCLUDED_IMAGES` (reason `camera_view_changed`); original-view frames kept | `1815` valid images: `611 -> 593`; Batch 2: `9,535 -> 9,517`; no other camera affected | Yes (`clean_dataset_v1.py`) |
| `CHG-B2-03` | `2026-11-16` | `V1.1` | กร (@kkooAAA) | Batch 2 location audit: `1112` (changed); `939`, `170`, `1071`, `1804`, `1815`, `178`, `179` (verified) | `1112` labelled with the wrong road (Vibhavadi Rangsit) although it views Sutthisan Winitchai Road; `1815` road recorded as Asok-Din Daeng in `CHG-003` | Updated `location_en` / `location_th` (`1112`) in `CAMERA_CURATION`; `1815` road clarified as Rama 9 Road (documentation only); other cameras verified unchanged | `1112` road: Vibhavadi Rangsit -> Sutthisan Winitchai; images unchanged (`9,517`) | Yes (`clean_dataset_v1.py`) |
| `CHG-B2-04` | `2026-11-17` | `V1.1` | กร (@kkooAAA) | `939`, `1112`, `1804` | `939` detail named Ramkhamhaeng Road instead of Ramkhamhaeng Bridge; `1112` / `1804` detail and `direction` did not match the camera view | Updated `location_detail_th/en` (`939`, `1112`, `1804`), `location_th/en` (`1112`, back to Vibhavadi Rangsit Road, supersedes `CHG-005`) and `direction` (`1112`, `1804`) in `CAMERA_CURATION` | `1112` direction: Inbound -> None; `1804` direction: Outbound -> None; direction totals `51/29/20 -> 50/28/22` (Inbound/Outbound/None); images unchanged | Yes (`clean_dataset_v1.py`) |
| `CHG-B2-05` | `2026-11-17` | `V1.1` | กร (@kkooAAA) | `cam_id=1112` | Road name: camera views Sutthisan Winitchai Road, not Vibhavadi Rangsit Road | Updated `location_th/en` and `location_detail_th/en` in `CAMERA_CURATION` to Sutthisan Winitchai Road (supersedes the `CHG-006` road revert); `direction` unchanged (`None`) | `location_th`: `แยกสุทธิสาร (ถนนวิภาวดีรังสิต)` -> `แยกสุทธิสาร (ถนนสุทธิสารวินิจฉัย)`; `location_en`: `Sutthisan Intersection (Vibhavadi Rangsit Road)` -> `Sutthisan Intersection (Sutthisan Winitchai Road)` (same for `location_detail_th/en`) | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-01` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=75` (Batch 3) | `location_detail_th`/`en` in raw metadata misstated incoming approach as Sathu Pradit Expressway (Ratchadaphisek Rd), whereas daylight/night images show BRT median lane on Naradhiwas Rd inbound from Naradhiwas–Rama 3 Intersection | Updated `CAMERA_CURATION[75]` (`location_detail_th` & `location_detail_en`) in `clean_dataset_v1.py` | `location_detail_th`: `รถมาจากแยกด่วนสาธุประดิษฐ์` -> `รถมาจากแยกนราธิวาส-พระราม 3`; `location_detail_en`: `From Sathu Pradit Expressway Intersection` -> `From Naradhiwas-Rama 3 Intersection` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-02` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=88` (Batch 3) | Two-way road with no median (`Chan Rd` near Soi `18/6`); YOLO counts both inbound (right lane towards Chan-Naradhiwas) and outbound (left lane towards camera) vehicles together in one frame | Changed `CAMERA_CURATION[88]["direction"]` from `"Inbound"` to `"None"` in `clean_dataset_v1.py` to avoid polluting Macro Directional Flow (`04`) | `direction`: `Inbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-03` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=186` (Batch 3) | Peer QA verification of `cctv_images/186/` and metadata (`location_*`, `district`, `corridor`, `direction`) | Verified all images and metadata against Google Maps; no broken frames or metadata errors found | No changes (`V1.0` baseline confirmed) | Yes (`clean_dataset_v1.py` unchanged) |
| `CHG-B3-04` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=188` (Batch 3) | Peer QA verification of `cctv_images/188/` and metadata (`location_*`, `district`, `corridor`, `direction`) | Verified all images and metadata against Google Maps; no broken frames or metadata errors found | No changes (`V1.0` baseline confirmed) | Yes (`clean_dataset_v1.py` unchanged) |
| `CHG-B3-05` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=194` (Batch 3) | Metadata listed South Sathon Rd (`Inbound`, towards Witthayu), whereas night/day imagery shows primary foreground traffic on North Sathon Rd coming from Witthayu towards Sathon-Naradhiwas (`Outbound`) | Updated `CAMERA_CURATION[194]` (`location_th`, `location_detail_th`, `location_en`, `location_detail_en`, `direction`) in `clean_dataset_v1.py` | `ถนนสาทรใต้` -> `ถนนสาทรเหนือ`; `รถมาจากแยกสาทร-นราธิวาส มุ่งหน้าแยกวิทยุ` -> `รถมาจากแยกวิทยุ มุ่งหน้าแยกสาทร-นราธิวาส`; `direction`: `Inbound` -> `Outbound` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-06` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=196` (Batch 3) | Peer QA verification of `cctv_images/196/` and metadata (`location_*`, `district`, `corridor`, `direction`) | Verified all images and metadata against Google Maps; no broken frames or metadata errors found | No changes (`V1.0` baseline confirmed) | Yes (`clean_dataset_v1.py` unchanged) |
| `CHG-B3-07` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=206` (Batch 3) | Metadata listed `ใกล้ซอยนราธิวาสราชนครินทร์ 20`, `รถมาจากแยกรัชดา-นราธิวาส มุ่งหน้าแยกจันทน์-นราธิวาส` (`Inbound`), and raw coordinates (`13.70545, 100.53835`) on the opposite side; also 6 frames (`5` severe gray P-frame corruptions, `1` heavy lens blur/smear) slipped past baseline thresholds | Updated `CAMERA_CURATION[206]` (`location_*`, `direction`, `lat`, `lon`), added optional `lat`/`lon` override in `build_cleaned_metadata()`, and added 6 filenames to `MANUAL_EXCLUDED_IMAGES` in `clean_dataset_v1.py` | `ใกล้ซอย...` -> `ตรงข้ามซอยนราธิวาสราชนครินทร์ 20`; `รถมาจากแยกรัชดา...` -> `รถมาจากแยกจันทน์-นราธิวาส มุ่งหน้าแยกรัชดา-นราธิวาส`; `Inbound` -> `Outbound`; `13.70545, 100.53835` -> `13.70555, 100.53865`; `-6` broken images queued | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-08` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=211` (Batch 1) | Peer QA verification of `cctv_images/211/` and metadata (`location_*`, `district`, `corridor`, `direction`) | Verified all images and metadata; no broken frames or metadata errors found | No changes (`V1.0` baseline confirmed) | Yes (`clean_dataset_v1.py` unchanged) |
| `CHG-B3-09` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=599` (Batch 3) | Wide intersection-box view at Surasak Intersection (`สีลม–สุรศักดิ์–มเหสักข์`) where YOLO counts cross-traffic across the junction box and both sides of the median simultaneously | Changed `CAMERA_CURATION[599]["direction"]` from `"Inbound"` to `"None"` in `clean_dataset_v1.py` | `direction`: `Inbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-10` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=603` (Batch 3) | `location_detail_th`/`en` stated `From Surasak Intersection` (only the side stop-line on Silom Rd left edge), whereas the main corridor stretching ahead is Naradhiwas Rd Northbound (`no BTS viaduct`, `tree-lined median`) fed from Sathon-Naradhiwas Intersection | Updated `CAMERA_CURATION[603]` (`location_detail_th`, `location_detail_en`) in `clean_dataset_v1.py` | `location_detail_th`: `รถมาจากแยกสุรศักดิ์` -> `รถมาจากแยกสาทร-นราธิวาส`; `location_detail_en`: `From Surasak Intersection` -> `From Sathon-Naradhiwas Intersection` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-11` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=604` (Batch 3) | Full 4-way Silom–Naradhiwas junction view capturing both southbound (`Outbound`) & northbound (`Inbound`) carriageways on Naradhiwas Rd under the BTS viaduct plus Silom Rd cross-traffic; old label also referenced `แยกศาลาแดง` which is off-axis on Silom Rd | Updated `CAMERA_CURATION[604]` (`location_detail_th`, `location_detail_en`, `direction`) in `clean_dataset_v1.py` | `location_detail_th`: `ท้ายรถมุ่งหน้าแยกศาลาแดง / แยกสาทร-นราธิวาส` -> `บริเวณแยกสีลม-นราธิวาส (ด้านถนนนราธิวาสฯ มุ่งหน้าแยกสาทร-นราธิวาส)`; `direction`: `Inbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-12` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=11` (Batch 3) | Divided 5-lane Ratchawithi Rd view near Soi Ratchawithi 6 showing both eastbound (`Outbound`, left 1 lane + center 2 lanes from Victory Monument) and westbound (`Inbound`, right 2 lanes towards Victory Monument) simultaneously; description also mentioned only Victory Monument | Updated `CAMERA_CURATION[11]` (`location_detail_th`, `location_detail_en`, `direction`) in `clean_dataset_v1.py` | `location_detail_th`: `รถมาจากอนุสาวรีย์ชัยสมรภูมิ` -> `ช่วงอนุสาวรีย์ชัยสมรภูมิ – แยกสามเหลี่ยมดินแดง (ทั้งสองทิศทาง)`; `direction`: `Outbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-13` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=82` (Batch 3) | `V1.0` metadata stated `From Mo Leng towards Pratu Nam` (`Inbound`), describing only the 1 leftmost contraflow bus lane; time-sliced imagery (`06:01`–`20:51`) confirms the 4 main right lanes flow northbound (`Pratu Nam -> Mo Leng`, `Outbound`) all day while the 1 left lane runs southbound contraflow traffic (`Inbound`, active mainly in morning hours) | Updated `CAMERA_CURATION[82]` (`location_detail_th`, `location_detail_en`, `direction`) in `clean_dataset_v1.py` | `location_detail_th`: `รถมาจากแยกหมอเหล็ง มุ่งหน้าแยกประตูน้ำ` -> `ช่วงแยกประตูน้ำ – แยกหมอเหล็ง (ทั้งสองทิศทาง: 4 เลนไปหมอเหล็ง / 1 เลนไปประตูน้ำ)`; `direction`: `Inbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-14` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=239` (Batch 3) | Peer QA verification of `cctv_images/239/` and metadata (`location_*`, `district`, `corridor`, `direction`) | Verified imagery (`From Pathum Wan towards Sam Yan`, 4 main southbound `Inbound` lanes in front of Triam Udom Suksa School; only a small fringe of the opposite northbound carriageway appears at far top-left); no metadata errors found | No changes (`V1.0` baseline confirmed) | Yes (`clean_dataset_v1.py` unchanged) |
| `CHG-B3-15` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=432` (Batch 3) | `V1.0` listed generic `Sam Yan Intersection` with `direction="None"`, whereas imagery shows a single clear westbound approach on Rama 4 Rd (`4` straight lanes + `1` left-turn slip lane onto Si Phraya Rd, looking East under the Thai-Japanese Flyover towards Henri Dunant / Silom) | Updated `CAMERA_CURATION[432]` (`location_detail_th`, `location_detail_en`, `direction`) in `clean_dataset_v1.py` | `location_detail_th`: `บริเวณแยกสามย่าน (ถนนพญาไท-พระรามที่ 4)` -> `รถมาจากสีลม มุ่งหน้าไปหัวลำโพง (บริเวณแยกสามย่าน ถนนพระรามที่ 4)`; `direction`: `None` -> `Inbound` | Yes (`clean_dataset_v1.py`) |
| `CHG-B3-16` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=542` (Batch 3) | Peer QA verification of `cctv_images/542/` and metadata (`location_*`, `district`, `corridor`, `direction`) | Verified bidirectional Sarasin–Lang Suan junction view beside Lumphini Park (`3` eastbound lanes left + `3` westbound lanes right, `direction="None"`) across day/night samples; no broken images or metadata errors found | No changes (`V1.0` baseline confirmed) | Yes (`clean_dataset_v1.py` unchanged) |
| `CHG-B3-17` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=619` (Batch 3) | Peer QA verification of `cctv_images/619/` and metadata (`location_*`, `district`, `corridor`, `direction`) | Verified multi-direction Henri Dunant Intersection box view under the Thai-Japanese Flyover (`PT-06-CH2`, cross-traffic across Henri Dunant Rd & Rama 4 Rd, `direction="None"`); no broken images or metadata errors found | No changes (`V1.0` baseline confirmed) | Yes (`clean_dataset_v1.py` unchanged) |
| `CHG-B3-18` | `2026-11-15` | `V1.1` | เฟิร์ม (`@nontaphatfirm`) | `cam_id=277` (Batch 3) | `V1.0` listed `Footbridge near Soi Rang Nam on Phayathai Road (Victory Monument)` / `รถมุ่งหน้าไปแยกพญาไท (ซอยรางน้ำ)` with `direction="Inbound"`, whereas `RW-3-3-CAM2` (`13.76429, 100.53867`) captures the Victory Monument Roundabout (`Phayathai Island` corner under the BTS Skywalk) with traffic circulating clockwise around the roundabout and splitting/entering across multiple directions | Updated `CAMERA_CURATION[277]` (`location_th`, `location_detail_th`, `location_en`, `location_detail_en`, `direction`) in `clean_dataset_v1.py` | `location_en`: `Footbridge near Soi Rang Nam...` -> `Victory Monument Roundabout`; `location_detail_th`: `รถมุ่งหน้าไปแยกพญาไท (ซอยรางน้ำ)` -> `บริเวณวงเวียนอนุสาวรีย์ชัยสมรภูมิ (มุมเกาะพญาไท เห็นรถวนรอบวงเวียนและแยกออกหลายทิศทาง)`; `direction`: `Inbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-01` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=26`, `cam_id=1195` (Batch 4) | Both `26` and `1195` watch Charoen Nakhon Rd from opposite sides of Bukkhalo Intersection (neither feed captures Mahai Sawan Rd); `1195` faces Outbound rather than Inbound | Updated `CAMERA_CURATION` in `clean_dataset_v1.py` and `CAMERA_AUDIT_CHECKLIST.md` (`pair_id`, `pair_type`, `1195` `location_*` & `direction`) | `pair_id`: `PAIR_JX_BUKKHALO` -> `PAIR_ARM_BUKKHALO`; `pair_type`: `perpendicular_junction` -> `opposite_intersection_arm`; `1195` `direction`: `Inbound` -> `Outbound`; `1195` Mahai Sawan labels -> Charoen Nakhon Rd | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-02` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=500`, `cam_id=1188` (Batch 4) | `500` contains a significant proportion (`>10%`) of unusable artifact images; `1188` is a wide-angle view whose nighttime frames are completely unusable due to tiny vehicles and severe glare | Logged recommendation to remove `500` and `1188` from the downstream dataset (kept `clean_dataset_v1.py`, `CAMERA_AUDIT_CHECKLIST.md`, and 100-cam contract unchanged pending team/maintainer decision & location detail verification) | Pending exclusion decision (`100 -> 98` cameras or `0` valid images retained for `500`/`1188`) | No (Pending decision) |
| `CHG-B4-03` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=32` (Batch 4) | Location labels are accurate, but the camera view clearly captures traffic flowing in both directions along Thoet Thai Rd | Updated `direction` to `"None"` in `CAMERA_CURATION` (`clean_dataset_v1.py`) and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=32` `direction`: `Inbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-04` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=36` (Batch 4) | Wide view of Ratchada-Ratchaphruek intersection with traffic going in multiple directions; camera is on the Ratchadaphisek Rd side with traffic approaching from Mahai Sawan Intersection (not Ratchaphruek Rd / Taksin) | Updated `location_*`, `location_detail_*`, and `direction` in `CAMERA_CURATION` (`clean_dataset_v1.py`) and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=36`: `location_*` Ratchaphruek Rd -> Ratchadaphisek Rd; `location_detail_*` Taksin -> Mahai Sawan Intersection; `direction`: `Outbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-05` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=158` (Batch 4) | Dominant 3-lane foreground carriageway flows Outbound (towards Bukkhalo Intersection); `location_detail_th` also said `ขาเข้า` | Updated `direction` to `"Outbound"` and aligned `location_detail_th` (`ขาเข้า` -> `ขาออก`) in `CAMERA_CURATION` (`clean_dataset_v1.py`), and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=158`: `direction`: `Inbound` -> `Outbound`; `location_detail_th`: `ขาเข้า` -> `ขาออก` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-06` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=251` (Batch 4) | English temple spelling mismatch vs. Google Maps (`Wat Dishongsaram` -> `Wat Ditsahongsaram (Wat Makkasan)`) and flow direction is Outbound (away from CBD towards Mit Samphan) | Updated `location_en` and `direction` in `CAMERA_CURATION` (`clean_dataset_v1.py`), and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=251`: `location_en` `Wat Dishongsaram` -> `Wat Ditsahongsaram (Wat Makkasan)`; `direction`: `Inbound` -> `Outbound` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-07` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=256` (Batch 4) | Centered two-way view over undivided Phetchaburi Rd (2 left lanes often congested vs. 4-5 opposing lanes free-flowing, plus tidal contraflow); expressway destination is Chalerm Maha Nakhon Expressway (`ใต้ทางด่วนเฉลิมมหานคร`) | Updated `direction` to `"None"` and refined `location_detail_th` / `location_detail_en` in `CAMERA_CURATION` (`clean_dataset_v1.py`), and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=256`: `direction`: `Outbound` -> `None`; `location_detail_*`: `Phetchaburi Expressway Intersection` -> `Chalerm Maha Nakhon Expressway` (`ใต้ทางด่วนเฉลิมมหานคร`) | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-08` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=500` (Batch 4) | Coordinates `(13.75001, 100.54103)` and map view confirm `500` is actually Pratu Nam Intersection (not Mit Samphan Intersection), with traffic from Ratchathewi heading towards `cam_id=256` and multi-directional intersection flow | Updated `location_*`, `location_detail_*`, and `direction` (`"None"`) in `CAMERA_CURATION` (`clean_dataset_v1.py`), and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` (`CHG-003` removal proposal remains open) | `cam_id=500`: `location_*` Mit Samphan -> Pratu Nam Intersection (`แยกประตูน้ำ`); `direction`: `Inbound` -> `None` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-09` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=529` (Batch 4) | Crossing interchange view split ~50/50 across roads with neither direction heading directly into central Bangkok | Updated `direction` to `"None"`, dropped `(Inbound)` / `(ฝั่งขาเข้า)` from `location_*` and `location_detail_*` in `CAMERA_CURATION` (`clean_dataset_v1.py`), and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=529`: `direction`: `Inbound` -> `None`; removed `(Inbound)` / `(ฝั่งขาเข้า)` from location labels | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-10` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=572` (Batch 4) | Ramp traffic flows Inbound onto the elevated highway and is strictly ascending (not ascending/descending) | Updated `direction` to `"Inbound"` and `location_detail_en` (`Taling Chan ascending/descending ramp` -> `Taling Chan ascending ramp`) in `CAMERA_CURATION` (`clean_dataset_v1.py`), and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=572`: `direction`: `None` -> `Inbound`; `location_detail_en`: `ascending/descending` -> `ascending` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-11` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=595` (Batch 4) | Wide fisheye view of Ban Khaek Intersection covering crossing traffic on both Itsaraphap and Prajadhipok (`ประชาธิปก`) Roads (with left leg barriered off) | Added Prajadhipok Rd (`ประชาธิปก`) to `location_detail_*` and set `direction` to `"None"` in `CAMERA_CURATION` (`clean_dataset_v1.py`), and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` | `cam_id=595`: `direction`: `Inbound` -> `None`; `location_detail_*` updated to include `ประชาธิปก` / `Prajadhipok Roads` | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-12` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=1188` (Batch 4) | Camera overlooks Kanchanaphisek Road (Motorway 9 / Western Outer Ring Rd) facing towards Bang Chueak Nang Interchange (`ทางแยกต่างระดับบางเชือกหนัง`) in both directions, rather than Borommaratchachonnani / Phutthamonthon Sai 2 | Updated `location_*` and `location_detail_*` in `CAMERA_CURATION` (`clean_dataset_v1.py`), kept `direction="None"`, and checked off `[x]` in `CAMERA_AUDIT_CHECKLIST.md` (`CHG-003` removal proposal remains open) | `cam_id=1188`: `location_*` Borommaratchachonnani / Phutthamonthon Sai 2 -> Kanchanaphisek Road (Chimphli Interchange) towards Bang Chueak Nang Interchange | Yes (`clean_dataset_v1.py`) |
| `CHG-B4-13` | `2026-11-15` | `V1.1` | สอง (@theme222) | `cam_id=32, 158, 529, 595, 1076` (Batch 4) | Visual sweep flagged `22` unusable frames slipping past automated gates (`2` `scanline_smear`, `17` `corrupt_artifact`, `1` `frozen_visual`, `2` `blocked_lens` rainwater) | Added all `22` filenames to `MANUAL_EXCLUDED_IMAGES` in `clean_dataset_v1.py` | `-22` broken images queued for exclusion (`32`: 2, `158`: 8, `529`: 9, `595`: 1, `1076`: 2) | Yes (`clean_dataset_v1.py`) |

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

### `V1.1` -- `2026-11-15` *(In Progress: Peer QA & Refinement)*

#### Batch 1 -- ปลื้ม (@siravidthongsook): Ratchadaphisek Corridor (17 cameras)

- **Date:** `2026-11-15`
- **Editor:** ปลื้ม (@siravidthongsook)
- **Batch / Scope:** Batch 1 -- `17` cameras (`112`, `118`, `119`, `120`, `123`, `124`, `125`, `126`, `127`, `135`, `211`, `212`, `215`, `219`, `224`, `225`, `1408`)
- **Problem Found:**
  - `cam_id=119` / `cam_id=120` (Ratchada-Sutthisan, `PAIR_ARM_SUTTHISAN`): the two opposite arms carried each other's coordinates, so the Ratchadaphisek Road camera sat on the Sutthisan Winitchai Road arm and vice versa (≈ `30-40 m` cross-arm error).
  - `cam_id=224` / `cam_id=225` (Criminal Court footbridge, `FB_04_CriminalCourt`): same pattern -- longitudes swapped between the inbound and outbound spans.
  - `cam_id=127` (Soi Ratchadaphisek 30, `FB_03_Ratchada30`): the pin sat on the road median, not on the outbound footbridge span.
  - `cam_id=120`: labelled `Inbound`, but the frame is a side-arm view carrying traffic in both directions.
  - Image sweep: `0` unusable frames across all `17` folders (no heavily corrupted, blocked, pitch-black, or residual frozen frames) -> nothing added to `MANUAL_EXCLUDED_IMAGES`.
  - `cam_id=225`: metadata verified, but its image folder was not visually swept in this pass (still unchecked in the audit checklist).
- **Fix / Decision Applied:**
  - Extended `CAMERA_CURATION` in [`00_data_cleaning_and_qa/src/clean_dataset_v1.py`](../00_data_cleaning_and_qa/src/clean_dataset_v1.py) with optional `lat` / `lon` keys that override the raw `cctv_info.csv` pin inside `build_cleaned_metadata()`:
    ```python
    "lat": float(meta.get("lat", row["latitude"])),
    "lon": float(meta.get("lon", row["longitude"])),
    ```
  - Applied `5` coordinate corrections and `1` direction correction in the same table; no threshold or gate changes.
- **Quantitative Impact (Before -> After):**
  - Metadata fields changed (`cctv_info_cleaned` after the maintainer re-runs the script):
    - `cam_id=119`: `lat` `13.78971 -> 13.789680`, `lon` `100.57410 -> 100.574437`
    - `cam_id=120`: `lat` `13.78968 -> 13.789785`, `lon` `100.57441 -> 100.574031`, `direction` `Inbound -> None`
    - `cam_id=127`: `lat` `13.81001 -> 13.810192`, `lon` `100.57511 -> 100.575261`
    - `cam_id=224`: `lat` `13.81524 -> 13.815228`, `lon` `100.57553 -> 100.575355`
    - `cam_id=225`: `lat` `13.81523 -> 13.815248`, `lon` `100.57533 -> 100.575513`
  - Direction distribution now: `Inbound` `50`, `Outbound` `29`, `None` `21` (was `51 / 29 / 20`).
  - Images affected: `0` (`60,210` valid images stay `60,210`; metadata-only change).
- **Verification:** `CAMERA_CURATION` parsed and compared field-by-field against the Batch 1 review answers (`17/17` cameras match); `py_compile` `PASS`. PR (`chore/00-qa-siravid` -> `main`) -> final `clean_dataset_v1.py` + `run_pipeline.py --check-contract` run `[Pending Maintainer Run]`.

---

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
