# Gated Geometry CV Report

- Model: `per_well_alpha_grid`
- Candidate type: `oracle_gated_residual`
- Eligible for auto submission: `False`

Important: this candidate searches alpha using each training well's own truth, then reports OOF on the same well. Treat it as a diagnostic upper bound, not as a validated leaderboard candidate. Use `learned_gated_geometry` for auto submission.

- Data hash: `unknown`
- Alpha grid: `[0.0, 0.25, 0.5, 0.75, 1.0]`
- Wells: `773`
- Rows: `3,783,989`

## Overall Metrics

| model | rmse | mae | p95_abs_error | bias |
|:---|---:|---:|---:|---:|
| baseline | 119.9333 | 53.6804 | 182.7800 | 4.9893 |
| geometry_ungated | 15.6288 | 11.1732 | 31.9450 | -0.0025 |
| gated_geometry | 13.3807 | 9.4678 | 27.3533 | -0.0955 |

## Alpha Distribution

|   alpha |   wells |
|--------:|--------:|
|    0    |     103 |
|    0.25 |      18 |
|    0.5  |      51 |
|    0.75 |     104 |
|    1    |     497 |

## Per-Well Summary

- Improved vs baseline: `670`
- Degraded vs baseline: `0`
- Mean alpha: `0.7827`
- Wells with alpha < 1.0: `276`

## Outputs

- OOF: `outputs\gated_geometry_oof.csv`
- Alpha table: `outputs\gated_alpha_by_well.csv`
- Submission: `submissions\gated_geometry_submission.csv`
