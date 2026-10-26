# P05 G4｜语料类型约束 Q1 定点复审 r2

owner Q1，独立 AI 语义审核。S1实际派发时给出包含本文件的精确起点；在既有独立worktree新建 `codex/q1-p05-g4-corpus-r2`。先实际读取avoid-overkill；只读输入，不修改生产实现或共享状态。

复审问题为 `Q1-G4-CORPUS-001`。原Q1提交 `fd0e8f34f3e7bf80d70914e5177d84cc8386a50e` 的首次REQUEST_CHANGES保留，当前连续未通过计1。D1候选 `76e114fcecf60a92d03580283549cc4009f83df3` 只补明原第10、13项的版本答案须为JSON字符串及对应约束证据；其余18项语义、全部答案/策略不变，报告见[语料r2](../../reports/P05_G4_CORPUS_R2.md)。

固定新输入：tasks文件SHA256 `b9c6f18995579d8af1a58d137cafe9cc1c9f2f40279d9434aa85e2c7769eb015`，任务包canonical hash `4c9e7edaef35352a294aa8d62130847264645059dd5ce529fb528f926c339bd8`，manifest SHA256 `e7ab7b10728513662ddf3521e2c4b73b83eee7c7d50af31b469539a5f9d0427c`。D1私有证据索引SHA256 `b2b9e9801ba8c5f4455b845c43f3d2e72df636bdc715eebde3d5c960b105aee7`；S1已核对34份文件及实际authoring差异，接收证据SHA256 `b2a79decddcd618c02509670a104844b5d495f480c2dc8bdeaa93a13adbf5e7b`。私有位置通过派发消息提供。

核对原第10项→新第5项、原第13项→新第11项的完整提示、约束依据、答案/合法替代策略及D1四条实际CPU轨迹。判断字符串要求是否充分，数字反例是否确实违反当前提示。核对全20项身份映射和group hash传导：其余18项仅group引用改变、分组拓扑和P02四split绑定保持，复用r1未受影响的语义与分组结论，不重复全量52条轨迹或训练数据审阅。

本轮可读回并独立重评分既有四条轨迹；仅在发现证据缺口时增加有区分力的小型CPU探针，不需重跑全部原轨迹。保留原20项审阅分母、r1的18 PASS/2 REQUEST_CHANGES与真实审核身份。本轮没有真实模型候选，不计算偏好误标率或替代后续正式偏好池Q1审核。

仅交付 `reports/reviews/P05_G4_CORPUS_Q1_R2.md` 与 `coordination/handoffs/P05-g4-corpus-q1-r2.md`，精确commit及私有证据索引。给出问题PASS/REQUEST_CHANGES/UNKNOWN和新输入能否用于有界真实生成；若PASS，建议按原ID关闭并归零，历史不删除。无需人类签字。禁止修改原数据/工具/oracle、模型/框架/新依赖/编码/GPU运行、sub-agent、新聊天或其他worker文件；S1独占正式台账与执行放行。
