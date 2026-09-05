# 05｜Apple Silicon 资源、训练和推理计划

## 1. 机器与性能声明

目标硬件由用户提供：M5 Pro，16 核 GPU，48GB 统一内存。P01 必须在本机记录实际型号、macOS、芯片/GPU 核数、物理内存、Python、MLX、MLX-LM 和 Metal 可用性。不要根据营销名称推断训练吞吐，也不要把上一轮讨论中的训练小时数写成实测。

**48GB unified memory 不是独立的 48GB VRAM。** CPU、GPU、系统和应用共享容量。项目不通过提高系统 wired-memory 限额或关闭保护来追求跑分。

## 2. 容量计算只做下界分析

假设所有参数均按指定位数储存，0.6B 的权重理论体积约 1.2GB（16-bit）或 0.30GB（4-bit）；1.7B 约 3.4GB 或 0.85GB。这些使用十进制 GB，**不包括量化元数据、未量化层、adapter、梯度、优化器、激活与缓存**，不是峰值训练内存。

LoRA 的训练态主要包括冻结底座、可训练 adapter 及其梯度/优化器、激活和临时 buffer。长上下文、大词表 logits、DPO 成对响应和 reference 都可能改变峰值，不能从权重文件大小推出峰值。

MLX 内存计数、进程 RSS 和系统统一内存不是互斥分区；同时报告但不能直接相加。可用统计 API 以锁定 MLX 的官方文档为准。[S14]

## 3. 项目默认资源政策（可配置，不是硬件极限）

| 项目 | 默认政策 |
|---|---|
| 重 GPU 作业 | 全局 1 个，正式训练与批量推理互斥 |
| MLX allocated peak 目标 | 尽量不超过 24GiB；超过先降 batch/长度/适配层 |
| 进程 RSS 警戒 | 30GiB；同时看系统压力而不是单一数字 |
| 系统压力/交换 | 持续内存警告或明显 swap 增长时保存并停止；阈值写入 P01 配置 |
| 磁盘 | 首期规划 50GiB 缓存/制品上限；不足先删可再生缓存，不删证据 |
| 网络/云 | 不默认调用付费模型或云 GPU |
| 长任务 | 每次启动前估算总步数与时间，记录恢复策略和终止条件 |

这些值是留出 macOS、Codex、浏览器、IDE 余量的工程预算，不保证后台软件全部打开仍稳定。P01 根据本机占用修订并记录 ADR。

## 4. P01 校准流程

0.6B 先验证加载、32 条数据的 token/mask、保存加载、DPO 小张量对照。之后 1.7B 按真实长度 bucket 采样，至少完成暖机和 100 个可测微步；如果预算不允许，记录实际样本数。

分别测 SFT、reference logprob 预计算、DPO、偏好生成、完整任务推理。不能用单 token decode 速度预测训练速度。

记录：实际处理的 token（含 padding 与不含 padding 两种）、有效监督 token、微步数、optimizer step、每步时间、编译/暖机、validation、checkpoint I/O、wall time 和资源峰值。区分 gradient accumulation 的微步与优化器步。

估算公式：

```text
T_total = N_measured_work_units / measured_units_per_second
        + warmup + validation + checkpoint_IO + reference_precompute
        + negative_generation + evaluation
```

分子分母必须同一口径。DPO 计算 chosen/rejected 两个序列；reference 是否缓存改变成本。训练表填 best/central/worst 三档，依据实测方差，不先承诺“几小时一定跑完”。

若估算超出十天预算，优先缩有效数据、取消多余超参搜索、将 0.6B 容量对照和高级推理优化后移；不能首先删掉独立测试和数据审计。

## 5. 推理优化优先级

**第一层，首期：** 固定模型驻留、受控长度/请求队列、精确 prefix cache。MLX-LM 提供 prompt cache；缓存必须是真实匹配 token prefix，而不是字符串看起来一样。[S01]

**第二层，后续：** 从同一来源模型比较 16/8/4-bit，检验参数与 schema 错误率；KV cache 量化须查锁定版本支持并测准确性。滑动/rotating cache 会丢弃历史，不能当零质量损失优化；早期 tool schemas 可能被淘汰。

**第三层，可选实验：** 0.6B draft + 1.7B target 的投机解码。先核验 tokenizer/vocabulary、target 分布、采样实现和 adapter 身份。目标模型本身很小时，验证开销可能使其更慢；未提速即保留负结果，不强行启用。官方生成接口是支持核查入口，不代表本机收益。[S15]

高级 continuous batching / paged cache 社区 server 暂不作为核心依赖。先有清晰的单请求结果，再比较多请求吞吐/队列延迟。

## 6. 缓存隔离与正确性

cache key：model revision、adapter hash、量化配置、tokenizer/template、thinking mode、exact prefix token hash、工具 schema revision，以及必要的用户/租户命名空间。训练更新 adapter 后所有相关 cache 失效。

共享缓存只存不含个人信息的静态 tool schemas/system prefix。禁止把上一用户 history 当下一用户 prefix。缓存命中率、构建时间、占用和失效次数都要测。

## 7. 部署环境的现实限制

首版 MLX 训练和服务 worker 在 macOS 原生运行。普通 Linux Docker 容器不会因此获得 macOS Metal/MLX GPU；Docker 仅用于 CPU API/测试工具，或另一个明确的 Linux/CUDA backend。

GitHub CI 的 CPU 测试不等于本机 Metal 验证。Mac GPU 实测输出来自受控本机运行，不让不可信公共 PR 在个人 Mac 自托管 runner 上执行。

## 8. 人工可解释的产物

最终能讲清：统一内存与专用显存区别；量化冻结底座如何减少成本；LoRA 为什么仍需要激活内存；DPO 为什么多算两条响应/reference；cache 为什么主要改变 prefill；为什么小模型投机解码不一定更快。全部用本机结果支撑。
