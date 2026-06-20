# ROGII Kaggle Rules 逐条核对版

来源页面：[ROGII - Wellbore Geology Prediction / Rules](https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction/rules)

读取时间：2026-06-20，Asia/Shanghai

读取方式：Kaggle 规则页为 JavaScript 渲染页面；本地静态读取只能拿到页面壳。正文通过已登录并已接受规则的本地浏览器会话读取，并在 `outputs/kaggle_rules_structured.json` 保留本地结构化抽取用于核验。该 `outputs/` 文件不提交 Git。

重要说明：

- 本文不是“摘要版”，而是按官方规则章节逐条整理的执行核对版。
- 为避免复制登录后规则页全文，本文采用中文转述和执行检查项；最终解释以 Kaggle 官方规则页为准。
- 本文不是法律意见，团队参赛、获奖、数据处理和代码发布前仍需核对官方原文。

## 0. 最高优先级结论

| 事项 | 项目执行判断 |
|---|---|
| 是否上传 Kaggle 原始数据到 GitHub | 不上传 |
| 是否上传 `outputs/` 大型中间结果到 GitHub | 不上传 |
| 是否可以上传代码、计划、验证报告、可复现说明 | 可以，但不能夹带 Competition Data |
| 是否可以公开私下只给本队的代码 | 不可以跨 Team 私享；公开分享需符合 Kaggle 公开分享规则 |
| 是否要保留完整复现链路 | 必须，从现在开始保留训练、推理、环境、配置、后处理、提交记录 |

## 0.1 官方章节覆盖矩阵

本节用于防止漏项。下表按官方页面章节层级逐项映射到本文位置；英文标题在正文中用中文转述，最终原文以 Kaggle 页面为准。

| 官方层级 | 本文位置 | 覆盖状态 |
|---|---|---|
| Competition-specific terms | 第 2 节 | 已覆盖 |
| Competition title | 第 2 节表格 | 已覆盖 |
| Competition sponsor | 第 2 节表格 | 已覆盖 |
| Competition sponsor address | 第 2 节表格 | 已覆盖 |
| Competition website | 第 2 节表格 | 已覆盖 |
| Total prizes available | 第 2 节奖金表 | 已覆盖 |
| Best Working Note Award | 第 2 节 Working Note Award | 已覆盖 |
| Winner license type | 第 2 节表格、第 3.5 节 | 已覆盖 |
| Data access and use | 第 2 节表格、第 3.4 节 | 已覆盖 |
| Competition-specific rules | 第 3 节 | 已覆盖 |
| Team limits | 第 3.1 节 | 已覆盖 |
| Submission limits | 第 3.2 节 | 已覆盖 |
| Competition timeline | 第 3.3 节 | 已覆盖 |
| Competition data | 第 3.4 节 | 已覆盖 |
| Winner license | 第 3.5 节 | 已覆盖 |
| External data and tools | 第 3.6 节 | 已覆盖 |
| Competition-specific eligibility | 第 3.7 节 | 已覆盖 |
| Winner obligations | 第 3.8 节 | 已覆盖 |
| Governing law | 第 3.9 节 | 已覆盖 |
| General rules binding agreement | 第 4 节 | 已覆盖 |
| General eligibility | 第 4.1 节 | 已覆盖 |
| Sponsor and hosting platform | 第 4.2 节 | 已覆盖 |
| Competition period | 第 4.3 节 | 已覆盖 |
| Competition entry | 第 4.4 节 | 已覆盖 |
| Individuals and teams | 第 4.5 节 | 已覆盖 |
| Submission code requirements | 第 4.6 节 | 已覆盖 |
| Determining winners | 第 4.7 节 | 已覆盖 |
| Winner notification and disqualification | 第 4.8 节 | 已覆盖 |
| Prizes | 第 4.9 节 | 已覆盖 |
| Taxes | 第 4.10 节 | 已覆盖 |
| General conditions | 第 4.11 节 | 已覆盖 |
| Publicity | 第 4.12 节 | 已覆盖 |
| Privacy | 第 4.13 节 | 已覆盖 |
| Warranty, indemnity and release | 第 4.14 节 | 已覆盖 |
| Internet | 第 4.15 节 | 已覆盖 |
| Right to cancel, modify or disqualify | 第 4.16 节 | 已覆盖 |
| Not employment | 第 4.17 节 | 已覆盖 |
| Definitions | 第 4.18 节 | 已覆盖 |

## 1. Entry And Binding Rules

官方规则开头强调：

| 条款点 | 逐条核对 |
|---|---|
| 参赛即接受规则 | 进入比赛、提交作品均意味着接受官方规则 |
| 规则具有约束力 | 规则构成参赛者与 Sponsor 之间的法律协议 |
| Submission 要符合网站要求 | 提交格式、方式、评估方式以 Kaggle 页面要求为准 |
| 评分依据 | 按 Competition Website 指定 metric 评分 |
| 奖项依据 | 在合规前提下，按模型/提交成绩决定奖项 |
| 多账号禁止 | 不能注册或使用多个 Kaggle 账号参赛/提交 |

工程动作：

- 所有成员只能用自己的唯一 Kaggle 账号。
- 不用备用号、共享号、小号提交。
- 提交前检查 Kaggle 页面当前 Requirements，不只看本仓库文档。

## 2. Competition-Specific Terms

| 编号 | 官方章节 | 内容 |
|---:|---|---|
| 1 | Competition Title | ROGII - Wellbore Geology Prediction |
| 2 | Competition Sponsor | ROGII |
| 3 | Sponsor Address | 11750 Katy Freeway, Suite 780, Houston, Texas 77079 |
| 4 | Competition Website | https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction |
| 5 | Total Prizes Available | 50,000 USD |
| 6 | Winner License Type | Non-exclusive license |
| 7 | Data Access and Use | Competition use only |

奖金：

| 奖项 | 金额 |
|---|---:|
| First Prize | 25,000 USD |
| Second Prize | 13,000 USD |
| Third Prize | 7,000 USD |
| Fourth Prize | 5,000 USD |

Best Working Note Award：

| 奖项 | 金额 |
|---|---:|
| Award 1 | 2,500 USD |
| Award 2 | 2,500 USD |

Working Note Award 条件：

- 鼓励尽早分享 working notes。
- Team 需要在 public leaderboard Medal Zone 才有资格。
- 相关提交截止时间：2026-07-06 23:59 UTC。
- 评审标准以 Evaluation 页面为准。

工程动作：

- 如果要冲 Working Note Award，需要单独维护 working note，而不是赛后补写。
- working note 需要能解释方法、验证、失败案例、工程可信性。
- 规则文件和 README 要链接到 Kaggle 官方页面，而不是替代官方页面。

## 3. Competition-Specific Rules

### 3.1 Team Limits

| 条款点 | 逐条核对 |
|---|---|
| 最大 team size | 5 人 |
| Team merger | 可由 team leader 执行 |
| Merger submission count 限制 | 合并后的队伍提交次数必须不超过规则允许的最大累计提交次数 |
| Hackathon 特例 | Hackathon 中每队通常只允许一次提交；合并前提交可能被 unsubmit |

工程动作：

- 记录正式 Team 成员名单。
- 合并团队前核对 submission count。
- 不和外部团队私下交换数据、代码、预测。

### 3.2 Submission Limits

| 条款点 | 逐条核对 |
|---|---|
| 每日提交上限 | 每天最多 5 次 |
| Final submission | 最多选择 2 个 final submissions |
| Hackathon 特例 | 每队只能提交 1 次 |

工程动作：

- 建立 `submissions/` 记录和实验日志。
- 每个 Kaggle 提交必须对应本地 CV 分数、假设、代码版本、配置。
- final 候选至少保留一个 conservative 版本和一个 aggressive 版本。

### 3.3 Competition Timeline

| 条款点 | 逐条核对 |
|---|---|
| 时间线来源 | Entry Deadline、Final Submission Deadline、Start Date、Team Merger Deadline 等以 Overview > Timeline 页面为准 |
| 时间可能变化 | 需要定期检查 Kaggle 页面 |

工程动作：

- 不把时间线硬编码成唯一事实；README 可提示去 Kaggle 页面核对。
- 提交计划按 UTC 处理，避免时区错误。
- Working Note Award 的 2026-07-06 23:59 UTC 单独设提醒。

### 3.4 Competition Data

#### 3.4.1 Data Access and Use

| 条款点 | 逐条核对 |
|---|---|
| 使用范围 | Competition Data 只能用于参加本竞赛和 Kaggle.com 论坛相关场景 |
| Sponsor 权利 | Sponsor 可取消违规使用数据者资格 |

工程动作：

- 本仓库不提交 `data/`。
- 本仓库不提交可还原训练数据的大型 `outputs/`。
- 数据下载只通过 Kaggle 官方渠道或已授权本地下载。

#### 3.4.2 Data Security

| 条款点 | 逐条核对 |
|---|---|
| 访问控制 | 需要采取合理措施，防止未接受规则的人访问 Competition Data |
| 禁止再分发 | 不得传输、复制、发布、再分发，或提供给未参赛/未同意规则的人 |
| 事故通知 | 发现未授权传输或访问后，需要通知 Kaggle 并配合处理 |

工程动作：

- 不把 zip、CSV、PNG、PPTX 上传 GitHub。
- 不把数据发给未加入竞赛或未接受规则的人。
- 如果团队共享数据，优先让成员各自用 Kaggle 下载。
- `.gitignore` 必须继续包含 `data/`、`outputs/`、`features/`、`models/`。

### 3.5 Winner License

| 条款点 | 逐条核对 |
|---|---|
| License type | Winner 需要授予 Sponsor 非独占使用许可 |
| 权利范围 | 对 winning Submission 和生成它的源代码，Sponsor 可在规则所述范围内使用、复制、分发、改作、展示等 |
| 商业软件例外 | 一般商业可购买的软件不需要交付其源代码，但需要说明如何取得和复现 |
| 不兼容数据/模型例外 | 若使用 license 不兼容的输入数据或预训练模型，规则中有例外说明，但仍需满足其他义务 |
| 方法描述 | Sponsor 可能要求详细说明 winning submission 生成方法 |
| 复现说明 | 描述应让人能复现，包括架构、预处理、损失、训练细节、超参数等 |
| 代码仓库 | 可能需要提供包含完整说明的代码仓库链接 |
| 结果讨论 | 通过验证后，可能需要参加 recorded call 或 panel call |

工程动作：

- 从现在开始保留完整训练代码、推理代码、环境文件和配置。
- 每个模型版本需要记录数据 hash、seed、feature config、后处理和 ensemble 权重。
- 不使用无法授权、无法说明来源、无法复现的组件。

### 3.6 External Data And Tools

| 条款点 | 逐条核对 |
|---|---|
| External Data | 可以使用 Competition Data 以外的数据开发和测试 |
| 公平访问 | 外部数据应公开、所有参赛者可平等访问、无成本，或满足 Reasonableness criteria |
| 外部模型/工具 | 可用，除非 Host 明确禁止 |
| 成本和地域限制 | 若成本过高、访问限制明显，Host 可按 Reasonableness Standard 判断是否排除 |
| 示例边界 | 小额订阅可能可接受；超过奖金额度的专有数据集通常不合理 |
| AMLT | 可使用 Automated Machine Learning Tools，但需有适当许可证并满足规则 |

工程动作：

- 每个外部数据/模型/工具都建登记表：名称、来源、URL、许可证、成本、是否所有参赛者可访问、使用方式。
- 不把高成本专有数据或地域受限资源做成核心依赖。
- 如果使用 AutoML、LLM、商业工具，记录版本、参数和复现替代路径。

### 3.7 Eligibility

| 条款点 | 逐条核对 |
|---|---|
| Competition Entities | Sponsor、Kaggle 及其母公司/子公司/关联方等员工、实习生、承包商、管理人员可参与但通常不能获奖 |
| 内部政策 | Competition Entities 相关人员还需遵守雇主内部政策 |

工程动作：

- 团队成员确认 eligibility。
- 如果代表学校/公司参赛，确认组织政策允许。

### 3.8 Winner's Obligations

| 条款点 | 逐条核对 |
|---|---|
| 交付代码 | 获奖条件之一是交付生成 winning Submission 的最终模型软件代码 |
| 文档要求 | 代码需有文档，能说明构建/运行资源 |
| 范围 | 包括 training code、inference code、计算环境说明 |
| 商业软件 | 对不归自己所有但可合理购买的软件，可不交付其源代码，但需说明获取方式和复现参数 |
| AMLT | 使用 AMLT 也可获奖，但仍需满足 license、winner obligations 等规则 |
| License grant | 需要授予 Sponsor 规则要求的 license，并声明自己有权授予 |
| Prize documents | 需要签署/返回 Sponsor 或 Kaggle 要求的领奖文件、税务表等 |

工程动作：

- 项目必须能从干净环境复现训练或至少复现最终 inference。
- 记录硬件、运行时长、依赖版本、Kaggle notebook 设置。
- 不能只保留 notebook 输出，不保留生成它的过程。

### 3.9 Governing Law

| 条款点 | 逐条核对 |
|---|---|
| Governing law | 适用 Texas law，排除冲突法规则 |
| Jurisdiction | 相关争议在 Harris County, Houston 的联邦或州法院处理 |
| Severability | 某条无效不影响其他条款继续有效 |

工程动作：

- 奖项、许可、争议相关事项以官方法律条款为准。

## 4. General Competition Rules

### 4.1 Eligibility

| 条款点 | 逐条核对 |
|---|---|
| Kaggle account | 必须是 Kaggle.com 注册账号持有人 |
| 年龄 | 满 18 岁或所在地成年年龄，除非 Sponsor 同意且有监护同意 |
| 地区和制裁 | Crimea、DNR、LNR、Cuba、Iran、North Korea 等地区/受制裁对象不可参赛 |
| Export controls | 受美国出口管制或制裁的个人/实体不可参赛 |
| 全球开放但有例外 | 除受限地区/对象外全球可参赛，本地法律仍需自行核对 |
| 代表机构参赛 | 代表公司/学校/雇主参赛时，个人和机构均受规则约束 |
| 雇主同意 | 若在工作范围内或代表第三方行动，需要确认雇主/第三方知情同意 |
| 虚假信息 | 身份、居住地、地址、电话、邮箱、权利归属等虚假信息可能立即取消资格 |

工程动作：

- 成员加入前确认 Kaggle account、地区、组织政策。
- 不用他人账号或共用账号提交。

### 4.2 Sponsor And Hosting Platform

| 条款点 | 逐条核对 |
|---|---|
| Sponsor | Sponsor 负责比赛 |
| Kaggle role | Kaggle 代表 Sponsor 托管比赛，是独立承包方 |
| Kaggle Terms | Kaggle 用户还受 Kaggle Terms of Service 约束 |
| Kaggle administrative functions | Kaggle 执行托管相关管理功能 |

工程动作：

- 同时遵守 Competition Rules、Competition Website 要求、Kaggle Terms。

### 4.3 Competition Period

| 条款点 | 逐条核对 |
|---|---|
| Competition Period | 从 Start Date 到 Final Submission Deadline |
| Timeline 可能变化 | Sponsor 可调整或增加 deadline |
| 参赛者责任 | 需要定期检查 Competition Website |
| 时区责任 | 参赛者自行确定本地对应时区 |

工程动作：

- 以 UTC 记录关键 deadline。
- 每次冲榜前核对 timeline 页面。

### 4.4 Competition Entry

| 条款点 | 逐条核对 |
|---|---|
| No purchase necessary | 不需购买即可进入/获奖 |
| Entry Deadline | 需要在 Entry Deadline 前注册 |
| Submission requirements | 需按 Competition Website 的方式、格式和其他要求提交 |
| Deadline | 迟交无效 |
| Human labeling | 除 Hackathon 明确允许外，不得用人工标注/人工预测 validation/test 记录 |
| Multi-stage | 多阶段比赛可能每阶段都需有效提交 |
| Invalid submissions | 不完整、损坏、篡改、欺诈、迟交等提交无效 |
| Disqualification | Sponsor 可取消不遵守规则者资格 |

工程动作：

- 严禁人工看 test 后手填预测。
- 不通过 public LB 反推单条 test label。
- 所有提交由代码生成，保留生成脚本和配置。

### 4.5 Individuals And Teams

| 条款点 | 逐条核对 |
|---|---|
| Unique account | 只能用一个唯一 Kaggle 账号提交 |
| Teams | 可组队，但只能加入一个 Team |
| Team membership | 每名成员需独立注册并确认 Team membership |
| Team size | 不超过 maximum team size |
| Team merger | 需满足 size、submission count、deadline 等条件 |
| Private sharing | Team 外不得私下共享代码或数据 |
| Public sharing | 如果公开分享代码，应对所有参赛者可见，通常通过论坛/competition notebooks |

工程动作：

- GitHub 私有/公开状态要和 Kaggle public sharing 规则匹配。
- 与外部人员讨论时不分享数据、私有代码、私有预测。

### 4.6 Submission Code Requirements

| 条款点 | 逐条核对 |
|---|---|
| Private code sharing | 比赛期间通常不能在不同 Team 之间私下分享 Competition Code |
| Competition Code 范围 | 与 Competition Data 或比赛相关的源代码/可执行代码 |
| Public code sharing | 可公开分享代码，但不能侵犯第三方权利 |
| Public sharing 许可 | 公开分享通常视为以 OSI-approved license 授权 |

工程动作：

- 如果仓库公开，需要确认里面没有数据，且代码共享方式不违反 Kaggle 规则。
- 不私发核心 competition code 给非 Team 成员。
- 第三方代码必须遵守 license。

### 4.7 Determining Winners

| 条款点 | 逐条核对 |
|---|---|
| Winners | 由合规 submission 的得分/排名决定 |
| Private leaderboard | 最终排名看 private leaderboard |
| Public leaderboard | Public leaderboard 是测试集代表性样本，不决定最终真实泛化 |
| Compliance review | Sponsor/Kaggle 可审核资格和合规性 |
| Tie / disputes | 以官方规则和 Sponsor/Kaggle 处理为准 |

工程动作：

- 不用 public LB 直接调参到过拟合。
- 本地 CV 和 multi-mask 必须作为主判断。

### 4.8 Winner Notification

| 条款点 | 逐条核对 |
|---|---|
| Notification | 潜在获奖者会收到通知 |
| Response | 需要在要求时间内响应并完成文件 |
| Verification | 获奖资格和提交合规需通过审核 |
| Failure | 不响应或不合规可能失去奖项 |

工程动作：

- Kaggle 账号邮箱保持可用。
- 决赛后保持仓库、环境、数据处理链路可运行。

### 4.9 Prizes

| 条款点 | 逐条核对 |
|---|---|
| Prize description | 奖项以 Competition Website 为准 |
| Odds | 获奖概率取决于有效提交数量和参赛者技能 |
| Review | 所有奖项受 Sponsor 审核 eligibility 和 compliance |
| Non-compliance | Sponsor 可取消提交或要求一周内修复问题 |
| Decline | 潜在 winner 可拒绝被提名 |
| Documents | 领奖文件通常需两周内返回 |
| Payment timing | 文件收到后约 30 天内发奖 |
| Transfer | 奖项不能转让或分配给他人 |
| Eligibility | 不满足 eligibility 则不能领奖 |
| Team split | 团队奖金默认平均分配，除非全队一致选择其他分配并提前通知 Kaggle |

工程动作：

- 提前清理 license 冲突。
- 提前准备可复现说明，避免一周整改压力。

### 4.10 Taxes

| 条款点 | 逐条核对 |
|---|---|
| Tax responsibility | 奖金税务由 winner 负责 |
| Documentation | 需要提交税务和合规文件 |
| Withholding | Sponsor 可能依法扣缴税款 |
| Failure | 不提交文件或不合规可能失去奖项 |
| U.S. residents | 美国居民可能收到 IRS Form-1099 |

工程动作：

- 团队奖金分配和税务责任提前沟通。

### 4.11 General Conditions

| 条款点 | 逐条核对 |
|---|---|
| Laws | 适用联邦、州、省、市、地方等法律法规 |

工程动作：

- 除 Kaggle 规则外，还要遵守所在地法律和组织政策。

### 4.12 Publicity

| 条款点 | 逐条核对 |
|---|---|
| Publicity | Sponsor、Kaggle 及其 affiliates 可在法律允许范围内使用参赛者姓名和肖像进行宣传 |
| Compensation | 通常无额外补偿 |

工程动作：

- 团队成员提前知晓获奖后可能公开姓名/形象。

### 4.13 Privacy

| 条款点 | 逐条核对 |
|---|---|
| Personal information | Kaggle/Sponsor 可收集、存储、共享、使用参赛过程中提供的个人信息 |
| Kaggle role | Kaggle 按其 Privacy Policy 处理个人信息 |
| Rights | 账号持有人可通过账号或 Kaggle Support 请求访问、修正、移植或删除个人数据 |
| Sponsor transfer | Kaggle 会向 Sponsor 转移必要个人信息 |
| Cross-border transfer | Sponsor 所在国家可能与参赛者所在地隐私法不同 |

工程动作：

- 参赛账号个人信息保持准确。
- 团队成员理解数据会转给 Sponsor 用于比赛管理。

### 4.14 Warranty, Indemnity And Release

| 条款点 | 逐条核对 |
|---|---|
| Original work | 参赛者保证 Submission 是自己的原创工作或有权提交 |
| Rights | 参赛者需拥有提交和授权所需权利 |
| No infringement | 不得侵犯第三方知识产权、隐私、公开权、保密义务等 |
| No unlawful content | 不得违反适用法律 |
| Indemnity | 因提交、虚假陈述、违规、侵权、领奖等造成索赔时，参赛者需承担规则中说明的赔偿/抗辩义务 |
| Release | Competition Entities 对网站故障、提交处理错误、公告错误等承担有限/免责边界 |

工程动作：

- 第三方库、模型、数据、代码片段都要有 license 记录。
- 不把来源不清的 notebook、脚本、权重塞进最终方案。

### 4.15 Internet

| 条款点 | 逐条核对 |
|---|---|
| Technical failures | Competition Entities 不对网站、网络、硬件、软件、服务器、传输、拥塞等故障导致的问题负责 |

工程动作：

- 不要压截止时间提交。
- 关键提交提前完成并保存日志。

### 4.16 Right To Cancel, Modify Or Disqualify

| 条款点 | 逐条核对 |
|---|---|
| Cancel/modify/suspend | 若病毒、bug、篡改、未授权干预、欺诈、技术故障等影响公平/完整性，Sponsor 可取消、终止、修改或暂停比赛 |
| Disqualification | Sponsor 可取消篡改提交流程或比赛网站者资格 |
| Legal action | 故意破坏网站或干扰比赛运行可能导致法律追责 |

工程动作：

- 不攻击、不压测、不绕过 Kaggle 系统。
- 不使用违规自动化访问、代理池、反风控手段。

### 4.17 Not An Offer Or Contract Of Employment

| 条款点 | 逐条核对 |
|---|---|
| No employment | 提交、获奖或规则内容不构成 Sponsor/Competition Entities 的雇佣 offer 或合同 |
| Voluntary submission | Submission 是自愿提交，不形成保密、信托、代理、雇佣等类似关系 |

工程动作：

- 不把参赛关系理解成雇佣或保密合作关系。

### 4.18 Definitions

| Term | 逐条整理 |
|---|---|
| Competition Data | Competition Website 上用于比赛的数据或数据集，包括可能提供的 prototype 或 executable code；包含 private/public test sets，哪些数据属于哪个 set 不会告知参赛者 |
| Entry | 参赛者加入、注册或接受规则 |
| Final Submission | 用户选择的或未选择时 Kaggle 自动选择的、用于最终排名的 submission |
| Participant / Participant User | 进入比赛并提交作品的个人 |
| Private Leaderboard | 基于 private test set 的排行榜，决定最终名次 |
| Public Leaderboard | 基于 test data 代表性样本的可见排行榜，比赛期间可见 |
| Sponsor | 负责举办比赛、提供数据、决定 winners、执行规则的一方 |
| Submission | 参赛者提供给 Sponsor 用于评估和确定 leaderboard position 的内容，形式可为 model、notebook、prediction file 或 Sponsor 指定的其他格式 |
| Team | 一个或多个 Participants 在 Kaggle 平台正式合并组成的参赛团队 |

工程动作：

- 明确 public LB 不是最终排名依据。
- 不能试图识别 private/public test set 划分。
- 所有 final submission 都要可追溯。

## 5. 本项目执行检查表

### 5.1 数据与仓库

| 检查项 | 状态要求 |
|---|---|
| `data/` | 不提交 GitHub |
| `outputs/` | 不提交 GitHub，尤其是可还原训练真值的文件 |
| `features/` | 不提交 GitHub |
| `models/` | 不提交 GitHub |
| 原始 zip | 不提交 GitHub |
| 解压 CSV/PNG/PPTX | 不提交 GitHub |
| 下载方式 | 通过 Kaggle 官方页面/API，要求账号已接受规则 |
| data hash | 本地记录，报告引用 |

### 5.2 代码与分享

| 检查项 | 状态要求 |
|---|---|
| Team 外私享代码 | 禁止 |
| 公开代码 | 不含数据；注意 Kaggle public sharing 规则 |
| 第三方代码 | 记录 license |
| 外部模型/数据 | 记录来源、成本、公开可得性、license |
| 最终方案 | 可复现、可交付、可解释 |

### 5.3 提交与冲榜

| 检查项 | 状态要求 |
|---|---|
| 每日提交 | 不超过 5 次 |
| Final submissions | 最多 2 个 |
| Public LB | 只能辅助判断，不做唯一依据 |
| Local CV | 每次提交必须有本地验证和实验记录 |
| Human labeling | 禁止人工标注/预测 validation/test records |
| Deadline | 按 UTC 提前完成 |

### 5.4 获奖准备

| 检查项 | 状态要求 |
|---|---|
| Training code | 保留 |
| Inference code | 保留 |
| Environment | 保留 |
| Hyperparameters | 保留 |
| Preprocessing | 保留 |
| Loss / model details | 保留 |
| Postprocessing / ensemble | 保留 |
| Resource requirements | 保留 |
| Method write-up | 可复现、可交付 |

## 6. 对“上传数据到 GitHub”的处理结论

不上传。理由有两层：

1. 规则层面：Competition Data 是 competition use only，并且禁止发布、再分发或提供给未接受规则的人。
2. 技术层面：本地 `data/` 约 2.0 GB，zip 约 779 MB，普通 GitHub 仓库无法合理承载，且 Git LFS 也不能绕开 Kaggle 数据再分发限制。

替代方案：

- 仓库保留下载命令、数据契约、hash、目录约定。
- 团队成员各自用 Kaggle 官方方式下载。
- 需要复现实验时，以 data hash 检查数据版本一致。

## 7. 来源

- Kaggle Rules 页面：<https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction/rules>
- Kaggle Competition 页面：<https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction>
- GitHub large file documentation：<https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github>
- GitHub LFS documentation：<https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage>
