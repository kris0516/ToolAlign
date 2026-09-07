# P02-QUALITY-ADJUDICATION-R1｜新版数据与材料技术独立审查

状态：CLAIMED，精确候选及完整交接已由S0接收，待原生派发；尚无独立结论。使用现有独立R1任务、gpt-6-astra / max，不创建新任务或sub-agent。

- 精确候选：`1c47e6af6af3e3419db97bdbb1296e6f56e04c2b`；原已验证生产基线`6c81dfcc855fca188181d1bb08870f47d8edacc9`。
- 原D1授权：`f8b81b9783892669d19aafee5a1d82a4a8409cd3`；修正后生产/测试提交`f7acd93595bfeb5e81b6eafe53c8d4106ce10a68`。本轮S0 authorization_commit由私有分发词提供。
- 新branch：`review/p02-quality-adjudication-r1`，从精确候选创建，仅自己的隔离worktree；新身份及私有结果写新的`review-p02-quality-adjudication-r1` scope。
- 契约：plan-v0.1 / coordination.v1 / toolalign.contracts.v1；Action JSON v1、原v1配置与源码保持。

先读取本轮授权中的本任务、AGENTS、GOAL、PROTOCOL、REVIEW_POLICY、REVIEW_FAILURES、原D1任务/精确v2配置、ADR-0024及[S0完整接收](../../reports/S0_P02_QUALITY_V2_HANDOFF.md)，保存本轮授权副本。切换前核验原`0cefe771c8d867d9e253b6603105ad31dc3a7787`及其504公开文件Git/快照、全部旧私有封存和根identity；新checkout中的公共路径按新候选解释，不把旧seal的公共字节冒称仍在当前checkout。S0已核验3,666个R1当前路径及26链接，分发时再次确认原生completed/idle。

审查完整12个新增文件和全部候选，不能只审最后的文档提交。492候选文件中480基线文件不变；新配置必须逐字匹配S0 SHA`7cf53c23568cd06c9543f253d9636b4655b135f0e6daf0eb318ace2100807ccb`。固定217输入manifest SHA`02e1f64ffb8c11d32b7653890c25996a1deb17708b2b6e74f5d9703e09761713`，新版manifest SHA`0b0fdb79f728256dac42ddba75e0f3fc43aebb9502f2e9097398a482d5774251`。本机路径、completion/receipt与S0证明由私有消息提供；原件只读，不追溯消费新台账替换D1冻结输入。

独立核验整来源处置与全部决策：80来源/98决策排除，3来源/3决策原字节恢复；所有Example行、group/split、原lineage、父rank及相对顺序保持；同group其他5,182来源/5,553决策保留；不补选、不重标晋升、不把旧staging纳入有效数据。有效train/validation7,421/230，formal5,940/213，smoke1,583/194；训练绑定必须保持false并说明旧SFT prepare尚不能消费新版。检查hash/配置/来源/Example/裁定类型替换、final split越界、输出替换、稳定构建和失败不留下成功manifest的行为。

材料核验覆盖固定13例、完整P/C/IDs/loss/causal mask、唯一EOS、右padding、原长度审计、固定parent tokenizer/格式身份与新revision/freeze绑定。先读原计数误标、材料顶层revision反例及修正；保留原349e manifest与两次旧构建。原两条编码路径发生在11:09–11:11 UTC，当时HEAD为6c81且新模块未提交；`d64531c6ae648b6f314c9b2a5b10b321f5adedf9`是后来保存的原源码字节提交，不是原运行提交。后续f7仅静态重封装，两路径各28份材料payload与原字节相同，新增编码0。不得用本轮新时间或源码冒充原编码。

使用现有默认纯CPU环境运行适用回归和少量有意义的独立反例。D1的1,193是最终默认766/48跳过，加未受修改影响的旧CPU分组427/0；53个新测试已包含、110 subtests另列。无需重复不受本修改影响的427旧分组；不得为补齐旧1,186分母而启用48个额外真实tokenizer fixture。固定13例额度已用完，R1本轮真实分词次数为0。

检查现存sdist/default wheel/从实际sdist重建wheel的内容、RECORD、metadata和62包文件与精确候选的绑定。允许一次用已有wheel和已有纯CPU依赖的隔离临时target安装，复核新build/verify入口与默认依赖边界，不创建持久环境或依赖。不要求重新生成同字节归档。必要时最多一次全量新版CPU构建和一次原13例材料静态核验，使用全新目录；独立小fixture不在此全量次数内。私有新增制品≤1GiB。CPU检查无必要时不重复；无模型/框架/GPU、真实分词、下载、业务API或浏览器重试。

本轮只允许新增`reports/review/P02-quality-adjudication-r1/`及`coordination/handoffs/P02-quality-adjudication-review-r1.md`。不修被审实现，不修改协调状态、台账、公共配置或其他worktree。全部原命令、失败、源码epoch、真实数组/归档和旧证据保持，新增检查附argv、UTC、退出码、stdout/stderr与源码绑定。公共报告不含私有路径、来源原文或完整来源/Example ID。

给出精确候选的PASS/FAIL/BLOCKED和P0/P1/P2、发现/证据及必要修订建议，完整封存、普通提交/推送、原生交接后结束本轮。重复命令或同候选复读不增加正式失败轮次，S0按稳定issue维护五次规则。Q1另审实际处置与材料语义；技术PASS不等于G-DATA或P04放行。
