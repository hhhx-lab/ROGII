# Part 3: GR / Typewell Alignment 特征与修正信号计划

Part 3 的目标不是直接生成最终 TVT，也不是把 baseline 丢掉。

它的正确定位是：

```text
baseline_tvt 是锚点
GR / typewell alignment 提供地质证据
residual model 或 gater 决定怎么用这些证据
```

也就是说，Part 3 产出的东西主要应该进入：

- residual model 的特征；
- gater 的输入；
- route / confidence；
- failure analysis。

不能把 alignment offset 直接无条件加到 final TVT 上。

## 1. 当前真实状态

当前已经实现的是 diagnostics / route，而不是强 correction。

`reports/part3_diagnostics_report.md` 显示：

- train routes：
  - `typewell_alignment`: `635`
  - `gr_residual`: `92`
  - `baseline_fallback`: `35`
  - `geometry_residual`: `11`
- test routes：
  - 当前全部是 `gr_residual`

当前 Part 3 已经做的事情：

- 估计 GR quality；
- 估计 baseline confidence；
- 估计 typewell quality；
- 生成 risk score；
- 给每口井一个 route suggestion。

当前还没有完成的事情：

- alignment 特征还没有系统进入更强模型；
- alignment correction 还没有被 OOF 证明稳定；
- route 还没有变成真正的 alpha gater；
- typewell offset 不能作为最终强修正直接使用。

## 2. 为什么需要 Part 3

Part 2 的 residual model 主要从 baseline 和轨迹几何里学习 correction。它可以修正很多系统性误差，但有些问题只有地质信号能解释：

- hidden 段 GR 形态和已知段明显不同；
- typewell 在某个 TVT offset 处和 horizontal GR 更相似；
- baseline 外推到的 TVT 层位可能不是最合适的层位；
- 某些井 residual 修坏，是因为模型没有判断信号是否可信。

Part 3 要解决的是：

```text
这口井现在有没有可信地质证据？
证据支持 residual 往哪个方向修？
证据强到足以让 alpha 变大吗？
证据弱时是否应该回退 baseline？
```

## 3. 输入与输出

### 3.1 输入

```text
data/train/*__horizontal_well.csv
data/train/*__typewell.csv
data/test/*__horizontal_well.csv
data/test/*__typewell.csv
features/baseline_features_train.csv
features/baseline_features_test.csv
features/geometry_features_train.csv
features/geometry_features_test.csv
outputs/residual_geometry_oof.csv
```

脚本层面当前主要入口：

```text
scripts/build_part3_diagnostics.py
scripts/build_part3_features.py
```

### 3.2 当前输出

当前已实现/预期已有的输出：

```text
outputs/part3_diagnostics.csv
reports/part3_diagnostics_report.md
features/gr_features_train.csv
features/gr_features_test.csv
features/typewell_features_train.csv
features/typewell_features_test.csv
features/alignment_features_train.csv
features/alignment_features_test.csv
```

### 3.3 下一步计划输出

下一步需要更明确地输出：

```text
best_offset
best_similarity
second_best_similarity
similarity_margin
alignment_confidence
alignment_support_fraction
alignment_enabled_flag
self_alignment_score
typewell_alignment_score
alignment_direction_consistency
alignment_failure_reason
```

这些字段应该同时出现在 train 和 test 特征表里，并且字段含义保持一致。

## 4. GR 基础特征

### 4.1 为什么做

GR 是测试 hidden rows 里可见的地质信号。它可以告诉我们 hidden 段的地层形态是否延续、突变或偏移。

### 4.2 解决什么问题

解决：

- 只有轨迹几何时无法识别的层位变化；
- GR 缺失导致模型不该过度信 GR；
- hidden 段和 known 段形态不同导致 baseline 可能偏。

### 4.3 输入

来自 horizontal well：

```text
MD
GR
TVT_input
row index
target mask
```

### 4.4 输出

基础 GR 特征：

```text
GR
GR_is_missing
GR_filled_interpolate
GR_global_median_fill
GR_roll_mean_25
GR_roll_std_25
GR_roll_mean_50
GR_roll_std_50
GR_roll_missing_rate_25
GR_gradient
GR_second_diff
GR_abs_gradient
GR_local_zscore
GR_peak_proxy
GR_trough_proxy
GR_volatility
gr_quality_score
```

每个填充特征都要保留 missing flag，不能把填充值当真实观测。

### 4.5 如何验证

- GR complete wells 是否比 GR missing high wells 更容易改善；
- GR quality 高的井，GR residual 是否优于 geometry residual；
- GR quality 低的井，gater 是否能回退；
- 加入 GR 后 P95/P99 是否变好。

### 4.6 失败时回退

- GR missing rate 高时禁用 GR 强特征；
- 只保留 `gr_quality_score` 给 gater；
- final candidate 回退 geometry residual 或 baseline。

## 5. Horizontal GR Self-Alignment

### 5.1 为什么做

PPTX 和数据结构都提示：水平井自身 PS 前后的 GR 形态可能很有用。也就是说，在看 typewell 之前，应该先问：

```text
hidden 段 GR 像不像 known 段后面某种延续？
hidden 段是否出现了明显形态漂移？
```

### 5.2 解决什么问题

解决：

- 只看 typewell 可能忽略 horizontal 自身的连续信号；
- typewell 和 horizontal 不完全同尺度时，自身 GR 更稳；
- baseline 修坏的井可能能通过 self-alignment 识别为“不要强修”。

### 5.3 输入

```text
known segment GR
known tail GR
hidden segment GR
row distance from last known
baseline confidence
GR missing flags
```

### 5.4 输出

建议输出：

```text
self_known_tail_mean
self_known_tail_std
self_hidden_mean
self_hidden_std
self_similarity_to_known_tail
self_best_lag
self_similarity_margin
self_change_point_score
self_alignment_confidence
self_alignment_enabled_flag
```

### 5.5 如何验证

- high self-alignment confidence 的井，residual 是否更准确；
- self change point 高的井，baseline 是否更容易失败；
- self-alignment 特征加入 residual 后，OOF 是否改善；
- self-alignment 作为 gater 输入后，degraded wells 是否减少。

### 5.6 失败时回退

- 如果 self-alignment 和 OOF residual 没有关系，只保留为诊断；
- 如果只在少数井有效，做 route-specific feature；
- 不允许 self-alignment 单独改 final TVT。

## 6. Horizontal GR vs Typewell GR Alignment

### 6.1 为什么做

baseline 给了每个 target row 一个 `baseline_tvt`。如果这个 TVT 有偏移，那么 horizontal GR 可能在：

```text
candidate_tvt = baseline_tvt + offset
```

附近和 typewell GR 更相似。这个 offset 可能提示 residual 的方向。

### 6.2 解决什么问题

解决：

- baseline TVT 整段偏上或偏下；
- typewell 提供了更稳定的垂直 GR 参考；
- Part 2 residual 没有明确地质锚点；
- gater 需要知道 alignment 信号是否可信。

### 6.3 输入

```text
horizontal target GR window
baseline_tvt for target rows
typewell TVT
typewell GR
GR quality score
typewell quality score
baseline confidence
```

### 6.4 对齐搜索

对每个 target window 搜索：

```text
candidate_tvt = baseline_tvt + offset
offset in [-offset_window, +offset_window]
```

第一版建议：

```text
offset_window: 100, 200, 400 ft
offset_step: 5, 10, 20 ft
curve_window: 25, 50, 100 rows
```

相似度可以比较：

- Pearson correlation；
- Spearman correlation；
- normalized MAE；
- cosine similarity；
- z-score 后的 shape distance。

### 6.5 输出

必须输出：

```text
best_offset
best_similarity
second_best_similarity
similarity_margin
alignment_confidence
alignment_support_fraction
alignment_enabled_flag
alignment_failure_reason
```

符号约定必须固定：

```text
best_offset = candidate_tvt - baseline_tvt
positive offset means candidate TVT is deeper/larger than baseline TVT
```

如果符号约定混乱，后续 residual / gater 会把 correction 方向弄反。

### 6.6 可信度判断

`alignment_confidence` 不能只看 best similarity，还要看：

- best 和 second best 的差距；
- horizontal GR 有效点比例；
- typewell GR 有效点比例；
- window 内 GR 方差是否足够；
- offset 是否在合理范围；
- 相邻 window 的 offset 是否连续；
- self-alignment 和 typewell alignment 是否一致。

建议规则：

```text
alignment_enabled_flag = 1 only if:
  horizontal valid fraction high enough
  typewell valid fraction high enough
  best_similarity high enough
  similarity_margin high enough
  offset not on search boundary
```

### 6.7 如何验证

验证不能只看 overall RMSE。需要切片：

- alignment enabled vs disabled；
- high confidence vs low confidence；
- offset positive vs negative；
- GR missing high vs low；
- baseline high error wells；
- baseline good wells；
- long target interval wells。

关键问题：

- high confidence alignment 是否真的更准；
- `best_offset` 的方向是否和真实 residual 符号一致；
- alignment 加入 residual 后是否减少 worst wells；
- alignment 加入 gater 后是否减少被修坏的 baseline-good wells。

### 6.8 失败时回退

- enabled subset 不提升：alignment 只保留 diagnostics；
- high confidence 也不稳定：不进入 candidate pool；
- offset 方向经常错：只把 similarity/confidence 给 gater，不使用 offset；
- 计算太慢：只对 high-risk wells 或窗口级运行；
- OOF 变差：禁用 alignment-enhanced residual。

## 7. Typewell 基础特征

### 7.1 为什么做

typewell 是垂直参考井，提供 `TVT` 和 `GR` 的关系。它可以帮助模型理解 baseline TVT 附近的地质背景。

### 7.2 输入

```text
typewell TVT
typewell GR
optional training Geology
baseline_tvt
```

训练集 typewell 可能有 `Geology`，测试集通常没有。不能依赖 test 不存在的 `Geology` 做最终特征。

### 7.3 输出

```text
typewell_tvt_min
typewell_tvt_max
typewell_gr_mean
typewell_gr_std
typewell_gr_missing_rate
typewell_gr_at_baseline
typewell_interp_gradient
typewell_out_of_range
typewell_boundary_margin
typewell_nearest_tvt_distance
typewell_quality_score
typewell_gr_window_mean_25
typewell_gr_window_std_25
typewell_gr_window_count_25
typewell_gr_window_missing_rate_25
```

### 7.4 如何验证

- typewell quality 高的井，typewell-enhanced residual 是否更好；
- out-of-range 的井是否更容易退化；
- typewell window 特征是否降低 long target wells 的误差。

### 7.5 失败时回退

- typewell quality 低时只保留 flag；
- out-of-range 时禁用强 alignment；
- `Geology` 只用于训练期分析，不进入 test 直接特征。

## 8. Alignment 如何进入最终模型

正确用法：

```text
alignment features -> residual model
alignment confidence -> gater
alignment route -> candidate selection
```

错误用法：

```text
final_tvt = baseline_tvt + best_offset
```

除非 direct offset correction 在 OOF 上单独证明稳定，否则不能这样做。

建议三步走：

1. 先只输出 diagnostics 和 alignment features；
2. 把 features 加入 residual candidate，比较 OOF；
3. 把 confidence 加入 gater，控制 alpha。

如果要做 direct correction，也必须写成 gated 形式：

```text
final_tvt = baseline_tvt + alpha * alignment_offset
```

而且 `alpha` 必须由 OOF 验证，不允许手工看 public LB 调。

## 9. Part 3 与 Gater 的关系

Part 3 提供 gater 最需要的信号：

```text
Part3_route
GR_missing_rate
gr_quality_score
typewell_quality_score
alignment_confidence
alignment_support_fraction
similarity_margin
alignment_enabled_flag
per_well_risk_score
```

gater 使用这些信号决定：

```text
alpha = how much to trust residual / alignment correction
```

例子：

```text
if alignment_confidence high and baseline_confidence low:
    allow larger correction
elif baseline_confidence high and alignment_confidence low:
    reduce alpha toward baseline
elif GR missing high:
    prefer geometry or baseline fallback
```

## 10. 防过拟合规则

必须遵守：

- 不用 hidden true TVT 构造 alignment；
- 不用 visible test 3 口井手调 offset；
- 不把训练专属 formation surface 直接用于 test；
- 不把 test 不存在的 `Geology` 当直接特征；
- 同一口井不能同时进入 residual train 和 validation；
- 所有 alignment 阈值必须通过 OOF 选择。

允许：

- 使用 test hidden rows 的 GR，因为比赛离线数据提供它；
- 使用 typewell GR；
- 使用 baseline TVT 附近的 typewell 插值；
- 使用 training Geology 做分析和统计，但不能假设 test 有同列。

## 11. 计算预算

alignment 搜索可能很慢。第一版必须控制计算量：

- 先做 window-level，不逐行独立搜索；
- offset step 先粗后细；
- 缓存 typewell 插值；
- 只对 target windows 做；
- 对 GR 缺失严重的井直接跳过；
- 输出运行时间统计。

如果全量运行超过 Kaggle notebook 预算：

- 只在服务器离线生成 features；
- 或只对 high-risk wells 启用 alignment；
- 或在 final submission 中回退 `baseline + SGD/XGBoost residual`。

## 12. 完成标准

当前已完成标准：

- diagnostics / route 能生成；
- GR / typewell / alignment feature 文件有基本输出；
- Part 4 可以读取 route 做候选 blend。

下一步完成标准：

- self-alignment features 完成；
- typewell alignment features 完成；
- `best_offset` / `best_similarity` / `similarity_margin` / `alignment_confidence` 等字段稳定输出；
- alignment-enhanced residual candidate 有 OOF；
- gater 能使用 alignment confidence；
- OOF 证明 alignment 至少在某个可信 subset 上有收益；
- 如果 OOF 不提升，alignment 不进入最终强 correction。

## 13. 进入 Part 4 的条件

Part 3 进入 Part 4 前，至少要提供：

```text
outputs/part3_diagnostics.csv
features/gr_features_train.csv
features/gr_features_test.csv
features/typewell_features_train.csv
features/typewell_features_test.csv
features/alignment_features_train.csv
features/alignment_features_test.csv
reports/part3_diagnostics_report.md
```

如果 alignment-enhanced residual 尚未通过 OOF，就只能把 Part 3 当作 route / gater 输入，不能把它写成已完成的 correction model。
