# Part 2: Baseline + Residual 主干模型

## 1. 阶段目标

本阶段要建立第一个真正有竞争力的模型主干：

```text
prediction = continuity_baseline + residual_model(features)
```

目标不是做花哨模型，而是让模型稳定修正 baseline 的系统性错误。

本阶段只使用通用工程特征和井轨迹特征，不引入复杂 typewell 对齐。这样可以先验证 residual learning 本身是否有效。

## 2. 输入与输出

### 2.1 输入

```text
data/raw/
outputs/baseline_predictions_train_hidden.csv
outputs/baseline_cv_by_well.csv
outputs/cv_splits.csv
```

### 2.2 输出

```text
features/
|-- geometry_features_train.csv
|-- geometry_features_test.csv
`-- residual_targets.csv

models/
|-- residual_geometry_hgb.pkl
|-- residual_geometry_config.json
`-- residual_geometry_feature_list.txt

outputs/
|-- residual_geometry_oof.csv
|-- residual_geometry_cv_by_well.csv
`-- residual_geometry_test_predictions.csv

reports/
|-- residual_geometry_cv_report.md
|-- residual_geometry_failure_analysis.md
`-- residual_geometry_feature_importance.md

submissions/
`-- geometry_residual_submission.csv
```

注意：本阶段的旧结果已经被清理掉，当前文档描述的是应当重新生成的产物，而不是仓库里已经保留的冻结文件。

## 3. 残差目标定义

### 3.1 基础定义

对每个验证目标行：

```text
baseline_tvt = baseline prediction
residual_target = true_TVT - baseline_tvt
```

模型预测：

```text
residual_pred = model(features)
final_pred = baseline_tvt + residual_pred
```

### 3.2 为什么预测 residual

优点：

- baseline 已经解释大部分连续趋势；
- residual 通常量级更小；
- 模型更专注于地层偏移、轨迹变化和局部异常；
- 输出容易被约束和解释；
- 模型失败时可以 clip 或回退 baseline。

### 3.3 Residual 统计检查

在训练前必须输出：

- residual mean/std；
- residual quantiles；
- residual by well；
- residual by target length；
- residual by baseline error bucket；
- residual by GR missing rate。

报告：

```text
reports/residual_target_report.md
```

### 3.4 训练样本粒度

默认训练粒度是 row-level，因为 Kaggle RMSE 也是 row-level。但必须同时控制井级偏置：

- row-level loss 用于优化 leaderboard；
- per-well metrics 用于防止少数长井主导；
- 可以实验 `sample_weight = 1 / target_rows_per_well` 的 well-balanced 版本；
- ensemble 中保留 row-weighted 和 well-balanced 两类模型，观察 public/private gap。

## 4. 特征工程

### 4.1 行级基础特征

```text
MD
X
Y
Z
row_index
row_position = row_index / total_rows
MD_normalized_within_well
Z_normalized_within_well
```

### 4.2 已知段关系特征

```text
last_known_row
last_known_MD
last_known_TVT_input
distance_row_from_last_known
distance_MD_from_last_known
known_rows_count
target_rows_count
known_ratio
```

### 4.3 Baseline 特征

```text
baseline_tvt
baseline_slope
baseline_tail_window
baseline_local_slope_std
baseline_confidence
baseline_distance_penalty
```

baseline confidence 可由以下因素组成：

- tail slope 稳定性；
- hidden interval 长度；
- GR 缺失率；
- known rows 数量；
- local curvature。

### 4.4 轨迹几何特征

一阶差分：

```text
dX = diff(X)
dY = diff(Y)
dZ = diff(Z)
dMD = diff(MD)
dZ_dMD
dXY_dMD
```

二阶变化：

```text
ddZ_dMD
trajectory_curvature_proxy
inclination_change_proxy
```

滚动窗口：

```text
rolling_Z_mean_50
rolling_Z_std_50
rolling_dZ_dMD_mean_50
rolling_dZ_dMD_std_50
rolling_curvature_mean_50
```

窗口建议：

```text
25, 50, 100, 200, 500
```

### 4.5 井级特征

```text
well_total_rows
well_MD_span
well_Z_span
well_known_TVT_span
well_known_slope_mean
well_known_slope_std
well_GR_missing_rate
well_target_length
```

### 4.6 禁止或谨慎特征

训练 horizontal 中的 formation surface 列：

```text
ANCC, ASTNU, ASTNL, EGFDU, EGFDL, BUDA
```

这些列在 test 文件中不存在。除非能通过 typewell 或模型推断出同源信息，否则不能作为最终 test 特征直接使用。

### 4.7 人工 mask 下的特征重算

多 mask CV 中，所有依赖 `TVT_input` 的特征必须按 split 重算，不能复用原始训练井的完整 `TVT_input`。

必须区分两类特征：

| 特征类型 | 是否需要按 split 重算 |
|---|---|
| `MD/X/Y/Z` 几何差分 | 不需要 |
| `GR` rolling | 不需要，测试集提供 hidden GR |
| `last_known_TVT_input` | 需要 |
| baseline slope/confidence | 需要 |
| distance from last known TVT | 需要 |
| known TVT slope/std | 需要 |

如果脚本没有 split 参数，只能用于 original hidden，不得用于多 mask CV。

### 4.8 不使用 well ID 记忆

模型不应把 `well` 作为可直接记忆的类别特征。hidden wells 是新井，well ID 没有泛化意义。

允许：

- well-level 数值统计；
- target length；
- GR quality；
- trajectory summary。

不允许：

- well ID one-hot；
- well ID target encoding；
- 用训练井 ID 学 residual bias。

## 5. 脚本拆解

### 5.1 build_baseline_features.py

职责：

- 读取 baseline 输出；
- 计算 baseline 相关特征；
- 对 train hidden 和 test submission 行生成统一表。

输出：

```text
features/baseline_features_train.csv
features/baseline_features_test.csv
```

### 5.2 build_geometry_features.py

职责：

- 读取 horizontal files；
- 按井计算轨迹差分和 rolling features；
- 只输出 target rows 所需特征；
- 保证 train/test 字段一致。

输出：

```text
features/geometry_features_train.csv
features/geometry_features_test.csv
```

实现细节：

- 第一版可以用 CSV 输出，避免 `pyarrow` 依赖；
- 目前默认先按 CSV 走，等真的需要再补 Parquet；
- 如果使用 Parquet，必须把 `pyarrow` 固定进 `requirements.txt`；
- 输出必须包含 `well/row/id` 作为 key；
- 合并特征时必须检查 key 唯一性和行数一致。

### 5.3 train_residual_model.py

职责：

- 合并 baseline + geometry features；
- 构造 residual target；
- 按 CV split 训练；
- 输出 OOF prediction；
- 训练 final model；
- 输出 test prediction。

### 5.4 evaluate_model_cv.py

职责：

- 比较 model vs baseline；
- 输出 overall metrics；
- 输出 per-well metrics；
- 输出 error bucket；
- 输出 worst wells。

## 6. 模型选择

### 6.1 首选模型

```text
sklearn.ensemble.HistGradientBoostingRegressor
```

原因：

- sklearn 默认环境稳定；
- 训练快；
- 支持非线性；
- 不需要额外 Kaggle 安装；
- 适合第一版工程主干。

### 6.2 备选模型

| 模型 | 用途 |
|---|---|
| Ridge / ElasticNet | 线性 residual control |
| RandomForestRegressor | 非线性参考 |
| ExtraTreesRegressor | 鲁棒参考 |
| LightGBM | 后续强模型 |
| XGBoost | 后续强模型 |

### 6.3 参数搜索策略

早期不要大规模调参。

第一轮固定：

```text
learning_rate: 0.03 to 0.08
max_iter: 300 to 800
max_leaf_nodes: 15 to 63
l2_regularization: 0.0 to 1.0
min_samples_leaf: 20 to 100
```

只在 CV 稳定后再做系统搜索。

### 6.4 训练配置记录

每次训练都写出：

```text
models/<run_id>_config.json
```

字段：

```text
run_id
data_version
feature_version
split_version
model_class
params
random_seed
feature_columns
target_definition
sample_weight_mode
clip_config
```

没有 config 的模型不能进入 ensemble。

## 7. 训练与验证流程

### 7.1 单 split 流程

```text
load split
  -> mask TVT_input
  -> build baseline
  -> build features
  -> fit residual model on train wells
  -> predict validation rows
  -> final = baseline + residual
  -> score
```

### 7.2 多 split 流程

对所有 mask types：

- original hidden；
- trailing short；
- trailing long；
- mid contiguous；
- random contiguous。

分别输出：

- baseline RMSE；
- model RMSE；
- improvement；
- wells improved；
- wells degraded；
- worst degradation。

### 7.3 判断标准

模型进入下一阶段必须：

- overall RMSE 比 baseline 降低；
- median well RMSE 降低；
- P95 abs error 降低；
- worst 20 wells 中至少多数改善；
- degraded wells 数量可控；
- public visible 3 井 submission 曲线正常。

## 8. 防过拟合设计

### 8.1 Group by well

同一口井不能同时用于 residual model 的 train 和 validation。

### 8.2 Mask 多样性

模型不能只在 original hidden 上好，还要在其他 mask 上不过度退化。

### 8.3 Residual clip

对 residual prediction 做统计检查：

- residual p1/p99；
- extreme correction count；
- per-step residual jump。

若 residual 太极端：

```text
final_pred = baseline + clipped_residual
```

### 8.4 Conservative blend

第一版 residual 不直接全量使用：

```text
final = baseline + alpha * residual
alpha in {0.25, 0.5, 0.75, 1.0}
```

在 CV 上选择 alpha，并保留 conservative 版本用于提交。

### 8.5 模型校准与偏差修正

Residual model 可能有系统性 bias。需要评估：

- overall residual bias；
- bias by target length；
- bias by baseline confidence；
- bias by predicted residual magnitude。

如果发现稳定 bias，可以在 OOF 上学习一个轻量校准：

```text
residual_calibrated = a * residual_pred + b
```

校准必须只用 OOF，不可用 test 或 public LB 手调。

## 9. Failure Analysis

Residual 模型必须回答：

- 哪些井 baseline 好，residual 反而变差；
- 哪些井 baseline 差，residual 明显改善；
- 改善是否来自几何特征；
- 退化是否集中在长隐藏区间；
- residual 是否引入不合理震荡。

输出：

```text
reports/residual_geometry_failure_analysis.md
reports/figures/residual_geometry_worst_degraded/
reports/figures/residual_geometry_best_improved/
```

### 9.1 可视化要求

每个 best improved / worst degraded well 绘制：

- baseline；
- residual model final prediction；
- truth；
- residual prediction；
- GR；
- hidden interval；
- local slope。

目标是判断模型到底学到了几何规律，还是制造了局部噪声。

## 10. 本阶段完成标准

Part 2 完成必须满足：

- baseline features 完成；
- geometry features 完成；
- residual target report 完成；
- 第一版 residual model 完成；
- OOF prediction 完成；
- CV report 完成；
- 至少一个 geometry residual submission 完成；
- 证明它是否值得进入 GR/typewell 阶段。

## 11. 下一阶段入口条件

进入 Part 3 前必须有：

```text
features/geometry_features_train.csv
features/geometry_features_test.csv
outputs/residual_geometry_oof.csv
outputs/residual_geometry_cv_by_well.csv
submissions/geometry_residual_submission.csv
reports/residual_geometry_cv_report.md
```
