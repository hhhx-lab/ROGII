# Residual Geometry CV Report

- Data hash: `unknown`
- Model: `SGDRegressorPipeline`
- Selected alpha: `1.0`
- Train rows per well cap: `0`
- Promotion decision: `PROMOTE_TO_PART3_INPUT`

## Overall Metrics

| model             |     rmse |     mae |   median_abs_error |   p90_abs_error |   p95_abs_error |   p99_abs_error |   max_abs_error |    bias |   selected_alpha |
|:------------------|---------:|--------:|-------------------:|----------------:|----------------:|----------------:|----------------:|--------:|-----------------:|
| baseline          | 119.933  | 53.6804 |            26.63   |        130.61   |         182.78  |        318.841  |        2552.66  |  4.9893 |                1 |
| geometry_residual |  15.6288 | 11.1732 |             8.2506 |         24.4477 |          31.945 |         50.8512 |         105.237 | -0.0025 |                1 |

## Alpha Search

|   alpha |     rmse |     mae |   median_abs_error |   p90_abs_error |   p95_abs_error |   p99_abs_error |   max_abs_error |    bias |
|--------:|---------:|--------:|-------------------:|----------------:|----------------:|----------------:|----------------:|--------:|
|    1    |  15.6288 | 11.1732 |             8.2506 |         24.4477 |         31.945  |         50.8512 |         105.237 | -0.0025 |
|    0.75 |  33.6079 | 18.244  |            10.9831 |         42.4888 |         57.6606 |         93.9656 |         619.762 |  1.2454 |
|    0.5  |  61.4914 | 29.3052 |            15.6277 |         69.9844 |         97.7526 |        165.943  |        1264.06  |  2.4934 |
|    0.25 |  90.5503 | 41.2999 |            20.8836 |         99.9259 |        140.564  |        242.084  |        1908.36  |  3.7414 |
|    0    | 119.933  | 53.6804 |            26.63   |        130.61   |        182.78   |        318.841  |        2552.66  |  4.9893 |

## Per-Well Summary

|   wells |   improved_wells |   degraded_wells |   mean_rmse_improvement |   median_rmse_improvement |   worst_degradation |   best_improvement |
|--------:|-----------------:|-----------------:|------------------------:|--------------------------:|--------------------:|-------------------:|
|     773 |              632 |              141 |                 44.9782 |                   25.4964 |            -47.3672 |            1431.35 |

## Residual Clip and Smoothness

|   residual_clip_abs |   raw_p01 |   raw_p99 |   clipped_p01 |   clipped_p99 |   extreme_raw_count |   max_abs_correction |   max_per_well_correction_jump |   p95_per_well_correction_jump |
|--------------------:|----------:|----------:|--------------:|--------------:|--------------------:|---------------------:|-------------------------------:|-------------------------------:|
|               1e+09 |   -249.32 |   236.383 |       -249.32 |       236.383 |                   0 |               2577.2 |                         0.7851 |                         0.3515 |

## Bias by Target Length

| target_length_bucket   |    rows |   wells |   baseline_bias |   geometry_bias |   baseline_rmse |   geometry_rmse |   rmse_improvement |
|:-----------------------|--------:|--------:|----------------:|----------------:|----------------:|----------------:|-------------------:|
| 0-500                  |     407 |       1 |          1.1742 |          4.0243 |          2.5553 |          4.6007 |            -2.0453 |
| 501-1500               |     911 |       1 |         10.7308 |          0.9757 |         12.3835 |          2.1247 |            10.2588 |
| 1501-3000              |  114845 |      44 |         -3.253  |          0.1858 |         26.6447 |         12.6732 |            13.9715 |
| 3001-5000              | 1613495 |     386 |          0.4316 |         -0.318  |         99.0637 |         15.2306 |            83.8331 |
| 5001+                  | 2054331 |     341 |          9.028  |          0.2335 |        136.921  |         16.0853 |           120.835  |

## Bias by Baseline Confidence

| confidence_bucket   |    rows |   wells |   baseline_bias |   geometry_bias |   baseline_rmse |   geometry_rmse |   rmse_improvement |
|:--------------------|--------:|--------:|----------------:|----------------:|----------------:|----------------:|-------------------:|
| 0-25%               | 3767292 |     764 |          4.987  |         -0.0318 |        120.191  |         15.6295 |           104.562  |
| 25-50%              |   15379 |       7 |          5.3164 |          6.9962 |         20.5943 |         16.0974 |             4.4968 |
| 50-75%              |    1318 |       2 |          7.7797 |          1.9171 |         10.3929 |          3.1075 |             7.2854 |

## Bias by Predicted Residual Magnitude

| predicted_residual_bucket   |   rows |   wells |   baseline_bias |   geometry_bias |   baseline_rmse |   geometry_rmse |   rmse_improvement |
|:----------------------------|-------:|--------:|----------------:|----------------:|----------------:|----------------:|-------------------:|
| q1_lowest                   | 756798 |     271 |        123.874  |          0.2844 |        236.422  |         19.1044 |           217.318  |
| q2                          | 756798 |     396 |         16.3543 |         -1.8263 |         23.4749 |         13.2773 |            10.1976 |
| q3                          | 756797 |     723 |          0.1876 |          1.2168 |         11.346  |         11.4275 |            -0.0816 |
| q4                          | 756798 |     394 |        -16.4985 |          2.1095 |         24.1327 |         13.1843 |            10.9484 |
| q5_highest                  | 756798 |     269 |        -98.9713 |         -1.7969 |        121.5    |         19.3809 |           102.119  |

## Outputs

- OOF predictions: `outputs\residual_geometry_oof.csv`
- Per-well CV: `outputs\residual_geometry_cv_by_well.csv`
- Test predictions: `outputs\residual_geometry_test_predictions.csv`
