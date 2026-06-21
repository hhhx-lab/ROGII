# Residual Geometry Feature Importance

Permutation importance is computed on a deterministic sample of training residual rows. It is a model-agnostic diagnostic, not a feature-selection contract.

- Sample rows: `20000`

| feature                             |   importance_mean |   importance_std |
|:------------------------------------|------------------:|-----------------:|
| baseline_pred_delta_from_last_known |          0.929011 |                0 |
| Z_centered                          |          0.013859 |                0 |
| well_gr_missing_rate                |          0.007123 |                0 |
| distance_from_last_known_row        |          0.005707 |                0 |
| baseline_slope_median               |          0.005094 |                0 |
| baseline_confidence                 |          0.005031 |                0 |
| target_ratio                        |          0.003991 |                0 |
| known_ratio                         |          0.003991 |                0 |
| target_rows                         |          0.003166 |                0 |
| well_target_rows                    |          0.003166 |                0 |
| row_position                        |          0.002909 |                0 |
| MD_norm                             |          0.002909 |                0 |
| path_length_norm                    |          0.002909 |                0 |
| baseline_slope_std                  |          0.002172 |                0 |
| gr_missing_rate                     |          0.001409 |                0 |
| speed_roll_std_25                   |          0.001158 |                0 |
| known_rows                          |          0.001124 |                0 |
| last_known_row                      |          0.001124 |                0 |
| trajectory_speed_proxy              |          0.001044 |                0 |
| speed_roll_mean_25                  |          0.000818 |                0 |
| baseline_tvt                        |          0.00067  |                0 |
| curvature_roll_mean_25              |          0.000521 |                0 |
| curvature_roll_std_25               |          0.000475 |                0 |
| trajectory_curvature_proxy          |          0.00042  |                0 |
| dZ_dMD                              |          0.000201 |                0 |
