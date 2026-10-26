# R1｜G3 原始 checkpoint 验证 CE 独立审查

2026-10-26。**PASS（CPU 技术审查）**。精确候选 `c633bd70f4446bc8ea3ee80440944e6e6da7ff87`，父提交及实现授权 `7eb0ac97e394528d82533c6cc92c298aa5d305b0`；本轮审查授权 `9bfb2b8467e9bfefd5b98c6de4557a38f4684d40`。P0=0、P1=0、P2=0。支持 S1 接纳该候选并冻结 G3 执行源码。

## 实现与集成判断

候选相对实现授权只修改 5 个允许文件，生产范围为 `engine.py` 和 `runtime.py`。fresh SFT 在加载模型和建立 Adam 后、首次 `train_group` 前执行原始验证；它遍历冻结 validation 的全部 ID，复用 `ValidationTotals` 的顺序、覆盖检查与 token 加权聚合。`original-validation.json` 在训练更新前写入，包含实际 numerator、denominator、样本数、profile、完整 identity 及 step/cursor 0；`summary.original_validation` 关联该文件。

[PEFT v0.18.1 的官方上下文](https://github.com/huggingface/peft/blob/v0.18.1/src/peft/peft_model.py)在 LoRA 路径临时禁用 adapter，并在退出时恢复；[对应层实现](https://github.com/huggingface/peft/blob/v0.18.1/src/peft/tuners/tuners_utils.py)管理 adapter 的启停和可训练标志。已同时检查指定环境中的实际实现。当前配置为 `bias="none"`、单个活动 LoRA，原始函数对照适用。

逐模块还原 `.training` 修正了已复现的 PEFT 包装器与 eval 底座模式不同的问题。恢复位于验证 `finally` 中；没有增加权重、RNG 复制或自动重试。`train_group` 的下一次训练模式设置保持原实现。

baseline 不传入 `CheckpointStore`，没有 step0 的保存或选模调用。capacity 与含 `resume_from` 的段在读取模型、数组前返回明确 NOT_RUN 原因。外层父进程截止时间覆盖包括新增验证在内的整个子进程；原 controller 按完整输出树导出，因此首段记录会随产物回收。恢复段继续由 S1 关联首段原始 CE。

v2 数值设置、依赖锁、训练目标、数组校验、checkpoint schema、累计步数及历史 best 路径未变。按本轮授权读取最新 G3 计划，以纯 CPU 接口 fixture 验证 smoke 100/198 与 formal 100–743 的共 10 个分段请求：100步验证、25步 checkpoint、最终尾批与累计上限均被现有接口接受。该检查未生成数组或启动运行。

## 独立 CPU 证据

R1 运行 **4 项定点检查，4 passed，5.85 秒，无跳过**。其中 2 项为独立原创数值/状态检查，另 2 项复用候选的 capacity/resume 拒绝访问检查；未重跑 T1 全部 8 项或 G2 旧矩阵。

独立 tiny 为随机初始化的 864 参数 Qwen3，BF16 底座、FP32 非零 LoRA。参考值直接由添加 adapter 前的底座 logits 和原始 prompt/completion/EOS 边界逐 token 计算 scalar log-sum-exp，没有调用生产 `completion_ce`、`evaluate` 或读取其 mask 作为参考。2 个样本含 7 个监督 token：

| 数值 | 独立结果 |
|---|---:|
| 原始底座 FP64 参考 CE 总和 | 10.03470557906124 |
| 新增 baseline 的 FP32 CE 总和 | 10.034706115722656 |
| CE 总和绝对误差 | 5.3666e-7 |
| 新增 baseline 的 token 加权 CE | 1.4335294451032365 |
| 非零 adapter 启用时的参考 CE | 1.432179761104829 |

baseline 与原始底座在预设 FP32 归约容差内一致，并区别于启用 adapter 的函数；原始底座逐样本均值 `1.4329345433782343` 也与 token 加权结果不同。实际输出覆盖完整 2 个 ID，分母为 completion+EOS 的 7 个 token。

成功路径前后，全部参数与 buffer、梯度、可训练标志、各模块模式、adapter 状态、空 Adam 状态，以及 Python/NumPy/Torch CPU RNG 均保持。随后一次真实 tiny 更新的 loss、参数和 Adam 状态与未调用 baseline 的对照完全一致。以比 baseline 更差的合成 step1 分数保存真实 tiny 更新状态，step1 仍成为唯一 SFT 选模候选，step0 未进入记录。

异常检查在已读取一个验证样本后触发读取错误：原错误传播、模式及完整状态恢复，没有留下成功 baseline 文件。capacity/resume 两个检查均以无模型、无数组对象执行，确认跳过分支不访问它们。

T1 原 5 failed、修后 8 passed 和定点 ruff 的原始回执及三个受检 Python 文件摘要已核对；旧模式反例和缺入口失败保留。本轮没有新增候选失败。

| R1 私有证据 | SHA-256 |
|---|---|
| 精确源码与 T1 原回执核对 | `f5f07b556c509310b3f11e32c0ef5bc8c3081ec2738a436f2facb742a023e747` |
| 独立原始函数、分母和后续更新结果 | `fd1070ae8510bf109e82cf7b27d576d5603be99e4d4111561286d0838e9c3bda` |
| 4 项独立检查命令回执 | `2d448e17b97d2290b4a13189072a25b7e5689db42b6af81350ced2c5f3bb1579` |
| 官方实现检查与最新 G3 接口核对 | `7bd759e0ad94e8a28b6bdfebdbb6755e59311a723efd51d6dd8eaa0cea591c8b` |

检查使用指定既有 CPU 环境、2 线程和每命令 300 秒上限；真实模型、GPU、SSH、编码与安装均为 0。G3 计划中的完整验证分母 smoke 21,226、formal 23,841 仍是冻结 sidecar 的预期，后续须由实际数组和 Q1 复核；两模型的完整原始 CE、正式 SFT 及语义效果尚未在本轮运行或验收。
