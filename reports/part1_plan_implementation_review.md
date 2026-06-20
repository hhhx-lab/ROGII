# Part 1 Plan Implementation Review

## Scope

This report maps `docs/plans/01_validation_baseline.md` to concrete scripts, outputs, reports, and raw-data boundary checks. It is intentionally stricter than a file-exists smoke test.

## Plan Requirements

| area             | requirement                                                                         | status   | evidence                                                                          | missing   |
|:-----------------|:------------------------------------------------------------------------------------|:---------|:----------------------------------------------------------------------------------|:----------|
| 数据契约             | 训练井 horizontal/typewell/png 完整，visible test horizontal/typewell 完整                  | PASS     | outputs/data_contract_summary.csv, reports/data_contract_report.md                |           |
| 数据版本             | 记录数据 hash、井数、sample submission 行数，所有报告可追溯                                           | PASS     | outputs/data_version.json                                                         |           |
| 原始隐藏段 CV         | 773 口训练井的 PS 后原始隐藏尾段全部进入 baseline CV                                                | PASS     | outputs/baseline_cv_by_well.csv, reports/baseline_cv_report.md                    |           |
| Baseline 家族      | Part 1 至少完成 B0/B1/B2，B2 包含多个 tail window                                            | PASS     | outputs/baseline_overall_metrics.csv                                              |           |
| 多 mask 验证        | 至少 5 类 mask，每类至少 300 口井，并区分官方 tail proxy 与压力测试                                      | PASS     | outputs/cv_splits.csv, reports/cv_design.md, reports/baseline_multimask_report.md |           |
| 防泄漏              | 人工 mask 必须隐藏 target/future TVT_input，truth-derived split diagnostics 不可作为 predictor | PASS     | scripts/rogii_utils.py, reports/cv_design.md                                      |           |
| Failure analysis | 773 口井输出失败候选、预定义失败类型、worst 20 图表和 typewell 诊断                                       | PASS     | outputs/failure_case_candidates.csv, reports/baseline_failure_analysis.md         |           |
| Submission QA    | 生成 B0/B1/B2 baseline submission，visible test 只作为格式 sanity                           | PASS     | reports/baseline_submission_report.md, submissions/                               |           |
| Raw-data 边界      | PPTX/sample/train/test 核对结论已进入计划，test Geology optional，visible test 不调参             | PASS     | reports/data_raw_review.md, docs/plans/01_validation_baseline.md                  |           |

## Raw-Data Boundary Checks

| check                                                                             | status   | evidence                   |
|:----------------------------------------------------------------------------------|:---------|:---------------------------|
| visible test wells overlap train and are sanity-only examples                     | PASS     | 000d7d20,00bbac68,00e12e8b |
| all train wells use one PS-to-tail hidden interval and known TVT_input equals TVT | PASS     | train_wells=773            |
| visible test sample is PS-to-tail target with no TVT truth column                 | PASS     | sample_rows=14151          |
| visible test typewell has TVT/GR and no required Geology                          | PASS     | test_typewell_files=3      |

## Result

- Checks: 13
- Failures: 0
- Status: PASS

## Notes

- B3/B4 remain intentionally deferred; Part 1 acceptance requires B0/B1/B2, and the current baseline evidence shows slope extrapolation is a risky stress-test rather than the main baseline.
- `outputs/` is local-only and regenerated from scripts; the review checks local reproducibility artifacts without committing them.
- Visible test wells overlap training IDs and are treated only as format and runtime sanity checks.
