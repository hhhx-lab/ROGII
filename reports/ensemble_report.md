# Ensemble Report

## CV Summary

| variant      |     rmse |
|:-------------|---------:|
| optimized    |  16.2932 |
| geometry     |  16.3081 |
| balanced     |  41.5657 |
| aggressive   |  59.3528 |
| conservative | 109.595  |
| baseline     | 119.933  |

## Optimized Route Weights

| route              |    rows |   geometry_weight |    rmse |
|:-------------------|--------:|------------------:|--------:|
| __global__         | 3783989 |              1    | 16.3081 |
| baseline_fallback  |  205186 |              1    | 20.2986 |
| geometry_residual  |   37915 |              1    | 11.5737 |
| gr_residual        |  461472 |              0.95 | 15.3679 |
| typewell_alignment | 3079416 |              1    | 16.1775 |

## Test Routing

| route       |   count |
|:------------|--------:|
| gr_residual |   14151 |

## Submission Files

- `submissions/conservative_submission.csv`
- `submissions/balanced_submission.csv`
- `submissions/aggressive_submission.csv`
- `submissions/optimized_submission.csv`
