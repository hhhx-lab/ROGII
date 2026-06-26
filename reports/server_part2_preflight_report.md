# Server Part 2 Preflight Report

- Created at: `2026-06-26T16:21:17.543302+00:00`
- Python: `3.13.7`
- Platform: `Windows-11-10.0.26200-SP0`
- Checks: 23
- Failures: 0
- Warnings: 2

## Checks

| Status | Check | Evidence | Critical |
|---|---|---|---|
| PASS | free disk is at least 25 GB | 1015.5 GB | True |
| PASS | free disk recommended at least 80 GB | 1015.5 GB | False |
| PASS | running inside a project or conda environment | C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv | False |
| WARN | RAM amount can be detected | unknown | False |
| PASS | python package available: joblib |  | True |
| PASS | python package available: matplotlib |  | True |
| PASS | python package available: numpy |  | True |
| PASS | python package available: pandas |  | True |
| PASS | python package available: pyarrow |  | True |
| PASS | python package available: scikit-learn |  | True |
| PASS | python package available: tabulate |  | True |
| PASS | competition data root exists | C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\data\raw | True |
| PASS | train directory exists | C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\data\raw\train | True |
| PASS | test directory exists | C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\data\raw\test | True |
| PASS | sample submission is loadable or synthesizable | rows=14151 | True |
| PASS | task PPTX exists |  | False |
| PASS | train horizontal well file count is 773 | 773 | True |
| PASS | test horizontal well file count is 3 | 3 | True |
| PASS | sample submission row count is 14151 | 14151 | False |
| PASS | git branch is detectable | main | False |
| PASS | git commit is detectable | ef7df18 | False |
| PASS | github remote is configured | origin	https://github.com/hhhx-lab/ROGII (fetch) \| origin	https://github.com/hhhx-lab/ROGII (push) | False |
| WARN | worktree has no uncommitted tracked changes | D outputs/baseline_cv_by_well.csv
 D outputs/data_contract_summary.csv
 D outputs/data_version.json
 D outputs/ensemble_cv_summary.csv
 D outputs/ensemble_route_weights.csv
 D outputs/gated_alpha_by_well.csv
 D outputs/learned_gated_alpha_by_well.csv
 D outputs/learned_gated_geometry_cv_by_well.csv
 D outputs/part3_diagnostics.csv
 D outputs/postprocess_diagnostics.csv
 D outputs/residual_geometry_cv_by_well.csv
 D outputs/selected_candidate.json
 D outputs/submission_manifest.json
 D reports/baseline_cv_report.md
 D reports/candidate_selection_report.md
 D reports/ensemble_report.md
 D reports/part2_completion_audit.md
 D reports/postprocess_report.md
 D reports/residual_geometry_cv_report.md
 D reports/residual_geometry_multimask_report.md
 D reports/residual_target_report.md
 D reports/residual_xgb_leftover_cv_report.md
 D reports/submission_log.md
 D submission.csv
 D submissions/aggressive_submission.csv
 D submissions/balanced_submission.csv
 D submissions/conservative_submission.csv
 D submissions/gated_geometry_plus_xgb_leftover_submission.csv
 D submissions/gated_geometry_submission.csv
 D submissions/geometry_residual_submission.csv
 D submissions/learned_gated_geometry_submission.csv
 D submissions/optimized_submission.csv
 D submissions/xgb_leftover_submission.csv | False |

## Result

PASS
