# P06 G5｜新关系语料接口独立技术审核 R1 r2

owner R1；S1派发D1精确候选、最终私有索引与集成头后启动。沿用独立worktree，分支 `codex/r1-p06-g5-corpus-r2`。先实际读取avoid-overkill，按[语料范围](P06_G5_CORPUS_CPU_R2.md)、[冻结协议](P06_G5_PROTOCOL.md)及[审核政策](../REVIEW_POLICY.md)审查。仅CPU；不代修实现或题目，不运行固定模型或GPU。

本次范围是D1新增的两个明确profile、实际oracle选择、私有新语料构造与消费证据。核对新catalog和观察oracle按显式profile进入authoring checks及当前G5 reader，ModelInput保持模型可见字段，旧v1包与原A2身份保持。复用已接纳的工具、观察oracle、历史隔离和分析实现证据；没有新差异或反例时不重跑这些矩阵。

核对全部实际检查过的ID、保留/隔离处置、完整历史参考绑定、连通group、8个恢复ID及M0/M1/A1固定计划；任何旧组件桥接都须传递隔离。检查每个保留题作者的正反轨迹、观察约束与进程回收记录，以及固定tokenizer的初始和最长合法历史input+256≤2048证据。独立选择最少量能区分profile错选、依赖预提交误判、旧包回归或图遗漏的消费案例，不机械重跑全题矩阵。

逐题语义和Q1-G5-CORPUS-001/002正式关闭由Q1承担，本技术审核不提前替代。已接纳的BFCL零题处置和A2输入审核不重开。交付PASS/REQUEST_CHANGES及稳定issue ID，公开仅 `reports/reviews/P06_G5_CORPUS_R2.md` 和 `coordination/handoffs/P06-g5-corpus-review-r2.md`；私有证据留 `.toolalign-local/review-p06-g5-corpus-r2/`，给出精确commit、evidence-index和受检源码/输入/命令绑定。S1接纳技术与Q1语义复验、完成主干集成后才执行GPU评测。
