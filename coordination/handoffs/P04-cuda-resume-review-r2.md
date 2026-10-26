# R1｜P04 CUDA 恢复诊断复核交接

结论 **DIAGNOSTIC_READY**；精确候选 `739c9b382f2841848a80b514ca1f31558728b5b3`，基线 `97637f336df4299a4bfd59b06f9716bb3c104796`。本轮仅新增本交接及[独立报告](../../reports/reviews/P04_CUDA_RESUME_R2.md)，没有修实现或修改协调状态。

候选两项 CPU 测试通过；独立原创 attention fixture 对不等监督长度的梯度平均、旧梯度清除、算子记录和零更新检查通过。沿用的独立保存状态分析确认原 99 个 adapter / 92 个 Adam 张量及验证 CE 超容差，定位重点收窄到梯度；完整 CUDA 原因仍待实测。

两项公开测试的复现命令如下。`CPU_PYTHON` 指既有 Torch 2.8.0 CPU 环境，`REVIEW_TMP` 必须是本次独占的新临时目录；实际 argv、时间、exit code 与结果摘要见私有命令回执及报告中的 SHA-256。

```sh
PYTHONPATH=src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
  "$CPU_PYTHON" -m pytest tests/training/test_cuda_sft_resume_probe.py \
  -q --basetemp="$REVIEW_TMP"
```

`P04-CUDA-RESUME-001` 仍 OPEN，原 CUDA FAIL 和旧 CPU PASS 保留；本次正式修订失败计数增量为 0。实际 CUDA 诊断、checkpointing 关闭后的显存和 S1 外层远程执行均 NOT_RUN。S1 在合并后冻结精确 source/request，再单独执行四组 backward、零更新的诊断；不得把其 COMPLETE 当作恢复通过。

本轮计算 CPU 2 线程、每命令不超过 300 秒；新增私有证据不足 1 MiB。真实模型、编码、SSH/GPU、共享环境修改均为 0。全部计算子进程已正常结束并回收，公共文件只包含允许的两份审查材料。
