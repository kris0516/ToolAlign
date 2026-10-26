# R1｜P04 CUDA 严格确定性策略独立审查

状态：CPU PASS；S1实际三份运行比较PASS，交R1数值终验。精确候选 `f6f66545c17827fa442c38d4d3af52d6cb7231e3`；独立审查提交 `9212903fc8f86955ba713d75016bfd6bc3bd935f`，9项定点检查通过。owner R1，协调者 S1。实现范围见 [T1任务](P04_CUDA_DETERMINISM_R3.md)，数值决定见 [ADR-0032](../DECISIONS.md)。在既有隔离worktree建立 `codex/review-p04-cuda-determinism-r3`，代码基线及候选由S1原生派发。

只新增 `reports/reviews/P04_CUDA_DETERMINISM_R3.md`、`coordination/handoffs/P04-cuda-determinism-review-r3.md` 和必要私有证据，不修生产/配置/锁或协调状态。核对v2与v1仅schema及三项numerics差异；实际训练子进程在首次CUDA调用前应用策略，import/父进程/prepare无全局副作用；runtime identity绑定真实strict/warn_only/workspace，旧checkpoint不能被伪装为新策略。

基于原诊断和对应版本官方实现审查；只做受影响的CPU行为检查，不重跑旧数组、安装、控制及保存-state矩阵。CPU每命令≤300秒、2线程、新增≤512MiB，使用既有环境。真实模型/编码/SSH/GPU均0。源码级候选可给出明确CPU技术结论，真实数值验收保持待定。

S1后续提供v2三步连续、新进程和新实例恢复的实际证据，再按原预注册容差独立接受或拒绝该同一候选。保存原v1 FAIL及所有诊断；本轮CPU审查不能提前关闭 `P04-CUDA-RESUME-001`，不按多次读取同一证据重复累计失败。

实际补充：运行主干 `eb73fbcdb5f053509a396c59092e28d7c317cdd9`，生产文件等同已审候选。参见 [S1实测](../../reports/S1_P04_CUDA_V2_RECOVERY.md)。私有索引、完整checkpoint和33命令回执由S1原生提供。继续使用本轮两个允许文件追加实际验收；先保存旧CPU结论与失败历史，再从S1授权提交建立隔离分支 `codex/review-p04-cuda-determinism-real-r3`。仅对三份新证据做必要独立CPU核验，不重复既有CPU矩阵或原诊断。正式失败计数按同一候选的一次最终结论登记。
