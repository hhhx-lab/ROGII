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
| leftover_target_std      | 15.628806519739642                |
| geometry_oof_rmse        | 15.628804658466327                |
| leftover_target_mean_abs | 11.173170794666355                |

## Metrics

| target | rmse | mae | p95_abs_error |
|:---|---:|---:|---:|
| residual_target | 119.9333 | 53.6804 | 182.7800 |
| geometry_oof | 15.6288 | 11.1732 | 31.9450 |
| leftover_target | 15.6288 | 11.1732 | 31.9450 |

- Output: `features\leftover_targets.csv`
