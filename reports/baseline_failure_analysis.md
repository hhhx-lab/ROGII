# Baseline Failure Analysis

- Data hash: `46fd84d5e7e1`
- Baseline analyzed: `B0_constant_last`
- Candidate wells: 773
- Diagnostic figures: `reports/figures/baseline_worst_wells`

## Primary Failure Types

| failure_type       |   wells |
|:-------------------|--------:|
| smooth_bias        |     418 |
| slope_change       |     194 |
| abrupt_shift       |       0 |
| gr_transition      |       0 |
| long_extrapolation |      72 |
| missing_gr         |      89 |

## Failure Tags

| failure_tag        |   wells |
|:-------------------|--------:|
| smooth_bias        |     514 |
| slope_change       |     194 |
| missing_gr         |     189 |
| long_extrapolation |     142 |
| abrupt_shift       |       0 |
| gr_transition      |       0 |

## Worst 20 Wells

| data_hash    | baseline         | well     |    rmse |     mae |     bias |   max_abs_error |   target_rows |   target_md_span |   target_tvt_span |   target_gr_missing_rate |   baseline_slope |   typewell_rows |   typewell_tvt_span |   typewell_gr_missing_rate |   typewell_geology_label_count | typewell_geology_labels                                                                | failure_type   | failure_tags                                           |
|:-------------|:-----------------|:---------|--------:|--------:|---------:|----------------:|--------------:|-----------------:|------------------:|-------------------------:|-----------------:|----------------:|--------------------:|---------------------------:|-------------------------------:|:---------------------------------------------------------------------------------------|:---------------|:-------------------------------------------------------|
| 46fd84d5e7e1 | B0_constant_last | 1b1eba53 | 70.6394 | 65.9312 | -65.9312 |           98.92 |          4655 |             4654 |             98.88 |                   0.1631 |                0 |            2414 |             1206.5  |                          0 |                              5 | ASTNL|ASTNU|BUDA|EGFDL|EGFDU                                                           | slope_change   | smooth_bias,slope_change                               |
| 46fd84d5e7e1 | B0_constant_last | 86454a6f | 70.2634 | 65.8288 | -65.8288 |           96.69 |          7964 |             7963 |             96.68 |                   0.8118 |                0 |             645 |              322    |                          0 |                              4 | ASTNL|BUDA|EGFDL|EGFDU                                                                 | slope_change   | smooth_bias,slope_change,long_extrapolation,missing_gr |
| 46fd84d5e7e1 | B0_constant_last | a959858c | 65.3587 | 63.6659 | -63.6659 |           91.06 |          4404 |             4403 |             90.53 |                   0.614  |                0 |            5482 |             1369.74 |                          0 |                              7 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU|MNSS                                                 | smooth_bias    | smooth_bias,missing_gr                                 |
| 46fd84d5e7e1 | B0_constant_last | 2fd68f7b | 60.7402 | 56.0657 | -56.0197 |           75.13 |          4730 |             4729 |             75.99 |                   0.614  |                0 |            1782 |              890.47 |                          0 |                              6 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU                                                      | slope_change   | smooth_bias,slope_change,missing_gr                    |
| 46fd84d5e7e1 | B0_constant_last | 5f4d2a52 | 56.9149 | 47.2092 | -47.1666 |           93.29 |          5225 |             5224 |             93.91 |                   0.2151 |                0 |            1927 |              962.93 |                          0 |                             10 | AC_UEF_BHL|AC_UEF_THL|AC_UEF_TRGT|ANCC|ASTNL|ASTNU|BUDA|Clay Rich Interval|EGFDL|EGFDU | slope_change   | smooth_bias,slope_change                               |
| 46fd84d5e7e1 | B0_constant_last | f88ddb26 | 51.4031 | 46.5001 |  46.5001 |           78.62 |          4990 |             4989 |             78.59 |                   0.0373 |                0 |            1006 |              502.48 |                          0 |                              6 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU                                                      | slope_change   | smooth_bias,slope_change                               |
| 46fd84d5e7e1 | B0_constant_last | ba48188d | 50.9372 | 38.507  |  38.3416 |          103.78 |          4166 |             4165 |            104.99 |                   0.1769 |                0 |            1203 |              601    |                          0 |                              6 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU                                                      | slope_change   | smooth_bias,slope_change                               |
| 46fd84d5e7e1 | B0_constant_last | 389ae58f | 49.763  | 47.8121 | -47.8121 |           68.56 |          6463 |             6462 |             68.5  |                   0.1954 |                0 |            1972 |              985.5  |                          0 |                             10 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU|LBHL|LTGT|LTHL|MNSS                                  | slope_change   | smooth_bias,slope_change,long_extrapolation            |
| 46fd84d5e7e1 | B0_constant_last | f6d009f4 | 47.0392 | 40.2779 | -40.2779 |           84.76 |          6715 |             6714 |             84.48 |                   0.3232 |                0 |            2251 |             1125    |                          0 |                              6 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU                                                      | smooth_bias    | smooth_bias,long_extrapolation                         |
| 46fd84d5e7e1 | B0_constant_last | 43e16325 | 45.7767 | 37.5208 | -37.5043 |           84.13 |          3720 |             3719 |             84.48 |                   0.1605 |                0 |            2417 |             1207.78 |                          0 |                              7 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU|MNSS                                                 | slope_change   | smooth_bias,slope_change                               |
| 46fd84d5e7e1 | B0_constant_last | fef8af96 | 44.5517 | 37.3204 |  37.2538 |           87.86 |          3826 |             3825 |             88.76 |                   0.3489 |                0 |            1316 |              657.43 |                          0 |                              7 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU|MNSS                                                 | slope_change   | smooth_bias,slope_change                               |
| 46fd84d5e7e1 | B0_constant_last | fb03ae90 | 42.8876 | 41.4537 |  41.4537 |           50.8  |          6431 |             6430 |             50.76 |                   0.169  |                0 |            1985 |              992    |                          0 |                              7 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU|OLMOS                                                | smooth_bias    | smooth_bias,long_extrapolation                         |
| 46fd84d5e7e1 | B0_constant_last | c8d9680c | 42.7704 | 39.5914 | -39.1037 |           56.51 |          6281 |             6280 |             63.59 |                   0.3856 |                0 |            1377 |              687.59 |                          0 |                              6 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU                                                      | slope_change   | smooth_bias,slope_change,long_extrapolation            |
| 46fd84d5e7e1 | B0_constant_last | 91db7070 | 40.8075 | 34.4789 | -34.4789 |           62.39 |          4073 |             4072 |             62.36 |                   0.3337 |                0 |            3039 |              759.5  |                          0 |                              7 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU|MNSS                                                 | slope_change   | smooth_bias,slope_change                               |
| 46fd84d5e7e1 | B0_constant_last | 7e721392 | 40.3318 | 37.7314 |  37.7314 |           53.05 |          6174 |             6173 |             53.02 |                   0.5672 |                0 |            2194 |             1096.5  |                          0 |                              7 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU|OLMOS                                                | slope_change   | smooth_bias,slope_change,long_extrapolation,missing_gr |
| 46fd84d5e7e1 | B0_constant_last | 25050f63 | 37.9966 | 37.1329 | -37.1329 |           48.54 |          6124 |             6123 |             48.36 |                   0.05   |                0 |            1743 |              870.99 |                          0 |                              6 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU                                                      | smooth_bias    | smooth_bias,long_extrapolation                         |
| 46fd84d5e7e1 | B0_constant_last | 4c2208f5 | 37.3819 | 35.3869 | -35.3869 |           49.79 |          5384 |             5383 |             49.77 |                   0.0377 |                0 |            2171 |             1085    |                          0 |                              5 | ASTNL|ASTNU|BUDA|EGFDL|EGFDU                                                           | smooth_bias    | smooth_bias                                            |
| 46fd84d5e7e1 | B0_constant_last | 94d813a4 | 36.7309 | 29.4229 |  29.4219 |           61.39 |          4847 |             4846 |             61.44 |                   0.2864 |                0 |            1927 |              963    |                          0 |                              7 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU|MNSS                                                 | slope_change   | smooth_bias,slope_change                               |
| 46fd84d5e7e1 | B0_constant_last | 206b6193 | 36.509  | 31.5079 |  31.5079 |           70.07 |          6535 |             6534 |             70.07 |                   0.041  |                0 |            1776 |              887.13 |                          0 |                              6 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU                                                      | slope_change   | smooth_bias,slope_change,long_extrapolation            |
| 46fd84d5e7e1 | B0_constant_last | 57f05c51 | 36.3245 | 31.4785 | -31.4737 |           63.52 |          4771 |             4770 |             63.83 |                   0.0581 |                0 |            2380 |             1189.45 |                          0 |                              6 | ANCC|ASTNL|ASTNU|BUDA|EGFDL|EGFDU                                                      | slope_change   | smooth_bias,slope_change                               |

## Engineering Interpretation

- `smooth_bias` indicates a mostly coherent offset and is the cleanest first target for residual modeling.
- `slope_change` and `abrupt_shift` indicate that pure continuation is too weak and geometry/typewell alignment should be prioritized.
- `gr_transition` marks wells where GR morphology can plausibly locate stratigraphic movement.
- `long_extrapolation` and `missing_gr` should route to conservative fallback and uncertainty controls.
- `typewell_*` columns in `failure_case_candidates.csv` are structured checks that the plotted typewell GR and Geology bands exist and can be joined in Part 3.

Detailed candidates: `outputs/failure_case_candidates.csv`
