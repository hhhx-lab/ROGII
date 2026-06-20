# Part 1: 数据契约、验证体系与可信 Baseline

## 1. 阶段目标

本阶段的目标是建立整个项目的“地基”：

1. 明确数据契约，保证所有脚本对输入输出的理解一致；
2. 建立真实训练隐藏段 CV，作为所有后续模型的最低验证标准；
3. 建立多 mask CV，防止模型只适配一种隐藏区间；
4. 建立多个 baseline 版本，形成冲榜控制组；
5. 产出第一批 failure analysis，明确 baseline 失效在哪里。

本阶段不追求复杂模型。它的价值在于让后续所有模型都有可信比较对象。

## 2. 输入与输出

### 2.1 输入

```text
data/raw/
|-- train/
|-- test/
|-- sample_submission.csv
`-- AI_wellbore_geology_prediction_task_en.pptx
```

### 2.2 输出

```text
outputs/
|-- data_contract_summary.csv
|-- baseline_cv_by_well.csv
|-- baseline_predictions_train_hidden.csv
|-- cv_splits.csv
`-- failure_case_candidates.csv

reports/
|-- data_contract_report.md
|-- baseline_cv_report.md
|-- cv_design.md
`-- baseline_failure_analysis.md

submissions/
`-- baseline_tail_slope_submission.csv
```

## 3. 数据契约任务

### 3.1 文件级检查

脚本：

```text
scripts/check_data_contract.py
```

检查内容：

- `train/` 中每口井是否同时存在 horizontal、typewell、png；
- `test/` 中每口井是否同时存在 horizontal、typewell；
- `sample_submission.csv` 的 well ID 是否都能在 `test/` 找到；
- 每个 submission row index 是否落在对应 horizontal 文件行数范围内；
- 文件数量是否和 EDA 报告一致。

验收标准：

- 所有训练井配套文件完整；
- 所有 sample submission id 可解析；
- 所有 row index 有效；
- 报告中列出异常文件，异常数量必须为 0 才能进入下一步。

### 3.2 列级检查

训练 horizontal 必须包含：

```text
MD, X, Y, Z, ANCC, ASTNU, ASTNL, EGFDU, EGFDL, BUDA, TVT, GR, TVT_input
```

测试 horizontal 必须包含：

```text
MD, X, Y, Z, GR, TVT_input
```

typewell 必须包含：

```text
TVT, GR, Geology
```

检查内容：

- 缺失列；
- dtype；
- 全空列；
- TVT_input 缺失比例；
- GR 缺失比例；
- MD 是否单调；
- row index 是否连续。

验收标准：

- 关键列缺失时脚本直接失败；
- 非关键异常写入 report；
- 所有后续脚本读取该 report，避免静默错误。

### 3.3 数据版本与可追溯性

必须记录数据版本，避免后续 Kaggle 更新或重新下载后结果不可复现。

输出：

```text
outputs/data_version.json
```

字段：

```text
zip_path
zip_size_bytes
zip_sha256
raw_file_count
train_well_count
test_well_count
sample_submission_rows
created_at
```

验收标准：

- 每次跑 CV 和训练都读取并写入该 data version；
- 报告中引用相同 data hash；
- 如果数据 hash 变化，旧模型结果必须标记为不可直接比较。

## 4. CV Level 1: 训练井原始隐藏段验证

### 4.1 背景

训练井中 `TVT_input` 已经有 NaN 隐藏段，同时 `TVT` 保留完整真值。这个结构非常接近 Kaggle hidden rerun 任务。

验证定义：

```text
known_rows = TVT_input not null
target_rows = TVT_input is null
truth = TVT[target_rows]
```

### 4.2 脚本

当前已有：

```text
scripts/evaluate_baseline_cv.py
```

需要完善：

- 支持多个 baseline；
- 输出每行 prediction；
- 输出每口井 metrics；
- 输出整体 metrics；
- 输出 worst wells；
- 输出 error distribution。

### 4.3 指标

整体：

- RMSE；
- MAE；
- median absolute error；
- P90/P95/P99 absolute error；
- max absolute error；
- bias。

每口井：

- well RMSE；
- target_rows；
- target_md_span；
- target_tvt_span；
- target GR missing rate；
- baseline slope；
- residual bias；
- max jump。

### 4.4 验收标准

- 773 口训练井全部进入评估；
- 输出 `outputs/baseline_cv_by_well.csv`；
- 输出 `reports/baseline_cv_report.md`；
- 识别 worst 20 wells；
- 后续模型必须默认读取该 baseline 分数作为比较目标。

## 5. CV Level 2: 多 Mask 验证

### 5.1 为什么需要多 mask

Kaggle hidden test 的缺失区间可能不完全等同训练井原始 `TVT_input` NaN 区间。只使用原始隐藏段，模型可能过度适配一种缺失模式。

### 5.2 Mask 类型

| Mask 类型 | 设计 | 目的 |
|---|---|---|
| original_hidden | 直接使用 TVT_input NaN | 最接近官方结构 |
| trailing_short | 隐藏最后 10% 到 25% | 短尾段鲁棒性 |
| trailing_long | 隐藏最后 40% 到 75% | 长隐藏段鲁棒性 |
| mid_contiguous | 隐藏中间连续段 | 防止只会尾部外推 |
| random_contiguous | 随机起点连续隐藏 | 防止过拟合固定起点 |
| high_gr_missing | 选择 GR 缺失高区间 | 测 GR 失效场景 |
| high_curvature | 选择 TVT 曲率变化区间 | 测结构变化场景 |

### 5.3 脚本

```text
scripts/make_cv_splits.py
```

输出：

```text
outputs/cv_splits.csv
```

字段：

```text
split_id
well
mask_type
start_row
end_row
target_rows
known_rows_before
known_allowed_start_row
known_allowed_end_row
md_span
tvt_span
gr_missing_rate
local_slope_mean
local_slope_std
curvature_proxy
mask_seed
```

### 5.4 防泄漏规则

对每个 split：

- mask 区间内的 `TVT_input` 必须置 NaN；
- 特征不能使用 mask 区间的真实 `TVT`；
- 允许使用 mask 区间的 `MD/X/Y/Z/GR`，因为测试集也提供；
- 允许使用 typewell，因为测试集也提供；
- 禁止使用训练-only formation surface 作为最终 test 特征，除非仅用于分析或训练辅助。
- 人工 mask 后必须重新生成该 split 下的 `TVT_input_masked`，baseline 和所有“已知段相关特征”只能看 masked 后的已知段；
- 对 mid-section mask，不允许使用 mask 后方的 `TVT_input` 作为“未来已知段”，除非该实验明确模拟离线补全而非 Kaggle hidden rerun；
- 所有 split 必须保存 `known_allowed_start_row` 和 `known_allowed_end_row`，让特征脚本明确知道哪些 `TVT_input` 可用。

### 5.5 验收标准

- 至少生成 5 类 mask；
- 每类 mask 至少覆盖 300 口井；
- split 可复现，固定 seed；
- 每个 split 可以直接喂给 baseline 和 residual 评估脚本。

## 6. Baseline 家族设计

### 6.1 B0: Constant baseline

方法：

```text
pred = last known TVT_input
```

用途：

- 最低控制组；
- 检查任务难度；
- 验证 submission 流程。

### 6.2 B1: Per-well linear MD baseline

方法：

```text
fit TVT_input ~ MD on known rows
predict hidden rows
```

用途：

- 评估全局线性趋势是否足够；
- 通常会弱于局部 tail slope。

### 6.3 B2: Tail-slope baseline

方法：

```text
slope = median(diff(TVT_input) / diff(MD)) over last K known rows
pred = last_known_tvt + slope * (MD - last_known_MD)
```

参数：

- `K = 50, 100, 200, 500`；
- 对每个 K 做 CV；
- 选择 conservative 和 best-CV 两个版本。

### 6.4 B3: Robust local polynomial

方法：

- 取最后 K 个已知点；
- 拟合一阶或二阶多项式；
- 使用 robust loss 或异常点裁剪；
- 对斜率做限制。

用途：

- 捕捉轻微曲率；
- 风险是长距离外推不稳定。

### 6.5 B4: Smoothed baseline

方法：

- 先用 B2/B3 外推；
- 对预测曲线做轻量 smoothing；
- 限制单步跳变。

用途：

- 后处理控制组；
- 给 ensemble 提供 conservative curve。

### 6.6 Baseline 评估细节

Kaggle 评分是 row-level RMSE，所以整体分数按行计算；但工程稳健性必须同时看 per-well。

报告必须同时给：

- row-weighted overall RMSE；
- unweighted mean well RMSE；
- median well RMSE；
- worst 20 wells；
- target length weighted bucket；
- long hidden interval subset；
- high GR missing subset。

如果一个 baseline overall 最好但 worst-well tail 明显恶化，不直接作为主 baseline，只作为 aggressive candidate。

## 7. Failure Analysis

### 7.1 输出文件

```text
outputs/failure_case_candidates.csv
reports/baseline_failure_analysis.md
reports/figures/baseline_worst_wells/
```

### 7.2 每个失败井分析

记录：

- well id；
- RMSE；
- max absolute error；
- target length；
- GR missing rate；
- baseline slope；
- TVT true curve；
- baseline curve；
- GR curve；
- typewell GR；
- Geology labels；
- 失败类型初判。

### 7.3 失败类型

| 类型 | 含义 | 后续解决方向 |
|---|---|---|
| smooth_bias | 整段偏移 | residual model |
| slope_change | 斜率变化 | geometry / curvature |
| abrupt_shift | 突然跳变 | typewell / geology |
| gr_transition | GR 形态变化 | GR features |
| long_extrapolation | 隐藏段过长 | uncertainty routing |
| missing_gr | GR 缺失严重 | fallback strategy |

### 7.4 图表细节

每个 worst well 至少生成一张图，包含：

- `TVT` truth；
- `TVT_input` known points；
- baseline prediction；
- absolute error；
- `GR` 曲线；
- hidden interval shade；
- typewell Geology label bands，如果可读。

图表用于工程判断，不提交 Kaggle。

### 7.5 运行时间与缓存

Part 1 会反复读取 773 口井 CSV。为避免后续迭代变慢：

- 先实现 CSV 版本，保证无额外依赖；
- 如需 Parquet 缓存，必须在 `requirements.txt` 加 `pyarrow` 或改用 `pickle/csv`；
- 所有缓存必须写入 `features/` 或 `outputs/`，并在文件名中包含 data version 或 config hash。

## 8. 本阶段完成标准

Part 1 完成必须满足：

- 数据契约报告完成；
- 真实训练隐藏段 baseline CV 完成；
- 多 mask split 完成；
- B0 到 B4 至少完成 B0/B1/B2；
- worst wells 报告完成；
- 明确 baseline 失效类型；
- 后续 residual 模型有明确训练目标和验证入口。

## 9. 下一阶段入口条件

进入 Part 2 前必须有：

```text
outputs/baseline_cv_by_well.csv
outputs/baseline_predictions_train_hidden.csv
outputs/cv_splits.csv
reports/baseline_cv_report.md
reports/baseline_failure_analysis.md
```

这些文件是 residual model 的训练和比较基础。
