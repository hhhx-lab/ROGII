# ROGII 全量推理指南

这份文档说明如何从比赛数据走到可提交的 `submission.csv`。它同时区分三件事：

- 当前已实现：现在仓库脚本能直接跑的流程；
- 下一步计划实现：文档计划里已经明确，但代码还没完成的能力；
- 完成优化后的推荐流程：后续冲榜时希望达到的标准流程。

本轮计划的核心公式保持不变：

```text
final_tvt = baseline_tvt + correction
```

不要把流程理解成直接预测绝对 TVT。

## 1. 数据位置与契约

推荐数据位置：

```text
data/
|-- train/
|-- test/
`-- sample_submission.csv
```

脚本通过 `scripts/data_paths.py` 读取数据，兼容：

- `data/train`、`data/test`
- `data/raw/train`、`data/raw/test`

一次实验只使用一套有效数据入口，避免新旧数据混用。

当前可运行的数据检查：

```bash
.venv/bin/python scripts/run_eda.py
.venv/bin/python scripts/evaluate_baseline_cv.py
```

这些步骤会更新或生成：

```text
reports/eda_summary.md
outputs/baseline_cv_by_well.csv
reports/baseline_cv_report.md
```

验证重点：

- train/test 文件能被找到；
- sample submission 行数和 id 顺序正确；
- 训练井 hidden rows 能用于 OOF；
- baseline 结果能正常生成。

## 2. 环境

推荐使用项目本地虚拟环境：

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

后续命令统一使用：

```bash
.venv/bin/python ...
```

不要在同一次 run 里混用系统 Python、Conda 和 `.venv`。

## 2.1 训练前清理 / 旧产物归档规则

正式 full run 之前，先把旧训练产物移动到 `archive/`，不要直接删除。

为什么要做：

- `features/`、`outputs/`、`submissions/`、`reports/` 里可能混有不同 run 的旧文件；
- candidate selection 依赖 OOF 覆盖、数据版本和同一次 run 的候选产物；
- 旧 OOF 文件会让自动选择逻辑误判，例如只在少量井上比较候选；
- leaderboard submission 应该从干净产物目录开始，避免把旧结果当成新结果。

推荐归档目录格式：

```text
archive/runs/YYYYMMDD_HHMMSS_pre_full_run_cleanup/
```

可以归档的文件：

```text
features/*.csv
features/*.parquet
outputs/*.csv
outputs/*.json
submissions/*.csv
submission.csv
reports/candidate_selection_report.md
reports/postprocess_report.md
reports/ensemble_report.md
reports/residual_*_report.md
reports/full_inference_run_summary.md
reports/full_inference_run_summary.json
reports/part2_completion_audit.md
reports/submission_log.md
reports/step_time_log.md
reports/figures/residual_geometry_*/
```

不能动的文件和目录：

```text
data/train
data/test
data/raw
.venv
scripts
docs
README.md
requirements.txt
.git
.gitignore
features/README.md
features/.gitkeep
outputs/README.md
outputs/.gitkeep
submissions/README.md
```

推荐操作流程：

1. 看当前 git 状态，确认有哪些 dirty diff：

```bash
git status --short --branch
git status --short --ignored
du -sh data features outputs submissions reports .venv 2>/dev/null
```

2. 建归档目录：

```bash
mkdir -p archive/runs/<timestamp>_pre_full_run_cleanup
```

3. 把旧产物移动进去，保持相对路径结构。不要用 `rm` 删除旧结果。

4. 在归档目录写 `cleanup_manifest.json` 和 `cleanup_manifest.md`，记录：

```text
cleanup started / finished time
git branch
HEAD commit
pre-cleanup dirty summary
moved files
skipped files
moved total size
archive directory
restore command
```

5. 清理后检查：

```bash
git status --short --branch
du -sh data features outputs submissions reports archive 2>/dev/null
find features -maxdepth 1 -type f | sort
find outputs -maxdepth 1 -type f | sort
find submissions -maxdepth 1 -type f | sort
```

检查重点：

- `data/train` 和 `data/test` 还在；
- `features/README.md` 和 `features/.gitkeep` 还在；
- `outputs/README.md` 和 `outputs/.gitkeep` 还在；
- `submissions/README.md` 还在；
- 旧的大产物已经进入 `archive/runs/<run_id>/`；
- `scripts/`、`docs/`、`.venv/` 没被误动。

恢复方式：

```bash
rsync -av archive/runs/<run_id>/ ./
```

和 full run 的关系：

- 训练前清理不是训练本身；
- 清理完成后，再从 Step 1 开始跑 full inference；
- 如果只是临时调试，不一定每次都归档；
- 如果是准备正式 leaderboard submission，必须先归档旧产物。

## 3. 当前已实现的全量流程

当前可运行流程是：

```text
1. data contract / EDA
2. baseline generation
3. baseline CV
4. feature build
5. geometry SGD full-row residual candidate
6. Part 3 diagnostics / route
7. per-well oracle alpha gater (`gated_geometry`, diagnostic upper bound)
8. learned gater (`learned_gated_geometry`, auto-submission candidate)
9. optional XGBoost leftover stack (`xgb_leftover` + `gated_geometry_plus_xgb_leftover`)
10. blend candidate generation
11. candidate selection with oracle candidates excluded by default
12. postprocess with guard
13. final submission export
14. submission validation
```

注意：

- residual backbone 是 `--spec geometry --max-rows-per-well 0`；
- `gated_geometry` 现在明确是 oracle / diagnostic upper bound：它用每口训练井自己的 truth 搜 alpha，不能默认代表线上泛化能力；
- 当前推荐的可提交 gater 是 `learned_gated_geometry`，它用井级特征学习 alpha，并用 GroupKFold by well 验证；
- `--spec xgb` 只保留为 direct full-residual 对照，不是当前默认冲榜主线；
- `--spec xgb_leftover` 只在 geometry gater 之后作为可选 stack 层；
- 正式训练必须使用 full-row training，也就是 `--max-rows-per-well 0`；
- 正式 XGBoost run 建议加 `--require-xgboost`，避免环境缺依赖时静默 fallback 到 sklearn HistGradientBoosting；
- 当前 Part 3 主要是 diagnostics / route，不是 direct correction；
- postprocess 只有 OOF 不变差才应被接受。

### 3.1 每次全量运行都会记录配置

使用服务器全量入口时：

```bash
.venv/bin/python scripts/run_part2_full_server.py
```

脚本会在开跑前写入本次 run 的配置快照，跑完后再补上结果：

```text
reports/server_part2_full_run_config.md
reports/server_part2_full_run_config.json
reports/server_part2_full_run_configs/<run_id>.md
reports/server_part2_full_run_configs/<run_id>.json
```

配置快照会记录：

- 本次命令行参数，例如 `--residual-spec`、`--train-rows-per-well`、`--max-iter`、`--require-xgboost`；
- git branch / HEAD / dirty 状态；
- 数据入口、train/test 文件数、sample submission 行数；
- full-row training 是否开启；
- gater / xgb_leftover 是否开启；
- 计划执行的每一步命令和日志路径；
- 运行结束后的 return code、耗时和失败步骤。

为什么要看它：

- leaderboard 结果差时，先确认是不是跑错配置；
- 避免把 sampled run、fallback run、旧产物 run 当成正式 full run；
- 多次实验之间可以按 `run_id` 对比配置差异。

## 4. 当前短期可运行命令

如果你要从头跑当前已实现脚本，按下面顺序：

```bash
.venv/bin/python scripts/run_eda.py
.venv/bin/python scripts/evaluate_baseline_cv.py
.venv/bin/python scripts/build_baseline_features.py
.venv/bin/python scripts/build_geometry_features.py
.venv/bin/python scripts/train_residual_model.py --spec geometry --max-rows-per-well 0
.venv/bin/python scripts/build_part3_diagnostics.py
.venv/bin/python scripts/build_gated_geometry.py
.venv/bin/python scripts/train_learned_gater.py --model ridge
.venv/bin/python scripts/build_leftover_targets.py
.venv/bin/python scripts/train_residual_model.py --spec xgb_leftover --max-rows-per-well 0 --require-xgboost --max-iter 500
.venv/bin/python scripts/build_gated_stack.py
# optional control: .venv/bin/python scripts/train_residual_model.py --spec xgb --max-rows-per-well 0 --require-xgboost --max-iter 500
.venv/bin/python scripts/evaluate_model_cv.py
.venv/bin/python scripts/evaluate_residual_multimask.py
.venv/bin/python scripts/validate_part2_outputs.py
.venv/bin/python scripts/build_part3_features.py
.venv/bin/python scripts/blend_predictions.py
.venv/bin/python scripts/select_submission_candidate.py --dry-run
.venv/bin/python scripts/postprocess_predictions.py --variant auto
.venv/bin/python scripts/make_submission.py --variant auto --output submission.csv
.venv/bin/python scripts/validate_submission.py --submission submission.csv
```

如果你只想用已经存在的候选重新导出最终提交：

```bash
.venv/bin/python scripts/blend_predictions.py
.venv/bin/python scripts/select_submission_candidate.py --dry-run
.venv/bin/python scripts/postprocess_predictions.py --variant auto
.venv/bin/python scripts/make_submission.py --variant auto --output submission.csv
.venv/bin/python scripts/validate_submission.py --submission submission.csv
```

这条短路径要求前面的 baseline/residual/diagnostics/OOF/submission 产物都存在，且来自同一次有效 run。`--variant auto` 现在必须通过 `select_submission_candidate.py` 的覆盖率和 eligibility 检查；如果只是想手动导出某个旧候选，需要显式写 `--variant geometry`、`--variant optimized` 等具体名字。

## 5. Step 1: Baseline Generation

当前已实现：

```bash
.venv/bin/python scripts/build_baseline_features.py
.venv/bin/python scripts/evaluate_baseline_cv.py
```

主要产物：

```text
outputs/baseline_predictions_train_hidden.csv
outputs/baseline_predictions_test.csv
features/baseline_features_train.csv
features/baseline_features_test.csv
features/residual_targets.csv
reports/baseline_cv_report.md
reports/residual_target_report.md
```

为什么要做：

- baseline 是所有 correction 的锚点；
- residual target 依赖 baseline；
- final candidate 必须能和 baseline 比较。

验证是否成功：

- baseline OOF report 存在；
- train hidden rows 有 truth 和 baseline；
- test rows 和 sample submission 对齐；
- `features/residual_targets.csv` 里有 `residual_target`。

失败时回退：

- 不继续训练 residual；
- 先修数据路径、sample id、baseline feature。

## 6. Step 2: Feature Build

当前已实现：

```bash
.venv/bin/python scripts/build_geometry_features.py
.venv/bin/python scripts/build_part3_diagnostics.py
.venv/bin/python scripts/build_part3_features.py
```

当前产物：

```text
features/geometry_features_train.csv
features/geometry_features_test.csv
outputs/part3_diagnostics.csv
features/gr_features_train.csv
features/gr_features_test.csv
features/typewell_features_train.csv
features/typewell_features_test.csv
features/alignment_features_train.csv
features/alignment_features_test.csv
reports/part3_diagnostics_report.md
```

当前状态说明：

- geometry features 已用于当前 XGBoost residual primary 和 SGD residual control；
- Part 3 diagnostics 可用于 route / blend；
- alignment features 还应被视为下一步增强输入，不要当成已验证强 correction。

验证是否成功：

- train/test feature 行数和目标行一致；
- key 列 `well/split/row/id` 可对齐；
- 没有关键特征整列缺失；
- `outputs/part3_diagnostics.csv` 有 train/test route。

## 7. Step 3: Residual Candidates

### 7.1 正式冲榜主线: Geometry SGD + Gater

命令：

```bash
.venv/bin/python scripts/train_residual_model.py --spec geometry --max-rows-per-well 0
.venv/bin/python scripts/build_gated_geometry.py
```

当前正式主模型：

```text
StandardScaler + SGDRegressor
final_tvt = baseline_tvt + alpha * geometry_residual
```

目标：

```text
residual_target = truth_tvt - baseline_tvt
```

输出：

```text
outputs/residual_geometry_oof.csv
outputs/gated_geometry_oof.csv
outputs/gated_alpha_by_well.csv
outputs/gated_geometry_test_predictions.csv
submissions/gated_geometry_submission.csv
reports/gated_geometry_cv_report.md
models/gated_geometry_config.json
```

验证：

- gated OOF RMSE 是否优于 ungated geometry；
- degraded wells 是否下降；
- worst-well RMSE / P95 是否改善；
- `fit_fraction` 应接近 `1.0`；
- `max_rows_per_well` 应为 `0`。

失败时回退：

- 回退 ungated geometry；
- 再回退 baseline。

### 7.2 可选 stack: XGBoost Leftover After Geometry

只在 geometry gater 已验证后再尝试：

```bash
.venv/bin/python scripts/build_leftover_targets.py
.venv/bin/python scripts/train_residual_model.py --spec xgb_leftover --max-rows-per-well 0 --require-xgboost --max-iter 500
.venv/bin/python scripts/build_gated_stack.py
```

目标：

```text
leftover_target = truth_tvt - (baseline_tvt + geometry_oof_residual)
final_tvt = baseline_tvt + alpha * (geometry_residual + xgb_leftover_residual)
```

输出：

```text
features/leftover_targets.csv
outputs/residual_xgb_leftover_oof.csv
outputs/gated_geometry_plus_xgb_leftover_oof.csv
submissions/gated_geometry_plus_xgb_leftover_submission.csv
reports/gated_geometry_plus_xgb_leftover_cv_report.md
models/residual_xgb_leftover_config.json
```

若 stack OOF 不优于 `gated_geometry`，则不要把它选为最终候选。

### 7.3 保留对照: Direct XGBoost Full Residual

`--spec xgb` 仍保留，但只作为反面教材/对照，不是默认冲榜主线：

```bash
.venv/bin/python scripts/train_residual_model.py --spec xgb --max-rows-per-well 0 --require-xgboost --max-iter 500
```

用途：

- 对比 direct tree residual 与 geometry+gater 路线；
- 检查 fold 泛化问题；
- 当 geometry pipeline 异常时帮助定位问题。

### 7.3 XGBoost fallback 只用于实验

如果不加 `--require-xgboost`，脚本仍允许 fallback 到：

```text
sklearn.ensemble.HistGradientBoostingRegressor
```

这只能作为环境不完整时的实验，不应作为正式 leaderboard run。

### 7.4 下一步计划: Tree Residual 对照

部分已实现。

候选：

- HistGradientBoosting residual：已作为 xgb fallback 接入；
- LightGBM residual，如果环境允许；
- Ridge / ElasticNet 作为线性 sanity check。

统一要求：

- 同一 residual target；
- 同一 OOF split；
- 同一评估表；
- 有 test prediction；
- 有回退逻辑。

## 8. Step 4: Gated Residual

当前状态：

- 已实现 `scripts/build_gated_geometry.py`；
- 已实现 `scripts/train_learned_gater.py`；
- `gated_geometry` 是 per-well oracle alpha grid，会产出诊断上界；
- `learned_gated_geometry` 才是默认可提交候选：它用 train wells 学 alpha，再对 held-out wells / test wells 预测 alpha；
- candidate selection 默认排除 oracle / diagnostic-only 候选。

为什么 oracle OOF 会虚高：

- 它先看某口井的真实 TVT，选出这口井最优 alpha；
- 再用同一口井的 OOF rows 计算 RMSE；
- 这相当于“看过答案再调旋钮”，能说明这条路线的上限，但不能证明 test wells 会同样好。

目标公式：

```text
final_tvt = baseline_tvt + alpha * predicted_residual
```

输入可以包括：

```text
baseline_confidence
target_length
known_length
baseline_slope_std
predicted_residual_magnitude
GR_missing_rate
Part3_route
alignment_confidence
per_well_risk_score
```

输出应包括：

```text
alpha
gated_residual
final_tvt
gater_reason
```

验证：

- gated residual 是否优于 ungated residual；
- baseline-good wells 是否少被修坏；
- degraded wells 是否减少；
- P95/P99 是否改善。
- learned gater 必须用 GroupKFold / per-well OOF 验证，不能用同一口井真值先选 alpha 再评价同一口井。

失败时回退：

- 回退 ungated SGD/XGBoost residual；
- 或回退 baseline。

## 9. Step 5: GR / Typewell Alignment Enhanced Residual

当前状态：

- Part 3 diagnostics / route 已有；
- alignment features 的完整 correction 使用是计划中；
- 不能把 alignment offset 写成已完成最终模型。

计划目标：

```text
alignment features -> residual model
alignment confidence -> gater
alignment route -> candidate selection
```

关键字段：

```text
best_offset
best_similarity
second_best_similarity
similarity_margin
alignment_confidence
alignment_support_fraction
alignment_enabled_flag
```

验证：

- high confidence alignment subset 是否改善；
- best offset 方向是否和真实 residual 一致；
- alignment 加入 residual/gater 后是否减少 worst wells；
- OOF 不提升时不进入最终 correction。

失败时回退：

- 只保留 diagnostics / route；
- 不使用 alignment direct correction；
- final candidate 回退 residual 或 baseline。

## 10. Step 6: Candidate OOF Evaluation

当前已实现：

```bash
.venv/bin/python scripts/blend_predictions.py
.venv/bin/python scripts/select_submission_candidate.py --dry-run
```

会生成：

```text
submissions/conservative_submission.csv
submissions/balanced_submission.csv
submissions/aggressive_submission.csv
submissions/optimized_submission.csv
outputs/blend_oof.csv
outputs/ensemble_cv_summary.csv
outputs/ensemble_route_weights.csv
reports/ensemble_report.md
reports/candidate_selection_report.md
outputs/selected_candidate.json
```

当前候选包括：

- baseline；
- geometry residual；
- gated_geometry，oracle diagnostic only，默认不可自动提交；
- learned_gated_geometry，默认可自动提交；
- xgb/tree residual direct，如果已经生成 OOF；
- xgb_leftover；
- gated_geometry_plus_xgb_leftover，复用 oracle alpha，默认不可自动提交；
- conservative；
- balanced；
- aggressive；
- optimized。

重要提醒：

- 当前本地 OOF 最优的 `gated_geometry` 是 oracle 上界，不应默认提交；
- 默认选择应在 eligible candidates 里比较，例如 `learned_gated_geometry`、`geometry`、`optimized`、`xgb_leftover`；
- 不要因为 `balanced` 名字更像主力就默认选 balanced；
- stack 候选只有 OOF 真正更优、且不是 oracle / diagnostic-only 时才应被选中；
- 没有 OOF 或被标成 diagnostic-only 的候选不能进入正式 selection。

下一步计划：

- 把 gr/typewell residual 和 alignment-enhanced gater 接入；
- 把 candidate registry 从当前 JSON/report 扩展成正式 registry；
- 增加更严格的 smoothness guard。

## 11. Step 7: Candidate Selection

当前已实现：

```bash
.venv/bin/python scripts/select_submission_candidate.py --dry-run
.venv/bin/python scripts/make_submission.py --variant auto --output submission.csv
```

`--variant auto` 不会在 selector 失败时回退到旧的 ensemble summary。没有同一次 run 的完整 OOF 时，它会失败；这比悄悄导出旧候选更适合正式冲榜。

当前逻辑：

- 读取 baseline、geometry、xgb/tree、blend 和 postprocess candidate；
- 跳过缺 OOF、缺 submission 或 postprocess guard rejected 的候选；
- 跳过 `eligible_for_auto_submission=false` 的 oracle / diagnostic-only 候选；
- 每个候选先独立检查 OOF rows/wells 覆盖率，覆盖不足不能进入正式排名；
- 共同 `id` 覆盖只作为诊断报告，不默认拿小交集决定最终胜负；
- 默认按 OOF RMSE 最低选择；
- RMSE 很接近时，用 worst-well RMSE、degraded wells、P95 作为 tie breaker；
- 写出 `submission.csv`；
- 写出 `reports/candidate_selection_report.md` 和 `outputs/selected_candidate.json`；
- 记录到 `reports/submission_log.md`。

下一步计划：

```text
choose candidate with best validated OOF CV
check per-well degradation
check worst-well tail
check smoothness
then export final submission
```

失败时回退：

- 如果没有 CV summary，不能自信选择；
- 如果最优 candidate 风险过高，回退次优稳定候选；
- 如果所有 candidate 不完整，回退 baseline 或已验证的 SGD control。

## 12. Step 8: Postprocess With Guard

当前已实现：

全量入口 `scripts/run_part2_full_server.py` 在 candidate selection 之后会默认执行：

```bash
.venv/bin/python scripts/postprocess_predictions.py --variant auto
```

`make_submission.py` 默认 `--postprocess-policy auto`，**不会主动运行** postprocess；它只会复用同一次 run 中已经生成、且 guard 通过的 postprocessed submission。若要现场生成后处理产物，必须先单独执行上面的命令，或使用 `--postprocess-policy always`。

硬规则：

```text
if postprocess_rmse_after > postprocess_rmse_before:
    reject postprocessed submission
    use original candidate
```

`scripts/postprocess_predictions.py` 也支持：

```bash
--allow-worse
--min-improvement 0.0
```

默认 `--min-improvement 0.0`，也就是至少不能让 OOF RMSE 变差。脚本会额外写出：

```text
outputs/postprocess_oof_summary.csv
outputs/postprocess_oof_by_well.csv
```

当前报告已经证明 postprocess 可能变差：

```text
balanced OOF RMSE: 41.6539 -> 78.1925
```

所以不要用 `--postprocess-policy always` 或 `--allow-worse` 生成正式提交。

验证：

- 看 `reports/postprocess_report.md`；
- 确认 `Decision` 是 accepted 还是 rejected；
- 如果 rejected，最终文件应等价于原候选。

失败时回退：

- OOF 变差：自动回退；
- OOF 覆盖不足：回退；
- postprocess 只作为诊断，不作为最终能力宣传。

## 13. Step 9: Final Submission Validation

最终 `submission.csv` 必须满足：

```text
columns exactly: id,tvt
row count equals sample_submission
id order equals sample_submission
no duplicated id
no NaN / inf
tvt numeric
```

当前 visible test 行数是 `14,151`，但正式检查应该以本地 `sample_submission.csv` 为准，不要把这个数字写死到代码里。

如果需要单独验证，可用：

```bash
.venv/bin/python scripts/validate_submission.py --submission submission.csv
```

如果该脚本参数和当前实现不一致，以脚本 `--help` 为准。

## 14. 完成优化后的推荐全流程

当 gater / alignment-enhanced residual 也实现后，推荐全流程应是：

```text
1. data contract / EDA
2. baseline generation
3. baseline CV
4. feature build
5. residual candidates:
   - XGBoost full-row residual primary
   - SGD residual control
   - HistGradientBoosting residual fallback only for experiments
   - LightGBM residual if allowed
   - gated residual
   - GR/typewell alignment enhanced residual
6. candidate OOF evaluation
7. candidate selection
8. postprocess with guard
9. final submission export
10. submission validation
```

推荐选择规则：

```text
valid_candidates = candidates with:
  complete OOF
  complete test prediction
  no NaN / inf
  acceptable per-well risk
  acceptable worst-well tail
  postprocess not worse if used

selected = lowest OOF RMSE among valid_candidates
```

## 15. 交接时怎么说当前能力

可以说：

- 当前系统已经是 `baseline + residual correction`；
- 当前 residual backbone 是 `geometry SGD full-row`；
- `gated_geometry` 是 oracle diagnostic upper bound，默认不参与 auto selection；
- `learned_gated_geometry` 是当前推荐的可泛化 gater 候选；
- direct `--spec xgb` 仍保留为对照，不是默认冲榜主线；
- `xgb_leftover` 是 geometry 之后的可选 stack 层，需 OOF 验证；
- 当前 `scripts/select_submission_candidate.py` 已实现候选选择，先按各候选完整 OOF 覆盖过滤，再按 OOF 排序；共同 OOF 覆盖只作诊断；
- 当前 Part 3 能提供 route / diagnostics；
- 当前 Part 4 能生成多个候选并按 OOF 自动选；
- 当前 postprocess 有 `--min-improvement` guard。

不要说：

- `gated_geometry_plus_xgb_leftover` 一定优于 `gated_geometry`；
- alignment correction 已经是主模型；
- postprocess 一定提升；
- balanced 一定是最终主力。

## 16. 相关文档

- [`../plans/00_overview.md`](../plans/00_overview.md)
- [`../plans/02_residual_modeling.md`](../plans/02_residual_modeling.md)
- [`../plans/03_gr_typewell_alignment.md`](../plans/03_gr_typewell_alignment.md)
- [`../plans/04_ensemble_submission_ops.md`](../plans/04_ensemble_submission_ops.md)
- [`GITHUB_RUN_GUIDE.md`](GITHUB_RUN_GUIDE.md)
- [`part2_server_full_run_guide.md`](part2_server_full_run_guide.md)
