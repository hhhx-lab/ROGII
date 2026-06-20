# Part 1 Quality Review

## 复核结论

这次复核不是重新跑一遍脚本，而是按 `docs/plans/01_validation_baseline.md` 逐项找质量缺口。结论是：Part 1 主链路已经可用，但上一版确实有几处工程边界不够硬，已在本次修补并重新验证。

## 发现并修复的问题

| 问题 | 风险 | 修复 |
|---|---|---|
| 数据契约只按固定数量检查，没有显式和 EDA 报告交叉核验 | EDA 报告与 contract 可能悄悄不一致 | `scripts/check_data_contract.py` 增加 `reports/eda_summary.md` inventory 解析与比对，报告新增 EDA cross-check |
| 多 mask 的 `TVT_input_masked` 只在评估脚本内部临时生成 | 后续 residual/typewell 特征脚本可能各写各的 mask 逻辑，增加泄漏风险 | `scripts/rogii_utils.py` 新增 `apply_cv_split_mask()`，统一生成 `TVT_input_masked` 并隐藏 target/future TVT_input |
| `cv_splits.csv` 中 `local_slope_mean/local_slope_std/curvature_proxy` 来自目标真值，但文档边界不够显式 | Part 2 如果误把这些列当特征，会产生目标泄漏 | `reports/cv_design.md` 明确这些列是 truth-derived diagnostics，只能用于 split 设计和报告，不能作为 predictor |
| failure analysis 图里有 typewell GR/Geology，但候选表缺结构化字段 | 后续自动筛选 failure case 时无法用 typewell/geology 信息 | `outputs/failure_case_candidates.csv` 增加 `typewell_rows/typewell_tvt_span/typewell_gr_missing_rate/typewell_geology_label_count/typewell_geology_labels` |
| failure type 报告只显示出现过的类别 | 容易误以为没有设计 `abrupt_shift/gr_transition` | `reports/baseline_failure_analysis.md` 现在保留所有预定义 failure type，未出现类别记 0 |
| 最终审计覆盖不够细 | 只证明文件存在，不足以证明防泄漏和结构化诊断可用 | `scripts/validate_part1_outputs.py` 从 34 项扩展到 40 项，新增 EDA cross-check、mask 防泄漏、truth-derived non-feature 文档、typewell/geology 诊断、质量报告和进度文档检查 |
| Part 1 计划按 raw-data 复核后新增边界，但审计未同步 | 计划已写 test `Geology` optional、visible test 不可调参、tail masks 主优先级，但完成审计无法强制这些约束 | 新增 `scripts/review_part1_plan_alignment.py` 与 `reports/part1_plan_implementation_review.md`，并将最终审计扩展到 51 项，覆盖 PPTX/sample、visible-test overlap、test typewell fallback、CV 优先级和 submission sanity 声明 |

## 重新验证结果

| 验证项 | 结果 |
|---|---|
| Python 语法检查 | 通过 |
| `git diff --check` | 通过 |
| 数据契约 | `critical_errors=0`, `warnings=11` |
| CV splits | 7 类 mask，5,411 splits，每类 773 口井 |
| Baseline CV | 最优 `B0_constant_last`, row RMSE 15.9099 |
| Multi-mask baseline | 7 类 mask 全覆盖 |
| Failure analysis | 773 candidates，20 张 worst-well 图 |
| Submission QA | 7 个 baseline submission 均 14,151 行、3 口 visible wells、无空预测 |
| 计划-实现复核 | 13 checks, 0 failures |
| 最终审计 | 51 checks, 0 failures |

## 仍需记住的边界

| 边界 | 说明 |
|---|---|
| Visible test typewell 无 `Geology` | 训练 typewell 有 `Geology`，visible test typewell 只有 `TVT/GR`；合同已将 test Geology 标为 optional，后续模型不能假设 test Geology label 一定存在 |
| `B3/B4` 未实现 | 计划允许 Part 1 至少完成 B0/B1/B2；B3/B4 应在 Part 2/4 有稳定 residual 后再做，不应现在引入过拟合风险 |
| failure type 是启发式初判 | 已足够用于第一批 failure analysis，但不是地质解释终稿；Part 3 需要结合 GR/typewell 对齐复核 |
| `baseline_predictions_train_hidden.csv` 很大 | 本地约 2.7G，按计划作为 residual 入口保留在 `outputs/`，不进入 git |
| Visible test 与 train ID 重合 | 3 口 visible test 只能用于格式和运行 sanity，不可用于调参、offset 选择或 blend 权重选择 |

## 当前可进入 Part 2 的证据

- `outputs/baseline_cv_by_well.csv`
- `outputs/baseline_predictions_train_hidden.csv`
- `outputs/cv_splits.csv`
- `outputs/failure_case_candidates.csv`
- `reports/baseline_cv_report.md`
- `reports/baseline_failure_analysis.md`
- `reports/part1_plan_implementation_review.md`
- `reports/part1_completion_audit.md`
