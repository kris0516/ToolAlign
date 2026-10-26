# S1｜CUDA 同状态重复反向诊断

2026-10-26。**同一进程在相同参数和 RNG 下重复 backward，梯度相对 L2 差约0.86%；关闭 checkpointing 后仍约0.87%。** 跨进程恢复并非复现差异的必要条件。完整初始状态恢复严格一致，下一步定位当前 CUDA 反向计算的确定性。原 `P04-CUDA-RESUME-001` 仍 OPEN，原恢复 FAIL 保留。

执行源码为 [PR23](https://github.com/kris0516/ToolAlign/pull/23) 合并提交 `fee99c83ac6e2aeebbb8d565087eb5a80966ac26`；候选 `739c9b3` 已经 [R1](reviews/P04_CUDA_RESUME_R2.md) 在 `0947a91` 独立评为 DIAGNOSTIC_READY。生产包、配置、依赖锁及控制器与原训练提交 `97637f3` 字节相同。探针仍使用原容量数组 `51a72127087eb0b3db90a1252c1c8154986df0ae2fb35bbb2efdfcd8ba57cd0f` 和第2步 checkpoint `efb423314a70f118c9c4668ace4a932fe73710c66a39adabcb5a2d3f9db04736`。

## 实际对照

在新的 L4 实例上恢复原 checkpoint，只读取最后两条 train 样本。首次 backward 前重新 capture，adapter、完整 Adam、常数学习率、step/cursor、参数顺序和四类 RNG 共10项检查均严格一致。四组均从相同 RNG 开始并清除旧梯度，采用原每例监督 token 均值、尾组除数2；四组的两条样本 loss 均为 `2.3235387802124023`、`2.271536111831665`。

| 梯度比较 | 相对 L2 差 | 最大绝对差 | 严格相同 tensor |
|---|---:|---:|---:|
| checkpointing 开，重复 A/B | 0.0085657661 | 0.0046695620 | 6 / 112 |
| checkpointing 关，重复 A/B | 0.0086842069 | 0.0032189265 | 6 / 112 |
| 开 A / 关 A | 0.0084002734 | 0.0028727055 | 6 / 112 |

实际记录到 `aten::_scaled_dot_product_flash_attention` 和 `aten::_flash_attention_backward`。开启 checkpointing 时每组 attention 前向112次、反向56次，关闭时为56/56。算子记录和重复差异支持优先核查当前 CUDA 反向数值路径；单凭这些记录尚不能排除其他 CUDA 算子的贡献，也不能声称确定性设置已经修复问题。

四组共8次 microstep，**optimizer update 为0**；结束时 adapter、Adam 和冻结底座均未变。进程正常退出，总耗时70.691秒，满足300秒/128MiB上限。`summary.status=COMPLETE`，`recovery_acceptance=NOT_EVALUATED`；这不是后续更新恢复通过或正式 SFT。

## 资源与回收

实际设备为 L4 23034MiB。开启 checkpointing 时 Torch 峰值 allocated/reserved 为 `4982839808 / 5158993920` bytes；关闭时为 `10137743872 / 10320084992` bytes。设备1秒采样56次，观测峰值10102MiB；两种路径均保留超过20%的显存余量。

依赖安装的 SSH 连接被远端关闭，原失败回执保留；随后同实例 status 读到 `setup-exit.json` 为0，安装已在155.633秒完成，没有重新安装或重复启动。专用诊断由单独 tmux 入口执行；Colab 控制器只负责 setup、recover、stop。

29个运行文件已全部下载、清单校验并在Mac回读。停止前确认诊断退出、tmux及记录进程不存在、GPU lease空闲；实例已停止并确认不存在。本实例占用722.391秒，余额观察差0.21CU。三次实例合计2365.114秒、观察余额差0.78CU；原5400秒/8CU上限剩3034.886秒。余额差仅为观察值。当前活动实例0。

| 证据 | SHA-256 |
|---|---|
| 诊断完整摘要 | `83127446c36cd55fa8b81c4045b12030f047be2b48be3bf7d0adaadb4749c59b` |
| 初始状态、四组梯度及命令索引 | `a4c4043d7415fc72f949530a3bb3a07a2ee1068fe9a4351d165a9ae0fdc78ee6` |
| 远端终态与摘要读回命令 | `db42b132c7fa356f4b174839cbe0cf38c9c627fa76262a3f7d1c88e98d93e64a` |
| 全部文件持久回收命令 | `50c3ddc097db85bf0b9360c163b5b509a58dd6f1308629ff520bc6c371c20f3a` |
| 停止与不存在验证命令 | `311286724af4f81b326447f97c7d98e57c4a1f8c79ecfb731c90a89e6edc67c2` |

T1对应版本源码核对支持严格确定性路线；S1已按 [ADR-0032](../coordination/DECISIONS.md) 冻结v2三项数值设置，交T1实现、R1独立复核后再实际GPU复验。原容差保持不变；正式SFT/DPO/模型评测仍NOT_RUN。
