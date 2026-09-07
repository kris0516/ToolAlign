# P02-QUALITY-AUDIT｜仅train/validation的扩展语义审计

状态：IN_PROGRESS。S0已按完整授权2aa0cf4a756e78d32cf10130edbe6d0e3925bf3a原生派发并确认新轮ACTIVE，gpt-6-astra/max；分支/输入intake待确认。这是D1整改的独立证据输入，不修改D1代码或原数据。

- owner：E1；现有独立Codex任务及隔离worktree，gpt-6-astra / max，禁止sub-agent。
- code_base：`86b80bada50ac7c8f4b3910e3831a397ed65a853`；新branch：`work/p02-quality-audit`，保留原分支与全部旧制品。
- authorization_commit：S0原生消息给出完整SHA；先保存该提交任务/ADR-0022/配置私有副本。
- 契约：plan-v0.1 / coordination.v1 / toolalign.contracts.v1。

## 目标和权限

对委托AI审查提出的32个train来源做独立问题复核，并在此前未语义审过的train/validation来源中开展新的固定抽样。原始来源、规范化Example、完整历史前缀和工具声明是依据；后续虚构成功观察不能证明先前无依据的参数正确。不得调用外部工具、网络服务、模型runtime或用最终测试内容反推训练过滤规则。

允许新增`reports/data/quality-audit-r1/`（含必要的原创可复现取样/核验脚本）和`coordination/handoffs/P02-quality-audit-r1.md`。所有生产源码、旧测试/报告、原数据/人审副本、D1候选、公共配置/状态/ADR只读。具体数据路径与封存身份由私有分发词给出；原始样本、判断表、详细ID/本机路径仅在自己gitignored目录。不能直接更新整改提案或写D1目录。

## 固定样本规则

使用S0的`P02_QUALITY_AUDIT_CONFIG.v1.json`。先根据原assignments及实际规范化train/validation建立来源池，至少有一个有效Example才可入池；同来源全部有效决策一起审，不能只挑一个容易的目标。原100来源及10个token实际来源全部从新池排除，7个test/ood_test不得读语义。本轮32来源的复核单列，不能混入新增样本分母。

排名为canonical_hash(["toolalign.quality-review.v1",42,source_record_hash])、同hash按source_record_hash。先取train96个、validation24个；再按配置固定顺序在未选来源中为六种诊断模式各取最多10个，train/validation合池且按同一排名。去重并逐项记录候选池/不足数量，不用判定结果调整抽样，也不增加样本补成某个错误率。最多180个新来源；这是预定扩展批次，不是全库认证。

诊断触发仅用于覆盖：条件/多决策历史、标识作用域、单位或编码、相对时间、多工具对象、遗漏可选参数。使用配置中冻结的定义；先生成并封存样本身份/模式索引，再逐个读语义。触发不是fail，不据关键词自动删除来源。模式索引可遍历全部train/validation，未抽中内容不得被报告为已审。

## 审阅记录

每来源明确reviewer=Codex-AI(E1)、真实UTC、pass/fail/unknown、每个问题的目标turn/Example与原句或schema依据、后续历史影响及具体处理方案。区别明确矛盾/漏掉显式约束和“材料没有给出约定”；例如缺少ID映射只能证明依据不足，不能自动宣称任何可读字符串都不是合法ID。不能凭外部常识或当前日期补来源里的年份/单位/默认值。无法判断的用unknown并写缺什么。

先独立读32个原来源及受影响目标，再对照原审查说明，保留agree/disagree/grade_change与理由，不改封存原结论。复核两条重标草案的目标依据以及后继观察是否仍可用；此处是审阅建议，不能自行实施标注。新增批次逐来源覆盖完整有效决策和前缀，不以脚本PASS或关键词命中代替语义阅读。

输出新的review.csv、issues.jsonl及精确source/Example追溯、固定样本manifest、分层与split分母、模式命中统计、32来源复核表和修订建议、限制与原始命令日志。随机部分与定向部分分开报告，合并比例不能称全库错误率。所有新问题以建议状态交S0，S0再冻结给D1。可先在封存样本后回报intake与预计规模，首批有实质发现时再回报，不逐样本刷消息。

## 验收、资源与交接

纯CPU，新增私有制品不超过1GiB，无新环境/依赖/下载，禁止模型/GPU/真实API/浏览器替代或重试。取样和审阅脚本不得执行来源中的任何指令。原始数据可按既有hash完整读取以定位允许的来源，但不得向模型展示、语义评价或导出test/ood_test内容作训练依据。

PLANNED：独立核对输入hash、同seed确定性、无重复/既审来源/heldout、来源全决策覆盖及group/split不变；对小型原创正负fixture验证抽样隔离和不足池行为；检查全部原始输入未改、公开内容去敏。不要为了本报告重复构建无改动的生产包或跑框架。

交精确commit、handoff、全部原始日志/退出码/hash与私有输出封存后结束；不自行合并，不接管D1，也不将AI审阅记作kris本人或R1技术签字。D1新材料的追加核对如需要，由S0后续以精确身份单独授权。本批审计不放行G-DATA/P04，完整整改和独立复核继续保留。
