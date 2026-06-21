# Postprocess Report

- Variant: `balanced`
- Rows: 14,151

## OOF Summary

| metric      |   value | variant   |   delta |
|:------------|--------:|:----------|--------:|
| rmse_before | 48.71   | balanced  |  0      |
| rmse_after  | 48.6876 | balanced  | -0.0224 |
| mae_before  | 44.5885 | balanced  | -4.0991 |
| mae_after   | 44.5868 | balanced  | -0.0017 |
| p95_before  | 74.3978 | balanced  | 29.811  |
| p95_after   | 73.4916 | balanced  | -0.9062 |
| max_before  | 86.7135 | balanced  | 13.2218 |
| max_after   | 85.0693 | balanced  | -1.6441 |

## Worst Wells

| well     |   rows |   rmse_before |   rmse_after |   mae_before |   mae_after |
|:---------|-------:|--------------:|-------------:|-------------:|------------:|
| 00bbac68 |  12028 |       51.6663 |      51.641  |      47.3863 |     47.3851 |
| 000d7d20 |   7672 |       43.6741 |      43.6569 |      40.2021 |     40.1996 |

## Route Stats

| route              |   residual_low |   residual_high |   step_cap |
|:-------------------|---------------:|----------------:|-----------:|
| typewell_alignment |       -33.3511 |         19.5258 |      4.636 |

## Global Stats

|   residual_low |   residual_high |   step_cap |
|---------------:|----------------:|-----------:|
|       -33.3511 |         19.5258 |      4.636 |
