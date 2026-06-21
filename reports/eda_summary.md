# ROGII EDA Summary

## Dataset Inventory

- Train horizontal CSV files: 773
- Train typewell CSV files: 773
- Train PNG visualizations: 773
- Visible test horizontal CSV files: 3
- Visible test typewell CSV files: 3
- Sample submission rows: 14,151

## Horizontal Well Columns

`MD`, `X`, `Y`, `Z`, `ANCC`, `ASTNU`, `ASTNL`, `EGFDU`, `EGFDL`, `BUDA`, `TVT`, `GR`, `TVT_input`

## Train Row Statistics

|       |     rows |   md_min |   md_max |   tvt_min |   tvt_max |   gr_missing |   tvt_input_missing |
|:------|---------:|---------:|---------:|----------:|----------:|-------------:|--------------------:|
| count |   773    |   773    |   773    |    773    |    773    |       773    |              773    |
| mean  |  6587.65 | 10900.5  | 17487.1  |  10834.4  |  11568.8  |      1950.8  |             4895.2  |
| std   |  1311.46 |   645.75 |  1428.48 |    635.42 |    620.04 |      1391.02 |             1301.18 |
| min   |  2058    |  9335    | 12854    |   9245.19 |  10072.2  |        42    |              407    |
| 25%   |  5706    | 10403    | 16511    |  10353.1  |  11052.5  |       767    |             4044    |
| 50%   |  6576    | 10746    | 17522    |  10650.9  |  11384.6  |      1754    |             4840    |
| 75%   |  7388    | 11434    | 18378    |  11358.3  |  12067.5  |      2992    |             5694    |
| max   | 12141    | 12573    | 22964    |  12444.1  |  12893.9  |      7289    |            10052    |

## Visible Test Summary

| well     |   rows |   submission_rows |   gr_missing |   tvt_input_missing |
|:---------|-------:|------------------:|-------------:|--------------------:|
| 000d7d20 |   5278 |              3836 |         2258 |                3836 |
| 00bbac68 |   7559 |              6014 |          942 |                6014 |
| 00e12e8b |   6384 |              4301 |          584 |                4301 |

## Missing Values Across Train Horizontal Files

| Column | Missing values | Missing rate |
|---|---:|---:|
| ANCC | 45,634 | 0.90% |
| ASTNL | 0 | 0.00% |
| ASTNU | 0 | 0.00% |
| BUDA | 0 | 0.00% |
| EGFDL | 6,067 | 0.12% |
| EGFDU | 0 | 0.00% |
| GR | 1,507,972 | 29.61% |
| MD | 0 | 0.00% |
| TVT | 0 | 0.00% |
| TVT_input | 3,783,989 | 74.31% |
| X | 0 | 0.00% |
| Y | 0 | 0.00% |
| Z | 0 | 0.00% |

## Typewell Geology Labels

| Label | Count |
|---|---:|
| ANCC | 294,268 |
| EGFDL | 205,397 |
| ASTNL | 172,223 |
| BUDA | 140,640 |
| ASTNU | 118,025 |
| EGFDU | 70,013 |
| OLMOS | 23,345 |
| MNSS | 5,026 |
| UPSN | 2,731 |
| LBHL | 1,625 |
| LTHL | 1,137 |
| LTGT | 981 |
| Clay Rich Interval | 868 |
| AC_UEF_BHL | 840 |
| AC_UEF_TRGT | 840 |
| AC_UEF_THL | 840 |
| UTGT | 760 |
| UTHL | 589 |
| UEGFD THL | 570 |
| UEGFD TGT | 570 |
| LL_BHL | 444 |
| UEGFD BHL | 323 |
| LL_THL | 276 |
| UL_THL | 258 |
| UL_TGT | 216 |
| UBHL | 190 |
| LL_TGT | 144 |
| UL_BHL | 120 |
| LLEF BHL | 69 |
| LLEF THL | 36 |
| ULEF TGT | 35 |
| EGFD400 | 34 |
| LL THL | 30 |
| LLEF TGT | 26 |
| EGFD300 | 23 |
| EGFD300c | 18 |
| ULEF THL | 16 |
| LL TGT | 10 |
| EGFD100 | 8 |
| EGFD_IPT | 2 |
| EGFD300b | 2 |
| ULEF BHL | 2 |
| EGFD200 | 1 |

## First Observations

- The public test folder contains only three example wells; hidden evaluation wells are substituted by Kaggle at submission time.
- `TVT_input` is available before the evaluation interval and missing exactly where `sample_submission.csv` asks for predictions.
- A per-well extrapolation baseline is a strong first sanity check because visible targets continue from the known `TVT_input` segment.
- Stronger models should use cross-well validation rather than trusting the three visible test wells.

Data root resolved as: `data`
