# ROGII 本地跑通指南

这份指南用来说明：在本仓库里，怎么从已有数据和现成产物，最小跑通一次最终提交生成。

## 1. 你需要什么

- Python 环境里有 `numpy`、`pandas`、`scikit-learn`
- 训练数据放在 `data/train/`
- 测试数据放在 `data/test/`
- `data/sample_submission.csv` 可用

推荐先建一个本地虚拟环境：

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 2. 最小跑通目标

只验证一条链路：

```text
现成的 baseline / residual / postprocess 产物
  -> 生成最终 submission.csv
```

这一步不训练模型，不重建特征，只检查提交生成链路是否正常。

## 3. 先检查文件

确认这些文件存在：

- `outputs/baseline_predictions_test.csv`
- `outputs/residual_geometry_test_predictions.csv`
- `outputs/part3_diagnostics.csv`
- `outputs/baseline_predictions_train_hidden.csv`
- `outputs/residual_geometry_oof.csv`

## 4. 运行命令

推荐用仓库内的 `.venv`：

```bash
.venv/bin/python scripts/make_submission.py --variant balanced --output submission.csv
```

如果你想先做一个临时验证，可以把输出放到别的路径：

```bash
.venv/bin/python scripts/make_submission.py --variant balanced --output /tmp/rogii_submission.csv
```

## 5. 成功标志

命令结束后会看到类似：

```text
Wrote final submission to ...
```

然后检查输出文件：

- 列必须是 `id,tvt`
- 行数必须和 `data/sample_submission.csv` 一致
- `id` 顺序必须完全一致
- `tvt` 不能有空值

## 6. 常见问题

### `ModuleNotFoundError: numpy` / `pandas` / `sklearn`

说明你用的 Python 环境没装依赖。换到有依赖的环境，或者先安装 `requirements.txt` 里的包。

### `Missing baseline_tvt column`

说明 `outputs/baseline_predictions_test.csv` 缺失，或者格式不对。

### `submission ids are not in the same order as sample submission`

说明生成的提交文件顺序错了。这个仓库的最终提交必须严格按 `sample_submission.csv` 的顺序输出。

## 7. 这条链路现在代表什么

这不是完整训练流程，只是最小可跑通验证。

完整流程以后再按下面顺序跑：

```text
EDA
  -> baseline CV
  -> feature build
  -> residual training
  -> blend
  -> postprocess
  -> final submission
```
