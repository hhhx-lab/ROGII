# Part 3: GR 信号、水平井自对齐与 Typewell 对齐增强

## 1. 阶段目标

本阶段引入真正的地质信号。Part 2 的 geometry residual 主要利用井轨迹和 TVT 连续性，但遇到地层变化、断层、GR 形态突变时会不足。

这里的目标不是再做一个和 baseline 并列竞争的“新模型”，而是做一个以 baseline 为锚点的统一修正器：

```text
final = baseline + gated_correction
```

也就是说，Part 3 的工作是回答：

- 什么时候应该沿着 baseline 继续走；
- 什么时候可以用 GR/typewell 把预测往上或往下修一点；
- 修正幅度多大才算可信；
- 什么时候应该直接把 gate 关掉，回到 baseline。

本阶段要解决：

1. 水平井 GR 能否提示 hidden interval 的地层变化；
2. 先做 horizontal self-GR alignment，再判断是否需要 typewell 证据；
3. typewell 垂直参考 GR 能否帮助定位 TVT 偏移；
4. Geology label 能否约束 residual correction；
5. GR/typewell 信息什么时候可信，什么时候必须回退。

## 2. 输入与输出

### 2.1 输入

```text
data/raw/train/*__horizontal_well.csv
data/raw/train/*__typewell.csv
data/raw/test/*__horizontal_well.csv
data/raw/test/*__typewell.csv
features/baseline_features_*.csv
features/geometry_features_*.csv
outputs/residual_geometry_oof.csv
```

### 2.2 输出

```text
features/
|-- gr_features_train.csv
|-- gr_features_test.csv
|-- typewell_features_train.csv
|-- typewell_features_test.csv
|-- alignment_features_train.csv
`-- alignment_features_test.csv

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

训练集 typewell 还带有 `Geology` 列；测试集 typewell 只有 `TVT` 和 `GR`，没有 `Geology`。

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
- test 中没有 `Geology`，所以这里的编码只能用于训练期分析、类别统计和路由规则，不能作为 test 直接特征。

## 5. Horizontal self-GR 对齐计划

### 5.1 对齐目标

`reports/data_raw_review.md` 已确认，PPTX 提示 PS 前 horizontal GR 可能比 typewell 更能解释 PS 后 horizontal GR。因此 Part 3 不能只做 typewell 对齐，还要先做水平井自身的 GR 模式对齐。

目标是：

- 用已知段的 horizontal GR 作为参考模板；
- 在 hidden interval 中寻找与已知段最相似的 motif、shape 或局部统计；
- 判断 hidden 段是延续、漂移，还是发生了层位偏移。

### 5.2 特征

```text
known_tail_GR_mean
known_tail_GR_std
known_tail_GR_gradient
hidden_GR_similarity_to_known_tail
hidden_GR_change_point_score
hidden_GR_motif_score
```

### 5.3 路由关系

- self-GR alignment 先做低成本、强约束版本；
- typewell alignment 作为第二路证据；
- 两者一致时提高置信度，不一致时回退 baseline 或 geometry residual。

## 6. GR / Typewell 对齐计划

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

第一版实现里，窗口大小先固定，先保证能稳定跑通和解释；等窗口级结果稳定后，再做更细的 offset 搜索。

第一版路由阈值可以先用：

- `typewell_alignment`: `gr_quality_score >= 0.12` 且 `typewell_quality_score >= 0.48`，再加上 `alignment_confidence > 0.04`
- `gr_residual`: `gr_quality_score >= 0.10`
- `geometry_residual`: `baseline_confidence >= 0.10`
- 其余全部回退到 `baseline_fallback`

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

## 7. 模型结构

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
- 给统一修正器提供一个可解释的 correction source；
- 作为后续 blend / routing 的输入，而不是和 baseline 平行竞争。

## 8. 验证切片

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

## 9. 防过拟合规则

### 9.1 GR 不能变成泄漏代理

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

注意：`typewell Geology` 只在训练集存在，所以它适合做训练期分析、类别聚合和路由先验，不适合直接进入 test 特征表。

### 9.2 Alignment 需要 confidence

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
- 产出 aggressive submission；
- 所有修正都能解释成 baseline 上的 gated correction，而不是独立黑盒模型。

## 11. 下一阶段入口条件

进入 Part 4 前必须有：

```text
features/gr_features_train.csv
features/typewell_features_train.csv
features/alignment_features_train.csv
outputs/residual_gr_oof.csv
outputs/residual_typewell_oof.csv
reports/typewell_alignment_report.md
submissions/typewell_residual_submission.csv
```
