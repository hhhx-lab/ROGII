# ROGII 全量推理指南

这份指南说明：如果你要从原始比赛数据一路跑到最终 `submission.csv`，应该怎么做。

## 1. 目标

目标是生成一个可提交的 `submission.csv`：

- 列必须是 `id,tvt`
- 行数必须和 `data/sample_submission.csv` 一致
- `id` 顺序必须和样例完全一致

## 2. 数据放置

把比赛数据放到仓库的 `data/` 下：

```text
data/
|-- train/
|-- test/
`-- sample_submission.csv
```

如果你是旧目录，也可以兼容 `data/raw/`，但当前推荐直接用 `data/`。

## 3. 推荐环境

推荐用这个环境跑：

```bash
conda run -n py3.9 python ...
```

这个环境里需要：

- `numpy`
- `pandas`
- `scikit-learn`

## 4. 全量流程

按这个顺序跑。

### 4.1 先做数据检查和 EDA

```bash
conda run -n py3.9 python scripts/run_eda.py
```

这会生成：

- `reports/eda_summary.md`

### 4.2 跑 baseline

```bash
conda run -n py3.9 python scripts/baseline_tail_slope.py
```

这会生成：

- `submissions/baseline_tail_slope_submission.csv`
- `reports/baseline_report.md`

然后做 baseline 的 CV：

```bash
conda run -n py3.9 python scripts/evaluate_baseline_cv.py
```

这会生成：

- `outputs/baseline_cv_by_well.csv`
- `reports/baseline_cv_report.md`

### 4.3 生成特征

如果你要重跑全量特征，顺序一般是：

```bash
conda run -n py3.9 python scripts/build_baseline_features.py
conda run -n py3.9 python scripts/build_geometry_features.py
conda run -n py3.9 python scripts/build_part3_features.py
conda run -n py3.9 python scripts/build_part3_diagnostics.py
```

这些脚本会更新：

- `features/*.csv`
- `outputs/part3_diagnostics.csv`

### 4.4 训练 residual 模型

```bash
conda run -n py3.9 python scripts/train_residual_model.py --spec all
```

这会生成：

- `outputs/residual_geometry_oof.csv`
- `outputs/residual_gr_oof.csv`
- `outputs/residual_typewell_oof.csv`
- `outputs/residual_geometry_test_predictions.csv`
- `outputs/residual_gr_test_predictions.csv`
- `outputs/residual_typewell_test_predictions.csv`
- `reports/residual_*_cv_report.md`
- `models/residual_*`

### 4.5 做融合和后处理

先做 blend：

```bash
conda run -n py3.9 python scripts/blend_predictions.py
```

这会生成：

- `submissions/conservative_submission.csv`
- `submissions/balanced_submission.csv`
- `submissions/aggressive_submission.csv`
- `outputs/blend_oof.csv`
- `outputs/blend_cv_by_well.csv`

再做后处理：

```bash
conda run -n py3.9 python scripts/postprocess_predictions.py --variant balanced
```

最后生成提交文件：

```bash
conda run -n py3.9 python scripts/make_submission.py --variant balanced --output submission.csv
```

## 5. 最终成功标志

最终你要检查：

- `submission.csv` 存在
- `submission.csv` 只有 `id,tvt`
- `submission.csv` 和 `sample_submission.csv` 行数一致
- `id` 顺序一致
- `tvt` 全是有效数字

## 6. 这套全量流程的逻辑

这套流程是：

```text
数据检查
  -> baseline
  -> baseline CV
  -> feature build
  -> residual training
  -> blend
  -> postprocess
  -> final submission
```

它不是“随便跑几个模型”，而是每一步都要有前一步的输出作为依据。

## 7. 常见失败点

### 7.1 依赖缺失

如果报 `ModuleNotFoundError`，说明当前环境没装依赖。换到 `py3.9`，或者先装 `requirements.txt`。

### 7.2 某个脚本找不到文件

说明上一步没有跑完，或者数据目录不对。先检查：

- `data/`
- `features/`
- `outputs/`
- `models/`

### 7.3 最终提交顺序不对

说明生成 `submission.csv` 时没有按 `sample_submission.csv` 的 `id` 顺序输出。

## 8. 你当前仓库里的现状

目前仓库已经有这些现成产物：

- `data/train/`
- `data/test/`
- `features/*.csv`
- `outputs/*.csv`
- `submissions/*.csv`
- `models/residual_geometry_hgb.pkl`

所以如果你只是想先验证提交链路，直接跑：

```bash
conda run -n py3.9 python scripts/make_submission.py --variant balanced --output submission.csv
```

