# Task 05 Source Directory (`05_ds_ml_forecasting/src/`)

See full technical specification in [`../GOAL.md`](../GOAL.md).

## Recommended Module Architecture

```text
05_ds_ml_forecasting/src/
├── build_lag_dataset.py            # Gap-safe lag & lead (t+30m) feature engineering
├── train_lgbm_forecaster.py        # Chronological split, LightGBM training & Naive evaluation
└── compute_shap_explanations.py    # TreeExplainer SHAP summary & feature attribution export
```
