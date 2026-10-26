# T1｜P04 CUDA 严格确定性 r3 交接

候选实现完成，待R1独立审核。授权 `e23ee150d2759419170750139c211d2d0ebe3805`，运行代码基线 `fee99c83ac6e2aeebbb8d565087eb5a80966ac26`；分支 `codex/p04-cuda-determinism-r3`。精确交付提交由原生回报提供。

活动协议切到S1冻结的v2；训练子进程在GPU lease内、首次CUDA检查前应用workspace和严格确定性，runtime identity读取真实strict、warn_only、workspace。配置原字节保留，旧checkpoint不转写，原完整身份拒绝规则保持。实现只修改两个生产模块。

[检查报告](../../reports/P04_CUDA_DETERMINISM_R3.md)包含实际命令、环境、失败与成功记录。10项定点CPU检查通过，五个变更Python文件的ruff通过；修改前5项失败已保留。未重复数组编码、Colab控制或安装矩阵。本轮真实模型、编码、SSH、GPU和新包安装均0。

`P04-CUDA-RESUME-001` 仍OPEN；CPU结果不等于真实CUDA恢复通过。R1审核后由S1冻结v2三步连续及step2的新进程、新实例恢复，原验收容差不变。
