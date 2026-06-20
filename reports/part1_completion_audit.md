# Part 1 Completion Audit

- Data hash: `46fd84d5e7e1`
- Checks: 40
- Failures: 0

## Checks

| check                                                                   | status   | evidence                                                                                                                                        |
|:------------------------------------------------------------------------|:---------|:------------------------------------------------------------------------------------------------------------------------------------------------|
| required output exists: outputs/data_contract_summary.csv               | PASS     |                                                                                                                                                 |
| required output exists: outputs/data_version.json                       | PASS     |                                                                                                                                                 |
| required output exists: outputs/baseline_cv_by_well.csv                 | PASS     |                                                                                                                                                 |
| required output exists: outputs/baseline_predictions_train_hidden.csv   | PASS     |                                                                                                                                                 |
| required output exists: outputs/cv_splits.csv                           | PASS     |                                                                                                                                                 |
| required output exists: outputs/failure_case_candidates.csv             | PASS     |                                                                                                                                                 |
| required report exists: reports/data_contract_report.md                 | PASS     |                                                                                                                                                 |
| required report exists: reports/baseline_cv_report.md                   | PASS     |                                                                                                                                                 |
| required report exists: reports/cv_design.md                            | PASS     |                                                                                                                                                 |
| required report exists: reports/baseline_failure_analysis.md            | PASS     |                                                                                                                                                 |
| required report exists: reports/baseline_multimask_report.md            | PASS     |                                                                                                                                                 |
| required report exists: reports/baseline_submission_report.md           | PASS     |                                                                                                                                                 |
| required report exists: reports/part1_quality_review.md                 | PASS     |                                                                                                                                                 |
| progress document exists: docs/plans/01_validation_baseline_progress.md | PASS     |                                                                                                                                                 |
| data_version contains required fields                                   | PASS     | created_at,raw_file_count,sample_submission_rows,test_well_count,train_well_count,zip_path,zip_sha256,zip_size_bytes                            |
| train_well_count == 773                                                 | PASS     |                                                                                                                                                 |
| test_well_count == 3                                                    | PASS     |                                                                                                                                                 |
| data contract critical errors == 0                                      | PASS     | 0                                                                                                                                               |
| data contract compares against EDA inventory                            | PASS     |                                                                                                                                                 |
| baseline CV covers 773 wells for every baseline                         | PASS     | 773                                                                                                                                             |
| baseline families include B0/B1/B2                                      | PASS     | B0,B1,B2                                                                                                                                        |
| baseline configs include B2 K variants                                  | PASS     | B0_constant_last,B1_linear_md,B2_tail_slope_k100,B2_tail_slope_k200,B2_tail_slope_k50,B2_tail_slope_k500                                        |
| row-level baseline predictions cover every target row and baseline      | PASS     | actual=22703934, expected=22703934                                                                                                              |
| cv_splits has at least 5 mask types                                     | PASS     | 7                                                                                                                                               |
| each mask type covers at least 300 wells                                | PASS     | 773                                                                                                                                             |
| cv_splits has leakage boundary columns                                  | PASS     |                                                                                                                                                 |
| apply_cv_split_mask hides target and future TVT_input                   | PASS     | high_curvature:True,high_gr_missing:True,mid_contiguous:True,original_hidden:True,random_contiguous:True,trailing_long:True,trailing_short:True |
| truth-derived split diagnostics are documented as non-features          | PASS     |                                                                                                                                                 |
| multi-mask baseline metrics cover all split mask types                  | PASS     | 7                                                                                                                                               |
| failure candidates cover 773 wells                                      | PASS     | 773                                                                                                                                             |
| worst-well diagnostic figures count >= 20                               | PASS     | 20                                                                                                                                              |
| failure types are populated                                             | PASS     | long_extrapolation,missing_gr,slope_change,smooth_bias                                                                                          |
| failure candidates include typewell and Geology diagnostics             | PASS     | typewell_geology_label_count,typewell_geology_labels,typewell_gr_missing_rate,typewell_rows,typewell_tvt_span                                   |
| submission valid: submissions/b0_constant_last_submission.csv           | PASS     | rows=14151, wells=3                                                                                                                             |
| submission valid: submissions/b1_linear_md_submission.csv               | PASS     | rows=14151, wells=3                                                                                                                             |
| submission valid: submissions/b2_tail_slope_k50_submission.csv          | PASS     | rows=14151, wells=3                                                                                                                             |
| submission valid: submissions/b2_tail_slope_k100_submission.csv         | PASS     | rows=14151, wells=3                                                                                                                             |
| submission valid: submissions/b2_tail_slope_k200_submission.csv         | PASS     | rows=14151, wells=3                                                                                                                             |
| submission valid: submissions/b2_tail_slope_k500_submission.csv         | PASS     | rows=14151, wells=3                                                                                                                             |
| submission valid: submissions/baseline_tail_slope_submission.csv        | PASS     | rows=14151, wells=3                                                                                                                             |

## Result

PASS
