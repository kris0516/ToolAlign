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

## 后续实际数值终验交接（2026-10-26）

**PASS，支持 S1 关闭 `P04-CUDA-RESUME-001`。** 授权 `873b88858da13c993ebeeee4c17546772752413f`；候选仍为 `f6f66545c17827fa442c38d4d3af52d6cb7231e3`，实际运行主干 `eb73fbcdb5f053509a396c59092e28d7c317cdd9` 的生产文件相同。P0/P1/P2 均为 0，本候选正式修订失败计数增量为 0。旧 CPU 结论、原 v1 FAIL 和诊断均保留；R1 未修改协调状态。

独立数值与状态核验 **1,025 项通过**，672 个 adapter/Adam 张量比较最大差值为 0；两种恢复的完整第 3 步 state 与连续运行完全一致。原容差、四类 RNG、Adam 计数、参数顺序、LR、游标和历史选择记录全部满足。实际共 3+1+1 次更新，固定 18 train / 2 validation；最终 loss `2.298484444618225`、CE `0.874913822003265`（335 supervised tokens）。

65 个文件、三份 tar 及 33 条原始命令回执已绑定核验；外部 Mac checkpoint 的回收、原实例停止、新实例分配与上传、最终回收停止的顺序通过。两实例均已停止且确认不存在，最终账户查询为 0 active assignments；显存均满足 20% 余量。G2 累计 3,640.213026 / 5,400 秒，余额观测差 1.27 / 8 CU，非账单归因。报告列出实际资源数值与证据 SHA-256。

私有目录保留 `audit_integrity.py`、`audit_numeric.py`、`audit_chain.py` 及对应 JSON 结果和 `commands/` 原始回执。实际独立分析命令如下；`R1_REVIEW_ROOT` 为本轮私有证据目录，`R1_CPU_PYTHON` 为既有 Torch 2.8.0 CPU 环境，完整 argv、时间与退出码见回执。

```sh
python3 -B "$R1_REVIEW_ROOT/audit_integrity.py"
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  "$R1_CPU_PYTHON" -B "$R1_REVIEW_ROOT/audit_numeric.py"
python3 -B "$R1_REVIEW_ROOT/audit_chain.py"
```

完整性核验首轮将 73 个源码文件与 49 个安装分发包误作同一计数；确认源码摘要全部一致后修正 R1 审查脚本，通过 432 项核验，原失败回执保留。运行及资源核验另有 58 项通过。这是审查脚本计数修正，不是候选缺陷。S1 两次安装连接断开及一次上传 429 的原始失败也均保留。

本轮只追加两个允许的报告文件，新增私有证据不足 1 MiB；所有独立 CPU 命令已完成并回收。未新增模型运行、编码、安装或远程操作，也未重跑旧 CPU/Q1 矩阵。正式 SFT 与语义效果须由后续阶段分别验收。
