# Leftover Target Report

Fold-safe leftover targets are built from geometry **OOF** residuals only.

```text
leftover_target = truth_tvt - (baseline_tvt + geometry_oof_residual)
```

## Summary

|                          | value                             |
|:-------------------------|:----------------------------------|
| data_hash                | unknown                           |
| rows                     | 3783989                           |
| wells                    | 773                               |
| source_geometry_oof      | outputs\residual_geometry_oof.csv |
| residual_target_std      | 119.82948699592599                |
| leftover_target_std      | 16.307642110026727                |
| geometry_oof_rmse        | 16.30806037415457                 |
| leftover_target_mean_abs | 11.517928435352504                |

## Metrics

| target | rmse | mae | p95_abs_error |
|:---|---:|---:|---:|
| residual_target | 119.9333 | 53.6804 | 182.7800 |
| geometry_oof | 16.3081 | 11.5179 | 32.8121 |
| leftover_target | 16.3081 | 11.5179 | 32.8121 |

- Output: `features\leftover_targets.csv`
