# Residual Geometry Feature Importance

Permutation importance is computed on a deterministic sample of training residual rows. It is a model-agnostic diagnostic, not a feature-selection contract.

- Sample rows: `20000`

| feature                       |   importance_mean |   importance_std |
|:------------------------------|------------------:|-----------------:|
| rolling_dZ_dMD_mean_500       |          2.27956  |         0.032709 |
| last_known_TVT_input          |          2.05412  |         0.049488 |
| baseline_local_slope_std      |          2.00785  |         0.009799 |
| Z_normalized_within_well      |          1.86186  |         0.001934 |
| b1_linear_md_slope            |          1.57122  |         0.018405 |
| baseline_known_tail_slope_50  |          1.46646  |         0.00964  |
| X                             |          1.31348  |         0.027835 |
| Y                             |          1.12893  |         0.010203 |
| last_known_row                |          1.12403  |         0.012171 |
| baseline_local_slope_mean     |          0.967904 |         0.001875 |
| well_Z_span                   |          0.792028 |         0.017931 |
| well_known_TVT_span           |          0.776712 |         0.003091 |
| last_known_MD                 |          0.734118 |         0.013836 |
| target_rows_count             |          0.702468 |         0.015457 |
| well_GR_missing_rate          |          0.698847 |         0.006861 |
| baseline_confidence           |          0.694152 |         0.014947 |
| well_total_rows               |          0.672755 |         0.009415 |
| dZ                            |          0.663705 |         0.012403 |
| dX                            |          0.604033 |         0.000915 |
| dY                            |          0.581995 |         0.003322 |
| known_ratio                   |          0.525254 |         0.016047 |
| b2_tail_slope_k500_pred       |          0.518226 |         0.004053 |
| baseline_known_tail_slope_100 |          0.437423 |         0.012437 |
| b2_tail_slope_k50_pred        |          0.437268 |         0.00136  |
| baseline_known_tail_slope_500 |          0.413852 |         0.001963 |
| baseline_known_tail_slope_200 |          0.381591 |         0.012291 |
| target_gr_missing_rate        |          0.337299 |         0.007987 |
| Z                             |          0.299389 |         0.007698 |
| distance_row_from_last_known  |          0.289732 |         0.00516  |
| MD                            |          0.274545 |         0.00491  |
| b2_tail_slope_k200_pred       |          0.221929 |         0.005948 |
| b1_linear_md_pred             |          0.205817 |         0.002818 |
| row_position                  |          0.170107 |         0.000376 |
| row_index                     |          0.16351  |         0.001572 |
| rolling_Z_mean_500            |          0.155489 |         0.007158 |
| baseline_distance_penalty     |          0.125069 |         0.00127  |
| rolling_Z_mean_200            |          0.076709 |         0.000962 |
| rolling_Z_std_500             |          0.063615 |         0.001442 |
| rolling_Z_mean_100            |          0.059589 |         0.001395 |
| rolling_Z_mean_25             |          0.032839 |         0.003169 |
| rolling_Z_mean_50             |          0.016847 |         0.000409 |
| rolling_dZ_dMD_std_500        |          0.013454 |         0.000198 |
| rolling_dZ_dMD_mean_25        |          0.013426 |         0.000307 |
| rolling_curvature_mean_500    |          0.006132 |         0.000182 |
| b2_tail_slope_k200_slope      |          0.005171 |         0.000213 |
| b2_tail_slope_k50_slope       |          0.004792 |         0.000675 |
| rolling_dZ_dMD_std_200        |          0.001079 |         9.5e-05  |
| rolling_dZ_dMD_std_100        |          0.000848 |         2.5e-05  |
| rolling_Z_std_25              |          0.000797 |         0.000197 |
| rolling_dZ_dMD_mean_200       |          0.000523 |         7.4e-05  |
