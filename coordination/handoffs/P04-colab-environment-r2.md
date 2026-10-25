# P04-COLAB-ENVIRONMENT｜E1 交接 r2

2026-10-26。**READY_FOR_REVIEW**，待 S1 派 R1 独立复审。

- 修订基点：`8faa75e7010290a11f13a8006fba5d4b16ac44f9`。
- 授权：`85b49e38f5410e87bf325c173891d8a778138cb5`。
- 原正式 FAIL：`2f449452636712f2622d40a3040a45034e56228f`；S1 映射 `81cb0be1f12cd9312035f00a378ea63dce52dbf6`。
- 实现：`a662567b9adf3c47d748b19e1c4bb8ca8689e4b9`；后续候选提交仅新增本交接和 r2 报告，精确 SHA 随原生交付/私有回执提供。
- 分支：`codex/p04-colab-environment-r2`；r1 分支、报告和失败证据保留，未合并 main。

两项已复现问题均已针对性修订：`P04-COLAB-PROCESS-001` 改为有界清理整个自有进程组并回收直接子进程；`P04-COLAB-RECOVERY-001` 在停止前核对该 endpoint 全部 run 的当前 Mac 完整副本及远端快照。[验证报告](../../reports/experiments/P04_COLAB_ENVIRONMENT_R2.md)保存原候选 2 fail、修订中失败与最终 **26 passed / ruff PASS** 的命令和边界。

**S1 接口事项：** `stop` 的本地 control spec 可增加 `recovery_directories`，值为“较早 run ID → 含 recovered.json 的绝对私有 run 目录”。不同 `local_root` 的合法 run 必须提供映射；缺失、错指、损坏或 tar 缺失均拒绝停止，重新回收后可继续。当前 run 使用当前目录，其他同根 run 自动按 run ID 定位。训练 run schema 和五个外部命令不变；本地/远端脚本同步部署，详见 [运行说明](../../docs/18_CUDA_RUNTIME.md)。

本轮私有范围为 `p04-colab-environment-r2/`，包含授权副本、未改写的 R1 原材料、原候选复现、两个修复复现、实际命令回执、实现绑定核对和最终回执。R1 复现代码原件未变；不同结果写入独立目录。精确绝对路径仅通过私有交付提供。

复用唯一 CPU 环境；GPU/SSH/新安装/真实模型/训练均 0。依赖锁、T1 训练源码和共享状态未改。T1 跨 session 子进程修复及最终组合验证单独进行；真实 Colab/Linux/CUDA/跨实例恢复仍 **NOT_RUN**。两项正式失败计数由 S1 维护，本自测不替代独立关闭结论。
