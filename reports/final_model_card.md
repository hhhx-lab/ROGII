# Final Model Card

## Data

- Competition: ROGII Wellbore Geology Prediction
- Training wells: 773
- Visible test wells: 3
- Sample submission rows: 14,151

## Pipeline

1. Tail-slope baseline.
2. Geometry residual model.
3. Part 3 routing with GR / typewell confidence.
4. Ensemble blend with OOF-selected route weights.
5. Guarded postprocess and automatic submission selection.

## Artifacts

- `outputs/baseline_cv_by_well.csv`
- `reports/baseline_cv_report.md`
- `outputs/part3_diagnostics.csv`
- `reports/part3_diagnostics_report.md`
- `outputs/residual_geometry_oof.csv`
- `reports/residual_geometry_cv_report.md`
- `outputs/ensemble_cv_summary.csv`
- `outputs/ensemble_route_weights.csv`
- `reports/ensemble_report.md`
- `reports/postprocess_report.md`
- `reports/submission_log.md`

## Repro Steps

```bash
./.venv/bin/python scripts/build_baseline_features.py
./.venv/bin/python scripts/build_geometry_features.py
./.venv/bin/python scripts/build_part3_features.py
./.venv/bin/python scripts/blend_predictions.py
./.venv/bin/python scripts/make_submission.py --variant auto
```

## Risks

- Public leaderboard can still differ from local CV.
- Long hidden intervals remain the hardest case.
- Postprocess is accepted only when OOF does not get worse; otherwise final export falls back to the selected raw candidate.
