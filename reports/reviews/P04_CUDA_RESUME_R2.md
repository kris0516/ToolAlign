# R1｜P04 CUDA 恢复诊断候选独立复核

2026-10-26。结论：**DIAGNOSTIC_READY**，范围为零更新诊断候选的技术复核。候选 `739c9b382f2841848a80b514ca1f31558728b5b3`，基线 `97637f336df4299a4bfd59b06f9716bb3c104796`。阻断项 P0=0、P1=0、P2=0。`P04-CUDA-RESUME-001` 仍 **OPEN**，原 CUDA 恢复 **FAIL** 保留；本次不构成恢复修复通过，也不增加正式修订失败计数。

[候选脚本](../experiments/P04_CUDA_RESUME_DIAGNOSTIC.py) SHA-256 为 `6b806fe75e5f20dd2c87ee0f433479b1d0c4c38ce0fbf513b2b498821e1e4dec`。四个新增文件符合原任务及 `9ca0bf1490070b00ed24e14169601fc5869cf58b` 的单探针补充范围；全部 73 个生产包文件与原第 2 步 checkpoint 的源码身份逐项相同。协议、依赖锁、数据和验收容差未改。

## 原差异与诊断价值

沿用本轮已完成的独立保存状态分析，没有重跑旧训练矩阵。两份第 2 步 checkpoint 字节和加载后的完整状态一致，恢复初始 adapter 摘要吻合；第 3 步的参数顺序、optimizer groups、步数、游标、RNG 和两条更新前 loss 一致。原容差下，99 个 adapter、91 个一阶矩和 1 个二阶矩仍未通过；验证 CE 差 `0.0030274804`，超过预设界限 `0.0001866044`。

两条路径最终参数与各自 Adam 状态的更新公式最大残差为 `9.45381e-10`。反推梯度最大绝对差 `0.0026839552`，整体相对 L2 差 `0.0085183299`；二阶矩也符合相应递推。这将定位重点收窄到梯度形成或累积。反推量不等同于真实更新前梯度快照，具体 CUDA 原因尚未确定。

候选提供了下一项有区分力的实测：恢复同一第 2 步状态后，仅对最后两条 train 样本执行 `checkpoint_on_a/b`、`checkpoint_off_a/b` 四组 backward。它能区分同模式重复差异与 checkpointing 开关差异；若四组都一致，仍需继续定位原连续运行与新进程之间的差异。候选报告保留了这一判读边界。

## 代码与边界核对

- 在首次 backward 前，实际 `restore` 后重新 `capture` adapter、完整 Adam、固定学习率、步数、游标及四类 RNG；按值、形状、dtype、字典顺序严格比较，并另核对实际参数名顺序，保存恢复实物与检查结果。
- 四组复用同一模型和最后两条固定样本；每组恢复原 RNG、清除旧梯度，以生产 `completion_ce` 和实际尾组除数 2 累积。脚本没有 optimizer update；最终逐项核对 adapter、Adam 及底座参数未变。
- 四组采用相同 CPU operator profiler，记录实际 attention 前向/反向算子名称与次数；这是算子记录，不声称已在本机观察到 CUDA kernel。梯度比较仅描述差异，不新设或放宽恢复阈值。
- 当前探针提交和实际执行包分别绑定；旧 checkpoint、原数组 manifest、模型、配置、依赖和运行时身份仍按原身份校验。脚本不能以新提交改写旧训练来源。
- 复用 GPU lease 与 20% 显存余量检查；入口限制 4 组、8 次 microstep、零更新、300 秒、128 MiB 输出。写入前检查输出预算，异常不自动重试。关闭 checkpointing 的真实显存仍待测。
- 对 S1 外层三个控制脚本作了只读核对：实际 HEAD 和探针 SHA 校验、唯一 tmux 启动、GNU `timeout --signal=TERM --kill-after=10s`、330 秒有限监测及退出回执。它们调用专用诊断入口。外层控制和 CUDA 路径本轮未执行，S1 仍需在合并后冻结精确请求再运行。

## 本轮验证与证据

精确候选的 `tests/training/test_cuda_sft_resume_probe.py`：**2 passed**。另用 20 个可训练参数的原创 CPU attention fixture 检查不同监督 token 数（2、3）的两例平均、旧梯度清除、快照独立、重复梯度、零参数更新及 RNG：**PASS**。与独立按监督位置构造的每例均值梯度完全一致；错误的全 token 池化梯度与之相差 `0.0017498368`，该 fixture 能区分两种归约。实际记录到 CPU attention 前向和反向算子各 2 次。

所有计算使用既有 Torch 2.8.0 CPU 环境、2 线程和每命令 300 秒上限。真实模型加载、真实数据编码、SSH、GPU 分配或运行均为 0；未修改共享环境，未重跑旧数组、安装、控制或训练矩阵。旧 CPU PASS 与原 CUDA FAIL 均保持其原范围。

以下原始结果和实际命令回执保存在 R1 本轮私有证据目录；绝对路径未公开。

| 证据 | SHA-256 |
|---|---|
| 独立保存状态分析 | `c2fe1fa3733a5af241f703802ddc1875d1cb908826357770380708d933c474fd` |
| 候选源码及外层控制字节绑定 | `feac912f5338f70f31ae7eb0091e1c2cc19aa42987f34a40fa9eef8498d1465a` |
| 两项候选测试命令回执 | `a95d6704040f6fb426bab1f3476cb67dbe5c126081fe6bb69e0ecb3645687cf8` |
| 独立 CPU attention 检查结果 | `f2dcc2e1cfbbec763f086f68e32b35ad2f8b9abe088446190bd2ba955a1cf5a3` |

接续由 S1 冻结合并后的源码、请求与资源界限，执行本候选的有限 CUDA 诊断。`summary.status=COMPLETE` 仅表示诊断执行完成；`recovery_acceptance=NOT_EVALUATED`，不能用来关闭原恢复失败。
