# S1｜P04 CUDA v2 容量与完整恢复实测

2026-10-26。**Qwen3-1.7B 在同规格 L4 上的连续三步、新进程恢复和新实例恢复均通过实际比较。** 两种恢复分别从 v2 第 2 步 checkpoint 完成第 3 步；672 个 adapter/Adam 张量比较的最大绝对差为 **0**，完整检查 **1,883 PASS、0 FAIL**。原恢复容差未变。这支持进入正式 SFT 的独立验收关口，R1/Q1 最终结论目前待接纳。

本次为固定 18 train、2 validation 的容量与恢复验证，实际执行 3+1+1 个 optimizer update。正式 epoch、模型语义效果、DPO 和服务仍 NOT_RUN。

## 固定执行身份与输入

执行主干为 PR24 合并提交 `eb73fbcdb5f053509a396c59092e28d7c317cdd9`，双 Python CI 40261767879 全部通过。生产实现等同 T1 `f6f66545c17827fa442c38d4d3af52d6cb7231e3`，R1 CPU 审查 `9212903fc8f86955ba713d75016bfd6bc3bd935f`。v2 三项设置为 strict=true、warn_only=false、workspace=`:4096:8`，三次运行均读回相同实际策略。模型 revision、BF16 底座、FP32 LoRA、Q/V、rank 8、alpha 16、SDPA、非重入 checkpointing、损失和 AdamW 均保持冻结方案。

新源码实际 prepare 用时 100.613 秒，新编码 20 条用时 1.941 秒；两命令源码均未变化。20 条数组和 13 例审查材料与 Q1 `ed022da` 已审版本逐字节相同。数组 manifest 仅配置摘要、源码提交、两个生产文件摘要和 stage 绑定改变，其余字段一致；原数据、格式、tokenizer、完整 profile 计数与 cohort 身份未变。Mac 未加载真实模型或进行训练。

| 身份 | SHA-256 |
|---|---|
| v2 配置 | `ee235d612b2552be5927b4ff790887a34b088ab842f78a15fcb8212323b60045` |
| 实际数组 manifest | `8be8d1867980bfadf50543894cd38df8770ab176c332356cfabe18fbbff75389` |
| Linux 依赖锁 | `6a793bfd46af168b2df581f19ce8f23f97af239a12ac95b436e99baff080b2ea` |
| v2 第 2 步完整 state | `34c1c4a609419aa702610a81f1b2dfbac5305590948cee470a8ef92082e9add1` |
| 三份第 3 步完整 state | `034bed4b8a9848c30dc69d4ac84a600ee47d6ee1b006b9e07e73da62c6067183` |

## 实际结果

两实例实际均为 NVIDIA L4，23,034 MiB，驱动 580.82.07；Torch 2.8.0+cu128、CUDA 12.8，环境按同一锁重建。连续运行分组为 8+8+2，恢复运行各为最后 2 条；训练游标最终为 18。1,605,632 个 LoRA 参数完成更新，底座运行前后内容摘要一致。

| 运行 | 本次更新数 | trainer 用时（秒） | Torch peak allocated / reserved（GiB） | 设备采样峰值（MiB） |
|---|---:|---:|---:|---:|
| 连续三步 | 3 | 62.344 | 4.691 / 5.412 | 5,838 |
| 同实例新进程恢复 | 1 | 45.986 | 4.687 / 4.816 | 5,228 |
| 新实例恢复 | 1 | 46.202 | 4.687 / 4.816 | 5,228 |

设备数值是 1 秒间隔采样的观测峰值，三次分别取得 45、34、15 个样本；Torch 峰值由 trainer 记录。各运行均满足预定至少 20% 显存余量。连续三个 optimizer update 分别用时 8.718、7.761、1.524 秒；trainer 总时长还包括加载、验证和 checkpoint 操作。

三份第 3 步训练 loss 均为 `2.298484444618225`，容量验证 CE 均为 `0.874913822003265`；验证分母为 2 examples、335 supervised tokens。两种恢复的初始 adapter 对应保存的第 2 步，完整第 2 步字节保持；更新后的 adapter、Adam moments、参数顺序、整数计数、constant LR、历史选择记录、四类 RNG、步数和数据游标均一致。

比较沿用原阈值：FP32 adapter/Adam 为 `atol=1e-6, rtol=1e-4`，loss/CE 为 `atol=1e-4, rtol=1e-4`；状态结构与 RNG 等要求 exact。新进程先通过 952 项检查后才申请新实例，最终三份比较为 1,883 项、672 个张量比较、最大 scaled error 0。

## 持久化、资源与失败保留

第一实例的 23+19 个产物文件回收并校验到 Mac 后停止，确认不存在，再申请具有不同运行端点的新实例。新实例从该外部副本上传完整 checkpoint，重建环境与模型后恢复；其 23 个产物文件也已回收并校验。合计 **65 个文件**，两实例均为 `STOPPED_AND_ABSENCE_VERIFIED`，最终账户查询为 0 active assignments、0.00 CU/hr。

两实例分别占用 696.073284 和 579.025397 秒，含安装、断线、传输与空闲。加上既有尝试，G2 累计占用 **3,640.213026 / 5,400 秒**，剩余 1,759.786974 秒；账户余额从 G2 初始 174.21 到 172.94 CU，观测差 1.27 CU，未超过 8 CU 上限。这是余额观测，不是账单归因。

两个安装 SSH 连接均曾以 exit 255 / Broken pipe 断开；同一实例的原安装进程随后都正常退出 0，未重复安装。第一实例在安装连接活动时尝试上传被 HTTP 429 拒绝，未开始传输；待原连接结束后串行上传成功。未重复提交任何训练。全部命令回执及原始错误保留。

[原 v1 恢复 FAIL](S1_P04_CUDA_CAPACITY_R1.md)和[零更新诊断](S1_P04_CUDA_RESUME_DIAGNOSTIC_R1.md)保持原结论。本次没有迁移旧 checkpoint、改变数据或放宽容差；`P04-CUDA-RESUME-001` 等待 R1 对本候选实际结果的独立验收后再关闭。

| 实际证据 | SHA-256 |
|---|---|
| 连续运行 summary | `e80ab0ef843da6e6f3246ed46d9d9bd3015c666a2a6eaa624ce7cfbfe9239a1b` |
| 新进程 summary | `f8c2d492489418f8c42248683a7dd1fe55cc9b3871885edf9534bd4e21f05628` |
| 新实例 summary | `6b7e23044a2ae6fd31c25e3dcbc86bf6e3f10338af47b2ba8668339847c054ea` |
| 三份完整比较结果 | `bf5b44b434fd03970c738389fb467c052bb3a8d6ba39d8e84e7d89bcc9e2a7dd` |
| 比较命令回执 | `29e21f720cd726fe0156c55510a60401d4cd539dce3ee7b7843a0d1e9f8cae78` |
| 65 文件、33 命令及资源索引 | `2918cac2801ed992695fcfe1c2169091e7db1f9887249338e30062aab05638bb` |
