# 100-Camera Metadata Peer Audit Checklist (`CAMERA_AUDIT_CHECKLIST.md`)

> **Instructions:** The 100 CCTV cameras in [`Dataset_Clean_V1/cctv_info_cleaned.csv`](../Dataset_Clean_V1/cctv_info_cleaned.csv) are partitioned into **6 corridor-aligned batches (16-17 cameras per team member)**. Camera pairs sharing a `pair_id` are grouped within the same member's batch for side-by-side verification.  
> Check off `[x]` each camera after confirming its `location_en`, `location_th`, `district`, `corridor`, `pair_id`, and `direction`.

---

## Batch 1 -- ปลื้ม (@siravidthongsook): Ratchadaphisek Corridor (17 Cameras)
*Focus: Bidirectional footbridge pairs `126/127` (Soi Ratchada 30), `224/225` (Criminal Court), and Sutthisan / Lat Phrao / Thiam Ruam Mit intersections.*

| Verified | `cam_id` | `location_en` | `location_detail_en` | `location_th` | `district` | `corridor` | `pair_id` | `direction` |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| [ ] | `112` | Thiam Ruam Mit Intersection (Thiam Ruam Mit Road) | Towards Huai Khwang / Ratchadaphisek Road | แยกเทียมร่วมมิตร (ถนนเทียมร่วมมิตร) | Huai Khwang | Ratchadaphisek | `PAIR_JX_THIAMRUAMMIT` | `Inbound` |
| [ ] | `1408` | Thiam Ruam Mit Intersection (Cyber World Tower) | From Huai Khwang Intersection towards Thiam Ruam Mit Intersection | แยกเทียมร่วมมิตร (หน้าอาคารไซเบอร์เวิลด์) | Huai Khwang | Ratchadaphisek | `PAIR_JX_THIAMRUAMMIT` | `Inbound` |
| [ ] | `118` | Ratchada-Sutthisan Intersection (Sutthisan Winitchai Road) | From Sutthisan-Vibhavadi Rangsit Intersection | แยกรัชดา-สุทธิสาร (ด้านถนนสุทธิสารวินิจฉัย) | Huai Khwang | Ratchadaphisek | `PAIR_ARM_SUTTHISAN` | `Outbound` |
| [ ] | `119` | Ratchada-Sutthisan Intersection (Ratchadaphisek Road) | From Huai Khwang Intersection | แยกรัชดา-สุทธิสาร (ด้านถนนรัชดาภิเษก) | Huai Khwang | Ratchadaphisek | `PAIR_ARM_SUTTHISAN` | `Outbound` |
| [ ] | `120` | Ratchada-Sutthisan Intersection (Sutthisan Winitchai Road) | From Soi Lat Phrao 64 | แยกรัชดา-สุทธิสาร (ด้านถนนสุทธิสารวินิจฉัย) | Huai Khwang | Ratchadaphisek | `PAIR_ARM_SUTTHISAN` | `Inbound` |
| [ ] | `123` | Ratchada-Lat Phrao Intersection (Ratchadaphisek Road) | From Ratchada-Sutthisan Intersection | แยกรัชดา-ลาดพร้าว (ด้านถนนรัชดาภิเษก) | Chatuchak | Ratchadaphisek | `PAIR_ARM_RATCHADALATPHRAO` | `Outbound` |
| [ ] | `124` | Ratchada-Lat Phrao Intersection (Lat Phrao Road) | From Chok Chai 4 Intersection | แยกรัชดา-ลาดพร้าว (ด้านถนนลาดพร้าว) | Chatuchak | Ratchadaphisek | `PAIR_ARM_RATCHADALATPHRAO` | `Inbound` |
| [ ] | `125` | Ratchada-Lat Phrao Intersection (Ratchadaphisek Road) | From Ratchayothin Intersection towards Ratchada-Sutthisan | แยกรัชดา-ลาดพร้าว (ด้านถนนรัชดาภิเษก) | Chatuchak | Ratchadaphisek | `PAIR_ARM_RATCHADALATPHRAO` | `Inbound` |
| [ ] | `126` | Footbridge near Soi Ratchadaphisek 30 on Ratchadaphisek Road | From Ratchayothin Intersection towards Ratchada-Lat Phrao Intersection | สะพานลอยซอยรัชดาภิเษก 30 ถนนรัชดาภิเษก | Chatuchak | Ratchadaphisek | `FB_03_Ratchada30` | `Inbound` |
| [ ] | `127` | Footbridge near Soi Ratchadaphisek 30 on Ratchadaphisek Road | From Ratchada-Lat Phrao Intersection towards Ratchayothin Intersection | สะพานลอยซอยรัชดาภิเษก 30 ถนนรัชดาภิเษก | Chatuchak | Ratchadaphisek | `FB_03_Ratchada30` | `Outbound` |
| [ ] | `135` | Footbridge in front of Toyota Sure on Ratchadaphisek Road | From Ratchayothin Intersection towards Ratchada-Lat Phrao Intersection | สะพานลอยหน้าโตโยต้าชัวร์ ถนนรัชดาภิเษก | Chatuchak | Ratchadaphisek | `None` | `Inbound` |
| [ ] | `211` | Footbridge near Soi Ratchadaphisek 3 on Ratchadaphisek Road | From Rama 9 Intersection towards Thiam Ruam Mit Intersection | สะพานลอยใกล้ซอยรัชดาภิเษก 3 ถนนรัชดาภิเษก | Din Daeng | Ratchadaphisek | `None` | `Outbound` |
| [ ] | `212` | Footbridge near Big C Ratchadaphisek on Ratchadaphisek Road | From Thiam Ruam Mit Intersection towards Rama 9 Intersection | สะพานลอยใกล้บิ๊กซีรัชดา ถนนรัชดาภิเษก | Din Daeng | Ratchadaphisek | `None` | `Inbound` |
| [ ] | `215` | Footbridge near Soi Ratchadaphisek 7 on Ratchadaphisek Road | From Thiam Ruam Mit Intersection towards Huai Khwang Intersection | สะพานลอยใกล้ซอยรัชดาภิเษก 7 ถนนรัชดาภิเษก | Din Daeng | Ratchadaphisek | `None` | `Outbound` |
| [ ] | `219` | Footbridge near Soi Ratchadaphisek 14 on Ratchadaphisek Road | From Ratchada-Sutthisan Intersection towards Huai Khwang Intersection | สะพานลอยใกล้ซอยรัชดาภิเษก 14 ถนนรัชดาภิเษก | Huai Khwang | Ratchadaphisek | `None` | `Inbound` |
| [ ] | `224` | Footbridge near The Criminal Court on Ratchadaphisek Road | From Ratchayothin Intersection towards Ratchada-Lat Phrao Intersection | สะพานลอยใกล้ศาลอาญา ถนนรัชดาภิเษก | Chatuchak | Ratchadaphisek | `FB_04_CriminalCourt` | `Inbound` |
| [ ] | `225` | Footbridge near The Criminal Court on Ratchadaphisek Road | From Ratchada-Lat Phrao Intersection towards Ratchayothin Intersection | สะพานลอยใกล้ศาลอาญา ถนนรัชดาภิเษก | Chatuchak | Ratchadaphisek | `FB_04_CriminalCourt` | `Outbound` |

---

## Batch 2 -- กร (@kkooAAA): Phahon Yothin - Lat Phrao & East Bangkok Corridors (16 Cameras)
*Focus: Bidirectional footbridge pairs `136/137` (Big C Lat Phrao), `176/177` (Chatuchak Park), `178/179` (Phyathai 2 Hospital), and Ramkhamhaeng / On Nut cameras.*

| Verified | `cam_id` | `location_en` | `location_detail_en` | `location_th` | `district` | `corridor` | `pair_id` | `direction` |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| [ ] | `1815` | Rama 9 Intersection | From Phang Mueang Intersection | แยกพระราม 9 | Huai Khwang | Ratchadaphisek | `None` | `Inbound` |
| [ ] | `136` | Footbridge near Big C Extra (Soi Lat Phrao 7) on Lat Phrao Road | From Lat Phrao Intersection towards Ratchada-Lat Phrao Intersection | สะพานลอยใกล้บิ๊กซีเอ็กซ์ตร้า ลาดพร้าว | Chatuchak | Phahon Yothin - Lat Phrao | `FB_01_LatPhrao_BigC` | `Outbound` |
| [ ] | `137` | Footbridge near Big C Extra (Soi Lat Phrao 7) on Lat Phrao Road | From Ratchada-Lat Phrao Intersection towards Lat Phrao Intersection | สะพานลอยใกล้บิ๊กซีเอ็กซ์ตร้า ลาดพร้าว | Chatuchak | Phahon Yothin - Lat Phrao | `FB_01_LatPhrao_BigC` | `Inbound` |
| [ ] | `139` | Footbridge in front of Horwang School on Phahon Yothin Road | From Ratchayothin Intersection towards Lat Phrao Intersection | สะพานลอยหน้าโรงเรียนหอวัง ถนนพหลโยธิน | Chatuchak | Phahon Yothin - Lat Phrao | `None` | `Inbound` |
| [ ] | `141` | Footbridge in front of PTT HQ near Soi Vibhavadi Rangsit 11 | From Lat Phrao Intersection towards Ratchawipha Interchange | สะพานลอยหน้าบริษัท ปตท. จำกัด (มหาชน) ถนนวิภาวดีรังสิต | Chatuchak | Phahon Yothin - Lat Phrao | `None` | `Outbound` |
| [ ] | `170` | Footbridge near Nawutti Somdet Ya Hospital on Phahon Yothin Road | From Victory Monument towards Saphan Khwai Intersection | สะพานลอยใกล้โรงพยาบาลนวุติสมเด็จย่า ถนนพหลโยธิน | Phaya Thai | Phahon Yothin - Lat Phrao | `None` | `Outbound` |
| [ ] | `176` | Footbridge in front of Chatuchak Park on Phahon Yothin Road | From Lat Phrao Intersection towards Kamphaeng Phet Intersection | สะพานลอยหน้าสวนจตุจักร ถนนพหลโยธิน | Chatuchak | Phahon Yothin - Lat Phrao | `FB_05_ChatuchakPark` | `Inbound` |
| [ ] | `177` | Footbridge in front of Chatuchak Park on Phahon Yothin Road | From Kamphaeng Phet Intersection towards Lat Phrao Intersection | สะพานลอยหน้าสวนจตุจักร ถนนพหลโยธิน | Chatuchak | Phahon Yothin - Lat Phrao | `FB_05_ChatuchakPark` | `Outbound` |
| [ ] | `178` | Footbridge in front of Phyathai 2 Hospital on Phahon Yothin Road | From Saphan Khwai Intersection towards Victory Monument | สะพานลอยหน้าโรงพยาบาลพญาไท 2 ถนนพหลโยธิน | Phaya Thai | Phahon Yothin - Lat Phrao | `FB_02_Phyathai2` | `Inbound` |
| [ ] | `179` | Footbridge in front of Phyathai 2 Hospital on Phahon Yothin Road | From Victory Monument towards Saphan Khwai Intersection | สะพานลอยหน้าโรงพยาบาลพญาไท 2 ถนนพหลโยธิน | Phaya Thai | Phahon Yothin - Lat Phrao | `FB_02_Phyathai2` | `Outbound` |
| [ ] | `1070` | Footbridge near Soi Phahon Yothin 18/2 on Phahon Yothin Road | From Kamphaeng Phet Intersection towards Lat Phrao Intersection | สะพานลอยใกล้ซอยพหลโยธิน 18/2 ถนนพหลโยธิน | Chatuchak | Phahon Yothin - Lat Phrao | `None` | `Outbound` |
| [ ] | `1071` | Kamphaeng Phet Intersection (Phahon Yothin Road) | From Lat Phrao Intersection (near Soi Phahon Yothin 18) | แยกกำแพงเพชร (ด้านถนนพหลโยธิน) | Chatuchak | Phahon Yothin - Lat Phrao | `None` | `Inbound` |
| [ ] | `1112` | Sutthisan Intersection (Vibhavadi Rangsit Road) | From Ratchada-Sutthisan Intersection | แยกสุทธิสาร (ถนนวิภาวดีรังสิต) | Din Daeng | Phahon Yothin - Lat Phrao | `None` | `Inbound` |
| [ ] | `938` | Ramkhamhaeng - Rama 9 Intersection | Ramkhamhaeng - Rama 9 Intersection *(98 frozen frames)* | แยกรามคำแหง-พระราม 9 | Suan Luang | East Bangkok (Ramkhamhaeng - On Nut) | `None` | `None` |
| [ ] | `939` | Mahadthai Intersection | Mahadthai Intersection (Ramkhamhaeng Road) *(95 frozen frames)* | แยกมหาดไทย | Bang Kapi | East Bangkok (Ramkhamhaeng - On Nut) | `None` | `None` |
| [ ] | `1804` | Entrance to Soi On Nut 33 on On Nut Road | Towards Suan Luang Intersection *(16 rainbow frames)* | ปากซอยอ่อนนุช 33 ถนนอ่อนนุช | Suan Luang | East Bangkok (Ramkhamhaeng - On Nut) | `None` | `Outbound` |

---

## Batch 3 -- เฟิร์ม (@nontaphatfirm): Sathon - Naradhiwas - Rama 3 & Pathum Wan Corridors (17 Cameras)
*Focus: Silom / Sathon / Naradhiwas CBD cameras and Sam Yan / Henri Dunant / Lang Suan intersections.*

| Verified | `cam_id` | `location_en` | `location_detail_en` | `location_th` | `district` | `corridor` | `pair_id` | `direction` |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| [ ] | `75` | Ratchada-Naradhiwas Intersection (Naradhiwas Road) | From Sathu Pradit Expressway Intersection | แยกรัชดา-นราธิวาส (ด้านถนนนราธิวาสฯ) | Yan Nawa | Sathon - Naradhiwas - Rama 3 | `None` | `Inbound` |
| [ ] | `88` | Chan-Sathu Pradit Intersection | Towards Chan-Naradhiwas Intersection | แยกจันทน์-สาธุประดิษฐ์ | Sathon | Sathon - Naradhiwas - Rama 3 | `None` | `Inbound` |
| [ ] | `186` | Directional sign gantry to Rama 3 Bridge on Ratchadaphisek Road | From Ratchada-Naradhiwas Intersection towards Sathu Pradit Intersection | โครงสร้างป้ายบอกทางขึ้นสะพานพระราม 3 ถนนรัชดาภิเษก | Yan Nawa | Sathon - Naradhiwas - Rama 3 | `None` | `Outbound` |
| [ ] | `188` | Footbridge near Rama 3 Soi 68 on Rama 3 Road | From Na Ranong Intersection towards Nang Linchi Intersection | สะพานลอยใกล้ซอยพระรามที่ 3 ซอย 68 ถนนพระรามที่ 3 | Yan Nawa | Sathon - Naradhiwas - Rama 3 | `None` | `Outbound` |
| [ ] | `194` | Footbridge near Soi Convent on South Sathon Road | From Sathon-Naradhiwas Intersection towards Witthayu Intersection | สะพานลอยใกล้ปากซอยคอนแวนต์ ถนนสาทรใต้ | Bang Rak | Sathon - Naradhiwas - Rama 3 | `None` | `Inbound` |
| [ ] | `196` | Footbridge in front of Makro on Naradhiwas Ratchanakharin Road | From Sathon-Naradhiwas Intersection towards Chan-Naradhiwas Intersection | สะพานลอยหน้าแม็คโคร ถนนนราธิวาสราชนครินทร์ | Sathon | Sathon - Naradhiwas - Rama 3 | `None` | `Outbound` |
| [ ] | `206` | Footbridge near Soi Naradhiwas 20 on Naradhiwas Ratchanakharin Road | From Ratchada-Naradhiwas Intersection towards Chan-Naradhiwas Intersection | สะพานลอยใกล้ซอยนราธิวาสราชนครินทร์ 20 | Yan Nawa | Sathon - Naradhiwas - Rama 3 | `None` | `Inbound` |
| [ ] | `599` | Surasak Intersection | Towards Sathon-Surasak Intersection | แยกสุรศักดิ์ | Bang Rak | Sathon - Naradhiwas - Rama 3 | `None` | `Inbound` |
| [ ] | `603` | Silom-Naradhiwas Intersection | From Surasak Intersection | แยกสีลม-นราธิวาส | Bang Rak | Sathon - Naradhiwas - Rama 3 | `PAIR_JX_SILOM_NARADHIWAS` | `Inbound` |
| [ ] | `604` | Silom-Naradhiwas Intersection | Towards Sala Daeng / Sathon-Naradhiwas Intersection | แยกสีลม-นราธิวาส | Bang Rak | Sathon - Naradhiwas - Rama 3 | `PAIR_JX_SILOM_NARADHIWAS` | `Inbound` |
| [ ] | `11` | Near Soi Ratchawithi 6 on Ratchawithi Road | From Victory Monument | ใกล้ซอยราชวิถี 6 ถนนราชวิถี | Ratchathewi | Pathum Wan - Phetchaburi - Victory Monument | `None` | `Outbound` |
| [ ] | `82` | Footbridge near Soi Ratchaprarop 3 on Ratchaprarop Road | From Mo Leng Intersection towards Pratu Nam Intersection | สะพานลอยใกล้ซอยราชปรารภ 3 ถนนราชปรารภ | Ratchathewi | Pathum Wan - Phetchaburi - Victory Monument | `None` | `Inbound` |
| [ ] | `239` | Footbridge near Triam Udom Suksa School on Phayathai Road | From Pathum Wan Intersection towards Sam Yan Intersection | สะพานลอยใกล้โรงเรียนเตรียมอุดมศึกษา ถนนพญาไท | Pathum Wan | Pathum Wan - Phetchaburi - Victory Monument | `None` | `Inbound` |
| [ ] | `432` | Sam Yan Intersection | Sam Yan Intersection (Phayathai-Rama 4 Road) *(17 rainbow frames)* | ทางแยกสามย่าน | Pathum Wan | Pathum Wan - Phetchaburi - Victory Monument | `None` | `None` |
| [ ] | `542` | Lang Suan - Sarasin Intersection | Lang Suan - Sarasin Intersection near Lumphini Park | ทางแยกหลังสวน (สารสิน-หลังสวน) | Pathum Wan | Pathum Wan - Phetchaburi - Victory Monument | `None` | `None` |
| [ ] | `619` | Henri Dunant Intersection | Henri Dunant Intersection *(Repaired row-shift)* | ทางแยกอังรีดูนังต์ | Pathum Wan | Pathum Wan - Phetchaburi - Victory Monument | `None` | `None` |
| [ ] | `277` | Footbridge near Soi Rang Nam on Phayathai Road (Victory Monument) | From Victory Monument towards Phayathai Intersection | ทางแยกอนุสาวรีย์ชัยสมรภูมิ | Ratchathewi | Pathum Wan - Phetchaburi - Victory Monument | `None` | `Inbound` |

---

## Batch 4 -- สอง (@theme222): Phetchaburi & Thon Buri - Charoen Nakhon - Borommaratchachonnani Corridors (17 Cameras)
*Focus: Bidirectional footbridge pair `1078/1132` (Wat Suwan on Charoen Nakhon), Bukkhalo pair `26/1195`, and Phutthamonthon Sai 2 `529`.*

| Verified | `cam_id` | `location_en` | `location_detail_en` | `location_th` | `district` | `corridor` | `pair_id` | `direction` |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| [ ] | `250` | Footbridge near Soi Phetchaburi 38 on Phetchaburi Road | From Phrom Phong Intersection towards Asok-Phetchaburi Intersection | สะพานลอยใกล้ซอยเพชรบุรี 38 ถนนเพชรบุรี | Ratchathewi | Pathum Wan - Phetchaburi - Victory Monument | `None` | `Inbound` |
| [ ] | `251` | Footbridge near Wat Dishongsaram on Phetchaburi Road | From Phetchaburi Expressway Intersection towards Mit Samphan Intersection | สะพานลอยใกล้วัดดิสหงษาราม ถนนเพชรบุรี | Ratchathewi | Pathum Wan - Phetchaburi - Victory Monument | `None` | `Inbound` |
| [ ] | `256` | Footbridge near Soi Phetchaburi 27 on Phetchaburi Road | From Pratu Nam Intersection towards Phetchaburi Expressway Intersection | สะพานลอยใกล้ซอยเพชรบุรี 27 ถนนเพชรบุรี | Ratchathewi | Pathum Wan - Phetchaburi - Victory Monument | `None` | `Outbound` |
| [ ] | `500` | Mit Samphan Intersection | Towards Ratchaprasong Intersection | ทางแยกมิตรสัมพันธ์ | Ratchathewi | Pathum Wan - Phetchaburi - Victory Monument | `None` | `Inbound` |
| [ ] | `26` | Bukkhalo Intersection (Charoen Nakhon Road) | From Charoen Nakhon / Rat Burana Road | แยกบุคคโล (ด้านถนนเจริญนคร) | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `PAIR_JX_BUKKHALO` | `Inbound` |
| [ ] | `1195` | Bukkhalo Intersection (Mahai Sawan Road Inbound) | From Charoen Nakhon Road | แยกบุคคโล (ถนนมไหสวรรย์ ขาเข้า) | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `PAIR_JX_BUKKHALO` | `Inbound` |
| [ ] | `32` | Bang Yi Ruea Intersection (Thoet Thai Road) | From Talat Phlu Intersection | แยกบางยี่เรือ (ด้านถนนเทอดไท) | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `Inbound` |
| [ ] | `36` | Ratchada-Ratchaphruek Intersection (Ratchaphruek Road) | From Taksin / Mahai Sawan Intersection | แยกรัชดา-ราชพฤกษ์ (ด้านถนนราชพฤกษ์) | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `Outbound` |
| [ ] | `1103` | Ratchada-Ratchaphruek Intersection (Ratchadaphisek Road) | From Tha Phra Intersection | แยกรัชดา-ราชพฤกษ์ (ด้านถนนรัชดาภิเษก) | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `Inbound` |
| [ ] | `1076` | Footbridge near Soi Thoet Thai 21 on Ratchaphruek Road | From Taksin Intersection towards Ratchada-Ratchaphruek Intersection | สะพานลอยใกล้ซอยเทอดไท 21 ถนนราชพฤกษ์ | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `Outbound` |
| [ ] | `158` | Footbridge near Soi Charoen Nakhon 46 on Charoen Nakhon Road | From Charoen Nakhon Tai Intersection towards Bukkhalo Intersection | สะพานลอยใกล้ซอยเจริญนคร 46 ถนนเจริญนคร | Khlong San | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `Inbound` |
| [ ] | `1078` | Footbridge in front of Wat Suwan on Charoen Nakhon Road | From Khlong San Intersection towards Charoen Nakhon Tai Intersection | สะพานลอยหน้าวัดสุวรรณ ถนนเจริญนคร | Khlong San | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `FB_06_WatSuwan` | `Outbound` |
| [ ] | `1132` | Footbridge in front of Wat Suwan on Charoen Nakhon Road | From Charoen Nakhon Tai Intersection towards Khlong San Intersection | สะพานลอยหน้าวัดสุวรรณ ถนนเจริญนคร | Khlong San | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `FB_06_WatSuwan` | `Inbound` |
| [ ] | `529` | Phutthamonthon Sai 2 - Borommaratchachonnani Interchange (Inbound) | Phutthamonthon Sai 2 / Borommaratchachonnani Inbound | จุดตัดถนนพุทธมณฑลสาย 2 (ฝั่งขาเข้า) | Thawi Watthana | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `Inbound` |
| [ ] | `572` | Borommaratchachonnani Elevated Highway (Taling Chan Ramp) | Taling Chan ascending/descending ramp | ทางคู่ขนานลอยฟ้าบรมราชชนนี (ช่วงทางขึ้นตลิ่งชัน) | Taling Chan | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `None` |
| [ ] | `1188` | Borommaratchachonnani - Kanchanaphisek Interchange (Phutthamonthon Sai 2 Side) | Borommaratchachonnani Road near Phutthamonthon Sai 2 | ต่างระดับฉิมพลี-พุทธมณฑลสาย 2 (ถนนบรมราชชนนี) | Taling Chan | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `None` |
| [ ] | `595` | Ban Khaek Intersection | Itsaraphap Road, from Pho Sam Ton Intersection | แยกบ้านแขก | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `Inbound` |

---

## Batch 5 -- นิว (@Pranithi-New): Dusit - Rama 5 - Samsen Corridor (17 Cameras)
*Focus: Bank of Thailand pair `70/1361`, Chitralada Palace pair `233/1063`, Saphan Daeng `18/1028`, Thewet `370/371`, and Panichayakarn `546/1368`.*

| Verified | `cam_id` | `location_en` | `location_detail_en` | `location_th` | `district` | `corridor` | `pair_id` | `direction` |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| [ ] | `915` | Wongwian Yai Roundabout | Wongwian Yai Roundabout | วงเวียนใหญ่ | Thon Buri | Thon Buri - Charoen Nakhon - Borommaratchachonnani | `None` | `None` |
| [ ] | `18` | Saphan Daeng Intersection (Thahan Road) | Towards Kiakkai Intersection | แยกสะพานแดง (ด้านถนนทหาร) | Dusit | Old Town - Dusit - Rama 5 | `PAIR_OV_SAPHANDAENG` | `Outbound` |
| [ ] | `1028` | Saphan Daeng Intersection | Saphan Daeng Intersection | แยกสะพานแดง | Dusit | Old Town - Dusit - Rama 5 | `PAIR_OV_SAPHANDAENG` | `None` |
| [ ] | `70` | In front of Bank of Thailand on Sam Sen Road | From Thewet Intersection towards Bang Khun Phrom Intersection | หน้าธนาคารแห่งประเทศไทย ถนนสามเสน | Phra Nakhon | Old Town - Dusit - Rama 5 | `PAIR_2W_BOT_SAMSEN` | `Inbound` |
| [ ] | `1361` | In front of Bank of Thailand on Sam Sen Road | Right side, from Bang Khun Phrom Intersection | หน้าธนาคารแห่งประเทศไทย ถนนสามเสน | Phra Nakhon | Old Town - Dusit - Rama 5 | `PAIR_2W_BOT_SAMSEN` | `Outbound` |
| [ ] | `150` | Footbridge near Samsenwittayalai School on Rama 6 Road | From Ari Samphan Intersection towards Pradiphat Intersection *(124 frozen frames)* | สะพานลอยใกล้โรงเรียนสามเสนวิทยาลัย ถนนพระรามที่ 6 | Phaya Thai | Old Town - Dusit - Rama 5 | `None` | `Outbound` |
| [ ] | `169` | Footbridge in front of Wat Sao Hin near Soi Wong Sawang 3 on Wong Sawang Road | From Rama 7 Bridge towards Wong Sawang Intersection | สะพานลอยหน้าวัดเสาหิน ใกล้ซอยวงศ์สว่าง 3 ถนนวงศ์สว่าง | Bang Sue | Old Town - Dusit - Rama 5 | `None` | `Inbound` |
| [ ] | `230` | Entrance to Soi Ranong 2 on Rama 5 Road | From Saphan Daeng Intersection towards Kesakomon Intersection | ปากซอยระนอง 2 ถนนพระรามที่ 5 | Dusit | Old Town - Dusit - Rama 5 | `None` | `Inbound` |
| [ ] | `233` | Opposite Chitralada Palace on Rama 5 Road | From Ratchawithi Intersection towards Wat Benchamabophit Intersection | ตรงข้ามพระตำหนักจิตรลดารโหฐาน ถนนพระรามที่ 5 | Dusit | Old Town - Dusit - Rama 5 | `PAIR_2W_CHITRALADA` | `Inbound` |
| [ ] | `1063` | Opposite Chitralada Palace on Rama 5 Road | From Wat Benchamabophit Intersection | ตรงข้ามพระตำหนักจิตรลดารโหฐาน ถนนพระรามที่ 5 | Dusit | Old Town - Dusit - Rama 5 | `PAIR_2W_CHITRALADA` | `Outbound` |
| [ ] | `301` | U Thong Nok Intersection | Towards Kan Ruean Intersection | แยกอู่ทองนอก | Dusit | Old Town - Dusit - Rama 5 | `None` | `Outbound` |
| [ ] | `332` | Ratchawat Intersection | Towards Phichai Intersection | แยกราชวัตร | Dusit | Old Town - Dusit - Rama 5 | `None` | `Inbound` |
| [ ] | `363` | Khet Dusit Intersection | From Ratchawithi Intersection | แยกเขตดุสิต | Dusit | Old Town - Dusit - Rama 5 | `None` | `Inbound` |
| [ ] | `370` | Thewet Intersection | Left side towards Pracha Kasem Intersection | แยกเทเวศร์ | Phra Nakhon | Old Town - Dusit - Rama 5 | `PAIR_OV_THEWET` | `Inbound` |
| [ ] | `371` | Thewet Intersection | Left side towards Makkhawan Rangsan Intersection | แยกเทเวศร์ | Phra Nakhon | Old Town - Dusit - Rama 5 | `PAIR_OV_THEWET` | `Inbound` |
| [ ] | `546` | Panichayakarn Intersection (Phitsanulok Road) | Phitsanulok Road side | แยกพาณิชยการ (ด้านถนนพิษณุโลก) | Dusit | Old Town - Dusit - Rama 5 | `PAIR_JX_PANICHAYAKARN` | `None` |
| [ ] | `1368` | Panichayakarn Intersection (Rama 5 Road) | Rama 5 Road side | แยกพาณิชยการ (ด้านถนนพระรามที่ 5) | Dusit | Old Town - Dusit - Rama 5 | `PAIR_JX_PANICHAYAKARN` | `None` |

---

## Batch 6 -- โม่ (@moaqilo): Historic Old Town - Phra Nakhon - Pom Prap Sattru Phai Corridor (16 Cameras)
*Focus: Phra Athit pair `411/412`, Sao Chingcha `395` (`348x261` resolution), Bang Lamphu, Worachak, and Klang Hospital.*

| Verified | `cam_id` | `location_en` | `location_detail_en` | `location_th` | `district` | `corridor` | `pair_id` | `direction` |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| [ ] | `68` | In front of Bangkok Bank Worachak Branch on Worachak Road | From Maen Si Intersection towards Worachak Intersection | หน้าธนาคารกรุงเทพ สาขาวรจักร | Pom Prap Sattru Phai | Old Town - Dusit - Rama 5 | `None` | `Inbound` |
| [ ] | `228` | In front of Klang Hospital on Luang Road | From Klang Hospital Intersection towards Worachak Intersection | หน้าโรงพยาบาลกลาง ถนนหลวง | Pom Prap Sattru Phai | Old Town - Dusit - Rama 5 | `None` | `Inbound` |
| [ ] | `395` | Sao Chingcha Intersection | Sao Chingcha Intersection *(348x261 px, 72 frozen frames)* | แยกเสาชิงช้า | Phra Nakhon | Old Town - Dusit - Rama 5 | `None` | `None` |
| [ ] | `411` | Phra Athit Road (Camera 1) | Phra Athit Road | แนวถนนพระอาทิตย์ 2 | Phra Nakhon | Old Town - Dusit - Rama 5 | `PAIR_OV_PHRAATHIT` | `None` |
| [ ] | `412` | Phra Athit Road (Camera 2) | Phra Athit Road | แนวถนนพระอาทิตย์ 2 | Phra Nakhon | Old Town - Dusit - Rama 5 | `PAIR_OV_PHRAATHIT` | `None` |
| [ ] | `413` | Tanao Road | Tanao Road | แนวถนนตะนาว 1 | Phra Nakhon | Old Town - Dusit - Rama 5 | `None` | `None` |
| [ ] | `414` | Under Phra Phuttha Yodfa Bridge (Memorial Bridge) | Under Memorial Bridge | บริเวณใต้สะพานพุทธ | Phra Nakhon | Old Town - Dusit - Rama 5 | `None` | `None` |
| [ ] | `556` | Vajira Intersection | From Krung Thon Bridge | แยกวชิระ | Dusit | Old Town - Dusit - Rama 5 | `None` | `Inbound` |
| [ ] | `569` | Jor Por Ror Intersection | Jor Por Ror Intersection | แยก จ.ป.ร. | Phra Nakhon | Old Town - Dusit - Rama 5 | `None` | `None` |
| [ ] | `576` | Bang Lamphu Intersection | Bang Lamphu Intersection | แยกบางลำพู | Phra Nakhon | Old Town - Dusit - Rama 5 | `None` | `None` |
| [ ] | `630` | Kesakomon Intersection (Amnuay Songkhram Road) | Towards Saphan Daeng Intersection | แยกเกษะโกมล (ด้านถนนอำนวยสงคราม) | Dusit | Old Town - Dusit - Rama 5 | `None` | `Outbound` |
| [ ] | `913` | S.A.B. Intersection | S.A.B. Intersection (Charoen Krung - Worachak Road) | แยกเอส.เอ.บี. | Pom Prap Sattru Phai | Old Town - Dusit - Rama 5 | `None` | `None` |
| [ ] | `1039` | Near Narit Damrat Bridge (Khlong Mahanak) | Towards Lan Luang Intersection | ใกล้สะพานนริศดำรัส (คลองมหานาค) | Pom Prap Sattru Phai | Old Town - Dusit - Rama 5 | `None` | `Outbound` |
| [ ] | `1060` | In front of Sai Panya School on Krung Kasem Road | Towards Rama 1 Road | หน้าโรงเรียนสายปัญญา ถนนกรุงเกษม | Pom Prap Sattru Phai | Old Town - Dusit - Rama 5 | `None` | `Inbound` |
| [ ] | `1362` | Samsen Intersection | Left side towards Uphai Chetsaduthit Intersection | แยกสามเสน | Dusit | Old Town - Dusit - Rama 5 | `None` | `Inbound` |
| [ ] | `1589` | Maen Si Intersection | Maen Si Intersection | แยกแม้นศรี | Pom Prap Sattru Phai | Old Town - Dusit - Rama 5 | `None` | `None` |

