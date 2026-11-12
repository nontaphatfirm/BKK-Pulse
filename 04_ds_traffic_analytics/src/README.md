# Task 04 Source Directory (`04_ds_traffic_analytics/src/`)

See full technical specification in [`../GOAL.md`](../GOAL.md).

## Recommended Module Architecture

```text
04_ds_traffic_analytics/src/
├── compute_congestion_index.py     # Module 2.1: PCU & adaptive P95 Congestion Index (0-100)
├── analyze_corridor_and_tidal.py   # Module 2.2: Corridor heatmaps & 6-footbridge-pair tidal flow
├── analyze_rain_recovery.py        # Module 2.3: CCTV image-processing rain/wet-road detection & recovery time
└── cluster_road_archetypes.py      # Module 2.4: K-Means (k=4), PCA 2D projection & POI profiling
```
