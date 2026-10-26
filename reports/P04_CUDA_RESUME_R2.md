# P04-CUDA-RESUME-001：梯度鉴别候选

保存状态将差异定位到梯度形成或累积阶段，具体 CUDA 原因尚未确定。112 个 adapter 的保存顺序和 optimizer groups 一致；两条路径的最终参数均符合各自保存的 Adam 状态，独立 FP64 更新公式最大残差分别为 `9.45381e-10`、`9.45339e-10`。用 `g3=(m3−0.9m2)/0.1` 反推的梯度，整体相对 L2 差异为 `0.00851833`，最大绝对差为 `0.002683955`。这些是由一阶矩推导的梯度，尚无真实更新前梯度快照。

反推梯度在第 27 层完全相同，差异向较早层增大；第 0 层 Q/LoRA B 的相对 L2 差异为 `0.0226657`。两条路径的二阶矩同时满足由上述梯度推导的递推式，全部 1,605,632 个元素的残差均落在所检查的 FP32 舍入尺度内。该分析支持检查 backward；下一次仍需在真实模型中直接核对恢复后的 Adam、adapter、顺序与 RNG。

分析使用三份原 checkpoint，按 manifest 验证字节后在 CPU 读取，未构造真实模型。原创 3,336 参数、4 层、8 token 的 BF16 底座/FP32 LoRA 新进程对照，在最多 3 次更新后，81 个 tensor 比较和全部 1,403 个字段检查严格一致。该 CPU 结果不能关闭真实 CUDA 差异。一次原创 fixture 使用未注册 profile 的失败已保留，改为既有 `TOY_CPU` 后完成上述对照；没有修改生产配置。

基线 `97637f336df4299a4bfd59b06f9716bb3c104796`；定位授权 `a48e3354daba2e1f81bd3f21d9b6895daef7e0fe`，单文件探针补充授权 `9ca0bf1490070b00ed24e14169601fc5869cf58b`。生产包、协议、模型、数据、依赖和原验收容差保持原字节。原 CUDA 数值 FAIL 保留。

## 最小 Colab 鉴别方案，尚未运行

[单文件探针](experiments/P04_CUDA_RESUME_DIAGNOSTIC.py) 复用已回收的完整第 2 步 checkpoint、原 20 条容量数组和现有 engine/checkpoint；不编码、不生成、不做 optimizer update。它只对最后两条 train 样本做四组 backward，每组从相同 RNG 开始：

| Case | gradient checkpointing | 用途 |
|---|---|---|
| `checkpoint_on_a` | 原 non-reentrant 设置 | 直接采集恢复后梯度 |
| `checkpoint_on_b` | 相同设置 | 同进程、同参数、同输入重复 |
| `checkpoint_off_a` | 临时关闭 | 检查 recomputation 路径的影响 |
| `checkpoint_off_b` | 仍关闭 | 检查关闭后的重复性 |

在第一次 backward 前保存并严格核对实际恢复后的 adapter、完整 Adam、步数、游标、Python/NumPy/Torch CPU/CUDA RNG 和参数顺序。四组均使用相同的 CPU operator profiler，保存实际 attention forward/backward 的后端算子名和调用次数，不导出庞大的 trace。每组保存梯度、两条 loss、RNG 和 CUDA 内存；最后核对参数、底座和 Adam 未变。没有更换 SDPA backend、精度、确定性开关或验收容差。关闭 checkpointing 是本次鉴别变量，未进入生产配置。

判读顺序：先看物理恢复检查；若通过，再比较开启时的两次梯度、关闭时的两次梯度、开启与关闭的梯度。开启重复不一致而关闭重复一致支持继续定位 checkpointing 相关路径；两者都不一致支持检查更广的 CUDA backward；同模式都稳定但跨模式不同则检查 recomputation。若本次都一致，结合原两次保存状态与新 attention 算子记录，继续区分进程历史和算子选择，不宣布原问题已修复。梯度比较是描述性诊断，原正式恢复阈值不变。

只申请一个 GPU 作业；四组、八次 microstep、零更新。Python 时限最多 300 秒，外部 deadline 另留 10 秒强制结束；输出最多 128 MiB，沿用 20% GPU 内存余量。关闭 checkpointing 的真实内存尚未测量；遇到 OOM、余量不足或其他异常即停止，保留已写输出，不自动改配置重试。准备、回收和实例停止由 S1 在剩余 G2 预算内单独冻结。

下面是供 S1 填入探针提交和实际私有路径的请求模板。`source_commit` 指探针候选的 checkout；`training_source_commit` 是旧训练基线。入口要求全部 73 个生产包文件与旧 checkpoint 的源码字节相同，并单独核对探针文件与自己的提交；不改写旧 checkpoint 的身份。

```json
{
  "schema": "toolalign.cuda-sft-resume-diagnostic.v1",
  "authorized_by": "S1",
  "run_id": "p04-g2-resume-diagnostic-r2",
  "run_kind": "capacity",
  "profile": "formal",
  "source_commit": "REPLACE_WITH_DIAGNOSTIC_COMMIT_40HEX",
  "training_source_commit": "97637f336df4299a4bfd59b06f9716bb3c104796",
  "config_sha256": "3d4785e1e130dd04990abb3767c23d92cdb7b18dad1d30cc6991f976cd44c9c4",
  "array_manifest_sha256": "51a72127087eb0b3db90a1252c1c8154986df0ae2fb35bbb2efdfcd8ba57cd0f",
  "dependency_lock_sha256": "6a793bfd46af168b2df581f19ce8f23f97af239a12ac95b436e99baff080b2ea",
  "checkpoint_sha256": "efb423314a70f118c9c4668ace4a932fe73710c66a39adabcb5a2d3f9db04736",
  "frozen_base_sha256": "4cbb20b94d0e5c585e8574ea38428c52a5c58f1ffba32aafcf469dc60ed10f02",
  "repository": "/content/toolalign",
  "lock_root": "/content/toolalign",
  "array_dir": "/content/toolalign-private/capacity-arrays",
  "dependency_lock": "/content/toolalign/requirements/cuda-linux-py312.lock.txt",
  "model_root": "/content/toolalign-private/models/Qwen3-1.7B",
  "checkpoint_dir": "/content/toolalign-private/recovered-step2",
  "output_dir": "/content/toolalign-private/resume-diagnostic-r2",
  "max_wall_seconds": 300,
  "max_output_bytes": 134217728,
  "validation_every_steps": 2,
  "checkpoint_every_steps": 2,
  "max_optimizer_updates": 0,
  "max_backward_groups": 4,
  "diagnostic_passes": ["checkpoint_on_a", "checkpoint_on_b", "checkpoint_off_a", "checkpoint_off_b"]
}
```

在候选 checkout 中执行，输出父目录需存在、目标目录需不存在；S1 先核验既有环境和外部 `timeout` 可用：

```sh
PYTHONPATH=src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
  timeout --signal=TERM --kill-after=10s 300s \
  .toolalign-local/cuda-env/bin/python -B reports/experiments/P04_CUDA_RESUME_DIAGNOSTIC.py \
  --request /content/toolalign-private/resume-diagnostic-request.json
```

收回整个输出目录，包括 `restored-state.pt`、`restoration.json`、四份梯度 `.pt` 及 case JSON、`summary.json` 和原请求。`summary.status=COMPLETE` 仅表示诊断完成，固定带 `diagnostic_only=true`、`recovery_acceptance=NOT_EVALUATED`。没有新的训练 checkpoint。

本地验证为探针的两项原创 CPU 检查：范围拒绝、独立手算梯度及零参数更新。生产模块未改，不重复旧数据、环境、控制或完整训练测试。实际 GPU probe 和其 memory/profile 路径仍 `NOT_RUN`。核对依据包括已安装 Torch 2.8 的 optimizer 状态按顺序映射和 Adam 更新实现，以及官方 [optimizer 源码](https://github.com/pytorch/pytorch/blob/v2.8.0/torch/optim/optimizer.py)、[Adam 源码](https://github.com/pytorch/pytorch/blob/v2.8.0/torch/optim/adam.py)；[SDPA 文档](https://docs.pytorch.org/docs/2.8/generated/torch.nn.functional.scaled_dot_product_attention.html)说明不同后端可能有数值差异，本次原因须由上述实测区分。
