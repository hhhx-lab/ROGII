# Server Part 2 Full Run Config

- Run id: `20260626_162116`
- Started at: `2026-06-26T16:21:16.542714+00:00`
- Finished at: `2026-06-26T16:50:58.853215+00:00`
- Dry run: `False`
- Failed step: `part2_cv_reports`
- Git branch: `main`
- Git HEAD: `ef7df18`
- Data root: `C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\data\raw`
- Train wells/files: `773`
- Test wells/files: `3`
- Sample rows: `14151`

## Training Policy

- residual_spec: `geometry`
- full_row_training: `True`
- train_rows_per_well: `0`
- min_fit_fraction: `0.95`
- require_xgboost: `True`
- with_gated_pipeline: `True`
- with_learned_gater: `True`
- learned_gater_model: `ridge`
- learned_gater_snap_alpha_grid: `False`
- with_direct_xgb: `True`
- with_xgb_leftover: `False`
- allow_oracle_auto_selection: `False`
- candidate_eligibility_policy: `oracle/diagnostic and legacy stack candidates are excluded unless explicitly enabled`

## Planned Steps

| # | Step | Command | Log |
|---:|---|---|---|
| 1 | preflight | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/server_part2_preflight.py` | `reports\server_part2_full_run_logs\20260626_162116_01_preflight.log` |
| 2 | data_contract | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/check_data_contract.py` | `reports\server_part2_full_run_logs\20260626_162116_02_data_contract.log` |
| 3 | part1_baseline_cv | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/evaluate_baseline_cv.py` | `reports\server_part2_full_run_logs\20260626_162116_03_part1_baseline_cv.log` |
| 4 | make_cv_splits | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/make_cv_splits.py` | `reports\server_part2_full_run_logs\20260626_162116_04_make_cv_splits.log` |
| 5 | baseline_multimask | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/evaluate_baseline_multimask.py` | `reports\server_part2_full_run_logs\20260626_162116_05_baseline_multimask.log` |
| 6 | part2_baseline_features | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/build_baseline_features.py` | `reports\server_part2_full_run_logs\20260626_162116_06_part2_baseline_features.log` |
| 7 | part2_geometry_features | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/build_geometry_features.py` | `reports\server_part2_full_run_logs\20260626_162116_07_part2_geometry_features.log` |
| 8 | train_geometry_residual | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/train_residual_model.py --spec geometry --max-rows-per-well 0 --max-iter 500 --learning-rate 0.05 --max-leaf-nodes 31 --min-samples-leaf 50 --l2-regularization 0.05 --min-fit-fraction 0.95` | `reports\server_part2_full_run_logs\20260626_162116_08_train_geometry_residual.log` |
| 9 | train_direct_xgb_residual | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/train_residual_model.py --spec xgb --max-rows-per-well 0 --max-iter 500 --learning-rate 0.05 --max-leaf-nodes 31 --min-samples-leaf 50 --l2-regularization 0.05 --min-fit-fraction 0.95 --require-xgboost` | `reports\server_part2_full_run_logs\20260626_162116_09_train_direct_xgb_residual.log` |
| 10 | part2_cv_reports | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/evaluate_model_cv.py` | `reports\server_part2_full_run_logs\20260626_162116_10_part2_cv_reports.log` |
| 11 | part2_full_residual_multimask | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/evaluate_residual_multimask.py` | `reports\server_part2_full_run_logs\20260626_162116_11_part2_full_residual_multimask.log` |
| 12 | part3_diagnostics | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/build_part3_diagnostics.py` | `reports\server_part2_full_run_logs\20260626_162116_12_part3_diagnostics.log` |
| 13 | part2_gated_geometry | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/build_gated_geometry.py` | `reports\server_part2_full_run_logs\20260626_162116_13_part2_gated_geometry.log` |
| 14 | part2_learned_gater | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/train_learned_gater.py --model ridge` | `reports\server_part2_full_run_logs\20260626_162116_14_part2_learned_gater.log` |
| 15 | part2_completion_audit | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/validate_part2_outputs.py --primary-spec geometry` | `reports\server_part2_full_run_logs\20260626_162116_15_part2_completion_audit.log` |
| 16 | blend_predictions | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/blend_predictions.py` | `reports\server_part2_full_run_logs\20260626_162116_16_blend_predictions.log` |
| 17 | candidate_selection | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/select_submission_candidate.py --dry-run` | `reports\server_part2_full_run_logs\20260626_162116_17_candidate_selection.log` |
| 18 | postprocess_selected | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/postprocess_predictions.py --variant auto` | `reports\server_part2_full_run_logs\20260626_162116_18_postprocess_selected.log` |
| 19 | make_submission | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/make_submission.py --variant auto --output submission.csv` | `reports\server_part2_full_run_logs\20260626_162116_19_make_submission.log` |
| 20 | validate_submission | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/validate_submission.py --submission submission.csv` | `reports\server_part2_full_run_logs\20260626_162116_20_validate_submission.log` |
| 21 | package_part2_outputs | `'C:\Users\31745\Desktop\新建文件夹 (6)\ROGII\.venv\Scripts\python.exe' scripts/package_part2_server_outputs.py` | `reports\server_part2_full_run_logs\20260626_162116_21_package_part2_outputs.log` |

## Results

| Step | Return code | Seconds |
|---|---:|---:|
| preflight | 0 | 0.8 |
| data_contract | 0 | 10.1 |
| part1_baseline_cv | 0 | 16.0 |
| make_cv_splits | 0 | 11.3 |
| baseline_multimask | 0 | 55.9 |
| part2_baseline_features | 0 | 96.3 |
| part2_geometry_features | 0 | 495.4 |
| train_geometry_residual | 0 | 172.2 |
| train_direct_xgb_residual | 0 | 918.0 |
| part2_cv_reports | 1 | 6.0 |

## Full JSON

- Latest: `reports\server_part2_full_run_config.json`
- This run: `reports\server_part2_full_run_configs\20260626_162116.json`
