# Part 2: Residual Modeling 主干计划

Part 2 的任务是学习 baseline 的误差，而不是重新预测绝对 TVT。

固定公式：

```text
final_tvt = baseline_tvt + correction
```

其中 Part 2 主要负责：

```text
correction = predicted_residual
residual_target = truth_tvt - baseline_tvt
```

## 1. 当前阶段定位

初学者可以这样理解：

- Part 1 的 baseline 先画出一条“按这口井已知趋势继续走”的线；
- Part 2 看训练井里 baseline 和真值差多少；
- 模型学习这些差值；
- 预测测试井时，把学到的差值加回 baseline。

这样做比直接预测 TVT 更稳，因为 baseline 已经保留了每口井自己的尺度和趋势，模型只需要学“什么时候 baseline 会偏、偏多少”。

## 2. 当前真实状态

当前仓库里的 `scripts/train_residual_model.py` 实际使用：

```text
StandardScaler + SGDRegressor
```

这点必须写清楚：当前已经有 `--spec xgb` 的 XGBoost/tree residual 训练入口，但当前已生成、可作为控制组的 residual 产物仍主要来自 SGD pipeline。部分旧模型文件名里仍有 `_hgb` 历史命名，不代表当前 geometry control 一定是 HGB。

当前已实现能力：

- 构造 residual target；
- 合并 baseline / geometry / GR / typewell / alignment 特征；
- 按 well 使用 `GroupKFold` 做 OOF；
- 输出 OOF residual prediction；
- 输出 test prediction；
- 输出 per-well CV report；
- 支持 `geometry`、`gr`、`typewell` 三类 `ModelSpec`。
- 支持 `xgb` tree residual `ModelSpec`，优先 `xgboost.XGBRegressor`，缺依赖时 fallback 到 sklearn `HistGradientBoostingRegressor`。

当前报告里的事实：

- `reports/residual_geometry_cv_report.md` 显示 baseline RMSE `119.933`，geometry residual RMSE `16.1024`；
- `633` 口井改善，`140` 口井退化；
- `selected_alpha = 1.0`；
- 说明 SGD residual 已经是很强的 control model，但仍需要 gater 限制退化井。

## 3. 输入与输出

### 3.1 输入

当前可运行脚本主要读取：

```text
features/baseline_features_train.csv
features/baseline_features_test.csv
features/geometry_features_train.csv
features/geometry_features_test.csv
features/gr_features_train.csv
features/gr_features_test.csv
features/typewell_features_train.csv
features/typewell_features_test.csv
features/alignment_features_train.csv
features/alignment_features_test.csv
features/residual_targets.csv
outputs/baseline_predictions_train_hidden.csv
outputs/baseline_predictions_test.csv
```

不同 `--spec` 依赖不同特征：

- `geometry`：baseline + geometry；
- `gr`：GR features；
- `typewell`：GR + typewell + alignment features。

### 3.2 输出

当前脚本会输出类似：

```text
outputs/residual_geometry_oof.csv
outputs/residual_geometry_cv_by_well.csv
outputs/residual_geometry_test_predictions.csv
submissions/geometry_residual_submission.csv
reports/residual_geometry_cv_report.md
models/residual_geometry_hgb.pkl
models/residual_geometry_hgb_config.json
models/residual_geometry_hgb_feature_list.txt
```

注意：这里的 `_hgb` 是历史文件名，不代表当前模型是 HGB。

## 4. Residual Target 定义

所有 residual model 必须使用同一个目标：

```text
residual_target = truth_tvt - baseline_tvt
```

训练时：

```text
predicted_residual = model(features)
final_tvt = baseline_tvt + predicted_residual
```

为什么这样做：

- baseline 已经解释了每口井的大趋势；
- residual 数值通常更小，模型更容易学；
- residual 可以被 clip、smooth、gater 控制；
- 模型失败时可以回退 baseline。

不允许：

- 某个模型直接预测绝对 `tvt` 后和 residual model 混在一起比较；
- 用不同 target 定义参加同一个 candidate pool；
- 用 public leaderboard 反推 residual target。

## 5. 当前 SGD Residual 是什么角色

当前 SGD residual 不是最终上限，而是 residual control。

它的作用：

- 证明 `baseline + residual` 这个框架有效；
- 提供一个轻量、可复现、低依赖的候选；
- 给 XGBoost/tree model 提供比较对象；
- 给 Part 4 提供当前可运行的 geometry residual submission。

它解决的问题：

- baseline 在长 hidden interval 中的系统性偏差；
- 轨迹几何特征能解释的一部分趋势错误；
- 对所有井提供统一 correction。

它没有解决的问题：

- 某些 baseline 本来很好的井被修坏；
- 非线性特征交互可能没学充分；
- GR/typewell alignment 信号还没有充分转化为强 correction；
- 没有显式学习“这口井到底该信多少 correction”。

验证方式：

- 和 baseline 比整体 RMSE；
- 看 per-well improved/degraded wells；
- 看 P95/P99 abs error；
- 看 worst degradation；
- 看不同 target length / baseline confidence bucket。

失败时回退：

- 如果新 run 的 SGD 结果不稳定，回退最近一次通过审计的 baseline；
- 如果某些井退化严重，交给 Part 4 的 gater / candidate selection 处理。

## 6. 下一步模型候选

下一步不是推翻框架，而是替换或增强 residual model：

```text
final_tvt = baseline_tvt + model(features)
```

候选列表：

| 候选 | 状态 | 为什么做 | 风险 |
|---|---|---|---|
| SGD residual | 已实现 | 轻量、稳定、低依赖 | 非线性能力有限 |
| XGBoost residual | 脚本已实现，产物需运行生成 | 擅长非线性特征交互，适合 tabular | 需要依赖和参数控制 |
| HistGradientBoosting residual | 已作为 XGBoost fallback 实现 | sklearn 自带，环境更稳 | 表达力可能低于 XGBoost |
| LightGBM residual | planned if environment allows | tabular 强模型，速度快 | Kaggle/服务器环境依赖要确认 |
| Ridge / ElasticNet residual | optional control | 线性 sanity check | 上限低 |

所有候选必须满足：

- 使用同一个 `residual_target`；
- 使用同一套 train hidden rows；
- 使用同一套 GroupKFold / per-well CV；
- 输出 OOF prediction；
- 输出 test prediction；
- 输出 per-well degradation report；
- 不能只看 public leaderboard 判断优劣。

## 7. XGBoost / Tree Residual 实现计划

### 7.1 为什么做

当前 SGD 是线性模型，输入特征之间的复杂组合需要人工特征来表达。`scripts/train_residual_model.py --spec xgb` 已经接入 tree residual：如果 `xgboost` 可 import，则使用 `XGBRegressor`；否则自动使用 sklearn `HistGradientBoostingRegressor`。XGBoost 更擅长自动学习非线性规则，例如：

- target 很长且 baseline slope 不稳定时，correction 可能更大；
- GR 缺失率高时，某些 GR 特征应该降权；
- predicted residual magnitude 太大时，风险可能更高；
- alignment confidence 高时，typewell offset 才值得信。

### 7.2 解决当前什么问题

主要解决：

- SGD 对特征交互表达不足；
- residual 在不同井型和不同 hidden length 下表现不一致；
- geometry / GR / alignment 特征合并后，线性模型不容易学出条件规则。

### 7.3 依赖输入

第一版输入建议：

```text
baseline features
geometry features
GR quality features
target length / known length
baseline confidence
predicted residual magnitude from SGD
Part 3 route
alignment confidence if available
```

不要第一版就塞入所有高维特征。先做一个可解释、可比较的 XGBoost residual。

### 7.4 输出

建议输出：

```text
outputs/residual_xgb_oof.csv
outputs/residual_xgb_cv_by_well.csv
outputs/residual_xgb_test_predictions.csv
submissions/xgb_residual_submission.csv
reports/residual_xgb_cv_report.md
models/residual_xgb.pkl
models/residual_xgb_config.json
```

### 7.5 如何验证是否变好

必须和 SGD residual 同表比较：

- overall RMSE；
- mean well RMSE；
- P95/P99 abs error；
- improved/degraded wells；
- worst degradation；
- long target wells；
- baseline-good wells；
- high GR missing wells。

通过标准不是“XGBoost overall 更低一点”这么简单。更合理的标准是：

- overall RMSE 不差于 SGD；
- worst degradation 不明显变差；
- baseline-good wells 的退化不增加；
- 如果只在少数难井有提升，可以先作为 aggressive candidate。

### 7.6 失败时回退

- 如果 XGBoost 整体不如 SGD，回退 SGD；
- 如果 XGBoost 只改善高风险井，作为 route-specific candidate；
- 如果 XGBoost 修坏 baseline-good wells，必须接 gater；
- 如果依赖安装不稳定，先用 sklearn HistGradientBoosting 做替代实验。

## 8. Gated Correction 计划

### 8.1 为什么需要 gater

当前 SGD residual 总体很强，但仍有 `140` 口井退化。问题不是 residual 没用，而是“每口井该信多少 residual”还没有学好。

因此引入：

```text
final_tvt = baseline_tvt + alpha * predicted_residual
```

其中：

- `predicted_residual` 来自 SGD / XGBoost / tree residual；
- `alpha` 表示这口井或这一段信多少 correction。

### 8.2 解决当前什么问题

gater 重点解决：

- baseline 本来很好，但 residual 修坏；
- alignment 信号不稳定，不能直接使用；
- 低置信井需要回退；
- aggressive model 可以存在，但不能在所有井上强行启用。

### 8.3 gater 输入

候选输入：

```text
baseline_confidence
target_length
known_length
known_ratio
baseline_slope_std
predicted_residual_magnitude
residual_step_or_smoothness
GR_missing_rate
Part3_route
alignment_confidence
alignment_support_fraction
model_disagreement
per_well_risk_score
```

第一版可以先用规则或 alpha grid：

```text
alpha in {0.0, 0.25, 0.5, 0.75, 1.0}
```

第二版再训练 tree-based gater。

### 8.4 gater 输出

输出可以是 row-level 或 well-level：

```text
alpha
gated_residual = alpha * predicted_residual
final_tvt = baseline_tvt + gated_residual
gater_reason
gater_confidence
```

如果第一版只做 well-level alpha，也要保留到每一行，方便后续分析。

### 8.5 如何验证是否真的变好

至少比较三组：

```text
baseline
ungated residual
gated residual
```

检查：

- overall RMSE 是否下降；
- baseline-good wells 是否少被修坏；
- degraded wells 数量是否减少；
- worst degradation 是否减少；
- P95/P99 是否改善；
- long target wells 是否仍保留提升；
- alpha 分布是否合理，不是一律接近 0 或 1。

### 8.6 失败时回退

- tree gater 不稳，回退手工 alpha grid；
- alpha grid 不稳，回退固定 `alpha = 1.0` 的 SGD residual；
- 如果所有 residual 都不稳，回退 baseline；
- 如果某类 route 退化严重，只对该 route 降 alpha。

## 9. 特征工程原则

### 9.1 Baseline 特征

需要保留：

```text
baseline_tvt
baseline_slope_median
baseline_slope_std
baseline_confidence
baseline_pred_delta_from_last_known
distance_from_last_known_row
known_rows
target_rows
known_ratio
target_ratio
```

原因：这些特征告诉模型 baseline 自己是否可信。

### 9.2 Geometry 特征

需要保留：

```text
MD_norm
Z_centered
dZ_dMD
trajectory_speed_proxy
trajectory_curvature_proxy
path_length_norm
rolling curvature / speed features
```

原因：井轨迹变化会影响 TVT 外推误差。

### 9.3 GR / Typewell / Alignment 特征

这些主要来自 Part 3：

```text
gr_quality_score
GR_roll_mean/std/missing_rate
typewell_quality_score
best_offset
best_similarity
second_best_similarity
similarity_margin
alignment_confidence
alignment_support_fraction
alignment_enabled_flag
Part3_route
```

原因：它们提供地质信号，但必须先通过 OOF 验证，不能直接覆盖 baseline。

### 9.4 禁止特征

不允许使用：

- test 不存在的训练专属 formation surface 列；
- well ID one-hot；
- well ID target encoding；
- hidden rows 的真值 TVT；
- public visible test 手调参数。

## 10. CV 与比较标准

所有 residual candidate 必须使用：

```text
GroupKFold by well
```

原因：同一口井的行高度相关。如果同一口井同时出现在 train 和 validation，分数会虚高。

必须输出：

- OOF row-level prediction；
- per-well metrics；
- overall RMSE / MAE；
- median abs error；
- P90/P95/P99 abs error；
- max abs error；
- bias；
- improved/degraded well count；
- worst degraded wells；
- best improved wells。

比较顺序：

1. 先和 baseline 比；
2. 再和当前 SGD residual 比；
3. 再看是否值得进入 Part 4 candidate pool。

## 11. Part 2 完成标准

当前已完成的最低能力：

- SGD residual 可训练；
- geometry residual OOF 可生成；
- test residual submission 可生成；
- GroupKFold OOF 可输出；
- report 可输出。

下一步完成标准：

- XGBoost residual 完成；
- HistGradientBoosting residual 完成；
- 至少一个 gater candidate 完成；
- 所有候选写入统一 OOF summary；
- 每个候选都能回答“为什么做、解决什么问题、输入是什么、输出是什么、如何验证、失败怎么回退”。

## 12. 进入 Part 3 / Part 4 的条件

进入 Part 3：

- 至少有 baseline features；
- 至少有 geometry residual OOF；
- 知道 residual 哪些井改善、哪些井退化；
- 需要 GR/typewell 去解释或控制退化。

进入 Part 4：

- 每个 candidate 都有 OOF；
- 每个 candidate 都有 test prediction；
- 能在统一 CV 表中比较；
- postprocess 只能作为 guarded candidate；
- 最终选择不能只靠名字，必须靠 OOF 和风险检查。
