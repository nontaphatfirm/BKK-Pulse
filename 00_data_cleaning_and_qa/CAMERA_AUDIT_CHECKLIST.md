# 100-Camera Metadata Peer Audit Checklist (`CAMERA_AUDIT_CHECKLIST.md`)

> **Instructions:** The 100 CCTV cameras in [`Dataset_Clean_V1/cctv_info_cleaned.csv`](../Dataset_Clean_V1/cctv_info_cleaned.csv) are partitioned into **6 corridor-aligned batches (16-17 cameras per team member)**. Camera pairs sharing a `pair_id` are grouped within the same member's batch for side-by-side verification.  
> **Consolidated Status (`V2.0` Final Lock, 2026-11-17):** All 6 Peer QA PRs (`#2`, `#4`, `#6`, `#7`, `#8`, `#9`), `cam_id=225` visual sweep (**`100 / 100` `[x]`**), and Batch 4 `CHG-B4-02` resolution (`cam_id=500`: `78` severe corruptions excluded -> `522` clean frames; `cam_id=1188`: all `607` frames retained) are consolidated into `main`. **`100 / 100` cameras** audited (`56` metadata updates; **`Inbound: 32` | `Outbound: 23` | `None: 45`**) with **`181` `manual_excluded` frames** queued in `MANUAL_EXCLUDED_IMAGES`.

## Peer QA Progress Summary

| Batch | Owner (GitHub) | Cameras | Visual Sweep `[x]` | Metadata Edited | Manual Frame Exclusions | Status / Notes |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **1** | **ปลื้ม** (`@siravidthongsook`) | `17` | `17 / 17` | `5` cams (`119, 120, 127, 224, 225`) | `0` | Complete (`225` visual sweep verified clean `607/607`) |
| **2** | **กร** (`@kkooAAA`) | `16` | `16 / 16` | `5` cams (`938, 939, 1112, 1804, 1815`) | `18` (`1815`) | `28` identical Drive duplicate files in `136`/`176` noted for Drive `V2.0` sync |
| **3** | **เฟิร์ม** (`@nontaphatfirm`) | `17` | `17 / 17` | `11` cams (`11, 75, 82, 88, 194, 206, 277, 432, 599, 603, 604`) | `6` (`206`) | Also cross-checked Batch 1 `211` |
| **4** | **สอง** (`@theme222`) | `17` | `17 / 17` | `12` cams (`26, 32, 36, 158, 251, 256, 500, 529, 572, 595, 1188, 1195`) | `100` (`32, 158, 500, 529, 595, 1076`) | Resolved `CHG-B4-02` (`V2.0`): kept `500` (`-78` corrupt -> `522` clean) & `1188` (`607/607`) |
| **5** | **นิว** (`@Pranithi-New`) | `17` | `17 / 17` | `15` cams (`18, 70, 150, 230, 233, 301, 332, 363, 370, 371, 546, 915, 1063, 1361, 1368`) | `25` (`169`: 20, `332`: 5) | `370/371` low contrast & `546/1368` glare verified healthy |
| **6** | **โม่** (`@moaqilo`) | `16` | `16 / 16` | `8` cams (`68, 414, 556, 576, 630, 1039, 1060, 1362`) | `32` (`68`: 1, `413`: 1, `630`: 25, `1039`: 5) | `1362` coords & road label updated |
| **Total** | **All 6 Members** | **`100`** | **`100 / 100`** | **`56`** (`100 / 100` audited) | **`181`** | **`Inbound: 32` · `Outbound: 23` · `None: 45` (`V2.0` Final Lock)** |

---

## Batch 1 -- ปลื้ม (@siravidthongsook): Ratchadaphisek Corridor (17 Cameras)
*Focus: Bidirectional footbridge pairs `126/127` (Soi Ratchada 30), `224/225` (Criminal Court), and Sutthisan / Lat Phrao / Thiam Ruam Mit intersections.*

| Verified | `cam_id` | `location_en` | `location_detail_en` | `location_th` | `district` | `corridor` | `pair_id` | `direction` |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| [x] | `112` | Thiam Ruam Mit Intersection (Thiam Ruam Mit Road) | Towards Huai Khwang / Ratchadaphisek Road | แยกเทียมร่วมมิตร (ถนนเทียมร่วมมิตร) | Huai Khwang | Ratchadaphisek | `PAIR_JX_THIAMRUAMMIT` | `Inbound` |
| [x] | `1408` | Thiam Ruam Mit Intersection (Cyber World Tower) | At Thiam Ruam Mit Intersection (in front of Cyber World Tower) | แยกเทียมร่วมมิตร (หน้าอาคารไซเบอร์เวิลด์) | Huai Khwang | Ratchadaphisek | `PAIR_JX_THIAMRUAMMIT` | `None` |
| [x] | `118` | Ratchada-Sutthisan Intersection (Sutthisan Winitchai Road) | At Ratchada-Sutthisan Intersection (Sutthisan Winitchai Road side) | แยกรัชดา-สุทธิสาร (ด้านถนนสุทธิสารวินิจฉัย) | Huai Khwang | Ratchadaphisek | `PAIR_ARM_SUTTHISAN` | `None` |
| [x] | `119` | Ratchada-Sutthisan Intersection (Sutthisan Winitchai Road) | At Ratchada-Sutthisan Intersection (Sutthisan Winitchai Road side) *(coords updated)* | แยกรัชดา-สุทธิสาร (ด้านถนนสุทธิสารวินิจฉัย) | Huai Khwang | Ratchadaphisek | `PAIR_ARM_SUTTHISAN` | `None` |
| [x] | `120` | Ratchada-Sutthisan Intersection (Sutthisan Winitchai Road) | At Ratchada-Sutthisan Intersection *(coords updated)* | แยกรัชดา-สุทธิสาร (ด้านถนนสุทธิสารวินิจฉัย) | Huai Khwang | Ratchadaphisek | `PAIR_ARM_SUTTHISAN` | `None` |
| [x] | `123` | Ratchada-Lat Phrao Intersection (Ratchadaphisek Road) | From Ratchada-Sutthisan Intersection | แยกรัชดา-ลาดพร้าว (ด้านถนนรัชดาภิเษก) | Chatuchak | Ratchadaphisek | `PAIR_ARM_RATCHADALATPHRAO` | `Outbound` |
| [x] | `124` | Ratchada-Lat Phrao Intersection (Lat Phrao Road) | At Ratchada-Lat Phrao Intersection | แยกรัชดา-ลาดพร้าว (ด้านถนนลาดพร้าว) | Chatuchak | Ratchadaphisek | `PAIR_ARM_RATCHADALATPHRAO` | `None` |
| [x] | `125` | Ratchada-Lat Phrao Intersection (Ratchadaphisek Road) | From Ratchayothin Intersection towards Ratchada-Sutthisan | แยกรัชดา-ลาดพร้าว (ด้านถนนรัชดาภิเษก) | Chatuchak | Ratchadaphisek | `PAIR_ARM_RATCHADALATPHRAO` | `Inbound` |
| [x] | `126` | Footbridge near Soi Ratchadaphisek 30 on Ratchadaphisek Road | From Ratchayothin Intersection towards Ratchada-Lat Phrao Intersection | สะพานลอยซอยรัชดาภิเษก 30 ถนนรัชดาภิเษก | Chatuchak | Ratchadaphisek | `FB_03_Ratchada30` | `Inbound` |
| [x] | `127` | Footbridge near Soi Ratchadaphisek 30 on Ratchadaphisek Road | From Ratchada-Lat Phrao Intersection towards Ratchayothin Intersection *(coords updated)* | สะพานลอยซอยรัชดาภิเษก 30 ถนนรัชดาภิเษก | Chatuchak | Ratchadaphisek | `FB_03_Ratchada30` | `Outbound` |
| [x] | `135` | Footbridge in front of Toyota Sure on Ratchadaphisek Road | Between Ratchayothin and Ratchada-Lat Phrao Intersections (both directions visible) | สะพานลอยหน้าโตโยต้าชัวร์ ถนนรัชดาภิเษก | Chatuchak | Ratchadaphisek | `None` | `None` |
| [x] | `211` | Footbridge near Soi Ratchadaphisek 3 on Ratchadaphisek Road | From Rama 9 Intersection towards Thiam Ruam Mit Intersection | สะพานลอยใกล้ซอยรัชดาภิเษก 3 ถนนรัชดาภิเษก | Din Daeng | Ratchadaphisek | `None` | `Outbound` |
| [x] | `212` | Footbridge near Big C Ratchadaphisek on Ratchadaphisek Road | From Thiam Ruam Mit Intersection towards Rama 9 Intersection | สะพานลอยใกล้บิ๊กซีรัชดา ถนนรัชดาภิเษก | Din Daeng | Ratchadaphisek | `None` | `Inbound` |
| [x] | `215` | Footbridge near Soi Ratchadaphisek 7 on Ratchadaphisek Road | From Thiam Ruam Mit Intersection towards Huai Khwang Intersection | สะพานลอยใกล้ซอยรัชดาภิเษก 7 ถนนรัชดาภิเษก | Din Daeng | Ratchadaphisek | `None` | `Outbound` |
| [x] | `219` | Footbridge near Soi Ratchadaphisek 14 on Ratchadaphisek Road | From Ratchada-Sutthisan Intersection towards Huai Khwang Intersection | สะพานลอยใกล้ซอยรัชดาภิเษก 14 ถนนรัชดาภิเษก | Huai Khwang | Ratchadaphisek | `None` | `Inbound` |
| [x] | `224` | Footbridge near The Criminal Court on Ratchadaphisek Road | From Ratchayothin Intersection towards Ratchada-Lat Phrao Intersection *(coords updated)* | สะพานลอยใกล้ศาลอาญา ถนนรัชดาภิเษก | Chatuchak | Ratchadaphisek | `FB_04_CriminalCourt` | `Inbound` |
| [x] | `225` | Footbridge near The Criminal Court on Ratchadaphisek Road | From Ratchada-Lat Phrao Intersection towards Ratchayothin Intersection *(coords updated)* | สะพานลอยใกล้ศาลอาญา ถนนรัชดาภิเษก | Chatuchak | Ratchadaphisek | `FB_04_CriminalCourt` | `Outbound` |

> **Batch 1 note:** `225` metadata (position + `Outbound` direction) and full `607`-frame visual/optical folder sweep (`0` corrupted frames; rain/lens droplets on `29_1511`, `29_1521`, `30_1641` retained for Task 04) verified clean (`17 / 17`).

---

## Batch 2 -- กร (@kkooAAA): Phahon Yothin - Lat Phrao & East Bangkok Corridors (16 Cameras)
*Focus: Bidirectional footbridge pairs `136/137` (Big C Lat Phrao), `176/177` (Chatuchak Park), `178/179` (Phyathai 2 Hospital), and Ramkhamhaeng / On Nut cameras.*

| Verified | `cam_id` | `location_en` | `location_detail_en` | `location_th` | `district` | `corridor` | `pair_id` | `direction` |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| [x] | `1815` | Rama 9 Intersection | From Phang Mueang Intersection *(18 view-changed exclusions)* | แยกพระราม 9 | Din Daeng | Ratchadaphisek | `None` | `Inbound` |
| [x] | `136` | Footbridge near Big C Extra (Soi Lat Phrao 7) on Lat Phrao Road | From Lat Phrao Intersection towards Ratchada-Lat Phrao Intersection | สะพานลอยใกล้บิ๊กซีเอ็กซ์ตร้า ลาดพร้าว | Chatuchak | Phahon Yothin - Lat Phrao | `FB_01_LatPhrao_BigC` | `Outbound` |
| [x] | `137` | Footbridge near Big C Extra (Soi Lat Phrao 7) on Lat Phrao Road | From Ratchada-Lat Phrao Intersection towards Lat Phrao Intersection | สะพานลอยใกล้บิ๊กซีเอ็กซ์ตร้า ลาดพร้าว | Chatuchak | Phahon Yothin - Lat Phrao | `FB_01_LatPhrao_BigC` | `Inbound` |
| [x] | `139` | Footbridge in front of Horwang School on Phahon Yothin Road | From Ratchayothin Intersection towards Lat Phrao Intersection | สะพานลอยหน้าโรงเรียนหอวัง ถนนพหลโยธิน | Chatuchak | Phahon Yothin - Lat Phrao | `None` | `Inbound` |
| [x] | `141` | Footbridge in front of PTT HQ near Soi Vibhavadi Rangsit 11 | From Lat Phrao Intersection towards Ratchawipha Interchange | สะพานลอยหน้าบริษัท ปตท. จำกัด (มหาชน) ถนนวิภาวดีรังสิต | Chatuchak | Phahon Yothin - Lat Phrao | `None` | `Outbound` |
| [x] | `170` | Footbridge near Nawutti Somdet Ya Hospital on Phahon Yothin Road | From Victory Monument towards Saphan Khwai Intersection | สะพานลอยใกล้โรงพยาบาลนวุติสมเด็จย่า ถนนพหลโยธิน | Phaya Thai | Phahon Yothin - Lat Phrao | `None` | `Outbound` |
| [x] | `176` | Footbridge in front of Chatuchak Park on Phahon Yothin Road | From Lat Phrao Intersection towards Kamphaeng Phet Intersection | สะพานลอยหน้าสวนจตุจักร ถนนพหลโยธิน | Chatuchak | Phahon Yothin - Lat Phrao | `FB_05_ChatuchakPark` | `Inbound` |
| [x] | `177` | Footbridge in front of Chatuchak Park on Phahon Yothin Road | From Kamphaeng Phet Intersection towards Lat Phrao Intersection | สะพานลอยหน้าสวนจตุจักร ถนนพหลโยธิน | Chatuchak | Phahon Yothin - Lat Phrao | `FB_05_ChatuchakPark` | `Outbound` |
| [x] | `178` | Footbridge in front of Phyathai 2 Hospital on Phahon Yothin Road | From Saphan Khwai Intersection towards Victory Monument | สะพานลอยหน้าโรงพยาบาลพญาไท 2 ถนนพหลโยธิน | Phaya Thai | Phahon Yothin - Lat Phrao | `FB_02_Phyathai2` | `Inbound` |
| [x] | `179` | Footbridge in front of Phyathai 2 Hospital on Phahon Yothin Road | From Victory Monument towards Saphan Khwai Intersection | สะพานลอยหน้าโรงพยาบาลพญาไท 2 ถนนพหลโยธิน | Phaya Thai | Phahon Yothin - Lat Phrao | `FB_02_Phyathai2` | `Outbound` |
| [x] | `1070` | Footbridge near Soi Phahon Yothin 18/2 on Phahon Yothin Road | From Kamphaeng Phet Intersection towards Lat Phrao Intersection | สะพานลอยใกล้ซอยพหลโยธิน 18/2 ถนนพหลโยธิน | Chatuchak | Phahon Yothin - Lat Phrao | `None` | `Outbound` |
| [x] | `1071` | Kamphaeng Phet Intersection (Phahon Yothin Road) | At Kamphaeng Phet Intersection (Phahon Yothin Road side) | แยกกำแพงเพชร (ด้านถนนพหลโยธิน) | Chatuchak | Phahon Yothin - Lat Phrao | `None` | `None` |
| [x] | `1112` | Sutthisan Intersection (Sutthisan Winitchai Road) | Sutthisan Intersection (Sutthisan Winitchai Road) | แยกสุทธิสาร (ถนนสุทธิสารวินิจฉัย) | Din Daeng | Phahon Yothin - Lat Phrao | `None` | `None` |
| [x] | `938` | Ramkhamhaeng - Rama 9 Intersection | Ramkhamhaeng - Rama 9 Intersection *(98 frozen frames)* | แยกรามคำแหง-พระราม 9 | Bang Kapi | East Bangkok (Ramkhamhaeng - On Nut) | `None` | `None` |
| [x] | `939` | Mahadthai Intersection | Mahadthai Intersection (Ramkhamhaeng Bridge) *(95 frozen frames)* | แยกมหาดไทย | Bang Kapi | East Bangkok (Ramkhamhaeng - On Nut) | `None` | `None` |
| [x] | `1804` | Entrance to Soi On Nut 33 on On Nut Road | Entrance to Soi On Nut 33 on On Nut Road *(16 rainbow frames)* | ปากซอยอ่อนนุช 33 ถนนอ่อนนุช | Suan Luang | East Bangkok (Ramkhamhaeng - On Nut) | `None` | `None` |

> **Batch 2 location audit notes (`CHG-B2-01`–`CHG-B2-05`):**
> - `1112` final road set to Sutthisan Winitchai Road (`CHG-B2-05`); district `Din Daeng` confirmed; `direction` set to `None`.
> - `939` clarified as Ramkhamhaeng Bridge; `1804` set to Soi On Nut 33 (`direction` -> `None`); `1815` confirmed on Rama 9 Road (`Din Daeng`, `Inbound`, `18` post-rotation frames excluded in `CHG-B2-02`).
> - `178` / `179`: extra physical references (~180 m / ~120 m after turning right from Phyathai 2 Hospital) recorded as code comments in `CAMERA_CURATION`.

---

## Batch 3 -- เฟิร์ม (@nontaphatfirm): Sathon - Naradhiwas - Rama 3 & Pathum Wan Corridors (17 Cameras)
*Focus: Silom / Sathon / Naradhiwas CBD cameras and Sam Yan / Henri Dunant / Lang Suan intersections.*

| Verified | `cam_id` | `location_en` | `location_detail_en` | `location_th` | `district` | `corridor` | `pair_id` | `direction` |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| [x] | `75` | Ratchada-Naradhiwas Intersection (Naradhiwas Road) | From Naradhiwas-Rama 3 Intersection | แยกรัชดา-นราธิวาส (ด้านถนนนราธิวาสฯ) | Yan Nawa | Sathon - Naradhiwas - Rama 3 | `None` | `Inbound` |
| [x] | `88` | Chan-Sathu Pradit Intersection | At Chan-Sathu Pradit Intersection | แยกจันทน์-สาธุประดิษฐ์ | Sathon | Sathon - Naradhiwas - Rama 3 | `None` | `None` |
| [x] | `186` | Directional sign gantry to Rama 3 Bridge on Ratchadaphisek Road | From Ratchada-Naradhiwas Intersection towards Sathu Pradit Intersection | โครงสร้างป้ายบอกทางขึ้นสะพานพระราม 3 ถนนรัชดาภิเษก | Yan Nawa | Sathon - Naradhiwas - Rama 3 | `None` | `Outbound` |
| [x] | `188` | Footbridge near Rama 3 Soi 68 on Rama 3 Road | From Na Ranong Intersection towards Nang Linchi Intersection | สะพานลอยใกล้ซอยพระรามที่ 3 ซอย 68 ถนนพระรามที่ 3 | Yan Nawa | Sathon - Naradhiwas - Rama 3 | `None` | `Outbound` |
| [x] | `194` | Footbridge near Soi Convent on North Sathon Road | From Witthayu Intersection towards Sathon-Naradhiwas Intersection | สะพานลอยใกล้ปากซอยคอนแวนต์ ถนนสาทรเหนือ | Bang Rak | Sathon - Naradhiwas - Rama 3 | `None` | `Outbound` |
| [x] | `196` | Footbridge in front of Makro on Naradhiwas Ratchanakharin Road | From Sathon-Naradhiwas Intersection towards Chan-Naradhiwas Intersection | สะพานลอยหน้าแม็คโคร ถนนนราธิวาสราชนครินทร์ | Sathon | Sathon - Naradhiwas - Rama 3 | `None` | `Outbound` |
| [x] | `206` | Footbridge opposite Soi Naradhiwas 20 on Naradhiwas Ratchanakharin Road | From Chan-Naradhiwas Intersection towards Ratchada-Naradhiwas Intersection *(6 exclusions; coords updated)* | สะพานลอยตรงข้ามซอยนราธิวาสราชนครินทร์ 20 ถนนนราธิวาสราชนครินทร์ | Yan Nawa | Sathon - Naradhiwas - Rama 3 | `None` | `Outbound` |
| [x] | `599` | Surasak Intersection | At Surasak Intersection | แยกสุรศักดิ์ | Bang Rak | Sathon - Naradhiwas - Rama 3 | `None` | `None` |
| [x] | `603` | Silom-Naradhiwas Intersection | At Silom-Naradhiwas Intersection | แยกสีลม-นราธิวาส | Bang Rak | Sathon - Naradhiwas - Rama 3 | `PAIR_JX_SILOM_NARADHIWAS` | `None` |
| [x] | `604` | Silom-Naradhiwas Intersection | At Silom-Naradhiwas Intersection | แยกสีลม-นราธิวาส | Bang Rak | Sathon - Naradhiwas - Rama 3 | `PAIR_JX_SILOM_NARADHIWAS` | `None` |
| [x] | `11` | Near Soi Ratchawithi 6 on Ratchawithi Road | Between Victory Monument and Din Daeng Intersection (both directions) | ใกล้ซอยราชวิถี 6 ถนนราชวิถี | Ratchathewi | Pathum Wan - Phetchaburi - Victory Monument | `None` | `None` |
| [x] | `82` | Footbridge near Soi Ratchaprarop 3 on Ratchaprarop Road | Between Pratu Nam and Mo Leng Intersections (both directions: 4 northbound / 1 southbound contraflow lane) | สะพานลอยใกล้ซอยราชปรารภ 3 ถนนราชปรารภ | Ratchathewi | Pathum Wan - Phetchaburi - Victory Monument | `None` | `None` |
| [x] | `239` | Footbridge near Triam Udom Suksa School on Phayathai Road | From Pathum Wan Intersection towards Sam Yan Intersection | สะพานลอยใกล้โรงเรียนเตรียมอุดมศึกษา ถนนพญาไท | Pathum Wan | Pathum Wan - Phetchaburi - Victory Monument | `None` | `Inbound` |
| [x] | `432` | Sam Yan Intersection | From Silom towards Hua Lamphong (Sam Yan Intersection, Rama 4 Road) *(17 rainbow frames)* | ทางแยกสามย่าน | Pathum Wan | Pathum Wan - Phetchaburi - Victory Monument | `None` | `Inbound` |
| [x] | `542` | Lang Suan - Sarasin Intersection | Lang Suan - Sarasin Intersection near Lumphini Park | ทางแยกหลังสวน (สารสิน-หลังสวน) | Pathum Wan | Pathum Wan - Phetchaburi - Victory Monument | `None` | `None` |
| [x] | `619` | Henri Dunant Intersection | Henri Dunant Intersection *(Repaired row-shift)* | ทางแยกอังรีดูนังต์ | Pathum Wan | Pathum Wan - Phetchaburi - Victory Monument | `None` | `None` |
| [x] | `277` | Victory Monument Roundabout | Victory Monument Roundabout (Phayathai Island side, multi-directional roundabout traffic) | วงเวียนอนุสาวรีย์ชัยสมรภูมิ | Ratchathewi | Pathum Wan - Phetchaburi - Victory Monument | `None` | `None` |

---

## Batch 4 -- สอง (@theme222): Phetchaburi & Thon Buri - Charoen Nakhon - Borommaratchachonnani Corridors (17 Cameras)
*Focus: Bidirectional footbridge pair `1078/1132` (Wat Suwan on Charoen Nakhon), Bukkhalo pair `26/1195`, and Phutthamonthon Sai 2 `529`.*

| Verified | `cam_id` | `location_en` | `location_detail_en` | `location_th` | `district` | `corridor` | `pair_id` | `direction` |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| [x] | `250` | Footbridge near Soi Phetchaburi 38 on Phetchaburi Road | Between Phrom Phong and Asok-Phetchaburi Intersections (both directions visible) | สะพานลอยใกล้ซอยเพชรบุรี 38 ถนนเพชรบุรี | Ratchathewi | Pathum Wan - Phetchaburi - Victory Monument | `None` | `None` |
| [x] | `251` | Footbridge near Wat Ditsahongsaram (Wat Makkasan) on Phetchaburi Road | Between Phetchaburi Expressway and Mit Samphan Intersections (both directions visible) | สะพานลอยใกล้วัดดิสหงษาราม ถนนเพชรบุรี | Ratchathewi | Pathum Wan - Phetchaburi - Victory Monument | `None` | `None` |
| [x] | `256` | Footbridge near Soi Phetchaburi 27 on Phetchaburi Road | Between Pratu Nam Intersection and Chalerm Maha Nakhon Expressway (both directions visible) | สะพานลอยใกล้ซอยเพชรบุรี 27 ถนนเพชรบุรี | Ratchathewi | Pathum Wan - Phetchaburi - Victory Monument | `None` | `None` |
| [x] | `500` | Pratu Nam Intersection | At Pratu Nam Intersection *(78 corrupt/green exclusions)* | แยกประตูน้ำ | Ratchathewi | Pathum Wan - Phetchaburi - Victory Monument | `None` | `None` |
| [x] | `26` | Bukkhalo Intersection (Charoen Nakhon Road) | From Charoen Nakhon / Rat Burana Road | แยกบุคคโล (ด้านถนนเจริญนคร) | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `PAIR_ARM_BUKKHALO` | `Inbound` |
| [x] | `1195` | Bukkhalo Intersection (Charoen Nakhon Road) | At Bukkhalo Intersection (Charoen Nakhon Road side) | แยกบุคคโล (ด้านถนนเจริญนคร) | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `PAIR_ARM_BUKKHALO` | `None` |
| [x] | `32` | Bang Yi Ruea Intersection (Thoet Thai Road) | Bang Yi Ruea Intersection (Thoet Thai Road side) | แยกบางยี่เรือ (ด้านถนนเทอดไท) | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `None` |
| [x] | `36` | Ratchada-Ratchaphruek Intersection (Ratchadaphisek Road) | At Ratchada-Ratchaphruek Intersection | แยกรัชดา-ราชพฤกษ์ (ด้านถนนรัชดาภิเษก) | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `None` |
| [x] | `1103` | Ratchada-Ratchaphruek Intersection (Ratchadaphisek Road) | From Tha Phra Intersection | แยกรัชดา-ราชพฤกษ์ (ด้านถนนรัชดาภิเษก) | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `Inbound` |
| [x] | `1076` | Footbridge near Soi Thoet Thai 21 on Ratchaphruek Road | From Taksin Intersection towards Ratchada-Ratchaphruek Intersection | สะพานลอยใกล้ซอยเทอดไท 21 ถนนราชพฤกษ์ | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `Outbound` |
| [x] | `158` | Footbridge near Soi Charoen Nakhon 46 on Charoen Nakhon Road | Charoen Nakhon Road near Soi Charoen Nakhon 55 (both directions visible) | สะพานลอยใกล้ซอยเจริญนคร 46 ถนนเจริญนคร | Khlong San | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `None` |
| [x] | `1078` | Footbridge in front of Wat Suwan on Charoen Nakhon Road | From Khlong San Intersection towards Charoen Nakhon Tai Intersection | สะพานลอยหน้าวัดสุวรรณ ถนนเจริญนคร | Khlong San | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `FB_06_WatSuwan` | `Outbound` |
| [x] | `1132` | Footbridge in front of Wat Suwan on Charoen Nakhon Road | From Charoen Nakhon Tai Intersection towards Khlong San Intersection | สะพานลอยหน้าวัดสุวรรณ ถนนเจริญนคร | Khlong San | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `FB_06_WatSuwan` | `Inbound` |
| [x] | `529` | Phutthamonthon Sai 2 - Borommaratchachonnani Interchange | Phutthamonthon Sai 2 / Borommaratchachonnani | จุดตัดถนนพุทธมณฑลสาย 2 | Thawi Watthana | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `None` |
| [x] | `572` | Borommaratchachonnani Elevated Highway (Taling Chan Ramp) | Taling Chan ascending ramp | ทางคู่ขนานลอยฟ้าบรมราชชนนี (ช่วงทางขึ้นตลิ่งชัน) | Taling Chan | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `Inbound` |
| [x] | `1188` | Kanchanaphisek Road (Chimphli Interchange) | Overlooking Kanchanaphisek Road (Motorway 9) towards Bang Chueak Nang Interchange (both directions) | ถนนกาญจนาภิเษก (ต่างระดับฉิมพลี) | Taling Chan | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `None` |
| [x] | `595` | Ban Khaek Intersection | At Ban Khaek Intersection | แยกบ้านแขก | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `None` |

---

## Batch 5 -- นิว (@Pranithi-New): Dusit - Rama 5 - Samsen Corridor (17 Cameras)
*Focus: Bank of Thailand pair `70/1361`, Chitralada Palace pair `233/1063`, Saphan Daeng `18/1028`, Thewet `370/371`, and Panichayakarn `546/1368`.*

| Verified | `cam_id` | `location_en` | `location_detail_en` | `location_th` | `district` | `corridor` | `pair_id` | `direction` |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| [x] | `915` | Wongwian Yai Roundabout | At Wongwian Yai Roundabout | วงเวียนใหญ่ | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `None` |
| [x] | `18` | Saphan Daeng Intersection (Thahan Road) | Saphan Daeng Bridge towards Kiakkai Intersection (both directions visible) | แยกสะพานแดง (ด้านถนนทหาร) | Dusit | Old Town - Dusit - Rama 5 | `PAIR_OV_SAPHANDAENG` | `None` |
| [x] | `1028` | Saphan Daeng Intersection | Saphan Daeng Intersection | แยกสะพานแดง | Dusit | Old Town - Dusit - Rama 5 | `PAIR_OV_SAPHANDAENG` | `None` |
| [x] | `70` | In front of Bank of Thailand on Sam Sen Road | From Thewet Intersection towards Bang Khun Phrom Intersection (with contraflow lane) | หน้าธนาคารแห่งประเทศไทย ถนนสามเสน | Phra Nakhon | Old Town - Dusit - Rama 5 | `PAIR_2W_BOT_SAMSEN` | `None` |
| [x] | `1361` | In front of Bank of Thailand on Sam Sen Road | In front of Bank of Thailand (both main and contraflow lanes visible) | หน้าธนาคารแห่งประเทศไทย ถนนสามเสน | Phra Nakhon | Old Town - Dusit - Rama 5 | `PAIR_2W_BOT_SAMSEN` | `None` |
| [x] | `150` | Footbridge near Samsenwittayalai School on Rama 6 Road | Between Ari Samphan and Pradiphat Intersections (both directions visible) *(124 frozen frames)* | สะพานลอยใกล้โรงเรียนสามเสนวิทยาลัย ถนนพระรามที่ 6 | Phaya Thai | Old Town - Dusit - Rama 5 | `None` | `None` |
| [x] | `169` | Footbridge in front of Wat Sao Hin near Soi Wong Sawang 3 on Wong Sawang Road | From Rama 7 Bridge towards Wong Sawang Intersection *(20 gray P-frame exclusions)* | สะพานลอยหน้าวัดเสาหิน ใกล้ซอยวงศ์สว่าง 3 ถนนวงศ์สว่าง | Bang Sue | Old Town - Dusit - Rama 5 | `None` | `Inbound` |
| [x] | `230` | Entrance to Soi Ranong 2 on Rama 5 Road | Between Saphan Daeng and Kesakomon Intersections (both directions visible) | ปากซอยระนอง 2 ถนนพระรามที่ 5 | Dusit | Old Town - Dusit - Rama 5 | `None` | `None` |
| [x] | `233` | Opposite Chitralada Palace on Rama 5 Road | Between Ratchawithi and Wat Benchamabophit Intersections (both directions visible) | ตรงข้ามพระตำหนักจิตรลดารโหฐาน ถนนพระรามที่ 5 | Dusit | Old Town - Dusit - Rama 5 | `PAIR_2W_CHITRALADA` | `None` |
| [x] | `1063` | Opposite Chitralada Palace on Rama 5 Road | Between Wat Benchamabophit and Ratchawithi Intersections (both directions visible) | ตรงข้ามพระตำหนักจิตรลดารโหฐาน ถนนพระรามที่ 5 | Dusit | Old Town - Dusit - Rama 5 | `PAIR_2W_CHITRALADA` | `None` |
| [x] | `301` | U Thong Nok Intersection | At U Thong Nok Intersection (U Thong Nok Road side) | แยกอู่ทองนอก | Dusit | Old Town - Dusit - Rama 5 | `None` | `None` |
| [x] | `332` | Ratchawat Intersection | Ratchawat Intersection towards Phichai Intersection (both directions and cross traffic visible) *(5 scanline smear exclusions)* | แยกราชวัตร | Dusit | Old Town - Dusit - Rama 5 | `None` | `None` |
| [x] | `363` | Khet Dusit Intersection | Khet Dusit Intersection, Rama 5 & Sukhothai Roads (multi-directional view) | แยกเขตดุสิต | Dusit | Old Town - Dusit - Rama 5 | `None` | `None` |
| [x] | `370` | Thewet Intersection | Krung Kasem Rd between Thewet and Pracha Kasem Intersections (both directions) *(low contrast_std verified healthy)* | แยกเทเวศร์ | Phra Nakhon | Old Town - Dusit - Rama 5 | `PAIR_OV_THEWET` | `None` |
| [x] | `371` | Thewet Intersection | Thewet Intersection crosswalks (multi-directional intersection view) *(low contrast_std verified healthy)* | แยกเทเวศร์ | Phra Nakhon | Old Town - Dusit - Rama 5 | `PAIR_OV_THEWET` | `None` |
| [x] | `546` | Panichayakarn Intersection (Phitsanulok Road) | At Panichayakarn Intersection (Phitsanulok Road side) *(night wet-road glare kept for Task 04)* | แยกพาณิชยการ (ด้านถนนพิษณุโลก) | Dusit | Old Town - Dusit - Rama 5 | `PAIR_JX_PANICHAYAKARN` | `None` |
| [x] | `1368` | Panichayakarn Intersection (Rama 5 Road) | Rama 5 Rd side past RMUTP (both directions) *(night wet-road glare kept for Task 04)* | แยกพาณิชยการ (ด้านถนนพระรามที่ 5) | Dusit | Old Town - Dusit - Rama 5 | `PAIR_JX_PANICHAYAKARN` | `None` |

---

## Batch 6 -- โม่ (@moaqilo): Historic Old Town - Phra Nakhon - Pom Prap Sattru Phai Corridor (16 Cameras)
*Focus: Phra Athit pair `411/412`, Sao Chingcha `395` (`348x261` resolution), Bang Lamphu, Worachak, and Klang Hospital.*

| Verified | `cam_id` | `location_en` | `location_detail_en` | `location_th` | `district` | `corridor` | `pair_id` | `direction` |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| [x] | `68` | In front of Bangkok Bank Worachak Branch on Worachak Road | Between Worachak and Maen Si Intersections (both directions visible) *(1 blocked_by_crow exclusion)* | หน้าธนาคารกรุงเทพ สาขาวรจักร | Pom Prap Sattru Phai | Old Town - Dusit - Rama 5 | `None` | `None` |
| [x] | `228` | In front of Klang Hospital on Luang Road | From Klang Hospital Intersection towards Worachak Intersection | หน้าโรงพยาบาลกลาง ถนนหลวง | Pom Prap Sattru Phai | Old Town - Dusit - Rama 5 | `None` | `Inbound` |
| [x] | `395` | Sao Chingcha Intersection | Sao Chingcha Intersection *(348x261 px, 72 frozen frames)* | แยกเสาชิงช้า | Phra Nakhon | Old Town - Dusit - Rama 5 | `None` | `None` |
| [x] | `411` | Phra Athit Road (Camera 1) | Phra Athit Road *(coords updated)* | แนวถนนพระอาทิตย์ 2 | Phra Nakhon | Old Town - Dusit - Rama 5 | `PAIR_OV_PHRAATHIT` | `None` |
| [x] | `412` | Phra Athit Road (Camera 2) | Phra Athit Road *(coords updated)* | แนวถนนพระอาทิตย์ 2 | Phra Nakhon | Old Town - Dusit - Rama 5 | `PAIR_OV_PHRAATHIT` | `None` |
| [x] | `413` | Tanao Road | Tanao Road *(1 blocked_by_pickup exclusion)* *(coords updated)* | แนวถนนตะนาว 1 | Phra Nakhon | Old Town - Dusit - Rama 5 | `None` | `None` |
| [x] | `414` | Under Phra Phuttha Yodfa Bridge (Memorial Bridge) | Towards Phra Nakhon area and Sanam Chai *(coords updated)* | บริเวณใต้สะพานพุทธ | Phra Nakhon | Old Town - Dusit - Rama 5 | `None` | `Inbound` |
| [x] | `556` | Vajira Intersection | From Wat Prasat Bunyawat | แยกวชิระ | Dusit | Old Town - Dusit - Rama 5 | `None` | `Inbound` |
| [x] | `569` | Jor Por Ror Intersection | Jor Por Ror Intersection | แยก จ.ป.ร. | Phra Nakhon | Old Town - Dusit - Rama 5 | `None` | `None` |
| [x] | `576` | Bang Lamphu Intersection | Towards Khao San Road / Sanam Luang | แยกบางลำพู | Phra Nakhon | Old Town - Dusit - Rama 5 | `None` | `Inbound` |
| [x] | `630` | Kesakomon Intersection (Rama 5 Road) | Between Kesakomon and Ratchawat Intersections (both directions visible) *(25 corrupt/stretched/blurry exclusions)* | แยกเกษะโกมล (ด้านถนนพระราม 5) | Dusit | Old Town - Dusit - Rama 5 | `None` | `None` |
| [x] | `913` | S.A.B. Intersection | S.A.B. Intersection (Charoen Krung - Worachak Road) | แยกเอส.เอ.บี. | Pom Prap Sattru Phai | Old Town - Dusit - Rama 5 | `None` | `None` |
| [x] | `1039` | Near Narit Damrat Bridge (Khlong Mahanak) | At Narit Damrat Bridge *(5 overexposed_glare exclusions)* | ใกล้สะพานนริศดำรัส (คลองมหานาค) | Pom Prap Sattru Phai | Old Town - Dusit - Rama 5 | `None` | `None` |
| [x] | `1060` | In front of Sai Panya School on Krung Kasem Road | From Rama 1 Road | หน้าโรงเรียนสายปัญญา ถนนกรุงเกษม | Pom Prap Sattru Phai | Old Town - Dusit - Rama 5 | `None` | `Inbound` |
| [x] | `1362` | Samsen Road | Samsen Road in front of the entrance to Wat Rajadhivas Vihara *(coords updated)* | ถนนสามเสน | Dusit | Old Town - Dusit - Rama 5 | `None` | `None` |
| [x] | `1589` | Maen Si Intersection | Maen Si Intersection | แยกแม้นศรี | Pom Prap Sattru Phai | Old Town - Dusit - Rama 5 | `None` | `None` |

