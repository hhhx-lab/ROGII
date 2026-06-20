# Residual Geometry Server Runbook

The local Part 2 run is intentionally reproducible and can be scaled on a larger machine without changing code.

## Full-Row Training

```bash
.venv/bin/python scripts/build_baseline_features.py
.venv/bin/python scripts/build_geometry_features.py
ROGII_PART2_TRAIN_ROWS_PER_WELL=0 \
ROGII_PART2_MAX_ITER=500 \
.venv/bin/python scripts/train_residual_model.py
.venv/bin/python scripts/evaluate_model_cv.py
ROGII_PART2_MULTIMASK_TRAIN_ROWS_PER_WELL=0 \
ROGII_PART2_MULTIMASK_MAX_ITER=500 \
.venv/bin/python scripts/evaluate_residual_multimask.py
.venv/bin/python scripts/validate_part2_outputs.py
```

## Local Default

- `ROGII_PART2_TRAIN_ROWS_PER_WELL=600`
- selected alpha: `0.75`
- residual clip abs: `66.5900`
- local multi-mask validation defaults are lighter than full-row server training and are controlled by `ROGII_PART2_MULTIMASK_*` environment variables.

All generated `features/` and `outputs/` artifacts are reproducible from scripts and should be regenerated on the server after syncing `data/raw/`.
