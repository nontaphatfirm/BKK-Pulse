# Task 00 Source Directory (`00_data_cleaning_and_qa/src/`)

See full technical specification in [`../GOAL.md`](../GOAL.md).

## Scripts

- [`clean_dataset_v1.py`](clean_dataset_v1.py): Executes the 5-stage Automated Image Quality Gate across all 61,319 raw images, copies valid ASCII-renamed images (`60,210` files) into `Dataset_Clean_V1/cctv_images/`, and builds `cctv_info_cleaned.parquet` / `.csv` and `image_quality_manifest.parquet` / `.csv`.

## CLI Usage

```bash
# Full run (image quality gate + ASCII copy + metadata cleansing)
python 00_data_cleaning_and_qa/src/clean_dataset_v1.py

# Fast metadata-only update (after editing CAMERA_CURATION during peer QA)
python 00_data_cleaning_and_qa/src/clean_dataset_v1.py --skip-copy
```
