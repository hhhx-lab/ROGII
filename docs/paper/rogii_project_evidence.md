# ROGII 课程论文事实底稿

> 仅记录仓库报告、代码与官方资料中已经证实的事实；未确认内容一律保留为【待补】或【待填写】。文中数值尽量保留 3 位小数。

## 0. 封面待填写信息

- 论文题目：ROGII井筒地质预测中的残差校正与模型筛选
- 作者姓名：【待填写】
- 学号：【待填写】
- 小组成员：【待填写】；若确认为单人提交，则写“无”
- 日期：【待填写】

## 1. 题目来源与作业约束

### 1.1 官方来源

- Kaggle 竞赛概览页：<https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction/overview>
- Kaggle 数据页：<https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction/data>
- Kaggle 规则页：<https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction/rules>

### 1.2 课程要求对应

| 课程要求 | 仓库事实对应 |
|---|---|
| 选题必须来自公开竞赛平台正式赛题 | 选用 Kaggle 正式赛题 `ROGII - Wellbore Geology Prediction` |
| 论文采用小论文形式 | 采用中文课程论文结构：摘要、背景、数据、分析、结论、附录 |
| 至少比较两种课程方法 | 已有尾部外推基线、几何特征残差回归、树模型残差回归、学习型门控与集成候选 |
| 必须说明数据来源和网站 | 数据来源为 Kaggle 官方赛题页、数据页和规则页 |
| 必须展示预处理、描述统计、建模、参数选择与优化 | 已有数据契约、描述统计、交叉验证、候选筛选、后处理护栏等报告 |
| 不能用测试集调参 | 模型选择依据训练井上的 GroupKFold / 交叉验证预测 |
| 正文应尽量简洁 | 主要结果可放正文，详细报告与脚本放附录 |

### 1.3 论文术语映射

| 仓库代码名 / 术语 | 论文中的表述 |
|---|---|
| `baseline` | 基线模型 |
| `geometry` | 基于几何特征的残差回归模型 |
| `xgb` | 基于树模型的残差回归模型 |
| `learned_gated_geometry` | 学习型门控残差模型 |
| `gated_geometry` | 诊断上界（基于同井真值的上界分析） |
| `blend` | 集成候选模型 |
| `candidate selection` | 候选模型筛选 |
| `postprocess` | 后处理 |
| `visible test` | 公开可见测试集 |
| `OOF` | 交叉验证预测 |

## 2. 任务定义与数据结构

- 任务目标：根据水平井已知段 `TVT_input`、轨迹坐标与 `GR`，预测隐藏尾段的 `TVT`。
- 评价指标：RMSE。
- 提交格式：`id,tvt`，其中 `id = {well}_{row_index}`。
- 公开可见测试集中的 3 口井与训练井重合，因此它只能用于格式检查与一致性核验，不能作为独立验证集。
- 官方资料强调：水平井的隐藏段位于预测起点（PS）之后；水平井 GR 的形态延续、与 typewell GR 的对应关系以及井轨迹连续性都可能提供信息。

### 2.1 数据规模

| 项目 | 数值 |
|---|---:|
| 训练井 | 773 |
| 可见测试井 | 3 |
| 样例提交行数 | 14,151 |
| raw 文件总数 | 2,327 |
| 训练 horizontal 总行数 | 5,092,255 |
| 测试 horizontal 总行数 | 19,221 |
| 训练 hidden target 行数 | 3,783,989 |

补充说明：

- 每口训练井配有 horizontal CSV、typewell CSV 和 PNG 视觉图。
- 公开可见测试井配有 horizontal CSV 和 typewell CSV。
- 公开可见测试集的 3 个 well ID 与 train 重合：`000d7d20`、`00bbac68`、`00e12e8b`。

### 2.2 关键 schema

训练 horizontal：

```text
MD, X, Y, Z, ANCC, ASTNU, ASTNL, EGFDU, EGFDL, BUDA, TVT, GR, TVT_input
```

测试 horizontal：

```text
MD, X, Y, Z, GR, TVT_input
```

训练 typewell：

```text
TVT, GR, Geology
```

可见测试 typewell：

```text
TVT, GR
```

### 2.3 主要字段说明

| 字段 | 含义 / 作用 |
|---|---|
| `MD` | 测深或井深索引，用于表示沿井轨迹的采样位置 |
| `X`, `Y`, `Z` | 井轨迹空间坐标，用于描述轨迹几何形态 |
| `GR` | 自然伽马测井曲线，反映测井响应 |
| `TVT` | 预测目标，即真实 TVT 值 |
| `TVT_input` | 预测起点之前已知的 TVT 段；在隐藏尾段对应位置缺失 |
| `ANCC` | 训练-only 地层相关列；具体地质语义未在仓库报告中逐项确认 |
| `ASTNU` | 训练-only 地层相关列；具体地质语义未在仓库报告中逐项确认 |
| `ASTNL` | 训练-only 地层相关列；具体地质语义未在仓库报告中逐项确认 |
| `EGFDU` | 训练-only 地层相关列；具体地质语义未在仓库报告中逐项确认 |
| `EGFDL` | 训练-only 地层相关列；具体地质语义未在仓库报告中逐项确认 |
| `BUDA` | 训练-only 地层相关列；具体地质语义未在仓库报告中逐项确认 |
| `Geology` | typewell 训练标签；测试集中不存在 |

要点：

- `Geology` 仅在训练 typewell 中出现，不能写成测试必需输入。
- 训练 horizontal 中的 `ANCC`、`ASTNU`、`ASTNL`、`EGFDU`、`EGFDL`、`BUDA` 属于训练-only 信息，不能作为最终测试输入。
- 对证据不足的训练-only 地层列，正文中统一写作“训练-only 地层相关列”。

### 2.4 数据契约

- `reports/data_contract_report.md` 的 critical errors 为 `0`，warnings 为 `11`。
- `outputs/data_version.json` 已写出，用于记录当前数据版本。

`outputs/data_version.json` 中可直接引用的字段包括：

- `raw_file_count = 2327`
- `train_well_count = 773`
- `test_well_count = 3`
- `sample_submission_rows = 14151`

## 3. 数据分布与任务难点

### 3.1 描述统计

| 指标 | 数值 | 说明 |
|---|---:|---|
| 训练 horizontal 每井 rows mean / std / min / median / max | 6,587.650 / 1,311.460 / 2,058 / 6,576 / 12,141 | 原始水平井长度分布较宽 |
| 公开可见测试井 rows | 5,278 / 7,559 / 6,384 | 仅用于格式与一致性核验 |
| 公开可见测试井 target rows | 3,836 / 6,014 / 4,301 | 公开可见尾段长度 |
| 训练 horizontal GR missing rate | 29.610% | GR 缺失较多 |
| 训练 horizontal TVT_input missing rate | 74.310% | 与隐藏尾段对应 |
| 训练 horizontal ANCC missing rate | 0.900% | formation surface 列少量缺失 |
| 训练 horizontal EGFDL missing rate | 0.120% | formation surface 列少量缺失 |
| target rows min / median / max | 407 / 4,840 / 10,052 | 隐藏尾段长度跨度大 |
| known rows min / median / max | 851 / 1,703 / 2,392 | 已知段长度相对较短 |
| target ratio q25 / median / q75 | 0.7003 / 0.7400 / 0.7755 | 多数井隐藏尾段占比高 |
| target GR missing q0 / q25 / q50 / q75 / q90 / max | 0.0067 / 0.1308 / 0.3029 / 0.4977 / 0.5946 / 0.8118 | target 段 GR 缺失率分布 |

### 3.2 结构性难点

- 773 口训练井的隐藏区间均为单尾段，因此按井分组的交叉验证是合理的验证方式。
- 隐藏尾段越长，基线模型越容易失效；baseline 的平均误差随 target rows bucket 明显上升。
- typewell 的 `Geology` 标签分布极不均衡，最大类 `ANCC` 为 294,268，最小类 `EGFD200` 为 1。

### 3.3 基线难点分层

| target rows bucket | mean RMSE |
|---|---:|
| 0-2k | 9.709 |
| 2k-4k | 30.137 |
| 4k-6k | 57.833 |
| 6k-8k | 91.024 |
| 8k-12k | 122.556 |

## 4. 方法与实验设置

### 4.1 方法类别

| 方法 | 论文表述 | 说明 |
|---|---|---|
| `baseline` | 基线模型 | 尾部斜率外推，对照组 |
| `geometry` | 基于几何特征的残差回归模型 | 以 `truth_tvt - baseline_tvt` 为目标 |
| `xgb` | 基于树模型的残差回归模型 | 同样预测残差，再与基线相加 |
| `learned_gated_geometry` | 学习型门控残差模型 | 学习每口井的残差权重 |
| `gated_geometry` | 诊断上界 | 用同井真值搜索最佳权重，仅作上界分析 |
| `blend` | 集成候选模型 | 比较不同组合策略 |
| `candidate selection` | 候选模型筛选 | 在满足覆盖率约束的候选中选出最终提交候选 |
| `postprocess` | 后处理 | 仅在交叉验证不恶化时才保留 |

### 4.2 验证口径

- 所有可泛化候选均以训练井为单位做 GroupKFold。
- 交叉验证预测是模型选择的依据。
- 公开可见测试集不参与调参。
- `gated_geometry` 只作为诊断上界，不参与自动提交排序。

### 4.3 主要超参数与设置

| 方法 | 主要设置 | 证据来源 |
|---|---|---|
| `geometry` | `StandardScaler + SGDRegressor`，`alpha=0.0005`，`max_iter=30`，`tol=1e-3`，`early_stopping=True`，`validation_fraction=0.1`，`n_iter_no_change=3`，`average=True` | `reports/residual_geometry_cv_report.md` |
| `geometry` 训练方式 | 全量训练行，`train_rows_per_well = 0` | `reports/residual_geometry_cv_report.md` |
| `xgb` | `n_estimators=30`，`max_depth=4`，`learning_rate=0.05`，`subsample=0.9`，`colsample_bytree=0.9`，`reg_lambda=1.0`，`tree_method=hist`，`n_jobs=1` | `models/residual_xgb_config.json` / `reports/residual_xgb_cv_report.md` |
| `learned_gated_geometry` | `ridge`，特征列数 `27`，`snap alpha = False` | `reports/learned_gated_geometry_cv_report.md` |
| `gated_geometry` | alpha 网格 `[0.0, 0.25, 0.5, 0.75, 1.0]` | `reports/gated_geometry_cv_report.md` |

### 4.4 候选模型筛选与后处理

- 候选模型筛选以 baseline 的覆盖范围为参照；正式排名要求候选的行覆盖率和井覆盖率均不低于 baseline 的 95%。
- 排序首先比较完整覆盖下的交叉验证预测 RMSE；若差异很小，再比较最差井 RMSE、退化井数量与 P95 绝对误差。
- `geometry` 的覆盖率与 baseline 完全一致（1.000 / 1.000），因此可以进入正式排序。
- `gated_geometry` 的交叉验证预测更低，但属于诊断上界，不作为最终提交模型。
- 后处理采用交叉验证保护：若后处理后 RMSE 变差，则不保留后处理结果。

## 5. 主要结果

### 5.1 核心模型比较

| 方法 | 角色 | RMSE | MAE | P95 abs error | 改善 / 退化井 |
|---|---|---:|---:|---:|---:|
| 基线模型（`baseline`） | 对照组 | 119.933 | 53.680 | 182.780 | - |
| 基于几何特征的残差回归模型（`geometry`） | 线性残差回归 | 15.629 | 11.173 | 31.945 | 632 / 141 |
| 基于树模型的残差回归模型（`xgb`） | 树残差回归 | 31.473 | 13.748 | 34.654 | 626 / 147 |
| 学习型门控残差模型（`learned_gated_geometry`） | 可泛化门控 | 19.818 | 13.984 | 41.698 | 653 / 120 |
| 诊断上界（`gated_geometry`） | 上界分析 | 13.381 | 9.468 | 27.353 | 670 / 0 |

### 5.2 集成与后处理

| 候选 | RMSE |
|---|---:|
| `geometry` | 15.629 |
| `optimized` | 15.629 |
| `balanced` | 42.223 |
| `aggressive` | 59.901 |
| `conservative` | 109.595 |
| `baseline` | 119.933 |

结论：

- 简单集成未优于基于几何特征的残差回归模型。
- `optimized` 与 `geometry` 持平。
- `balanced`、`aggressive`、`conservative` 均明显劣化。

### 5.3 候选筛选结果

- 最终选中的候选：`geometry`
- 选中交叉验证预测 RMSE：15.628804658466327
- 覆盖率（相对 baseline）：rows `1.000`，wells `1.000`
- tie tolerance：`0.010`
- 选中依据：完整覆盖下的交叉验证预测 RMSE 最低

### 5.4 后处理结果

- `geometry_postprocessed` 的交叉验证预测 RMSE 从 `15.628804658466327` 恶化到 `69.92550348606268`
- 因此该后处理候选被拒绝，不能作为最终提交结果

## 6. 可直接写入正文的边界性事实

- 仓库中尚未找到 Kaggle 官方 public/private leaderboard 分数或最终 hidden rerun 分数的明确记录，因此官方测试结果应保留为【官方测试结果待补】。
- `gated_geometry` 只能作为诊断上界，不能作为最终泛化模型。
- 公开可见测试集与训练集重合，不能用于调参或独立验证。
- 在当前特征集和样本结构下，`xgb` 的交叉验证预测 RMSE 为 31.473，明显高于 `geometry` 的 15.629，说明更高的模型复杂度并未自动带来更优效果。
- 如果正文需要引用官方来源，可写 Kaggle 竞赛页、数据页和规则页三项链接。

## 7. 附录材料（按主题归类）

> 附录只保留能支撑正文、但展开后会较长的事实材料；脚本清单、运行日志和工程调试说明不纳入论文附录正文。

### 7.1 数据与任务说明附录

- 官方来源仍以 Kaggle 竞赛概览页、数据页和规则页为准。
- 任务定义：根据水平井已知段 `TVT_input`、轨迹坐标与 `GR`，预测隐藏尾段 `TVT`。
- 评价指标：RMSE；提交格式：`id,tvt`，其中 `id = {well}_{row_index}`。
- 训练 horizontal 固定列为 `MD, X, Y, Z, ANCC, ASTNU, ASTNL, EGFDU, EGFDL, BUDA, TVT, GR, TVT_input`；测试 horizontal 固定列为 `MD, X, Y, Z, GR, TVT_input`。
- 训练 typewell 固定列为 `TVT, GR, Geology`；可见测试 typewell 固定列为 `TVT, GR`。
- `Geology` 仅在训练 typewell 中出现。
- `ANCC`、`ASTNU`、`ASTNL`、`EGFDU`、`EGFDL`、`BUDA` 属于训练-only 地层相关列，不能作为正式测试阶段的必需输入。

### 7.2 数据统计与任务难点附录

- 数据规模：训练井 773，公开可见测试井 3，样例提交 14,151 行，训练 horizontal 总行数 5,092,255，训练 hidden target 行数 3,783,989。
- 训练 horizontal 每井长度分布：mean 6,587.650，std 1,311.460，min 2,058，median 6,576，max 12,141。
- 公开可见测试井 rows 分别为 5,278、7,559、6,384；对应 target rows 分别为 3,836、6,014、4,301。
- 训练 horizontal 的 `GR` 缺失率为 29.610%，`TVT_input` 缺失率为 74.310%；`ANCC` 缺失率为 0.900%，`EGFDL` 缺失率为 0.120%。
- hidden target rows 的 min / median / max 为 407 / 4,840 / 10,052；known rows 的 min / median / max 为 851 / 1,703 / 2,392。
- target GR 缺失率分位数为 q0 0.0067、q25 0.1308、q50 0.3029、q75 0.4977、q90 0.5946、max 0.8118。
- typewell `Geology` 标签分布显著不均衡，最大类 `ANCC` 为 294,268，最小类 `EGFD200` 为 1。
- baseline 在不同 hidden interval 长度上的 mean RMSE 为：0-2k 9.709、2k-4k 30.137、4k-6k 57.833、6k-8k 91.024、8k-12k 122.556。

### 7.3 完整实验结果附录

- `baseline`：RMSE 119.933，MAE 53.680，P95 abs error 182.780，max abs error 2552.660。
- `geometry`：RMSE 15.629，MAE 11.173，P95 abs error 31.945，improved wells 632，degraded wells 141。
- `xgb`：RMSE 31.473，MAE 13.748，P95 abs error 34.654，improved wells 626，degraded wells 147。
- `learned_gated_geometry`：RMSE 19.818，MAE 13.984，P95 abs error 41.698，degraded wells 120。
- `gated_geometry` 诊断上界：RMSE 13.381，MAE 9.468，P95 abs error 27.353，degraded wells 0。
- 集成候选中，`optimized` 与 `geometry` 持平（RMSE 15.629），`balanced` 为 42.223，`aggressive` 为 59.901，`conservative` 为 109.595。
- 后处理候选 `geometry_postprocessed` 的 RMSE 从 15.628804658466327 恶化到 69.92550348606268，因此被拒绝。
- `geometry` 的 alpha 搜索结果：alpha 1.0 对应 RMSE 15.628804658466327；0.75 对应 33.6079；0.5 对应 61.4914；0.25 对应 90.5503；0 对应 119.933。

### 7.4 候选筛选与失败案例附录

- 候选筛选以 baseline 覆盖范围为参照，正式排名要求行覆盖率和井覆盖率均不低于 95%；最终排序依据完整覆盖下的 OOF RMSE。
- tie tolerance 为 0.01；若差异很小，再比较 worst-well RMSE、退化井数量和 P95 abs error。
- 当前数据版本记录为 `raw_file_count = 2327`、`train_well_count = 773`、`test_well_count = 3`、`sample_submission_rows = 14151`。
- 当前最终选中的可泛化候选为 `geometry`，其覆盖率相对 baseline 为 rows 1.000、wells 1.000，Selected OOF RMSE 为 15.628804658466327。
- `gated_geometry` 作为诊断上界被排除在自动选择之外。
- `geometry_postprocessed` 因后处理护栏失败被拒绝，不能作为最终提交结果。
- selected candidate 的典型 worst wells 包括 `1b1eba53`、`86454a6f`、`5f4d2a52`、`2fd68f7b`、`ba48188d`、`f88ddb26`、`fef8af96`、`43e16325`，其中部分井仍比 baseline 退化。

### 7.5 图表材料附录

- `reports/figures/baseline_worst_wells/` 记录 baseline 最差井示例，共 20 张图。
- `reports/figures/residual_geometry_best_improved/` 记录几何残差模型最优改进井示例，共 10 张图。
- `reports/figures/residual_geometry_worst_degraded/` 记录几何残差模型最差退化井示例，共 10 张图。
- 代表性井包括 `a959858c`（baseline 最差且 residual 改进明显）和 `1b1eba53`（residual 退化示例）。
