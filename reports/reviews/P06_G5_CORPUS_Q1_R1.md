# P06 G5 L1 语料与 A2 输入独立 Q1 审核 r1

**结论：REQUEST_CHANGES。本候选暂不能冻结为正式 L1 输入。** 全部 48 题已逐项审阅，发现两项 P1 问题：16 条多步/恢复题缺少模型观察先后的评分约束；一条被遗漏的新旧语义连接使全部 48 题按冻结规则应整组隔离。候选原记录为保留 48、隔离 0、1 个连通组；Q1 加入有据语义连接后的处置为保留 **0**、隔离 **48**。这两个问题各建议登记首次正式未通过、连续计数 1。A2 的四组开发回放输入审核 **PASS**。

实际审核者为 Q1 AI，范围见[本轮任务](../../coordination/tasks/P06_G5_CORPUS_Q1_R1.md)、[语料任务](../../coordination/tasks/P06_G5_CORPUS_CPU.md)及[冻结协议](../../coordination/tasks/P06_G5_PROTOCOL.md)。受检集成头为 `2b47be95bc685e1ec11e99b8171d5b2a7d11e1ea`；D1 实现为 `72b18ad9c47da4932857cb53400b6a3c9ead6aad`，交付为 `d4c4251a0e676d39f30c62c6c767f274987501ca`。Q1 未修改候选、生产代码或共享状态。

全部 48 题的工作目标、答案值及 JSON 类型有题意依据；调用目标、次数及禁止额外读取的要求均已明确。三题的两种合法参数顺序均有正向证据。无需工具、追问和拒绝题的结构值由题目明确要求。逐题记录绑定模型可见投影、真实 schema、oracle、全部允许策略、fault schedule、正反脚本和实际执行证据。执行语义分项为 **32 PASS / 16 REQUEST_CHANGES**；独立测试隔离分项因整组连接而全部未通过。

| 稳定 issue ID | 实证与影响 | 关闭条件 |
|---|---|---|
| Q1-G5-CORPUS-001，P1 | 把一条多步题的两次调用预先放入同一 Action，再给正确 final，实际被判 success；一条真实 owned block/timeout 恢复题同样误判。两次调用都发生在 model_decisions=1、tool_rounds=1，第二调用提交时模型尚未收到首次观察。8 条多步和 8 条恢复题都有这项未编码要求。 | 由 S1 协调受影响的评分约束，使这些题能检查后继调用来自观察后的新决策；两条反例应失败，原分轮正向及合法等价策略应继续通过。若采用隔离处置，须保留误判历史并排除其正式使用。 |
| Q1-G5-CORPUS-002，P1 | 新缺参题与 G4 既有 missing-field 任务同为“保留一个已给标量、返回明确点名的缺失字段、禁止调用、输出 clarify”。字段与实体改名后，答案构造和空执行策略相同，未执行的新工具目录不能区分这个任务程序。作者仅凭查询对象/缺失字段含义不同，未登记这条 family 连接。 | 登记有据语义连接并按冻结规则隔离整个相连组件，保存全部已查看 ID 和理由；不能通过删去连接题或改 family/group 名恢复其余题的独立测试身份。 |

第一项的根因位于[语义 oracle](../../src/toolalign/evaluation/oracles/semantic.py)：它将 execution/observation 展开为工具步骤序列，再匹配允许策略；保留了工具执行顺序，却没有保留模型决策边界。[Harness](../../src/toolalign/evaluation/harness.py)会顺序执行同一 Action 内的多个调用，全部执行后才把观察写回下一次 ModelInput。因此，两条实测反例与正确分轮轨迹产生相同的工具步骤序列。此发现针对本轮题目的明确依赖要求；不要求禁止其他任务中合法的同轮独立调用。

第二项是逐题语义判断，并已保存新旧题目、字段映射、相同答案程序和对应旧任务身份。它有明确的作答流程证据，不由共享 `clarify` 标签单独推出。Q1 向现有[分组闭包](../../src/toolalign/data/evaluation/audit.py)加入这一条语义连接后，原 48 题组件连接到 10 个 P03 开发节点和 20 个 G4 train 节点，全部触发 `old_data_component` 隔离。候选文件保持原样；审核中的 0/48 是冻结规则要求的处置数量，待 S1 接纳落实。

元数据部分重新核对 P02 的 11,300 条记录、3,517 个旧组及实际 tool/schema/normalized-schema/source/template/family 键；不加语义连接时，构造出的完整审计与 D1 交付一致。四域通过共同拒绝 family 连为一组，不能作为四个独立统计单位。P02 冻结 v3 manifest 和 S1 指定的既有分组根身份匹配；未读取 P02 保留测试 prompt 或答案。2,568 对 trigram 比较及新旧最大 Jaccard 0.09375 是词面证据，不能替代此次发现所需的语义审阅。少于两个独立组时仍不计算 cluster bootstrap 区间或 leave-one-group-out。

| 证据范围 | 实际结果 |
|---|---|
| D1 已绑定 CPU 轨迹复用 | 51 条正向、48 条反例逐条核对响应、完整历史投影、oracle/registry 身份并重评分，结果保持 51 success / 48 failure；199 个 owned child 的回收记录通过。未重跑该矩阵。 |
| Q1 新增真实 CPU 检查 | 多步预提交、超时恢复预提交两条应失败却 success；JSON 同值数字与键顺序变化一条 success；boolean 代替 number 一条 failure。共 4 条轨迹、10 个 owned child，全部回收。 |
| 原恢复正向可行性 | 8 题均有真实 transient 或 timeout 后重试再 final 的轨迹，遵守 3 次决策、2 轮工具、30 秒。可行性通过不消除第一项错误策略误判。 |
| ModelInput 与长度 | 全部实际输入仅 messages/tools；答案、group、faults 和 oracle 留 host。复用并逐条绑定固定 tokenizer 的 48 条初始和 104 条正向历史测量；初始最大 924、历史最大 1,340，加 256 最大 1,596，无截断。 |
| A2 | 4 组 × 3 个纯 ModelInput 均还原到 P03 开发资源；每组顺序为同一请求两次，再一个不同请求。tenant、顺序、seed 42–53 和输入 hash 一致，最长 1,299 tokens，共享前缀测量已绑定。正式 cache 命中、延迟和模型输出仍 NOT_RUN。 |

Q1 实际运行 `probes.py`、`audit.py`、`finalize_review.py`，均 exit 0；前两项分别记录反例和证据/闭包结果，最后一项封存逐题判定。脚本、真实轨迹和命令记录位于本次私有交付目录。公开变更只含本报告及[交接](../../coordination/handoffs/P06-g5-corpus-q1-r1.md)，并完成文档链接、差异和公开内容检查。

| 输入或交付 | SHA256 |
|---|---|
| D1 evidence-index，177 份文件全部核对 | `b77873d5954f6488a06c2fe94a7a695bdb7b99290e80d1b8612cab6642939f64` |
| S1 intake | `65965505c038199529b911858025bc1fa03a00d4b20aa421138bf133fe5d2565` |
| 原 L1 tasks 文件 | `10a842b4a0c2d15470ba9d61e010621a8dc0807ce5a9e4c0cc552b994b67d70e` |
| A2 inputs 文件 | `ec282f4779deca1815af39e2c68c846e831c184965318f3550eeaff973d03166` |
| Q1 逐题判定 | `c1e33dd615ef88850836393028f924949f9d5b26c93eee423a2e9bc2a14c7db8` |
| Q1 review-result | `c1e2135a3723c84413dacc368b7486b24d598cf03367856a9d139d3d79a3a53f` |
| Q1 evidence-index，203 份文件 | `f53c050cd6847654836c943a6f74a82287817d81232960354f712b87fbe1aa6d` |

正式模型评测、GPU、训练和偏好生成均未运行；scripted 结果不计为模型效果。按[审核政策](../../coordination/REVIEW_POLICY.md)，两项首次未通过由 S1 继续组织修订或有据隔离，不触发第五次未通过的整体暂停。Q1 不代签用户，也未更新共享失败台账。
