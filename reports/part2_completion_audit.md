# Part 2 Completion Audit

- Primary spec: `geometry`
- Checks: 25
- Failures: 0

## Checks

| check                                                                                  | status   | evidence                                             |
|:---------------------------------------------------------------------------------------|:---------|:-----------------------------------------------------|
| required feature exists: features\baseline_features_train.csv                          | PASS     | present                                              |
| required feature exists: features\baseline_features_test.csv                           | PASS     | present                                              |
| required feature exists: features\geometry_features_train.csv                          | PASS     | present                                              |
| required feature exists: features\geometry_features_test.csv                           | PASS     | present                                              |
| required feature exists: features\residual_targets.csv                                 | PASS     | present                                              |
| required geometry model artifact exists: models\residual_geometry_hgb.pkl              | PASS     | present                                              |
| required geometry model artifact exists: models\residual_geometry_hgb_config.json      | PASS     | present                                              |
| required geometry model artifact exists: models\residual_geometry_hgb_feature_list.txt | PASS     | present                                              |
| required geometry output exists: outputs\residual_geometry_oof.csv                     | PASS     | present                                              |
| required geometry output exists: outputs\residual_geometry_cv_by_well.csv              | PASS     | present                                              |
| required geometry output exists: outputs\residual_geometry_test_predictions.csv        | PASS     | present                                              |
| required geometry report exists: reports\residual_target_report.md                     | PASS     | present                                              |
| required geometry report exists: reports\residual_geometry_cv_report.md                | PASS     | present                                              |
| required geometry submission exists: submissions\geometry_residual_submission.csv      | PASS     | present                                              |
| train feature keys align with residual targets                                         | PASS     | rows=3783989                                         |
| test feature keys align                                                                | PASS     | rows=14151                                           |
| residual targets are finite                                                            | PASS     | rows=3783989 wells=773                               |
| model config records feature columns                                                   | PASS     | models\residual_geometry_hgb_config.json features=25 |
| feature list excludes well id, truth and training-only formation surfaces              | PASS     |                                                      |
| geometry residual submission matches sample format                                     | PASS     | rows=14151 sample=14151                              |
| geometry residual submission covers sample wells                                       | PASS     | 3                                                    |
| geometry residual OOF predictions cover every residual target row                      | PASS     | oof=3783989, targets=3783989                         |
| per-well geometry residual CV is finite                                                | PASS     | wells=773                                            |
| optional xgb/tree residual artifacts                                                   | SKIP     | not generated in this run                            |
| reports describe residual CV metrics                                                   | PASS     |                                                      |

## Result

PASS
