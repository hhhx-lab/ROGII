# Residual Geometry Failure Analysis

## Worst Wells

| well     |    rmse |   mean_abs_error |     bias |   rows |
|:---------|--------:|-----------------:|---------:|-------:|
| 00bbac68 | 62.4207 |          57.1549 | -57.1549 |   6014 |
| 000d7d20 | 51.012  |          47.8717 |  47.8717 |   3836 |

## Best Wells

| well     |    rmse |   mean_abs_error |     bias |   rows |
|:---------|--------:|-----------------:|---------:|-------:|
| 000d7d20 | 51.012  |          47.8717 |  47.8717 |   3836 |
| 00bbac68 | 62.4207 |          57.1549 | -57.1549 |   6014 |

The first residual model is intentionally conservative: it should improve the easy geometry cases before it is trusted on harder structural shifts.
