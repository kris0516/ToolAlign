# P05 G4｜最终技术复核 R1 r1

2026-10-26，独立技术审核者 R1 AI。结论：**PASS，支持 `DATA_INSUFFICIENT_WITH_NO_DPO` 的有据降级处置；新增 P0/P1/P2 均为 0。** 原 80 条正式候选仍为 0 成功、0 有效偏好。单列诊断在相同输入前缀下返回了第三次动作，但继续请求工具，最终因 `tool_round_limit` 失败。证据支持结束本轮偏好生成并转入 M0/M1 的同协议评测；DPO CUDA 容量、恢复、正式训练及 M2 checkpoint 保持 **NOT_RUN**。原计划的 DPO checkpoint 交付缺失须留在降级记录中，G4 最终状态由 S1 裁定。

授权提交 `31dc871d0a4c8c2a04545dcfca684f483f1e0b4a`，范围见[技术复核任务](../../coordination/tasks/P05_G4_FINAL_R1.md)。实际诊断执行 PR29 主干 `3250f1b83ecbaccea535d74232d6c3f28ffe4df7`。R1 核对了 [S1 报告](../S1_P05_G4_GENERATION_R1.md)对应的 **111 份输入、55,616,193 bytes**，全部文件 hash/大小一致；实际记录的 93 份执行包文件与执行提交及受检文件逐字节一致。保存的 CI 40331335284 显示 Python 3.11/3.14 两项作业及全部步骤成功；本地核对合并树与受检头 `6bb18ee970e9a89d49af05ea0062394f26cf6905` 的树一致。

## 实际诊断与原样本对应

新 run、控制 payload、授权、固定任务、48 包锁和实际环境绑定一致。运行配置 SHA256 为 `7096ccff37566516bbfe2b678eba0745b899f9617c4823baea0b102ed8b88e13`；回收脚本与此前 R1 已审脚本逐字节一致，SHA256 为 `c951acfe94069f0ffd40f4cb405d2b04bf31dd1ecd4588030b33f76412f5cc40`。模型仍为 Qwen3-1.7B 固定 revision、G3 step743 SFT，实际 backend 报告的 checkpoint/adapter hash 与冻结身份一致。

此次只有 **ordinal 8（第 9 条）、seed 50** 的一组 started/terminal 和一条候选输出，采用独立诊断身份及 `formal_training_eligible=false`。R1 从原候选文件复算该行 hash，与 Q1 选样和授权一致；新三次 ModelInput 与原三次输入逐项相同，首输入同时与任务投影一致。前两条完整 decision 对象相同，包括 raw text、解析动作、输入 hash、token 数和 finish reason；两次 tool observation 也相同。

三次 raw text 均重新解析并匹配所存动作，实际输入 hash 逐项匹配。新第三动作在 **20.681 秒**返回 `filter_build_logs` 请求；实际只执行了前两次文档查询、单位转换，第三次工具未执行。最终预算为 3 次决策、2 轮工具、4,536 input tokens / 144 output tokens，token 计数完整，终态为 `failure / tool_round_limit`，没有 final。原先未知的第三动作现已观测为额外调用；该结果不重判其余 60 条超时候选，也不支持 SFT 导致退化或 DPO 负效果的结论。

原 80 条文件保持 Q1 已审 hash `ea1c3dd168bc7d4edc3591186b2d3e8e6de4d5514b983891eb3f4761e1515dea`，前 12 条与 pilot 逐字节一致；80 个候选 ID 唯一，ordinal 与 seed42–121 完整对应。终态重计为 61 timed_out、12 invalid_arguments、5 unadvertised_tool、2 no_records。原 preferences/lineage 仍为空，80 条处置记录及空抽样不变；新诊断未替换原行或进入正式提取。新候选文件 SHA256 为 `b1c4c7d1cf08ec1f52b7e7c56faa5a14bb4d8743534a1c992263fda077133f0e`。

## 计时、预算与回收

| 项目 | 独立回读结果 |
|---|---:|
| 父进程完整文件预检 | 12.307 秒 |
| child 冷加载，排除上述预检 | 7.219 秒 |
| 预检 + child 冷加载 | 19.527 秒 |
| 轨迹 / 完整段 | 20.883 / 33.939 秒 |
| Torch 峰值 allocated / reserved | 3,765,318,656 / 3,867,148,288 bytes |
| 设备采样峰值 / 容量 | 3,952 / 23,034 MiB |
| 设备采样 / 模型与工具进程已回收 | 34 次 / 3 个 |
| 本次分配 / 余额观测消耗 | 718.631040 秒 / 0.17 CU |
| G4 两次分配累计 / 余额观测消耗 | 4,477.560427 秒 / 1.75 CU |

已审脚本只调用一次完整预检，然后把当前验证对象传给原 backend；执行源码保持加载前后复查，实际记录达到 `decision_complete` 且标明复用策略。轨迹 deadline 仍为 30 秒，段上限 90 秒，3/2/256 预算保持。预检进入完整段与分配成本。原样本 child 冷加载为 19.125 秒；新 7.219 秒排除了父预检，因此本次支持第三动作在轨迹预算内返回，尚未测得单请求整体加速或批量吞吐提升。

R1 从原始采样复算设备峰值、host 可用内存最小值及进程 HWM，与资源 summary 一致；Torch 和设备采样分别保留。23 份 manifest 文件逐一核对，并核对回收 tar 的 hash、大小和全部成员内容，ACK 与 stop-ready 记录相连。三个子进程均 `reaped`、目录已清理；模型进程在收尾中停止，两工具进程 exit 0。外层 exit 0、未触发段超时；模型任务本身失败的终态保留。

两实例停止记录及前后余额记录一致，最后 usage 为 0 活动分配。分配时间与开始/停止时间戳在毫秒内相符，包含安装、空闲与回收。累计余额观测消耗由 169.09−167.34 复算；剩余上限为 17,122.439573 秒 / 10.25 CU，预算未耗尽。新实例安装的客户端 exit 1/SSH 断开记录保留；远端 setup exit 0、48 包版本与锁一致、`pip check` 通过，没有将连接失败写成安装成功的原始回执。

## 既有证据与处置边界

执行主干与 [R1 文件验证 r2](P05_G4_MODEL_VALIDATION_R2.md)受检集成提交之间的生产、测试、配置、依赖及脚本无差异；DPO 目录、配置和锁与 [R1 DPO r2](P05_G4_DPO_R2.md)候选一致。因此复用原 47 项文件/生成检查、独立 spawn 反例，以及 [DPO 首轮](P05_G4_DPO_R1.md)的 SUM/mask/reference/CPU 恢复和 r2 输出预算结论，未重跑矩阵。原 `P05-DPO-OUTPUT-001` 首次未通过及关闭历史保持，当前连续计数无需增加。

此前 [Q1 零对处置](P05_G4_PREFERENCE_Q1_R1.md)绑定的 42 份原始输入与本次输入逐字节一致，审核样本仍为 0，误标率不定义，DPO 质量门 BLOCKED。按[冻结协议](../../coordination/tasks/P05_G4_PROTOCOL.md)，零对不能启动真实 DPO；剩余预算不能替代合格 chosen/rejected。CPU 数学与工程验收不填补 CUDA 容量/恢复/训练或 M2 的缺失。

建议 S1 结合独立 Q1 终验按上述有据降级结束 G4，并在 G5 冻结已有 M0 原始模型与 M1 已选 SFT 的共同输入、模板、解码、预算、oracle 和测试分母，显式单列 M2 为 NOT_RUN。该比较能区分已有 SFT 的 next-tool-call 拟合与完整任务表现；遵守原分组和最终测试隔离，不把已用于生成与诊断的 G4 train 任务当作独立 held-out 证据。本轮不要求补造偏好或继续消耗预算。

## 实际核对命令与证据

新增独立 CPU 文件/记录核对命令 `audit-02` **exit 0**，使用已授权的既有 CPU 环境，未安装依赖、导入模型框架、调用模型或连接远端。实际绝对参数及 stdout/stderr 在私有回执中；`PYTHON` 为该解释器，`R1_PRIVATE` 为交付中的证据目录。

```sh
"$PYTHON" -B "$R1_PRIVATE/run_check.py" audit-02 "$PYTHON" -B "$R1_PRIVATE/audit.py"
```

初次 `audit-01` 因审核脚本误要求 `output/run.json` 与原 run 的序列化字节相同而 exit 1；核实输出副本为字段完全一致的规范 JSON 后修正断言，原 run/control 字节 hash 约束保留，原脚本与失败回执也保留。这是审核脚本修正，不增加生产候选的正式未通过计数。

输入索引 SHA256：`e7e278dbe0a12f6dd51357612c0582c5253b9ae80a560cade1721d8bb61dede1`。R1 私有索引 `.toolalign-local/review-p05-g4-final-r1/evidence-index.json` SHA256：`acd061720acb9bf45ba8c345212d50f55c81c745322511d59bce90ea0a94a1b0`。公开变更仅本报告及[交接](../../coordination/handoffs/P05-g4-final-review-r1.md)；未改共享状态、App goal、生产文件或旧审核。
