# P02-QUALITY-AUDIT-REVIEW｜扩展审计技术独立复核

状态：CHANGES_REQUESTED，原精确5270正式review964505512b56af927e4022aab260ab5a91ca5b86为FAIL/P0/P1=0/P2=1；S0核验9,673路径及27原命令，R1原生空闲。四种表现同属TYPE-001、首次正式未通过1次；见[接收报告](../../reports/S0_P02_AUDIT_TYPE_FIX_HANDOFF.md)。以下原范围与中间证据保持。

- owner：现有独立R1，gpt-6-astra / max；新branch `review/p02-quality-audit-r1`。
- 精确待审候选：`5270d1e9bdadb9db36deac7ba9b2e256b267b831`；基线`86b80bada50ac7c8f4b3910e3831a397ed65a853`，内容`e5030e9`、固定采样器`7298456`；[Draft PR13](https://github.com/kris0516/ToolAlign/pull/13)。完整S0授权SHA和私有路径另行给出。
- 契约：plan-v0.1 / coordination.v1 / toolalign.contracts.v1；ADR-0022/0023及审核政策保持。

独立审查完整10个新增文件和本轮证据，不能只审核最终文档。目标是确认固定抽样、来源/完整目标与前缀展示、已有判断导出、token-mask材料核验和证据报告忠实。Q1负责扩展发现的语义裁定；技术PASS不能证明全库语义正确、放行G-DATA/P04或用程序替代逐条语义阅读。

先绑定438候选/428不变基线、E1完整seal `adcf1a3ffd22a3803afc4cce7914f3bb37ee515a2eee282733521b05ff349889` 与receipt `b4b9d5898594d2c9fc9026ea75a197c4b82ee67b78a6afaa745fbb93fcc9306c`，保存新scope intake及身份。原采样manifest `cfbfd97125b52ff60e7ae39db8127936a7a55bc6e8b0161244f27c055b0596d3`、完整180判断seal与16材料seal不可改变。S0已核验4,536当前路径、26条原命令和原失败，证明 `eb50aab537f8aba07a1930159656965e2555858fea33b00861c199dd7786a32a`，仍须R1自行检查关键行为。

切换前先核验S0旧轮交接证明 `bda9b18fc8c557300b186cea41411cbe0f1f1a6058666225c8242cc6b75cf211` 及其450份公开文件副本映射，以原`1e45cf2` Git和不可变副本保存旧公开字节；不要把新checkout后的公开路径当作仍等于旧seal。旧`review/p02-quality-r1`分支、旧scope的3,216私有文件、186链接及八个测试目录保持。新身份只写新scope，不覆盖旧根identity或旧封存；新授权副本从本次完整授权提交读取。

必要验证：12项原创取样fixture；在新私有目录最多一次真实输入重放，独立核对96 train/24 validation和六个定向批次、去重/原审排除/不足池、来源全部有效Example、group/split及先冻结后判断。程序可读取已授权原文件定位允许来源，不向模型展示或语义评判heldout；抽样后不得按结果补选。另做有区分力的反例，检查未调用工具参数/无有效目标、重复来源/多决策覆盖等实际边界，不重复已有同义测试。

核对展示与聚合脚本未丢完整source/schema/前缀/有效目标、不以字符串复用误替内容、不读取原文指令执行操作；在新目录最多一次已有222判断汇总/视图重建，核对222来源/251决策、随机与定向分母、87 Action问题的24 fail/63 unknown、单独advisory与79建议、已有issue override和CSV/JSON逐字段来源。对必要字段被替换或错配作有限新反例；不重写原判断。抽查16份既有材料完整数组/身份与失败修正，不运行tokenizer。检查所有10个公共文件的去敏范围和引用、日志执行时HEAD/工作文件映射、两次原exit1及修正、737普通私有文件和1个不跟随的fixture链接记录。

只可新增 `reports/review/P02-quality-audit-r1/` 和 `coordination/handoffs/P02-quality-audit-review-r1.md`；不改待审实现、数据、其他worktree或协调文件。新私有scope目录保存身份和授权，旧R1运行/封存原件保持。仅现有CPU环境、PYTHONDONTWRITEBYTECODE=1，新增私有制品≤1GiB；无新环境/依赖/包构建、模型/分词/框架/GPU、网络业务API/浏览器、正式评测/训练。无变化的生产全套测试不重复。

正式PASS/FAIL/BLOCKED、P0/P1/P2清单、精确候选与完整review SHA、命令/退出码/原失败/输入保全及封存后结束。纯技术边界的代码失败与既有语义问题分别登记，但不得改名规避同问题第五次升级。不要自行给Q1或D1发新实现范围。
