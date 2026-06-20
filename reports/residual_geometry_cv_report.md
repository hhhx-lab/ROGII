# Residual Geometry CV Report

- Data hash: `46fd84d5e7e1`
- Model: `sklearn.ensemble.HistGradientBoostingRegressor`
- Selected alpha: `0.75`
- Train rows per well cap: `600`
- Promotion decision: `PROMOTE_TO_PART3_INPUT`

## Overall Metrics

| model             |    rmse |     mae |   median_abs_error |   p90_abs_error |   p95_abs_error |   p99_abs_error |   max_abs_error |    bias |   selected_alpha |
|:------------------|--------:|--------:|-------------------:|----------------:|----------------:|----------------:|----------------:|--------:|-----------------:|
| baseline          | 15.9099 | 11.1965 |              8.03  |          24.68  |          32.34  |          53.13  |          103.78 | -1.596  |             0.75 |
| geometry_residual | 14.99   | 10.6821 |              7.818 |          23.006 |          30.129 |          51.244 |           97.87 | -0.3027 |             0.75 |

## Alpha Search

|   alpha |    rmse |     mae |   median_abs_error |   p90_abs_error |   p95_abs_error |   p99_abs_error |   max_abs_error |    bias |
|--------:|--------:|--------:|-------------------:|----------------:|----------------:|----------------:|----------------:|--------:|
|    0.75 | 14.99   | 10.6821 |             7.8182 |         23.0055 |         30.1294 |         51.2438 |         97.8698 | -0.3027 |
|    1    | 15.063  | 10.8251 |             8.0234 |         23.1434 |         30.0728 |         51.3808 |         97.7665 |  0.1284 |
|    0.5  | 15.1109 | 10.6922 |             7.6901 |         23.1567 |         30.7545 |         51.1616 |         98.337  | -0.7338 |
|    0.25 | 15.4212 | 10.8578 |             7.7773 |         23.7365 |         31.426  |         51.5306 |        101.059  | -1.1649 |
|    0    | 15.9099 | 11.1965 |             8.0303 |         24.6797 |         32.3398 |         53.1299 |        103.78   | -1.596  |

## Per-Well Summary

|   wells |   improved_wells |   degraded_wells |   mean_rmse_improvement |   median_rmse_improvement |   worst_degradation |   best_improvement |
|--------:|-----------------:|-----------------:|------------------------:|--------------------------:|--------------------:|-------------------:|
|     773 |              449 |              324 |                  0.5814 |                     0.448 |            -15.9239 |            19.8456 |

## Residual Clip and Smoothness

|   residual_clip_abs |   raw_p01 |   raw_p99 |   clipped_p01 |   clipped_p99 |   extreme_raw_count |   max_abs_correction |   max_per_well_correction_jump |   p95_per_well_correction_jump |
|--------------------:|----------:|----------:|--------------:|--------------:|--------------------:|---------------------:|-------------------------------:|-------------------------------:|
|               66.59 |  -14.0727 |   19.5382 |      -14.0727 |       19.5382 |                   0 |              35.2988 |                        13.9203 |                         3.7201 |

## Bias by Target Length

| target_length_bucket   |    rows |   wells |   baseline_bias |   geometry_bias |   baseline_rmse |   geometry_rmse |   rmse_improvement |
|:-----------------------|--------:|--------:|----------------:|----------------:|----------------:|----------------:|-------------------:|
| 0-500                  |     407 |       1 |          1.1742 |         -1.1091 |          2.5553 |          3.1421 |            -0.5868 |
| 501-1500               |     911 |       1 |         -2.9492 |          0.8092 |          3.6012 |          1.9893 |             1.6118 |
| 1501-3000              |  114845 |      44 |         -0.3832 |          0.3359 |         12.4785 |         12.3956 |             0.0829 |
| 3001-5000              | 1613495 |     386 |         -1.2577 |         -0.0686 |         15.7208 |         15.0382 |             0.6826 |
| 5001+                  | 2054331 |     341 |         -1.9294 |         -0.5226 |         16.2302 |         15.0889 |             1.1413 |

## Bias by Baseline Confidence

| confidence_bucket   |    rows |   wells |   baseline_bias |   geometry_bias |   baseline_rmse |   geometry_rmse |   rmse_improvement |
|:--------------------|--------:|--------:|----------------:|----------------:|----------------:|----------------:|-------------------:|
| 25-50%              |  935687 |     162 |         -2.8495 |         -0.9298 |         16.5168 |         15.7522 |             0.7646 |
| 50-75%              | 2847895 |     610 |         -1.1845 |         -0.0966 |         15.7065 |         14.732  |             0.9744 |
| 75-100%             |     407 |       1 |          1.1742 |         -1.1091 |          2.5553 |          3.1421 |            -0.5868 |

## Bias by Predicted Residual Magnitude

| predicted_residual_bucket   |   rows |   wells |   baseline_bias |   geometry_bias |   baseline_rmse |   geometry_rmse |   rmse_improvement |
|:----------------------------|-------:|--------:|----------------:|----------------:|----------------:|----------------:|-------------------:|
| q1_lowest                   | 756798 |     437 |          5.0649 |         -0.262  |         16.7998 |         15.4176 |             1.3822 |
| q2                          | 756798 |     611 |         -0.244  |         -1.3224 |         13.8987 |         13.9509 |            -0.0522 |
| q3                          | 756797 |     651 |         -1.2492 |         -0.0699 |         14.5118 |         14.4579 |             0.0539 |
| q4                          | 756798 |     597 |         -3.8069 |         -0.3228 |         16.1226 |         15.6405 |             0.4821 |
| q5_highest                  | 756798 |     453 |         -7.7447 |          0.4637 |         17.8796 |         15.4115 |             2.4681 |

## Outputs

- OOF predictions: `outputs/residual_geometry_oof.csv`
- Per-well CV: `outputs/residual_geometry_cv_by_well.csv`
- Test predictions: `outputs/residual_geometry_test_predictions.csv`
