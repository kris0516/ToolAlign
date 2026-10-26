# P06 G5 关系约束工具独立技术审核 R1 r2

2026-10-27（Asia/Shanghai）；实际审核者：R1 AI。**PASS，新增实质问题0。** 四域八工具符合冻结的关系算法，显式新catalog经G5 reader、subset registry到真实owned child的链路通过。完整历史图及工具声明的tool/schema/normalized-schema交集均为0。S1可接纳本CPU工具实现，供后续新语料构造与Q1逐题审核使用。

受检候选为 `6f6a4974d254c8486417a1c4e51c15ba349a8012`，精确集成及审核起点为 `5c859cbb59c808ba941ec89a85fcf8f22e19d888`；实现者基线为 `1233d0f917bedc5ce1aca31ff514e3ec4e54d18b`。范围遵循[审核任务](../../coordination/tasks/P06_G5_CONSTRAINT_TOOLS_REVIEW_R2.md)、[实现任务](../../coordination/tasks/P06_G5_CONSTRAINT_TOOLS_CPU_R2.md)和[构造边界](../../coordination/tasks/P06_G5_L1_REPLACEMENT_PLAN_R2.md)。公开仅本报告及[交接](../../coordination/handoffs/P06-g5-constraint-tools-review-r2.md)，未改实现、语料、共享状态或依赖。

本轮不关闭Q1-G5-CORPUS-001/002，两项仍OPEN、连续计数各1、本轮增量0。原48题保持永久隔离；工具键无交集不替代新题的语义独立性审核，四域不据此认定为四个独立group。

## 算法与可区分边界

R1读取全部8份声明、每域两份固定资源及实现。读取工具返回完整有限关系；对应检查工具绑定同一关系ID。声明明确阶段累计、区间端点、DAG方向与必需集合、唯一shard及故障域含义。操作仅访问代码内固定数据，参数有界，未增加路径、网络或环境访问。

| 算法 | 独立检查的具体结果 |
|---|---|
| 逐阶段、逐分区quorum | `session-layout-1`依次摘除`[n1]`、`[n1,s1]`、`[s2]`、空阶段，各区剩余数为`(1,3),(1,2),(1,1),(1,1)`；前两阶段安全，首次失败为第3阶段，重复实例不重复扣除。另只摘除`n1,n2`时全局仍有3个实例，但north为0，因此失败。 |
| 整数左闭右开区间 | `snapshot-timeline-1`窗口`[4,24)`得到覆盖`[4,7),[20,24)`、补集`[7,20)`；窗口`[7,40)`把相邻事件合并为`[20,26)`，覆盖6、未覆盖27；`[44,120)`覆盖为空、未覆盖76。裁剪、相邻合并及边界外事件处理均一致。 |
| 目标的传递前置闭包 | `metrics-graph-1`目标为重复sender及孤立viewer，必需集合恰为base、codec、sender、viewer。`viewer,base,codec,sender`合法；交换codec/sender时明确报告`codec→sender`顺序错误；额外加入collector时因超出必需集合失败。没有把下游agent或无关节点加入闭包。 |
| 唯一shard与阈值 | archive失效rack-c/rack-d（重复rack-c）后，4个副本代表3个唯一shard，恰达k=3，可恢复。下述真实链路中journal失效rack-z后，3个副本只代表2个唯一shard，不能恢复。 |

上述包含9个新增直接算法案例及1条真实CPU链路。未重跑作者已绑定的2,550个区间窗口或两图各120个排列；缺失/额外/重复安装节点、错误ID、无效窗口、输入界限和深拷贝行为由源码阅读及既有定点证据支持。

## 新reader与执行身份

R1构造一条原创storage组件fixture，使用完整新catalog hash及实际两工具subset，经当前`read_inputs`读取，再将其返回的registry传入`LocalHarness`。脚本按三次决策执行读取placement、观察后检查rack-z故障、返回`{"recoverable":false,"unique":2,"copies":3}`。两份工具输出与独立写明的固定关系及预期结果完全相同，显式`toolalign.semantic-observation.v1`及依赖`[0,1]`评分success。

实际manifest全部绑定`toolalign.tools.constraints_catalog`；完整与subset身份明确区分。三次模型输入均只含`messages`和`tools`，truth及依赖约束保持在host。新增1个scripted模型child及2个工具child全部启动、回收并清理，sandbox为空。该链路验证CPU接口和工具结果，没有使用固定模型或计算模型效果。

| 身份 | 值 |
|---|---|
| 新catalog | `heldout-constraints.v1` |
| catalog源码SHA256 | `bfb4e6f8991bbfd4db9854ce85905e32a93f8b6adce3f1369480ef34ff8a953e` |
| 完整registry hash | `6f3623a97707e706afd49640c455f01e10fabcbc4de310dfa881ecd4a4b6ed05` |
| 独立storage subset hash | `2ae4c4b715f9b7a2dc2fe468110281a2f30521bf079f93f052af7bf6d6f1b813` |

旧两个catalog源码字节保持，完整、空集、各单工具共18种registry变体的tools/manifest/hash与变更前一致，默认仍为local-devops。旧reader的实际三行记录保持success、success、recovery-disabled failure，初始模型输入与旧工具manifest均已回读。新reader只明确加入第二个heldout catalog选择；executor、runner、旧oracle和冻结契约未变。

## 完整排除参考与证据绑定

R1使用已接纳的D1 `f159b52d201efde370c572aed973651c68340120`参考快照，重新核对三个固定入口及manifest的22份产物。参考包含全部P02 split metadata、P03、G4、原48题及历史语义/近重复连接。原retained=0、quarantined=48保持。

独立键计算覆盖3,595个历史节点和16,940份工具声明记录：P02完整tool-lineage 16,650份、P03 60份、G4 120份、原G5 96份及两个旧catalog 14份。对每个新工具计算三类键，并同时与图中键及完整声明键比较，8工具均无交集。逐工具键、命中列表及旧键计数与E1最终审计一致。作者首次冻结的声明/资源与最终实现一致，实现前、交付前两份审计结果相同；本轮不重算已接纳的历史连通闭包。

| 已绑定证据 | 使用范围 |
|---|---|
| E1索引93份、公开交付7份 | hash/长度逐一核对；7份文件与候选、集成头及当前工作树逐字节相同。 |
| 新工具/reader共58项、旧reader2项 | 复用53项未变工具检查及最终5项reader检查；原58项通过记录保留，随后补全reader fixture的truth只重跑5项。两项旧reader测试及其运行源码绑定通过，未把重复5项累加为新增测试。 |
| 四域8工具的真实执行 | 回读四对调用、参数、观察、新catalog manifest及8个已回收child；所有工具均实际执行过。 |
| R1三项独立检查 | 算法边界、reader到真实child链路、完整历史键交集均exit 0，合计2.12秒；新增3个child全部回收。 |

原旧reader测试在实际运行后，将工具description附加` tampered`并保存负例。R1首次证据脚本误把该最终文件当作运行输入，触发正确的schema拒绝；该脚本及失败日志已保留。依据未变测试源码在独立副本还原这一处变化后，SHA256精确匹配原run记录的`6c655c12a5dfb63fa2d59c9f76920a8d26ec4b2d1be595f150767235d859a205`，当前reader读取通过，原负例仍被拒绝。未改写原输入、候选或测试；这不是候选正式修订失败。

私有入口为 `.toolalign-local/review-p06-g5-constraint-tools-r2/evidence-index.json`，封存原93份证据、参考快照、实际源码、独立输入/轨迹/键审计及命令结果。候选索引SHA256为`33bb0de0a2fa3a75b38949b57e8391a3ef1a63b95886933cc7b07f388816e944`；参考SHA256为`9e24be0903bd821fc63b38018eb22c988c176caa28b5185d4948fcf3e56e5f44`，参考manifest为`6ae740f9be378de15826b3af31dbd8ad6b27e64cd37b34f12afb14b73209fcc5`。精确审核commit、最终索引SHA256及文件数随交付回报。

建议S1接纳本工具技术PASS，继续新语料构造和Q1独立审核。本轮没有新正式L1题、依赖安装、固定模型运行或GPU分配，未重跑原99条轨迹、取消矩阵或模型数值检查。正式L1/L2模型评测、A1/A2性能及001/002关闭均不由本结论替代。
