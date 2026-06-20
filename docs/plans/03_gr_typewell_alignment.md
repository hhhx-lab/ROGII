# Part 3: GR 信号与 Typewell 对齐地质增强

## 1. 阶段目标

本阶段引入真正的地质信号。Part 2 的 geometry residual 主要利用井轨迹和 TVT 连续性，但遇到地层变化、断层、GR 形态突变时会不足。

本阶段要解决：

1. 水平井 GR 能否提示 hidden interval 的地层变化；
2. typewell 垂直参考 GR 能否帮助定位 TVT 偏移；
3. Geology label 能否约束 residual correction；
4. GR/typewell 信息什么时候可信，什么时候必须回退。

## 2. 输入与输出

### 2.1 输入

```text
data/raw/train/*__horizontal_well.csv
data/raw/train/*__typewell.csv
data/raw/test/*__horizontal_well.csv
data/raw/test/*__typewell.csv
features/baseline_features_*.parquet
features/geometry_features_*.parquet
outputs/residual_geometry_oof.csv
```

### 2.2 输出

```text
features/
|-- gr_features_train.parquet
|-- gr_features_test.parquet
|-- typewell_features_train.parquet
|-- typewell_features_test.parquet
|-- alignment_features_train.parquet
`-- alignment_features_test.parquet

models/
|-- residual_gr_hgb.pkl
|-- residual_typewell_hgb.pkl
`-- residual_alignment_config.json

outputs/
|-- residual_gr_oof.csv
|-- residual_typewell_oof.csv
|-- typewell_alignment_diagnostics.csv
`-- geology_failure_cases.csv

reports/
|-- gr_feature_report.md
|-- typewell_alignment_report.md
|-- geology_failure_analysis.md
`-- residual_typewell_cv_report.md
```

## 3. GR 特征计划

### 3.1 基础 GR 特征

对 horizontal well：

```text
GR
GR_is_missing
GR_filled_ffill
GR_filled_bfill
GR_filled_interpolate
GR_global_median_fill
```

每个填充值都必须保留 missing flag，不能假装真实观测。

### 3.2 局部滚动特征

窗口：

```text
25, 50, 100, 200, 500
```

特征：

```text
GR_roll_mean
GR_roll_std
GR_roll_min
GR_roll_max
GR_roll_median
GR_roll_range
GR_roll_valid_count
GR_roll_missing_rate
```

### 3.3 GR 形态特征

```text
GR_gradient
GR_abs_gradient
GR_second_diff
GR_local_zscore
GR_peak_proxy
GR_trough_proxy
GR_volatility
GR_trend_sign
```

### 3.4 与已知段关系

```text
GR_last_known
GR_last_known_roll_mean
GR_delta_from_last_known
GR_hidden_mean_minus_known_tail_mean
GR_hidden_std_minus_known_tail_std
```

### 3.5 GR 质量评分

每口井生成：

```text
well_GR_missing_rate
target_GR_missing_rate
GR_valid_count_in_target
GR_quality_score
```

用途：

- 作为模型特征；
- 用于 ensemble routing；
- 用于 typewell alignment 是否启用。

### 3.6 GR 特征边界

Kaggle 测试文件提供 hidden rows 的 `GR`，因此比赛任务中允许使用 hidden interval 的 GR。报告中必须明确这是 Kaggle 离线预测设定；如果未来做实时钻井版本，要另设只能使用当前位置之前 GR 的在线特征版本。

GR 填充规则：

- 保留原始 `GR_is_missing`；
- 插值只用于 rolling/shape 特征，不覆盖原始观测；
- 大段缺失时不做虚假平滑；
- 每个 rolling 特征同时输出 valid count。

## 4. Typewell 特征计划

### 4.1 Typewell 基础统计

对 `{well}__typewell.csv`：

```text
typewell_TVT_min
typewell_TVT_max
typewell_GR_mean
typewell_GR_std
typewell_GR_missing_rate
geology_label_count
dominant_geology_label
```

### 4.2 Baseline TVT 附近采样

对每个 target row 的 baseline TVT：

在 typewell 中查找最近 TVT 点，提取：

```text
typewell_GR_at_baseline
typewell_GR_window_mean_25
typewell_GR_window_std_25
typewell_GR_window_mean_50
typewell_GR_window_std_50
typewell_geology_at_baseline
distance_to_geology_boundary
nearby_geology_change_flag
```

越界处理：

- 如果 `baseline_tvt` 超出 typewell TVT 范围，设置 `typewell_out_of_range = 1`；
- 所有 typewell window 特征置为 NaN 或边界值，并保留 flag；
- alignment 模块对 out-of-range 点降权或禁用。

### 4.3 Geology label 编码

初版：

- one-hot top labels；
- rare label 合并为 `OTHER`；
- boundary distance；
- current label run length。

后续：

- label transition pattern；
- label sequence embedding；
- geology risk class。

编码防过拟合：

- 不做基于 `TVT` 真值 residual 的 label target encoding，除非严格 OOF；
- rare label 合并规则必须只由训练 label 频次决定；
- test 中新 label 归入 `OTHER`。

## 5. GR / Typewell 对齐计划

### 5.1 对齐目标

如果 baseline TVT 有偏移，那么 horizontal GR 在某个 candidate TVT offset 处可能与 typewell GR 更相似。

因此对每个 target row 或 target window，搜索：

```text
candidate_tvt = baseline_tvt + offset
offset in [-offset_window, +offset_window]
```

找到最相似的 offset，并把 offset 或相似度作为特征。

### 5.2 简单滑窗相关

参数：

```text
offset_window: 100, 200, 400 ft
offset_step: 5, 10, 20 ft
curve_window: 25, 50, 100 rows
```

相似度指标：

- Pearson correlation；
- Spearman correlation；
- normalized MAE；
- cosine similarity；
- shape distance after z-score。

输出特征：

```text
best_offset
best_similarity
second_best_similarity
similarity_margin
similarity_confidence
alignment_enabled_flag
```

符号约定：

```text
best_offset = candidate_tvt - baseline_tvt
positive offset means predicted TVT should move deeper/larger
```

所有报告和模型必须使用同一符号约定，避免 blend 时方向反了。

### 5.3 分段对齐

不要每一行独立对齐，否则噪声大。

方案：

1. 将 hidden interval 划分成固定窗口；
2. 每个窗口估计一个 best offset；
3. 对 offset 曲线平滑；
4. 每行继承窗口 offset 和 confidence。

窗口质量控制：

- 有效 GR 点少于最小阈值时不对齐；
- horizontal GR 方差过低时不对齐；
- typewell GR 方差过低时不对齐；
- best 和 second best similarity 差距太小时 confidence 降低。

### 5.4 DTW 对齐实验

如果滑窗相关在 CV 上有效，再做 DTW：

- 只在 GR quality 高的井启用；
- 对 GR 做 smoothing 和 z-score；
- 限制 warping window；
- 输出 DTW cost 和 estimated offset。

风险：

- 计算量大；
- 容易过拟合；
- 解释复杂。

所以 DTW 不作为第一版主线，只作为后期增强。

## 6. 模型结构

### 6.1 GR residual model

特征：

```text
baseline + geometry + GR
```

目标：

```text
residual = TVT - baseline
```

输出：

```text
outputs/residual_gr_oof.csv
reports/residual_gr_cv_report.md
```

### 6.2 Typewell residual model

特征：

```text
baseline + geometry + GR + typewell + alignment
```

目标：

```text
residual = TVT - baseline
```

输出：

```text
outputs/residual_typewell_oof.csv
reports/residual_typewell_cv_report.md
```

### 6.3 Alignment direct correction

额外实验：

```text
pred = baseline + alpha * best_offset
```

或者：

```text
alignment_residual = f(best_offset, similarity_confidence)
```

用途：

- 判断对齐信号本身是否有预测力；
- 给模型 ensemble 提供独立成员。

## 7. 验证切片

GR/typewell 模块不能只看 overall RMSE。

必须比较：

| 切片 | 目的 |
|---|---|
| GR complete wells | GR 特征上限 |
| GR missing high wells | fallback 是否稳 |
| high baseline error wells | 是否解决 baseline 失败 |
| long hidden intervals | 对长区间是否有效 |
| high curvature wells | 对地层变化是否有效 |
| typewell similarity high | 对齐可信场景 |
| typewell similarity low | 对齐不可信场景 |

## 8. 防过拟合规则

### 8.1 GR 不能变成泄漏代理

不能用 hidden target 真值构造 GR 特征。

允许：

- hidden rows 的 GR；
- typewell GR；
- typewell Geology；
- baseline TVT 附近 typewell 信息。

不允许：

- 用 hidden rows 的 `TVT`；
- 用训练-only formation surface 直接推 test；
- 根据 visible test 3 井手调 offset。

### 8.2 Alignment 需要 confidence

如果相似度低：

- 不使用 direct correction；
- 只作为弱特征；
- ensemble 中降权。

### 8.3 按质量路由

```text
if GR_quality_low:
    prefer baseline + geometry
elif alignment_confidence_high:
    allow typewell correction
else:
    use balanced residual
```

### 8.4 Typewell 对齐的计算预算

滑窗搜索可能很慢。第一版必须限制计算量：

- 只对 target rows 或 target windows 做对齐；
- 先按窗口估计 offset，再广播到行；
- offset step 从粗到细；
- 缓存每口井的 typewell 插值结果；
- 输出运行时间统计。

若全量对齐超过 Kaggle notebook 预算，必须降级为：

```text
baseline + geometry + GR
```

或只对 high-risk wells 启用 typewell alignment。

## 9. Failure Analysis

要回答：

- GR 加入后哪些井明显改善；
- typewell 对齐后 worst wells 是否减少；
- 对齐失败的井有什么共同特征；
- GR 缺失时模型是否退化；
- Geology boundary 附近是否改善。

输出：

```text
reports/geology_failure_analysis.md
reports/figures/typewell_alignment_examples/
```

图表：

- horizontal GR；
- typewell GR；
- baseline TVT；
- final prediction；
- truth；
- best offset curve；
- Geology label bands。

### 9.1 对齐有效性判定

不能只看模型分数，还要验证 alignment 是否有物理意义：

- high confidence offset 是否连续；
- offset 是否集中在合理范围；
- best similarity 是否显著高于 second best；
- Geology boundary 附近 offset 是否更有解释力；
- alignment correction 是否降低 baseline residual，而不是放大噪声。

## 10. 本阶段完成标准

Part 3 完成必须满足：

- GR features 完成；
- typewell features 完成；
- simple alignment features 完成；
- GR residual CV 完成；
- typewell residual CV 完成；
- 至少在 high baseline error wells 上有明显改善；
- 有 alignment confidence 和 fallback 机制；
- 产出 aggressive submission。

## 11. 下一阶段入口条件

进入 Part 4 前必须有：

```text
features/gr_features_train.parquet
features/typewell_features_train.parquet
features/alignment_features_train.parquet
outputs/residual_gr_oof.csv
outputs/residual_typewell_oof.csv
reports/typewell_alignment_report.md
submissions/typewell_residual_submission.csv
```
