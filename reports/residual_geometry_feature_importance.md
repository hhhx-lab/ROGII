# Residual Geometry Feature Importance

Permutation importance is computed on a deterministic sample of training residual rows. It is a model-agnostic diagnostic, not a feature-selection contract.

- Sample rows: `20000`

| feature                             |   importance_mean |   importance_std |
|:------------------------------------|------------------:|-----------------:|
| baseline_pred_delta_from_last_known |          0.869699 |                0 |
| well_gr_missing_rate                |          0.024497 |                0 |
| baseline_confidence                 |          0.015098 |                0 |
| gr_missing_rate                     |          0.014847 |                0 |
| distance_from_last_known_row        |          0.012371 |                0 |
| Z_centered                          |          0.01124  |                0 |
| target_ratio                        |          0.007701 |                0 |
| known_ratio                         |          0.007701 |                0 |
| row_position                        |          0.004545 |                0 |
| MD_norm                             |          0.004545 |                0 |
| path_length_norm                    |          0.004541 |                0 |
| well_target_rows                    |          0.004401 |                0 |
| target_rows                         |          0.004401 |                0 |
| baseline_slope_median               |          0.003258 |                0 |
| last_known_row                      |          0.002944 |                0 |
| known_rows                          |          0.002944 |                0 |
| baseline_slope_std                  |          0.002401 |                0 |
| baseline_tvt                        |          0.001981 |                0 |
| curvature_roll_std_25               |          0.000344 |                0 |
| curvature_roll_mean_25              |          0.000279 |                0 |
| speed_roll_std_25                   |          0.00019  |                0 |
| trajectory_speed_proxy              |          4e-05    |                0 |
| speed_roll_mean_25                  |          2e-05    |                0 |
| trajectory_curvature_proxy          |          7e-06    |                0 |
| dZ_dMD                              |          5e-06    |                0 |
