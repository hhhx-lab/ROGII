# Baseline Multi-Mask Report

- Data hash: `unknown`
- Splits evaluated: 5411
- Mask types: 7
- Baselines: 6

## Best Baseline by Mask Type

| data_hash   | mask_type         | baseline         | family   |   tail_window |   splits |   wells |   target_rows |   row_weighted_rmse |   row_weighted_mae |   mean_split_rmse |   median_split_rmse |   worst_split_rmse |   mean_bias |
|:------------|:------------------|:-----------------|:---------|--------------:|---------:|--------:|--------------:|--------------------:|-------------------:|------------------:|--------------------:|-------------------:|------------:|
| unknown     | high_curvature    | B0_constant_last | B0       |           nan |      773 |     773 |       1018445 |             99.0218 |            51.2274 |           60.0785 |             10.6903 |           442.214  |    -52.2132 |
| unknown     | high_gr_missing   | B0_constant_last | B0       |           nan |      773 |     773 |       1273066 |             39.7869 |            12.9017 |           15.146  |              6.6824 |           415.394  |     -7.8774 |
| unknown     | mid_contiguous    | B0_constant_last | B0       |           nan |      773 |     773 |        888302 |              8.4333 |             5.6585 |            6.4388 |              5.242  |            95.4457 |     -0.2212 |
| unknown     | original_hidden   | B0_constant_last | B0       |           nan |      773 |     773 |       3783989 |             15.9099 |            11.1965 |           12.8125 |             10.6651 |            70.6394 |     -1.4232 |
| unknown     | random_contiguous | B0_constant_last | B0       |           nan |      773 |     773 |       1259444 |             28.9184 |            11.9257 |           13.8966 |              7.0152 |           286.761  |     -6.8592 |
| unknown     | trailing_long     | B0_constant_last | B0       |           nan |      773 |     773 |       2930108 |             14.9329 |             9.7706 |           11.6399 |              9.5634 |           245.136  |     -0.8743 |
| unknown     | trailing_short    | B0_constant_last | B0       |           nan |      773 |     773 |        896051 |              9.2371 |             5.9229 |            6.7349 |              5.2922 |            50.7366 |      0.2959 |

## Row-Weighted RMSE Pivot

| mask_type         |   B0_constant_last |   B1_linear_md |   B2_tail_slope_k100 |   B2_tail_slope_k200 |   B2_tail_slope_k50 |   B2_tail_slope_k500 |
|:------------------|-------------------:|---------------:|---------------------:|---------------------:|--------------------:|---------------------:|
| high_curvature    |            99.0218 |        409.452 |             219.953  |             242.985  |            208.526  |             296.175  |
| high_gr_missing   |            39.7869 |        499.864 |             110.194  |             130.901  |            102.898  |             207.632  |
| mid_contiguous    |             8.4333 |        288.096 |              17.1653 |              16.8497 |             16.9512 |              15.9684 |
| original_hidden   |            15.9099 |       1404.73  |             116.257  |             119.933  |            112.557  |             155.285  |
| random_contiguous |            28.9184 |        461.489 |             120.236  |             148.225  |            110.177  |             202.913  |
| trailing_long     |            14.9329 |        729.62  |              66.7326 |              67.6414 |             66.3729 |              89.6189 |
| trailing_short    |             9.2371 |        139.003 |              16.3651 |              16.0539 |             17.1524 |              14.6114 |

## Acceptance Notes

- Artificial masks regenerate `TVT_input` from `TVT` only in the allowed known interval.
- Hidden target intervals never expose `TVT` to baseline features.
- This report is split-level only; row-level predictions are intentionally limited to the official-style original hidden CV.

## Outputs

- Split-level metrics: `outputs\baseline_multimask_by_split.csv`
- Overall metrics: `outputs\baseline_multimask_overall.csv`
