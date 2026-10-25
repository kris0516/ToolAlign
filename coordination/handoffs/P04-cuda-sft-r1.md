# P04-CUDA-SFT r1 交接

Owner T1；协调 S1；状态 `READY_FOR_REVIEW`。代码与测试提交 `95cf14224ceb2ea3a3e817826aeef0e651eb459d`，本交接的后续提交只新增报告与交接单。基线 `61c2176d556fd0e4cfc2af00b16242dddcfadfd3`，授权 `04415938c749ea2e8dc1ef5e8ab7e30b777aeb47`。最终完整候选 SHA 通过原生交接回报。

交付新增 CUDA SFT 模块、三个原创 CPU 测试模块和逐字节复制的 S1 配置。没有修改默认依赖、旧 MLX/数据路径或共享看板。E1 已收到固定 `train --run-config FILE` 接口；全部模板、portable 格式与恢复规则见 [报告](../../reports/experiments/P04_CUDA_SFT.md)。

本轮自测：17 项全部通过，16.13 秒。覆盖独立 CE/梯度、long/short 样本权重、mask/EOS/右 pad/shift、尾组 7/2、官方 PEFT 的原创微型 Qwen adapter 更新与 frozen weights 不变、新进程完整恢复、best/last/rollback、非法 checkpoint 和重复 lease。另有实际 CPU 进程验证外部 SIGTERM、内部超时与正常完成后的自有子进程回收及信号处理器恢复。每条 tensor 轨迹参数不超过 4,096、序列 8、最多 3 updates、2 线程，单次命令少于 300 秒。

实际安装的专用 CPU 环境为 Python 3.12.14 / Torch 2.8.0 / Transformers 4.57.6 / PEFT 0.18.1。E1 Linux hashed lock 的 48 pins 可解析，Mac hashed lock 的 37 pins 与当前环境逐项相符。定点 ruff 与公开扫描通过，冻结契约沿用本轮未受影响的成功记录。`95cf142` 的 73 个包文件源码绑定通过，过程未导入模型框架。

保留失败：首次 CE 测试容差低于一个 FP32 ULP，按独立误差证据调整为 2 ULP；新增反例发现缺失 Adam moments 的恢复缺陷，已修复并回归。S1 指出的 SIGTERM 退出缺陷已用实际 supervisor 和原创 CPU 子进程复现，修复前父进程退出后子进程仍存活；新增清理与信号处理器恢复后回归通过。初稿两处 F401 已移除。精确命令、退出码、源码 hash、失败及成功日志位于本任务私有 `checks` 索引，S1 可取阅；没有覆写旧任务证据。

恢复所需文件为完整 checkpoint 目录，不能只回收 adapter。`resume_checkpoint_sha256` 是 `state.pt` SHA；状态同时绑定验证 score 与历史 best 引用。当前第二目录 copy/readback 只报告 `remote_copy_verified`，外部持久化和新实例恢复需 E1 实测。

真实数据 prepare/rebind/新编码由 S1 按独立有界请求执行，本 worker 次数为 0。真实模型加载、GPU 分配/训练、CUDA capacity、跨实例 resume、正式 SFT/DPO、模型评测和部署均 `NOT_RUN`。接续为 R1 技术审查、Q1 数据/mask 对应检查、S1 集成后签发容量运行；本包自测不替代这些验收。
