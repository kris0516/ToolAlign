# P06 G5｜观察评分与历史隔离参考技术复验 R1 r2

owner R1；等待S1提供T1/D1精确候选与集成头再启动。使用原独立worktree，分支 `codex/r1-p06-g5-oracle-reference-r2`，先实际读取avoid-overkill。对应Q1-G5-CORPUS-001/002，原首次未通过及原48题隔离不变。本轮只复验实现修订；新28题的资格由后续Q1逐题审核，不能由实现PASS代替。

观察oracle：从两条Q1原预提交反例、合法分轮轨迹和T1交付出发，检查显式版本选择确实进入G5入口，未知或不完整payload保持unknown，v1源码及默认行为保持；依赖约束必须在一次实际观察之后出现新的模型决策，不能仅靠调用/轮次数量或任意后来的观察。保留多种合法策略、数值等价和合法独立batch。复用绑定的T1真实owned进程证据，独立选最少有区分力的反例验证即可。

历史参考：核对D1从原48完整包及Q1语义桥重算后retained=0、quarantined=48，原包字节未变；冻结参考确实包含P02所有split metadata、P03、G4和原48的工具声明、schema/normalized-schema键、family、语义及近重复边、完整组件成员。独立验证新节点连接任一旧G5节点时会沿完整历史组件隔离；catalog或函数改名不能丢掉其余真实连接。历史G5参数不用时，原audit调用行为保持。不要重跑原99条轨迹或所有无关数值矩阵。

按真实源码/输入绑定给两个组件分别PASS/REQUEST_CHANGES及稳定问题ID；同轮多个反例或引用旧结论不新增失败次数。公开仅交付 `reports/reviews/P06_G5_ORACLE_REFERENCE_R2.md`、`coordination/handoffs/P06-g5-oracle-reference-review-r2.md`；私有证据在 `.toolalign-local/review-p06-g5-oracle-reference-r2/`，给精确commit和evidence-index。不改实现、数据、共享状态，不装依赖/固定模型/GPU。S1接纳后再推进新语料接口和Q1正式复验。
