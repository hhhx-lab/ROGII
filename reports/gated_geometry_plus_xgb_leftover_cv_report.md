# Gated Geometry + XGB Leftover CV Report

- Candidate type: `oracle_gated_stack`
- Eligible for auto submission: `False`

Important: this stack reuses the per-well oracle alpha from `gated_geometry`. It is useful for diagnostics, but it is not a default auto-submission candidate.

```text
final_tvt = baseline_tvt + alpha * (geometry_residual + xgb_leftover_residual)
```

## Overall Metrics

- Stack RMSE: `15.0304`
- Stack MAE: `10.7642`
- Stack P95: `30.3961`
- Rows: `3,783,989`
- Wells: `773`

## Outputs

- `outputs\gated_geometry_plus_xgb_leftover_oof.csv`
- `submissions\gated_geometry_plus_xgb_leftover_submission.csv`

## Comparison

- gated_geometry RMSE: `13.6705`
- stack RMSE: `15.0304`
- delta: `-1.3600`
