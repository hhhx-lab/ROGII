# ROGII

ROGII 是围绕 Kaggle 竞赛 `ROGII - Wellbore Geology Prediction` 整理的课程项目。任务目标是根据水平井井轨迹、已知段测井信息和参考地层信息，预测隐藏尾段的 `TVT`。

## 任务说明

该任务属于井筒地质预测问题。主要难点包括隐藏尾段长度差异较大、`TVT_input` 缺失比例较高、训练集与正式预测阶段可用字段并不完全一致。实现难度为中等偏高，关键工作在于数据边界控制、按井分组交叉验证、残差建模和候选模型筛选，而不是单一模型拟合。

## 代码结构

- `data/`：本地数据入口，原始数据放在本地 `data/raw/`，不随 Git 上传。
- `scripts/`：数据检查、特征构造、模型训练、候选筛选和提交导出脚本。
- `models/`：模型配置与特征清单。
- `results/`：与论文一一对应的精简结果表和最终提交文件。
- `docs/paper/`：论文源码、论文 PDF、模板、配图和成员分工文件。

## 模型运行

原始数据体积较大，不上传到 GitHub。本地运行前需放入 `data/raw/`；若本地缺少原始数据，需在接受 Kaggle 竞赛规则并完成本地认证后重新下载。

```bash
python scripts/download_data.py
python scripts/check_data_contract.py
python scripts/make_cv_splits.py
python scripts/evaluate_baseline_cv.py
python scripts/build_baseline_features.py
python scripts/build_geometry_features.py
python scripts/train_residual_model.py --spec geometry
python scripts/train_residual_model.py --spec xgb --tree-backend auto
python scripts/evaluate_model_cv.py
python scripts/build_part3_diagnostics.py
python scripts/build_gated_geometry.py
python scripts/train_learned_gater.py
python scripts/blend_predictions.py
python scripts/postprocess_predictions.py
python scripts/select_submission_candidate.py --dry-run
python scripts/make_submission.py --variant auto --output results/final_submission.csv
python scripts/validate_submission.py --submission results/final_submission.csv
```

## 结果文件

- 数据概览：`results/data_overview.csv`
- 模型对比：`results/model_comparison.csv`
- 门控搜索：`results/alpha_search.csv`
- 集成比较：`results/ensemble_comparison.csv`
- 候选筛选：`results/candidate_selection.csv`
- 后处理比较：`results/postprocess_comparison.csv`
- 最终提交：`results/final_submission.csv`
- 格式与复现检查：`results/format_and_reproducibility_check.md`

## 成员分工

- 翁凯乐（10245001419）：数据下载、数据契约检查、数据统计与描述整理。
- 何剑宝（10245001417）：基线模型、几何残差回归模型与树模型训练。
- 冯炳睿（10245001411）：门控模型、集成实验、候选筛选与后处理比较。
- 万席宁（10245001421）：论文撰写、图表整理、格式核对与最终提交文件归档。
