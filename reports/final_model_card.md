# Final Model Card

## Data

- Competition: ROGII Wellbore Geology Prediction
- Training wells: 773
- Visible test wells: 3
- Sample submission rows: 14,151

## Pipeline

1. Tail-slope baseline.
2. Geometry SGD residual model (full-row).
3. Per-well alpha gater (`gated_geometry`).
4. Optional XGBoost leftover stack (`gated_geometry_plus_xgb_leftover`, OOF-validated only).
5. Part 3 routing with GR / typewell confidence.
6. Blend candidates and automatic OOF-based submission selection.
7. Guarded postprocess when an accepted postprocessed variant exists.

## Selected Candidate (local OOF)

- Name: `gated_geometry`
- OOF RMSE: `13.67`
- Degraded wells vs baseline: `0`
- Formula: `final_tvt = baseline_tvt + alpha * geometry_residual`

## Artifacts

- `outputs/baseline_cv_by_well.csv`
- `reports/baseline_cv_report.md`
- `outputs/part3_diagnostics.csv`
- `reports/part3_diagnostics_report.md`
- `outputs/residual_geometry_cv_by_well.csv`
- `reports/residual_geometry_cv_report.md`
- `outputs/gated_alpha_by_well.csv`
- `reports/gated_geometry_cv_report.md`
- `reports/residual_xgb_leftover_cv_report.md`
- `reports/gated_geometry_plus_xgb_leftover_cv_report.md`
- `outputs/ensemble_cv_summary.csv`
- `outputs/ensemble_route_weights.csv`
- `reports/ensemble_report.md`
- `outputs/selected_candidate.json`
- `reports/candidate_selection_report.md`
- `reports/submission_log.md`
- `submission.csv`

Large train-side OOF files remain local-only and are excluded from git.

## Repro Steps

```bash
./.venv/bin/python scripts/build_baseline_features.py
./.venv/bin/python scripts/build_geometry_features.py
./.venv/bin/python scripts/train_residual_model.py --spec geometry --max-rows-per-well 0
./.venv/bin/python scripts/build_gated_geometry.py
./.venv/bin/python scripts/build_leftover_targets.py
./.venv/bin/python scripts/train_residual_model.py --spec xgb_leftover --max-rows-per-well 0 --require-xgboost --max-iter 500
./.venv/bin/python scripts/build_gated_stack.py
./.venv/bin/python scripts/build_part3_features.py
./.venv/bin/python scripts/build_part3_diagnostics.py
./.venv/bin/python scripts/blend_predictions.py
./.venv/bin/python scripts/select_submission_candidate.py --dry-run
./.venv/bin/python scripts/make_submission.py --variant auto --output submission.csv
```

## Risks

- Public leaderboard can still differ from local CV.
- Long hidden intervals remain the hardest case.
- `gated_geometry_plus_xgb_leftover` may not beat `gated_geometry`; selection must stay OOF-driven.
- Postprocess is accepted only when OOF does not get worse; otherwise final export falls back to the selected raw candidate.