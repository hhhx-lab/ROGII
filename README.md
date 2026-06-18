<div align="center">

# ROG-II-

**A Kaggle competition workspace for wellbore geology prediction.**

![Kaggle Competition](https://img.shields.io/badge/Kaggle-Competition-20BEFF?style=flat-square)
![Task](https://img.shields.io/badge/Task-TVT%20Prediction-7c3aed?style=flat-square)
![Data](https://img.shields.io/badge/Data-Horizontal%20Wells-059669?style=flat-square)
![Workflow](https://img.shields.io/badge/Workflow-Notebook%20Only-111827?style=flat-square)

`kaggle competitions download -c rogii-wellbore-geology-prediction`

</div>

> Build models that help predict geology along a horizontal wellbore.

This repository is the working base for the Kaggle competition **ROGII - Wellbore Geology Prediction**. The goal is to predict **TVT (True Vertical Thickness)** for horizontal well evaluation zones using trajectory, log, and vertical reference data.

The competition is a notebook-only code contest with RMSE scoring. Kaggle exposes the public description, the data bundle, and the submission format through the competition page. This repo keeps the brief, the download path, and the project layout together so the next modeling step starts fast.

## Competition Brief

ROGII asks participants to build a model for drilling-time geology prediction. The data includes horizontal well trajectories, geological surfaces, well logs, typewell reference logs, and per-well visualizations. The hidden test set replaces the visible sample data when Kaggle re-runs a submission.

## What You Get

| Item | Details |
|---|---|
| Competition summary | A concise, local README for the Kaggle task |
| Data download path | A repeatable Kaggle download command and script |
| Working data folder | Local files under `data/` after download |
| Project hygiene | Large data stays out of git history |

## Capability Matrix

| Capability | What it covers | Why it matters |
|---|---|---|
| Competition overview | Problem, score, timeline, and constraints | Gives the team one shared source of truth |
| Data layout | Train/test directories, file types, and targets | Makes the first preprocessing pass easier |
| Download workflow | Kaggle web/API path plus local script | Turns access into a repeatable step |
| Repo hygiene | Ignores giant artifacts and temp files | Keeps the repo practical to clone and review |

## Workflow

```text
Kaggle competition page
  |
  v
Read public problem statement and data schema
  |
  v
Download competition bundle locally
  |
  v
Inspect train/test files and sample submission
  |
  v
Build features, validate RMSE, submit notebooks
```

## Key Rules

- Metric: root mean squared error (RMSE).
- Submission format: `id,tvt`.
- Submission channel: Kaggle Notebooks only.
- Runtime limits: CPU <= 9 hours, GPU <= 9 hours.
- Internet access: disabled in submissions.
- External data: freely and publicly available data is allowed.

## Data Layout

The competition bundle is organized into `train/` and `test/` folders. Each well is identified by an 8-character hash. Public preview data includes:

- `__horizontal_well.csv` for trajectory and log data;
- `__typewell.csv` for vertical reference logs;
- `.png` visualizations for training wells;
- `sample_submission.csv` for the target format.

## Local Download

```bash
python -m venv .venv
.venv/bin/pip install --upgrade pip kaggle
kaggle auth login
python scripts/download_data.py
```

## Repository Layout

```text
.
|-- README.md
|-- data/
|-- scripts/
|   `-- download_data.py
`-- .gitignore
```

## Boundaries

This repo keeps the competition data local. The raw bundle is too large for git, so the repository only tracks the downloader and the working notes. Kaggle access still depends on an authenticated account that has accepted the competition rules.

## Source

- [Kaggle competition page](https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction)
- [Kaggle data page](https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction/data)
