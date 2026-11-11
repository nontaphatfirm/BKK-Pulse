# Task 06 Source Directory (`06_bi_dashboard/src/`)

See full technical specification in [`../GOAL.md`](../GOAL.md).

## Recommended Module Architecture

```text
06_bi_dashboard/src/
├── app.py                          # Main Streamlit entrypoint (streamlit run 06_bi_dashboard/src/app.py)
├── data_loader.py                  # Cached Parquet/DuckDB loaders with sample-dataset fallback
└── tabs/
    ├── tab1_live_pulse_map.py      # Interactive map of 100 cameras, 30-min alerts & inspector
    ├── tab2_corridor_and_tidal.py  # Space-time heatmaps, 6 footbridge pairs & K-Means archetypes
    ├── tab3_weather_and_ml.py      # Rain recovery, What-If simulator & LightGBM SHAP
    └── tab4_network_health.py      # BMA CCTV Network Health Audit (Day-1 ready from Dataset_Clean_V1/)
```
