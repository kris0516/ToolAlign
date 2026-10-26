# T1｜G3 原始 checkpoint 验证 CE

状态：READY。S1 接纳 G2 的主干为 `75209551c8520e5c97ed5cb424a686657a6d9da4`；T1 从 S1 原生派发的精确授权提交建立 `codex/p04-cuda-sft-baseline-r1`。本包为 CPU 实现和检查，不申请 GPU。G3 固定计划见 [配置](../../configs/sft-cuda-g3.v1.json)。

当前 `runtime.execute` 只在更新后验证，缺少同格式、同完整验证集的原始模型 CE。补齐这项记录，供 G3 对照原始 checkpoint 与验证集选出的 SFT；工具语义效果留待 G5。

## 最小实现

- 仅在新的 `run_kind=sft` 且没有 `resume_from` 时，加载模型后、任何 optimizer update 前，用 PEFT 官方 `disable_adapter()` 上下文调用已有 `evaluate`，覆盖该 profile 全部冻结 validation。记录 CE numerator、supervised-token denominator、examples、profile、完整运行 identity 和 step/cursor 0；在训练开始前写入独立结果，并在 summary 明确关联。
- 继续用现有角色格式、causal mask、completion+EOS 分母与 `ValidationTotals`。这是原始 checkpoint 对照；DPO 仍须保留已选 SFT reference，不能照搬 disable-adapter。
- 初始验证不进入 `CheckpointStore` 或 SFT 最佳 checkpoint 竞争，不改变更新数、游标、优化器、训练权重、RNG 和训练模式。若实际测试表明调用已有接口会改变这些状态，做必要的最小恢复；不要添加猜测驱动的恢复层。
- `capacity` 与恢复段不重复执行原始模型验证；summary 清楚表明本段未执行。S1 后续用首段已回收记录关联整个 epoch。保持已有累计 step 上限、100步验证/25步 checkpoint 的支持和历史 best 恢复语义。
- 不改训练目标、v2 numerics、配置摘要、依赖锁、checkpoint schema 或 Colab 控制器；不新建通用评测框架。

允许修改 `src/toolalign/training/cuda_sft/runtime.py`，必要时 `engine.py`，新增小型 `tests/training/test_cuda_sft_baseline.py`，以及 `reports/experiments/P04_CUDA_SFT_BASELINE_R1.md`、`coordination/handoffs/P04-cuda-sft-baseline-r1.md`。共享状态由 S1 维护。

## 检查与交付

使用已有 Torch CPU/PEFT 环境和原创 tiny 模型。必须实际核对：有非零 adapter 时原始验证与禁用 adapter 的原始函数一致；分母与现有 evaluate 一致；恢复 adapter、模式和训练状态；step0 不参与 SFT 选模；fresh-sft、resume、capacity 的分支行为。测试复用生产入口和现成 fixture，避免大面积 mock。只运行新行为及受影响的已有检查，不重跑旧完整矩阵。

每命令≤300秒、2线程、新增私有产物≤256MiB。真实模型、GPU、SSH、编码和安装均为0。保留命令、退出、实际环境与源码身份；提交精确候选供 R1 独立审核。报告区分 CPU PASS 与真实 G3 尚未运行。
