# P06 G5 观察评分与历史隔离参考独立技术复验 R1 r2

2026-10-27（Asia/Shanghai）；实际审核者：R1 AI。**T1 观察依赖 oracle PASS；D1 历史隔离参考 PASS。** 两条 Q1 原预提交轨迹在显式新版本下由误判 success 改为 failure，合法分轮、多策略与数值等价保持。原48题已按已确认的语义桥整组隔离，retained=0、quarantined=48；其完整历史组件可供后续候选读取。S1 可接纳这两个 CPU 实现，继续新语料接口与独立 Q1 正式复验。

本轮复验对应[任务书](../../coordination/tasks/P06_G5_ORACLE_REFERENCE_REVIEW_R2.md)。原48题的正式评测资格未恢复；本报告不接纳后续新题。Q1-G5-CORPUS-001/002 的技术修订获得支持，正式关闭仍待 Q1 复验及 S1 登记，当前连续未通过各1、本轮增量0。

| 受检对象 | 精确身份 |
|---|---|
| R1 起点 | `959cf7ad948b2371b1aa4befa04026c5d513ce2b` |
| T1 候选 | `ecbb5202209582f57aee82ae490ae455e5f5dba0` |
| D1 实现 / 交付 | `2153c6823ed98db58782037acba7ca348e4010ed` / `f159b52d201efde370c572aed973651c68340120` |
| S1 联合集成头 | `1233d0f917bedc5ce1aca31ff514e3ec4e54d18b` |
| 原 Q1 判定 | `08d4c5a33cb77cf06dfafa373d3b693873f4abcf`，[首次审核](P06_G5_CORPUS_Q1_R1.md) |

R1 受检生产代码、测试、配置和契约与上述集成头一致。公开交付仅本报告和[交接](../../coordination/handoffs/P06-g5-oracle-reference-review-r2.md)，未改实现、原语料、依赖或共享状态。

## T1：观察之后的新决策

G5 实际入口按 `oracle_payload.version` 显式调用 `select_oracle`。`toolalign.semantic-observation.v1` 保留原答案及工具步骤匹配，并以每条策略自己的 `after_observation` 边要求：前项工具观察已发生，后项调用前出现新的 generating/parsing 事件，决策和工具轮次计数与该调用一致。仅增加调用数、借用其他策略的边或使用后来的观察不能满足依赖。未知版本及不完整 truth 返回 unknown。

原 `SemanticOracle` 源码和 `LocalHarness` 默认行为逐字节保持。新 payload 的空依赖列表明确允许独立 batch；数值等价及合法多策略继续由原语义匹配处理。

R1 核对 T1 索引的127份文件及7份源码/文档，复用最终受检源码对应的 **141项通过记录**。其中真实 G5 入口的4行原创运行均回读评分、模型输入及进程记录：依赖题预提交失败，其余三行成功；12个 owned child 全部回收、目录清理。传给模型的输入保持 `messages`、`tools`。

R1 直接以当前源码重评分 Q1 保存的8份原始结果，没有重跑原轨迹：

| 原证据 | v1 | 显式新版本 |
|---|---|---|
| 多步、恢复各一条预提交反例 | success / success | failure / failure |
| 对应两条合法分轮轨迹 | success / success | success / success |
| 两条允许的不同策略 | success / success | success / success |
| 数值等价与键顺序变化 | success | success |
| boolean 冒充 number | failure | failure |

新版本的答案和步骤与原 truth 相同，仅增加版本及明确依赖。作者 Q1 重评分后对新 oracle 的变动只有 docstring，R1 另核对了可执行 AST；本轮上述重评分使用最终源码。

R1 另运行 **1条原创真实 CPU 轨迹**：先独立 batch 两次读取，收到两份观察后再执行第三次调用。三次决策、两轮工具调用中，依赖 `[0,2]` 和 `[1,2]` 同时通过；在同一真实轨迹上要求 `[0,1]`，即使随后已有新观察、新决策，仍失败。显式空依赖和原 v1 均通过。该检查新增4个 owned child，全部启动、回收并清理；没有固定模型推理。

## D1：完整历史组件的永久隔离

R1 核对 D1 索引59份文件、4份最终公开文件和参考 manifest 的22份产物，验证原D1/Q1证据及输入共391份受保护文件的hash和长度未变。原48条记录、23个family、8个工具声明、8条恢复题身份均保留。`group-audit.json` 与 Q1 原审计逐字节相同；原调用不传历史参数时，当前源码重算仍得到相同文件及0条保留。

| 完整参考 | 独立核对结果 |
|---|---|
| P02 全部 split metadata | 11,300条、3,517个原group；train 10,033、validation 411、test 381、ood_test 475。原 assignments 与完整 tool-lineage hash 绑定，派生 normalized-schema 键与交付一致。未读取保留测试题面或答案。 |
| P03 / G4 / 原G5 | 10 / 20 / 48个任务；从实际记录重建工具、schema、normalized-schema、family、source、template及原group键，与保存节点逐项对应。 |
| 历史连接 | Q1 原组件的851条边仅把角色前缀 `new:` 映射为 `g5:`；含7条近重复和1条已确认语义边。完整图另有902条键连接，共1,753条边记录。 |
| 独立邻接表与遍历 | 3,595个节点、3,506个组件及成员与交付完全一致；包含所有未连接原G5的P02旧组。每个原G5节点都到达同一78节点组件：48个G5、20个G4、10个P03。 |

复用与当前源码相同的13项定点测试记录；未重跑14项不受影响检查。R1 新增验证在**完整历史参考的私有副本**中改名全部工具及版本，并反转 required/enum、显式写入字符串 `minLength:0`。一个有效的当前格式原创图节点与这些历史任务只共享两个 normalized-schema 键，不共享工具名、原始schema、family或题面键。真实 `audit_groups` 在不加载历史时保留1，加载后保留0，组件仍含全部78个旧成员。该节点未执行脚本或工具，也不是新L1题；原参考文件保持不变。

新增 `historical_g5_reference` 恢复已提供历史边并保留完整图，足以阻止通过删桥接题、函数/catalog改名丢失已知隔离关系。后续候选与旧任务的新语义等价关系仍须作者及 Q1 提供实际程序证据；词法和结构键不代表语义检索完备。

## 判定、证据与历史

| 稳定 issue ID | 本轮技术判定 | 后续处置 |
|---|---|---|
| Q1-G5-CORPUS-001 | PASS：两个原预提交反例均被显式新版本拒绝，合法分轮、多策略及独立batch保持。 | 新题须实际采用相应版本与依赖；由Q1正式复验，S1登记关闭。原首次未通过保留。 |
| Q1-G5-CORPUS-002 | PASS：原48题整组隔离、完整参考及传递闭包成立，原包字节保持。 | 后续构造须消费该参考及新增语义证据；正式隔离处置由Q1复验、S1接纳。原首次未通过保留。 |

新增实质问题0。两项独立检查均 exit 0，合计3.07秒；复用154项已绑定测试通过记录。新增真实执行仅上述1条 scripted CPU轨迹、4个已回收child；未重跑原99条轨迹或tokenizer矩阵，未安装依赖、下载固定模型或分配GPU。正式L1/L2、A1/A2模型结果保持NOT_RUN。

私有入口为 `.toolalign-local/review-p06-g5-oracle-reference-r2/evidence-index.json`，包含两包原证据副本、源码对应、独立脚本/命令/轨迹/图及结果。精确审核commit、索引SHA256和文件数随交付回报。

| 关键输入 | SHA256 |
|---|---|
| T1 evidence-index | `30f6908a62b05c45a7577c03a0b4a27cd415f5909a15fcaf4630bbb75ee4564d` |
| D1 evidence-index | `16445958531c53f5f4748b5550bf18a35a88d245e543dbfd89ef5859d8a2b356` |
| 原 Q1 evidence-index | `f53c050cd6847654836c943a6f74a82287817d81232960354f712b87fbe1aa6d` |
| 完整 reference.json | `9e24be0903bd821fc63b38018eb22c988c176caa28b5185d4948fcf3e56e5f44` |
| reference-manifest.json | `6ae740f9be378de15826b3af31dbd8ad6b27e64cd37b34f12afb14b73209fcc5` |

失败历史未改写：T1 的预修订预期失败，以及首次测试和证据脚本读取未序列化budget属性的失败均在原索引中保留；修正记录位置后对应最终检查通过。Q1 原反例、首次REQUEST_CHANGES及原D1证据保持。本轮不重复累计旧问题，也不以实现PASS代替后续逐题语义审核。
