# P04 CUDA SFT 原始 checkpoint 验证 CE

新的 fresh `run_kind=sft` 在任何更新前，用 PEFT `disable_adapter()` 上下文和现有 `evaluate` 遍历完整冻结 validation。结果先写入 `original-validation.json`，包含 `ce_sum`、`supervised_tokens`、`examples`、`validation_ce`、profile、完整运行 identity、run ID，以及均为0的 optimizer step 和数据游标。`summary.original_validation` 用 `{"status":"PASS","file":"original-validation.json"}` 关联该记录。

capacity 段返回 `{"status":"NOT_RUN","reason":"capacity_run"}`，恢复段返回 `{"status":"NOT_RUN","reason":"resume_segment"}`，不读取原始验证样本。记录不进入 `CheckpointStore`；step0不参与SFT最佳checkpoint竞争。训练更新数、累计游标、验证/checkpoint间隔、v2数值配置、依赖和checkpoint schema均保持原规则。

代码基线为 G2 验收主干 `75209551c8520e5c97ed5cb424a686657a6d9da4`；本分支从 S1 授权 `7eb0ac97e394528d82533c6cc92c298aa5d305b0` 建立，范围见[任务](../../coordination/tasks/P04_CUDA_SFT_BASELINE_R1.md)。正式 G3 按[固定计划](../../configs/sft-cuda-g3.v1.json)另行运行。

## 实测驱动的模式恢复

原创 tiny 复现了已有 `evaluate` 的状态变化：按真实 loader 的方式令底座处于 eval 模式，再添加 PEFT，会得到训练模式的包装器与 eval 模式的底座。旧 `model.train(was_training)` 将所有子模块统一成顶层模式。本包因此将恢复缩小为逐模块还原原有 `.training` 值；成功和验证异常路径均验证通过。adapter 的启停和可训练标志由现有 PEFT 上下文恢复。未添加额外 RNG 或权重恢复层。

## CPU 验证

环境为既有 Python3.12.14、Torch2.8.0、Transformers4.57.6、PEFT0.18.1、NumPy2.2.6、pytest9.0.2。每条命令外层上限300秒，2线程，本轮新建独占临时目录。

| 检查 | 实际结果 |
|---|---|
| 修改前新增检查 | 5 failed，退出码1，5.81秒；保留模式变化反例与尚缺入口的失败 |
| 新行为及受影响的已有检查 | 8 passed，退出码0，14.79秒，无跳过 |
| 三个变更 Python 文件定点 ruff | PASS，退出码0 |

原创 tiny 使用 BF16 底座、FP32 非零 LoRA，参数少于4096，复用已有短/长样本 fixture。启用 adapter 时的CE与原始底座不同；新增baseline与添加adapter前的底座、官方禁用adapter上下文结果完全一致。2个样本共7个completion与EOS监督token，分母与现有 `evaluate` 一致。

baseline前后实际核对全部权重、可训练标志、每个模块模式、adapter启用状态、空Adam状态以及Python/NumPy/Torch CPU RNG；后续一次tiny更新的loss与参数与未调用baseline的对照相同。step0没有产生训练checkpoint；用故意更差的合成step1验证分数检查选模时，step1仍是唯一候选。capacity/resume跳过分支不接触模型或数组；验证覆盖不完整时恢复模式与adapter且不写成功结果。既有独立CE/梯度、原创新进程完整恢复及import检查同时通过。

实际内部命令如下；`T1_CPU_PYTHON` 为S1指定的既有CPU Python，`T1_TEST_TMP` 为本轮独占新目录，外层使用 `subprocess.run(..., timeout=300)`：

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 "$T1_CPU_PYTHON" -B -m pytest -q \
  tests/training/test_cuda_sft_baseline.py \
  tests/training/test_cuda_sft_tensors.py::test_independent_ce_gradient_mask_eos_right_pad_and_single_shift \
  tests/training/test_cuda_sft_tensors.py::test_fresh_process_resume_matches_loss_parameters_all_rng_and_selection \
  tests/training/test_cuda_sft_protocol.py::test_import_and_help_have_no_framework_side_effects \
  --basetemp="$T1_TEST_TMP"

ruff check src/toolalign/training/cuda_sft/runtime.py src/toolalign/training/cuda_sft/engine.py \
  tests/training/test_cuda_sft_baseline.py
```

| 原始命令记录 | SHA-256 |
|---|---|
| 修改前5项失败 | `8c3c8da97af5299c6fd52903b560043ce3631a19317e2a2eba440e2e1c6ecc02` |
| 修改后8项通过 | `9df825cbcf74c40da3a80d37b94aae34e73e3cf689257e550733aa44c6bed838` |
| 定点ruff | `25b66316ca0a3428c5079aa02fd256be379ccb0f42a9168aea321638d05313c2` |

本轮真实模型、GPU、SSH、编码及安装均0。CPU结果证明新增记录和状态保持行为；真实两个profile的完整原始CE及正式SFT仍NOT_RUN，须经R1审查后由S1冻结执行。CE对照不替代G5工具语义评测；DPO的reference仍须是已选SFT checkpoint。
