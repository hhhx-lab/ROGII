# Residual Geometry CV Report

- Data hash: `unknown`
- Model: `SGDRegressorPipeline`
- Selected alpha: `1.0`
- Train rows per well cap: `0`
- Promotion decision: `PROMOTE_TO_PART3_INPUT`

## Overall Metrics

| model             |     rmse |     mae |   median_abs_error |   p90_abs_error |   p95_abs_error |   p99_abs_error |   max_abs_error |    bias |   selected_alpha |
|:------------------|---------:|--------:|-------------------:|----------------:|----------------:|----------------:|----------------:|--------:|-----------------:|
| baseline          | 119.933  | 53.6804 |            26.63   |        130.61   |        182.78   |        318.841  |        2552.66  |  4.9893 |                1 |
| geometry_residual |  16.3081 | 11.5179 |             8.3217 |         25.1793 |         32.8121 |         55.0561 |         109.893 | -0.1171 |                1 |

## Alpha Search

|   alpha |     rmse |     mae |   median_abs_error |   p90_abs_error |   p95_abs_error |   p99_abs_error |   max_abs_error |    bias |
|--------:|---------:|--------:|-------------------:|----------------:|----------------:|----------------:|----------------:|--------:|
|    1    |  16.3081 | 11.5179 |             8.3217 |         25.1793 |         32.8121 |         55.0561 |         109.893 | -0.1171 |
|    0.75 |  32.8179 | 18.2028 |            10.9637 |         42.3638 |         58.189  |         93.5504 |         588.433 |  1.1595 |
|    0.5  |  60.8307 | 29.2495 |            15.6375 |         69.7868 |         97.2641 |        164.607  |        1243.18  |  2.4361 |
|    0.25 |  90.2    | 41.2606 |            20.8918 |         99.7828 |        140.283  |        241.377  |        1897.92  |  3.7127 |
|    0    | 119.933  | 53.6804 |            26.63   |        130.61   |        182.78   |        318.841  |        2552.66  |  4.9893 |

## Per-Well Summary

|   wells |   improved_wells |   degraded_wells |   mean_rmse_improvement |   median_rmse_improvement |   worst_degradation |   best_improvement |
|--------:|-----------------:|-----------------:|------------------------:|--------------------------:|--------------------:|-------------------:|
|     773 |              635 |              138 |                 44.6716 |                    25.505 |            -79.3786 |            1408.32 |

## Residual Clip and Smoothness

|   residual_clip_abs |   raw_p01 |   raw_p99 |   clipped_p01 |   clipped_p99 |   extreme_raw_count |   max_abs_correction |   max_per_well_correction_jump |   p95_per_well_correction_jump |
|--------------------:|----------:|----------:|--------------:|--------------:|--------------------:|---------------------:|-------------------------------:|-------------------------------:|
|               1e+09 |  -250.678 |   236.925 |      -250.678 |       236.925 |                   0 |              2618.97 |                         1.0161 |                         0.7847 |

## Bias by Target Length

| target_length_bucket   |    rows |   wells |   baseline_bias |   geometry_bias |   baseline_rmse |   geometry_rmse |   rmse_improvement |
|:-----------------------|--------:|--------:|----------------:|----------------:|----------------:|----------------:|-------------------:|
| 0-500                  |     407 |       1 |          1.1742 |         -8.1502 |          2.5553 |          8.4969 |            -5.9416 |
| 501-1500               |     911 |       1 |         10.7308 |         21.0424 |         12.3835 |         21.1113 |            -8.7278 |
| 1501-3000              |  114845 |      44 |         -3.253  |          0.9294 |         26.6447 |         12.8891 |            13.7556 |
| 3001-5000              | 1613495 |     386 |          0.4316 |         -0.4065 |         99.0637 |         15.4125 |            83.6512 |
| 5001+                  | 2054331 |     341 |          9.028  |          0.0439 |        136.921  |         17.1407 |           119.78   |

## Bias by Baseline Confidence

| confidence_bucket   |    rows |   wells |   baseline_bias |   geometry_bias |   baseline_rmse |   geometry_rmse |   rmse_improvement |
|:--------------------|--------:|--------:|----------------:|----------------:|----------------:|----------------:|-------------------:|
| 0-25%               | 3767292 |     764 |          4.987  |         -0.1496 |        120.191  |         16.3042 |           103.887  |
| 25-50%              |   15379 |       7 |          5.3164 |          6.8083 |         20.5943 |         17.0622 |             3.5321 |
| 50-75%              |    1318 |       2 |          7.7797 |         12.0277 |         10.3929 |         18.1756 |            -7.7827 |

## Bias by Predicted Residual Magnitude

| predicted_residual_bucket   |   rows |   wells |   baseline_bias |   geometry_bias |   baseline_rmse |   geometry_rmse |   rmse_improvement |
|:----------------------------|-------:|--------:|----------------:|----------------:|----------------:|----------------:|-------------------:|
| q1_lowest                   | 756798 |     267 |        123.727  |         -0.9374 |        236.404  |         20.2185 |           216.185  |
| q2                          | 756798 |     383 |         16.395  |         -2.0222 |         23.6032 |         13.3379 |            10.2653 |
| q3                          | 756797 |     711 |          0.0788 |          1.0696 |         11.5015 |         11.4919 |             0.0096 |
| q4                          | 756798 |     393 |        -16.5616 |          2.368  |         24.3574 |         13.3701 |            10.9873 |
| q5_highest                  | 756798 |     271 |        -98.693  |         -1.0634 |        121.452  |         20.7906 |           100.662  |

## Outputs

- OOF predictions: `outputs\residual_geometry_oof.csv`
- Per-well CV: `outputs\residual_geometry_cv_by_well.csv`
- Test predictions: `outputs\residual_geometry_test_predictions.csv`
