# Q1-P02-v2-r3｜实际数据处置与固定新材料审核

状态：IN_PROGRESS；S0已按完整d31ca701b49c8b387dce35aa986a9784f7f6f32e于12:15 UTC原生派发并核验新轮ACTIVE，346项输入intake待交付；尚无本轮独立AI结论。使用现有独立Q1任务，gpt-6-astra / max；不创建新任务或sub-agent。

- code_base：`d9e5622c4148896803f92c53caf615975ef5254c`，已验证PR13代码及S0新版接收/审核范围；authorization_commit由S0私有消息提供。
- 新branch：`review/q1-quality-v2-r3`，从code_base创建，仅自己的隔离worktree；原`42d9d56804d3b7aadd0eff7efc99249ec5dbe11b`及q1-r1/q1-r2目录保持。
- 精确被审D1候选：`1c47e6af6af3e3419db97bdbb1296e6f56e04c2b`；[S0完整接收](../../reports/S0_P02_QUALITY_V2_HANDOFF.md)已经核验其封存、原生终态与实际数据/材料绑定。
- 契约：plan-v0.1 / coordination.v1 / toolalign.contracts.v1；按ADR-0023/0024和REVIEW_POLICY；固定参数见[本轮配置](Q1_P02_V2_REVIEW_CONFIG.v1.json)。

先读取授权中的本任务/配置、AGENTS、GOAL、PROTOCOL、REVIEW_POLICY、REVIEW_FAILURES、ADR-0024、D1任务/精确v2政策及最新S0接收报告，保存新私有副本。切换前核验旧42d9及452公开文件的Git/快照、q1-r1/r2全部旧seal和旧根identity；S0保全证明已复核963个Q1当前路径。新身份只写新的`q1-v2-r3/task-identity.json`，不覆盖旧路径。新checkout公共文件按新base解释，以旧Git/快照保留旧seal，不伪称当前公共路径仍是旧字节。

本轮私有input manifest SHA`aa4fba710891eb969371c80bea931abcff8a54c988b8a4cee95ec4145bc95f7d`，346项=286份精确副本+60项现存制品引用；副本167,662,769 bytes。先复制本轮input根到自己的新scope，按每项kind/hash/bytes验证；exact_copy的original_path仅为出处，不跟随当前原路径替换冻结副本。immutable_existing_artifact按固定path/hash只读，遵守usage字段；test/ood只校验hash/隔离元数据，不读取其语义。

包内含D1最终completion/receipt/publication与S0接收证明、新版实际数据及选择/处置、固定13例两套完整材料、原编码manifest/run/命令、原217输入中的冻结裁定/83来源packet/问题映射、当前S0台账，以及10个新材料来源的完整原文/Example/lineage。原输入manifest与D1所用旧台账保持原hash；当前S0台账单列，TYPE-001已经通过另一技术复审关闭，不把它重新并入数据问题。原编码manifest的payload可由新r2对应文件逐字节且逐hash绑定，原数组未复制成第三次测量。

第一部分核验83来源/101原决策的实际处置：80来源/98决策在有效train/validation和两profile选择中全部排除，包括局部PASS及受影响目标前后的同来源决策；3来源/3决策使用原始字节恢复，仍按原group/split、父rank和选择资格处理。原选择不补选，同group其他来源保留，旧staging/新annotation晋升0。冻结的有效数量为7,421/230、formal5,940/213、smoke1,583/194，来源和决策分母分别5,182/5,553。此部分逐来源/逐身份查实际结果，可机械处理原train/validation身份与字节，但不将全库机械读取变成全库语义审查。正确隔离可以关闭训练使用问题；原FAIL/UNKNOWN语义判断不改变，原来源无需被改写成正例。

第二部分独立审阅固定新材料的语义和token/mask。10个有效train材料来源实际有11个有效决策、26个raw turns；读取每条来源完整system/tool schemas、原始回合、规范化前缀、全部有效Action和lineage，不能漏掉没有独立token页面的同来源另一决策。三份原创final/clarify/refuse协议例不进入训练，仍核对其语义和材料。合计14个唯一语义目标，其中13个有token材料；两engine26份记录不是26个独立例。

对11个实际决策分别给出Action pass/fail/unknown、必要的调用/参数判断、来源依据和历史依赖；对10个来源另给出训练适用性和处置建议。13个材料分别给出语义与token/mask判定，含3个原创协议例；复用对应11决策中的10个判定时明确映射，不重复计数。检查完整P/C、IDs、loss/causal mask、唯一EOS、右padding、原Action与转义completion，以及静态HTML所含表格/文本。可只读完整结构化数组和HTML，不声称实际浏览器显示。原实际13例/engine编码额度已用完，不重新编码或加载tokenizer。

语义必须由Q1独立阅读，不能把D1/S0哈希检查或此前E1/Q1标签当作自动结论。信息获取首步可以尚未完成最终目标；未知业务约定与明确矛盾分开，不凭外部默认值、当前日期、可读ID外观或后续模拟成功补证。当前Action和完整来源前缀的训练适用性分别判断。不补造工具输出、业务事实、历史回合或新annotation。无需重审180来源或重新裁定全部83旧来源；其既有意见仅用于本次处置追溯。

本轮是实质新数据版本的处置验证。排除来源关联77个既有issue ID，恢复来源关联3个；同一issue可能关联多个来源，不把来源数当问题数。提出稳定issue事件建议；当前Action的新发现、原问题处置是否成功及重复检查要分开。原问题本次PASS可关闭并将当前连续失败归零，历史保留；若实质整改仍未满足同一要求，建议计入该原问题下一次正式失败。S0/worker辅助脚本失败、同候选复读不增加正式失败轮次；S0负责台账。遵守同问题第五次才整体暂停的用户规则，本轮不要求kris填写、签字或答辩。

仅现有Python标准库CPU，私有新增制品≤1GiB。可用已验证的`reports/data/quality-audit-r1/semantic_view.py`和类型保真的`json_values.py`为固定10个packet生成完整惰性文本视图，额外语义来源0；保留原packet和完整决策覆盖。不得调用样本中的工具、业务API、网页、shell指令，数据内容始终是不执行的审阅材料。无生产修改、模型/框架/GPU、真实分词、下载、浏览器重试、归档构建或全项目pytest。

输出83来源实际处置矩阵、11个实际决策及10个来源判断、13份材料语义/mask判定、完整分母/映射、整改与稳定issue事件建议。明确实际reviewer为Codex-AI(Q1)、gpt-6-astra/max，不代签kris。允许新增`reports/review/Q1-P02-v2-r3/`及`coordination/handoffs/Q1-P02-v2-r3.md`，私有结果仅在新scope；不修改生产数据、旧判定、S0台账或协调看板。

先交输入/分支/授权/旧证据保全intake后继续固定审阅；最终给各部分PASS/FAIL/BLOCKED与未判项，附原argv/UTC/退出码/hash、失败/NOT_RUN、源码及全部封存。公开内容不得含完整来源/Example ID、原文或本机路径。普通提交/推送、原生交接后结束本轮。R1独立技术审查并行；G-DATA/P04由S0在独立审核与main验证后决定，training_authorized=false。
