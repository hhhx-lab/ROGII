# Residual Target Report

- Data hash: `46fd84d5e7e1`
- Baseline anchor: `B0_constant_last`
- Train rows: 3,783,989
- Train wells: 773
- Test rows: 14,151

## Residual Distribution

|   mean |     std |    p01 |    p05 |   p50 |   p95 |   p99 |     min |   max |
|-------:|--------:|-------:|-------:|------:|------:|------:|--------:|------:|
|  1.596 | 15.8296 | -39.66 | -22.52 |  0.84 | 26.33 | 47.82 | -103.78 | 98.92 |

## Residual by Well

|        | well     |     rows |   residual_mean |   residual_std |
|:-------|:---------|---------:|----------------:|---------------:|
| count  | 773      |   773    |      773        |      773       |
| unique | 773      |          |                 |                |
| top    | 000d7d20 |          |                 |                |
| freq   | 1        |          |                 |                |
| mean   |          |  4895.2  |        1.42318  |        7.85442 |
| std    |          |  1301.18 |       12.6984   |        4.30593 |
| min    |          |   407    |      -46.5001   |        1.00759 |
| 25%    |          |  4044    |       -5.26933  |        5.09129 |
| 50%    |          |  4840    |        0.942878 |        6.90942 |
| 75%    |          |  5694    |        8.12702  |        9.52432 |
| max    |          | 10052    |       65.9312   |       33.5378  |

## Residual by Target Length

| target_length_bucket   |    rows |   wells |   residual_mean |   residual_std |   residual_rmse |   median_abs_residual |   p95_abs_residual |
|:-----------------------|--------:|--------:|----------------:|---------------:|----------------:|----------------------:|-------------------:|
| 0-500                  |     407 |       1 |         -1.1742 |         2.2724 |          2.5553 |                  1.97 |               4.09 |
| 501-1500               |     911 |       1 |          2.9492 |         2.0677 |          3.6012 |                  2.37 |               7.6  |
| 1501-3000              |  114845 |      44 |          0.3832 |        12.4727 |         12.4785 |                  5.31 |              25.78 |
| 3001-5000              | 1613495 |     386 |          1.2577 |        15.6704 |         15.7208 |                  7.6  |              30.52 |
| 5001+                  | 2054331 |     341 |          1.9294 |        16.1152 |         16.2302 |                  8.53 |              33.82 |

## Residual by Baseline Error Bucket

| baseline_abs_error_bucket   |   rows |   wells |   residual_mean |   residual_std |   residual_rmse |   median_abs_residual |   p95_abs_residual |
|:----------------------------|-------:|--------:|----------------:|---------------:|----------------:|----------------------:|-------------------:|
| q1_lowest                   | 756798 |     773 |          0.0292 |         1.3761 |          1.3764 |                  1.1  |               2.37 |
| q2                          | 756798 |     772 |          0.1154 |         4.274  |          4.2756 |                  4.12 |               5.77 |
| q3                          | 756797 |     758 |          0.4679 |         8.2058 |          8.2191 |                  8.03 |              10.31 |
| q4                          | 756798 |     692 |          1.7752 |        13.8211 |         13.9346 |                 13.67 |              17.13 |
| q5_highest                  | 756798 |     478 |          5.5922 |        30.8617 |         31.3642 |                 24.68 |              53.13 |

## Residual by GR Missing Rate

| gr_missing_bucket   |    rows |   wells |   residual_mean |   residual_std |   residual_rmse |   median_abs_residual |   p95_abs_residual |
|:--------------------|--------:|--------:|----------------:|---------------:|----------------:|----------------------:|-------------------:|
| 0-25%               | 1556967 |     321 |          1.098  |        16.4409 |         16.4775 |                  7.9  |            34.59   |
| 25-50%              | 1287715 |     264 |          1.5877 |        14.746  |         14.8312 |                  8.23 |            29.85   |
| 50-75%              |  917362 |     184 |          1.9648 |        15.0771 |         15.2046 |                  7.92 |            29.6995 |
| 75-100%             |   21945 |       4 |         21.9961 |        36.4421 |         42.5652 |                  8.12 |            85.6    |

## Outputs

- Baseline train features: `features/baseline_features_train.parquet`
- Baseline test features: `features/baseline_features_test.parquet`
- Residual targets: `features/residual_targets.parquet`

## Server Scaling

Feature generation is full-row and deterministic. Model training can be scaled independently with `ROGII_PART2_TRAIN_ROWS_PER_WELL=0` on a server.
