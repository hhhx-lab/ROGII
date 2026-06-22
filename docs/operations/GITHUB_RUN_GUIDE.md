# ROGII GitHub / 跑通入口

这是一份轻量入口文档。完整全量流程看：

- [`FULL_INFERENCE_GUIDE.md`](FULL_INFERENCE_GUIDE.md)
- [`part2_server_full_run_guide.md`](part2_server_full_run_guide.md)
- [`../plans/00_overview.md`](../plans/00_overview.md)

## 当前能直接跑什么

当前仓库可运行的是：

```text
baseline
  -> SGD residual
  -> optional XGBoost/tree residual
  -> Part 3 diagnostics / route
  -> blend candidates
  -> select_submission_candidate.py
  -> make_submission.py --variant auto
```

最短导出命令：

```bash
.venv/bin/python scripts/blend_predictions.py
.venv/bin/python scripts/select_submission_candidate.py --dry-run
.venv/bin/python scripts/make_submission.py --variant auto --output submission.csv
```

前提是 baseline、residual 和 Part 3 diagnostics 产物已经由同一次有效 run 生成。

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

- 独立 gated residual；
- GR/typewell alignment-enhanced residual；
- LightGBM residual 对照；
- 更正式的 candidate registry 和 smoothness guard。

## 运行时记住三点

- 原始数据优先放 `data/train` / `data/test`，旧布局 `data/raw/train` / `data/raw/test` 也兼容。
- 当前 SGD residual 是主控制模型；`--spec xgb` 已支持 XGBoost/tree residual，缺 `xgboost` 时 fallback 到 HistGradientBoosting。
- 最终提交必须按共同 OOF 覆盖选择；postprocess 只有满足 `--min-improvement` guard 时才允许使用。

当前 smoke test：

```bash
.venv/bin/python -m py_compile scripts/train_residual_model.py scripts/postprocess_predictions.py scripts/select_submission_candidate.py scripts/validate_part2_outputs.py
.venv/bin/python scripts/select_submission_candidate.py --dry-run
.venv/bin/python scripts/make_submission.py --variant auto --output submission.csv
.venv/bin/python scripts/validate_submission.py --submission submission.csv
```

文档、plan 和 run guide 后续都放在 `docs/` 下维护，不再新增根目录跳转占位文档。
