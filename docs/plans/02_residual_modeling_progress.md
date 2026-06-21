# Part 2 执行进度：Baseline + Residual 主干模型

更新时间：2026-06-20

## 当前目标

严格执行 `docs/plans/02_residual_modeling.md`，完成 baseline + geometry residual 主干。优先完成本机可运行版本；如果本机算力不足，则保留同一套脚本、配置和 server runbook，使服务器上可以直接放大全量训练。

注意：当前仓库里虽然已经有 Part 2 的审计通过记录，但这次已经把旧结果清理掉了，因此 `reports/part2_completion_audit.md`、`models/residual_geometry*`、`outputs/residual_geometry*`、`submissions/geometry_residual*` 和 `features/*.parquet` 的旧产物不再保留。后续最终冻结结果应以服务器 full-row 复跑后的新产物为准，而不是把上一轮 CV 报告当成最终版。

## 进度总览

| 模块 | 状态 | 当前证据 |
|---|---|---|
| Part 2 计划复核 | 已完成 | 已按计划逐项补齐 residual target 分桶、井级 slope 特征、clip/bias/smoothness 诊断、多 mask residual 验证和服务器 runbook |
| 依赖检查 | 已完成 | `.venv` 已安装 `pyarrow`，`requirements.txt` 已加入 `pyarrow` |
| baseline features | 已完成 | `features/baseline_features_train.parquet` 3,783,989 行，`features/baseline_features_test.parquet` 14,151 行；mask 相关 baseline 特征按 target interval 重算 |
| geometry features | 已完成 | `features/geometry_features_train.parquet` 3,783,989 行，`features/geometry_features_test.parquet` 14,151 行；已补 `well_known_slope_mean/std` |
| residual target report | 已完成 | `reports/residual_target_report.md` 包含 residual 分布、by well、by target length、by baseline error bucket、by GR missing rate |
| residual HGB model | 已完成 | 5-fold GroupKFold OOF 完成，`selected_alpha=0.75`，已生成 model/config/test prediction/submission |
| CV/report/failure/importance | 已完成 | `reports/residual_geometry_cv_report.md`：baseline RMSE 15.9099，geometry residual RMSE 14.9900，改善 0.9198，`PROMOTE_TO_PART3_INPUT` |
| multi-mask residual 验证 | 已完成 | `reports/residual_geometry_multimask_report.md`：5 类 mask、每类 773 井 split，全部 row-weighted RMSE 改善 |
| Part 2 完成审计 | 已完成 | `scripts/validate_part2_outputs.py` 通过，`reports/part2_completion_audit.md` 记录 `checks=34 failures=0` |

## 本机与服务器策略

默认本机训练参数：

```bash
ROGII_PART2_TRAIN_ROWS_PER_WELL=600
ROGII_PART2_MAX_ITER=220
```

服务器全量训练建议：

```bash
.venv/bin/python scripts/build_baseline_features.py
.venv/bin/python scripts/build_geometry_features.py
ROGII_PART2_TRAIN_ROWS_PER_WELL=0 \
ROGII_PART2_MAX_ITER=500 \
.venv/bin/python scripts/train_residual_model.py
.venv/bin/python scripts/evaluate_model_cv.py
ROGII_PART2_MULTIMASK_TRAIN_ROWS_PER_WELL=0 \
ROGII_PART2_MULTIMASK_MAX_ITER=500 \
.venv/bin/python scripts/evaluate_residual_multimask.py
.venv/bin/python scripts/validate_part2_outputs.py
```

## 关键结果

原始 hidden OOF：

| 指标 | baseline | geometry residual | 改善 |
|---|---:|---:|---:|
| RMSE | 15.9099 | 14.9900 | 0.9198 |
| MAE | 11.1965 | 10.6821 | 0.5144 |
| P95 abs error | 32.3398 | 30.1294 | 2.2104 |
| bias | -1.5960 | -0.3027 | 1.2933 |

井级表现：

| 项 | 数值 |
|---|---:|
| train wells | 773 |
| improved wells | 449 |
| degraded wells | 324 |
| median RMSE improvement | 0.4480 |
| worst degradation | -15.9239 |
| best improvement | 19.8456 |

多 mask 验证：

| mask_type | baseline RMSE | geometry RMSE | RMSE 改善 | improved splits | degraded splits |
|---|---:|---:|---:|---:|---:|
| original_hidden | 15.9099 | 15.0212 | 0.8887 | 454 | 319 |
| trailing_short | 9.2371 | 8.3085 | 0.9286 | 484 | 289 |
| trailing_long | 14.9329 | 14.1560 | 0.7769 | 473 | 300 |
| mid_contiguous | 8.4333 | 7.3871 | 1.0462 | 505 | 268 |
| random_contiguous | 28.9184 | 16.0386 | 12.8798 | 491 | 282 |

## 当前判断

- residual 主干值得进入 Part 3：原始 hidden、多 mask、P95、bias 均有改善。
- 不能盲目全量信任 residual：仍有 324 个原始 hidden 井级退化，worst degradation 达 -15.9239。
- 后续 Part 3 应优先加入 GR/typewell 对齐解释层位偏移；Part 4 必须做 conservative routing/blending，对低置信或退化模式回退 baseline。

## 完成标准

- `features/baseline_features_train.parquet`
- `features/baseline_features_test.parquet`
- `features/geometry_features_train.parquet`
- `features/geometry_features_test.parquet`
- `features/residual_targets.parquet`
- `models/residual_geometry_hgb.pkl`
- `models/residual_geometry_config.json`
- `models/residual_geometry_feature_list.txt`
- `outputs/residual_geometry_oof.csv`
- `outputs/residual_geometry_cv_by_well.csv`
- `outputs/residual_geometry_test_predictions.csv`
- `outputs/residual_geometry_multimask_by_split.csv`
- `outputs/residual_geometry_multimask_overall.csv`
- `reports/residual_target_report.md`
- `reports/residual_geometry_cv_report.md`
- `reports/residual_geometry_failure_analysis.md`
- `reports/residual_geometry_feature_importance.md`
- `reports/residual_geometry_multimask_report.md`
- `reports/residual_geometry_server_runbook.md`
- `submissions/geometry_residual_submission.csv`
- `reports/part2_completion_audit.md`

最终以 `scripts/validate_part2_outputs.py` 通过为准。
