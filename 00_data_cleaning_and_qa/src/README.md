# Task 00 Source Directory (`00_data_cleaning_and_qa/src/`)

See full technical specification in [`../GOAL.md`](../GOAL.md).

## Scripts

- [`clean_dataset_v1.py`](clean_dataset_v1.py): Executes the 5-stage Automated Image Quality Gate across all 61,319 raw images, copies valid ASCII-renamed images (`60,210` files) into `Dataset_Clean_V1/cctv_images/`, and builds `cctv_info_cleaned.parquet` / `.csv` and `image_quality_manifest.parquet` / `.csv`.

## CLI Usage

```bash
# Full run (image quality gate + ASCII copy + metadata cleansing)
python 00_data_cleaning_and_qa/src/clean_dataset_v1.py

# Fast metadata-only update (after editing CAMERA_CURATION during peer QA; preserves custom README.md & CLEANING_CHANGELOG.md)
python 00_data_cleaning_and_qa/src/clean_dataset_v1.py --skip-copy
```

> **Note:** Team members reviewing Batches 1–6 only need to edit `clean_dataset_v1.py`, [`../../Dataset_Clean_V1/CLEANING_CHANGELOG.md`](../../Dataset_Clean_V1/CLEANING_CHANGELOG.md), and [`../CAMERA_AUDIT_CHECKLIST.md`](../CAMERA_AUDIT_CHECKLIST.md) on a personal branch and open a **PR into `main`** (never push directly to `main` or upload files to Google Drive). Once all 6 PRs are merged, the maintainer runs `clean_dataset_v1.py`, validates [`../../DATA_CONTRACT.md`](../../DATA_CONTRACT.md) with `python run_pipeline.py --check-contract`, and syncs the final `V2.0` release to Google Drive once.
