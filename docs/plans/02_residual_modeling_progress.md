# Part 2 执行进度：Residual Modeling

更新时间：2026-06-22

这份文件只记录 Part 2 当前仓库状态和下一步执行重点。模型路线以 [`02_residual_modeling.md`](02_residual_modeling.md) 为准。

## 当前事实

当前 Part 2 的主框架仍然是：

```text
final_tvt = baseline_tvt + predicted_residual
residual_target = truth_tvt - baseline_tvt
```

当前真实脚本状态：

- `scripts/train_residual_model.py` 使用 `StandardScaler + SGDRegressor`；
- 当前已新增 `--spec xgb` tree residual 入口；
- 如果 `xgboost` 可 import，会使用 `xgboost.XGBRegressor`；
- 如果没有 `xgboost`，会 fallback 到 `HistGradientBoostingRegressor`；
- 部分文件名仍带 `_hgb`，这是历史命名，不代表模型类型；
- 当前特征和脚本主口径是 CSV；
- LightGBM、gater、alignment-enhanced residual 仍是下一步计划。

## 当前已完成能力

| 模块 | 状态 | 说明 |
|---|---|---|
| baseline features | 已实现 | 为 residual target 和 test prediction 提供 `baseline_tvt` |
| geometry features | 已实现 | 提供轨迹、slope、curvature 等几何特征 |
| residual target | 已实现 | `truth_tvt - baseline_tvt` |
| SGD residual | 已实现 | 当前 residual control model |
| XGBoost/tree residual | 脚本已实现 | `--spec xgb`，优先 XGBoost，缺依赖 fallback 到 HGB |
| GroupKFold OOF | 已实现 | 按 well 分组，避免同井泄漏 |
| per-well report | 已实现 | 用于看 improved / degraded wells |
| test residual submission | 已实现 | 可生成 `geometry_residual_submission.csv` |

## 当前报告信号

以当前仓库报告为准：

- `reports/residual_geometry_cv_report.md` 显示 baseline RMSE `119.933`，geometry residual RMSE `16.1024`；
- `633` 口井改善，`140` 口井退化；
- `selected_alpha = 1.0`；
- 这说明 residual correction 很有效，但仍需要 gater 控制被修坏的井。

## 仍未完成的优化

| 优化项 | 状态 | 为什么需要 |
|---|---|---|
| XGBoost residual | 脚本已实现，需运行生成产物 | 学习更强的非线性 residual |
| HistGradientBoosting residual | 已作为 fallback 实现 | sklearn 环境下的 tree baseline |
| LightGBM residual | planned if environment allows | 作为强 tabular 对照 |
| gated residual | planned | 防止 baseline-good wells 被 residual 修坏 |
| alignment-enhanced residual | planned | 把 Part 3 GR/typewell alignment 特征接入 residual |
| candidate registry | planned | 让 Part 4 自动选择时知道每个候选来源 |

## 下一步执行顺序

1. 固化当前 SGD residual 作为 control。
2. 用 `--spec xgb` 跑出 tree residual OOF，并保持同一 `residual_target`。
3. 对 SGD / XGBoost-or-HGB 使用同一 GroupKFold 和 per-well CV 比较。
4. 做第一版 alpha grid 或 rule-based gater。
5. 把 Part 3 alignment confidence / route 接入 gater 或 residual 特征。
6. 把所有候选交给 Part 4 做 OOF selection 和 postprocess guard。

## 完成标准

Part 2 下一阶段完成时，需要有：

```text
outputs/residual_geometry_oof.csv
outputs/residual_geometry_cv_by_well.csv
outputs/residual_geometry_test_predictions.csv
reports/residual_geometry_cv_report.md
outputs/residual_xgb_oof.csv
outputs/residual_xgb_test_predictions.csv
reports/residual_xgb_cv_report.md
outputs/gated_residual_oof.csv
reports/gated_residual_cv_report.md
```

其中 XGBoost 和 gater 文件是下一步计划产物，不是当前已完成产物。

最终判断标准：

- 不能只看 public leaderboard；
- 必须和 baseline、当前 SGD residual 使用同一套 OOF 比较；
- 必须检查 degraded wells 和 worst-well tail；
- 如果新模型 OOF 不如 SGD，就回退 SGD；
- 如果 postprocess 后 OOF 变差，不能使用 postprocessed submission。
