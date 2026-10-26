# S1｜P04 首次 CUDA 容量与新进程恢复

2026-10-26。**L4三步容量PASS；新进程恢复的数值比较FAIL，跨实例恢复未运行。** 这组作业是容量诊断，不是正式SFT或工具效果评测。

源码为PR22合并提交 `97637f336df4299a4bfd59b06f9716bb3c104796`，Linux锁 `6a793bfd46af168b2df581f19ce8f23f97af239a12ac95b436e99baff080b2ea`。该锁在真实Linux/Python3.12中安装通过，48包身份及pip check通过，安装164.98秒。实际L4为23034MiB，驱动580.82.07。Notebook控制首次连接丢失，后续沿用带endpoint存在性检查的SSH；安装占用SSH时一次并行只读查询被CLI以HTTP429拒绝，后续控制串行执行。两项控制故障均未重复提交训练。

容量输入来自主干重新执行prepare/encode的manifest `51a72127087eb0b3db90a1252c1c8154986df0ae2fb35bbb2efdfcd8ba57cd0f`，18条最长train与2条validation。输入行及13例材料与Q1 `ed022dae68c516727ec4cdbc91a09ce050a50338` 审核的字节相同，仅manifest源码/准备阶段身份更新。固定Qwen3-1.7B revision、BF16底座、FP32 Q/V LoRA rank8、alpha16、SDPA、非重入gradient checkpointing；配置、目标和长度均未改变。

| 实测 | 三步连续运行 | 第2步恢复的新进程 |
|---|---:|---:|
| 正常退出 | 0 | 0 |
| trainer总耗时（秒） | 60.349 | 46.672 |
| optimizer step / cursor | 3 / 18 | 3 / 18 |
| 最后组训练loss | 2.2975374460220337 | 2.2975374460220337 |
| 最后验证CE（2例、335监督token） | 0.8660437740496735 | 0.8690712544455457 |
| Torch峰值allocated（bytes） | 4987051008 | 4982839808 |
| Torch峰值reserved（bytes） | 5171576832 | 5158993920 |
| 设备采样峰值（MiB） | 5180 | 5168 |

连续运行三组更新分别为7.066、6.333、1.349秒，末组实际2条样本。设备按1秒采样，连续运行48次、恢复运行7次；设备值为观测峰值，Torch分配器峰值覆盖整个trainer。主机GPU进程VmHWM最高4198560KiB。两次底座hash相同且前后不变，adapter均有更新。

第2步完整state hash为 `efb423314a70f118c9c4668ace4a932fe73710c66a39adabcb5a2d3f9db04736`；恢复前adapter与该步严格相同。恢复后两条样本的更新前loss和最终RNG hash相同。按运行前冻结的容差比较：944项中193项未通过，其中99个adapter张量、92项Adam张量、2项同一验证CE的核对；最大tensor绝对差0.0002683955244719982，最大容差比例188.8467。FP32 tensor容差为 `1e-6 + 1e-4*abs(reference)`，CE为 `1e-4 + 1e-4*abs(reference)`。失败保留，尚未确定原因；不得把进程exit0或旧CPU恢复PASS写成当前CUDA恢复PASS。

两个run的全部文件已由Colab控制器下载、清单回读并向远端确认；停止时核对了两个run的当前完整快照。实例占用973.294秒（含安装、失败控制、训练、传输），已确认不存在。该实例前后余额观察差0.34CU；与此前setup失败实例合计1642.723秒、观察余额差0.57CU，均计入原5400秒/8CU的G2上限。余额差不是费用账单。当前活动实例0。

| 私有证据摘要 | SHA-256 |
|---|---|
| Linux安装命令receipt | `571c42761707c33a5bb29cbf3c1ebd53b60a100a750d0bb8a56002e4a366a5dd` |
| 连续运行读回receipt | `f58e4a63674145ff193af22a41c6a2c9fc35d2dfd8bd179d2a472a4507bae2bf` |
| 新进程运行读回receipt | `5420cef61a08d520ccc6703fedde50f66861f6352428d061440ead3adb5665ba` |
| CPU保存状态比较receipt | `3fc985a68106f58f9d66226f55860987b0cf8619bceb362b0c440b435b31f135` |
| 完整比较结果 | `678960c8b76296863f3f83378d72633728012edf916ec104fb69d61499e269b3` |
| 连续运行持久回收receipt | `c1441ec3a532a10b5b8f9dff9df33bebb392eab2f886dbe3359abe8e4a48b851` |
| 新进程持久回收receipt | `4bba64aaf837fcce5285cbed37a76dfc136d810e61561fc514a6cc86e310731e` |
| 停止与不存在验证 | `9fc9027e7b6d8923ae71880454f6497a41d785d10c970835d611e10dab17035a` |

下一步由T1定位 `P04-CUDA-RESUME-001`，R1独立复核，之后S1在剩余G2预算内重新冻结必要的真实验证。正式SFT/DPO/模型评测仍NOT_RUN。
