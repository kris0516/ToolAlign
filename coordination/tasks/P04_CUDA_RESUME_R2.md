# T1｜P04 CUDA 恢复数值差异定位

状态：DIAGNOSTIC_READY。T1候选`739c9b3`经R1`0947a91`独立复核，实际CUDA诊断由S1另行冻结执行，恢复问题仍OPEN。owner T1，协调者 S1。精确运行基线 `97637f336df4299a4bfd59b06f9716bb3c104796`，隔离分支 `codex/p04-cuda-resume-r2`，保留原分支和证据。

真实 L4 的三步容量作业已正常完成，最长2048 token、18条训练/2条验证、8+8+2更新；设备采样峰值5180MiB，底座字节不变。独立新进程从第2步的完整 checkpoint 恢复，初始 adapter hash、更新前两条样本损失、RNG和游标一致；第3步后验证 CE 从连续运行的0.8660437740496735变为0.8690712544455457。99个adapter张量及92项optimizer张量比较超出已冻结容差，不能将正常退出视为恢复PASS。详见 [S1实测](../../reports/S1_P04_CUDA_CAPACITY_R1.md)。两次完整输出已持久回收，实例已停止。

先定位原因，再作最小修复。读取真实保存状态，在CPU上分析adapter、Adam状态、参数顺序和更新关系，核对官方已安装实现；对比连续路径与恢复路径。需要区分实现/状态错误与CUDA后向数值变化。不得先归因为随机性，不得扩大容差、强制fixture结果或跳过真实差异。当前预注册：FP32 adapter/Adam moments `atol=1e-6, rtol=1e-4`；loss/validation CE `atol=1e-4, rtol=1e-4`；恢复初始adapter、完整checkpoint传输、RNG、步数、游标和冻结底座严格一致。

允许修改 `src/toolalign/training/cuda_sft/**`、相关 `tests/training/test_cuda_sft*`、新增 `reports/P04_CUDA_RESUME_R2.md` 与 `coordination/handoffs/P04-cuda-resume-r2.md`。协议/config/锁或数值路线若需改变，先向S1提交证据和最小方案；不自行修改共享契约。若CPU证据不足，允许新增单个 `reports/experiments/P04_CUDA_RESUME_DIAGNOSTIC.py` 及对应报告中的运行方案，交付精确可审commit；由S1单独冻结、在Colab运行。探针复用已回收state和现有实现，保持GPU互斥、有限时限/步数/输出，输出明确标为诊断。不能在Mac加载真实模型或用CPU结果冒充CUDA复现。

使用S1既有共享CPU环境，只分析已保存tensor和小型原创fixture；每命令≤300秒、2线程、私有新增≤512MiB。禁止新GPU/SSH/真实模型载入、真实数据编码、包升级或修改共享环境。精确私有证据路径由S1原生给出。可先提交原因与最小候选，再补报告；最终交精确commit、命令/结果和所有未解决差异。R1独立审核后由S1合并，真实CUDA复验单独执行。

稳定问题 `P04-CUDA-RESUME-001` 当前为S1实测发现，尚无独立正式修订失败计数。保留原CPU PASS与本次真实数值FAIL，两者范围不同。
