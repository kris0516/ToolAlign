# T1｜P04 CUDA resume r2 早期诊断交接

状态 `DIAGNOSTIC_CANDIDATE`；问题 `P04-CUDA-RESUME-001` 尚未关闭。已保存状态将重点收窄到 backward/梯度累积，尚未确定具体 CUDA 原因。基线 `97637f336df4299a4bfd59b06f9716bb3c104796`，原授权 `a48e3354daba2e1f81bd3f21d9b6895daef7e0fe`，单探针路径授权 `9ca0bf1490070b00ed24e14169601fc5869cf58b`。

本候选新增单个 [诊断脚本](../../reports/experiments/P04_CUDA_RESUME_DIAGNOSTIC.py)、两项小型 CPU 检查和[证据/精确运行方案](../../reports/P04_CUDA_RESUME_R2.md)。生产包、协议、数据、依赖、控制程序均未改。精确候选提交通过原生回报提供。

方案复用第 2 步 checkpoint 和最后两条 train 样本；物理恢复逐项核对后，对 checkpointing 开启/关闭各重复一次，共四组 backward、零 optimizer update，输出真实梯度与 attention 后端算子。GPU lease、300 秒时限、128 MiB 输出和 20% 内存余量仍受限；由 S1 单独冻结执行，原恢复容差不变。

T1 独立保存状态分析与原创 BF16/FP32 新进程 CPU 对照的原始脚本、命令、成功及失败记录保存在本任务私有证据根。CPU 对照的 81 个 tensor 比较严格一致；这不等于 CUDA 恢复通过。首次 fixture profile 错误和初稿 import-format 检查失败均保留。当前真实模型加载、数据编码、SSH/GPU/Colab运行次数为 0。

接续：R1 审核这个鉴别候选，S1 冻结请求并执行；按物理恢复、同模式重复、跨 checkpointing 模式的顺序判读。没有因未经验证的假设修改生产数值路径，没有扩大容差。
