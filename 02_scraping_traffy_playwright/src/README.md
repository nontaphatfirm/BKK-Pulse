# Task 02 Source Directory (`02_scraping_traffy_playwright/src/`)

Data contract, matching rule and run instructions: [`../README.md`](../README.md).
Course specification: [`../GOAL.md`](../GOAL.md).

## Modules

```text
02_scraping_traffy_playwright/src/
├── audit_categories.py         # Type label inventory and bucket audit from the page cache
├── category_map.json           # Raw Traffy tag -> flood / traffic / other
├── fetch_traffy_geojson.py     # PostgREST crawl, cache segment scan, matching, parquet outputs
├── scrape_traffy_playwright.py # Interactive browser run, XHR capture (rubric evidence)
└── merge_external_dataset.py   # Trailing 7-day Traffy counts -> data/external_weather_poi.parquet
```
