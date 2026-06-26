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
| geometry_ungated | 16.3081 | 11.5179 | 32.8121 | -0.1171 |
| gated_geometry | 13.6705 | 9.6476 | 27.8348 | -0.3199 |

## Alpha Distribution

|   alpha |   wells |
|--------:|--------:|
|    0    |     103 |
|    0.25 |      23 |
|    0.5  |      38 |
|    0.75 |     114 |
|    1    |     495 |

## Per-Well Summary

- Improved vs baseline: `670`
- Degraded vs baseline: `0`
- Mean alpha: `0.7830`
- Wells with alpha < 1.0: `278`

## Outputs

- OOF: `outputs\gated_geometry_oof.csv`
- Alpha table: `outputs\gated_alpha_by_well.csv`
- Submission: `submissions\gated_geometry_submission.csv`
