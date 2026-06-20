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

## Competition Brief

ROGII asks participants to build a model for drilling-time geology prediction. The data includes horizontal well trajectories, geological surfaces, well logs, typewell reference logs, and per-well visualizations. The hidden test set replaces the visible sample data when Kaggle re-runs a submission.

## Engineering Method

The project direction is deliberately practical:

- use `TVT_input` continuation as the control baseline;
- simulate hidden intervals from training wells before trusting any model;
- add GR, trajectory, and typewell features only when they beat the baseline under cross-validation;
- report errors by well and by failure type, not only by one aggregate RMSE;
- keep the final notebook deterministic and runnable with Kaggle internet disabled.
- treat each leaderboard submission as a tracked experiment with a local CV score and a hypothesis.

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
- Project rule checklist: [`docs/kaggle_rules_checklist.md`](docs/kaggle_rules_checklist.md).

## Data Layout

The competition bundle is organized into `train/` and `test/` folders. Each well is identified by an 8-character hash. Public preview data includes:

- `__horizontal_well.csv` for trajectory and log data;
- `__typewell.csv` for vertical reference logs;
- `.png` visualizations for training wells;
- `sample_submission.csv` for the target format.

Raw data and PPTX findings that affect the modeling plan are documented in [`reports/data_raw_review.md`](reports/data_raw_review.md).

## Local Download

```bash
python -m venv .venv
.venv/bin/pip install --upgrade pip kaggle
kaggle auth login
python scripts/download_data.py
```

## Reproduce Local Outputs

`outputs/` is intentionally not committed. It contains reproducible intermediate artifacts, including one row-level prediction file that is about 2.7 GB and unsuitable for normal GitHub pushes. After the Kaggle data is downloaded to `data/raw/`, run the commands below from the repository root to recreate the same local state.

```bash
.venv/bin/python scripts/check_data_contract.py
.venv/bin/python scripts/evaluate_baseline_cv.py
.venv/bin/python scripts/make_cv_splits.py
.venv/bin/python scripts/evaluate_baseline_multimask.py
.venv/bin/python scripts/analyze_baseline_failures.py
.venv/bin/python scripts/make_baseline_submissions.py
.venv/bin/python scripts/review_part1_plan_alignment.py
.venv/bin/python scripts/validate_part1_outputs.py
```

| Local path | Generated by | Purpose |
|---|---|---|
| `outputs/data_version.json` | `scripts/check_data_contract.py` | Data fingerprint, counts, zip hash |
| `outputs/data_contract_summary.csv` | `scripts/check_data_contract.py` | Per-file schema and contract checks |
| `outputs/baseline_overall_metrics.csv` | `scripts/evaluate_baseline_cv.py` | Baseline aggregate RMSE/MAE/Bias |
| `outputs/baseline_cv_by_well.csv` | `scripts/evaluate_baseline_cv.py` | Per-well baseline validation metrics |
| `outputs/baseline_predictions_train_hidden.csv` | `scripts/evaluate_baseline_cv.py` | Row-level hidden-train predictions, about 2.7 GB, local only |
| `outputs/cv_splits.csv` | `scripts/make_cv_splits.py` | Multi-mask validation split definitions |
| `outputs/baseline_multimask_overall.csv` | `scripts/evaluate_baseline_multimask.py` | Multi-mask aggregate baseline metrics |
| `outputs/baseline_multimask_by_split.csv` | `scripts/evaluate_baseline_multimask.py` | Per-split multi-mask metrics |
| `outputs/failure_case_candidates.csv` | `scripts/analyze_baseline_failures.py` | Failure taxonomy and Part 2 candidate wells |

The committed reports, figures, and submission CSVs can also be regenerated by the same command sequence. The current Part 1 audit expects `outputs/` to exist locally and reports `51 checks, 0 failures` when the artifacts match the data bundle.

## Repository Layout

```text
.
|-- README.md
|-- data/          # local only, downloaded from Kaggle
|-- docs/
|   |-- kaggle_rules_checklist.md
|   `-- plans/
|-- reports/
|-- scripts/
|-- submissions/
|-- outputs/        # local only, regenerated from scripts
`-- .gitignore
```

## Boundaries

This repo keeps the competition data and `outputs/` artifacts local. The raw bundle is too large for git, and Kaggle rules restrict redistribution; `outputs/` includes large reproducible intermediate files. The repository tracks the downloader, reproducible scripts, plans, reports, generated diagnostics, and submission artifacts that support experiment review. Kaggle access still depends on an authenticated account that has accepted the competition rules.

Competition data is also rule-restricted: it is for competition use only and should not be published, redistributed, or pushed to this GitHub repository. Intermediate outputs under `outputs/` are regenerated from scripts instead of pushed.

## Source

- [Kaggle competition page](https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction)
- [Kaggle data page](https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction/data)
- [Kaggle rules checklist](docs/kaggle_rules_checklist.md)
