# P06 G5｜关系约束工具技术审核 R1 r2

owner R1；等待S1提供E1精确候选、证据索引和集成头后启动。使用原独立worktree的 `codex/r1-p06-g5-constraint-tools-r2`，先实际读取avoid-overkill，按[实现范围](P06_G5_CONSTRAINT_TOOLS_CPU_R2.md)与[模型输出前构造边界](P06_G5_L1_REPLACEMENT_PLAN_R2.md)审核。仅CPU，不改生产实现、共享状态或依赖，不运行固定模型或GPU。

核对四种关系算法与冻结定义一致：逐阶段累计摘除后的每区quorum、整数左闭右开区间并集与补集、prerequisite→dependent DAG的目标传递闭包和精确无重复安装序列、按存活故障域统计唯一shard后与k比较。阅读全部8工具声明及固定资源，检查其输出足以支持关系推理，错误边界能改变结论。复用E1已经绑定的检查，只独立验证少量能区分错误累计、端点、前置方向或副本重复计数的边界。

核对新catalog从G5 reader、subset registry到真实owned child的一致性；旧两个catalog模块、声明与registry身份保持，旧输入消费保持。核对完整历史排除参考上的实际tool/schema/normalized-schema交集及所有命中处置；技术无交集不能替代后续逐题语义独立性审核。复用未受影响的进程取消、模型数值和旧oracle证据，不重复全库或原99条轨迹。

公开仅提交 `reports/reviews/P06_G5_CONSTRAINT_TOOLS_R2.md` 与 `coordination/handoffs/P06-g5-constraint-tools-review-r2.md`；私有证据放 `.toolalign-local/review-p06-g5-constraint-tools-r2/`，交付精确commit、evidence-index、实际源码绑定和PASS/REQUEST_CHANGES。问题使用稳定ID并给最小可复现边界。本轮不关闭Q1-G5-CORPUS-001/002，不提前接纳尚未审核的新语料。
