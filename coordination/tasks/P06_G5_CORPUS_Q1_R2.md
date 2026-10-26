# P06 G5｜关系任务逐题语义与隔离复验 Q1 r2

owner Q1 AI；等待S1派发D1精确候选、完整参考及集成头后启动。使用原独立worktree的 `codex/q1-p06-g5-corpus-r2`，先实际读取avoid-overkill，按[冻结协议](P06_G5_PROTOCOL.md)、[构造边界](P06_G5_L1_REPLACEMENT_PLAN_R2.md)、[语料范围](P06_G5_CORPUS_CPU_R2.md)与[审核政策](../REVIEW_POLICY.md)执行。本轮正式复验Q1-G5-CORPUS-001/002，原首次失败和48题永久隔离保留；不代修题目、实现、图或共享状态。

逐题阅读全部新保留任务的可见输入、真实工具声明/数据、oracle及每个合法策略、故障表和作者正反轨迹。关系算法须实际影响参数、结果或证据选择；拒绝仅改标识、抄字段或复制缺字段名的旧程序。单工具及恢复须有一步读取后的实质推导，无工具题必须给全关系数据，澄清须由真实观察揭示不可同时满足的约束和需用户选择的取舍。答案结构、类型、允许调用和次数须有题意依据，等价合法答案不能因固定措辞或遗漏策略被拒绝。

001复验使用显式新版oracle及真实harness：后继调用必须来自对应前驱观察之后的新决策，不能用同Action预提交、无关观察或事后补观察满足依赖。每个允许策略声明正确的依赖，独立调用的合法batch继续允许。恢复题的失败→重试→final须在3决策/2工具轮内，8个恢复ID及A1映射与实际可行性一致。复用D1全部已绑定轨迹，独立选择最有区分力的反例，不机械重复整个矩阵。

002复验核对完整P02全部split metadata、P03、G4及原48题的工具/schema/normalized-schema/source/template/family连接、语义边和完整历史组件传递隔离。不得读取P02保留测试prompt/答案；旧48组件任何成员仍不可恢复。对潜在语义连接给具体输入程序和理由，不能仅以一般行为类别相同断言重复。记录全部检查过的ID、真实保留/排除数量与group；四域不预设四组，不以目标数量倒推删边或改名。

核对固定tokenizer实测初始及最长合法历史加256≤2048、host oracle不进入模型投影、M0/M1/A1固定计划。A2沿用已接纳原12请求及原hash，仅核对身份，不重新造数据或把已有输入审核改写为性能PASS。实际模型推理保持NOT_RUN。

交付逐题判定、全部边界证据、两项问题分别PASS/REQUEST_CHANGES及稳定ID；同次复验多个反例不增加多轮计数。公开仅提交 `reports/reviews/P06_G5_CORPUS_Q1_R2.md` 与 `coordination/handoffs/P06-g5-corpus-q1-r2.md`；题目、答案和轨迹留私有 `.toolalign-local/review-p06-g5-corpus-q1-r2/`，给精确commit和evidence-index。S1回读后决定接纳与计数，技术实现PASS不代替本次逐题审核。
