# P04 CUDA 严格确定性策略 r3

活动 CUDA 协议已切到 S1 冻结的 v2。训练子进程持有 GPU lease 后、首次 CUDA 检查前设置 `CUBLAS_WORKSPACE_CONFIG=:4096:8`，调用 `torch.use_deterministic_algorithms(True, warn_only=False)`；该状态持续覆盖模型加载、forward、backward/recompute 和验证。runtime identity 从 PyTorch 和进程环境读取实际 strict、warn_only、workspace，沿用 checkpoint 的完整身份匹配。

代码基线为 `fee99c83ac6e2aeebbb8d565087eb5a80966ac26`，任务授权为 `e23ee150d2759419170750139c211d2d0ebe3805`，实现分支从授权提交建立。依据为 [ADR-0032](../coordination/DECISIONS.md) 和[实际同状态诊断](S1_P04_CUDA_RESUME_DIAGNOSTIC_R1.md)。v1、v2 配置均与授权提交逐字节相同；v2 SHA-256 为 `ee235d612b2552be5927b4ff790887a34b088ab842f78a15fcb8212323b60045`。

生产改动限于 `protocol.py` 的活动文件与 SHA，以及 `runtime.py` 的设置时点和两项身份字段。没有新增数值策略选项或迁移旧 checkpoint；旧请求的 v1 配置身份会被拒绝。SDPA、checkpointing、TF32、LoRA、优化器、损失、数据和恢复容差沿用原规则。

## CPU 检查

既有 CPU 环境：Python 3.12.14、Torch 2.8.0、Transformers 4.57.6、PEFT 0.18.1、NumPy 2.2.6、pytest 9.0.2。每条检查外层时限300秒、2线程，使用本轮独占临时目录。

| 检查 | 实际结果 |
|---|---|
| 修改生产代码前的新增要求 | 5 failed，退出码1，2.13秒；旧 loader、缺失策略设置及身份字段均被检出 |
| 修改后的相关协议、策略、恢复、父进程检查 | 10 passed，退出码0，12.46秒，无跳过 |
| 五个变更 Python 文件的定点 ruff | PASS，退出码0 |

策略检查使用真实 Torch 开关及进程环境，通过实际 `execute()` 和临时仓库的 `GPULease` 到达首次 CUDA 检查边界，再主动抛出 CPU fixture 错误；确认该错误直接传播、租约释放且没有加载模型。输入 I/O 使用原创替身。身份检查只替换 CUDA 设备元数据，分别改变真实 strict、warn_only、workspace 后，均在读取 tensor 前拒绝旧身份。import 和三种父进程退出路径保持环境、框架导入状态不变；现有原创小模型新进程恢复继续核对 loss、参数、RNG 与选模状态。

下列为实际检查的内部命令；`T1_CPU_PYTHON` 是 S1 指定的既有 CPU Python，`T1_TEST_TMP` 是本轮新建独占目录，外层使用 `subprocess.run(..., timeout=300)`。原始 argv、输出、退出码、耗时和修改前失败保存在本轮私有证据中。

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 "$T1_CPU_PYTHON" -B -m pytest -q \
  tests/training/test_cuda_sft_determinism.py \
  tests/training/test_cuda_sft_protocol.py::test_import_and_help_have_no_framework_side_effects \
  tests/training/test_cuda_sft_protocol.py::test_frozen_config_and_run_bounds \
  tests/training/test_cuda_sft_tensors.py::test_fresh_process_resume_matches_loss_parameters_all_rng_and_selection \
  tests/training/test_cuda_sft_process.py --basetemp="$T1_TEST_TMP"

ruff check src/toolalign/training/cuda_sft/protocol.py src/toolalign/training/cuda_sft/runtime.py \
  tests/training/test_cuda_sft_determinism.py tests/training/test_cuda_sft_protocol.py \
  tests/training/test_cuda_sft_process.py
```

| 原始命令记录 | SHA-256 |
|---|---|
| 修改前5项失败 | `c52ac8f2c6ccc7da3c35d04afd584211cd36ac2a3620968b5a2d51b6438a60ec` |
| 修改后10项通过 | `fb56b8f4aa3eea28cdc37666b8bbb511c0f73e98b71f7cb1b2331d516dedd181` |
| 定点ruff | `427846b3ae55d13ef9d6ec9e2f878af72886569adef68e0f4b8a2e12d0df6ba1` |

## 真实恢复仍待验收

本轮真实模型加载、数据编码、SSH、GPU和新包安装均为0。CPU检查不能证明 CUDA backward 确定性，`P04-CUDA-RESUME-001` 仍 OPEN。R1复核后，由S1绑定新源码与v2配置，连续运行三步生成自己的step2，再分别在新进程和新实例恢复到step3，按原预注册容差及20%显存余量验收。原v1失败和四组诊断保持原记录。
