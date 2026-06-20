# Part 1 执行进度：数据契约、验证体系与可信 Baseline

更新时间：2026-06-20

## 当前目标

严格实现 `docs/plans/01_validation_baseline.md` 的第一部分，完成数据梳理、数据契约、验证 split、baseline 家族、failure analysis，并为 Part 2 residual model 留出可直接读取的入口。

## 进度总览

| 模块 | 状态 | 当前证据 |
|---|---|---|
| 数据盘点 | 已完成 | 本地 `data/raw` 文件可读取，zip/pptx/sample submission 存在 |
| 数据契约与版本 | 已完成 | `critical_errors=0`，已生成 `outputs/data_version.json` 与 `reports/data_contract_report.md` |
| 原始隐藏段 baseline CV | 已完成 | 773 口井、3,783,989 行 target，最佳 baseline 为 `B0_constant_last`，RMSE=15.9099 |
| 多 mask split | 已完成 | 7 类 mask，共 5,411 个 split，每类覆盖 773 口井 |
| 多 mask baseline 验证 | 已完成 | `reports/baseline_multimask_report.md` 显示 7 类 mask 下 B0 均为最优 |
| Baseline B0/B1/B2 | 已完成 | B0、B1、B2(K=50/100/200/500) 已进入 CV 和 submission 控制组 |
| Failure analysis | 已完成 | 已生成 773 口井候选表、worst 20 图表和失败类型统计 |
| Part 1 计划-实现复核 | 已完成 | `reports/part1_plan_implementation_review.md`：13 项检查，0 个失败 |
| Part 1 完成审计 | 已完成 | `reports/part1_completion_audit.md`：51 项检查，0 个失败 |
| 二次质量复核 | 已完成 | `reports/part1_quality_review.md` 记录发现问题、修复和剩余边界 |

## 实施顺序

1. 建立公共数据读取、ID 解析、baseline 和 metric 工具。已完成。
2. 实现数据契约检查与 `outputs/data_version.json`。已完成。
3. 扩展原始隐藏段 baseline CV，输出 per-row prediction 和 per-well metrics。已完成。
4. 生成多 mask split，确保固定 seed、至少 5 类 mask、每类至少 300 口井。已完成。
5. 基于 baseline 输出做 failure analysis 和图表。已完成。
6. 运行全链路验证并更新本进度文档。已完成。

## 关键运行结果

| 项目 | 结果 |
|---|---|
| 数据 hash | `46fd84d5e7e1` |
| 数据契约 critical errors | 0 |
| 数据契约 warnings | 11，均为 test typewell 无 Geology 或少数 train formation 列全空 |
| 下游契约门禁 | `assert_data_contract_ready()` 已接入 CV split、baseline CV、多 mask、failure、submission、审计脚本 |
| 原始隐藏段 target rows | 3,783,989 |
| 原始隐藏段最佳 baseline | `B0_constant_last` |
| 原始隐藏段最佳 row RMSE | 15.9099 |
| 旧 tail-slope k200 row RMSE | 119.9333 |
| 多 mask split | 5,411 |
| 多 mask 类型 | 7 |
| 每类 mask 覆盖井数 | 773 |
| failure candidates | 773 |
| worst-well 诊断图 | 20 张 |
| Part 1 计划-实现复核 | 13 checks, 0 failures |
| Part 1 审计 | 51 checks, 0 failures |

## 当前工程结论

- `B0_constant_last` 是当前最可信的 conservative baseline，也是 Part 2 residual 的首选残差基准。
- Tail-slope 外推在本数据上显著过激，适合作为 geometry trend stress-test，而不是主 baseline。
- 高曲率 mask 的 B0 row RMSE 明显升高，说明后续最大收益点不是简单外推，而是 GR/typewell 对齐与层位偏移识别。
- Failure analysis 中主要类型是 `smooth_bias` 与 `slope_change`，这与“先 residual，再 GR/typewell 对齐”的路线一致。

## 最终审计结果

`scripts/review_part1_plan_alignment.py` 已运行通过，生成 `reports/part1_plan_implementation_review.md`。`scripts/validate_part1_outputs.py` 已运行通过，生成 `reports/part1_completion_audit.md`。二次质量复核发现并修补了 EDA 交叉核验、公共 mask 防泄漏入口、truth-derived split 诊断列边界、failure type 零计数展示、typewell/geology 结构化诊断，以及 raw-data 复核后新增的 visible-test/typewell-Geology/CV-priority 边界。审计覆盖：

- Part 1 要求的关键 output/report 是否存在；
- `data_version.json` 必要字段和井数；
- 数据契约 critical error 是否为 0；
- 下游脚本是否通过数据契约门禁读取同一 data hash；
- baseline CV 是否覆盖 773 口井；
- B0/B1/B2 及 B2 K variants 是否都进入验证；
- 逐行 baseline prediction 行数是否匹配；
- CV split mask 类型和每类井数是否达标；
- CV 设计是否明确 original/trailing tail 为主 proxy、mid/random 为压力测试；
- visible test 是否被明确限制为 sanity check；
- test typewell 无 Geology 时是否要求 fallback；
- failure candidates、worst-well 图表和 failure type 是否达标；
- Part 1 计划-实现复核是否通过；
- baseline submission 是否行数、列名、非空预测均有效。

## 风险与处理

| 风险 | 处理方式 |
|---|---|
| 人工 mask 泄漏未来 `TVT_input` | split 中显式保存 `known_allowed_start_row` / `known_allowed_end_row` |
| baseline 只看 overall RMSE | 报告同时输出 row-weighted、per-well、bucket、GR-missing 子集 |
| 数据重新下载导致结果不可比 | 所有报告写入 data hash，训练/评估脚本读取 `outputs/data_version.json` |
| 图表过多影响仓库体积 | 只生成 worst 20 wells 的 PNG，作为工程诊断图 |
