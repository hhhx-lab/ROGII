# Baseline Report

## Method

This baseline fills the missing evaluation interval per well by extrapolating `TVT_input` from the latest observed segment. It uses the median `dTVT/dMD` slope over the last 200 observed points, then writes predictions in Kaggle submission format.

## Output

- Submission: `submissions/baseline_tail_slope_submission.csv`
- Rows: 14,151

## Per-Well Diagnostics

| well     |   rows |   known_tvt_input |   predicted_rows |   pred_min |   pred_max |
|:---------|-------:|------------------:|-----------------:|-----------:|-----------:|
| 000d7d20 |   5278 |              1442 |             3836 |    11747.4 |    11785.7 |
| 00bbac68 |   7559 |              1545 |             6014 |    12163.4 |    12223.5 |
| 00e12e8b |   6384 |              2083 |             4301 |    11604.8 |    11690.8 |

## Local Visible-Test Check

- RMSE against matching train truth for the three visible example wells: 38.5016

This check is only a sanity test. It is not a reliable public leaderboard estimate because Kaggle replaces the visible test examples with hidden wells during submission reruns.
