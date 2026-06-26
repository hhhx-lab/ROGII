# ROGII GitHub / 跑通入口

这是一份轻量入口文档。完整全量流程看：

- [`FULL_INFERENCE_GUIDE.md`](FULL_INFERENCE_GUIDE.md)
- [`part2_server_full_run_guide.md`](part2_server_full_run_guide.md)
- [`../plans/00_overview.md`](../plans/00_overview.md)

## 当前能直接跑什么

当前仓库可运行的是：

```text
baseline
  -> geometry full-row residual candidate
  -> direct XGBoost residual candidate
  -> Part 3 diagnostics / route
  -> optional oracle/learned gater diagnostics
  -> blend candidates
  -> select_submission_candidate.py
  -> postprocess_predictions.py --variant auto
  -> make_submission.py --variant auto
  -> validate_submission.py
```

最短导出命令：

```bash
.venv/bin/python scripts/blend_predictions.py
.venv/bin/python scripts/select_submission_candidate.py --dry-run
.venv/bin/python scripts/postprocess_predictions.py --variant auto
.venv/bin/python scripts/make_submission.py --variant auto --output submission.csv
.venv/bin/python scripts/validate_submission.py --submission submission.csv
```

前提是 baseline、residual、learned gater、Part 3 diagnostics、OOF 和 submission 产物已经由同一次有效 run 生成。如果 `learned_gated_geometry` 还没生成，auto selection 会跳过它，并在其他 eligible 候选里选择；如果没有完整 OOF，`--variant auto` 会失败，避免用旧 summary 悄悄导出提交。

## 正式 full run 前先归档旧产物

如果要生成正式 leaderboard submission，不要直接复用当前 `features/outputs/submissions/reports` 里的旧文件。旧 OOF、旧 submission 或旧 report 可能来自不同 run，会污染 `select_submission_candidate.py` 的自动选择。

训练前先把可再生成产物移动到：

```text
archive/runs/YYYYMMDD_HHMMSS_pre_full_run_cleanup/
```

可以归档：

```text
features/*.csv
features/*.parquet
outputs/*.csv
outputs/*.json
submissions/*.csv
submission.csv
run-generated reports
reports/figures/residual_geometry_*/
```

不能动：

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

恢复旧产物：

```bash
rsync -av archive/runs/<run_id>/ ./
```

完整规则见 [`FULL_INFERENCE_GUIDE.md`](FULL_INFERENCE_GUIDE.md) 的“训练前清理 / 旧产物归档规则”。

## 还没实现但计划实现什么

下面这些是计划，不要当成当前已完成能力：

- GR/typewell alignment-enhanced residual；
- LightGBM residual 对照；
- 更正式的 candidate registry 和 smoothness guard。

## 运行时记住三点

- 原始数据优先放 `data/train` / `data/test`，旧布局 `data/raw/train` / `data/raw/test` 也兼容。
- 当前主线是 `baseline + residual correction`，不是直接预测绝对 TVT。
- 默认 full run 会并列训练 `geometry` residual 和 direct `xgb` residual，二者使用同一个 `residual_target = truth_tvt - baseline_tvt`。
- `gated_geometry` 是 oracle / diagnostic upper bound，默认不允许 auto selection 选它；`learned_gated_geometry` 可保留为可泛化候选。
- `xgb_leftover` / `gated_geometry_plus_xgb_leftover` 是历史/诊断路线，默认不训练、不选择。
- 不要用缺 `xgboost` 时的 HistGradientBoosting fallback 当正式 leaderboard run；正式 direct xgb 必须 `--require-xgboost`。
- 最终提交必须先检查各候选 OOF 覆盖率和 `eligible_for_auto_submission`；共同 OOF 覆盖只作诊断，不用小交集决定最终胜负。
- postprocess 只有满足 `--min-improvement` guard 时才允许使用。
- 全量入口 `scripts/run_part2_full_server.py` 每次都会写 `reports/server_part2_full_run_config.md/json`，先看配置快照再解释结果。

当前 smoke test：

```bash
.venv/bin/python -m py_compile scripts/train_learned_gater.py scripts/select_submission_candidate.py scripts/make_submission.py scripts/run_part2_full_server.py
.venv/bin/python scripts/select_submission_candidate.py --dry-run
.venv/bin/python scripts/run_part2_full_server.py --dry-run --skip-package
```

只有在同一次 run 的完整 OOF 和 selected candidate 已经生成后，才把 `make_submission.py --variant auto` 和 `validate_submission.py` 作为提交前检查。

文档、plan 和 run guide 后续都放在 `docs/` 下维护，不再新增根目录跳转占位文档。
