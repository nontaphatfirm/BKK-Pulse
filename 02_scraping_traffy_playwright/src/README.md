# Task 02 Source Directory (`02_scraping_traffy_playwright/src/`)

See full technical specification in [`../GOAL.md`](../GOAL.md).

## Module Architecture

```text
02_scraping_traffy_playwright/src/
├── scrape_traffy_playwright.py   # Interactive Playwright: district + category filters, XHR capture, screenshots
├── fetch_traffy_geojson.py       # Full May-Oct backfill via get_bkk_geojson_feed + 1 km nearest-camera matching
└── merge_external_dataset.py     # Joins Task 01 & Task 02 into data/external_weather_poi.parquet
```

## Run (from the project root)

```bash
pip install -r requirements.txt && python -m playwright install chromium
python 02_scraping_traffy_playwright/src/scrape_traffy_playwright.py
python 02_scraping_traffy_playwright/src/fetch_traffy_geojson.py                  # fetch (slow, API is throttled) + build
python 02_scraping_traffy_playwright/src/fetch_traffy_geojson.py --combine-cache  # rebuild from cached pages only
python 02_scraping_traffy_playwright/src/merge_external_dataset.py               # needs data/weather_air_poi.parquet from Task 01
```

Both fetch modes keep only complaints with `--start <= timestamp < --end + 1 day` (the feed can return out-of-window pages). Re-run `--combine-cache` and the merge whenever camera coordinates in `Dataset_Clean_V1/cctv_info_cleaned.parquet` change, since nearest-camera assignment depends on them.

## Outputs

| Path | Description |
| :--- | :--- |
| `data/traffy_complaints_near_cctv.parquet` | Deliverable 1: 70,822 complaints assigned to their single nearest camera at `<= 1 km` (May-Oct 2026; each complaint counted once) |
| `data/traffy_camera_counts.parquet` | Per-camera 6-month and 7-day (`*_7d`) flood / traffic / total counts |
| `data/traffy_hourly_week.parquet` | Hourly in-week complaint counts per camera (`*_1h`), same key as Table 4 |
| `data/external_weather_poi.parquet` | Deliverable 2: canonical Table 4 (16,800 rows, 17 columns) |
| `data/scraping_summary_02.json`, `data/scraping_summary_merged.json` | Run summaries |
| `artifacts/` | Playwright screenshots, intercepted complaints, network capture, interaction log |
| `data/raw_traffy_cache/pages/` | Cached API pages (gitignored; regenerate with the fetch command) |
