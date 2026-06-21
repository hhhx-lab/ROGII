<div align="center">

# ROG-II-

**An engineering workspace for reproducible wellbore geology prediction.**

![Kaggle Competition](https://img.shields.io/badge/Kaggle-Competition-20BEFF?style=flat-square)
![Task](https://img.shields.io/badge/Task-TVT%20Prediction-7c3aed?style=flat-square)
![Data](https://img.shields.io/badge/Data-Horizontal%20Wells-059669?style=flat-square)
![Workflow](https://img.shields.io/badge/Workflow-Notebook%20Only-111827?style=flat-square)

`kaggle competitions download -c rogii-wellbore-geology-prediction`

</div>

> Build a defensible TVT prediction workflow, not just a one-off Kaggle submission.

This repository is the working base for the Kaggle competition **ROGII - Wellbore Geology Prediction**. The goal is to predict **TVT (True Vertical Thickness)** for horizontal well evaluation zones using trajectory, log, and vertical reference data, with a workflow strong enough to compete for the top of the leaderboard.

The competition is a notebook-only code contest with RMSE scoring. Kaggle exposes the public description, the data bundle, and the submission format through the competition page. This repo treats that setup as an engineering problem: define the data contracts, build a validation loop that mimics hidden wells, keep a simple baseline as a control, and only promote models that improve in a measurable and explainable way.

The current workspace already contains a full local submission loop:

- tail-slope baseline;
- geometry residual model;
- route-aware Part 3 correction diagnostics;
- blend / postprocess / final submission scripts;
- a Kaggle notebook skeleton;
- a generated `submission.csv`.

## Competition Brief

ROGII asks participants to build a model for drilling-time geology prediction. The data includes horizontal well trajectories, geological surfaces, well logs, typewell reference logs, and per-well visualizations. The hidden test set replaces the visible sample data when Kaggle re-runs a submission.

## Engineering Method

The project direction is deliberately practical:

- use `TVT_input` continuation as the control baseline;
- validate on the hidden rows already present in training wells before trusting any model;
- add GR, geometry, and typewell features only when they improve the baseline under cross-validation;
- use Part 3 as a gated correction layer on top of baseline, not as a separate competing model;
- report errors by well and by failure type, not only by one aggregate RMSE;
- keep the final notebook deterministic and runnable with Kaggle internet disabled;
- treat each leaderboard submission as a tracked experiment with a local CV score and a hypothesis.

## What You Get

| Item | Details |
|---|---|
| Competition summary | A concise, local README for the Kaggle task |
| Data download path | A repeatable Kaggle download command and script |
| Working data folder | Local files under `data/` after download |
| Project hygiene | Large data stays out of git history |
| Submission loop | Local scripts that end in `submission.csv` |

## Capability Matrix

| Capability | What it covers | Why it matters |
|---|---|---|
| Competition overview | Problem, score, timeline, and constraints | Gives the team one shared source of truth |
| Data layout | `data/train/`, `data/test/`, file types, and targets | Makes the first preprocessing pass easier |
| Download workflow | Kaggle web/API path plus local script | Turns access into a repeatable step |
| Model plan | Baseline, residual, GR/typewell, ensemble | Shows how the project will improve step by step |
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

The working data is organized under `data/train/` and `data/test/` folders. Each well is identified by an 8-character hash. Public preview data includes:

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
|-- notebooks/
|-- scripts/
|   |-- download_data.py
|   |-- blend_predictions.py
|   |-- postprocess_predictions.py
|   `-- make_submission.py
|-- reports/
`-- submission.csv
```

## Boundaries

This repo keeps the competition data local. The raw bundle is too large for git, so the repository only tracks the downloader and the working notes. Kaggle access still depends on an authenticated account that has accepted the competition rules.

The helper in `scripts/data_paths.py` resolves the current `data/` layout and also tolerates an older `data/raw/` layout if it still appears in another environment.

## Source

- [Kaggle competition page](https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction)
- [Kaggle data page](https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction/data)
