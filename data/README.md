# Local Data Directory

This directory is the local ROGII competition data entry point.

Raw data is intentionally not uploaded to GitHub because of its size. For local execution, place the complete competition data under `data/raw/`.

Expected local layout:

```text
data/
|-- raw/
|   |-- train/
|   |-- test/
|   |-- sample_submission.csv
|   `-- AI_wellbore_geology_prediction_task_en.pptx
|-- README.md
`-- .gitkeep
```

Inventory:

- Training horizontal CSV files: 773.
- Training typewell CSV files: 773.
- Training PNG files: 773.
- Visible test horizontal CSV files: 3.
- Visible test typewell CSV files: 3.
- Sample submission rows: 14,151.

If the raw data is absent in a fresh environment, regenerate it after accepting the competition rules and authenticating Kaggle locally:

```bash
python scripts/download_data.py
```

Expected local layout after download:

```text
data/
|-- rogii-wellbore-geology-prediction.zip
`-- raw/
    |-- train/
    |-- test/
    |-- sample_submission.csv
    `-- AI_wellbore_geology_prediction_task_en.pptx
```
