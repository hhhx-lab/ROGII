# Ensemble Report

## CV Summary

| variant      |     rmse |
|:-------------|---------:|
| geometry     |  15.6288 |
| optimized    |  15.6288 |
| balanced     |  42.2231 |
| aggressive   |  59.9014 |
| conservative | 109.595  |
| baseline     | 119.933  |

## Optimized Route Weights

| route              |    rows |   geometry_weight |    rmse |
|:-------------------|--------:|------------------:|--------:|
| __global__         | 3783989 |                 1 | 15.6288 |
| baseline_fallback  |  205186 |                 1 | 19.5549 |
| geometry_residual  |   37915 |                 1 | 11.6032 |
| gr_residual        |  461472 |                 1 | 14.6272 |
| typewell_alignment | 3079416 |                 1 | 15.5225 |

## Test Routing

| route       |   count |
|:------------|--------:|
| gr_residual |   14151 |

## Submission Files

- `submissions/conservative_submission.csv`
- `submissions/balanced_submission.csv`
- `submissions/aggressive_submission.csv`
- `submissions/optimized_submission.csv`
