# P04 CUDA G2 实际结果与说明：Q1-r1 终验

**PASS（数据与报告范围）。** 已审的 18 train / 2 validation 和 13 例材料身份保持；三次实际运行对应连续 3 步、同实例新进程恢复 1 步、新实例恢复 1 步，验证分母均为 335。实际回收、停止和资源记录支持 [S1 v2 报告](../S1_P04_CUDA_V2_RECOVERY.md)中的数字与容量诊断解释。Q1 未发现需整改的问题；S1 可结合 R1 的独立技术结论裁定 G2 门槛。

2026-10-26；实际 reviewer：Codex-AI（Q1），独立 AI 对话，`gpt-6-astra / max`。授权提交 `873b88858da13c993ebeeee4c17546772752413f`，实际执行源码 `eb73fbcdb5f053509a396c59092e28d7c317cdd9`。被审 S1 报告 SHA256 为 `5421c2a410e79b723a921ce206afb4c65c16e2344e8b532b48efbaae5e0240d5`。完整张量、优化器和恢复技术验收由 R1 承担，本结论不替代该验收。

## 数据身份与实际分母

新 train、validation 数组和 13 例 review-arrays 与 Q1 `ed022dae68c516727ec4cdbc91a09ce050a50338` 留存实物逐字节相同，沿用该轮及 `82f1e88e168b80298c47455c26084cc9a4b54b92` 的语义与 mask 结论，未重跑旧 531 项矩阵。直接对比原 Q1 manifest，以及 S1 实测前的 v1 manifest，变化均恰为五处：`config_sha256`、`source.commit`、`source.package_files` 中的 `training/cuda_sft/protocol.py` 与 `runtime.py`、`stage_manifest_sha256`。数据、格式、tokenizer、cohort 和其余字段一致。

v1→v2 配置除 schema 外只增加确定性策略：`deterministic_algorithms=true`、`deterministic_warn_only=false`、`cublas_workspace_config=:4096:8`。三份 summary 均读回这三项设置，执行源码、数组 manifest、cohort 和依赖锁绑定一致。静读源码差异确认数组构造、损失和 optimizer 路径保持；生产正确性沿用独立技术审查。

| 核对项 | 实际结果 |
|---|---|
| 完整 formal profile | 5,938 train / 213 validation，保持原身份 |
| 完整 smoke profile | 1,583 train / 194 validation，保持原身份 |
| 连续容量运行 | 18 条 train；实际组长 8+8+2，游标 8→16→18 |
| 两种恢复 | 各从新 v2 第 2 步、游标 16 开始；各消费最后 2 条并到第 3 步、游标 18 |
| 训练 loss | 各 event 的 per-example loss 按实际组长求均值；三份末步均为 `2.298484444618225` |
| 容量验证 | 2 examples；已有 causal mask 合计 335；末步 `293.09613037109375 / 335 = 0.874913822003265` |

实际为 3+1+1 个 optimizer update；恢复重复消费同两条训练数据。三份 summary 均为 `diagnostic_only=true`、`validation_scope=capacity_cohort`、`epoch_complete=false`。容量 CE 未被解释为测试集结果、正式 epoch 或工具语义效果；正式 SFT、DPO、模型评测与服务仍为 NOT_RUN。

## 运行、恢复与报告数字

三份 events、summary 和退出记录一致；trainer 均正常退出 0。底座前后摘要不变，adapter 更新后摘要一致。Q1 对实际回收文件作字节核对，三份第 2 步 state 均为 `34c1c4a609419aa702610a81f1b2dfbac5305590948cee470a8ef92082e9add1`，三份第 3 步 state 均为 `034bed4b8a9848c30dc69d4ac84a600ee47d6ee1b006b9e07e73da62c6067183`；未加载 state 张量。

| 实际路径 | trainer 秒 | Torch peak allocated / reserved（GiB） | 设备采样峰值 MiB / 样本数 |
|---|---:|---:|---:|
| 连续三步 | 62.344 | 4.691 / 5.412 | 5,838 / 45 |
| 同实例新进程 | 45.986 | 4.687 / 4.816 | 5,228 / 34 |
| 新实例 | 46.202 | 4.687 / 4.816 | 5,228 / 15 |

以上数值由原 JSON 重算，与 S1 报告舍入一致。设备采样间隔为 1 秒，采样峰值与 Torch 分配器峰值分别解释。显存记录满足既定至少 20% 余量；连续三步的 update 秒数为 8.718、7.761、1.524，trainer 总时长另含加载、验证及 checkpoint 操作。

同实例两次运行具有不同进程记录；新实例端点与第一实例不同。第一实例的 23+19 个产物文件已外部回收、完整清单和归档摘要对应后才停止，新实例申请晚于该停止记录。新实例上传源指向已回收的 v2 第 2 步副本，上传文件摘要与恢复配置对应；其 23 个产物文件也已回收。65 个文件均有实际字节核对及匹配的 recovery/MANIFEST，两个停止回执均为 `STOPPED_AND_ABSENCE_VERIFIED`。trainer 的 `remote_copy_verified=true` 与 `durability_verified=false` 未被当作外部持久化证明，外部证明来自回收和停止记录。

S1 比较结果记录 1,883 项 PASS、672 个张量比较且最大绝对差/scaled error 为 0；672 是两种恢复各与连续运行比较，各含 112 个 adapter 与 224 个 Adam 张量。Q1 核对结果、脚本、输入摘要与命令绑定，未执行这些张量比较。新进程的 952 项比较先通过，之后才申请新实例。原 adapter/Adam `atol=1e-6, rtol=1e-4` 与 loss/CE `atol=1e-4, rtol=1e-4` 均保持。

## 资源与失败历史

两个实例记录占用 696.073284、579.025397 秒，承接既有尝试 2,365.114345 秒，合计 **3,640.213026 / 5,400 秒**，余 1,759.786974 秒。最终资源查询记录于 2026-10-26 11:30:11（Asia/Shanghai），为 0 active assignments、0.00 CU/hr、余额 172.94 CU；相对 G2 初始 174.21 CU 的观测差为 1.27 CU，低于 8 CU 上限。余额差保持为观测值，不作账单归因；Q1 未另行连接 Colab 查询。

[原 v1 恢复 FAIL](../S1_P04_CUDA_CAPACITY_R1.md)与[零更新诊断](../S1_P04_CUDA_RESUME_DIAGNOSTIC_R1.md)保留。两次安装 SSH `exit 255 / Broken pipe` 均有原始事件，原安装进程随后退出 0；一次并行上传 HTTP 429 拒绝后，串行重试成功。33 份命令回执保留 30 个 exit 0 和 3 个 exit 1，三次训练各有一次实际 launch，没有以重试结果覆盖错误。

## Q1 实际核对与证据

本轮核对 206 个输入路径的摘要和大小，其中 197 份非二进制副本保存在本 reviewer 私有目录，另 3 个归档与 6 个 state 文件只流式核对字节、不复制或加载。私有产物约 10 MiB，低于 200 MiB。98 项 JSON/分母/身份/时序核对全部通过；另存与原 Q1 manifest 的直接绑定结果。原材料内容、端点及本机身份均未进入公开文件。

实际核对命令使用已有系统 Python，环境中四项线程上限均为 2，外部 timeout 为 300 秒：

```sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2 \
PYTHONDONTWRITEBYTECODE=1 \
  python3 -B .toolalign-local/q1-p04-cuda-g2-final-r1/review_results.py
```

最终 exit 0，约 0.090 秒。首次 helper 在 97 项中有 1 项未通过：错误要求停止时间戳之差与随后独立读钟的占用字段完全相等。静读 controller 确认两次读钟，实差 44/46 微秒；修正为采用原占用字段，并验证其位于停止时间戳和命令结束时间之间。原脚本、FAIL 输出、回执保留。另一次字段探查误读数组 manifest 中不存在的 `files` 键，按实际 `artifacts` 键纠正。两者均为 reviewer helper 错误，未改生产、输入或资源数字，不构成候选正式修订失败。

| 证据 | SHA256 |
|---|---|
| S1 实际结果索引 | `2918cac2801ed992695fcfe1c2169091e7db1f9887249338e30062aab05638bb` |
| 实际数组 manifest | `8be8d1867980bfadf50543894cd38df8770ab176c332356cfabe18fbbff75389` |
| S1 完整比较结果 | `bf5b44b434fd03970c738389fb467c052bb3a8d6ba39d8e84e7d89bcc9e2a7dd` |
| Q1 `review-result.json` | `43faa51cd1d8f4817137edf5228272f458509a6e44a7aa9895711cf5690886e6` |
| Q1 `review-command-r2.json` | `6bb915399585f6fadd19d0ccaaeb17235fd988630a0c55b4623d64378a27d1be` |
| Q1 `prior-review-binding.json` | `f4395eb165d5de6455a14291d2f7aa6ea84e7f93b8245eb025d0bed2c355b9cd` |

本轮新增 GPU/SSH、模型加载、训练、编码和安装均为 0。公开修改仅本审核报告与交接；Q1 不修改共享状态或关闭 `P04-CUDA-RESUME-001`，阶段裁定及失败计数由 S1 维护。
