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

## 后续实际数值终验（2026-10-26）

**PASS（真实 v2 容量与完整恢复）**。授权 `873b88858da13c993ebeeee4c17546772752413f`，实际运行提交 `eb73fbcdb5f053509a396c59092e28d7c317cdd9`；生产文件与上述精确候选 `f6f66545c17827fa442c38d4d3af52d6cb7231e3` 相同。P0=0、P1=0、P2=0。**支持 S1 关闭 `P04-CUDA-RESUME-001`**；本候选正式修订失败计数增量为 0。以上 CPU 阶段结论及当时的 OPEN / NOT_RUN 记录原样保留。

R1 独立读取三份回收产物，重新计算完整 state 的差异：**1,025 项数值与状态检查全部通过，672 个 FP32 adapter/Adam 张量比较最大绝对差与最大 scaled error 均为 0**。新进程与新实例的第 3 步完整 state 均与连续运行完全一致，序列化文件 SHA-256 同为 `034bed4b8a9848c30dc69d4ac84a600ee47d6ee1b006b9e07e73da62c6067183`。这是本轮 R1 的独立结果；[S1 原比较](../S1_P04_CUDA_V2_RECOVERY.md)的 1,883 项检查记录另外保留并核对。

原预注册阈值保持：FP32 adapter/Adam moments 为 `atol=1e-6, rtol=1e-4`，loss/validation CE 为 `atol=1e-4, rtol=1e-4`；结构、参数顺序、步数、游标、constant LR、RNG 和恢复起点要求 exact。两份运行前 release 与实际比较均沿用这些阈值。

三次实际执行为连续 3 步、新进程恢复 1 步、新实例恢复 1 步，共 **5 个 optimizer update**。连续分组为 `8+8+2`，游标为 `8/16/18`；两次恢复均从 v2 第 2 步完整 checkpoint 开始，执行最后 2 条并到达游标 18。三份保留的第 2 步 state 均为 `34c1c4a609419aa702610a81f1b2dfbac5305590948cee470a8ef92082e9add1`，恢复初始 adapter 摘要等于该保存状态的独立重算值。

对 112 个 adapter 张量、112 组 Adam 状态、参数顺序、步计数、LR、Python/NumPy/Torch CPU/CUDA 四类 RNG、历史选择记录及完整状态键均已复核。1,605,632 个 LoRA 参数对应的 adapter 从第 2 步到第 3 步发生更新；底座运行前后记录的内容摘要一致。实际 strict=true、warn_only=false、workspace=`:4096:8`，三份运行身份和 73 个生产包文件均绑定到同一已审提交。

三份第 3 步 loss 均为 `2.298484444618225`，validation CE 均为 `0.874913822003265`；逐例 loss 的均值与验证 CE 的 `CE_sum / 335` 分母已独立核算。验证范围为固定容量 cohort 的 2 examples、335 supervised tokens。

### 持久化与资源核验

65 个回收文件、三份实际 tar 的成员与内容摘要、33 条原始命令回执及执行前后源码快照均通过核验。连续运行与新进程的启动 PID 不同、时间不重叠。第一实例的 23+19 个文件先回收到 Mac，03:18:57 UTC 停止并确认不存在，03:19:39 UTC 账户查询为 0 active assignments；第二实例于 03:20:26 UTC 分配，端点不同，从该 Mac 外部副本上传完整第 2 步 checkpoint 后恢复。第二实例的 23 个文件于 03:29:04 UTC 回收，03:30:05 UTC 停止，最终查询仍为 0 active assignments、0.00 CU/hr。

| 运行 | 本次更新 | trainer 秒数 | Torch peak allocated / reserved（GiB） | 设备采样峰值（MiB） |
|---|---:|---:|---:|---:|
| 连续三步 | 3 | 62.344 | 4.691 / 5.412 | 5,838 |
| 新进程恢复 | 1 | 45.986 | 4.687 / 4.816 | 5,228 |
| 新实例恢复 | 1 | 46.202 | 4.687 / 4.816 | 5,228 |

设备采样分别为 45、34、15 次，以上为观测峰值；最小采样空闲比例分别为 72.61%、75.26%、75.26%。训练事件中的 free/reserved 记录也均满足预定 20% 余量。两实例占用 696.073284、579.025397 秒；加上已登记旧尝试 2,365.114345 秒，累计为 **3,640.213026 / 5,400 秒**。最终余额 172.94 CU，相对 G2 初始 174.21 CU 的观测差为 1.27 CU，低于 8 CU 上限；该差值不是账单归因。

两次 setup SSH exit 255 / Broken pipe、一次上传 HTTP 429 的原始错误均保留。安装在各自原实例继续完成并退出 0，上传随后串行成功；三次训练均正常退出 0，未重复提交训练。原 v1 恢复 FAIL 和零更新诊断保持原结论。

| 本轮 R1 私有证据 | SHA-256 |
|---|---|
| 产物、归档与 33 命令完整性核验 | `8426bba1707fa68ebe6d84578af846693e3f1ed9ff706260b5b280ca68c4f8ea` |
| 独立完整状态与数值比较 | `f691fb03b9670d985f21165f60b4c58325e027b95d687f45579cd63c36abc68a` |
| 独立数值比较命令回执 | `f1dbd3f958799a61ced49409ef1f3a80b2a940c7a7c38495bc308b59b2aa5215` |
| 外部 checkpoint、运行时序与资源回收核验 | `65140d1b291201e76a604212dd5202744df05a3ed4ceef01849845f772180e3d` |

本轮 R1 仅在既有 CPU 环境读取保存张量，使用 `map_location="cpu", weights_only=True`、2 线程和单命令 300 秒上限。新增 GPU、SSH、真实模型构建、编码、训练和安装均为 0，未重跑既有 CPU 或 Q1 矩阵。本结论验收固定 18 train / 2 validation 的容量与恢复能力；正式 epoch、模型语义效果、DPO 和服务不在本次验收范围内。
