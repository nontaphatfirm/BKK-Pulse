# Task 01 Source Directory (`01_scraping_apis/src/`)

See full technical specification in [`../GOAL.md`](../GOAL.md).

## Module Architecture

```text
01_scraping_apis/src/
├── fetch_weather_air_poi.py   # Entrypoint: Open-Meteo weather + air quality (one batched request each),
│                              # joins 500m POI counts, exports data/weather_air_poi.parquet
└── fetch_pois_overpass.py     # Single-BBox Overpass QL query + 500m Haversine matcher (imported by the entrypoint)
```

## Run

```bash
python 01_scraping_apis/src/fetch_weather_air_poi.py            # uses cached API responses when present
python 01_scraping_apis/src/fetch_weather_air_poi.py --refresh  # re-download weather, air quality and OSM POIs
```

## Outputs

| Path | Description |
| :--- | :--- |
| `data/weather_air_poi.parquet` | 16,800 rows (100 cameras x 168 hours), 14 columns, zero nulls |
| `data/raw_weather_air/weather.json`, `air_quality.json` | Cached Open-Meteo responses |
| `data/raw_osm/bkk_pois.json` | Cached Overpass response (transit nodes + school/mall/hospital nodes, ways and relations) |
| `data/scraping_summary_01.json` | Row/null counts and max POI counts |

Then run `02_scraping_traffy_playwright/src/merge_external_dataset.py` to rebuild `data/external_weather_poi.parquet`.
