# P05 G4｜生成前原创 train 语料 Q1 审阅

状态：READY；owner Q1。S1 派发精确授权提交，复用 Q1 独立 worktree，新分支 `codex/q1-p05-g4-corpus-r1`。这是固定数据包的语义与分组审阅，代码包技术验收另交 R1；当前真实候选和正式偏好均未生成。

固定候选包共20任务、12个 family、10类别、1个共享工具/schema连通组。S1 已核对文件身份及 D1 的32条正向替代策略和20条反例 CPU 证据；这不代替 Q1 判断。完整内容、oracle、authoring 和原始轨迹仅在派发给出的私有快照及只读索引中，禁止进入公开提交。

- tasks.json 文件 SHA256：`d9fc455fa667bc323249bc5907571f1e38b446bc97f4f4b3da24a813d9649030`。
- package manifest SHA256：`41284ee99539c9eebb8ba8eec53e50f4811a4ee48aa4b3f4ba1f069ca0d577d0`。
- S1 快照索引 SHA256：`3bf2f4664fb185e9595dad044b57691ef5979519a0e89d2402fec3b274c6fea0`。

Q1 对20个任务逐项检查：提示足以确定可执行目标；答案、字段、数字、日期/对象/版本准确；所有已知合法替代策略正确；“恰好一次/指定两工具/返回字段”等限制确实来自任务提示；多步依赖要求先观察后调用；故障日程与可恢复步骤相容。用现有确定性工具与 oracle 做有区分力的独立 CPU 复核，不仅抄录 D1 的 PASS，也不机械重复所有相同测试。

核对来源为新原创 train，未把 P03 的10个公开开发例换 ID 复用；共享完整工具/schema明确披露，不能声称与 P03 schema 隔离。基于索引所列冻结 P02 grouping metadata 检查 train/validation/test/ood_test 全部 group；验证该分组根与冻结 v3 的关系，不读取 held-out prompt/答案用于创作。新分量若触及正式 held-out 应整体隔离，仅新增语料可处置；P02/P03身份不改。当前20任务共享1个group，未来同组只能报 seen-group 诊断。

审阅现有 authoring 对有限 oracle 的语义边界：不把未匹配枚举本身当作错误证明；合法但未枚举者应 unknown/tie，而不能成为 rejected。评估这一语料是否适合按 [G4协议](P05_G4_PROTOCOL.md)生成候选，明确缺陷对哪些任务及后续偏好判断有影响。不要把 scripted CPU 轨迹当真实 chosen，不填写任何真实偏好 PASS。

允许：只读本任务输入；在自己的私有目录保存逐项判断/证据和有界独立 CPU 检查；新增公开摘要 `reports/reviews/P05_G4_CORPUS_Q1_R1.md` 与交接 `coordination/handoffs/P05-g4-corpus-q1-r1.md`。公开只给统计、hash、结论及定位规则，不复制正式任务原文或原始材料。禁止改实现、数据、配置、共享状态、依赖，禁止GPU、真实模型、训练、sub-agent或新聊天。

交付精确 review commit、PASS/REQUEST_CHANGES、每项实质问题、实际检查命令与证据索引。本轮只验收生成前语料；正式偏好池冻结后的 Q1 分层审阅与严格大于5%规则仍须另行实际执行。
