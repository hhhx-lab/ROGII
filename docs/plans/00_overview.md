# ROGII 模型总计划

这份文档是整个项目的总路线图。它不描述某一次临时提交，而是说明后续怎么把当前系统继续优化成更稳定、更容易冲榜的模型流程。

当前最重要的原则是：不要把问题改成直接预测绝对 TVT。我们的主框架保持为：

```text
final_tvt = baseline_tvt + correction
```

其中：

- `baseline_tvt` 是每口井自己的 TVT 延续趋势；
- `correction` 是模型学到的修正量；
- 所有新模型都应该增强 `correction`、控制 `correction` 或帮助判断 `correction` 是否可信。

## 1. 任务是什么

Kaggle ROGII Wellbore Geology Prediction 要求根据水平井轨迹、已知段 `TVT_input`、Gamma Ray 日志和 typewell 参考井，预测测试井 hidden rows 的 `tvt`。

初学者可以这样理解：

1. 每口井前半段有已知 TVT，后半段要预测。
2. baseline 先根据这口井前半段的趋势往后延伸。
3. residual model 再学习 baseline 通常会错在哪里。
4. GR/typewell alignment 提供地质证据，帮助判断修正方向是否可信。
5. 最终提交只能来自经过 OOF CV 验证的候选。

## 2. 当前仓库事实

下面是当前代码和报告支持的事实，后续文档都以这个口径为准。

| 模块 | 当前真实状态 |
|---|---|
| 主框架 | `baseline + residual correction` |
| baseline | 已能生成 train hidden OOF 和 test submission |
| Part 2 residual | 当前实际模型是 `StandardScaler + SGDRegressor` |
| XGBoost | 尚未实现，是下一步 planned residual candidate |
| residual target | `residual_target = truth_tvt - baseline_tvt` |
| Part 3 | 当前主要是 diagnostics / route，不是强 correction |
| Part 4 | 已有 candidate / blend / auto selection 雏形，但计划需要更严格 |
| postprocess | 已有 OOF guard 代码；报告显示无保护后处理会显著变差 |

当前报告里的关键信号：

- `reports/residual_geometry_cv_report.md`：baseline RMSE `119.933`，geometry residual RMSE `16.1024`。
- 同一报告显示 `633` 口井改善、`140` 口井退化，说明 residual 很有价值，但不能无条件全信。
- `reports/ensemble_report.md`：geometry residual RMSE `16.0862`，balanced RMSE `41.6539`，aggressive RMSE `59.3856`，说明“听起来更复杂”的 blend 不一定更好。
- `reports/postprocess_report.md`：balanced 后处理 OOF RMSE 从 `41.6539` 变差到 `78.1925`，说明 postprocess 必须有硬保护。
- `reports/part3_diagnostics_report.md`：Part 3 当前主要输出 route，test 侧当前全部路由到 `gr_residual`。

## 3. 为什么不直接预测绝对 TVT

直接训练一个模型输出 `tvt` 看起来简单，但这里风险很高：

- 不同井的绝对 TVT 尺度不同，直接跨井学习容易泛化失败；
- Kaggle hidden rerun 可能换掉 visible test，不能靠记住公开 3 口井；
- 直接预测容易生成不连续、不符合井内趋势的曲线；
- 模型错了以后，不容易判断该回退到哪里。

所以我们保留 baseline 作为锚点：

```text
baseline_tvt = use known TVT_input segment to extend this well
residual_target = truth_tvt - baseline_tvt
predicted_residual = model(features)
final_tvt = baseline_tvt + predicted_residual
```

这样做的好处是：

- baseline 是一个稳定控制组；
- residual 的含义清楚，就是“baseline 错了多少”；
- correction 可以被 clip、gater、route 和 postprocess 控制；
- 复杂模型失败时，可以回退 baseline 或降低 correction 权重。

## 4. 四个阶段的关系

| 阶段 | 文档 | 作用 |
|---|---|---|
| Part 1 | [`01_validation_baseline.md`](01_validation_baseline.md) | 建数据契约、CV 和 baseline |
| Part 2 | [`02_residual_modeling.md`](02_residual_modeling.md) | 学习 residual correction，当前 SGD，下一步 XGBoost/tree |
| Part 3 | [`03_gr_typewell_alignment.md`](03_gr_typewell_alignment.md) | 把 GR/typewell 做成 alignment features、route 和 gater 信号 |
| Part 4 | [`04_ensemble_submission_ops.md`](04_ensemble_submission_ops.md) | 生成候选、OOF 选择、postprocess guard、导出 submission |

整体流向：

```text
data contract / EDA
  -> baseline generation
  -> baseline CV
  -> feature build
  -> residual candidates
  -> gater / route
  -> candidate OOF evaluation
  -> automatic selection
  -> guarded postprocess
  -> final submission
```

## 5. Baseline 的角色

Baseline 解决的是“这口井自己原本的 TVT 趋势是什么”。

输入：

- `TVT_input` 已知段；
- `MD/X/Y/Z` 轨迹；
- target rows 的位置。

输出：

- `baseline_tvt`；
- baseline OOF metrics；
- baseline test prediction。

它能解决：

- 已知段到 hidden 段的基本连续趋势；
- 每口井自己的局部尺度；
- residual target 的参考基准。

它不能解决：

- 地层发生偏移；
- GR 形态提示 hidden 段已经换层；
- typewell 显示 baseline TVT 附近并不是最相似层位；
- 长 hidden interval 中后段的系统性漂移。

验证方式：

- 训练井 hidden rows OOF RMSE；
- per-well RMSE；
- P95/P99 error；
- worst wells；
- 多 mask 压力测试。

失败时怎么回退：

- baseline 本身就是全系统的安全回退；
- 后续任何 correction 如果没有通过 OOF 验证，都不能覆盖 baseline。

## 6. Residual Correction 的角色

Residual model 解决的是“baseline 往后延伸以后，通常会错多少”。

固定目标：

```text
residual_target = truth_tvt - baseline_tvt
```

当前已实现：

- `scripts/train_residual_model.py` 使用 `StandardScaler + SGDRegressor`；
- 支持 `geometry`、`gr`、`typewell` 三类 `ModelSpec`；
- 使用 `GroupKFold` 按 well 做 OOF；
- 输出 `final_pred = baseline_tvt + oof_residual_pred`。

下一步计划：

- 增加 XGBoost residual；
- 增加 HistGradientBoosting residual；
- 如果环境允许，再增加 LightGBM residual；
- 所有模型使用同一套 residual target、GroupKFold 和 per-well CV 比较。

为什么要这样做：

- SGD 是可靠、轻量、可运行的 residual control；
- XGBoost/tree model 更适合学习非线性特征交互；
- 只有同一套 OOF 比较，才能知道提升来自模型本身，不是来自验证口径差异。

失败时怎么回退：

- 如果新模型不如 SGD，就保留 SGD；
- 如果整体 RMSE 好但退化井变多，就只能作为 aggressive candidate；
- 如果对 baseline-good wells 修坏太多，就必须交给 gater 降权。

## 7. Gated Correction 的角色

当前最大的风险不是“没有 correction”，而是“correction 在某些井上修过头”。

因此下一步要引入 gater：

```text
final_tvt = baseline_tvt + alpha * predicted_residual
```

`alpha` 表示这一口井或这一段要信多少 correction：

- `alpha = 0`：完全回退 baseline；
- `alpha = 1`：完全使用 residual；
- `0 < alpha < 1`：保守修正。

gater 可以是：

- 第一版手工规则或 alpha grid；
- tree-based gater；
- route confidence；
- OOF 学出来的 per-well 风险规则。

输入特征可以包括：

- baseline confidence；
- target length；
- known length；
- baseline slope std；
- predicted residual magnitude；
- GR missing rate；
- Part 3 route；
- alignment confidence；
- per-well risk score。

验证方式：

- gated residual 是否优于 ungated residual；
- baseline-good wells 的退化是否减少；
- worst degradation 是否下降；
- long target wells 是否仍有提升；
- P95/P99 abs error 是否改善。

失败时怎么回退：

- tree gater 不稳时，用固定 alpha grid；
- 固定 alpha 仍不稳时，回退 SGD residual 或 baseline。

## 8. GR / Typewell Alignment 的角色

Part 3 的目标不是单独生成最终 TVT，而是提供地质证据。

当前已实现：

- GR quality；
- baseline confidence；
- typewell quality；
- risk score；
- route suggestion。

下一步计划：

- horizontal GR self-alignment；
- horizontal GR vs typewell GR alignment；
- `best_offset`；
- `best_similarity`；
- `second_best_similarity`；
- `similarity_margin`；
- `alignment_confidence`；
- `alignment_support_fraction`；
- `alignment_enabled_flag`。

这些结果不能直接覆盖 baseline，只能用于：

- residual model 的输入特征；
- gater 的输入；
- route/confidence 的依据；
- failure analysis。

为什么要谨慎：

- GR 曲线相似不代表 TVT offset 一定方向正确；
- typewell 可能局部噪声大；
- alignment 在可视化上可能合理，但 OOF 上会修坏井。

验证方式：

- high confidence alignment subset 是否更准；
- `best_offset` 的符号是否和真实 residual 方向一致；
- 加入 alignment 特征后 residual OOF 是否改善；
- worst wells 是否减少。

失败时怎么回退：

- confidence 低时禁用 alignment correction；
- 只保留 route diagnostic；
- 不允许 alignment 单独生成 final submission。

## 9. Candidate Selection 和 Postprocess

最终提交不能靠手工喜欢某个名字，比如固定 `balanced`。正确流程应该是：

```text
candidate models:
  baseline
  SGD residual
  XGBoost residual planned
  HistGradientBoosting residual planned
  gated residual planned
  GR/typewell alignment enhanced residual planned
  blend candidates

selection:
  choose candidate with best validated OOF CV
  check per-well degradation
  check worst-well tail
  check smoothness
  then export final submission
```

postprocess 也只能作为候选变换：

```text
if postprocess_rmse_after > postprocess_rmse_before:
    reject postprocessed submission
    use original candidate
```

当前 `scripts/postprocess_predictions.py` 已有这类 guard 逻辑；文档和操作流程必须把它作为硬规则，而不是可选项。

## 10. 后续推荐顺序

1. 固化当前 SGD residual 作为 residual control。
2. 实现 XGBoost residual，并和 SGD 用同一套 GroupKFold OOF 比较。
3. 增加 HistGradientBoosting residual，作为 sklearn tree baseline。
4. 实现第一版 alpha grid / rule-based gater。
5. 把 Part 3 alignment 特征接入 residual / gater，而不是直接改 final TVT。
6. 扩展 `blend_predictions.py`，把所有候选统一写入 OOF summary。
7. 强化 `make_submission.py --variant auto`，只导出 OOF 最优且通过 guard 的候选。
8. 最后再做 Kaggle Notebook 化和 leaderboard 提交闭环。

## 11. 最低验收原则

任何新模型想进入最终候选池，必须满足：

- 有 OOF prediction；
- 有 per-well metrics；
- 和 baseline、SGD residual 在同一套 CV 下比较；
- 不能只看 public leaderboard；
- 不能只看 overall RMSE；
- 要检查 degraded wells、worst wells、P95/P99；
- postprocess 后如果 OOF 变差，不能使用后处理版本。

一句话总结：

```text
baseline 是锚点，residual 是修正，gater 决定信多少，alignment 提供证据，OOF CV 决定最终提交。
```
