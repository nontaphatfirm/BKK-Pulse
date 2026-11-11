# Task 01 Source Directory (`01_scraping_apis/src/`)

See full technical specification in [`../GOAL.md`](../GOAL.md).

## Recommended Module Architecture

```text
01_scraping_apis/src/
├── fetch_weather_openmeteo.py      # Source 1: Hourly weather archive ingestion
├── fetch_pois_overpass.py          # Source 2: Single-BBox Overpass QL + 500m Haversine matcher
├── fetch_air_quality_openmeteo.py  # Source 3: Hourly PM2.5, NO2, CO ingestion
└── build_weather_air_poi.py        # Pipeline runner exporting data/weather_air_poi.parquet
```
