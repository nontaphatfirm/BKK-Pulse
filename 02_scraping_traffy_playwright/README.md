# Task 02 — Traffy Fondue complaints (`02_scraping_traffy_playwright`)

Fetches every BMA Traffy Fondue complaint in the study window, matches each one
to its nearest CCTV camera, and produces the Traffy columns of Table 4.

Entry points:

| File | Role |
|---|---|
| `src/scrape_traffy_playwright.py` | Interactive Playwright run. Captures XHRs and screenshots. Rubric evidence only, not the data source. |
| `src/fetch_traffy_geojson.py` | Calls the public PostgREST feed directly and builds the parquet outputs. This is what the data comes from. |
| `src/merge_external_dataset.py` | Computes the trailing 7-day counts and joins them onto Task 01's hourly grid, writing `data/external_weather_poi.parquet` (Table 4). |

`GOAL.md` is the course specification. This file documents what the code
actually produces.

## Outputs

### `data/traffy_complaints_near_cctv.parquet` — 70,822 rows x 10 columns

One row per complaint that is within 1,000 m of at least one camera.

| Column | Type | Meaning | Example |
|---|---|---|---|
| `ticket_id` | `str` | Traffy ticket id, unique in the window | `2026-93M2TH` |
| `nearest_cam_id` | `int64` | Camera id from `Dataset_Clean_V1/cctv_info_cleaned.parquet` | `11` |
| `distance_m` | `float64` | Haversine metres from the complaint to that camera, always `<= 1000` | `702.8146` |
| `timestamp` | `datetime64[us]` | Report time as published by the feed (Bangkok local clock, no tz attached) | `2026-05-01 08:16:16` |
| `problem_type` | `str` | Derived bucket, `flood` / `traffic` / `other` | `other` |
| `description` | `str` | Citizen free text | `ขอบฝาท่อชำรุดบริเวณแยกดินแดง` |
| `status` | `str` | Traffy state at crawl time, not updated afterwards | `เสร็จสิ้น` |
| `lat` | `float64` | **Complaint** latitude, WGS84 | `13.75955` |
| `lon` | `float64` | **Complaint** longitude, WGS84 | `100.54603` |
| `type_raw` | `str` | Raw Traffy type label, one or more comma-separated tags | `อุปกรณ์ชำรุด` |

`lat` / `lon` are the reported event location, not the camera. Two consequences
follow. The reported point is what `distance_m` is measured to, and the point
stays meaningful if the matching rule ever changes, so a radius-based count can
be recomputed from this file without re-crawling.

`description` is cut at 255 characters by the source database (`varchar(255)`).
About 23% of rows hit that limit mid-word. The truncation happens upstream and
is not recoverable from the feed.

### `data/traffy_camera_counts.parquet` — 100 rows x 7 columns

One row per camera, zero-filled, so every camera id in `cctv_info_cleaned`
appears even when it has no complaints.

| Column | Type | Meaning |
|---|---|---|
| `cam_id` | `int64` | Camera id |
| `traffy_complaint_count` | `int64` | All matched complaints |
| `traffy_flood_count` | `int64` | Matched complaints bucketed `flood` |
| `traffy_traffic_count` | `int64` | Matched complaints bucketed `traffic` |
| `traffy_complaint_count_7d` | `int64` | Same, restricted to 2026-08-25 .. 2026-08-31 |
| `traffy_flood_count_7d` | `int64` | Same |
| `traffy_traffic_count_7d` | `int64` | Same |

The three `_7d` columns are computed here but **not carried into Table 4**.
`merge_external_dataset.py` selects the 17 contract columns and drops them.

### `data/scraping_summary_02.json`

Run report. Repeat runs should be diffed against this rather than against the
parquet.

| Key | Meaning |
|---|---|
| `window_start`, `window_end` | Requested window |
| `actual_first_timestamp`, `actual_last_timestamp` | Observed bounds after the crawl |
| `complaints_fetched` | Rows citywide in the window before matching |
| `complaints_within_1000m` | Rows that survived the radius filter |
| `category_counts_all`, `category_counts_matched` | Bucket totals before and after matching |
| `cameras_with_any_complaint`, `cameras_with_flood_complaint` | Coverage spread |
| `week_complaints_within_1000m` | Size of the `_7d` slice |
| `match_radius_m` | Radius actually used |
| `complete` | `true` only if every cached page chain is intact and the segments cover the window |
| `fetch` | `termination` (`empty_page` / `max_pages` / `error_prefix` / `cache`), `pages`, `terminal_offset` |
| `coverage` | `days_in_window`, `days_with_records`, `days_missing`, `hours_in_window`, `empty_hours`, `largest_gap_hours`, `complete`. Advisory only; it no longer gates the build |
| `unmatched_type_tags` | Raw tags missing from `category_map.json`, with counts. `{}` means the map covers the cache |
| `dropped` | Features discarded this run: `no_id`, `no_coords`, `null_timestamp`, `null_coords` |
| `cache_segments` | One per crawl window: `window_start`, `window_end`, `pages`, `offsets`, `direction`, `complete`, `first_ts`, `last_ts`, `covered` |
| `coverage_gaps` | ISO pairs of the parts of the window no segment covers. Empty means complete |

### `data/traffy_provenance.json`

Written by every build that produces parquet outputs. It carries the window,
build time, git commit, `complete`, termination, page count, the covered segment
intervals, coverage, row count, drop counters, the `--reason` on a partial build,
and the sha256 of both parquet outputs.

The same block, minus the output hashes, is written into the Arrow schema
metadata of `traffy_complaints_near_cctv.parquet` and Table 4 under the key
`bkk_pulse_provenance`, so a reader holding one file can tell a complete build
from a truncated one. `run_pipeline.py --check-contract` fails when the file says
`complete: false` and warns when it is missing.

### `data/traffy_fetch_progress.json`

Written by `--fetch-only`. Records the same completeness fields for a cache fill
that has not yet produced parquet outputs.

### `data/external_weather_poi.parquet` — Table 4

Produced by `merge_external_dataset.py`, 16,800 rows (100 cameras x 168 hourly
slots) x 17 columns. The Traffy contract columns are

| Column | Semantics |
|---|---|
| `traffy_complaint_count` | Complaints within 1,000 m of the camera with `timestamp > row.timestamp - 7 days` and `timestamp <= row.timestamp` |
| `traffy_flood_count` | Same window, bucket `flood` |
| `traffy_traffic_count` | Same window, bucket `traffic` |

Each value is computed per `(cam_id, timestamp)`, never broadcast, and never
counts a complaint after the row's own hour, so the column is safe as a feature
for that hour. `sum(traffy_complaint_count)` over the table is 464,229.

The first row of the week counts complaints from 2026-08-18 onward, which is
inside the crawl window, so no row is zero padded. The largest value in the
table is 193, and 373 of the 16,800 rows are zero.

`data/traffy_camera_counts.parquet` keeps the six-month lifetime totals and the
`_7d` slice. A consumer that wants a structural flood indicator without a time
limit must read that file; Table 4 no longer carries a lifetime figure.

## Matching rule

1. Parse each feature to `(ticket_id, lat, lon, timestamp, type_raw, description, status)`.
2. Dedupe by `ticket_id`, first occurrence wins. Repeated ids across overlapping
   pages are expected and were verified to agree.
3. Drop rows with no timestamp or no coordinates, counted under `dropped`.
4. Drop anything outside `[start, end]`.
5. Classify to `flood` / `traffic` / `other`.
6. Attach the nearest camera by Haversine distance over all 100 cameras.
7. Keep rows with `distance_m <= 1000`.

Assignment is **nearest camera only**. A complaint belongs to exactly one
camera, so counts add up to the row count. The cost is that two cameras under
100 m apart (21 such pairs) split shared traffic arbitrarily. Counts per camera
in a pair are not comparable to each other; their sum is.

## Classification

`classify()` splits `type_raw` on commas, looks every tag up in
`src/category_map.json`, and takes flood over traffic over the map's default.

| Bucket | Tags |
|---|---|
| `flood` | `น้ำท่วม`, `น้ำท่วมขัง`, `ท่อระบายน้ำ`, `อุทกภัย` |
| `traffic` | `ผิดกฎจราจร`, `ถนน`, `อุบัติเหตุ`, and the longer road and traffic labels the map lists, such as `ภัยทางถนน` and `ระเบียบจราจร - จอดรถ` |
| `other` | every other tag, plus the explicit `default` |

The map holds all 98 tags observed in the cache. A tag missing from it falls to
the default and is listed with its count under `unmatched_type_tags`, so a new
label surfaces instead of silently changing a bucket. The current split over the
matched 70,822 rows is `other` 49,219, `traffic` 19,267, `flood` 2,336, identical
to the old substring rule on this data. `ผิดกฎจราจร` (illegal parking, 59% of
traffic) drives the traffic bucket. Whether it belongs there is an open decision.

`type_raw` can hold several comma-joined tags. Flood wins, so `อื่นๆ,น้ำท่วม`
lands in `flood`.

`src/audit_categories.py` regenerates `artifacts/type_raw_counts.csv` and
`artifacts/type_tag_counts.csv` from the cache. That is how the map was built
and how it gets rechecked after a new crawl.

## Page cache

`data/raw_traffy_cache/pages/<start>_<end>_<offset:07d>.json.gz`, one gzipped
JSON array per API page after compaction. Gitignored; it is delivered
separately as a heavy-data archive.

- Writes go to `.tmp` and are renamed, so an interrupted crawl cannot leave a
  half-written page.
- A page is reused when present. `--refresh` re-requests it.
- `--combine-cache` rebuilds outputs from the cache alone, no network.
- Only pages whose filename window intersects `[start, end]` are read, so a
  stray page cannot leak records into an unrelated build.
- A page filename that does not match `<date>_<date>_<offset>.json.gz` is
  ignored entirely.

The cache is a mosaic, not one crawl. The current build combines seven complete
windows, five months plus two single-day backfills, with the newest 46 pages of
a six-month run that a 503 cut short. Because the feed returns newest first,
those 46 pages hold 2026-09-25 13:18 through 2026-10-31, and the complete
windows hold everything before it.

`data/raw_traffy_cache/windows.json` is rewritten on every build. It lists each
segment with its page count, offsets, direction, per-page sha256, covered
interval, and any gaps. It is not the gate. The gate always rescans the pages,
so a stale or missing manifest cannot make a bad cache look complete. The file
belongs in the cache archive.

### Where the cache ships

The cache and the parquet outputs are gitignored, so they travel as one archive:

- Drive, folder `BKK-Pulse`:
  <https://drive.google.com/drive/folders/1_ehYKZTxllg0CvE5ejynhTICYKjwAxb2>
- File `BKK-Pulse_Traffy_heavy_data_2026-11-18.zip`, 43.9 MB,
  MD5 `406aa9b978058f32be1590ef3d7ff1ba`

Contents, paths anchored at the repo root so it extracts in place:

```text
BKK-Pulse/
└── data/
    ├── raw_traffy_cache/pages/*.json.gz              190 pages
    ├── raw_traffy_cache/windows.json                 segment manifest
    └── traffy_complaints_near_cctv.parquet           70,822 rows
```

```bash
unzip -q ~/Downloads/BKK-Pulse_Traffy_heavy_data_2026-11-18.zip -d ~/coding
```

The earlier `BKK-Pulse_Traffy_heavy_data_2026-11-13.zip` in the same folder is
superseded. It has 188 pages, the 13.6 h gap on 2026-09-25, V1.0 camera pins and
70,881 rows. Do not mix it with the current build.

The `2026-11-18` zip predates `windows.json` and the provenance stamp. Both are
regenerated from the pages by `--combine-cache`, so the archive stays usable as
it is; add the manifest on the next repack.

### Completeness guard

A truncated crawl used to produce a full-looking parquet. It now fails instead.

The gate reads the cache, not a timestamp heuristic. `scan_cache` groups pages
by their crawl window and checks each group's offset chain. The first page must
be at offset 0, and every later offset must equal the previous offset plus that
page's row count. A broken chain is a hole, and the error names the missing
offset.

Each intact group becomes a segment with a covered interval:

| Segment | Covered |
|---|---|
| ended on an empty page | its whole requested window |
| cut short, newest first | `first_ts` to the window end |
| cut short, oldest first | the window start to `last_ts` |

The build passes when the union of covered intervals leaves no gap in
`[start, end]`. Direction is read from the pages, because the truncated segment
is only trustworthy at the end its ordering guarantees.

The 2026-09-25 hole is still caught. That day comes from two crawls, and with
the three backfill pages missing the seam shows up as a 13.30 h gap from
2026-09-25 00:00 to 13:18. The original truncation measured 13.52 h.

The old 6-hour threshold is still computed in `coverage` and now only warns.
It was measured once on one window. A genuinely quiet night could exceed it, and
a valid crawl should not fail on that.

A failure raises `IncompleteWindow` and writes nothing. `--allow-partial` builds
anyway, but it requires `--reason "<text>"`. The flag alone exits 2, and the
reason is written into `data/traffy_provenance.json` and the build output.

## Running

```bash
PY=.venv/bin/python

# Fill the cache only
$PY 02_scraping_traffy_playwright/src/fetch_traffy_geojson.py --fetch-only

# One day
$PY 02_scraping_traffy_playwright/src/fetch_traffy_geojson.py \
    --fetch-only --start 2026-09-25 --end 2026-09-25

# Rebuild outputs from the cache, then table 4
$PY 02_scraping_traffy_playwright/src/fetch_traffy_geojson.py --combine-cache
$PY 02_scraping_traffy_playwright/src/merge_external_dataset.py
$PY run_pipeline.py --check-contract

# Deliberately accept an incomplete window
$PY 02_scraping_traffy_playwright/src/fetch_traffy_geojson.py --combine-cache \
    --allow-partial --reason "2026-09-25 backfill not fetched yet"

# Rebuild the type label audit from the cache
$PY 02_scraping_traffy_playwright/src/audit_categories.py
```

Costs about 10 s per page in `_request_page`, deliberately, because sustained
bursts return 503. The window needs roughly 190 pages, so a cold full crawl is
upwards of half an hour. Cached rebuilds take seconds.

The API facts in the module docstring were verified 2026-11-12 and still hold.
Three matter most: `p_limit` caps at 2000, `p_offset` paginates, and the
response `total` undercounts, so the loop runs until an empty page rather than
trusting `total`.

## Current snapshot (2026-11-18)

Built from the V2.0 locked camera table plus the 2026-09-25 backfill.

| Metric | Value |
|---|---:|
| Window | 2026-05-01 .. 2026-10-31 |
| Cache pages | 190 |
| Complaints citywide in window | 356,513 |
| Matched within 1,000 m | 70,822 |
| Cameras with any complaint | 100 |
| Cameras with a flood complaint | 94 |
| `_7d` slice (2026-08-25 .. 08-31) | 2,513 |
| Days covered | 184 / 184 |
| Cache segments | 8, all chains intact |
| Empty hours | 9 of 4,416 |
| Largest timestamp gap | 3.05 h |
| Table 4 rows | 16,800 x 17 |
| Table 4 complaint sum | 464,229 |
| Largest trailing 7-day count | 193 |
| Cameras with a nonzero trailing count | 99 |

## Known limitations

- **Nearest-only assignment.** Paired cameras under 100 m split shared complaints
  arbitrarily. Switching to a radius-based count is an open decision.
- **Trailing counts are an as-of snapshot.** A complaint logged after its hour
  appears only in later rows. Late status changes and back-filled tickets do not
  propagate, the same as the rest of the crawl.
- **Lifetime totals are camera-level only.** Task 04 wants a structural flood
  indicator without a time limit, so it must read `traffy_camera_counts.parquet`.
  Table 4 carries no lifetime figure.
- **`ผิดกฎจราจร` inside `traffic`.** Open decision.
- **Description truncation** at 255 characters is upstream and permanent.
- **Status is a snapshot.** `status` reflects the feed at crawl time and is not
  refreshed by a later `--combine-cache`.
- **National feed.** About 23% of every page sits outside the Bangkok bounding
  box and is filtered out after download. Those rows were already paid for in
  crawl time and page size.
