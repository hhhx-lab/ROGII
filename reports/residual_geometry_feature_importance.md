# Residual Geometry Feature Importance

Permutation importance is computed on a deterministic sample of training residual rows. It is a model-agnostic diagnostic, not a feature-selection contract.

- Sample rows: `20000`

| feature                             |   importance_mean |   importance_std |
|:------------------------------------|------------------:|-----------------:|
| baseline_pred_delta_from_last_known |          0.887539 |                0 |
| well_gr_missing_rate                |          0.021211 |                0 |
| gr_missing_rate                     |          0.013226 |                0 |
| Z_centered                          |          0.012304 |                0 |
| distance_from_last_known_row        |          0.010858 |                0 |
| baseline_confidence                 |          0.010053 |                0 |
| target_ratio                        |          0.006418 |                0 |
| known_ratio                         |          0.006418 |                0 |
| row_position                        |          0.004145 |                0 |
| MD_norm                             |          0.004145 |                0 |
| path_length_norm                    |          0.00414  |                0 |
| baseline_slope_median               |          0.004128 |                0 |
| well_target_rows                    |          0.003575 |                0 |
| target_rows                         |          0.003575 |                0 |
| baseline_slope_std                  |          0.002046 |                0 |
| known_rows                          |          0.001821 |                0 |
| last_known_row                      |          0.001821 |                0 |
| baseline_tvt                        |          0.001744 |                0 |
| speed_roll_std_25                   |          0.000281 |                0 |
| curvature_roll_std_25               |          0.000257 |                0 |
| curvature_roll_mean_25              |          0.00022  |                0 |
| trajectory_speed_proxy              |          3.6e-05  |                0 |
| speed_roll_mean_25                  |          1.6e-05  |                0 |
| dZ_dMD                              |          1.3e-05  |                0 |
| trajectory_curvature_proxy          |          1.3e-05  |                0 |
