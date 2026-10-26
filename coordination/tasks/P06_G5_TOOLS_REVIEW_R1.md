# P06 G5｜独立工具集技术审核 R1

owner R1 AI；复用自己的隔离worktree，从S1派发的精确集成提交建立 `codex/r1-p06-g5-tools-r1`。先实际读取avoid-overkill。审核对象是E1的精确候选与私有证据索引，二者由S1消息绑定；只审核[新工具任务](P06_G5_TOOLS_CPU.md)，不评价尚未交付的模型后端或最终测试效果。

先回读E1实际命令、109项工具检查和四域真实owned child的两步输入/输出/回收证据，再做少量独立检查。重点是固定catalog_id选择在parent与child一致、subset工具白名单与实际实现/sourcehash绑定、旧catalog.py/default manifest/registry_hash逐字节保持。检查新8工具的参数/输出语义能区分发布计划与实况、事件与规则、构建与套件、物理空间与配额；选择至少一个错误catalog或source绑定反例及一条真实工具调用独立核对。复用未受影响的旧超时/取消/一次性ValidatedCall证据，不重跑ML矩阵或以重复109项作为独立性证明。

只能新增 `reports/reviews/P06_G5_TOOLS_R1.md` 与 `coordination/handoffs/P06-g5-tools-review-r1.md`，私有检查放 `.toolalign-local/review-p06-g5-tools-r1/`。不修生产代码，不改E1报告、旧审核、共享状态或依赖；不用模型、GPU、远端或新依赖。可复用已有轻CPU环境，保存实际命令、退出码、受检精确源码和证据索引。

交付精确commit、PASS/REQUEST_CHANGES及新问题；若有实质发现，给可复现边界、稳定issue ID和最小修正建议，按REVIEW_POLICY建议计数。这是工具实现技术审查，私有L1任务的语义/分组由后续Q1另审，不能提前宣称held-out隔离或模型效果。
