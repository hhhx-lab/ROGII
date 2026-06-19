# ROGII 地质勘测预测冲榜工程计划

## 0. 总目标

本项目的目标不是做一个能跑通的 Kaggle baseline，而是做一个真正可实现、可验证、可解释、可持续迭代的 **水平井地质位置 TVT 预测工程系统**，并以此为基础冲击 leaderboard 第一名。

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

- 可从原始 Kaggle 数据开始运行；
- 可生成 EDA 报告、CV 报告、failure analysis；
- 可训练多个模型版本；
- 可输出 conservative / balanced / aggressive 三类提交；
- 可解释每次提交为什么可能提升，以及在哪里可能失败。

## 四个子计划

总计划拆成四个可逐步实现的子计划：

| 阶段 | 子计划 | 目标 |
|---|---|---|
| Part 1 | [`plans/01_validation_baseline.md`](plans/01_validation_baseline.md) | 建立数据契约、CV 框架和可信 baseline |
| Part 2 | [`plans/02_residual_modeling.md`](plans/02_residual_modeling.md) | 建立 baseline + residual 主干模型 |
| Part 3 | [`plans/03_gr_typewell_alignment.md`](plans/03_gr_typewell_alignment.md) | 加入 GR 和 typewell 对齐地质信号 |
| Part 4 | [`plans/04_ensemble_submission_ops.md`](plans/04_ensemble_submission_ops.md) | 集成、后处理、Notebook 工程化和冲榜运营 |

## 1. 方法总判断

### 1.1 为什么不直接黑盒预测 TVT

直接用 tabular model 预测绝对 `TVT` 风险很高：

- 不同井的绝对深度、轨迹、构造背景不同；
- hidden wells 与 public visible test 的 3 口井不一致；
- 模型可能记住训练井尺度和深度分布，而不是学地质规律；
- 直接预测容易产生不连续、不合理的曲线。

### 1.2 为什么采用 baseline + residual

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

### 1.3 冲第一的核心矛盾

单纯外推很稳，但遇到地层变化、断层、GR 形态变化时会弱。

冲第一的关键不是把模型做复杂，而是解决：

- hidden interval 里地层是否发生偏移；
- 水平井 GR 和 typewell GR 如何对齐；
- residual 修正什么时候可信；
- 什么时候应该保守回退到 baseline；
- local CV 与 Kaggle hidden set 是否一致。

## 2. 项目约束与原则

### 2.1 工程约束

- 最终 Kaggle 提交必须在 Notebook 环境运行；
- 提交环境关闭 internet；
- CPU/GPU 运行时间均不超过 9 小时；
- 输出文件必须为 `submission.csv`；
- 原始数据不进 git；
- 代码必须能从 `data/raw/` 开始复现。

### 2.2 防过拟合原则

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

## 3. 数据理解与数据契约

### 3.1 原始数据结构

当前解压目录：

```text
data/raw/
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

### 3.2 horizontal well 数据契约

训练 horizontal 文件包含：

- `MD`: measured depth；
- `X`, `Y`, `Z`: 井轨迹坐标；
- `ANCC`, `ASTNU`, `ASTNL`, `EGFDU`, `EGFDL`, `BUDA`: 地层面预测深度，训练可见；
- `TVT`: 训练真值；
- `GR`: Gamma Ray；
- `TVT_input`: 已知目标输入，隐藏区间为 NaN。

测试 horizontal 文件包含：

- `MD`, `X`, `Y`, `Z`, `GR`, `TVT_input`。

### 3.3 typewell 数据契约

typewell 文件包含：

- `TVT`: vertical depth index；
- `GR`: 垂直参考 Gamma Ray；
- `Geology`: 地层标签。

### 3.4 submission 契约

```text
id,tvt
000d7d20_1442,11747.38
...
```

`id` 格式：

```text
{well}_{row_index}
```

## 4. 验证体系设计

验证体系是冲榜核心。没有可信 CV，就会变成猜 leaderboard。

### 4.1 CV Level 1: 原始训练隐藏段验证

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

产物：

- `scripts/evaluate_baseline_cv.py`
- `outputs/baseline_cv_by_well.csv`
- `reports/baseline_cv_report.md`

### 4.2 CV Level 2: 多 mask 验证

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

产物：

- `scripts/make_cv_splits.py`
- `outputs/cv_splits.parquet`
- `reports/cv_design.md`

### 4.3 CV Level 3: Group / Fold 验证

为了评估跨井泛化：

- 按 well 分组；
- 不让同一口井同时出现在 train 和 validation；
- 使用 5-fold 或 repeated group split；
- 同时保留 train-hidden-row validation。

注意：

Residual 模型训练时可以使用一口井已知段的信息生成 baseline 和特征，但不能偷看该井隐藏段真值。

### 4.4 指标体系

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

## 5. Phase 1: Continuity Baseline

### 5.1 目标

建立稳定、可解释、可提交的控制组。

### 5.2 方法

对每口井：

1. 找到 `TVT_input` 已知行；
2. 在 `MD` 方向拟合局部趋势；
3. 用尾段 `dTVT/dMD` 中位数外推隐藏区间；
4. 对左右越界做边界外推；
5. 生成 `id,tvt`。

baseline 版本：

| 版本 | 方法 |
|---|---|
| B0 | last known TVT constant |
| B1 | global MD-TVT linear fit per well |
| B2 | tail slope median |
| B3 | robust local polynomial |
| B4 | monotonic constrained smoothing |

当前已有：

- `scripts/baseline_tail_slope.py`
- `submissions/baseline_tail_slope_submission.csv`
- `reports/baseline_report.md`

### 5.3 验收标准

- submission 无 NaN；
- CV 覆盖 773 口井；
- 产出 worst wells；
- 作为后续模型最低门槛。

## 6. Phase 2: Geometry Residual Model

### 6.1 目标

在 baseline 上学习几何和轨迹带来的偏移。

目标变量：

```text
residual = TVT - baseline_TVT
```

### 6.2 特征设计

基础行特征：

- `MD`, `X`, `Y`, `Z`
- row index；
- normalized row position；
- distance from last known TVT；
- distance from first hidden row；
- hidden interval length。

轨迹特征：

- `dX/dMD`, `dY/dMD`, `dZ/dMD`；
- inclination proxy；
- curvature proxy；
- local `Z` slope；
- rolling mean/std of `Z`；
- cumulative horizontal displacement；
- distance to kickoff-like changes。

baseline 特征：

- baseline TVT；
- baseline slope；
- slope stability；
- local extrapolation distance；
- baseline confidence score。

well-level 特征：

- row count；
- known rows；
- hidden rows；
- MD span；
- GR missing rate；
- known TVT slope mean/std；
- known TVT curvature。

### 6.3 模型

第一版优先：

- `HistGradientBoostingRegressor`
- `RandomForestRegressor` 作为参考

后续可加：

- LightGBM；
- XGBoost；
- CatBoost。

### 6.4 防过拟合

- group split by well；
- mask split by interval；
- residual clipping；
- early stopping；
- 不使用训练-only 地层面列去做最终 test 模型，除非有可迁移替代特征。

### 6.5 验收标准

必须同时满足：

- overall RMSE 低于 baseline；
- P95 absolute error 低于 baseline；
- worst 20 wells 不显著恶化；
- public test 3 口井 sanity 不异常；
- 曲线无明显不合理跳变。

## 7. Phase 3: GR Residual Model

### 7.1 目标

引入岩性响应信号，解决单纯外推在地层变化处弱的问题。

### 7.2 GR 特征

原始特征：

- `GR`
- `GR_is_missing`
- filled GR；
- GR local rank。

滚动特征：

- rolling mean；
- rolling std；
- rolling min/max；
- rolling gradient；
- rolling z-score；
- known segment end GR；
- hidden segment GR drift。

形态特征：

- peak/trough count；
- GR volatility；
- GR trend direction；
- GR correlation with known tail。

缺失特征：

- missing run length；
- missing rate in hidden interval；
- distance to nearest valid GR；
- missing pattern type。

### 7.3 模型策略

训练两个版本：

- geometry residual；
- geometry + GR residual。

比较：

- GR 完整井；
- GR 缺失严重井；
- high baseline error wells；
- formation-like transition wells。

### 7.4 风险

GR 缺失多，不能让模型过度依赖 GR。

处理：

- 所有 GR 特征必须配 missing flag；
- 对缺失井启用 fallback；
- ensemble 中按 GR quality 调权。

## 8. Phase 4: Typewell / GR 对齐

这是最可能带来大提升的地质信号。

### 8.1 目标

用 typewell 的垂直 GR 和 Geology 信息，帮助判断水平井 hidden interval 的真实 TVT 是否偏离 baseline。

### 8.2 简单对齐版本

对每个预测点：

1. 用 baseline TVT 找到 typewell 附近窗口；
2. 提取 typewell GR 局部统计；
3. 提取 typewell Geology label；
4. 比较 horizontal GR 与 typewell GR 的局部形态；
5. 生成 similarity features。

特征：

- typewell GR at baseline TVT；
- typewell GR rolling mean/std；
- nearby Geology label；
- label change distance；
- horizontal-typewell GR difference；
- local correlation；
- candidate TVT offset with best GR match。

### 8.3 滑窗相关版本

在 baseline TVT 附近搜索候选 offset：

```text
candidate_tvt = baseline_tvt + offset
offset in [-window, +window]
```

对每个 offset：

- 取 typewell GR window；
- 与 horizontal GR window 做 correlation / MAE；
- 选择 best offset；
- 将 best offset 作为 residual feature 或 direct correction。

### 8.4 DTW 版本

若滑窗相关有效，再尝试 dynamic time warping：

- 对 GR 曲线做平滑和标准化；
- 在候选 TVT 范围内做局部 DTW；
- 生成 alignment cost；
- 只在 GR 质量足够时启用。

### 8.5 Geology 约束

利用 `Geology` label：

- 当前 candidate TVT 属于哪个 formation；
- 预测段是否跨 formation boundary；
- 距离上/下 boundary 的距离；
- 是否进入风险地层。

### 8.6 验收标准

typewell 模块必须：

- 降低 high baseline error wells；
- 降低 worst 20 wells tail；
- 在 GR 缺失严重井上不会恶化；
- 对 leaderboard 有正向反馈。

## 9. Phase 5: 模型集成

### 9.1 为什么需要集成

不同模型擅长不同场景：

- baseline 稳；
- geometry residual 处理轨迹偏移；
- GR residual 处理岩性响应；
- typewell residual 处理层位对齐；
- aggressive 模型可能在困难井更强但更不稳定。

### 9.2 候选模型池

| 模型 | 角色 |
|---|---|
| B2 tail slope baseline | control / fallback |
| Geometry HGB residual | first ML mainline |
| GR HGB residual | petrophysical signal |
| Typewell alignment residual | geology alignment |
| LightGBM residual | stronger tabular model |
| Sequence residual | late-stage experiment |

### 9.3 Blend 方式

固定权重：

```text
pred = w0 * baseline + w1 * geometry + w2 * gr + w3 * typewell
```

按井路由：

- GR missing high -> baseline/geometry 权重大；
- typewell similarity high -> typewell 权重大；
- hidden interval long -> conservative residual；
- baseline confidence low -> ensemble 分散风险。

按误差桶路由：

- baseline CV error low bucket -> 少修正；
- baseline CV error high bucket -> 多用 residual/typewell。

### 9.4 三类提交

| 提交类型 | 作用 |
|---|---|
| Conservative | 稳定保底，少残差 |
| Balanced | 主力，baseline + geometry + GR |
| Aggressive | 冲高，typewell + ensemble + stronger correction |

## 10. Phase 6: 后处理约束

### 10.1 目标

避免模型输出工程上不可信的曲线。

### 10.2 约束类型

连续性约束：

- 限制单步 TVT jump；
- 限制 `dTVT/dMD` 极端值；
- 限制 residual 高频震荡。

平滑策略：

- 只平滑 residual，不强行平滑 baseline；
- 使用 rolling median / Savitzky-Golay；
- 对长区间使用渐进置信度衰减。

回退策略：

- residual 过大 -> clip；
- typewell similarity 低 -> 降权；
- GR 缺失严重 -> 回退 geometry/baseline；
- 模型 disagreement 大 -> conservative blend。

### 10.3 验收标准

后处理必须：

- 降低 P95/max error；
- 不牺牲 overall RMSE；
- 不抹掉真实地层变化；
- 有清晰的 before/after 报告。

## 11. Phase 7: Kaggle Notebook 工程化

### 11.1 Notebook 结构

```text
1. imports and config
2. load train/test/sample_submission
3. schema checks
4. build baseline
5. load/train residual models
6. build features for hidden rows
7. predict conservative/balanced/aggressive
8. postprocess
9. write submission.csv
10. print diagnostics
```

### 11.2 Kaggle 环境策略

- internet disabled；
- 尽量使用 Kaggle 默认可用库；
- 若使用 LightGBM/XGBoost，提前确认 Notebook 环境；
- 模型训练时间必须可控；
- 对大型中间文件谨慎缓存。

### 11.3 可复现要求

- 固定 random seed；
- 所有路径相对 `/kaggle/input`；
- 输出只写 `submission.csv`；
- notebook 日志打印关键诊断；
- 本地脚本与 Kaggle notebook 逻辑一致。

## 12. Leaderboard 运营

### 12.1 提交记录表

每次提交必须记录：

| 字段 | 内容 |
|---|---|
| submission_id | 自定义版本号 |
| date | 日期 |
| model | 模型组合 |
| local_cv | 本地 CV |
| public_lb | public leaderboard |
| hypothesis | 本次为什么可能提升 |
| change | 相对上次改了什么 |
| risk | 可能哪里过拟合 |
| decision | keep / discard / investigate |

产物：

- `reports/submission_log.md`

### 12.2 提交节奏

早期：

- baseline；
- geometry residual；
- GR residual；
- typewell simple alignment。

中期：

- 多 mask CV；
- first ensemble；
- postprocess variants。

后期：

- conservative / balanced / aggressive 三路线；
- public/private gap 分析；
- 排名前几日降低高风险实验；
- 最终选择稳定高分模型。

### 12.3 public/private gap 防御

如果 public LB 与 local CV 不一致：

1. 检查 public test 是否偏向短/长 hidden interval；
2. 检查 GR missing pattern；
3. 检查 baseline vs residual 哪个更接近 LB；
4. 不立即大幅调参；
5. 用三类提交保持风险分散。

## 13. 产物清单

### 13.1 已有产物

- `scripts/download_data.py`
- `scripts/run_eda.py`
- `scripts/baseline_tail_slope.py`
- `scripts/evaluate_baseline_cv.py`
- `reports/eda_summary.md`
- `reports/baseline_report.md`
- `reports/modeling_plan.md`
- `reports/engineering_methodology.md`
- `reports/leaderboard_strategy.md`
- `submissions/baseline_tail_slope_submission.csv`

### 13.2 待建脚本

| 脚本 | 作用 |
|---|---|
| `scripts/make_cv_splits.py` | 多 mask CV |
| `scripts/build_baseline_features.py` | baseline 与距离特征 |
| `scripts/build_geometry_features.py` | 轨迹几何特征 |
| `scripts/build_gr_features.py` | GR 特征 |
| `scripts/build_typewell_features.py` | typewell/GR 对齐特征 |
| `scripts/train_residual_model.py` | 训练 residual |
| `scripts/evaluate_model_cv.py` | 模型 CV |
| `scripts/blend_predictions.py` | 集成 |
| `scripts/postprocess_predictions.py` | 后处理 |
| `scripts/make_submission.py` | 统一生成提交 |

### 13.3 待建报告

| 报告 | 作用 |
|---|---|
| `reports/cv_design.md` | 验证设计 |
| `reports/baseline_cv_report.md` | baseline 全训练井 CV |
| `reports/feature_report.md` | 特征有效性 |
| `reports/model_cv_report.md` | 模型效果 |
| `reports/failure_cases.md` | 失败井分析 |
| `reports/submission_log.md` | 提交记录 |
| `reports/final_model_card.md` | 最终模型说明 |

## 14. 阶段里程碑

### Milestone 1: 可信 baseline

目标：

- 数据已解压；
- EDA 完成；
- baseline submission 完成；
- 773 井 baseline CV 完成。

完成标准：

- 有 baseline CV report；
- 知道 worst wells；
- 知道 baseline 主要失败类型。

### Milestone 2: Geometry residual

目标：

- 完成 geometry feature；
- 训练 residual model；
- 多 mask CV 超过 baseline。

完成标准：

- overall RMSE 降低；
- P95 error 降低；
- worst wells 不恶化。

### Milestone 3: GR residual

目标：

- 加入 GR rolling/missing features；
- 分析 GR 完整井 vs 缺失井；
- 改善地层变化井。

完成标准：

- high baseline error wells 改善；
- GR 缺失严重井有 fallback。

### Milestone 4: Typewell alignment

目标：

- typewell GR 简单滑窗对齐；
- Geology label 特征；
- typewell residual model。

完成标准：

- worst 20 wells tail 明显下降；
- local CV 和 LB 同向提升。

### Milestone 5: Ensemble + postprocess

目标：

- 三类提交；
- 曲线约束；
- 提交日志闭环。

完成标准：

- conservative 稳；
- balanced 主力；
- aggressive 有冲高能力；
- 不因单次 public LB 波动失控。

## 15. 优先级排序

现在最该做：

1. 跑完 `evaluate_baseline_cv.py`，拿到 773 井 baseline 控制分；
2. 建 `make_cv_splits.py`，补多 mask；
3. 建 geometry feature；
4. 训练第一版 residual；
5. 才开始 GR/typewell。

不要现在就做：

- 深度学习；
- 大规模 stacking；
- 手动根据 public 3 井调参；
- 复杂但无法解释的特征。

## 16. 第一周执行计划

Day 1:

- baseline CV 跑通；
- 输出 worst wells；
- 明确 baseline 失败类型。

Day 2:

- 多 mask split；
- 验证不同 mask 下 baseline 稳定性。

Day 3:

- geometry features；
- 第一版 residual model。

Day 4:

- residual CV；
- failure analysis；
- 生成 first balanced submission。

Day 5:

- GR features；
- 对比 geometry vs geometry+GR。

Day 6:

- typewell simple alignment；
- 形成第一个 aggressive submission。

Day 7:

- ensemble；
- postprocess；
- leaderboard 反馈复盘。

## 17. 最终判断标准

一个方法只有满足以下条件，才进入主线：

- 在真实训练隐藏段 CV 上超过 baseline；
- 在多 mask CV 上不过拟合；
- 对 worst wells 有改善；
- 输出曲线工程上合理；
- Kaggle notebook 可复现；
- leaderboard 反馈与本地验证大体一致；
- 能解释为什么提升。

最终冲第一不是靠单个模型，而是靠完整系统：

```text
可信验证
  + 强 baseline
  + residual learning
  + GR/typewell 地质信号
  + ensemble 风险控制
  + 后处理工程约束
  + submission 运营闭环
```
