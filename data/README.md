# Local Data Directory

This directory is tracked as a placeholder only.

Do not commit Kaggle competition data here. After accepting the competition rules and authenticating Kaggle locally, regenerate the local data with:

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
