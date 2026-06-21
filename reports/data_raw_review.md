# Data Raw Review: PPTX, Sample Submission, Train/Test Schema

更新时间：2026-06-20

## 1. 检查范围

本次直接检查本地解压后的 `data/raw/`：

```text
data/raw/
|-- AI_wellbore_geology_prediction_task_en.pptx
|-- sample_submission.csv
|-- train/
`-- test/
```

检查目的不是重新做 EDA，而是核对原始数据和 PPTX 说明是否会改变现有建模计划。

## 2. PPTX 关键信息

PPTX 共 14 页。对建模有直接影响的内容如下：

1. 每口井有 horizontal well CSV 和 typewell CSV。
2. `TVT` 是需要预测的地质目标，训练集提供完整 `TVT`，测试集只给 `TVT_input` 的已知段。
3. horizontal well 提供 `MD/X/Y/Z/GR/TVT_input`；训练集额外提供 formation top depth 和完整 `TVT`。
4. typewell 提供垂直参考 `TVT` 与 `GR`，训练 typewell 还提供 `Geology` label。
5. 预测目标是 PS（Prediction Start）之后的 TVT；PS 之前的 `TVT_input` 已知，PS 之后为空。
6. 不能只做几何外推。PPTX 明确强调要用 horizontal GR 与 typewell GR 的形态对应来判断 TVT 增减、变平或偏移。
7. PPTX 特别提示：horizontal well 的 GR 可能比 typewell 更有分辨率，PS 前 horizontal GR 与 PS 后 horizontal GR 的自相关可能比直接匹配 typewell 更强。
8. offset wells、钻井方位、地层倾角会影响预期 TVT 变化，邻井地质趋势可能提供额外先验。
9. 评分是预测点逐行 `manualTVT - predictedTVT` 的 RMSE。

## 3. 文件数量与完整性

| 项目 | 数量 |
|---|---:|
| train horizontal CSV | 773 |
| train typewell CSV | 773 |
| train PNG | 773 |
| test horizontal CSV | 3 |
| test typewell CSV | 3 |
| test PNG | 0 |
| sample submission rows | 14,151 |

完整性结论：

- 773 口训练井全部具备 horizontal、typewell、PNG。
- 3 口 visible test 全部具备 horizontal、typewell。
- visible test 的 3 个 well ID 均同时存在于 train 中：`000d7d20`、`00bbac68`、`00e12e8b`。

因此 visible test 只能用于提交格式、脚本可运行性和 sanity check，不能当作独立验证集或调参依据。

## 4. Sample Submission 结构

`sample_submission.csv` 只有两列：

```text
id,tvt
```

其中 `id = {well}_{row_index}`。三口 visible test 的目标段如下：

| well | target rows | first target row | last target row | target 是否到井尾 | train 中是否有真值 |
|---|---:|---:|---:|---|---|
| `000d7d20` | 3,836 | 1,442 | 5,277 | 是 | 是 |
| `00bbac68` | 6,014 | 1,545 | 7,558 | 是 | 是 |
| `00e12e8b` | 4,301 | 2,083 | 6,383 | 是 | 是 |

visible test horizontal 文件在 target rows 中：

- `TVT_input` 全部为空；
- 不含 `TVT` 真值列；
- 提供 `MD/X/Y/Z/GR`。

## 5. Train/Test Schema 差异

### 5.1 Horizontal Well

训练 horizontal 固定列：

```text
MD, X, Y, Z, ANCC, ASTNU, ASTNL, EGFDU, EGFDL, BUDA, TVT, GR, TVT_input
```

测试 horizontal 固定列：

```text
MD, X, Y, Z, GR, TVT_input
```

关键结论：

- `ANCC/ASTNU/ASTNL/EGFDU/EGFDL/BUDA` 是训练-only formation surface/top depth 信息。
- 这些列不能作为 leaderboard 最终模型的直接输入特征。
- 它们可以用于训练集诊断、mask 分层、failure analysis、辅助理解地层变化，但所有 final test 特征必须在缺少这些列时可运行。

### 5.2 Typewell

训练 typewell 固定列：

```text
TVT, GR, Geology
```

visible test typewell 固定列：

```text
TVT, GR
```

关键结论：

- `TVT/GR` 是 typewell 对齐的稳定可用信息。
- `Geology` 在训练 typewell 中可用，但 visible test typewell 没有。
- 因此 Geology 只能作为训练诊断、CV 分层、可选特征；leaderboard pipeline 不能要求 test typewell 必须有 Geology。
- 如果 Kaggle hidden rerun 的 test typewell 仍然没有 Geology，模型必须自动禁用 Geology 相关特征并保留 `geology_available=0`。

## 6. TVT_input / PS 模式

773 口训练井全部满足：

- `TVT_input` 已知段是井开头到 PS 前；
- `TVT_input` 缺失段是从 PS 到井尾的单一尾段；
- 已知段 `TVT_input` 与训练真值 `TVT` 完全一致；
- 缺失段仍有 `TVT` 真值可用于 CV。

训练集隐藏段统计：

| 指标 | 数值 |
|---|---:|
| train wells | 773 |
| single-tail target wells | 773 |
| target rows min / median / max | 407 / 4,840 / 10,052 |
| known rows min / median / max | 851 / 1,703 / 2,392 |
| target ratio min / q25 / median / q75 / max | 0.1978 / 0.7003 / 0.7400 / 0.7755 / 0.8752 |
| target GR missing q0 / q25 / q50 / q75 / q90 / max | 0.0067 / 0.1308 / 0.3029 / 0.4977 / 0.5946 / 0.8118 |
| target GR fully missing wells | 0 |

结论：

- 官方任务形态高度接近 train 原始隐藏尾段，不是随机中间挖空。
- `original_hidden`、`trailing_short`、`trailing_long` 应作为主验证权重。
- `mid_contiguous`、`random_contiguous` 仍然有价值，但定位是防过拟合压力测试，不应覆盖官方尾段验证的优先级。

## 7. 对现有 Plan 的影响

### 7.1 保持不变

- `baseline + residual` 主路线仍然正确。
- `B0_constant_last` 作为 conservative baseline 仍然合理。
- 多 mask 验证仍然需要，用于避免只适配一种缺失长度、起点和 GR 缺失形态。
- GR/typewell 对齐仍然是最可能带来大提升的地质信号。

### 7.2 必须修改

1. Typewell `Geology` 不能作为 test 必需字段。
   - Part 1 数据契约应写成：train typewell 必须有 `TVT/GR/Geology`，test typewell 必须有 `TVT/GR`，`Geology` optional。
   - Part 3 所有 Geology 特征必须带 `geology_available` flag，并有无 Geology 的 fallback。

2. Visible test 不能用于独立验证或调参。
   - 3 口 visible test 与 train 重合，train 中有真值。
   - 可用于格式 sanity、notebook 输出检查、兼容性检查。
   - 不可根据这 3 口井手调 offset、blend 权重或后处理。

3. 官方结构是 PS 后尾段预测。
   - 主 CV 排序应优先看 `original_hidden`、`trailing_short`、`trailing_long`。
   - 中间 mask 和随机 mask 作为鲁棒性检查，而不是主 leaderboard proxy。

4. Part 3 需要加入 horizontal self-GR alignment。
   - PPTX 明确提示 PS 前 horizontal GR 可能比 typewell 更能解释 PS 后 horizontal GR。
   - 应先做“PS 前水平井 GR 模板 / motif / shape matching”，再做 typewell 对齐或与 typewell 对齐并行。

5. Offset well / dip prior 应作为后续增强候选。
   - 训练和测试都有 `X/Y/Z/MD`，训练还有 formation surfaces。
   - 可在 CV 中构造邻井空间先验、方位/倾角 proxy，但必须避免直接使用训练-only formation surfaces 推 test。

## 8. 更新建议

已确认需要同步修改：

- `docs/plans/00_overview.md`
- `docs/plans/01_validation_baseline.md`
- `docs/plans/03_gr_typewell_alignment.md`

不需要推翻：

- Part 1 baseline 和验证体系；
- Part 2 residual 主干；
- Part 4 ensemble/postprocess 思路。

整体结论：计划方向是靠谱的，但要把 test schema 边界和 PPTX 中的 horizontal self-GR signal 写得更明确，避免后续模型误把训练-only 信息当成 leaderboard 特征。
