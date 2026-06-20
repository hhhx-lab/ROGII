# Baseline Submission Report

- Data hash: `46fd84d5e7e1`
- Submission rows: 14,151
- Baselines generated: 6

## Visible Example Aggregate RMSE

| data_hash    | baseline           | well                  |   predicted_rows |   known_allowed_end_row |   pred_min |   pred_max |   baseline_slope |   visible_train_rmse |
|:-------------|:-------------------|:----------------------|-----------------:|------------------------:|-----------:|-----------:|-----------------:|---------------------:|
| 46fd84d5e7e1 | B0_constant_last   | __visible_aggregate__ |            14151 |                     nan |    11604.8 |    12223.5 |              nan |              11.5393 |
| 46fd84d5e7e1 | B2_tail_slope_k200 | __visible_aggregate__ |            14151 |                     nan |    11604.8 |    12223.5 |              nan |              38.5016 |
| 46fd84d5e7e1 | B2_tail_slope_k500 | __visible_aggregate__ |            14151 |                     nan |    11604.9 |    12283.7 |              nan |              52.4315 |
| 46fd84d5e7e1 | B2_tail_slope_k100 | __visible_aggregate__ |            14151 |                     nan |    11604.9 |    12283.7 |              nan |              65.4063 |
| 46fd84d5e7e1 | B2_tail_slope_k50  | __visible_aggregate__ |            14151 |                     nan |    11604.9 |    12283.7 |              nan |              69.0045 |
| 46fd84d5e7e1 | B1_linear_md       | __visible_aggregate__ |            14151 |                     nan |    11813.3 |    15602.4 |              nan |            1548.92   |

## Per-Well Diagnostics

| data_hash    | baseline           | well     |   predicted_rows |   known_allowed_end_row |   pred_min |   pred_max |   baseline_slope |   visible_train_rmse |
|:-------------|:-------------------|:---------|-----------------:|------------------------:|-----------:|-----------:|-----------------:|---------------------:|
| 46fd84d5e7e1 | B0_constant_last   | 000d7d20 |             3836 |                    1441 |    11747.4 |    11747.4 |           0      |               7.4544 |
| 46fd84d5e7e1 | B0_constant_last   | 00bbac68 |             6014 |                    1544 |    12223.5 |    12223.5 |           0      |              15.2631 |
| 46fd84d5e7e1 | B0_constant_last   | 00e12e8b |             4301 |                    2082 |    11604.8 |    11604.8 |           0      |               7.9246 |
| 46fd84d5e7e1 | B1_linear_md       | 000d7d20 |             3836 |                    1441 |    11864.8 |    13025.5 |           0.3027 |             781.003  |
| 46fd84d5e7e1 | B1_linear_md       | 00bbac68 |             6014 |                    1544 |    12399.1 |    15602.4 |           0.5327 |            2010.78   |
| 46fd84d5e7e1 | B1_linear_md       | 00e12e8b |             4301 |                    2082 |    11813.3 |    13744   |           0.449  |            1302.31   |
| 46fd84d5e7e1 | B2_tail_slope_k50  | 000d7d20 |             3836 |                    1441 |    11747.4 |    11824.1 |           0.02   |              51.4052 |
| 46fd84d5e7e1 | B2_tail_slope_k50  | 00bbac68 |             6014 |                    1544 |    12223.5 |    12283.7 |           0.01   |              44.3803 |
| 46fd84d5e7e1 | B2_tail_slope_k50  | 00e12e8b |             4301 |                    2082 |    11604.9 |    11776.9 |           0.04   |             102.741  |
| 46fd84d5e7e1 | B2_tail_slope_k100 | 000d7d20 |             3836 |                    1441 |    11747.4 |    11785.7 |           0.01   |              29.2975 |
| 46fd84d5e7e1 | B2_tail_slope_k100 | 00bbac68 |             6014 |                    1544 |    12223.5 |    12283.7 |           0.01   |              44.3803 |
| 46fd84d5e7e1 | B2_tail_slope_k100 | 00e12e8b |             4301 |                    2082 |    11604.9 |    11776.9 |           0.04   |             102.741  |
| 46fd84d5e7e1 | B2_tail_slope_k200 | 000d7d20 |             3836 |                    1441 |    11747.4 |    11785.7 |           0.01   |              29.2975 |
| 46fd84d5e7e1 | B2_tail_slope_k200 | 00bbac68 |             6014 |                    1544 |    12163.4 |    12223.5 |          -0.01   |              30.1351 |
| 46fd84d5e7e1 | B2_tail_slope_k200 | 00e12e8b |             4301 |                    2082 |    11604.8 |    11690.8 |           0.02   |              53.3094 |
| 46fd84d5e7e1 | B2_tail_slope_k500 | 000d7d20 |             3836 |                    1441 |    11709   |    11747.4 |          -0.01   |              15.3027 |
| 46fd84d5e7e1 | B2_tail_slope_k500 | 00bbac68 |             6014 |                    1544 |    12223.5 |    12283.7 |           0.01   |              44.3803 |
| 46fd84d5e7e1 | B2_tail_slope_k500 | 00e12e8b |             4301 |                    2082 |    11604.9 |    11733.9 |           0.03   |              77.9869 |

## Output Files

- `submissions/b0_constant_last_submission.csv`
- `submissions/b1_linear_md_submission.csv`
- `submissions/b2_tail_slope_k50_submission.csv`
- `submissions/b2_tail_slope_k100_submission.csv`
- `submissions/b2_tail_slope_k200_submission.csv`
- `submissions/b2_tail_slope_k500_submission.csv`
- `submissions/baseline_tail_slope_submission.csv` kept for compatibility with earlier workflow
