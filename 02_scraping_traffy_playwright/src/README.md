# Task 02 Source Directory (`02_scraping_traffy_playwright/src/`)

See full technical specification in [`../GOAL.md`](../GOAL.md).

## Recommended Module Architecture

```text
02_scraping_traffy_playwright/src/
├── scrape_traffy_playwright.py     # Interactive Playwright browser automation & XHR capture
├── match_traffy_spatial.py         # Haversine matching (<= 500m/1km) to 100 CCTV cameras
└── merge_external_dataset.py       # Joins Task 01 & Task 02 into data/external_weather_poi.parquet
```
