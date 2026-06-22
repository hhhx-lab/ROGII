# Part 4: Candidate Selection、Postprocess Guard 与 Submission Ops

Part 4 的目标不是手工挑一个名字好听的提交，而是建立一条可验证的最终提交链：

```text
generate candidates
  -> compare by OOF CV
  -> check per-well risk
  -> apply postprocess only if guarded
  -> export final submission
```

最终提交必须服务于总公式：

```text
final_tvt = baseline_tvt + correction
```

其中 correction 可以来自 SGD、XGBoost、tree residual、gated residual、alignment-enhanced residual 或 blend，但每个候选都必须有 OOF 证据。

## 1. 当前真实状态

当前已经实现的能力：

- `scripts/blend_predictions.py` 可以生成 `conservative`、`balanced`、`aggressive`、`optimized` 候选；
- blend 脚本会写 `outputs/ensemble_cv_summary.csv`；
- blend 脚本会按 route 搜索 `optimized` 权重；
- `scripts/select_submission_candidate.py` 会读取当前候选 OOF，并在共同 OOF 覆盖上比较候选；
- `scripts/make_submission.py --variant auto` 已接入 candidate selector；
- `scripts/postprocess_predictions.py` 已经有 `--min-improvement` OOF guard，后处理变差时会回退输入 submission。

当前报告显示的问题：

- `reports/ensemble_report.md` 中 geometry residual RMSE `16.0862`，明显好于 balanced `41.6539` 和 aggressive `59.3856`；
- 说明固定手写 blend 不一定优于单模型；
- `reports/postprocess_report.md` 中 balanced 后处理 RMSE 从 `41.6539` 变成 `78.1925`；
- 说明 postprocess 不能无条件启用。

因此 Part 4 的优化重点是把这些已有能力变成更严格的契约：

```text
OOF 最优优先
per-well 风险检查
postprocess hard guard
final manifest 记录选择理由
```

## 2. 输入与输出

### 2.1 输入

候选进入 Part 4 前，至少要有：

```text
outputs/baseline_predictions_train_hidden.csv
outputs/baseline_predictions_test.csv
outputs/residual_geometry_oof.csv
outputs/residual_geometry_test_predictions.csv
outputs/part3_diagnostics.csv
submissions/geometry_residual_submission.csv
```

未来新增候选还应提供：

```text
outputs/residual_xgb_oof.csv
outputs/residual_xgb_test_predictions.csv
outputs/residual_hgb_oof.csv
outputs/residual_hgb_test_predictions.csv
outputs/gated_residual_oof.csv
outputs/gated_residual_test_predictions.csv
outputs/alignment_enhanced_oof.csv
outputs/alignment_enhanced_test_predictions.csv
```

没有 OOF 的候选不能进入正式 selection。

### 2.2 输出

当前输出：

```text
submissions/conservative_submission.csv
submissions/balanced_submission.csv
submissions/aggressive_submission.csv
submissions/optimized_submission.csv
outputs/blend_oof.csv
outputs/ensemble_cv_summary.csv
outputs/ensemble_route_weights.csv
outputs/submission_manifest.json
reports/ensemble_report.md
reports/postprocess_report.md
reports/candidate_selection_report.md
reports/submission_log.md
outputs/selected_candidate.json
submission.csv
```

下一步建议扩展输出：

```text
outputs/candidate_registry.csv
outputs/candidate_oof_metrics.csv
outputs/candidate_per_well_risk.csv
outputs/candidate_selection_decision.json
reports/candidate_selection_report.md
```

其中 `outputs/selected_candidate.json` 和 `reports/candidate_selection_report.md` 是本轮已实现的最小 candidate selection 产物；正式 registry 后续再扩展。

## 3. Candidate Generation

### 3.1 当前候选

当前可运行候选：

| 候选 | 当前状态 | 作用 |
|---|---|---|
| baseline | 已实现 | 安全控制组 |
| geometry / SGD residual | 已实现 | 当前最强 residual control |
| xgb/tree residual | 脚本已实现，需运行生成 OOF | 非线性 residual candidate |
| conservative | 已实现 | 手写保守 blend |
| balanced | 已实现 | 手写中等 blend |
| aggressive | 已实现 | 手写激进 blend |
| optimized | 已实现 | route-aware OOF 搜索权重 |

注意：如果 OOF 显示 geometry residual 最好，最终就应该允许选择 geometry，而不是默认 balanced。

### 3.2 下一步候选

计划新增：

| 候选 | 目的 |
|---|---|
| XGBoost residual | 已接入 `--spec xgb`，运行后生成候选 |
| HistGradientBoosting residual | 已作为 XGBoost fallback 接入 |
| LightGBM residual | 环境允许时的强 tabular 候选 |
| gated residual | 降低 residual 修坏 baseline-good wells 的风险 |
| GR/typewell alignment enhanced residual | 使用 Part 3 alignment 特征 |
| alignment-gated residual | alignment confidence 只影响 alpha |
| postprocessed variants | 只在 OOF guard 通过时保留 |

### 3.3 候选注册表

每个候选应该登记：

```text
candidate_name
model_family
source_oof_path
source_test_path
uses_baseline
uses_residual
uses_gater
uses_alignment
postprocess_status
data_version
feature_version
cv_version
created_at
```

为什么需要 registry：

- 避免混用旧文件；
- 避免不知道某个 submission 来自哪个模型；
- 让 `make_submission.py --variant auto` 有更清楚的候选池；
- 方便后续 GitHub 交接。

## 4. OOF CV Comparison

### 4.1 为什么 OOF 是硬标准

Public leaderboard 只有有限公开样本，且 hidden rerun 可能换井。只靠 public LB 调模型，很容易过拟合。

因此候选优劣必须先看训练井 hidden rows OOF：

```text
truth_tvt vs candidate_oof_tvt
```

必须比较：

- overall RMSE；
- MAE；
- median abs error；
- P90/P95/P99 abs error；
- max abs error；
- mean well RMSE；
- improved/degraded wells；
- worst degradation；
- long target wells；
- GR missing high wells；
- baseline-good wells。

### 4.2 当前选择逻辑

当前 `scripts/make_submission.py --variant auto` 已经会：

1. 读取 `outputs/ensemble_cv_summary.csv`；
2. 过滤本地存在的 candidate submission；
3. 按 RMSE 排序；
4. 选择 RMSE 最低的 variant；
5. 生成最终 `submission.csv`。

这已经是正确方向，但下一步需要更严格：

- 不只看 overall RMSE；
- 增加 per-well risk guard；
- 增加 worst-tail guard；
- 增加 postprocess decision；
- 记录最终选择理由。

## 5. Gated Correction Selection

### 5.1 为什么在 Part 4 里还要管 gater

Part 2 负责训练 residual，Part 3 提供 route/alignment 信号，Part 4 负责决定最终候选。因此 gater 的结果也必须在 Part 4 里和其他候选公平比较。

gated candidate 统一写成：

```text
final_tvt = baseline_tvt + alpha * predicted_residual
```

其中：

- `predicted_residual` 可以来自 SGD/XGBoost/tree；
- `alpha` 可以来自 route、alignment confidence、tree gater 或 OOF 规则。

### 5.2 gater 解决什么问题

解决：

- baseline 本来很好但 residual 修坏；
- alignment 信号不可靠时强行修正；
- aggressive 模型整体不错但 tail risk 大；
- 不同 route 需要不同 correction 强度。

### 5.3 gater 候选如何进入 Part 4

gater 不能只输出 test submission，还必须输出：

```text
outputs/gated_residual_oof.csv
outputs/gated_residual_test_predictions.csv
outputs/gated_alpha_by_row.csv
reports/gated_residual_cv_report.md
```

报告至少说明：

- alpha 来源；
- alpha 分布；
- 哪些井 alpha 接近 0；
- 哪些井 alpha 接近 1；
- 和 ungated residual 的 OOF 对比；
- baseline-good wells 是否少被修坏。

### 5.4 失败时回退

- gated 不如 ungated：回退 ungated；
- gated 只改善 tail：作为 conservative candidate；
- alpha 过度保守导致收益消失：降低 gater 强度；
- alpha 过度激进导致 worst wells 爆炸：提高回退阈值。

## 6. Postprocess Guard

### 6.1 为什么 postprocess 不能无条件启用

后处理看起来会让曲线更平滑，但可能把真实变化抹掉。

当前报告已经显示：

```text
balanced OOF RMSE: 41.6539 -> 78.1925
```

所以规则必须是硬的：

```text
if postprocess_rmse_after > postprocess_rmse_before:
    reject postprocessed submission
    use original candidate
```

当前 `scripts/postprocess_predictions.py` 已有 `oof_worse_reverted` 逻辑；文档和运行指南必须要求默认使用这个 guard，不允许为了“曲线好看”绕过。

### 6.2 postprocess 可以做什么

允许：

- residual clip；
- residual rolling median；
- step cap；
- route-specific residual bounds；
- output range clip；
- submission QA。

不建议：

- 直接强平滑 final TVT；
- 在没有 OOF 的情况下启用；
- 用 `--allow-worse` 生成最终提交；
- 根据 public LB 手调平滑强度。

### 6.3 如何验证

每个 postprocessed candidate 都要比较：

- before/after OOF RMSE；
- before/after MAE；
- before/after P95/P99；
- before/after worst wells；
- jump count；
- per-route metrics。

只有 before/after 不变差，才允许进入 final candidate pool。

### 6.4 失败时回退

- OOF 变差：自动回退原 submission；
- OOF 覆盖不足：回退原 submission；
- 某个 route 变差：对该 route 禁用 postprocess；
- 只有少数井变好但 tail 爆炸：不作为 balanced。

## 7. Final Submission Export

### 7.1 当前可运行流程

当前短期可运行：

```bash
.venv/bin/python scripts/blend_predictions.py
.venv/bin/python scripts/make_submission.py --variant auto --output submission.csv
```

其中：

- `blend_predictions.py` 生成候选和 OOF summary；
- `make_submission.py --variant auto` 选 OOF RMSE 最低的可用候选；
- 默认 postprocess policy 是 `auto`；
- postprocess guard 不通过时输出会回退原候选。

### 7.2 完成优化后的推荐流程

完成 XGBoost / gater / alignment-enhanced residual 后，推荐流程应该变成：

```text
1. register all candidates
2. validate every candidate has OOF and test prediction
3. compute candidate OOF metrics
4. compute per-well risk metrics
5. reject candidates with unacceptable degradation
6. run guarded postprocess as optional candidate transform
7. choose best validated candidate
8. export submission.csv
9. write manifest and model card
```

最终选择伪代码：

```text
valid_candidates = candidates with:
  complete OOF
  complete test prediction
  no NaN / inf
  acceptable per-well risk
  postprocess not worse if used

selected = lowest OOF RMSE among valid_candidates
write submission.csv from selected
```

### 7.3 Submission QA

提交前必须检查：

```text
columns exactly: id,tvt
row count equals sample_submission
id order equals sample_submission
no duplicated id
no NaN / inf
tvt numeric
prediction summary reasonable
```

失败时不得提交。

## 8. Conservative / Balanced / Aggressive 的新定位

这三个名字可以保留，但不能再作为最终选择逻辑本身。

新的定位：

- `conservative`：风险低的候选；
- `balanced`：收益和风险折中候选；
- `aggressive`：高收益但 tail risk 更大的候选；
- `optimized`：OOF 搜索得到的候选；
- `geometry` / `xgb` / `gated`：也可以直接成为最终候选。

最终不是“默认 balanced”，而是：

```text
在所有通过 guard 的候选里选 OOF 最优，并记录为什么。
```

## 9. Leaderboard 使用原则

Public leaderboard 可以用于 sanity check，但不能替代 OOF。

允许：

- 提交前确认格式；
- 比较不同风险类型；
- 发现 local/public gap 后回到 CV 分析。

不允许：

- public LB 好就推翻 OOF；
- public LB 差就盲调参数；
- 用 visible test 3 口井手工改 route；
- 没有 hypothesis 就连续提交微调。

如果 local CV 好但 public LB 差：

- 检查 mask 是否不匹配；
- 检查 test GR/typewell 分布；
- 检查 postprocess 是否被接受或回退；
- 提交 conservative 对照；
- 更新 failure analysis。

如果 public LB 好但 local CV 一般：

- 标记为 aggressive；
- 不作为唯一最终候选；
- 查是否 public overfit。

## 10. 报告与交接

最终一次正式 run 至少要有：

```text
reports/ensemble_report.md
reports/postprocess_report.md
reports/submission_log.md
reports/final_model_card.md
outputs/submission_manifest.json
```

下一步建议新增：

```text
reports/candidate_selection_report.md
outputs/candidate_selection_decision.json
```

报告必须写清楚：

- 候选来源；
- OOF 分数；
- per-well 风险；
- postprocess 是否接受；
- 最终选择哪个；
- 为什么没有选择其他候选；
- 失败时回退到哪个候选。

## 11. Part 4 完成标准

当前已完成的最低能力：

- 能生成 hand-written blend candidates；
- 能生成 optimized candidate；
- 能按 OOF RMSE 自动选择可用 variant；
- postprocess 有 guard；
- 能导出 `submission.csv`。

下一步完成标准：

- candidate registry 完成；
- XGBoost / HGB / gated / alignment-enhanced candidates 可以进入统一评估；
- selection 不只看 overall RMSE，还看 tail risk；
- postprocess 变差时硬禁止；
- final manifest 记录完整选择理由；
- GitHub 运行指南能让别人从数据到 submission 复现当前推荐流程。

## 12. 最终原则

Part 4 的一句话原则：

```text
不要相信候选名字，只相信同一套 OOF 下的分数、风险和 guard 结果。
```
