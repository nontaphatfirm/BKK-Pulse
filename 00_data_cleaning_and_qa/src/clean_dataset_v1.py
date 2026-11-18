"""
Data Cleaning Pipeline V1 — Bangkok CCTV Image Dataset
====================================================
Implements Stage 1 (Automated Image Quality Gate - 5 Gates) and Stage 4
(Metadata Cleansing) from Info/Project Ideas.md and Info/EDA.md, writing the
cleaned dataset, manifests, and audit report to Dataset_Clean_V1/.

Usage:
    python 00_data_cleaning_and_qa/src/clean_dataset_v1.py
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import time
from typing import Any

import cv2
import numpy as np
import pandas as pd


# Match trailing _YYYYMMDD_HHMMSS.jpg in raw filenames (Gate 5: never rely on OSD text)
FILENAME_TS_PATTERN = re.compile(r"_(\d{8})_(\d{6})\.jpg$", re.IGNORECASE)

# Gate 1: Blank White Error Frames
WHITE_MAX_BYTES = 2000
WHITE_BRIGHTNESS_EXACT = 255.0

# Gate 2: Rainbow No Signal Frames (gst-launch-0.10 test pattern)
# Cam 432 uses 8,782 bytes and Cam 1804 uses 8,783 bytes; both share exact stats
# (mean ≈ 128.07, std ≈ 112.20). We match 8,782 bytes OR the exact rainbow fingerprint.
RAINBOW_EXACT_BYTES = 8782
RAINBOW_SIZE_MIN = 8700
RAINBOW_SIZE_MAX = 8900
RAINBOW_MEAN_MIN = 127.5
RAINBOW_MEAN_MAX = 128.5
RAINBOW_STD_MIN = 111.0

# Gate 3: Codec & YUV Stream Corruptions
GRAY_PFRAME_MEAN_MIN = 127.0
GRAY_PFRAME_MEAN_MAX = 132.0
GRAY_PFRAME_STD_MAX = 16.0
GREEN_SCREEN_CHANNEL_DIFF = 40.0

# Downstream diagnostic / visual environment thresholds (non-destructive warnings)
GLARE_PIXEL_THRESHOLD = 245
PARTIAL_GRAY128_TOLERANCE = 6
PARTIAL_GRAY128_WARN_RATIO = 0.45
PARTIAL_GREEN_DIFF = 80
PARTIAL_GREEN_WARN_RATIO = 0.08

# Manual per-image exclusions added during team Peer QA (Google Drive visual sweep).
# Key: clean ASCII filename shown in Dataset_Clean_V1/cctv_images/<cam_id>/ (e.g. "169_20260827_081012.jpg")
#      or raw filename.
# Value: short reason tag (e.g. "corrupt_artifact", "blocked_lens", "pitch_black", "frozen_visual").
MANUAL_EXCLUDED_IMAGES: dict[str, str] = {
    # "169_20260827_081012.jpg": "corrupt_artifact",
    # --- Batch 2 (@kkooAAA): cam_id=1815 (18 frames) ---
    # View changed (~180 deg reverse pan) from 2026-08-31 18:10:44 to end of capture;
    # original view ends at 1815_20260831_180044.jpg.
    "1815_20260831_181044.jpg": "camera_view_changed",
    "1815_20260831_182046.jpg": "camera_view_changed",
    "1815_20260831_183044.jpg": "camera_view_changed",
    "1815_20260831_184044.jpg": "camera_view_changed",
    "1815_20260831_185044.jpg": "camera_view_changed",
    "1815_20260831_190044.jpg": "camera_view_changed",
    "1815_20260831_191044.jpg": "camera_view_changed",
    "1815_20260831_192044.jpg": "camera_view_changed",
    "1815_20260831_193044.jpg": "camera_view_changed",
    "1815_20260831_194046.jpg": "camera_view_changed",
    "1815_20260831_195044.jpg": "camera_view_changed",
    "1815_20260831_200044.jpg": "camera_view_changed",
    "1815_20260831_201046.jpg": "camera_view_changed",
    "1815_20260831_202044.jpg": "camera_view_changed",
    "1815_20260831_203044.jpg": "camera_view_changed",
    "1815_20260831_204044.jpg": "camera_view_changed",
    "1815_20260831_205044.jpg": "camera_view_changed",
    "1815_20260831_210044.jpg": "camera_view_changed",
    # --- Batch 3 (@nontaphatfirm): cam_id=206 (6 frames) ---
    "206_20260825_183106.jpg": "corrupt_artifact",  # severe gray P-frame corruption
    "206_20260827_120106.jpg": "corrupt_artifact",  # severe gray P-frame corruption
    "206_20260828_130705.jpg": "corrupt_artifact",  # severe gray P-frame corruption
    "206_20260828_171605.jpg": "corrupt_artifact",  # severe gray P-frame corruption
    "206_20260831_104606.jpg": "corrupt_artifact",  # severe gray P-frame corruption
    "206_20260831_164105.jpg": "blocked_lens",      # heavy condensation/water smear occluding road center
    # --- Batch 4 (@theme222): cam_id=32, 158, 529, 595, 1076 (22 frames) ---
    "32_20260828_100545.jpg": "scanline_smear",
    "32_20260830_124541.jpg": "scanline_smear",
    "158_20260827_183605.jpg": "corrupt_artifact",
    "158_20260827_191605.jpg": "corrupt_artifact",
    "158_20260828_185607.jpg": "corrupt_artifact",
    "158_20260829_114604.jpg": "corrupt_artifact",
    "158_20260830_075603.jpg": "corrupt_artifact",
    "158_20260830_110607.jpg": "corrupt_artifact",
    "158_20260831_161604.jpg": "corrupt_artifact",
    "158_20260831_201605.jpg": "corrupt_artifact",
    "529_20260825_081011.jpg": "corrupt_artifact",
    "529_20260825_142011.jpg": "corrupt_artifact",
    "529_20260827_123022.jpg": "corrupt_artifact",
    "529_20260827_155011.jpg": "corrupt_artifact",
    "529_20260827_161011.jpg": "corrupt_artifact",
    "529_20260827_193511.jpg": "corrupt_artifact",
    "529_20260828_145011.jpg": "corrupt_artifact",
    "529_20260828_155011.jpg": "corrupt_artifact",
    "529_20260828_200011.jpg": "corrupt_artifact",
    "595_20260826_154043.jpg": "frozen_visual",
    "1076_20260831_163105.jpg": "blocked_lens",  # rainwater
    "1076_20260831_164105.jpg": "blocked_lens",  # rainwater
    # --- Batch 5 (@Pranithi-New): cam_id=169, 332 (25 frames) ---
    "169_20260825_093619.jpg": "corrupt_artifact",
    "169_20260825_124618.jpg": "corrupt_artifact",
    "169_20260825_155620.jpg": "corrupt_artifact",
    "169_20260825_160618.jpg": "corrupt_artifact",
    "169_20260826_100622.jpg": "corrupt_artifact",
    "169_20260826_130619.jpg": "corrupt_artifact",
    "169_20260826_144618.jpg": "corrupt_artifact",
    "169_20260827_154118.jpg": "corrupt_artifact",
    "169_20260828_124622.jpg": "corrupt_artifact",
    "169_20260828_162627.jpg": "corrupt_artifact",
    "169_20260828_164617.jpg": "corrupt_artifact",
    "169_20260829_195620.jpg": "corrupt_artifact",
    "169_20260830_100117.jpg": "corrupt_artifact",
    "169_20260830_121118.jpg": "corrupt_artifact",
    "169_20260830_125119.jpg": "corrupt_artifact",
    "169_20260830_130117.jpg": "corrupt_artifact",
    "169_20260831_080119.jpg": "corrupt_artifact",
    "169_20260831_100120.jpg": "corrupt_artifact",
    "169_20260831_145119.jpg": "corrupt_artifact",
    "169_20260831_174119.jpg": "corrupt_artifact",
    "332_20260825_163054.jpg": "scanline_smear",
    "332_20260825_164054.jpg": "scanline_smear",
    "332_20260825_165052.jpg": "scanline_smear",
    "332_20260826_064052.jpg": "scanline_smear",
    "332_20260828_112105.jpg": "scanline_smear",
    # --- Batch 6 (@moaqilo): cam_id=68, 413, 630, 1039 (32 frames) ---
    "68_20260828_092625.jpg": "blocked_by_crow",
    "413_20260827_111525.jpg": "blocked_by_pickup",
    "630_20260825_072031.jpg": "corrupt_artifact",
    "630_20260825_074031.jpg": "corrupt_artifact",
    "630_20260825_085033.jpg": "corrupt_artifact",
    "630_20260825_170031.jpg": "corrupt_artifact",
    "630_20260825_174034.jpg": "corrupt_artifact",
    "630_20260825_175032.jpg": "corrupt_artifact",
    "630_20260825_201032.jpg": "corrupt_artifact",
    "630_20260825_202032.jpg": "stretched_frame",
    "630_20260826_060531.jpg": "stretched_frame",
    "630_20260826_061540.jpg": "stretched_frame",
    "630_20260826_085032.jpg": "corrupt_artifact",
    "630_20260826_091031.jpg": "stretched_frame",
    "630_20260826_100032.jpg": "corrupt_artifact",
    "630_20260827_092031.jpg": "corrupt_artifact",
    "630_20260827_162032.jpg": "stretched_frame",
    "630_20260827_194035.jpg": "corrupt_artifact",
    "630_20260827_202032.jpg": "stretched_frame",
    "630_20260827_203032.jpg": "corrupt_artifact",
    "630_20260828_080531.jpg": "corrupt_artifact",
    "630_20260829_083530.jpg": "stretched_frame",
    "630_20260829_201532.jpg": "stretched_frame",
    "630_20260830_115531.jpg": "corrupt_artifact",
    "630_20260830_120533.jpg": "corrupt_artifact",
    "630_20260830_150531.jpg": "blurry_frame",
    "630_20260831_170532.jpg": "stretched_frame",
    "1039_20260825_185509.jpg": "overexposed_glare",
    "1039_20260826_195009.jpg": "overexposed_glare",
    "1039_20260829_194509.jpg": "overexposed_glare",
    "1039_20260830_185009.jpg": "overexposed_glare",
    "1039_20260831_195511.jpg": "overexposed_glare",
    # --- V2.0 Final Lock (Batch 4 CHG-B4-02 resolution): cam_id=500 (78 frames; 1188 kept 607/607) ---
    # Surgical exclusion of 7 partial_green_screen + 1 vertical scanline_smear + 70 severe H.264 P-frame macroblock smears
    "500_20260825_060027.jpg": "corrupt_artifact",
    "500_20260825_065518.jpg": "corrupt_artifact",
    "500_20260825_073524.jpg": "partial_green_screen",
    "500_20260825_091518.jpg": "corrupt_artifact",
    "500_20260825_092518.jpg": "corrupt_artifact",
    "500_20260825_093518.jpg": "corrupt_artifact",
    "500_20260825_094518.jpg": "corrupt_artifact",
    "500_20260825_100518.jpg": "corrupt_artifact",
    "500_20260825_131519.jpg": "corrupt_artifact",
    "500_20260825_141523.jpg": "corrupt_artifact",
    "500_20260825_162522.jpg": "corrupt_artifact",
    "500_20260825_163519.jpg": "corrupt_artifact",
    "500_20260825_164519.jpg": "corrupt_artifact",
    "500_20260825_173520.jpg": "corrupt_artifact",
    "500_20260825_183519.jpg": "corrupt_artifact",
    "500_20260825_184519.jpg": "corrupt_artifact",
    "500_20260825_190519.jpg": "corrupt_artifact",
    "500_20260825_191519.jpg": "partial_green_screen",
    "500_20260825_200519.jpg": "corrupt_artifact",
    "500_20260825_201519.jpg": "corrupt_artifact",
    "500_20260826_060042.jpg": "corrupt_artifact",
    "500_20260826_095518.jpg": "corrupt_artifact",
    "500_20260826_102519.jpg": "corrupt_artifact",
    "500_20260826_104523.jpg": "corrupt_artifact",
    "500_20260826_113518.jpg": "corrupt_artifact",
    "500_20260826_142523.jpg": "corrupt_artifact",
    "500_20260826_165519.jpg": "corrupt_artifact",
    "500_20260826_191519.jpg": "partial_green_screen",
    "500_20260826_193519.jpg": "corrupt_artifact",
    "500_20260826_195519.jpg": "corrupt_artifact",
    "500_20260826_201519.jpg": "corrupt_artifact",
    "500_20260826_202519.jpg": "corrupt_artifact",
    "500_20260826_205519.jpg": "corrupt_artifact",
    "500_20260827_092520.jpg": "corrupt_artifact",
    "500_20260827_112518.jpg": "corrupt_artifact",
    "500_20260827_122520.jpg": "corrupt_artifact",
    "500_20260827_162519.jpg": "corrupt_artifact",
    "500_20260827_183519.jpg": "corrupt_artifact",
    "500_20260827_194519.jpg": "corrupt_artifact",
    "500_20260827_195521.jpg": "corrupt_artifact",
    "500_20260827_203519.jpg": "corrupt_artifact",
    "500_20260827_205521.jpg": "corrupt_artifact",
    "500_20260828_090521.jpg": "corrupt_artifact",
    "500_20260828_092520.jpg": "corrupt_artifact",
    "500_20260828_111524.jpg": "partial_green_screen",
    "500_20260828_163519.jpg": "corrupt_artifact",
    "500_20260828_174519.jpg": "corrupt_artifact",
    "500_20260828_190519.jpg": "scanline_smear",
    "500_20260828_192519.jpg": "corrupt_artifact",
    "500_20260829_130521.jpg": "partial_green_screen",
    "500_20260829_131518.jpg": "corrupt_artifact",
    "500_20260829_140518.jpg": "corrupt_artifact",
    "500_20260829_142519.jpg": "corrupt_artifact",
    "500_20260829_151521.jpg": "corrupt_artifact",
    "500_20260829_152518.jpg": "corrupt_artifact",
    "500_20260829_180519.jpg": "corrupt_artifact",
    "500_20260829_182519.jpg": "corrupt_artifact",
    "500_20260829_193519.jpg": "corrupt_artifact",
    "500_20260829_195521.jpg": "corrupt_artifact",
    "500_20260829_200519.jpg": "corrupt_artifact",
    "500_20260829_205521.jpg": "corrupt_artifact",
    "500_20260830_154022.jpg": "corrupt_artifact",
    "500_20260830_163022.jpg": "corrupt_artifact",
    "500_20260830_165020.jpg": "corrupt_artifact",
    "500_20260830_174523.jpg": "corrupt_artifact",
    "500_20260831_092518.jpg": "corrupt_artifact",
    "500_20260831_103518.jpg": "corrupt_artifact",
    "500_20260831_112518.jpg": "corrupt_artifact",
    "500_20260831_113519.jpg": "corrupt_artifact",
    "500_20260831_180519.jpg": "corrupt_artifact",
    "500_20260831_182519.jpg": "corrupt_artifact",
    "500_20260831_190519.jpg": "corrupt_artifact",
    "500_20260831_191519.jpg": "corrupt_artifact",
    "500_20260831_192521.jpg": "corrupt_artifact",
    "500_20260831_195521.jpg": "corrupt_artifact",
    "500_20260831_200519.jpg": "corrupt_artifact",
    "500_20260831_201519.jpg": "partial_green_screen",
    "500_20260831_203519.jpg": "partial_green_screen",
}


# Curated metadata repairs & spatial/directional enrichment for all 100 cameras
# Fixes: NULL / '0' / 'connect BMAcctv' / '17/5000' / '(See Yellow)' / swapped
# English names / typos / truncated ~28-char Thai strings, plus district, corridor,
# pair_id, pair_type, and direction (Inbound / Outbound / None).
# Optional "lat"/"lon" keys override the raw cctv_info.csv coordinates when the
# pair cameras report their partner's position (peer-QA correction).
CAMERA_CURATION: dict[int, dict[str, Any]] = {
    11: {
        "location_th": "ใกล้ซอยราชวิถี 6 ถนนราชวิถี",
        "location_detail_th": "ช่วงอนุสาวรีย์ชัยสมรภูมิ – แยกสามเหลี่ยมดินแดง (ทั้งสองทิศทาง)",
        "location_en": "Near Soi Ratchawithi 6 on Ratchawithi Road",
        "location_detail_en": "Between Victory Monument and Din Daeng Intersection (both directions)",
        "district": "Ratchathewi",
        "corridor": "Pathum Wan - Phetchaburi - Victory Monument",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    18: {
        "location_th": "แยกสะพานแดง (ด้านถนนทหาร)",
        "location_detail_th": "ช่วงสะพานแดง – แยกเกียกกาย (เห็นรถทั้งสองทิศทาง)",
        "location_en": "Saphan Daeng Intersection (Thahan Road)",
        "location_detail_en": "Saphan Daeng Bridge towards Kiakkai Intersection (both directions visible)",
        "district": "Dusit",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": "PAIR_OV_SAPHANDAENG",
        "pair_type": "overlapping_junction",
        "direction": "None",
    },
    26: {
        "location_th": "แยกบุคคโล (ด้านถนนเจริญนคร)",
        "location_detail_th": "รถมาจากแยกเจริญนคร / ถนนราษฎร์บูรณะ",
        "location_en": "Bukkhalo Intersection (Charoen Nakhon Road)",
        "location_detail_en": "From Charoen Nakhon / Rat Burana Road",
        "district": "Thon Buri",
        "corridor": "Thon Buri - Charoen Nakhon - Borommaratchachonnani",
        "pair_id": "PAIR_ARM_BUKKHALO",
        "pair_type": "opposite_intersection_arm",
        "direction": "Inbound",
    },
    32: {
        "location_th": "แยกบางยี่เรือ (ด้านถนนเทอดไท)",
        "location_detail_th": "แยกบางยี่เรือ ด้านถนนเทอดไท",
        "location_en": "Bang Yi Ruea Intersection (Thoet Thai Road)",
        "location_detail_en": "Bang Yi Ruea Intersection (Thoet Thai Road side)",
        "district": "Thon Buri",
        "corridor": "Thon Buri - Charoen Nakhon - Borommaratchachonnani",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    36: {
        "location_th": "แยกรัชดา-ราชพฤกษ์ (ด้านถนนรัชดาภิเษก)",
        "location_detail_th": "บริเวณแยกรัชดา-ราชพฤกษ์",
        "location_en": "Ratchada-Ratchaphruek Intersection (Ratchadaphisek Road)",
        "location_detail_en": "At Ratchada-Ratchaphruek Intersection",
        "district": "Thon Buri",
        "corridor": "Thon Buri - Charoen Nakhon - Borommaratchachonnani",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    68: {
        "location_th": "หน้าธนาคารกรุงเทพ สาขาวรจักร",
        "location_detail_th": "ช่วงแยกวรจักร - แยกแม้นศรี (เห็นรถทั้งสองทิศทาง)",
        "location_en": "In front of Bangkok Bank Worachak Branch on Worachak Road",
        "location_detail_en": "Between Worachak and Maen Si Intersections (both directions visible)",
        "district": "Pom Prap Sattru Phai",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    70: {
        "location_th": "หน้าธนาคารแห่งประเทศไทย ถนนสามเสน",
        "location_detail_th": "ช่วงแยกเทเวศร์ – แยกบางขุนพรหม (รวมเลนสวนทาง)",
        "location_en": "In front of Bank of Thailand on Sam Sen Road",
        "location_detail_en": "From Thewet Intersection towards Bang Khun Phrom Intersection (with contraflow lane)",
        "district": "Phra Nakhon",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": "PAIR_2W_BOT_SAMSEN",
        "pair_type": "two_way_no_median",
        "direction": "None",
    },
    75: {
        "location_th": "แยกรัชดา-นราธิวาส (ด้านถนนนราธิวาสฯ)",
        "location_detail_th": "รถมาจากแยกนราธิวาส-พระราม 3",
        "location_en": "Ratchada-Naradhiwas Intersection (Naradhiwas Road)",
        "location_detail_en": "From Naradhiwas-Rama 3 Intersection",
        "district": "Yan Nawa",
        "corridor": "Sathon - Naradhiwas - Rama 3",
        "pair_id": None,
        "pair_type": None,
        "direction": "Inbound",
    },
    82: {
        "location_th": "สะพานลอยใกล้ซอยราชปรารภ 3 ถนนราชปรารภ",
        "location_detail_th": "ช่วงแยกประตูน้ำ – แยกหมอเหล็ง (ทั้งสองทิศทาง: 4 เลนไปหมอเหล็ง / 1 เลนไปประตูน้ำ)",
        "location_en": "Footbridge near Soi Ratchaprarop 3 on Ratchaprarop Road",
        "location_detail_en": "Between Pratu Nam and Mo Leng Intersections (both directions: 4 northbound / 1 southbound contraflow lane)",
        "district": "Ratchathewi",
        "corridor": "Pathum Wan - Phetchaburi - Victory Monument",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    88: {
        "location_th": "แยกจันทน์-สาธุประดิษฐ์",
        "location_detail_th": "บริเวณแยกจันทน์-สาธุประดิษฐ์",
        "location_en": "Chan-Sathu Pradit Intersection",
        "location_detail_en": "At Chan-Sathu Pradit Intersection",
        "district": "Sathon",
        "corridor": "Sathon - Naradhiwas - Rama 3",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    112: {
        "location_th": "แยกเทียมร่วมมิตร (ถนนเทียมร่วมมิตร)",
        "location_detail_th": "รถมุ่งหน้าไปแยกห้วยขวาง / ถนนรัชดาภิเษก",
        "location_en": "Thiam Ruam Mit Intersection (Thiam Ruam Mit Road)",
        "location_detail_en": "Towards Huai Khwang / Ratchadaphisek Road",
        "district": "Huai Khwang",
        "corridor": "Ratchadaphisek",
        "pair_id": "PAIR_JX_THIAMRUAMMIT",
        "pair_type": "perpendicular_junction",
        "direction": "Inbound",
    },
    118: {
        "location_th": "แยกรัชดา-สุทธิสาร (ด้านถนนสุทธิสารวินิจฉัย)",
        "location_detail_th": "บริเวณแยกรัชดา-สุทธิสาร ด้านถนนสุทธิสารวินิจฉัย",
        "location_en": "Ratchada-Sutthisan Intersection (Sutthisan Winitchai Road)",
        "location_detail_en": "At Ratchada-Sutthisan Intersection (Sutthisan Winitchai Road side)",
        "district": "Huai Khwang",
        "corridor": "Ratchadaphisek",
        "pair_id": "PAIR_ARM_SUTTHISAN",
        "pair_type": "opposite_intersection_arm",
        "direction": "None",
    },
    119: {
        "location_th": "แยกรัชดา-สุทธิสาร (ด้านถนนสุทธิสารวินิจฉัย)",
        "location_detail_th": "บริเวณแยกรัชดา-สุทธิสาร ด้านถนนสุทธิสารวินิจฉัย",
        "location_en": "Ratchada-Sutthisan Intersection (Sutthisan Winitchai Road)",
        "location_detail_en": "At Ratchada-Sutthisan Intersection (Sutthisan Winitchai Road side)",
        "district": "Huai Khwang",
        "corridor": "Ratchadaphisek",
        "pair_id": "PAIR_ARM_SUTTHISAN",
        "pair_type": "perpendicular_junction",
        "direction": "None",
        # Batch 1 QA: raw CSV carried cam 120's position (pair swap on Ratchadaphisek Rd).
        "lat": 13.789680,
        "lon": 100.574437,
    },
    120: {
        "location_th": "แยกรัชดา-สุทธิสาร (ด้านถนนสุทธิสารวินิจฉัย)",
        "location_detail_th": "บริเวณแยกรัชดา-สุทธิสาร",
        "location_en": "Ratchada-Sutthisan Intersection (Sutthisan Winitchai Road)",
        "location_detail_en": "At Ratchada-Sutthisan Intersection",
        "district": "Huai Khwang",
        "corridor": "Ratchadaphisek",
        "pair_id": "PAIR_ARM_SUTTHISAN",
        "pair_type": "opposite_intersection_arm",
        # Batch 1 QA: side-view arm camera - traffic flows both ways in frame.
        "direction": "None",
        "lat": 13.789785,
        "lon": 100.574031,
    },
    123: {
        "location_th": "แยกรัชดา-ลาดพร้าว (ด้านถนนรัชดาภิเษก)",
        "location_detail_th": "รถมาจากแยกรัชดา-สุทธิสาร",
        "location_en": "Ratchada-Lat Phrao Intersection (Ratchadaphisek Road)",
        "location_detail_en": "From Ratchada-Sutthisan Intersection",
        "district": "Chatuchak",
        "corridor": "Ratchadaphisek",
        "pair_id": "PAIR_ARM_RATCHADALATPHRAO",
        "pair_type": "opposite_intersection_arm",
        "direction": "Outbound",
    },
    124: {
        "location_th": "แยกรัชดา-ลาดพร้าว (ด้านถนนลาดพร้าว)",
        "location_detail_th": "บริเวณแยกรัชดา-ลาดพร้าว",
        "location_en": "Ratchada-Lat Phrao Intersection (Lat Phrao Road)",
        "location_detail_en": "At Ratchada-Lat Phrao Intersection",
        "district": "Chatuchak",
        "corridor": "Ratchadaphisek",
        "pair_id": "PAIR_ARM_RATCHADALATPHRAO",
        "pair_type": "perpendicular_junction",
        "direction": "None",
    },
    125: {
        "location_th": "แยกรัชดา-ลาดพร้าว (ด้านถนนรัชดาภิเษก)",
        "location_detail_th": "รถมาจากแยกรัชโยธิน มุ่งหน้าแยกรัชดา-สุทธิสาร",
        "location_en": "Ratchada-Lat Phrao Intersection (Ratchadaphisek Road)",
        "location_detail_en": "From Ratchayothin Intersection towards Ratchada-Sutthisan",
        "district": "Chatuchak",
        "corridor": "Ratchadaphisek",
        "pair_id": "PAIR_ARM_RATCHADALATPHRAO",
        "pair_type": "opposite_intersection_arm",
        "direction": "Inbound",
    },
    126: {
        "location_th": "สะพานลอยซอยรัชดาภิเษก 30 ถนนรัชดาภิเษก",
        "location_detail_th": "รถมาจากแยกรัชโยธิน มุ่งหน้าแยกรัชดา-ลาดพร้าว",
        "location_en": "Footbridge near Soi Ratchadaphisek 30 on Ratchadaphisek Road",
        "location_detail_en": "From Ratchayothin Intersection towards Ratchada-Lat Phrao Intersection",
        "district": "Chatuchak",
        "corridor": "Ratchadaphisek",
        "pair_id": "FB_03_Ratchada30",
        "pair_type": "footbridge_bidirectional",
        "direction": "Inbound",
    },
    127: {
        "location_th": "สะพานลอยซอยรัชดาภิเษก 30 ถนนรัชดาภิเษก",
        "location_detail_th": "รถมาจากแยกรัชดา-ลาดพร้าว มุ่งหน้าแยกรัชโยธิน",
        "location_en": "Footbridge near Soi Ratchadaphisek 30 on Ratchadaphisek Road",
        "location_detail_en": "From Ratchada-Lat Phrao Intersection towards Ratchayothin Intersection",
        "district": "Chatuchak",
        "corridor": "Ratchadaphisek",
        "pair_id": "FB_03_Ratchada30",
        "pair_type": "footbridge_bidirectional",
        "direction": "Outbound",
        # Batch 1 QA: snapped to the outbound footbridge span (raw pin sat on the median).
        "lat": 13.810192,
        "lon": 100.575261,
    },
    135: {
        "location_th": "สะพานลอยหน้าโตโยต้าชัวร์ ถนนรัชดาภิเษก",
        "location_detail_th": "ช่วงแยกรัชโยธินกับแยกรัชดา - ลาดพร้าว (เห็นรถทั้งสองทิศทาง)",
        "location_en": "Footbridge in front of Toyota Sure on Ratchadaphisek Road",
        "location_detail_en": "Between Ratchayothin and Ratchada-Lat Phrao Intersections (both directions visible)",
        "district": "Chatuchak",
        "corridor": "Ratchadaphisek",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    136: {
        "location_th": "สะพานลอยใกล้บิ๊กซีเอ็กซ์ตร้า ลาดพร้าว",
        "location_detail_th": "รถมาจากแยกลาดพร้าว มุ่งหน้าแยกรัชดา-ลาดพร้าว",
        "location_en": "Footbridge near Big C Extra (Soi Lat Phrao 7) on Lat Phrao Road",
        "location_detail_en": "From Lat Phrao Intersection towards Ratchada-Lat Phrao Intersection",
        "district": "Chatuchak",
        "corridor": "Phahon Yothin - Lat Phrao",
        "pair_id": "FB_01_LatPhrao_BigC",
        "pair_type": "footbridge_bidirectional",
        "direction": "Outbound",
    },
    137: {
        "location_th": "สะพานลอยใกล้บิ๊กซีเอ็กซ์ตร้า ลาดพร้าว",
        "location_detail_th": "รถมาจากแยกรัชดา-ลาดพร้าว มุ่งหน้าแยกลาดพร้าว",
        "location_en": "Footbridge near Big C Extra (Soi Lat Phrao 7) on Lat Phrao Road",
        "location_detail_en": "From Ratchada-Lat Phrao Intersection towards Lat Phrao Intersection",
        "district": "Chatuchak",
        "corridor": "Phahon Yothin - Lat Phrao",
        "pair_id": "FB_01_LatPhrao_BigC",
        "pair_type": "footbridge_bidirectional",
        "direction": "Inbound",
    },
    139: {
        "location_th": "สะพานลอยหน้าโรงเรียนหอวัง ถนนพหลโยธิน",
        "location_detail_th": "รถมาจากแยกรัชโยธิน มุ่งหน้าห้าแยกลาดพร้าว",
        "location_en": "Footbridge in front of Horwang School on Phahon Yothin Road",
        "location_detail_en": "From Ratchayothin Intersection towards Lat Phrao Intersection",
        "district": "Chatuchak",
        "corridor": "Phahon Yothin - Lat Phrao",
        "pair_id": None,
        "pair_type": None,
        "direction": "Inbound",
    },
    141: {
        "location_th": "สะพานลอยหน้าบริษัท ปตท. จำกัด (มหาชน) ถนนวิภาวดีรังสิต",
        "location_detail_th": "รถมาจากห้าแยกลาดพร้าว ขาออกมุ่งหน้าแยกรัชวิภา",
        "location_en": "Footbridge in front of PTT HQ near Soi Vibhavadi Rangsit 11",
        "location_detail_en": "From Lat Phrao Intersection towards Ratchawipha Interchange",
        "district": "Chatuchak",
        "corridor": "Phahon Yothin - Lat Phrao",
        "pair_id": None,
        "pair_type": None,
        "direction": "Outbound",
    },
    150: {
        "location_th": "สะพานลอยใกล้โรงเรียนสามเสนวิทยาลัย ถนนพระรามที่ 6",
        "location_detail_th": "ช่วงแยกอารีย์สัมพันธ์ – แยกประดิพัทธ์ (เห็นรถทั้งสองทิศทาง)",
        "location_en": "Footbridge near Samsenwittayalai School on Rama 6 Road",
        "location_detail_en": "Between Ari Samphan and Pradiphat Intersections (both directions visible)",
        "district": "Phaya Thai",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    158: {
        "location_th": "สะพานลอยใกล้ซอยเจริญนคร 46 ถนนเจริญนคร",
        "location_detail_th": "บริเวณซอยเจริญนคร 46",
        "location_en": "Footbridge near Soi Charoen Nakhon 46 on Charoen Nakhon Road",
        "location_detail_en": "Near Soi Charoen Nakhon 46",
        "district": "Khlong San",
        "corridor": "Thon Buri - Charoen Nakhon - Borommaratchachonnani",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    169: {
        "location_th": "สะพานลอยหน้าวัดเสาหิน ใกล้ซอยวงศ์สว่าง 3 ถนนวงศ์สว่าง",
        "location_detail_th": "รถมาจากสะพานพระราม 7 มุ่งหน้าแยกวงศ์สว่าง",
        "location_en": "Footbridge in front of Wat Sao Hin near Soi Wong Sawang 3 on Wong Sawang Road",
        "location_detail_en": "From Rama 7 Bridge towards Wong Sawang Intersection",
        "district": "Bang Sue",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "Inbound",
    },
    170: {
        "location_th": "สะพานลอยใกล้โรงพยาบาลนวุติสมเด็จย่า ถนนพหลโยธิน",
        "location_detail_th": "รถมาจากอนุสาวรีย์ชัยสมรภูมิ มุ่งหน้าแยกสะพานควาย",
        "location_en": "Footbridge near Nawutti Somdet Ya Hospital on Phahon Yothin Road",
        "location_detail_en": "From Victory Monument towards Saphan Khwai Intersection",
        "district": "Phaya Thai",
        "corridor": "Phahon Yothin - Lat Phrao",
        "pair_id": None,
        "pair_type": None,
        "direction": "Outbound",
    },
    176: {
        "location_th": "สะพานลอยหน้าสวนจตุจักร ถนนพหลโยธิน",
        "location_detail_th": "รถมาจากห้าแยกลาดพร้าว มุ่งหน้าแยกกำแพงเพชร",
        "location_en": "Footbridge in front of Chatuchak Park on Phahon Yothin Road",
        "location_detail_en": "From Lat Phrao Intersection towards Kamphaeng Phet Intersection",
        "district": "Chatuchak",
        "corridor": "Phahon Yothin - Lat Phrao",
        "pair_id": "FB_05_ChatuchakPark",
        "pair_type": "footbridge_bidirectional",
        "direction": "Inbound",
    },
    177: {
        "location_th": "สะพานลอยหน้าสวนจตุจักร ถนนพหลโยธิน",
        "location_detail_th": "รถมาจากแยกกำแพงเพชร มุ่งหน้าห้าแยกลาดพร้าว",
        "location_en": "Footbridge in front of Chatuchak Park on Phahon Yothin Road",
        "location_detail_en": "From Kamphaeng Phet Intersection towards Lat Phrao Intersection",
        "district": "Chatuchak",
        "corridor": "Phahon Yothin - Lat Phrao",
        "pair_id": "FB_05_ChatuchakPark",
        "pair_type": "footbridge_bidirectional",
        "direction": "Outbound",
    },
    # CHG-005 location reference (manual check, no schema field): approx. 180 m after
    # turning right from Phyathai 2 Hospital. Metadata values unchanged.
    178: {
        "location_th": "สะพานลอยหน้าโรงพยาบาลพญาไท 2 ถนนพหลโยธิน",
        "location_detail_th": "รถมาจากแยกสะพานควาย มุ่งหน้าอนุสาวรีย์ชัยสมรภูมิ",
        "location_en": "Footbridge in front of Phyathai 2 Hospital on Phahon Yothin Road",
        "location_detail_en": "From Saphan Khwai Intersection towards Victory Monument",
        "district": "Phaya Thai",
        "corridor": "Phahon Yothin - Lat Phrao",
        "pair_id": "FB_02_Phyathai2",
        "pair_type": "footbridge_bidirectional",
        "direction": "Inbound",
    },
    # CHG-005 location reference (manual check, no schema field): approx. 120 m after
    # turning right from Phyathai 2 Hospital. Metadata values unchanged.
    179: {
        "location_th": "สะพานลอยหน้าโรงพยาบาลพญาไท 2 ถนนพหลโยธิน",
        "location_detail_th": "รถมาจากอนุสาวรีย์ชัยสมรภูมิ มุ่งหน้าแยกสะพานควาย",
        "location_en": "Footbridge in front of Phyathai 2 Hospital on Phahon Yothin Road",
        "location_detail_en": "From Victory Monument towards Saphan Khwai Intersection",
        "district": "Phaya Thai",
        "corridor": "Phahon Yothin - Lat Phrao",
        "pair_id": "FB_02_Phyathai2",
        "pair_type": "footbridge_bidirectional",
        "direction": "Outbound",
    },
    186: {
        "location_th": "โครงสร้างป้ายบอกทางขึ้นสะพานพระราม 3 ถนนรัชดาภิเษก",
        "location_detail_th": "รถมาจากแยกรัชดา-นราธิวาส มุ่งหน้าแยกสาธุประดิษฐ์",
        "location_en": "Directional sign gantry to Rama 3 Bridge on Ratchadaphisek Road",
        "location_detail_en": "From Ratchada-Naradhiwas Intersection towards Sathu Pradit Intersection",
        "district": "Yan Nawa",
        "corridor": "Sathon - Naradhiwas - Rama 3",
        "pair_id": None,
        "pair_type": None,
        "direction": "Outbound",
    },
    188: {
        "location_th": "สะพานลอยใกล้ซอยพระรามที่ 3 ซอย 68 ถนนพระรามที่ 3",
        "location_detail_th": "รถมาจากแยก ณ ระนอง มุ่งหน้าแยกนางลิ้นจี่",
        "location_en": "Footbridge near Rama 3 Soi 68 on Rama 3 Road",
        "location_detail_en": "From Na Ranong Intersection towards Nang Linchi Intersection",
        "district": "Yan Nawa",
        "corridor": "Sathon - Naradhiwas - Rama 3",
        "pair_id": None,
        "pair_type": None,
        "direction": "Outbound",
    },
    194: {
        "location_th": "สะพานลอยใกล้ปากซอยคอนแวนต์ ถนนสาทรเหนือ",
        "location_detail_th": "รถมาจากแยกวิทยุ มุ่งหน้าแยกสาทร-นราธิวาส",
        "location_en": "Footbridge near Soi Convent on North Sathon Road",
        "location_detail_en": "From Witthayu Intersection towards Sathon-Naradhiwas Intersection",
        "district": "Bang Rak",
        "corridor": "Sathon - Naradhiwas - Rama 3",
        "pair_id": None,
        "pair_type": None,
        "direction": "Outbound",
    },
    196: {
        "location_th": "สะพานลอยหน้าแม็คโคร ถนนนราธิวาสราชนครินทร์",
        "location_detail_th": "รถมาจากแยกสาทร-นราธิวาส มุ่งหน้าแยกจันทน์-นราธิวาส",
        "location_en": "Footbridge in front of Makro on Naradhiwas Ratchanakharin Road",
        "location_detail_en": "From Sathon-Naradhiwas Intersection towards Chan-Naradhiwas Intersection",
        "district": "Sathon",
        "corridor": "Sathon - Naradhiwas - Rama 3",
        "pair_id": None,
        "pair_type": None,
        "direction": "Outbound",
    },
    206: {
        "location_th": "สะพานลอยตรงข้ามซอยนราธิวาสราชนครินทร์ 20 ถนนนราธิวาสราชนครินทร์",
        "location_detail_th": "รถมาจากแยกจันทน์-นราธิวาส มุ่งหน้าแยกรัชดา-นราธิวาส",
        "location_en": "Footbridge opposite Soi Naradhiwas 20 on Naradhiwas Ratchanakharin Road",
        "location_detail_en": "From Chan-Naradhiwas Intersection towards Ratchada-Naradhiwas Intersection",
        "district": "Yan Nawa",
        "corridor": "Sathon - Naradhiwas - Rama 3",
        "pair_id": None,
        "pair_type": None,
        "direction": "Outbound",
        "lat": 13.70555,
        "lon": 100.53865,
    },
    211: {
        "location_th": "สะพานลอยใกล้ซอยรัชดาภิเษก 3 ถนนรัชดาภิเษก",
        "location_detail_th": "รถมาจากแยกพระราม 9 มุ่งหน้าแยกเทียมร่วมมิตร",
        "location_en": "Footbridge near Soi Ratchadaphisek 3 on Ratchadaphisek Road",
        "location_detail_en": "From Rama 9 Intersection towards Thiam Ruam Mit Intersection",
        "district": "Din Daeng",
        "corridor": "Ratchadaphisek",
        "pair_id": None,
        "pair_type": None,
        "direction": "Outbound",
    },
    212: {
        "location_th": "สะพานลอยใกล้บิ๊กซีรัชดา ถนนรัชดาภิเษก",
        "location_detail_th": "รถมาจากแยกเทียมร่วมมิตร มุ่งหน้าแยกพระราม 9",
        "location_en": "Footbridge near Big C Ratchadaphisek on Ratchadaphisek Road",
        "location_detail_en": "From Thiam Ruam Mit Intersection towards Rama 9 Intersection",
        "district": "Din Daeng",
        "corridor": "Ratchadaphisek",
        "pair_id": None,
        "pair_type": None,
        "direction": "Inbound",
    },
    215: {
        "location_th": "สะพานลอยใกล้ซอยรัชดาภิเษก 7 ถนนรัชดาภิเษก",
        "location_detail_th": "รถมาจากแยกเทียมร่วมมิตร มุ่งหน้าแยกห้วยขวาง",
        "location_en": "Footbridge near Soi Ratchadaphisek 7 on Ratchadaphisek Road",
        "location_detail_en": "From Thiam Ruam Mit Intersection towards Huai Khwang Intersection",
        "district": "Din Daeng",
        "corridor": "Ratchadaphisek",
        "pair_id": None,
        "pair_type": None,
        "direction": "Outbound",
    },
    219: {
        "location_th": "สะพานลอยใกล้ซอยรัชดาภิเษก 14 ถนนรัชดาภิเษก",
        "location_detail_th": "รถมาจากแยกรัชดา-สุทธิสาร มุ่งหน้าแยกห้วยขวาง",
        "location_en": "Footbridge near Soi Ratchadaphisek 14 on Ratchadaphisek Road",
        "location_detail_en": "From Ratchada-Sutthisan Intersection towards Huai Khwang Intersection",
        "district": "Huai Khwang",
        "corridor": "Ratchadaphisek",
        "pair_id": None,
        "pair_type": None,
        "direction": "Inbound",
    },
    224: {
        "location_th": "สะพานลอยใกล้ศาลอาญา ถนนรัชดาภิเษก",
        "location_detail_th": "รถมาจากแยกรัชโยธิน มุ่งหน้าแยกรัชดา-ลาดพร้าว",
        "location_en": "Footbridge near The Criminal Court on Ratchadaphisek Road",
        "location_detail_en": "From Ratchayothin Intersection towards Ratchada-Lat Phrao Intersection",
        "district": "Chatuchak",
        "corridor": "Ratchadaphisek",
        "pair_id": "FB_04_CriminalCourt",
        "pair_type": "footbridge_bidirectional",
        "direction": "Inbound",
        # Batch 1 QA: raw CSV had the pair's outbound-side coordinates (224/225 swap).
        "lat": 13.815228,
        "lon": 100.575355,
    },
    225: {
        "location_th": "สะพานลอยใกล้ศาลอาญา ถนนรัชดาภิเษก",
        "location_detail_th": "รถมาจากแยกรัชดา-ลาดพร้าว มุ่งหน้าแยกรัชโยธิน",
        "location_en": "Footbridge near The Criminal Court on Ratchadaphisek Road",
        "location_detail_en": "From Ratchada-Lat Phrao Intersection towards Ratchayothin Intersection",
        "district": "Chatuchak",
        "corridor": "Ratchadaphisek",
        "pair_id": "FB_04_CriminalCourt",
        "pair_type": "footbridge_bidirectional",
        "direction": "Outbound",
        # Batch 1 QA: raw CSV had the pair's inbound-side coordinates (224/225 swap).
        "lat": 13.815248,
        "lon": 100.575513,
    },
    228: {
        "location_th": "หน้าโรงพยาบาลกลาง ถนนหลวง",
        "location_detail_th": "รถมาจากแยกโรงพยาบาลกลาง มุ่งหน้าแยกวรจักร",
        "location_en": "In front of Klang Hospital on Luang Road",
        "location_detail_en": "From Klang Hospital Intersection towards Worachak Intersection",
        "district": "Pom Prap Sattru Phai",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "Inbound",
    },
    230: {
        "location_th": "ปากซอยระนอง 2 ถนนพระรามที่ 5",
        "location_detail_th": "ช่วงแยกสะพานแดง – แยกเกษะโกมล (เห็นรถทั้งสองทิศทาง)",
        "location_en": "Entrance to Soi Ranong 2 on Rama 5 Road",
        "location_detail_en": "Between Saphan Daeng and Kesakomon Intersections (both directions visible)",
        "district": "Dusit",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    233: {
        "location_th": "ตรงข้ามพระตำหนักจิตรลดารโหฐาน ถนนพระรามที่ 5",
        "location_detail_th": "ช่วงแยกราชวิถี – แยกวัดเบญจมบพิตร (เห็นรถทั้งสองทิศทาง)",
        "location_en": "Opposite Chitralada Palace on Rama 5 Road",
        "location_detail_en": "Between Ratchawithi and Wat Benchamabophit Intersections (both directions visible)",
        "district": "Dusit",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": "PAIR_2W_CHITRALADA",
        "pair_type": "two_way_no_median",
        "direction": "None",
    },
    239: {
        "location_th": "สะพานลอยใกล้โรงเรียนเตรียมอุดมศึกษา ถนนพญาไท",
        "location_detail_th": "รถมาจากแยกปทุมวัน มุ่งหน้าแยกสามย่าน",
        "location_en": "Footbridge near Triam Udom Suksa School on Phayathai Road",
        "location_detail_en": "From Pathum Wan Intersection towards Sam Yan Intersection",
        "district": "Pathum Wan",
        "corridor": "Pathum Wan - Phetchaburi - Victory Monument",
        "pair_id": None,
        "pair_type": None,
        "direction": "Inbound",
    },
    250: {
        "location_th": "สะพานลอยใกล้ซอยเพชรบุรี 38 ถนนเพชรบุรี",
        "location_detail_th": "ช่วงแยกพร้อมพงษ์ - แยกอโศก-เพชรบุรี (เห็นรถทั้งสองทิศทาง)",
        "location_en": "Footbridge near Soi Phetchaburi 38 on Phetchaburi Road",
        "location_detail_en": "Between Phrom Phong and Asok-Phetchaburi Intersections (both directions visible)",
        "district": "Ratchathewi",
        "corridor": "Pathum Wan - Phetchaburi - Victory Monument",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    251: {
        "location_th": "สะพานลอยใกล้วัดดิสหงษาราม ถนนเพชรบุรี",
        "location_detail_th": "ช่วงแยกใต้ด่วนเพชรบุรี - แยกมิตรสัมพันธ์ (เห็นรถทั้งสองทิศทาง)",
        "location_en": "Footbridge near Wat Ditsahongsaram (Wat Makkasan) on Phetchaburi Road",
        "location_detail_en": "Between Phetchaburi Expressway and Mit Samphan Intersections (both directions visible)",
        "district": "Ratchathewi",
        "corridor": "Pathum Wan - Phetchaburi - Victory Monument",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    256: {
        "location_th": "สะพานลอยใกล้ซอยเพชรบุรี 27 ถนนเพชรบุรี",
        "location_detail_th": "ช่วงแยกประตูน้ำ - ใต้ทางด่วนเฉลิมมหานคร (เห็นรถทั้งสองทิศทาง)",
        "location_en": "Footbridge near Soi Phetchaburi 27 on Phetchaburi Road",
        "location_detail_en": "Between Pratu Nam Intersection and Chalerm Maha Nakhon Expressway (both directions visible)",
        "district": "Ratchathewi",
        "corridor": "Pathum Wan - Phetchaburi - Victory Monument",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    277: {
        "location_th": "วงเวียนอนุสาวรีย์ชัยสมรภูมิ",
        "location_detail_th": "บริเวณวงเวียนอนุสาวรีย์ชัยสมรภูมิ (มุมเกาะพญาไท เห็นรถวนรอบวงเวียนและแยกออกหลายทิศทาง)",
        "location_en": "Victory Monument Roundabout",
        "location_detail_en": "Victory Monument Roundabout (Phayathai Island side, multi-directional roundabout traffic)",
        "district": "Ratchathewi",
        "corridor": "Pathum Wan - Phetchaburi - Victory Monument",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    301: {
        "location_th": "แยกอู่ทองนอก",
        "location_detail_th": "บริเวณแยกอู่ทองนอก ด้านถนนอู่ทองนอก",
        "location_en": "U Thong Nok Intersection",
        "location_detail_en": "At U Thong Nok Intersection (U Thong Nok Road side)",
        "district": "Dusit",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    332: {
        "location_th": "แยกราชวัตร",
        "location_detail_th": "แยกราชวัตร ถนนนครไชยศรี – ถนนพระรามที่ 5 (เห็นรถทั้งสองทิศทางและรถตัดผ่านแยก)",
        "location_en": "Ratchawat Intersection",
        "location_detail_en": "Ratchawat Intersection towards Phichai Intersection (both directions and cross traffic visible)",
        "district": "Dusit",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    363: {
        "location_th": "แยกเขตดุสิต",
        "location_detail_th": "แยกเขตดุสิต ถนนพระรามที่ 5 – ถนนสุโขทัย (เห็นรถหลายทิศทาง)",
        "location_en": "Khet Dusit Intersection",
        "location_detail_en": "Khet Dusit Intersection, Rama 5 & Sukhothai Roads (multi-directional view)",
        "district": "Dusit",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    370: {
        "location_th": "แยกเทเวศร์",
        "location_detail_th": "ถนนกรุงเกษม ช่วงแยกเทเวศร์ – แยกประชาเกษม (เลียบคลองผดุงกรุงเกษม เห็นรถทั้งสองทิศทาง)",
        "location_en": "Thewet Intersection",
        "location_detail_en": "Krung Kasem Rd between Thewet and Pracha Kasem Intersections (both directions)",
        "district": "Phra Nakhon",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": "PAIR_OV_THEWET",
        "pair_type": "overlapping_junction",
        "direction": "None",
    },
    371: {
        "location_th": "แยกเทเวศร์",
        "location_detail_th": "บริเวณแยกเทเวศร์ ถนนสามเสน – ถนนกรุงเกษม (เห็นรถหลายทิศทาง)",
        "location_en": "Thewet Intersection",
        "location_detail_en": "Thewet Intersection crosswalks (multi-directional intersection view)",
        "district": "Phra Nakhon",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": "PAIR_OV_THEWET",
        "pair_type": "overlapping_junction",
        "direction": "None",
    },
    395: {
        "location_th": "แยกเสาชิงช้า",
        "location_detail_th": "บริเวณแยกเสาชิงช้า",
        "location_en": "Sao Chingcha Intersection",
        "location_detail_en": "Sao Chingcha Intersection",
        "district": "Phra Nakhon",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    411: {
        "location_th": "แนวถนนพระอาทิตย์ 2",
        "location_detail_th": "แนวถนนพระอาทิตย์",
        "location_en": "Phra Athit Road (Camera 1)",
        "location_detail_en": "Phra Athit Road",
        "lat": 13.7619642,
        "lon": 100.4934256,
        "district": "Phra Nakhon",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": "PAIR_OV_PHRAATHIT",
        "pair_type": "overlapping_junction",
        "direction": "None",
    },
    412: {
        "location_th": "แนวถนนพระอาทิตย์ 2",
        "location_detail_th": "แนวถนนพระอาทิตย์",
        "location_en": "Phra Athit Road (Camera 2)",
        "location_detail_en": "Phra Athit Road",
        "lat": 13.7619642,
        "lon": 100.4934256,
        "district": "Phra Nakhon",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": "PAIR_OV_PHRAATHIT",
        "pair_type": "overlapping_junction",
        "direction": "None",
    },
    413: {
        "location_th": "แนวถนนตะนาว 1",
        "location_detail_th": "แนวถนนตะนาว",
        "location_en": "Tanao Road",
        "location_detail_en": "Tanao Road",
        "lat": 13.754495,
        "lon": 100.4985768,
        "district": "Phra Nakhon",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    414: {
        "location_th": "บริเวณใต้สะพานพุทธ",
        "location_detail_th": "มุ่งเข้าสู่ย่านพระนครและสนามไชย",
        "location_en": "Under Phra Phuttha Yodfa Bridge (Memorial Bridge)",
        "location_detail_en": "Towards Phra Nakhon area and Sanam Chai",
        "lat": 13.7402672,
        "lon": 100.4977062,
        "district": "Phra Nakhon",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "Inbound",
    },
    432: {
        "location_th": "ทางแยกสามย่าน",
        "location_detail_th": "รถมาจากสีลม มุ่งหน้าไปหัวลำโพง (บริเวณแยกสามย่าน ถนนพระรามที่ 4)",
        "location_en": "Sam Yan Intersection",
        "location_detail_en": "From Silom towards Hua Lamphong (Sam Yan Intersection, Rama 4 Road)",
        "district": "Pathum Wan",
        "corridor": "Pathum Wan - Phetchaburi - Victory Monument",
        "pair_id": None,
        "pair_type": None,
        "direction": "Inbound",
    },
    500: {
        "location_th": "แยกประตูน้ำ",
        "location_detail_th": "บริเวณแยกประตูน้ำ",
        "location_en": "Pratu Nam Intersection",
        "location_detail_en": "At Pratu Nam Intersection",
        "district": "Ratchathewi",
        "corridor": "Pathum Wan - Phetchaburi - Victory Monument",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    529: {
        "location_th": "จุดตัดถนนพุทธมณฑลสาย 2",
        "location_detail_th": "ถนนบรมราชชนนี-พุทธมณฑลสาย 2",
        "location_en": "Phutthamonthon Sai 2 - Borommaratchachonnani Interchange",
        "location_detail_en": "Phutthamonthon Sai 2 / Borommaratchachonnani",
        "district": "Thawi Watthana",
        "corridor": "Thon Buri - Charoen Nakhon - Borommaratchachonnani",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    542: {
        "location_th": "ทางแยกหลังสวน (สารสิน-หลังสวน)",
        "location_detail_th": "แยกสารสิน-หลังสวน ริมสวนลุมพินี",
        "location_en": "Lang Suan - Sarasin Intersection",
        "location_detail_en": "Lang Suan - Sarasin Intersection near Lumphini Park",
        "district": "Pathum Wan",
        "corridor": "Pathum Wan - Phetchaburi - Victory Monument",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    546: {
        "location_th": "แยกพาณิชยการ (ด้านถนนพิษณุโลก)",
        "location_detail_th": "บริเวณแยกพาณิชยการ ด้านถนนพิษณุโลก",
        "location_en": "Panichayakarn Intersection (Phitsanulok Road)",
        "location_detail_en": "At Panichayakarn Intersection (Phitsanulok Road side)",
        "district": "Dusit",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": "PAIR_JX_PANICHAYAKARN",
        "pair_type": "perpendicular_junction",
        "direction": "None",
    },
    556: {
        "location_th": "แยกวชิระ",
        "location_detail_th": "รถมาจากวัดประสาทบุญญาวาส",
        "location_en": "Vajira Intersection",
        "location_detail_en": "From Wat Prasat Bunyawat",
        "district": "Dusit",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "Inbound",
    },
    569: {
        "location_th": "แยก จ.ป.ร.",
        "location_detail_th": "บริเวณแยก จ.ป.ร.",
        "location_en": "Jor Por Ror Intersection",
        "location_detail_en": "Jor Por Ror Intersection",
        "district": "Phra Nakhon",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    572: {
        "location_th": "ทางคู่ขนานลอยฟ้าบรมราชชนนี (ช่วงทางขึ้นตลิ่งชัน)",
        "location_detail_th": "ช่วงทางขึ้นตลิ่งชัน ถนนบรมราชชนนี",
        "location_en": "Borommaratchachonnani Elevated Highway (Taling Chan Ramp)",
        "location_detail_en": "Taling Chan ascending ramp",
        "district": "Taling Chan",
        "corridor": "Thon Buri - Charoen Nakhon - Borommaratchachonnani",
        "pair_id": None,
        "pair_type": None,
        "direction": "Inbound",
    },
    576: {
        "location_th": "แยกบางลำพู",
        "location_detail_th": "รถมุ่งหน้าไปถนนข้าวสาร / สนามหลวง",
        "location_en": "Bang Lamphu Intersection",
        "location_detail_en": "Towards Khao San Road / Sanam Luang",
        "district": "Phra Nakhon",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "Inbound",
    },
    595: {
        "location_th": "แยกบ้านแขก",
        "location_detail_th": "บริเวณแยกบ้านแขก",
        "location_en": "Ban Khaek Intersection",
        "location_detail_en": "At Ban Khaek Intersection",
        "district": "Thon Buri",
        "corridor": "Thon Buri - Charoen Nakhon - Borommaratchachonnani",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    599: {
        "location_th": "แยกสุรศักดิ์",
        "location_detail_th": "บริเวณแยกสุรศักดิ์",
        "location_en": "Surasak Intersection",
        "location_detail_en": "At Surasak Intersection",
        "district": "Bang Rak",
        "corridor": "Sathon - Naradhiwas - Rama 3",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    603: {
        "location_th": "แยกสีลม-นราธิวาส",
        "location_detail_th": "บริเวณแยกสีลม-นราธิวาส",
        "location_en": "Silom-Naradhiwas Intersection",
        "location_detail_en": "At Silom-Naradhiwas Intersection",
        "district": "Bang Rak",
        "corridor": "Sathon - Naradhiwas - Rama 3",
        "pair_id": "PAIR_JX_SILOM_NARADHIWAS",
        "pair_type": "perpendicular_junction",
        "direction": "None",
    },
    604: {
        "location_th": "แยกสีลม-นราธิวาส",
        "location_detail_th": "บริเวณแยกสีลม-นราธิวาส",
        "location_en": "Silom-Naradhiwas Intersection",
        "location_detail_en": "At Silom-Naradhiwas Intersection",
        "district": "Bang Rak",
        "corridor": "Sathon - Naradhiwas - Rama 3",
        "pair_id": "PAIR_JX_SILOM_NARADHIWAS",
        "pair_type": "perpendicular_junction",
        "direction": "None",
    },
    619: {
        "location_th": "ทางแยกอังรีดูนังต์",
        "location_detail_th": "บริเวณแยกอังรีดูนังต์",
        "location_en": "Henri Dunant Intersection",
        "location_detail_en": "Henri Dunant Intersection",
        "district": "Pathum Wan",
        "corridor": "Pathum Wan - Phetchaburi - Victory Monument",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    630: {
        "location_th": "แยกเกษะโกมล (ด้านถนนพระราม 5)",
        "location_detail_th": "ช่วงแยกเกษะโกมล - แยกราชวัตร (เห็นรถทั้งสองทิศทาง)",
        "location_en": "Kesakomon Intersection (Rama 5 Road)",
        "location_detail_en": "Between Kesakomon and Ratchawat Intersections (both directions visible)",
        "district": "Dusit",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    913: {
        "location_th": "แยกเอส.เอ.บี.",
        "location_detail_th": "บริเวณแยกเอส.เอ.บี. (ถนนเจริญกรุง-วรจักร)",
        "location_en": "S.A.B. Intersection",
        "location_detail_en": "S.A.B. Intersection (Charoen Krung - Worachak Road)",
        "district": "Pom Prap Sattru Phai",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    915: {
        "location_th": "วงเวียนใหญ่",
        "location_detail_th": "บริเวณวงเวียนใหญ่",
        "location_en": "Wongwian Yai Roundabout",
        "location_detail_en": "At Wongwian Yai Roundabout",
        "lat": 13.72572,
        "lon": 100.49268,
        "district": "Thon Buri",
        "corridor": "Thon Buri - Charoen Nakhon - Borommaratchachonnani",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    938: {
        "location_th": "แยกรามคำแหง-พระราม 9",
        "location_detail_th": "บริเวณแยกรามคำแหง-พระราม 9",
        "location_en": "Ramkhamhaeng - Rama 9 Intersection",
        "location_detail_en": "Ramkhamhaeng - Rama 9 Intersection",
        "district": "Bang Kapi",
        "corridor": "East Bangkok (Ramkhamhaeng - On Nut)",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    939: {
        "location_th": "แยกมหาดไทย",
        "location_detail_th": "บริเวณแยกมหาดไทย (สะพานรามคำแหง)",
        "location_en": "Mahadthai Intersection",
        "location_detail_en": "Mahadthai Intersection (Ramkhamhaeng Bridge)",
        "district": "Bang Kapi",
        "corridor": "East Bangkok (Ramkhamhaeng - On Nut)",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    1028: {
        "location_th": "แยกสะพานแดง",
        "location_detail_th": "บริเวณแยกสะพานแดง",
        "location_en": "Saphan Daeng Intersection",
        "location_detail_en": "Saphan Daeng Intersection",
        "district": "Dusit",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": "PAIR_OV_SAPHANDAENG",
        "pair_type": "overlapping_junction",
        "direction": "None",
    },
    1039: {
        "location_th": "ใกล้สะพานนริศดำรัส (คลองมหานาค)",
        "location_detail_th": "บริเวณสะพานนริศดำรัส",
        "location_en": "Near Narit Damrat Bridge (Khlong Mahanak)",
        "location_detail_en": "At Narit Damrat Bridge",
        "district": "Pom Prap Sattru Phai",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    1060: {
        "location_th": "หน้าโรงเรียนสายปัญญา ถนนกรุงเกษม",
        "location_detail_th": "รถมาจากถนนพระรามที่ 1",
        "location_en": "In front of Sai Panya School on Krung Kasem Road",
        "location_detail_en": "From Rama 1 Road",
        "district": "Pom Prap Sattru Phai",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "Inbound",
    },
    1063: {
        "location_th": "ตรงข้ามพระตำหนักจิตรลดารโหฐาน ถนนพระรามที่ 5",
        "location_detail_th": "ช่วงแยกวัดเบญจมบพิตร – แยกราชวิถี (เห็นรถทั้งสองทิศทาง)",
        "location_en": "Opposite Chitralada Palace on Rama 5 Road",
        "location_detail_en": "Between Wat Benchamabophit and Ratchawithi Intersections (both directions visible)",
        "district": "Dusit",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": "PAIR_2W_CHITRALADA",
        "pair_type": "two_way_no_median",
        "direction": "None",
    },
    1070: {
        "location_th": "สะพานลอยใกล้ซอยพหลโยธิน 18/2 ถนนพหลโยธิน",
        "location_detail_th": "รถมาจากแยกกำแพงเพชร มุ่งหน้าห้าแยกลาดพร้าว",
        "location_en": "Footbridge near Soi Phahon Yothin 18/2 on Phahon Yothin Road",
        "location_detail_en": "From Kamphaeng Phet Intersection towards Lat Phrao Intersection",
        "district": "Chatuchak",
        "corridor": "Phahon Yothin - Lat Phrao",
        "pair_id": None,
        "pair_type": None,
        "direction": "Outbound",
    },
    1071: {
        "location_th": "แยกกำแพงเพชร (ด้านถนนพหลโยธิน)",
        "location_detail_th": "บริเวณแยกกำแพงเพชร ด้านถนนพหลโยธิน",
        "location_en": "Kamphaeng Phet Intersection (Phahon Yothin Road)",
        "location_detail_en": "At Kamphaeng Phet Intersection (Phahon Yothin Road side)",
        "district": "Chatuchak",
        "corridor": "Phahon Yothin - Lat Phrao",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    1076: {
        "location_th": "สะพานลอยใกล้ซอยเทอดไท 21 ถนนราชพฤกษ์",
        "location_detail_th": "รถมาจากแยกตากสิน มุ่งหน้าแยกรัชดา-ราชพฤกษ์",
        "location_en": "Footbridge near Soi Thoet Thai 21 on Ratchaphruek Road",
        "location_detail_en": "From Taksin Intersection towards Ratchada-Ratchaphruek Intersection",
        "district": "Thon Buri",
        "corridor": "Thon Buri - Charoen Nakhon - Borommaratchachonnani",
        "pair_id": None,
        "pair_type": None,
        "direction": "Outbound",
    },
    1078: {
        "location_th": "สะพานลอยหน้าวัดสุวรรณ ถนนเจริญนคร",
        "location_detail_th": "รถมาจากแยกคลองสาน มุ่งหน้าแยกเจริญนครใต้",
        "location_en": "Footbridge in front of Wat Suwan on Charoen Nakhon Road",
        "location_detail_en": "From Khlong San Intersection towards Charoen Nakhon Tai Intersection",
        "district": "Khlong San",
        "corridor": "Thon Buri - Charoen Nakhon - Borommaratchachonnani",
        "pair_id": "FB_06_WatSuwan",
        "pair_type": "footbridge_bidirectional",
        "direction": "Outbound",
    },
    1103: {
        "location_th": "แยกรัชดา-ราชพฤกษ์ (ด้านถนนรัชดาภิเษก)",
        "location_detail_th": "รถมาจากแยกท่าพระ",
        "location_en": "Ratchada-Ratchaphruek Intersection (Ratchadaphisek Road)",
        "location_detail_en": "From Tha Phra Intersection",
        "district": "Thon Buri",
        "corridor": "Thon Buri - Charoen Nakhon - Borommaratchachonnani",
        "pair_id": None,
        "pair_type": None,
        "direction": "Inbound",
    },
    1112: {
        "location_th": "แยกสุทธิสาร (ถนนสุทธิสารวินิจฉัย)",
        "location_detail_th": "แยกสุทธิสาร (ถนนสุทธิสารวินิจฉัย)",
        "location_en": "Sutthisan Intersection (Sutthisan Winitchai Road)",
        "location_detail_en": "Sutthisan Intersection (Sutthisan Winitchai Road)",
        "district": "Din Daeng",
        "corridor": "Phahon Yothin - Lat Phrao",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    1132: {
        "location_th": "สะพานลอยหน้าวัดสุวรรณ ถนนเจริญนคร",
        "location_detail_th": "รถมาจากแยกเจริญนครใต้ มุ่งหน้าแยกคลองสาน",
        "location_en": "Footbridge in front of Wat Suwan on Charoen Nakhon Road",
        "location_detail_en": "From Charoen Nakhon Tai Intersection towards Khlong San Intersection",
        "district": "Khlong San",
        "corridor": "Thon Buri - Charoen Nakhon - Borommaratchachonnani",
        "pair_id": "FB_06_WatSuwan",
        "pair_type": "footbridge_bidirectional",
        "direction": "Inbound",
    },
    1188: {
        "location_th": "ถนนกาญจนาภิเษก (ต่างระดับฉิมพลี)",
        "location_detail_th": "ถนนกาญจนาภิเษก มุ่งหน้าทางแยกต่างระดับบางเชือกหนัง (เห็นทั้งขาเข้าและขาออก)",
        "location_en": "Kanchanaphisek Road (Chimphli Interchange)",
        "location_detail_en": "Overlooking Kanchanaphisek Road (Motorway 9) towards Bang Chueak Nang Interchange (both directions)",
        "district": "Taling Chan",
        "corridor": "Thon Buri - Charoen Nakhon - Borommaratchachonnani",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    1195: {
        "location_th": "แยกบุคคโล (ด้านถนนเจริญนคร)",
        "location_detail_th": "บริเวณแยกบุคคโล ด้านถนนเจริญนคร",
        "location_en": "Bukkhalo Intersection (Charoen Nakhon Road)",
        "location_detail_en": "At Bukkhalo Intersection (Charoen Nakhon Road side)",
        "district": "Thon Buri",
        "corridor": "Thon Buri - Charoen Nakhon - Borommaratchachonnani",
        "pair_id": "PAIR_ARM_BUKKHALO",
        "pair_type": "opposite_intersection_arm",
        "direction": "None",
    },
    1361: {
        "location_th": "หน้าธนาคารแห่งประเทศไทย ถนนสามเสน",
        "location_detail_th": "ถนนสามเสน หน้า ธปท. (เห็นทั้งรถขาเข้าและเลนสวนทาง)",
        "location_en": "In front of Bank of Thailand on Sam Sen Road",
        "location_detail_en": "In front of Bank of Thailand (both main and contraflow lanes visible)",
        "district": "Phra Nakhon",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": "PAIR_2W_BOT_SAMSEN",
        "pair_type": "two_way_no_median",
        "direction": "None",
    },
    1362: {
        "location_th": "ถนนสามเสน",
        "location_detail_th": "ถนนสามเสน บริเวณหน้าทางเข้าวัดราชาธิวาสวิหาร",
        "location_en": "Samsen Road",
        "location_detail_en": "Samsen Road in front of the entrance to Wat Rajadhivas Vihara",
        "lat": 13.7746377,
        "lon": 100.5067094,
        "district": "Dusit",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    1368: {
        "location_th": "แยกพาณิชยการ (ด้านถนนพระรามที่ 5)",
        "location_detail_th": "แยกพาณิชยการ ด้านถนนพระรามที่ 5 หน้า มทร.พระนคร (เห็นรถทั้งสองทิศทาง)",
        "location_en": "Panichayakarn Intersection (Rama 5 Road)",
        "location_detail_en": "Rama 5 Rd side past RMUTP (both directions)",
        "district": "Dusit",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": "PAIR_JX_PANICHAYAKARN",
        "pair_type": "perpendicular_junction",
        "direction": "None",
    },
    1408: {
        "location_th": "แยกเทียมร่วมมิตร (หน้าอาคารไซเบอร์เวิลด์)",
        "location_detail_th": "บริเวณแยกเทียมร่วมมิตร (หน้าอาคารไซเบอร์เวิลด์)",
        "location_en": "Thiam Ruam Mit Intersection (Cyber World Tower)",
        "location_detail_en": "At Thiam Ruam Mit Intersection (in front of Cyber World Tower)",
        "district": "Huai Khwang",
        "corridor": "Ratchadaphisek",
        "pair_id": "PAIR_JX_THIAMRUAMMIT",
        "pair_type": "perpendicular_junction",
        "direction": "None",
    },
    1589: {
        "location_th": "แยกแม้นศรี",
        "location_detail_th": "บริเวณแยกแม้นศรี",
        "location_en": "Maen Si Intersection",
        "location_detail_en": "Maen Si Intersection",
        "district": "Pom Prap Sattru Phai",
        "corridor": "Old Town - Dusit - Rama 5",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    1804: {
        "location_th": "ปากซอยอ่อนนุช 33 ถนนอ่อนนุช",
        "location_detail_th": "ปากซอยอ่อนนุช 33 ถนนอ่อนนุช",
        "location_en": "Entrance to Soi On Nut 33 on On Nut Road",
        "location_detail_en": "Entrance to Soi On Nut 33 on On Nut Road",
        "district": "Suan Luang",
        "corridor": "East Bangkok (Ramkhamhaeng - On Nut)",
        "pair_id": None,
        "pair_type": None,
        "direction": "None",
    },
    1815: {
        "location_th": "แยกพระราม 9",
        "location_detail_th": "หน้ารถมาจากแยกผังเมือง",
        "location_en": "Rama 9 Intersection",
        "location_detail_en": "From Phang Mueang Intersection",
        "district": "Din Daeng",
        "corridor": "Ratchadaphisek",
        "pair_id": None,
        "pair_type": None,
        "direction": "Inbound",
    },
}


def decode_image_unicode(filepath: Path) -> np.ndarray | None:
    """Read an image from a path that may contain non-ASCII (Thai) characters on Windows."""
    buf = np.fromfile(str(filepath), dtype=np.uint8)
    if buf.size == 0:
        return None
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def parse_timestamp_from_filename(filename: str) -> datetime:
    """Gate 5: Strictly extract capture timestamp from filename YYYYMMDD_HHMMSS."""
    match = FILENAME_TS_PATTERN.search(filename)
    if not match:
        raise ValueError(f"Filename does not match _YYYYMMDD_HHMMSS.jpg: {filename}")
    return datetime.strptime(f"{match.group(1)}_{match.group(2)}", "%Y%m%d_%H%M%S")


def evaluate_single_frame_metrics(filepath: Path) -> dict[str, Any]:
    """Compute file size, dimensions, pixel color stats, and Gates 1-3 flags."""
    file_size = filepath.stat().st_size
    img = decode_image_unicode(filepath)
    if img is None:
        return {
            "img": None,
            "file_size": file_size,
            "width": 0,
            "height": 0,
            "pixel_area": 0,
            "brightness_mean": 0.0,
            "contrast_std": 0.0,
            "b_mean": 0.0,
            "g_mean": 0.0,
            "r_mean": 0.0,
            "glare_ratio": 0.0,
            "gray128_ratio": 0.0,
            "neon_green_ratio": 0.0,
            "is_unreadable": True,
            "is_white_error": False,
            "is_no_signal_error": False,
            "is_gray_pframe": False,
            "is_green_screen": False,
        }

    height, width = img.shape[:2]
    pixel_area = int(width * height)
    b_ch = img[:, :, 0]
    g_ch = img[:, :, 1]
    r_ch = img[:, :, 2]

    brightness_mean = float(img.mean())
    contrast_std = float(img.std())
    b_mean = float(b_ch.mean())
    g_mean = float(g_ch.mean())
    r_mean = float(r_ch.mean())

    # Visual environment + partial corruption indicators (for downstream Stage 2/3)
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    glare_ratio = float(np.mean(gray_img > GLARE_PIXEL_THRESHOLD))

    b_i16 = b_ch.astype(np.int16)
    g_i16 = g_ch.astype(np.int16)
    r_i16 = r_ch.astype(np.int16)
    gray128_ratio = float(
        np.mean(
            (np.abs(r_i16 - 128) <= PARTIAL_GRAY128_TOLERANCE)
            & (np.abs(g_i16 - 128) <= PARTIAL_GRAY128_TOLERANCE)
            & (np.abs(b_i16 - 128) <= PARTIAL_GRAY128_TOLERANCE)
        )
    )
    neon_green_ratio = float(
        np.mean(
            ((g_i16 - r_i16) > PARTIAL_GREEN_DIFF)
            & ((g_i16 - b_i16) > PARTIAL_GREEN_DIFF)
        )
    )

    # Gate 1: Blank White Error Frames
    is_white_error = (file_size < WHITE_MAX_BYTES) or (
        brightness_mean == WHITE_BRIGHTNESS_EXACT
    )

    # Gate 2: Rainbow No Signal (gst-launch-0.10 test pattern)
    is_no_signal_error = (not is_white_error) and (
        (file_size == RAINBOW_EXACT_BYTES)
        or (
            RAINBOW_SIZE_MIN <= file_size <= RAINBOW_SIZE_MAX
            and RAINBOW_MEAN_MIN <= brightness_mean <= RAINBOW_MEAN_MAX
            and contrast_std >= RAINBOW_STD_MIN
        )
    )

    # Gate 3: Gray P-Frame & Green Screen YUV corruptions
    is_gray_pframe = (
        not is_white_error
        and not is_no_signal_error
        and (GRAY_PFRAME_MEAN_MIN <= brightness_mean <= GRAY_PFRAME_MEAN_MAX)
        and (contrast_std < GRAY_PFRAME_STD_MAX)
    )
    is_green_screen = (
        not is_white_error
        and not is_no_signal_error
        and ((g_mean - r_mean) > GREEN_SCREEN_CHANNEL_DIFF)
        and ((g_mean - b_mean) > GREEN_SCREEN_CHANNEL_DIFF)
    )

    return {
        "img": img,
        "file_size": file_size,
        "width": width,
        "height": height,
        "pixel_area": pixel_area,
        "brightness_mean": round(brightness_mean, 4),
        "contrast_std": round(contrast_std, 4),
        "b_mean": round(b_mean, 4),
        "g_mean": round(g_mean, 4),
        "r_mean": round(r_mean, 4),
        "glare_ratio": round(glare_ratio, 6),
        "gray128_ratio": round(gray128_ratio, 6),
        "neon_green_ratio": round(neon_green_ratio, 6),
        "is_unreadable": False,
        "is_white_error": bool(is_white_error),
        "is_no_signal_error": bool(is_no_signal_error),
        "is_gray_pframe": bool(is_gray_pframe),
        "is_green_screen": bool(is_green_screen),
    }


def process_camera_directory(
    cam_dir: Path,
    raw_root: Path,
    clean_images_root: Path,
    copy_valid: bool,
) -> list[dict[str, Any]]:
    """Run all 5 Image Quality Gates chronologically for one camera and copy valid frames."""
    cam_id = int(cam_dir.name)
    files = [p for p in cam_dir.iterdir() if p.is_file() and p.suffix.lower() == ".jpg"]

    parsed_files: list[tuple[datetime, Path]] = []
    for fpath in files:
        dt = parse_timestamp_from_filename(fpath.name)
        parsed_files.append((dt, fpath))
    parsed_files.sort(key=lambda item: item[0])

    records: list[dict[str, Any]] = []
    last_non_error_img: np.ndarray | None = None
    last_non_error_ts: datetime | None = None

    if copy_valid:
        out_cam_dir = clean_images_root / str(cam_id)
        out_cam_dir.mkdir(parents=True, exist_ok=True)

    for dt, fpath in parsed_files:
        clean_filename = f"{cam_id}_{dt.strftime('%Y%m%d_%H%M%S')}.jpg"
        manual_reason = (
            MANUAL_EXCLUDED_IMAGES.get(clean_filename)
            or MANUAL_EXCLUDED_IMAGES.get(fpath.name)
        )
        is_manual_excluded = manual_reason is not None

        metrics = evaluate_single_frame_metrics(fpath)
        img = metrics.pop("img")

        is_corrupt_color = metrics["is_gray_pframe"] or metrics["is_green_screen"]
        is_primary_error = (
            metrics["is_unreadable"]
            or metrics["is_white_error"]
            or metrics["is_no_signal_error"]
            or is_corrupt_color
            or is_manual_excluded
        )

        is_frozen = False
        mad_from_prev: float | None = None
        frozen_ref_ts_str: str | None = None

        # Gate 4: Compare against the most recent non-error frame of the same camera
        if not is_primary_error and img is not None:
            if last_non_error_img is not None and last_non_error_img.shape == img.shape:
                mad_val = float(
                    np.mean(
                        np.abs(
                            img.astype(np.int16) - last_non_error_img.astype(np.int16)
                        )
                    )
                )
                mad_from_prev = round(mad_val, 6)
                if mad_val == 0.0:
                    is_frozen = True
                    frozen_ref_ts_str = (
                        last_non_error_ts.strftime("%Y-%m-%d %H:%M:%S")
                        if last_non_error_ts is not None
                        else None
                    )
            if not is_frozen:
                last_non_error_img = img
                last_non_error_ts = dt

        if metrics["is_unreadable"]:
            status = "unreadable_error"
            error_subtype = "unreadable_error"
        elif metrics["is_white_error"]:
            status = "white_error"
            error_subtype = "white_error"
        elif metrics["is_no_signal_error"]:
            status = "no_signal_error"
            error_subtype = "no_signal_rainbow"
        elif metrics["is_gray_pframe"]:
            status = "corrupt_color"
            error_subtype = "gray_pframe"
        elif metrics["is_green_screen"]:
            status = "corrupt_color"
            error_subtype = "green_screen"
        elif is_manual_excluded:
            status = "manual_excluded"
            error_subtype = str(manual_reason).strip() or "manual_excluded"
        elif is_frozen:
            status = "frozen"
            error_subtype = "frozen"
        else:
            status = "valid"
            error_subtype = "none"

        is_valid = status == "valid"

        if is_valid and metrics["gray128_ratio"] > PARTIAL_GRAY128_WARN_RATIO:
            quality_warning = "partial_gray_pframe"
        elif is_valid and metrics["neon_green_ratio"] > PARTIAL_GREEN_WARN_RATIO:
            quality_warning = "partial_green_screen"
        else:
            quality_warning = "none"

        clean_rel_path = f"cctv_images/{cam_id}/{clean_filename}" if is_valid else None
        raw_rel_path = fpath.relative_to(raw_root.parent.parent).as_posix()

        if copy_valid:
            dest_path = clean_images_root / str(cam_id) / clean_filename
            if is_valid:
                shutil.copy2(fpath, dest_path)
            elif dest_path.exists():
                dest_path.unlink()

        records.append(
            {
                "cam_id": cam_id,
                "timestamp": dt,
                "date": dt.strftime("%Y-%m-%d"),
                "hour": dt.hour,
                "minute": dt.minute,
                "day_of_week": dt.strftime("%A"),
                "is_weekend": dt.weekday() >= 5,
                "filename": fpath.name,
                "clean_filename": clean_filename if is_valid else None,
                "clean_rel_path": clean_rel_path,
                "raw_rel_path": raw_rel_path,
                "file_size": metrics["file_size"],
                "width": metrics["width"],
                "height": metrics["height"],
                "pixel_area": metrics["pixel_area"],
                "status": status,
                "error_subtype": error_subtype,
                "is_valid": is_valid,
                "is_white_error": metrics["is_white_error"],
                "is_no_signal_error": metrics["is_no_signal_error"],
                "is_gray_pframe": metrics["is_gray_pframe"],
                "is_green_screen": metrics["is_green_screen"],
                "is_corrupt_color": bool(is_corrupt_color),
                "is_frozen": is_frozen,
                "is_manual_excluded": is_manual_excluded,
                "mad_from_prev": mad_from_prev,
                "frozen_ref_timestamp": frozen_ref_ts_str,
                "brightness_mean": metrics["brightness_mean"],
                "contrast_std": metrics["contrast_std"],
                "r_mean": metrics["r_mean"],
                "g_mean": metrics["g_mean"],
                "b_mean": metrics["b_mean"],
                "glare_ratio": metrics["glare_ratio"],
                "gray128_ratio": metrics["gray128_ratio"],
                "neon_green_ratio": metrics["neon_green_ratio"],
                "quality_warning": quality_warning,
            }
        )

    return records


def build_cleaned_metadata(
    raw_info_path: Path,
    manifest_df: pd.DataFrame,
) -> pd.DataFrame:
    """Clean cctv_info.csv and join per-camera quality statistics."""
    raw_df = pd.read_csv(raw_info_path)
    raw_ids = set(raw_df["camera_id"].astype(int).tolist())
    curated_ids = set(CAMERA_CURATION.keys())
    if raw_ids != curated_ids:
        missing = sorted(raw_ids - curated_ids)
        extra = sorted(curated_ids - raw_ids)
        raise ValueError(f"Camera curation mismatch: missing={missing}, extra={extra}")

    cam_stats = (
        manifest_df.groupby("cam_id", as_index=False)
        .agg(
            actual_raw_image_count=("filename", "count"),
            valid_image_count=("is_valid", "sum"),
            white_error_count=("is_white_error", "sum"),
            no_signal_error_count=("is_no_signal_error", "sum"),
            corrupt_color_count=("is_corrupt_color", "sum"),
            frozen_image_count=("is_frozen", "sum"),
        )
    )
    valid_dims = (
        manifest_df.loc[manifest_df["is_valid"]]
        .groupby("cam_id", as_index=False)
        .agg(
            img_width=("width", lambda s: int(s.mode().iloc[0])),
            img_height=("height", lambda s: int(s.mode().iloc[0])),
        )
    )
    cam_stats = cam_stats.merge(valid_dims, on="cam_id", how="left")
    cam_stats["error_image_count"] = (
        cam_stats["actual_raw_image_count"] - cam_stats["valid_image_count"]
    )
    cam_stats["valid_rate_pct"] = (
        cam_stats["valid_image_count"] * 100.0 / cam_stats["actual_raw_image_count"]
    ).round(2)

    cleaned_rows = []
    for _, row in raw_df.iterrows():
        cam_id = int(row["camera_id"])
        meta = CAMERA_CURATION[cam_id]
        ip_addr = str(row["ip_address"]).strip()
        ip_parts = ip_addr.split(".")
        ip_subnet = f"{ip_parts[0]}.{ip_parts[1]}.x.x" if len(ip_parts) >= 2 else "unknown"

        cleaned_rows.append(
            {
                "cam_id": cam_id,
                "location_th": meta["location_th"],
                "location_detail_th": meta["location_detail_th"],
                "location_en": meta["location_en"],
                "location_detail_en": meta["location_detail_en"],
                # Curation wins when peer QA corrected a swapped/misplaced pin.
                "lat": float(meta.get("lat", row["latitude"])),
                "lon": float(meta.get("lon", row["longitude"])),
                "district": meta["district"],
                "corridor": meta["corridor"],
                "pair_id": meta["pair_id"] if meta["pair_id"] is not None else "None",
                "pair_type": meta["pair_type"] if meta["pair_type"] is not None else "None",
                "direction": meta["direction"] if meta["direction"] is not None else "None",
                "ip_address": ip_addr,
                "ip_subnet": ip_subnet,
                "raw_info_image_count": int(row["image_count"]),
            }
        )

    cleaned_df = pd.DataFrame(cleaned_rows).merge(cam_stats, on="cam_id", how="left")
    cleaned_df = cleaned_df.sort_values("cam_id").reset_index(drop=True)
    return cleaned_df


def write_summary_and_readme(
    out_dir: Path,
    manifest_df: pd.DataFrame,
    meta_df: pd.DataFrame,
    elapsed_sec: float,
    overwrite_readme: bool = False,
) -> dict[str, Any]:
    """Generate cleaning_summary.json and write README.md only when missing or requested."""
    status_counts = manifest_df["status"].value_counts().to_dict()
    subtype_counts = manifest_df["error_subtype"].value_counts().to_dict()
    warning_counts = (
        manifest_df.loc[manifest_df["is_valid"], "quality_warning"]
        .value_counts()
        .to_dict()
    )

    daily_stats = (
        manifest_df.groupby("date", as_index=False)
        .agg(
            total=("filename", "count"),
            valid=("is_valid", "sum"),
            white_error=("is_white_error", "sum"),
            no_signal_error=("is_no_signal_error", "sum"),
            corrupt_color=("is_corrupt_color", "sum"),
            frozen=("is_frozen", "sum"),
        )
        .to_dict(orient="records")
    )

    top_faulty_cams = (
        meta_df.sort_values(["error_image_count", "cam_id"], ascending=[False, True])
        .head(10)[
            [
                "cam_id",
                "location_th",
                "ip_subnet",
                "actual_raw_image_count",
                "valid_image_count",
                "error_image_count",
                "white_error_count",
                "no_signal_error_count",
                "corrupt_color_count",
                "frozen_image_count",
                "valid_rate_pct",
            ]
        ]
        .to_dict(orient="records")
    )

    total_images = int(len(manifest_df))
    valid_images = int(manifest_df["is_valid"].sum())
    filtered_images = total_images - valid_images

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "elapsed_seconds": round(elapsed_sec, 2),
        "total_cameras": int(len(meta_df)),
        "total_raw_images": total_images,
        "total_valid_images": valid_images,
        "total_filtered_images": filtered_images,
        "valid_rate_pct": round(valid_images * 100.0 / total_images, 4),
        "status_counts": {k: int(v) for k, v in status_counts.items()},
        "error_subtype_counts": {k: int(v) for k, v in subtype_counts.items()},
        "quality_warning_counts_among_valid": {
            k: int(v) for k, v in warning_counts.items()
        },
        "daily_breakdown": daily_stats,
        "top_10_faulty_cameras": top_faulty_cams,
        "rules_applied": {
            "gate_1_white_error": "file_size < 2000 or brightness_mean == 255.0",
            "gate_2_no_signal_error": (
                "file_size == 8782 or (8700 <= file_size <= 8900 and "
                "127.5 <= brightness_mean <= 128.5 and contrast_std >= 111.0)"
            ),
            "gate_3_gray_pframe": "127.0 <= brightness_mean <= 132.0 and contrast_std < 16.0",
            "gate_3_green_screen": "(g_mean - r_mean > 40.0) and (g_mean - b_mean > 40.0)",
            "gate_4_frozen": "MAD == 0.0 compared against previous non-error frame of same cam_id",
            "gate_5_timestamp": "Parsed strictly from filename _YYYYMMDD_HHMMSS.jpg (never OSD)",
            "manual_excluded": f"{len(MANUAL_EXCLUDED_IMAGES)} filename(s) in MANUAL_EXCLUDED_IMAGES",
        },
    }

    (out_dir / "cleaning_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    daily_md_lines = [
        "| Date | Raw | Valid | White Error | No Signal | Corrupt Color | Frozen |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for d in daily_stats:
        daily_md_lines.append(
            f"| {d['date']} | {d['total']:,} | {d['valid']:,} | {int(d['white_error']):,} | "
            f"{int(d['no_signal_error']):,} | {int(d['corrupt_color']):,} | {int(d['frozen']):,} |"
        )

    cam_md_lines = [
        "| cam_id | Location | Subnet | Valid / Raw | White | No Signal | Corrupt Color | Frozen |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for c in top_faulty_cams:
        cam_md_lines.append(
            f"| {c['cam_id']} | {c['location_th']} | `{c['ip_subnet']}` | "
            f"{int(c['valid_image_count']):,} / {int(c['actual_raw_image_count']):,} ({c['valid_rate_pct']}%) | "
            f"{int(c['white_error_count'])} | {int(c['no_signal_error_count'])} | "
            f"{int(c['corrupt_color_count'])} | {int(c['frozen_image_count'])} |"
        )

    readme_path = out_dir / "README.md"
    if overwrite_readme or not readme_path.exists():
        readme_text = f"""# {out_dir.name} -- Cleaned Bangkok CCTV Dataset

Generated by [`clean_dataset_v1.py`](../00_data_cleaning_and_qa/src/clean_dataset_v1.py) based on `Info/Project Ideas.md` and `Info/EDA.md`.

## Summary Statistics

- **Total Cameras:** {summary['total_cameras']}
- **Total Raw Images:** {total_images:,}
- **Valid Clean Images Copied (`cctv_images/`):** {valid_images:,} ({summary['valid_rate_pct']:.2f}%)
- **Filtered Error/Frozen Images:** {filtered_images:,}
  - `white_error` (Gate 1): {status_counts.get('white_error', 0):,}
  - `no_signal_error` (Gate 2 -- Rainbow `gst-launch-0.10`): {status_counts.get('no_signal_error', 0):,}
  - `corrupt_color` (Gate 3): {status_counts.get('corrupt_color', 0):,} (`gray_pframe`: {subtype_counts.get('gray_pframe', 0):,}, `green_screen`: {subtype_counts.get('green_screen', 0):,})
  - `frozen` (Gate 4 -- `MAD == 0.0` vs previous non-error frame): {status_counts.get('frozen', 0):,}
  - `manual_excluded` (Peer QA visual sweep): {status_counts.get('manual_excluded', 0):,}

> **Notes on Data Findings vs Initial EDA:**
> - **Gate 2 (`no_signal_error`):** Camera `432` emits `8,782`-byte Rainbow frames (17 images), while Camera `1804` emits `8,783`-byte Rainbow frames (16 images) with identical statistical fingerprint (`mean ~ 128.07`, `std ~ 112.20`). Catching both yields all **33** Rainbow frames cleanly (and prevents `1804`'s 15 repeat Rainbow frames from inflating the `frozen` count from 553 to 568 or leaking 1 Rainbow frame into clean images).
> - **Gate 3 (`corrupt_color`):** Strict Gate 3 thresholds catch 11 severe Gray P-Frames and 8 severe Green Screens (`G - R > 40` and `G - B > 40`, preventing false positives on normal blue-lit night scenes). Valid images with mild/partial bottom-strip artifacts are retained in `cctv_images/` and tagged in `quality_warning` (`partial_gray_pframe` / `partial_green_screen`) inside `image_quality_manifest`.
> - **ASCII Filenames (`<cam_id>_<YYYYMMDD_HHMMSS>.jpg`):** Raw filenames contain Thai Unicode strings that fail `cv2.imread()` on Windows. Clean images use ASCII filenames while preserving the original `filename` and `raw_rel_path` in the manifest.

## Contents

- `cctv_images/<cam_id>/<cam_id>_<YYYYMMDD_HHMMSS>.jpg` -- {valid_images:,} verified valid images ready for YOLO / CV pipelines.
- `image_quality_manifest.parquet` & `image_quality_manifest.csv` -- Full audit log of all {total_images:,} raw images (Gate 1-5 flags, timestamps, pixel stats, MAD, `glare_ratio`, `quality_warning`).
- `cctv_info_cleaned.csv` & `cctv_info_cleaned.parquet` -- Cleaned 100-camera metadata (`cam_id`, `location_th`, `location_en`, `lat`, `lon`, `district`, `corridor`, `pair_id`, `pair_type`, `direction`, `ip_subnet`, plus per-camera quality counts).
- `cleaning_summary.json` -- Machine-readable summary metrics.

## Daily Breakdown

{chr(10).join(daily_md_lines)}

## Top 10 Cameras with Highest Filtered Frames

{chr(10).join(cam_md_lines)}
"""
        readme_path.write_text(readme_text, encoding="utf-8")
    else:
        print(f"  [NOTE] Preserved existing {readme_path} (use --overwrite-readme to regenerate)")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean Bangkok CCTV Dataset into Dataset_Clean_V1")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("Dataset"),
        help="Path to raw Dataset directory (default: Dataset)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("Dataset_Clean_V1"),
        help="Path to output cleaned directory (default: Dataset_Clean_V1)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=min(8, os.cpu_count() or 4),
        help="Number of parallel camera worker threads",
    )
    parser.add_argument(
        "--skip-copy",
        action="store_true",
        help="Generate manifests and cleaned metadata without copying image files",
    )
    parser.add_argument(
        "--overwrite-readme",
        action="store_true",
        help="Regenerate out_dir/README.md even if it already exists",
    )
    args = parser.parse_args()

    t0 = time.perf_counter()
    raw_images_root = args.raw_dir / "cctv_images" / "cctv_images"
    raw_info_path = args.raw_dir / "cctv_info.csv"
    clean_images_root = args.out_dir / "cctv_images"

    if not raw_images_root.exists():
        raise FileNotFoundError(f"Raw images folder not found: {raw_images_root}")
    if not raw_info_path.exists():
        raise FileNotFoundError(f"Raw metadata CSV not found: {raw_info_path}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    if not args.skip_copy:
        clean_images_root.mkdir(parents=True, exist_ok=True)

    cam_dirs = sorted(
        [d for d in raw_images_root.iterdir() if d.is_dir()],
        key=lambda p: int(p.name),
    )
    print(f"Found {len(cam_dirs)} camera folders in {raw_images_root}")
    print(f"Running Automated Image Quality Gate (5 Gates) using {args.workers} workers...")

    all_records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                process_camera_directory,
                cam_dir,
                raw_images_root,
                clean_images_root,
                not args.skip_copy,
            )
            for cam_dir in cam_dirs
        ]
        for idx, fut in enumerate(futures, start=1):
            all_records.extend(fut.result())
            if idx % 20 == 0 or idx == len(futures):
                print(f"  Processed {idx}/{len(futures)} cameras...")

    manifest_df = (
        pd.DataFrame(all_records)
        .sort_values(["cam_id", "timestamp"])
        .reset_index(drop=True)
    )

    manifest_parquet_path = args.out_dir / "image_quality_manifest.parquet"
    manifest_csv_path = args.out_dir / "image_quality_manifest.csv"
    manifest_df.to_parquet(manifest_parquet_path, index=False)
    manifest_df.to_csv(manifest_csv_path, index=False, encoding="utf-8-sig")

    meta_df = build_cleaned_metadata(raw_info_path, manifest_df)
    meta_csv_path = args.out_dir / "cctv_info_cleaned.csv"
    meta_parquet_path = args.out_dir / "cctv_info_cleaned.parquet"
    meta_df.to_csv(meta_csv_path, index=False, encoding="utf-8-sig")
    meta_df.to_parquet(meta_parquet_path, index=False)

    elapsed = time.perf_counter() - t0
    summary = write_summary_and_readme(
        args.out_dir,
        manifest_df,
        meta_df,
        elapsed,
        overwrite_readme=args.overwrite_readme,
    )

    print("\n=== Cleaning Complete ===")
    print(f"Elapsed: {summary['elapsed_seconds']}s")
    print(f"Total Raw Images: {summary['total_raw_images']:,}")
    print(f"Total Valid Images: {summary['total_valid_images']:,} ({summary['valid_rate_pct']:.2f}%)")
    print(f"Filtered Images: {summary['total_filtered_images']:,}")
    print(f"Status Breakdown: {summary['status_counts']}")
    print(f"Error Subtypes: {summary['error_subtype_counts']}")
    print(f"Quality Warnings (valid): {summary['quality_warning_counts_among_valid']}")
    print(f"Outputs written to: {args.out_dir.resolve()}")


if __name__ == "__main__":
    main()

