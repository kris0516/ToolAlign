# R1｜P04 CUDA 确定性策略 r3 独立审查

2026-10-26。**PASS（CPU 技术审查）**。精确候选 `f6f66545c17827fa442c38d4d3af52d6cb7231e3`，授权 `e23ee150d2759419170750139c211d2d0ebe3805`，运行代码基线 `fee99c83ac6e2aeebbb8d565087eb5a80966ac26`。P0=0、P1=0、P2=0。

候选正确接入 S1 冻结的 v2 策略，CPU 证据支持进入有界真实验证。`P04-CUDA-RESUME-001` 仍 **OPEN**；原 v1 恢复 FAIL 保留，本次不关闭数值问题，正式修订失败计数增量为 0。

## 依据与改动范围

已核对 [S1 实际诊断](../S1_P04_CUDA_RESUME_DIAGNOSTIC_R1.md)的索引、完整摘要、恢复检查及四份 case JSON 的原字节绑定。恢复的 10 项检查一致、零更新；同进程重复梯度相对 L2 差为开启 checkpointing `0.0085657661`、关闭 `0.0086842069`，实际记录包含 FlashAttention backward。没有重跑保存状态或梯度矩阵。

对应 [PyTorch v2.8.0 实现](https://github.com/pytorch/pytorch/blob/v2.8.0/aten/src/ATen/native/transformers/cuda/attention_backward.cu)在 strict 开启且 warn_only 关闭时，把 FlashAttention backward 的 deterministic 参数设为 true；[同版 API 文档](https://docs.pytorch.org/docs/2.8/generated/torch.use_deterministic_algorithms.html)说明严格模式及相关 CUDA 矩阵运算的 workspace 要求。这支持本候选的干预方向，实际恢复是否落在原容差内仍需运行确认。

v1、v2 文件均与授权提交逐字节相同。JSON 顶层差异仅 `schema` 和 `numerics`，三项数值设置为 `true / false / :4096:8`。v2 SHA-256 为 `ee235d612b2552be5927b4ff790887a34b088ab842f78a15fcb8212323b60045`；v1 原摘要 `3d4785e1e130dd04990abb3767c23d92cdb7b18dad1d30cc6991f976cd44c9c4` 保持。

相对授权提交，T1 变更为 7 个允许文件，生产改动仅两个模块：`protocol.py` 切换活动文件及摘要；`runtime.py` 应用策略并新增两项实际身份读回。SDPA、checkpointing、TF32、LoRA、损失、优化器、数据、依赖锁和原容差均未改，无后端切换、自动重试或旧 checkpoint 迁移。

## 时序、隔离与身份

- `execute()` 先完成输入和来源校验，取得实际 GPU lease 后设置 workspace，再调用真实 Torch 严格确定性 API，之后才执行首次 CUDA 检查。策略持续覆盖加载、训练、recompute 与验证；确定性错误沿原失败路径传播。
- 新增策略设置只位于 `execute()`。`supervise()` 保持 spawn 子进程，prepare/encode 不调用该训练函数；import、父进程及准备路径不新增全局数值设置。前置源码/依赖/数组校验不初始化 CUDA。
- runtime identity 通过 Torch getter 和进程环境读回实际 strict、warn_only、workspace，未以配置常量伪装实际状态。原完整身份相等检查保持；旧 v1 请求被配置身份拒绝，checkpoint 身份不匹配时在读取张量前终止。

## 本轮验证

R1 在精确候选独立运行 **9 项定点 CPU 检查，9 passed、无跳过，10.17 秒**：实际 lease 内策略时序与异常传播；三种真实数值状态变化的身份拒绝；import/help 状态保持；v2 配置和旧请求拒绝；父进程成功、截止时间及外部 SIGTERM 三条路径的状态保持和子进程回收。CPU 检查使用真实 Torch 开关，输入和 CUDA 设备元数据采用明确的原创替身，未执行真实 CUDA。

T1 原 5 failed 和修后 10 passed 的原始命令回执及五个受检 Python 文件摘要已核对。R1 未重复其中未变的原创小模型恢复用例，也未重跑旧数据、Colab 控制、安装或保存状态矩阵。全部使用既有 Torch 2.8.0 CPU 环境、2 线程及单命令 300 秒上限；真实模型加载、编码、SSH、GPU、新包安装和共享环境修改均为 0。

| R1 私有证据 | SHA-256 |
|---|---|
| 原诊断记录与 v1/v2 配置核对 | `4f4f4927981eb7fe553989091f77813c6743d81c0e0a31d77ef0c5995e64c46d` |
| 源码、官方依据与 T1 原回执核对 | `2a42bd33276110b8f81acaeb37be6f8a85b794f05cfd3430f2028ffae2eb9534` |
| 9 项独立检查命令回执 | `b6a4f224742c9a0ab4d4f960d317ffb5fdf1b53a0832919d190501caaa8db773` |

下一验收需要同一候选的 v2 三步连续运行、新进程恢复、新实例恢复三份实际证据，按原预注册容差比较；v2 必须生成自己的第 2 步 checkpoint。该真实数值验收目前 **NOT_RUN**，与本次 CPU 技术 PASS 分开登记。
