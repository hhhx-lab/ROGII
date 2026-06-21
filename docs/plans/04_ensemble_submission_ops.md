# Part 4: 集成、后处理、Notebook 工程化与冲榜运营

## 1. 阶段目标

本阶段把前面模型变成可控的冲榜系统。

目标：

1. 将 baseline、geometry residual、GR residual、typewell residual 组合到同一个最终预测器里；
2. 通过后处理约束保证曲线工程可信；
3. 生成 conservative / balanced / aggressive 三类提交；
4. 建立 Kaggle notebook 复现流程；
5. 建立 leaderboard 反馈闭环，持续冲击第一名。

当前仓库里，Part 2 的旧结果和最终提交成品已经被清理掉了。下面列出的 outputs / submissions / reports 更像是本阶段需要重新生成的契约，而不是已经稳定保留的冻结产物。

## 2. 输入与输出

### 2.1 输入

```text
outputs/baseline_predictions_*.csv
outputs/residual_geometry_oof.csv
outputs/part3_diagnostics.csv
submissions/*_submission.csv
reports/*_cv_report.md
```

### 2.2 输出

```text
submissions/
|-- conservative_submission.csv
|-- balanced_submission.csv
`-- aggressive_submission.csv

outputs/
|-- blend_oof.csv
|-- blend_cv_by_well.csv
|-- postprocess_diagnostics.csv
`-- submission_manifest.json

reports/
|-- ensemble_report.md
|-- postprocess_report.md
|-- submission_log.md
`-- final_model_card.md

notebooks/
`-- rogii_submission_pipeline.ipynb
```

当前可直接复用的脚本与文档：

- `scripts/blend_predictions.py`
- `scripts/postprocess_predictions.py`
- `scripts/make_submission.py`
- `notebooks/rogii_submission_pipeline.ipynb`
- `reports/ensemble_report.md`
- `reports/postprocess_report.md`
- `reports/submission_log.md`
- `reports/final_model_card.md`

## 3. 模型池设计

### 3.1 基础成员

| 成员 | 角色 |
|---|---|
| B2 tail-slope baseline | 稳定控制组 |
| geometry residual | 轨迹修正 |
| Part 3 routing | GR / typewell 置信修正 |

### 3.2 成员要求

每个模型成员必须提供：

- OOF prediction；
- test prediction；
- CV report；
- per-well metrics；
- prediction confidence 或 quality score；
- feature/config 记录。

没有 OOF 的模型不能进入正式 ensemble。

当前主线已经满足这一要求的成员是：

- tail-slope baseline；
- geometry residual；
- Part 3 routing / postprocess。

### 3.3 模型成员一致性检查

进入 ensemble 前必须检查：

- 所有 OOF 覆盖同一组 `split_id/well/row/id`；
- 所有 OOF 覆盖同一组 `well/row/id`；
- 所有 test prediction 覆盖完整 `sample_submission.csv`；
- 预测列无 NaN/inf；
- 预测值范围在训练 TVT 合理范围附近；
- 每个模型成员有 config 和 CV report。

## 4. 集成策略

### 4.1 固定权重 blend

第一版：

```text
final = baseline + w1 * geometry_residual
```

权重通过 OOF CV 选择。

搜索方式：

- coarse grid；
- 限制 aggressive 权重；
- 比较 overall RMSE 和 P95 error；
- 记录 top 20 candidate weights。

权重搜索约束：

- 每个权重非负；
- conservative blend 中 baseline 权重或 baseline residual anchor 必须足够高；
- aggressive blend 可以增加 typewell 权重，但必须记录 high-risk wells；
- 不用 public LB 直接拟合权重。

### 4.2 Residual blend

更推荐：

```text
final = baseline + blend(residual_geometry)
```

优点：

- baseline 主趋势不被稀释；
- residual 更容易 clip；
- 便于后处理。

### 4.3 按井路由 blend

按 well quality 调整权重：

```text
if GR_quality_low:
    reduce geometry weight
if hidden_interval_long:
    reduce aggressive residual
if baseline_confidence_high:
    keep conservative
if model_disagreement_high:
    fallback toward baseline
```

这里的 fallback 不是把 baseline 重新当成独立提交，而是把 gate 收紧，让最终输出更接近 baseline。

### 4.4 Meta model blend

后期可训练一个小模型预测 blend weights。

输入：

- baseline confidence；
- GR quality；
- alignment confidence；
- hidden interval length；
- model disagreement；
- well-level features。

风险：

- 容易过拟合；
- 必须用 OOF 训练；
- 只能在 CV 很稳后使用。

### 4.5 Ensemble 验收指标

ensemble 不是只要 overall 更低就通过。必须同时看：

- overall RMSE；
- mean well RMSE；
- P95/P99 absolute error；
- worst 20 wells；
- model disagreement high subset；
- long hidden interval subset；
- GR missing high subset。

如果 overall 降低但 P99 或 worst wells 爆炸，只能作为 aggressive，不可作为 balanced。

## 5. 三类提交设计

### 5.1 Conservative

目的：

- 保底；
- 防 private leaderboard 崩；
- 最终选择时可作为稳定候选。

组成：

```text
baseline + small geometry residual
```

约束：

- 强 clip；
- 强 fallback；
- 不使用低 confidence alignment。

### 5.2 Balanced

目的：

- 主力提交；
- 在稳健和提升之间平衡。

组成：

```text
baseline + weighted(geometry residual)
```

约束：

- 中等 clip；
- 按质量路由；
- 保留平滑。

### 5.3 Aggressive

目的：

- 冲高分；
- 利用 typewell alignment 和更大 residual correction。

组成：

```text
baseline + stronger residual
```

约束：

- 只在 confidence 高时启用；
- 对不可信井回退 balanced；
- 记录高风险 wells。

## 6. 后处理约束

### 6.1 约束目标

模型输出必须像一个可信的 TVT 曲线，而不是逐行噪声。

### 6.2 Residual clip

按 CV 统计设置：

```text
clip residual to p1/p99
or clip by well-level residual limit
```

可选：

```text
clip_strength = conservative / balanced / aggressive
```

### 6.3 Slope constraint

检查：

```text
dTVT/dMD
```

约束：

- 超出训练分布 P0.5/P99.5 的局部斜率需要修正；
- 对连续异常区间进行平滑；
- 不硬性强制全局单调，避免抹掉真实地质变化。

### 6.4 Smooth residual, not baseline

原则：

```text
final = baseline + smooth(residual)
```

不要直接强平滑 final curve，因为 baseline 本身包含主要趋势。

平滑方法：

- rolling median；
- rolling mean；
- Savitzky-Golay；
- spline smoothing。

### 6.5 Disagreement fallback

如果模型间分歧大：

```text
disagreement = std(pred_model_i)
```

策略：

- high disagreement -> 更接近 baseline；
- low disagreement -> 允许 residual；
- typewell high confidence 可例外。

### 6.6 Postprocess A/B 测试

所有后处理必须和 no-postprocess 版本对比：

- before/after overall；
- before/after P95；
- before/after worst wells；
- curve jump count；
- 平滑是否降低真实地层变化处的准确性。

后处理如果只让曲线看起来平滑但 CV 变差，不采用。

## 7. Kaggle Notebook 工程化

### 7.1 Notebook 文件

```text
notebooks/rogii_submission_pipeline.ipynb
```

本仓库当前是“本地脚本 + notebook 骨架”双轨：脚本负责真实落盘，notebook 作为 Kaggle 复现入口。

### 7.2 Notebook 结构

```text
1. Config
2. Imports
3. Path detection
4. Schema checks
5. Load sample submission
6. Build baseline
7. Build features
8. Load or train models
9. Predict residuals
10. Blend
11. Postprocess
12. Write submission.csv
13. Print diagnostics
```

### 7.3 环境约束

- Internet disabled；
- 不依赖本地绝对路径；
- 不读取 git ignored 本地模型，除非 Kaggle dataset 中包含；
- 训练时间可控；
- 输出只有 `submission.csv` 和必要诊断。

### 7.4 模型部署选择

选项 A：Notebook 内训练

- 优点：简单，不需要额外 dataset；
- 缺点：时间压力。

选项 B：预训练模型作为 Kaggle dataset

- 优点：提交快；
- 缺点：管理复杂，需要上传模型文件。

初期建议 A，后期可转 B。

### 7.5 Code Competition 风险控制

如果使用预训练模型作为 Kaggle dataset，必须确认比赛规则允许该形式，并记录：

- 预训练数据只来自本比赛训练集和允许外部数据；
- 模型文件版本；
- 生成模型的 notebook/script；
- 上传 dataset 的版本。

在规则不确定或时间允许时，优先使用 Notebook 内训练，减少合规风险。

### 7.6 Submission 文件 QA

提交前必须自动检查：

```text
columns exactly: id,tvt
row count equals sample_submission
id order equals sample_submission
no NaN / inf
tvt dtype numeric
no duplicated id
prediction summary printed
```

检查失败不得提交。

## 8. Submission Log

### 8.1 文件

```text
reports/submission_log.md
```

### 8.2 每次提交记录

```text
submission_id:
date:
variant: conservative / balanced / aggressive
local_cv:
public_lb:
private_lb_if_available:
features:
models:
postprocess:
hypothesis:
expected_gain:
risk:
result:
decision:
next_action:
```

### 8.3 提交命名

```text
v001_baseline_tail_slope
v002_geometry_residual_balanced
v003_gr_residual_balanced
v004_typewell_aggressive
v005_ensemble_conservative
```

## 9. Public / Private Gap 管理

### 9.1 如果 local CV 好但 public LB 差

检查：

- CV mask 是否不匹配 hidden；
- visible/public 是否更偏短区间；
- GR 缺失分布是否不同；
- typewell alignment 是否过拟合；
- postprocess 是否过强。

行动：

- 不立即推翻模型；
- 提交 conservative variant；
- 对 mask 分布加权重；
- 增加 public-like split。

### 9.2 如果 public LB 好但 local CV 一般

风险：

- 可能 public 过拟合；
- private 会掉。

行动：

- 保留为 aggressive；
- 不作为唯一最终选择；
- 与 conservative/balanced 分散。

### 9.3 最终阶段选择

最终保留：

- 一个 conservative；
- 一个 balanced；
- 一个 aggressive。

如果规则允许多次最终提交，按 public/private 风险选择组合。

### 9.4 提交预算

每天提交次数有限时：

- 不提交无本地 CV 的实验；
- 同一天提交要覆盖不同风险类型，而不是同类微调；
- 优先提交 conservative/balanced/aggressive 中差异最大的版本；
- 留出最后阶段提交名额。

## 10. 报告与模型卡

最终模型必须有：

```text
reports/final_model_card.md
```

内容：

- 数据版本；
- CV 设计；
- baseline 分数；
- 模型组成；
- 特征清单；
- 后处理；
- leaderboard 结果；
- 已知风险；
- 复现命令。

## 11. 本阶段完成标准

Part 4 完成必须满足：

- 至少 2 个模型成员有 OOF；
- ensemble / postprocess 能稳定生成三类 submission；
- `submission.csv` 自动 QA 通过；
- Kaggle notebook 有可执行骨架；
- submission log 建立；
- 有 public/private gap 分析策略。

## 12. 工程复现演练

最终提交前必须做一次从零演练：

```text
clean workspace
  -> install requirements
  -> download or place data
  -> run EDA
  -> run baseline CV
  -> build features
  -> train models
  -> ensemble
  -> postprocess
  -> generate submission
  -> verify submission
```

演练通过后，记录命令和耗时到 `reports/final_model_card.md`。

## 13. 冲第一工作法

每天循环：

```text
new hypothesis
  -> local CV
  -> failure analysis
  -> generate variant
  -> submit if justified
  -> record LB
  -> compare gap
  -> update plan
```

严格避免：

- 无 hypothesis 提交；
- 看 public LB 盲调；
- 删除失败实验记录；
- 只追 overall，不看 tail risk。

最终冲第一靠的是：

```text
可信 CV
  + 地质信号
  + 稳健 ensemble
  + 风险分散提交
  + 复盘闭环
```
