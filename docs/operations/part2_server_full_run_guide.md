# Part 2 服务器全量复跑傻瓜式操作手册

本文档给第一次接手项目的同学使用。目标是：把现有 GitHub 代码和 Kaggle 数据放到服务器上，完整复跑 Part 2 的 full-row residual 模型，打包输出，再把结果拿回本地。

你不需要理解所有模型细节。只要严格按顺序操作，最后看到 `checks=34 failures=0`，并把 `packages/part2_server_outputs_*.tar.gz` 拿回来即可。

## 0. 这次要跑什么

Part 2 的模型形式是：

```text
prediction = continuity_baseline + residual_model(features)
```

服务器要做的是把本机采样训练版放大成 full-row 训练版：

```bash
ROGII_PART2_TRAIN_ROWS_PER_WELL=0
ROGII_PART2_MAX_ITER=500
ROGII_PART2_MULTIMASK_TRAIN_ROWS_PER_WELL=0
ROGII_PART2_MULTIMASK_MAX_ITER=500
```

其中 `0` 表示每口井不再采样，训练时使用全部可用 target rows。

## 1. 最终你要交回什么

服务器跑完以后，请交回以下两个文件：

```text
packages/part2_server_outputs_YYYYMMDD_HHMMSS.tar.gz
packages/part2_server_outputs_YYYYMMDD_HHMMSS.tar.gz.sha256
```

这个包里会包含：

- `models/residual_geometry_hgb.pkl`
- `models/residual_geometry_config.json`
- `outputs/residual_geometry_oof.csv`
- `outputs/residual_geometry_cv_by_well.csv`
- `outputs/residual_geometry_test_predictions.csv`
- `outputs/residual_geometry_multimask_overall.csv`
- `outputs/residual_geometry_multimask_by_split.csv`
- `reports/residual_geometry_cv_report.md`
- `reports/residual_geometry_multimask_report.md`
- `reports/part2_completion_audit.md`
- `submissions/geometry_residual_submission.csv`
- 诊断图片和运行日志

默认不会把 `data/raw/`、`features/*.parquet` 和 Part 1 的 2.7GB 大 CSV 打包回来，避免包太大。需要这些文件时再用脚本参数单独加。

## 2. 服务器建议配置

最低能跑不等于推荐。为了少踩坑，建议：

| 项 | 建议 |
|---|---|
| 系统 | Linux |
| CPU | 16 核以上更好 |
| 内存 | 64GB 以上推荐，32GB 可能能跑但风险较高 |
| 磁盘 | 至少 80GB 可用空间 |
| Python | Conda 环境，Python 3.11 或 3.12 |
| 网络 | 能访问 GitHub；数据可以用 scp/rsync 从本地传上去 |

不要使用 `sudo pip`。不要混用系统 Python、Homebrew Python 和 Conda 环境。

## 3. 你需要提前准备

本地需要有：

```text
data/raw/
|-- sample_submission.csv
|-- AI_wellbore_geology_prediction_task_en.pptx
|-- train/
`-- test/
```

服务器需要能访问这个仓库：

```text
git@github.com:hhhx-lab/ROGII.git
```

如果服务器没有 Kaggle 登录，不要紧，直接从本地把 `data/raw/` 传上去即可。

## 4. 登录服务器

在本地终端执行：

```bash
ssh <用户名>@<服务器地址>
```

示例：

```bash
ssh ubuntu@1.2.3.4
```

进入服务器以后，建议先开一个 `tmux`，防止 SSH 断开导致任务中断：

```bash
tmux new -s rogii-part2
```

如果你中途断线了，重新登录服务器后执行：

```bash
tmux attach -t rogii-part2
```

## 5. 在服务器拉代码

选择一个空间比较大的目录，例如：

```bash
mkdir -p ~/projects
cd ~/projects
```

克隆代码：

```bash
git clone git@github.com:hhhx-lab/ROGII.git
cd ROGII
```

确认当前分支和代码：

```bash
git status -sb
git log -1 --oneline
```

应该看到类似：

```text
## main...origin/main
8c7e477 [docs] 更新第二部分完成审计状态
```

如果显示的是更新的提交，也可以；关键是服务器代码必须来自 `origin/main` 的最新版本。

后续如果仓库有更新，在服务器项目目录执行：

```bash
git pull origin main
```

## 6. 创建 Conda 环境

确认服务器有 Conda：

```bash
conda --version
```

创建环境：

```bash
conda create -n rogii-part2 python=3.11 -y
conda activate rogii-part2
```

安装依赖：

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

确认 Python 位置：

```bash
which python
python --version
```

`which python` 应该指向 Conda 环境，不应该是 `/usr/bin/python`。

## 7. 把数据放到服务器

### 方案 A：从本地直接传 `data/raw/`

在本地开一个新终端，不要在服务器终端里执行下面这条。

假设服务器项目路径是：

```text
/home/ubuntu/projects/ROGII
```

本地项目路径是：

```text
/Users/hwaigc/太空垃圾站/ROG II地质勘测
```

从本地执行：

```bash
rsync -avP "data/raw/" <用户名>@<服务器地址>:/home/ubuntu/projects/ROGII/data/raw/
```

示例：

```bash
rsync -avP "data/raw/" ubuntu@1.2.3.4:/home/ubuntu/projects/ROGII/data/raw/
```

如果没有 `rsync`，用 `scp`：

```bash
scp -r "data/raw" ubuntu@1.2.3.4:/home/ubuntu/projects/ROGII/data/
```

### 方案 B：服务器上用 Kaggle 下载

只有服务器已经配置好 Kaggle API 时才用这个方案。

```bash
kaggle competitions download -c rogii-wellbore-geology-prediction -p data
unzip data/rogii-wellbore-geology-prediction.zip -d data/raw
```

如果 Kaggle 权限、cookies 或账号规则没配置好，直接用方案 A。

## 8. 做服务器预检

回到服务器 tmux 窗口，确认在项目根目录：

```bash
cd ~/projects/ROGII
conda activate rogii-part2
```

执行预检：

```bash
python scripts/server_part2_preflight.py
```

成功时会看到类似：

```text
Wrote reports/server_part2_preflight_report.md
checks=... failures=0 warnings=...
Preflight passed. Warnings are allowed unless --strict is used.
```

如果出现 `failures>0`，先打开报告看原因：

```bash
sed -n '1,220p' reports/server_part2_preflight_report.md
```

常见失败：

| 问题 | 处理 |
|---|---|
| `data/raw` 不存在 | 重新传数据 |
| train 文件不是 773 个 | 数据没传完整，重新 `rsync -avP` |
| sample rows 不是 14151 | `sample_submission.csv` 不对，重新传 |
| 缺 `pyarrow` / `sklearn` | 重新 `python -m pip install -r requirements.txt` |

## 9. 先看一键脚本会跑哪些步骤

建议先 dry run：

```bash
python scripts/run_part2_full_server.py --dry-run
```

它不会真的训练，只会打印计划执行的步骤。正常会包括：

1. `server_part2_preflight.py`
2. `check_data_contract.py`
3. `evaluate_baseline_cv.py`
4. `make_cv_splits.py`
5. `evaluate_baseline_multimask.py`
6. `build_baseline_features.py`
7. `build_geometry_features.py`
8. `train_residual_model.py`
9. `evaluate_model_cv.py`
10. `evaluate_residual_multimask.py`
11. `validate_part2_outputs.py`
12. `package_part2_server_outputs.py`

## 10. 开始正式全量跑 Part 2

在服务器 tmux 里执行：

```bash
python scripts/run_part2_full_server.py
```

这条命令默认就是 full-row 配置：

```text
ROGII_PART2_TRAIN_ROWS_PER_WELL=0
ROGII_PART2_MAX_ITER=500
ROGII_PART2_MULTIMASK_TRAIN_ROWS_PER_WELL=0
ROGII_PART2_MULTIMASK_MAX_ITER=500
```

所有日志会自动写到：

```text
reports/server_part2_full_run_logs/
```

总摘要会写到：

```text
reports/server_part2_full_run_summary.md
reports/server_part2_full_run_summary.json
```

如果你不想用 tmux，也可以用 `nohup`：

```bash
nohup python scripts/run_part2_full_server.py > server_part2.nohup.log 2>&1 &
```

查看进度：

```bash
tail -f server_part2.nohup.log
```

但更推荐 tmux。

## 11. 怎么判断跑完了

跑完以后，终端最后应该看到：

```text
Wrote reports/server_part2_full_run_summary.md
Wrote reports/server_part2_full_run_summary.json
```

再执行：

```bash
python scripts/validate_part2_outputs.py
```

必须看到：

```text
checks=34 failures=0
```

然后查看核心报告：

```bash
sed -n '1,180p' reports/residual_geometry_cv_report.md
sed -n '1,120p' reports/residual_geometry_multimask_report.md
sed -n '1,120p' reports/part2_completion_audit.md
```

重点看：

- `Promotion decision`
- overall RMSE 是否比 baseline 低；
- multi-mask 各类 `rmse_improvement` 是否正常；
- `part2_completion_audit.md` 是否为 `PASS`。

## 12. 如果服务器太慢或内存不够

如果 full-row 训练失败，可以先跑一个服务器中等版确认链路：

```bash
python scripts/run_part2_full_server.py \
  --train-rows-per-well 1200 \
  --max-iter 300 \
  --multimask-train-rows-per-well 1200 \
  --multimask-max-iter 300
```

注意：这个只是服务器烟测或中等版，不是最终 full-row 结果。

如果只想跳过最重的 residual multi-mask：

```bash
python scripts/run_part2_full_server.py --skip-residual-multimask
```

但正式进入 Part 3 前，最好还是补跑 full residual multi-mask。

## 13. 打包服务器输出

如果你是用 `scripts/run_part2_full_server.py` 跑的，最后会自动打包。

如果需要手动重新打包：

```bash
python scripts/package_part2_server_outputs.py
```

成功时会看到：

```text
Wrote packages/part2_server_outputs_YYYYMMDD_HHMMSS.tar.gz
Wrote packages/part2_server_outputs_YYYYMMDD_HHMMSS.tar.gz.sha256
package_sha256=...
```

如果还想把 `features/*.parquet` 也打包回来：

```bash
python scripts/package_part2_server_outputs.py --include-features
```

一般不建议加 `--include-features`，除非明确需要在本地继续用这些特征。

## 14. 从服务器把输出拿回本地

在本地开一个新终端执行。

示例服务器路径：

```text
/home/ubuntu/projects/ROGII/packages/
```

本地项目路径：

```text
/Users/hwaigc/太空垃圾站/ROG II地质勘测
```

进入本地项目：

```bash
cd "/Users/hwaigc/太空垃圾站/ROG II地质勘测"
mkdir -p packages
```

复制包：

```bash
scp ubuntu@1.2.3.4:/home/ubuntu/projects/ROGII/packages/part2_server_outputs_*.tar.gz packages/
scp ubuntu@1.2.3.4:/home/ubuntu/projects/ROGII/packages/part2_server_outputs_*.tar.gz.sha256 packages/
```

或者用 `rsync`：

```bash
rsync -avP ubuntu@1.2.3.4:/home/ubuntu/projects/ROGII/packages/part2_server_outputs_*.tar.gz packages/
rsync -avP ubuntu@1.2.3.4:/home/ubuntu/projects/ROGII/packages/part2_server_outputs_*.tar.gz.sha256 packages/
```

## 15. 本地检查拿回来的包

本地执行：

```bash
python scripts/inspect_part2_server_package.py packages/part2_server_outputs_YYYYMMDD_HHMMSS.tar.gz
```

应该看到：

```text
missing_required_members=0
Inspection passed.
```

如果要解压查看：

```bash
mkdir -p server_results/part2_full
python scripts/inspect_part2_server_package.py \
  packages/part2_server_outputs_YYYYMMDD_HHMMSS.tar.gz \
  --extract-to server_results/part2_full
```

解压后查看：

```bash
sed -n '1,180p' server_results/part2_full/reports/residual_geometry_cv_report.md
sed -n '1,120p' server_results/part2_full/reports/residual_geometry_multimask_report.md
sed -n '1,120p' server_results/part2_full/reports/part2_completion_audit.md
```

## 16. 是否要覆盖本地 outputs/models/reports

默认不要急着覆盖本地目录。先把服务器结果放在：

```text
server_results/part2_full/
```

确认服务器结果更好、更完整，再决定是否同步回本地工作区。

如果确认要覆盖本地 ignored artifacts，可以执行：

```bash
rsync -av server_results/part2_full/outputs/ outputs/
rsync -av server_results/part2_full/models/ models/
rsync -av server_results/part2_full/reports/ reports/
rsync -av server_results/part2_full/submissions/ submissions/
```

注意：`outputs/` 是 ignored，正常不会进 git。`reports/`、`models/`、`submissions/` 里如果有需要保留的服务器最终结果，再单独提交。

## 17. 失败后怎么处理

### SSH 断了

如果用的是 tmux：

```bash
ssh <用户名>@<服务器地址>
tmux attach -t rogii-part2
```

### 磁盘满了

查看空间：

```bash
df -h
du -sh data features outputs reports models packages
```

可以删除旧包：

```bash
rm -f packages/part2_server_outputs_*.tar.gz
rm -f packages/part2_server_outputs_*.tar.gz.sha256
```

不要删除 `data/raw/`，除非你准备重新传数据。

### Python 包缺失

```bash
conda activate rogii-part2
python -m pip install -r requirements.txt
```

### 内存不够

先跑中等版确认链路：

```bash
python scripts/run_part2_full_server.py \
  --train-rows-per-well 1200 \
  --max-iter 300 \
  --multimask-train-rows-per-well 1200 \
  --multimask-max-iter 300
```

然后把报错日志和 summary 拿回来：

```text
reports/server_part2_full_run_summary.md
reports/server_part2_full_run_logs/
```

### 某一步失败了

打开 summary：

```bash
sed -n '1,220p' reports/server_part2_full_run_summary.md
```

找到失败步骤对应 log，例如：

```bash
sed -n '1,240p' reports/server_part2_full_run_logs/20260620_120000_08_part2_full_residual_training.log
```

把这个 log 发回来，不要只截图最后一行。

## 18. 禁止事项

- 不要把 `data/raw/` 上传到 GitHub。
- 不要把 `outputs/*.csv` 大文件上传到 GitHub。
- 不要使用 `sudo pip`。
- 不要在系统 Python 里安装依赖。
- 不要随手改 `.gitignore` 来强行提交数据。
- 不要用 notebook 手动改模型参数后不记录。

## 19. 新手检查清单

跑之前：

- [ ] 已进入 tmux。
- [ ] 已 `git clone` 或 `git pull origin main`。
- [ ] 已 `conda activate rogii-part2`。
- [ ] 已 `python -m pip install -r requirements.txt`。
- [ ] `data/raw/train` 有 773 个 horizontal well CSV。
- [ ] `data/raw/test` 有 3 个 horizontal well CSV。
- [ ] `python scripts/server_part2_preflight.py` 没有 failure。

跑的时候：

- [ ] 使用 `python scripts/run_part2_full_server.py`。
- [ ] 不关闭 tmux 窗口。
- [ ] 日志在 `reports/server_part2_full_run_logs/`。

跑完之后：

- [ ] `python scripts/validate_part2_outputs.py` 输出 `checks=34 failures=0`。
- [ ] `reports/residual_geometry_cv_report.md` 已更新。
- [ ] `reports/residual_geometry_multimask_report.md` 已更新。
- [ ] `packages/part2_server_outputs_*.tar.gz` 已生成。
- [ ] `.sha256` 文件已生成。
- [ ] 已把 tar.gz 和 sha256 拿回本地。
- [ ] 本地 `scripts/inspect_part2_server_package.py` 检查通过。
