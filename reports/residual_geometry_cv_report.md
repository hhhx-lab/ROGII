# Residual Geometry CV Report

- Data hash: `unknown`
- Model: `SGDRegressorPipeline`
- Selected alpha: `1.0`
- Train rows per well cap: `60`
- Promotion decision: `PROMOTE_TO_PART3_INPUT`

## Overall Metrics

| model             |     rmse |     mae |   median_abs_error |   p90_abs_error |   p95_abs_error |   p99_abs_error |   max_abs_error |    bias |   selected_alpha |
|:------------------|---------:|--------:|-------------------:|----------------:|----------------:|----------------:|----------------:|--------:|-----------------:|
| baseline          | 119.933  | 53.6804 |            26.63   |         130.61  |        182.78   |         318.841 |        2552.66  |  4.9893 |                1 |
| geometry_residual |  16.1024 | 11.4095 |             8.3184 |          25.013 |         32.6822 |          54.446 |         107.902 | -0.1719 |                1 |

## Alpha Search

|   alpha |     rmse |     mae |   median_abs_error |   p90_abs_error |   p95_abs_error |   p99_abs_error |   max_abs_error |    bias |
|--------:|---------:|--------:|-------------------:|----------------:|----------------:|----------------:|----------------:|--------:|
|    1    |  16.1024 | 11.4095 |             8.3184 |         25.013  |         32.6822 |         54.446  |         107.902 | -0.1719 |
|    0.75 |  32.9992 | 18.2021 |            10.9915 |         42.3248 |         57.9692 |         93.8411 |         596.719 |  1.1184 |
|    0.5  |  60.9887 | 29.2575 |            15.6255 |         69.774  |         97.413  |        164.935  |        1248.7   |  2.4087 |
|    0.25 |  90.2846 | 41.2676 |            20.8857 |         99.7954 |        140.35   |        241.611  |        1900.68  |  3.699  |
|    0    | 119.933  | 53.6804 |            26.63   |        130.61   |        182.78   |        318.841  |        2552.66  |  4.9893 |

## Per-Well Summary

|   wells |   improved_wells |   degraded_wells |   mean_rmse_improvement |   median_rmse_improvement |   worst_degradation |   best_improvement |
|--------:|-----------------:|-----------------:|------------------------:|--------------------------:|--------------------:|-------------------:|
|     773 |              633 |              140 |                 44.7991 |                   25.4487 |            -69.5518 |             1413.6 |

## Residual Clip and Smoothness

|   residual_clip_abs |   raw_p01 |   raw_p99 |   clipped_p01 |   clipped_p99 |   extreme_raw_count |   max_abs_correction |   max_per_well_correction_jump |   p95_per_well_correction_jump |
|--------------------:|----------:|----------:|--------------:|--------------:|--------------------:|---------------------:|-------------------------------:|-------------------------------:|
|               1e+09 |  -250.261 |   236.444 |      -250.261 |       236.444 |                   0 |              2607.92 |                         1.4015 |                         1.1237 |

## Bias by Target Length

| target_length_bucket   |    rows |   wells |   baseline_bias |   geometry_bias |   baseline_rmse |   geometry_rmse |   rmse_improvement |
|:-----------------------|--------:|--------:|----------------:|----------------:|----------------:|----------------:|-------------------:|
| 0-500                  |     407 |       1 |          1.1742 |         -8.2097 |          2.5553 |          8.5667 |            -6.0114 |
| 501-1500               |     911 |       1 |         10.7308 |          1.1494 |         12.3835 |          2.1237 |            10.2598 |
| 1501-3000              |  114845 |      44 |         -3.253  |         -0.1011 |         26.6447 |         12.5446 |            14.1001 |
| 3001-5000              | 1613495 |     386 |          0.4316 |         -0.3655 |         99.0637 |         15.3048 |            83.7589 |
| 5001+                  | 2054331 |     341 |          9.028  |         -0.0228 |        136.921  |         16.8763 |           120.044  |

## Bias by Baseline Confidence

| confidence_bucket   |    rows |   wells |   baseline_bias |   geometry_bias |   baseline_rmse |   geometry_rmse |   rmse_improvement |
|:--------------------|--------:|--------:|----------------:|----------------:|----------------:|----------------:|-------------------:|
| 0-25%               | 3767292 |     764 |          4.987  |         -0.1909 |        120.191  |         16.1069 |           104.085  |
| 25-50%              |   15379 |       7 |          5.3164 |          4.6093 |         20.5943 |         15.6213 |             4.973  |
| 50-75%              |    1318 |       2 |          7.7797 |         -1.7407 |         10.3929 |          5.0774 |             5.3155 |

## Bias by Predicted Residual Magnitude

| predicted_residual_bucket   |   rows |   wells |   baseline_bias |   geometry_bias |   baseline_rmse |   geometry_rmse |   rmse_improvement |
|:----------------------------|-------:|--------:|----------------:|----------------:|----------------:|----------------:|-------------------:|
| q1_lowest                   | 756798 |     269 |        123.805  |         -0.7336 |        236.414  |         19.821  |           216.593  |
| q2                          | 756798 |     412 |         16.3394 |         -2.0719 |         23.5157 |         13.3188 |            10.1969 |
| q3                          | 756797 |     706 |          0.1502 |          1.0617 |         11.4285 |         11.4499 |            -0.0214 |
| q4                          | 756798 |     420 |        -16.6194 |          2.1866 |         24.3233 |         13.275  |            11.0484 |
| q5_highest                  | 756798 |     271 |        -98.7288 |         -1.3024 |        121.463  |         20.4658 |           100.998  |

## Outputs

- OOF predictions: `outputs\residual_geometry_oof.csv`
- Per-well CV: `outputs\residual_geometry_cv_by_well.csv`
- Test predictions: `outputs\residual_geometry_test_predictions.csv`
