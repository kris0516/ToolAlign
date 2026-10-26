# R1｜P04 CUDA 严格确定性策略独立审查

状态：等待T1精确候选。owner R1，协调者 S1。实现范围见 [T1任务](P04_CUDA_DETERMINISM_R3.md)，数值决定见 [ADR-0032](../DECISIONS.md)。在既有隔离worktree建立 `codex/review-p04-cuda-determinism-r3`，代码基线及候选由S1原生派发。

只新增 `reports/reviews/P04_CUDA_DETERMINISM_R3.md`、`coordination/handoffs/P04-cuda-determinism-review-r3.md` 和必要私有证据，不修生产/配置/锁或协调状态。核对v2与v1仅schema及三项numerics差异；实际训练子进程在首次CUDA调用前应用策略，import/父进程/prepare无全局副作用；runtime identity绑定真实strict/warn_only/workspace，旧checkpoint不能被伪装为新策略。

基于原诊断和对应版本官方实现审查；只做受影响的CPU行为检查，不重跑旧数组、安装、控制及保存-state矩阵。CPU每命令≤300秒、2线程、新增≤512MiB，使用既有环境。真实模型/编码/SSH/GPU均0。源码级候选可给出明确CPU技术结论，真实数值验收保持待定。

S1后续提供v2三步连续、新进程和新实例恢复的实际证据，再按原预注册容差独立接受或拒绝该同一候选。保存原v1 FAIL及所有诊断；本轮CPU审查不能提前关闭 `P04-CUDA-RESUME-001`，不按多次读取同一证据重复累计失败。
