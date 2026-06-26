# Postprocess Report

- Variant: `geometry`
- OOF path: `C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\outputs\residual_geometry_oof.csv`
- Rows: 14,151
- Decision: `rejected`
- Decision reason: `oof_improvement_guard_failed`
- RMSE before: `15.628804658466327`
- RMSE after: `69.92550348606268`
- Actual RMSE improvement: `-54.29669882759635`
- Minimum required improvement: `0.0`

## OOF Summary

| metric      |     value | variant   |     delta |
|:------------|----------:|:----------|----------:|
| rmse_before |   15.6288 | geometry  |    0      |
| rmse_after  |   69.9255 | geometry  |   54.2967 |
| mae_before  |   11.1732 | geometry  |  -58.7523 |
| mae_after   |   15.6371 | geometry  |    4.4639 |
| p95_before  |   31.945  | geometry  |   16.3079 |
| p95_after   |   34.9359 | geometry  |    2.991  |
| max_before  |  105.237  | geometry  |   70.3014 |
| max_after   | 1928.08   | geometry  | 1822.84   |

## Worst Wells

| well     |   rows |   rmse_before |   rmse_after |   mae_before |   mae_after |
|:---------|-------:|--------------:|-------------:|-------------:|------------:|
| f6d009f4 |   6715 |       25.3652 |    1195.27   |      22.2827 |   1003.19   |
| 25050f63 |   6124 |       14.8766 |     959.355  |      13.1738 |    792.044  |
| a959858c |   4404 |       34.6156 |     656.614  |      31.6282 |    587.206  |
| 884ecb5f |   6724 |       22.3468 |     109.458  |      20.3741 |     81.3528 |
| fb03ae90 |   6431 |       38.4012 |     101.184  |      37.108  |     75.6604 |
| 684a6fc1 |   9818 |       15.2438 |      85.2876 |      13.4316 |     55.1196 |
| 57f05c51 |   4771 |       40.4712 |      84.7604 |      35.7182 |     64.8677 |
| 7271dd80 |   4340 |        4.7255 |      78.8809 |       3.6688 |     49.2896 |
| 521a7819 |   5200 |       30.2307 |      76.6305 |      27.9691 |     57.1106 |
| 7c607683 |   5328 |       13.1377 |      70.6379 |      12.4274 |     44.7817 |
| b95e7121 |   6306 |        8.9128 |      70.298  |       6.8851 |     41.1199 |
| 1b1eba53 |   4655 |       69.3534 |      69.3534 |      65.0419 |     65.0419 |
| 466fc788 |   6197 |       20.6258 |      65.7562 |      17.481  |     43.1428 |
| 86454a6f |   7964 |       64.3403 |      64.3404 |      60.2149 |     60.2151 |
| 5f4d2a52 |   5225 |       59.4918 |      59.4918 |      49.5215 |     49.5215 |

## Route Stats

| route              |   residual_low |   residual_high |   step_cap |
|:-------------------|---------------:|----------------:|-----------:|
| baseline_fallback  |      -191.326  |         306.116 |     0.1107 |
| geometry_residual  |       -81.6301 |         139.924 |     0.099  |
| gr_residual        |      -270.433  |         244.541 |     0.2891 |
| typewell_alignment |      -253.599  |         226.992 |     0.1284 |

## Global Stats

|   residual_low |   residual_high |   step_cap |
|---------------:|----------------:|-----------:|
|        -249.32 |         236.383 |     0.1295 |
