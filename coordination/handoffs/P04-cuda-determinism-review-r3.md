# R1｜P04 CUDA 确定性 r3 审查交接

**PASS（CPU 技术）**，精确候选 `f6f66545c17827fa442c38d4d3af52d6cb7231e3`。授权 `e23ee150d2759419170750139c211d2d0ebe3805`；P0/P1/P2 均为 0。只新增本交接与[独立报告](../../reports/reviews/P04_CUDA_DETERMINISM_R3.md)，未修生产实现或配置，未修改协调状态。

v1/v2 仅 schema 和三项 numerics 不同，均保持 S1 原字节。9 项独立 CPU 检查通过：租约内、首次 CUDA 前应用策略；导入及父进程不受影响；strict/warn_only/workspace 读取实际状态并拒绝不匹配 checkpoint；旧 v1 请求被拒绝。T1 原 5 项失败、修后 10 项通过的回执已核对，未重复旧恢复矩阵。

下列为独立检查的可复现命令；`R1_CPU_PYTHON` 为既有 Torch 2.8.0 CPU 环境，`R1_TEST_TMP` 为新建独占临时目录。实际绝对 argv、时间与退出码在私有回执中，摘要见报告。

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 "$R1_CPU_PYTHON" -m pytest -q \
  tests/training/test_cuda_sft_determinism.py \
  tests/training/test_cuda_sft_protocol.py::test_import_and_help_have_no_framework_side_effects \
  tests/training/test_cuda_sft_protocol.py::test_frozen_config_and_run_bounds \
  tests/training/test_cuda_sft_process.py --basetemp="$R1_TEST_TMP"
```

`P04-CUDA-RESUME-001` 仍 OPEN，原 v1 FAIL 与诊断保留，正式修订失败计数增量为 0。真实 v2 三步连续、新进程及新实例恢复均 NOT_RUN；S1 冻结执行并提供三份证据后，再独立验收同一候选的数值结果。本轮真实模型、编码、SSH/GPU、包安装均为 0；CPU 进程已结束并回收，新增私有证据不足 1 MiB。
