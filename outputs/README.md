# Local Outputs Directory

This directory is tracked as a placeholder only.

Generated intermediate artifacts are intentionally not committed. Recreate them from the repository root after `data/raw/` exists:

```bash
.venv/bin/python scripts/check_data_contract.py
.venv/bin/python scripts/evaluate_baseline_cv.py
.venv/bin/python scripts/make_cv_splits.py
.venv/bin/python scripts/evaluate_baseline_multimask.py
.venv/bin/python scripts/analyze_baseline_failures.py
.venv/bin/python scripts/make_baseline_submissions.py
.venv/bin/python scripts/validate_part1_outputs.py
```

Important local-only outputs include:

- `outputs/data_version.json`
- `outputs/data_contract_summary.csv`
- `outputs/baseline_cv_by_well.csv`
- `outputs/baseline_predictions_train_hidden.csv`
- `outputs/cv_splits.csv`
- `outputs/baseline_multimask_overall.csv`
- `outputs/baseline_multimask_by_split.csv`
- `outputs/failure_case_candidates.csv`
