# P06 G5｜L1保留任务与开发回放独立语义审核 Q1

owner Q1 AI；S1派发精确D1候选与证据索引后，从指定集成头建立 `codex/q1-p06-g5-corpus-r1`。实际读取avoid-overkill，按[共同协议](P06_G5_PROTOCOL.md)、[语料范围](P06_G5_CORPUS_CPU.md)和[审核政策](../REVIEW_POLICY.md)执行。只做CPU审阅及必要的真实scripted反例，不生成模型输出、训练、分配GPU或修改生产实现。工具实现已独立接纳，本轮关注实际题目/oracle和隔离。

逐题阅读全部保留L1任务的模型可见投影、真实工具schema、host oracle、允许策略、fault schedule、正向与反例执行证据。检查任务有可执行的工作目标；JSON答案结构/类型、仅允许哪些调用及次数限制均有题意依据，不用oracle暗加约束。多解题核对等价策略，不因无害读取误判；无工具/追问/拒绝题不能凭某句未经要求的固定措辞判分。原模型只收到messages/tools，不收到答案、group、故障表或oracle。

恢复题必须在冻结3决策/2工具轮/30秒内有实际可行策略，真实transient或owned block之后能重试再final；多步题的后继标识来自首次实际输出。核对错误对象、日期/版本、相近工具语义、猜测缺失参数、伪造完成和多余调用等反例确实能区分错误与正确。复用D1全部已绑定的CPU轨迹，独立选择最能推翻结论的几个边界做真实检查，不机械重跑整个矩阵。脚本fixture的成功不是模型效果。

核对P02冻结manifest与其现有metadata、P03开发/G4 train的身份及隔离范围；不读取P02保留测试prompt或答案。实际工具/schema/normalized-schema/source/template/family传递闭包和旧组件桥接隔离必须与保留清单相符。四域不预设四组，近重复启发式不能写成完整语义检索。检查所有已看过但隔离的题目、理由和最终固定ID，不能偷偷换题或改group以获得更好的估计区间。

固定tokenizer的所有初始及正向历史输入须有实测长度，加256不超过2048且无截断。A2四组开发回放每组3个纯ModelInput，来源限P03开发资源，含重复请求与共享前缀的合法另一请求；不得根据最终测试输出制作回放。检查其输入身份、顺序、tenant和固定seed说明，A2的结论限定请求回放性能。

交付逐题语义判定与所用证据绑定、实际保留/隔离数量与group、必要反例结果、明确PASS/REQUEST_CHANGES及稳定issue ID。公开提交仅 `reports/reviews/P06_G5_CORPUS_Q1_R1.md` 与 `coordination/handoffs/P06-g5-corpus-q1-r1.md`，原题目/答案/轨迹留私有并给evidence-index及精确commit。Q1不代修数据、工具或共享状态，不替用户签字。正式模型评测仍NOT_RUN，S1回读接纳后才冻结运行。
