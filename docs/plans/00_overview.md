# ROGII 地质勘测预测总计划

## 0. 总目标

本项目的目标不是做一个能跑通的 Kaggle baseline，而是做一个真正可实现、可验证、可解释、可持续迭代的水平井地质位置 TVT 预测工程系统，并以此冲击 leaderboard 第一名。

核心任务：

> 给定水平井轨迹、已知段 `TVT_input`、Gamma Ray 日志、垂直 typewell 参考井和地层标签，预测隐藏区间每一行的 `tvt`。

核心路线：

```text
数据契约与质量检查
  -> 真实 hidden interval 验证体系
  -> TVT 连续性 baseline
  -> baseline + residual 主干
  -> GR 信号增强
  -> typewell / GR 对齐增强
  -> 多模型集成
  -> 地质约束后处理
  -> Kaggle notebook 提交系统
  -> leaderboard 反馈闭环
```

最终要交付的不只是一个 `submission.csv`，而是一套可复现的工程流水线：

- 可从 `data/raw/` 下的原始 Kaggle 数据开始运行；
- 可生成 EDA 报告、CV 报告、failure analysis；
- 可训练多个模型版本；
- 可输出 conservative / balanced / aggressive 三类提交；
- 可解释每次提交为什么可能提升，以及在哪里可能失败。

## 1. 四个子计划

| 阶段 | 子计划 | 目标 |
|---|---|---|
| Part 1 | [`01_validation_baseline.md`](01_validation_baseline.md) | 建立数据契约、CV 框架和可信 baseline |
| Part 2 | [`02_residual_modeling.md`](02_residual_modeling.md) | 建立 baseline + residual 主干模型 |
| Part 3 | [`03_gr_typewell_alignment.md`](03_gr_typewell_alignment.md) | 加入 GR 和 typewell 对齐地质信号 |
| Part 4 | [`04_ensemble_submission_ops.md`](04_ensemble_submission_ops.md) | 集成、后处理、Notebook 工程化和冲榜运营 |

## 2. 方法总判断

### 2.1 为什么不直接黑盒预测 TVT

直接用 tabular model 预测绝对 `TVT` 风险很高：

- 不同井的绝对深度、轨迹、构造背景不同；
- hidden wells 与 public visible test 的 3 口井不一致；
- 模型可能记住训练井尺度和深度分布，而不是学地质规律；
- 直接预测容易产生不连续、不合理的曲线。

### 2.2 为什么采用 baseline + residual

每口井都有已知段 `TVT_input`。这是最强的局部先验，表示该井当前地质位置的实际趋势。

因此主方法应为：

```text
prediction = continuity_baseline + learned_residual
```

其中：

- `continuity_baseline` 捕捉每口井自身 TVT 的连续趋势；
- `learned_residual` 学习外推失败的部分；
- GR/typewell/轨迹特征都用于解释 residual，而不是从零预测绝对 TVT。

工程优势：

- 稳定，baseline 可独立提交；
- 可解释，残差代表“地质偏移修正”；
- 防过拟合，模型只学 correction；
- 可分层增强，GR/typewell 可逐步加入；
- 可回退，复杂模型失效时仍可使用 baseline 或 conservative blend。

### 2.3 冲第一的核心矛盾

单纯外推很稳，但遇到地层变化、断层、GR 形态变化时会弱。

冲第一的关键不是把模型做复杂，而是解决：

- hidden interval 里地层是否发生偏移；
- 水平井 GR 和 typewell GR 如何对齐；
- residual 修正什么时候可信；
- 什么时候应该保守回退到 baseline；
- local CV 与 Kaggle hidden set 是否一致。

## 3. 项目约束与原则

### 3.1 工程约束

- 最终 Kaggle 提交必须在 Notebook 环境运行；
- 提交环境关闭 internet；
- CPU/GPU 运行时间均不超过 9 小时；
- 输出文件必须为 `submission.csv`；
- 原始数据不进 git；
- 代码必须能从 `data/raw/` 下的 `train/` 和 `test/` 开始复现。

### 3.2 防过拟合原则

严禁：

- 只根据 public visible test 的 3 口井判断方法好坏；
- 使用同一口井的信息泄漏到验证目标；
- 只看整体 RMSE，不看 worst wells；
- 模型只在少数简单井提升，却让困难井爆炸；
- 每次 leaderboard 失败后盲目调参。

必须：

- 建立训练井隐藏段 CV；
- 每个模型和 baseline 比；
- 记录每次提交的本地 CV、特征、假设、LB 结果；
- 使用 per-well metrics 和 failure analysis；
- 对模型输出做曲线稳定性检查。

## 4. 数据理解与数据契约

### 4.1 原始数据结构

当前数据目录：

```text
data/
`-- raw/
    |-- train/
    |-- test/
    |-- sample_submission.csv
    `-- AI_wellbore_geology_prediction_task_en.pptx
```

已确认：

- 训练井：773 口；
- 每口训练井包含：
  - `{well}__horizontal_well.csv`
  - `{well}__typewell.csv`
  - `{well}.png`
- visible test：3 口样例井；
- sample submission：14151 行；
- Kaggle hidden rerun 会替换 visible test。

### 4.2 horizontal well 数据契约

训练 horizontal 文件包含：

- `MD`, `X`, `Y`, `Z`
- `ANCC`, `ASTNU`, `ASTNL`, `EGFDU`, `EGFDL`, `BUDA`
- `TVT`, `GR`, `TVT_input`

测试 horizontal 文件包含：

- `MD`, `X`, `Y`, `Z`, `GR`, `TVT_input`

### 4.3 typewell 数据契约

typewell 文件包含：

- `TVT`
- `GR`
- `Geology` 仅训练集可见；测试集 typewell 只有 `TVT` 和 `GR`

### 4.4 submission 契约

```text
id,tvt
000d7d20_1442,11747.38
...
```

`id` 格式：

```text
{well}_{row_index}
```

## 5. 验证体系设计

验证体系是冲榜核心。没有可信 CV，就会变成猜 leaderboard。

### 5.1 CV Level 1: 原始训练隐藏段验证

训练井自身已经有：

- `TVT_input` 缺失段；
- 完整 `TVT` 真值。

因此第一层验证直接使用：

```text
target_rows = rows where TVT_input is NaN
truth = TVT[target_rows]
```

优点：

- 与 Kaggle 预测任务结构一致；
- 无需人工造 mask；
- 覆盖 773 口井；
- 是当前最重要的 baseline control。

### 5.2 CV Level 2: 多 mask 验证

hidden test 的缺失区间可能与训练默认缺失模式不同，所以需要多 mask。

mask 类型：

| Mask | 目的 |
|---|---|
| trailing-short | 模拟短隐藏尾段 |
| trailing-long | 模拟长隐藏尾段 |
| mid-section | 模拟中间缺失 |
| random-contiguous | 防止模型只适配尾段 |
| high-GR-missing | 测 GR 缺失鲁棒性 |
| formation-transition | 专门测地层变化处 |

每种 mask 要记录：

- well ID；
- mask 起点、终点；
- mask 长度；
- GR 缺失率；
- TVT slope/curvature；
- typewell Geology 覆盖；
- baseline RMSE；
- model RMSE。

补强原则：

- mask 后面的 `TVT_input` 不得被泄漏进特征；
- row-level RMSE 和 per-well RMSE 要同时看；
- 再加一个简单的 group split，把相邻井尽量分到不同 fold，避免邻井泄漏把 CV 抬高。

### 5.3 CV Level 3: Group / Fold 验证

为了评估跨井泛化：

- 按 well 分组；
- 不让同一口井同时出现在 train 和 validation；
- 使用 5-fold 或 repeated group split；
- 同时保留 train-hidden-row validation。

注意：

Residual 模型训练时可以使用一口井已知段的信息生成 baseline 和特征，但不能偷看该井隐藏段真值。

### 5.4 指标体系

不能只看 overall RMSE。

必须报告：

- overall RMSE；
- per-well RMSE mean/median/P95；
- worst 20 wells；
- RMSE by hidden length；
- RMSE by GR missing rate；
- RMSE by baseline error bucket；
- residual bias；
- max absolute error；
- 曲线跳变次数。

## 6. 四个阶段

### Part 1: Continuity Baseline

建立稳定、可解释、可提交的控制组。

方法：

1. 找到 `TVT_input` 已知行；
2. 在 `MD` 方向拟合局部趋势；
3. 用尾段 `dTVT/dMD` 中位数外推隐藏区间；
4. 对左右越界做边界外推；
5. 生成 `id,tvt`。

### Part 2: Geometry Residual Model

在 baseline 上学习几何和轨迹带来的偏移。

目标变量：

```text
residual = TVT - baseline_TVT
```

重点是让模型稳定修正 baseline 的系统性错误。

### Part 3: GR Residual Model

引入岩性响应信号，解决单纯外推在地层变化处弱的问题。

重点判断：

- GR 很差时只允许弱修正；
- GR 好且 baseline 误差大的井，才给 GR 更高优先级。

### Part 4: Typewell / GR 对齐

把水平井 GR 和垂直参考井 GR 对齐，识别层位偏移。

核心思想：

- 先用 baseline 给出一个“差不多对”的 TVT；
- 再去 typewell 里找最像的那一段；
- 如果像得很明显，就把这个偏移当成修正；
- 如果不像，就不要硬修，直接回退。

## 7. 项目状态说明

当前仓库已经具备：

- Part 1 的数据契约、baseline CV 和多 mask 设计；
- Part 2 的 residual 设计文档与服务器复跑手册；
- Part 3 的 GR / typewell 路线；
- Part 4 的集成、后处理与 Notebook 工程化框架。

但其中一部分 Part 2 的旧结果已经被主动清理，新的最终结果应以服务器 full-row 复跑后的产物为准。

