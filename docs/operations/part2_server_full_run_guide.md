# Part 2 服务器全量复跑新手手册

这份手册是写给第一次接手这个项目的人看的。目标很简单：

1. 在服务器上把代码、数据、环境准备好
2. 从干净状态重新跑一遍 Part 2 的 full-row residual 训练
3. 把结果打包拿回本地
4. 记录这次跑出来的关键结果，方便后续进入 Part 3

当前仓库里 Part 1 已经通过审计，可以保留为稳定地基。Part 2 这条线之前的旧结果已经清理掉了，所以这次服务器复跑出来的结果会是新的准基线。不要拿旧报告当最终版。

## 你先看懂这几件事

- Part 2 不是在 Kaggle Notebook 里从零训练，而是在服务器上先把重活跑完。
- Kaggle Notebook 最后只负责轻量推理、后处理和导出 `submission.csv`。
- 本手册全程只用项目里的 `.venv`，不要再混用 Conda、系统 Python、Homebrew Python 或 `sudo pip`。
- 这次的“旧结果清理”是为了避免把以前的 `models/`、`outputs/`、`reports/` 误当成当前结果。

## 0. 先归档旧结果，不要直接删除

如果你本地工作区里还残留 Part 2 或 full run 旧产物，先移动到 `archive/`，再开始新跑。不要用 `rm` 或 `find ... -delete` 直接删旧结果，因为后面可能需要恢复、对比或排查。

推荐归档目录：

```text
archive/runs/YYYYMMDD_HHMMSS_pre_full_run_cleanup/
```

旧产物主要包括：

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

不要移动这些东西：

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

推荐流程：

1. 先看状态：

```bash
git status --short --branch
du -sh data features outputs submissions reports .venv 2>/dev/null
git status --short --ignored
```

2. 建归档目录并移动旧产物，保持相对路径结构：

```bash
mkdir -p archive/runs/<timestamp>_pre_full_run_cleanup
```

3. 写 `cleanup_manifest.json` 和 `cleanup_manifest.md`，记录移动了什么、总大小、git branch、HEAD commit 和恢复命令。

4. 清理后确认占位文件和原始数据还在：

```bash
find features -maxdepth 1 -type f | sort
find outputs -maxdepth 1 -type f | sort
find submissions -maxdepth 1 -type f | sort
test -d data/train
test -d data/test
```

恢复方式：

```bash
rsync -av archive/runs/<run_id>/ ./
```

完整规则见 [`FULL_INFERENCE_GUIDE.md`](FULL_INFERENCE_GUIDE.md) 的“训练前清理 / 旧产物归档规则”。

## 1. 服务器上要准备什么

你需要一台 Linux 服务器，建议至少：

| 项 | 建议 |
|---|---|
| CPU | 16 核以上 |
| 内存 | 64 GB 以上更稳 |
| 磁盘 | 至少 80 GB 可用空间 |
| Python | 3.11 或 3.12 |
| 网络 | 能访问 GitHub，最好也能 scp/rsync 传文件 |

如果服务器已经有 Python 3.11/3.12，就直接用它创建 `.venv`。如果只有 `python3.11` 或 `python3.12`，也可以直接用那个命令。

## 2. 登录服务器

在本地终端连服务器：

```bash
ssh <用户名>@<服务器地址>
```

建议进去后先开 `tmux`，这样 SSH 断了也不会中断任务：

```bash
tmux new -s rogii-part2
```

以后重新连上服务器，用：

```bash
tmux attach -t rogii-part2
```

## 3. 拉代码

先找一个工作目录，比如：

```bash
mkdir -p ~/projects
cd ~/projects
git clone git@github.com:hhhx-lab/ROGII.git
cd ROGII
```

如果仓库已经存在，就直接更新：

```bash
git pull origin main
```

确认你在 `main` 分支，并且代码是最新的：

```bash
git status -sb
git log -1 --oneline
```

## 4. 建虚拟环境

先看 Python 版本：

```bash
python3 --version
```

如果 `python3` 版本是 3.11 或 3.12，就直接建环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

如果服务器上 `python3` 不是 3.11/3.12，而是别的版本，就改用对应的可用命令，比如：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

确认现在用的是 `.venv`：

```bash
which python
python --version
```

`which python` 应该指向 `.venv/bin/python`。

## 5. 把数据传到服务器

推荐从本地直接传当前使用的数据目录。新口径优先支持：

```text
data/train/
data/test/
data/sample_submission.csv   # 可选；缺失时脚本会从 test hidden rows 合成 id
```

旧布局 `data/raw/train` / `data/raw/test` 仍然兼容。下面以旧布局为例，本地另开一个终端，执行：

```bash
rsync -avP "data/raw/" <用户名>@<服务器地址>:/home/<用户名>/projects/ROGII/data/raw/
```

如果你不知道服务器上的项目路径，就先手动建好再传：

```bash
mkdir -p /home/<用户名>/projects/ROGII/data/raw/
```

如果没有 `rsync`，可以用 `scp`：

```bash
scp -r "data/raw" <用户名>@<服务器地址>:/home/<用户名>/projects/ROGII/data/
```

如果服务器已经配置好了 Kaggle API，也可以在服务器上下载，但对新手来说，直接从本地传数据最稳。

数据传完以后，检查这几个东西：

```text
data/raw/train/
data/raw/test/
data/raw/sample_submission.csv                  # 可选
data/raw/AI_wellbore_geology_prediction_task_en.pptx  # 可选
```

## 6. 先做预检

回到服务器的 `tmux` 窗口，进入项目根目录：

```bash
cd ~/projects/ROGII
source .venv/bin/activate
```

先跑预检：

```bash
.venv/bin/python scripts/server_part2_preflight.py
```

成功时应该看到类似：

```text
Wrote reports/server_part2_preflight_report.md
checks=... failures=0 warnings=...
Preflight passed. Warnings are allowed unless --strict is used.
```

如果这里失败了，先看报告：

```bash
sed -n '1,220p' reports/server_part2_preflight_report.md
```

常见问题：

| 现象 | 处理 |
|---|---|
| `data/raw` 不存在 | 数据没传对，重新 rsync/scp |
| train 数量不是 773 | 数据缺文件，重新传 |
| sample rows 不是 14151 | `sample_submission.csv` 不对 |
| 缺 `pyarrow` / `sklearn` | 重新 `python -m pip install -r requirements.txt` |

## 7. 先看 dry run

正式开跑前，先看脚本打算做什么：

```bash
.venv/bin/python scripts/run_part2_full_server.py --dry-run
```

这个命令不训练，只打印步骤。它会告诉你脚本会按什么顺序跑：

1. 预检
2. 数据契约检查
3. Part 1 baseline CV
4. 生成 CV splits
5. baseline 多 mask 检查
6. 生成 baseline 特征
7. 生成 geometry 特征
8. 训练 residual
9. 跑 residual CV
10. 跑 residual 多 mask（geometry control 才需要）
11. 做 Part 2 最终审计
12. 打包服务器结果

如果 dry run 打印的步骤看起来合理，再进入正式运行。

## 8. 正式全量跑 Part 2

在服务器 `tmux` 里执行：

```bash
.venv/bin/python scripts/run_part2_full_server.py
```

这个命令默认就是 full-row 的 XGBoost 主线配置，也就是：

```text
--residual-spec xgb
--train-rows-per-well 0
--min-fit-fraction 0.95
--max-iter 500
--require-xgboost
```

并且训练入口会要求 `xgboost` 可用；如果环境里没有 `xgboost`，会直接失败，而不是静默回退到 sklearn fallback。

如果你担心 SSH 断开，也可以用：

```bash
nohup .venv/bin/python scripts/run_part2_full_server.py > server_part2.nohup.log 2>&1 &
```

但新手更推荐 `tmux`，因为它更容易看日志。

运行时日志会写到：

```text
reports/server_part2_full_run_logs/
```

总摘要会写到：

```text
reports/server_part2_full_run_summary.md
reports/server_part2_full_run_summary.json
```

## 9. 跑完后看什么

跑完以后，先看 summary：

```bash
sed -n '1,220p' reports/server_part2_full_run_summary.md
```

再做最终验证：

```bash
.venv/bin/python scripts/validate_part2_outputs.py
```

必须看到：

```text
checks=34 failures=0
```

然后看这几个报告：

```bash
sed -n '1,180p' reports/residual_geometry_cv_report.md
sed -n '1,120p' reports/residual_geometry_multimask_report.md
sed -n '1,120p' reports/part2_completion_audit.md
```

你要确认的重点不是“有没有文件”，而是：

- residual 是否比 baseline 更好
- multi-mask 是否都能工作
- 审计是否还是 `PASS`

## 10. 打包结果

验证没问题后，打包服务器结果：

```bash
.venv/bin/python scripts/package_part2_server_outputs.py
```

成功后会生成：

```text
packages/part2_server_outputs_YYYYMMDD_HHMMSS.tar.gz
packages/part2_server_outputs_YYYYMMDD_HHMMSS.tar.gz.sha256
```

如果你想把特征也一起带回来，可以加：

```bash
.venv/bin/python scripts/package_part2_server_outputs.py --include-features
```

一般不建议一开始就带特征，包会很大。

## 11. 把结果带回本地

在本地开一个新终端，把包拿回来：

```bash
mkdir -p packages
scp <用户名>@<服务器地址>:/home/<用户名>/projects/ROGII/packages/part2_server_outputs_*.tar.gz packages/
scp <用户名>@<服务器地址>:/home/<用户名>/projects/ROGII/packages/part2_server_outputs_*.tar.gz.sha256 packages/
```

或者用 `rsync`：

```bash
rsync -avP <用户名>@<服务器地址>:/home/<用户名>/projects/ROGII/packages/part2_server_outputs_*.tar.gz packages/
rsync -avP <用户名>@<服务器地址>:/home/<用户名>/projects/ROGII/packages/part2_server_outputs_*.tar.gz.sha256 packages/
```

拿回来以后，先检查包是不是完整：

```bash
.venv/bin/python scripts/inspect_part2_server_package.py packages/part2_server_outputs_YYYYMMDD_HHMMSS.tar.gz
```

如果你想解压到本地保留：

```bash
mkdir -p server_results/part2_full
.venv/bin/python scripts/inspect_part2_server_package.py \
  packages/part2_server_outputs_YYYYMMDD_HHMMSS.tar.gz \
  --extract-to server_results/part2_full
```

## 12. 结果怎么记录

这一步很重要，不然以后你会忘记这次到底跑了什么。

建议至少记录下面这些东西：

```text
date
server name or IP
git commit
data hash
package sha256
baseline rmse
geometry residual rmse
multi-mask summary
是否通过 part2_completion_audit
```

你可以把这些内容写进：

- `docs/plans/02_residual_modeling_progress.md`
- `reports/submission_log.md`
- `reports/final_model_card.md`

如果这次是新服务器复跑，最好把新的 package 名称和 sha256 也写进去。

## 13. 常见失败

### 13.1 预检失败

先看：

```bash
sed -n '1,220p' reports/server_part2_preflight_report.md
```

常见原因是数据没传完整，或者环境依赖没装全。

### 13.2 中途断线

如果你用了 `tmux`，重新连回服务器：

```bash
tmux attach -t rogii-part2
```

### 13.3 内存不够

先跑一个中等版确认链路，不要一上来就硬顶：

```bash
.venv/bin/python scripts/run_part2_full_server.py \
  --train-rows-per-well 1200 \
  --max-iter 300 \
  --multimask-train-rows-per-well 1200 \
  --multimask-max-iter 300
```

### 13.4 磁盘满了

先看空间：

```bash
df -h
```

可以删旧包，但不要删原始数据：

```bash
rm -f packages/part2_server_outputs_*.tar.gz
rm -f packages/part2_server_outputs_*.tar.gz.sha256
```

## 14. 最后检查清单

跑之前：

- [ ] 已进入 `tmux`
- [ ] 已拉到最新代码
- [ ] 已创建 `.venv`
- [ ] 已安装 `requirements.txt`
- [ ] `data/raw/train` 和 `data/raw/test` 都在
- [ ] 旧的 Part 2 结果已经删掉或移走

跑的时候：

- [ ] 先跑 `server_part2_preflight.py`
- [ ] 再跑 `run_part2_full_server.py --dry-run`
- [ ] 再跑正式 full-row
- [ ] 不要关闭 `tmux`

跑完之后：

- [ ] `validate_part2_outputs.py` 输出 `checks=34 failures=0`
- [ ] `package_part2_server_outputs.py` 已生成 tar.gz 和 sha256
- [ ] 包已经拿回本地
- [ ] `inspect_part2_server_package.py` 检查通过
- [ ] 结果已经记到进度文档或模型卡里
