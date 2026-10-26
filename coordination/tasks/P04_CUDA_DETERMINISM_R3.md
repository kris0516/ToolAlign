# T1｜P04 CUDA 严格确定性策略

状态：READY。owner T1，协调者 S1。代码基线 `fee99c83ac6e2aeebbb8d565087eb5a80966ac26`；在既有隔离worktree建立 `codex/p04-cuda-determinism-r3`，从S1本任务授权提交开始。原候选、分支和证据保留。

[同状态诊断](../../reports/S1_P04_CUDA_RESUME_DIAGNOSTIC_R1.md)已将下一步收敛到CUDA反向确定性。T1对应版本源码核对支持 [ADR-0032](../DECISIONS.md) 的最小路线。共享配置 `configs/sft-cuda.v2.json` 由S1冻结，SHA-256 `ee235d612b2552be5927b4ff790887a34b088ab842f78a15fcb8212323b60045`；逐字节接入，不能自行改动。v1保持原字节。

实现范围：`src/toolalign/training/cuda_sft/**`、受影响的 `tests/training/test_cuda_sft*`、新增 `reports/P04_CUDA_DETERMINISM_R3.md` 与 `coordination/handoffs/P04-cuda-determinism-r3.md`。活动loader及CONFIG_SHA256直接切到v2；训练子进程在GPU lease内、首次CUDA调用前设置workspace和严格确定性，贯穿加载、forward、backward/recompute与验证。父进程/import/prepare不设置策略。runtime identity从实际进程读取strict、warn_only及workspace，与原源码/配置/数据/依赖/设备身份共同严格绑定。

不增加多版本选择、后端切换或自动重试，不吞掉确定性错误；不改变SDPA、checkpointing、LoRA、损失、优化器、mask、选择和数值容差。旧v1 checkpoint不转写为v2，不为读取它而放宽身份校验。旧诊断脚本按其原提交保留，不扩展新探针框架。E1控制器和依赖锁保持原样。

使用既有共享CPU环境做必要的策略执行/真实读回、无import副作用、身份不符拒绝及受影响协议/恢复用例；每命令≤300秒、2线程、私有新增≤512MiB。真实模型加载、数据编码、SSH/GPU、新包安装和共享环境修改均0。无需重跑未变的数组、Colab控制或安装矩阵。

交付精确commit、变更与命令证据，明确CPU不能证明CUDA确定性。R1独立审查后由S1合并和冻结真实验证：v2三步连续生成step2，新进程及新实例各恢复到step3，按原容差比较并回收/停止实例。稳定问题 `P04-CUDA-RESUME-001` 仍OPEN，先前诊断不计正式修复失败；本候选的CPU和GPU证据按同一实际修订处理。
