# Local Feature Artifacts

This directory is tracked as a placeholder only.

Part 2 feature files are generated locally and intentionally not committed because full-row parquet artifacts can be large. Recreate them after `data/raw/` and Part 1 `outputs/` exist:

```bash
.venv/bin/python scripts/build_baseline_features.py
.venv/bin/python scripts/build_geometry_features.py
```

Expected local files:

- `features/baseline_features_train.parquet`
- `features/baseline_features_test.parquet`
- `features/geometry_features_train.parquet`
- `features/geometry_features_test.parquet`
- `features/residual_targets.parquet`

Residual multi-mask validation recomputes equivalent in-memory feature frames from `outputs/cv_splits.csv`; those temporary frames are not persisted.
