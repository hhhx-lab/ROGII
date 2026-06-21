# Part 3 Diagnostics

This report turns the Part 3 ideas into a routing table: estimate GR quality, estimate baseline confidence, mark whether typewell geology exists, and suggest which model family should handle the well.

## Split Summary

| split   |   wells |   mean_gr_quality |   mean_baseline_conf |   mean_risk |
|:--------|--------:|------------------:|---------------------:|------------:|
| test    |       3 |            0.2237 |               0.1157 |      0.9871 |
| train   |     773 |            0.1644 |               0.1118 |      0.9907 |

## Route Counts on Train Wells

|                    |   count |
|:-------------------|--------:|
| typewell_alignment |     635 |
| gr_residual        |      92 |
| baseline_fallback  |      35 |
| geometry_residual  |      11 |

## Route Rule

- `typewell_alignment`: GR is decent and typewell is informative enough to justify an alignment pass.
- `gr_residual`: GR is usable but alignment is not strong enough for direct typewell correction.
- `geometry_residual`: GR is weak, so geometry should dominate.
- `baseline_fallback`: the signal quality is too low for aggressive correction.

Diagnostics written to `outputs\part3_diagnostics.csv`.
