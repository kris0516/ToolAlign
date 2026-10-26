# R1｜P04 CUDA恢复差异独立复核

状态：READY。owner R1，协调者 S1。运行基线 `97637f336df4299a4bfd59b06f9716bb3c104796`；T1任务见 [定位任务](P04_CUDA_RESUME_R2.md)，S1事实见 [容量与恢复实测](../../reports/S1_P04_CUDA_CAPACITY_R1.md)。

在既有R1隔离worktree从基线建立 `codex/review-p04-cuda-resume-r2`。先独立核验真实回收state及预注册容差，区分状态恢复、参数/优化器对应、实际更新与CUDA数值因素；T1精确候选尚未交付，不对未交付修改出最终结论。任何GPU诊断需求先由S1冻结，R1不连接/分配GPU。

只新增 `reports/reviews/P04_CUDA_RESUME_R2.md`、`coordination/handoffs/P04-cuda-resume-review-r2.md` 及必要私有证据。可复用S1共享CPU环境读取已保存tensor、小型原创fixture及官方已安装库源码；不修生产/config/锁，不重跑未变的数组、安装或控制测试。CPU每命令≤300秒、2线程、新增≤512MiB；真实模型/新编码/SSH/GPU均0。

收到精确候选后，仅核对该问题的原因、最小修复与必要回归。若需要后续CUDA才能判断，明确CPU结论的范围，不能把CPU通过写成恢复通过。当前容差不得扩大；若证据要求数值路线/契约改变，由S1另行裁定。保留原CPU PASS与本次CUDA实测FAIL。

最终提交一次精确候选的PASS/FAIL与证据。稳定问题为 `P04-CUDA-RESUME-001`；当前为S1运行发现，正式修订失败计数0，重复读取同次差异不增加轮次。
