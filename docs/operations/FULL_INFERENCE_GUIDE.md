# ROGII 全量推理指南

这份文档说明当前仓库里，如何从 `data/raw/` 的原始比赛数据开始，走到可提交的 `submission.csv`。

当前仓库状态先说清楚：

- Part 1 已完成，可作为稳定基线。
- Part 2 的旧结果已经清理，不能再当成当前冻结产物。
- Part 3 现在走的是 horizontal self-GR 对齐 + typewell 对齐增强路线。
- Part 4 负责集成、后处理和最终提交导出。

## 1. 目标

最终要生成一个可提交文件：

- 文件名：`submission.csv`
- 列：`id,tvt`
- 行数：与 `data/raw/sample_submission.csv` 完全一致
- 顺序：与 `sample_submission.csv` 的 `id` 顺序完全一致

## 2. 当前数据位置

比赛原始数据统一放在：

```text
data/
`-- raw/
    |-- train/
    |-- test/
    |-- sample_submission.csv
    `-- AI_wellbore_geology_prediction_task_en.pptx
```

真实读取入口以 `data/raw/` 为准。`data/` 根目录只是历史兼容占位，不应再作为主要说明口径。

## 3. 当前仓库里有哪些现成脚本

这些脚本是现在的真实入口：

- `scripts/run_eda.py`
- `scripts/evaluate_baseline_cv.py`
- `scripts/build_baseline_features.py`
- `scripts/build_geometry_features.py`
- `scripts/build_part3_diagnostics.py`
- `scripts/build_part3_features.py`
- `scripts/train_residual_model.py`
- `scripts/evaluate_model_cv.py`
- `scripts/evaluate_residual_multimask.py`
- `scripts/blend_predictions.py`
- `scripts/postprocess_predictions.py`
- `scripts/make_submission.py`
- `scripts/server_part2_preflight.py`
- `scripts/run_part2_full_server.py`
- `scripts/package_part2_server_outputs.py`
- `scripts/inspect_part2_server_package.py`

## 4. 推荐环境

仓库默认使用项目本地虚拟环境：

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

后续都用：

```bash
.venv/bin/python ...
```

这个环境至少要能跑通：

- `numpy`
- `pandas`
- `scikit-learn`
- `pyarrow`

## 5. 先做最小健康检查

如果你只是想确认仓库和数据都齐了，先跑：

```bash
.venv/bin/python scripts/run_eda.py
.venv/bin/python scripts/evaluate_baseline_cv.py
```

会更新：

- `reports/eda_summary.md`
- `outputs/baseline_cv_by_well.csv`
- `reports/baseline_cv_report.md`

这一步的意义是确认数据契约、样例行数、训练隐藏段和 baseline 还正常。

## 6. Part 1 当前基线

Part 1 现在的主基线是 `B0_constant_last`，它来自训练井的隐藏尾段验证。

如果要补齐或重建 Part 1 相关产物，按顺序跑：

```bash
.venv/bin/python scripts/build_baseline_features.py
.venv/bin/python scripts/evaluate_baseline_cv.py
```

当前 Part 1 相关的结果文件主要是：

- `outputs/baseline_predictions_train_hidden.csv`
- `outputs/baseline_predictions_test.csv`
- `features/baseline_features_train.csv`
- `features/baseline_features_test.csv`
- `features/residual_targets.csv`
- `reports/residual_target_report.md`
- `reports/baseline_cv_report.md`

## 7. Part 2 当前状态

Part 2 的旧成品已经清理过一次，所以这些结果不要再当成现成可用的冻结产物：

- `models/residual_geometry*`
- `outputs/residual_geometry*`
- `submissions/geometry_residual*`
- `reports/residual_geometry*`

如果你要重新生成 Part 2，先走：

```bash
.venv/bin/python scripts/build_baseline_features.py
.venv/bin/python scripts/build_geometry_features.py
.venv/bin/python scripts/train_residual_model.py
.venv/bin/python scripts/evaluate_model_cv.py
.venv/bin/python scripts/evaluate_residual_multimask.py
.venv/bin/python scripts/validate_part2_outputs.py
```

Part 2 生成/依赖的关键文件是：

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

注意：当前代码里 Part 2 仍有 parquet 口径的历史依赖，实际运行时以脚本为准；如果本地环境只看到 CSV，就说明这部分产物还没重建完整，不能直接跳过。

## 8. Part 3 当前路线

Part 3 不再只是“再做一个 residual”，而是：

1. horizontal self-GR 对齐
2. typewell 对齐
3. route / confidence 诊断
4. 为 Part 4 blend 提供路由信号

对应脚本：

```bash
.venv/bin/python scripts/build_part3_diagnostics.py
.venv/bin/python scripts/build_part3_features.py
```

会更新：

- `outputs/part3_diagnostics.csv`
- `reports/part3_diagnostics_report.md`
- `features/gr_features_train.csv`
- `features/gr_features_test.csv`
- `features/typewell_features_train.csv`
- `features/typewell_features_test.csv`
- `features/alignment_features_train.csv`
- `features/alignment_features_test.csv`

## 9. Part 4 当前提交链

Part 4 的职责是把前面结果变成最终提交。当前真实链路是：

```bash
.venv/bin/python scripts/blend_predictions.py
.venv/bin/python scripts/postprocess_predictions.py --variant balanced
.venv/bin/python scripts/make_submission.py --variant balanced --output submission.csv
```

其中：

- `scripts/blend_predictions.py` 生成三种提交候选
- `scripts/postprocess_predictions.py` 做曲线平滑、clip 和诊断
- `scripts/make_submission.py` 生成最终 `submission.csv`

最终会得到：

- `submissions/conservative_submission.csv`
- `submissions/balanced_submission.csv`
- `submissions/aggressive_submission.csv`
- `submissions/balanced_postprocessed_submission.csv`
- `submission.csv`

## 10. 一条从零开始的推荐顺序

如果你要从头跑一遍，按这个顺序：

```bash
.venv/bin/python scripts/run_eda.py
.venv/bin/python scripts/evaluate_baseline_cv.py
.venv/bin/python scripts/build_baseline_features.py
.venv/bin/python scripts/build_geometry_features.py
.venv/bin/python scripts/train_residual_model.py
.venv/bin/python scripts/evaluate_model_cv.py
.venv/bin/python scripts/evaluate_residual_multimask.py
.venv/bin/python scripts/validate_part2_outputs.py
.venv/bin/python scripts/build_part3_diagnostics.py
.venv/bin/python scripts/build_part3_features.py
.venv/bin/python scripts/blend_predictions.py
.venv/bin/python scripts/postprocess_predictions.py --variant balanced
.venv/bin/python scripts/make_submission.py --variant balanced --output submission.csv
```

如果你只是要最终提交，且前面的产物都已经存在，就只需要最后三步。

## 11. 当前仓库的关键提醒

- `data/raw/` 是唯一正式数据入口。
- 旧的 Part 2 结果不要沿用，尤其不要把旧的 `reports/` 当新结果。
- 可提交文件必须和 `sample_submission.csv` 对齐。
- Kaggle Notebook 最终只应该承担轻量推理和提交导出，不应该把重训练塞回去。
- `submission.csv` 生成后务必检查 `id` 顺序和行数。

## 12. 最后验收

最终确认下面几项都对：

- `submission.csv` 存在
- 只有 `id,tvt` 两列
- 行数和 `data/raw/sample_submission.csv` 一致
- `id` 顺序完全一致
- `tvt` 没有空值、`NaN` 或无穷值

