# R1｜G3 原始验证 CE 审查交接

**PASS（CPU 技术）**，P0/P1/P2 均为 0。候选 `c633bd70f4446bc8ea3ee80440944e6e6da7ff87`；审查授权 `9bfb2b8467e9bfefd5b98c6de4557a38f4684d40`。分支 `codex/review-p04-cuda-sft-baseline-r1` 从精确候选建立；只新增本交接和[独立报告](../../reports/reviews/P04_CUDA_SFT_BASELINE_R1.md)，未改生产文件、共享配置或协调状态。

fresh SFT 的原始验证位于首次更新前，使用官方禁用 adapter 上下文，完整 validation 的实际分母和身份进入首段文件并由 summary 关联。step0 与 SFT 选模隔离，capacity/resume 明确跳过；逐模块模式恢复、现有总截止时间和产物回收路径均符合范围。最新 G3 计划的 10 个分段参数请求通过接口检查；完整数组分母仍待后续 S1/Q1 实测核对。

独立 **4 passed / 5.85秒**：原创 864 参数 tiny 的独立逐 token CE 与 baseline 总和误差 `5.3666e-7`，分母 7；非零 adapter 对照可区分。参数/buffer、梯度、模式、可训练标志、adapter、Adam、RNG 保持；后续一次更新与无 baseline 对照相同。验证读取异常恢复状态且无成功结果；两类跳过分支不访问模型或数据。step1 即使比 baseline 分数更差也正常参与 SFT 选模。没有重跑 T1 全部 8 项或旧 G2 矩阵。

实际独立检查命令如下；`R1_REVIEW_ROOT` 为本轮私有证据目录，`R1_CPU_PYTHON` 为指定既有环境，`R1_TEST_TMP` 为本轮独占目录。完整 argv、源码提交、退出码及时间在私有回执中；证据摘要见报告。

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 "$R1_CPU_PYTHON" -B -m pytest -q -s \
  "$R1_REVIEW_ROOT/test_independent_baseline.py" \
  tests/training/test_cuda_sft_baseline.py::test_capacity_and_resume_do_not_evaluate_original \
  --basetemp="$R1_TEST_TMP"
```

T1 原模式反例与缺入口的 5 项失败、修后 8 项通过和定点 ruff 回执均已核对并保留。本轮独立检查无失败。全部使用 CPU、2线程、单命令300秒上限；真实模型/GPU/SSH/编码/安装均0，新增私有证据不足1MiB，进程已结束并回收。S1 可接纳候选、冻结源码后继续 G3；本结论不构成正式 SFT 或完整原始模型 CE 的实测验收。
