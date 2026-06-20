# Part 2 Completion Audit

- Checks: 34
- Failures: 0

## Checks

| check                                                                     | status   | evidence                                                                                                               |
|:--------------------------------------------------------------------------|:---------|:-----------------------------------------------------------------------------------------------------------------------|
| required feature exists: features/baseline_features_train.parquet         | PASS     |                                                                                                                        |
| required feature exists: features/baseline_features_test.parquet          | PASS     |                                                                                                                        |
| required feature exists: features/geometry_features_train.parquet         | PASS     |                                                                                                                        |
| required feature exists: features/geometry_features_test.parquet          | PASS     |                                                                                                                        |
| required feature exists: features/residual_targets.parquet                | PASS     |                                                                                                                        |
| required model artifact exists: models/residual_geometry_hgb.pkl          | PASS     |                                                                                                                        |
| required model artifact exists: models/residual_geometry_config.json      | PASS     |                                                                                                                        |
| required model artifact exists: models/residual_geometry_feature_list.txt | PASS     |                                                                                                                        |
| required output exists: outputs/residual_geometry_oof.csv                 | PASS     |                                                                                                                        |
| required output exists: outputs/residual_geometry_cv_by_well.csv          | PASS     |                                                                                                                        |
| required output exists: outputs/residual_geometry_test_predictions.csv    | PASS     |                                                                                                                        |
| required output exists: outputs/residual_geometry_multimask_by_split.csv  | PASS     |                                                                                                                        |
| required output exists: outputs/residual_geometry_multimask_overall.csv   | PASS     |                                                                                                                        |
| required report exists: reports/residual_target_report.md                 | PASS     |                                                                                                                        |
| required report exists: reports/residual_geometry_cv_report.md            | PASS     |                                                                                                                        |
| required report exists: reports/residual_geometry_failure_analysis.md     | PASS     |                                                                                                                        |
| required report exists: reports/residual_geometry_feature_importance.md   | PASS     |                                                                                                                        |
| required report exists: reports/residual_geometry_multimask_report.md     | PASS     |                                                                                                                        |
| required report exists: reports/residual_geometry_server_runbook.md       | PASS     |                                                                                                                        |
| required submission exists: submissions/geometry_residual_submission.csv  | PASS     |                                                                                                                        |
| train feature keys align with residual targets                            | PASS     | rows=3783989                                                                                                           |
| test feature keys align                                                   | PASS     | rows=14151                                                                                                             |
| features cover 773 train wells                                            | PASS     | 773                                                                                                                    |
| model config records feature columns and selected alpha                   | PASS     | features=77, alpha=0.75                                                                                                |
| feature list excludes well id, truth and training-only formation surfaces | PASS     |                                                                                                                        |
| server runbook documents full-row training command                        | PASS     |                                                                                                                        |
| geometry residual submission matches sample format                        | PASS     | rows=14151                                                                                                             |
| geometry residual submission covers sample wells                          | PASS     | 3                                                                                                                      |
| OOF predictions cover every residual target row                           | PASS     | oof=3783989, targets=3783989                                                                                           |
| per-well residual CV covers 773 wells                                     | PASS     | 773                                                                                                                    |
| multi-mask residual validation covers required mask types                 | PASS     | mid_contiguous,original_hidden,random_contiguous,trailing_long,trailing_short                                          |
| multi-mask residual validation covers every train well per mask           | PASS     | {"mid_contiguous": 773, "original_hidden": 773, "random_contiguous": 773, "trailing_long": 773, "trailing_short": 773} |
| multi-mask residual metrics are finite                                    | PASS     |                                                                                                                        |
| reports state promotion decision or server readiness                      | PASS     |                                                                                                                        |

## Result

PASS
