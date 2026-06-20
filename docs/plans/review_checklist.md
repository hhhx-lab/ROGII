# 子计划工程核对清单

## 审查结论

四个子计划总体可实现，且路线适合“稳健工程 + 冲榜”双目标。审查后补强了以下容易遗漏的工程细节：

- 数据版本和 hash 记录；
- 人工 mask 下 `TVT_input` 相关特征必须重算；
- row-level RMSE 与 per-well 稳健性同时评估；
- Parquet 依赖和缓存策略；
- 禁止 well ID 记忆；
- residual 校准和 clipping；
- GR hidden rows 使用边界说明；
- typewell 越界、对齐符号、对齐置信度；
- alignment 计算预算；
- ensemble 成员一致性检查；
- submission QA；
- Kaggle code competition 预训练模型规则风险；
- 从零复现演练。

## Part 1: Validation / Baseline

必须确认：

- 数据文件、列、row index 全部通过契约检查；
- `outputs/data_version.json` 已生成；
- baseline CV 覆盖 773 口训练井；
- 多 mask split 保存了 allowed known rows，防止未来信息泄漏；
- baseline 同时报告 row-weighted 和 per-well 指标；
- worst wells 有图和失败类型；
- B0/B1/B2 至少实现，B3/B4 可后续补。

主要风险：

- mid-section mask 容易错误使用 mask 后方 `TVT_input`；
- 长井主导 row-level RMSE；
- 缓存文件没有 data/config 版本导致误比较。

## Part 2: Residual

必须确认：

- residual target 来自 baseline OOF 或合法 split prediction；
- split 相关特征按 mask 后 `TVT_input` 重算；
- 不使用 well ID one-hot 或 target encoding；
- 训练配置、feature list、seed 全部落盘；
- 同时比较 row-weighted 和 well-balanced 模型；
- residual 有校准、clip、alpha blend；
- failure analysis 包含 best improved 和 worst degraded。

主要风险：

- 用原始 `TVT_input` 构造人工 mask 特征造成泄漏；
- geometry residual 在少数长井上好但整体泛化弱；
- residual 模型引入曲线噪声。

## Part 3: GR / Typewell

必须确认：

- 使用 hidden rows GR 是基于 Kaggle 离线预测设定，并在报告中说明；
- GR 缺失有 flag 和 quality score；
- typewell TVT 越界时有 flag 和 fallback；
- alignment offset 符号统一；
- low-confidence alignment 不直接修正；
- 对齐计算有预算控制；
- typewell 模块主要改善 high baseline error/worst wells。

主要风险：

- GR 缺失或低方差时产生伪相似；
- alignment 符号反向导致灾难性修正；
- DTW/滑窗搜索过慢，不适合 Kaggle Notebook；
- Geology label 编码过拟合。

## Part 4: Ensemble / Submission

必须确认：

- 所有 ensemble 成员都有 OOF 和 test prediction；
- test prediction 与 sample submission id 顺序一致；
- ensemble 不用 public LB 直接调权；
- postprocess 必须 A/B 对比；
- conservative/balanced/aggressive 三种风险版本都可生成；
- `submission.csv` 自动 QA；
- Kaggle Notebook 可从输入数据完整运行；
- submission log 记录假设、CV、LB、风险和决策。

主要风险：

- public LB 诱导过拟合；
- aggressive 版本 P99/worst wells 爆炸；
- 预训练模型上传方式不符合 code competition 规则；
- Notebook 本地可跑但 Kaggle 路径/依赖失败。

## 最终执行顺序建议

1. 先实现 Part 1 到“baseline CV + worst wells”。
2. 只在 Part 1 验证可信后做 Part 2。
3. Part 2 确认 residual 真有效，再投入 Part 3。
4. Part 4 不应太早复杂化，至少有 3 个有效 OOF 成员再做正式 ensemble。
