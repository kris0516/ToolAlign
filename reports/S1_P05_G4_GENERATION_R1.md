# S1｜G4 真实候选生成 r1

2026-10-26。冻结20个train任务的80条真实SFT候选已全部完成并回收：**0成功、0有效偏好对**。61条超时、12条参数错误、5条调用未提供的工具、2条查询无记录。79条完整返回的首动作全部为`tool_calls`；原G3正式SFT的5,938条训练和213条验证目标也全部为`tool_calls`。当前证据要求同时处理重复文件验证成本和动作/终止监督覆盖，不能将失败全部归为超时，也不能从验证CE下降推定整条工具任务成功。

全部产物已回收，L4已停止。当前偏好池没有可供DPO使用的chosen；Q1处置审核待独立交付，DPO尚未运行。下一项运行前先完成批次文件验证复用的CPU修订与R1审查，再用独立小诊断区分时间不足和已发生的语义错误。以下保留原pilot与续段决定，并补充完整结果。

## 实际执行与输入

[PR28](https://github.com/kris0516/ToolAlign/pull/28)已合入主干 `6e2f1d28a8e5163ef29515da5cdf3a2c432ec7cc`。最终PR头 `eecdaf0e98d773d86c2dca86f4c58a9e42f3ad3a` 的CI 40311970393在Python 3.11/3.14全部步骤成功；S1确认合并后的文件树相同。生成实现经R1 `fac9ec5` 接纳，20题语料经Q1 `5044029` 复审通过。

实际采用[冻结计划](S1_P05_G4_GENERATION_PLAN.md)的Qwen3-1.7B、G3 step743 SFT、完整schema、固定non-thinking模板及原CUDA锁。任务文件SHA256 `b9c6f18995579d8af1a58d137cafe9cc1c9f2f40279d9434aa85e2c7769eb015`；checkpoint SHA256 `cfb02aec2279138c01f8b336abc08a588d0ab11efa8db68fd61ba0b6150b5d14`，adapter hash `973c440e29090892ad11d6d56b94bad4c98a5398c223e2b4302d7dba7c4640ed`。已回收12条的实际加载身份均匹配。

首段运行配置SHA256 `dfd36e61ecddff5590fe5a377ee19d04a8c2acc87edaa94eff0fb50c40e85129`，授权前12条、480秒、256 MiB输出。每条仍为3次决策、2轮工具、每次256新token、30秒整条轨迹deadline，冷加载计入deadline。实际seed42–53、完整candidate顺序和输入均已回读。

## 前12条结果

| 项目 | 实测 |
|---|---:|
| 完整终态 | 12/12 |
| 成功 | 0 |
| timed_out | 8 |
| invalid_arguments | 4 |
| infrastructure_error / OOM | 0 / 0 |
| 已提取有效偏好对 | 0 |
| 段运行时间 | 360.055秒 |
| 每轨迹冷加载，中位数（范围） | 19.077秒（19.020–19.463） |
| Torch峰值allocated / reserved | 3,761,385,984 / 3,852,468,224 bytes |
| 设备占用采样峰值 | 3,984 MiB / 23,034 MiB |

设备采样为333次、约1秒间隔，启动监控晚于作业启动，故记录为采样峰值；Torch计数来自各模型child。两类显存数值不相加。外层进程exit0、未达到480秒段上限，全部12条均有独立started/terminal记录。43份完整产物已校验回收到Mac并确认回收，候选文件SHA256 `e749539f1503f5b97147a7696a7aedcb5fdc35a5d6e9d0ed400b2f8fbeb13691`，batch SHA256 `ce20fafe8223f9496a18b53b518094bbbccdae0142154db0e47b281398be4138`。

前6条快照已显示两类具体问题：无需工具任务的4个候选均返回不允许的工具调用；日期任务返回了首次合法调用，随后重复调用或遗漏必需参数。冷加载约占30秒预算的三分之二，另外8条最终因deadline结束。终态超时不能抹去已经观察到的错误动作，也不能证明未完成的后续动作本来会成功。

T1只读核对源码和前6条原始记录，确认这两类问题；这次分析没有修改代码或调用模型。`cold_load_seconds`从首次tokenizer构建前计到模型恢复并完成CUDA同步，包含输入编码、导入、checkpoint/模型文件校验和加载，不含此前的进程启动及首次prefill/decode。现有累计指标不能把19秒归因于某个加载子步骤；若后续需要优化，先另记阶段计时诊断，不用猜测替代测量。第6条的第三次请求已经提交但无输出返回，不能写成“第三次请求前超时”。

实际提取使用原冻结80条计划，前12条全部按`nonsemantic_termination`排除，尚未启动的68条记为缺失终态；没有制造chosen或使用脚本答案替代。此为pilot处置，正式偏好池及Q1审核等待完整批次。

## 安装、连接与续跑

L4实际显存23,034 MiB。依赖安装完成181秒，48个锁定包及pip版本已回读，`pip check`通过。客户端SSH曾在安装中断开，但实例继续安装并产生exit0，S1读回完整安装记录后沿用该环境，没有重复安装。一次并发SCP因Colab单SSH连接限制被拒，发生于首个文件传输前；串行上传成功。原失败记录保留，后续同实例SSH/SCP操作串行执行。

首段未出现后端异常或显存不足，且剩余分配预算可以覆盖固定清单。S1冻结续跑配置SHA256 `fc40c499731a06d9675ac7e131090d2c4503696b4cbf98b25c0ec2faf72ce47f`：同一源码、任务、模型和batch身份，累计前缀80条，仅执行其余68个从未启动的ID，段上限2,400秒。12条原失败的终态原样继承，不改变deadline或采样，不按pilot产率替换任务。

本次实例分配上限5,400秒、G4全部分配累计上限21,600秒/12 CU。最终实际分配及完整结果见下文；原pilot失败与继续未启动ID的决定保留。

## 完整80条与资源回收

续段实际墙钟1,982.437秒，外层exit0、未触及段时限，80条均有完整started/terminal记录。前12条逐字节继承；其余68条只启动一次。全批batch SHA256仍为`ce20fafe8223f9496a18b53b518094bbbccdae0142154db0e47b281398be4138`，完整候选文件为`ea1c3dd168bc7d4edc3591186b2d3e8e6de4d5514b983891eb3f4761e1515dea`。续段175份产物已校验回收，含继承的原12条，文件份数不作为独立候选数。

| 完整批次项目 | 实测 |
|---|---:|
| success / infrastructure_error / OOM | 0 / 0 / 0 |
| timed_out / invalid_arguments | 61 / 12 |
| unadvertised_tool / no_records | 5 / 2 |
| 已返回完整决策 | 101 |
| 完整token计数的轨迹 | 23 / 80 |
| 已确认回收的模型/工具子进程记录 | 202 |
| 有效偏好对 | 0 |
| 冷加载中位数（范围） | 19.083秒（18.979–19.463） |
| 全部轨迹记录耗时合计 | 2,337.562秒 |
| Torch峰值allocated / reserved | 3,761,385,984 / 3,852,468,224 bytes |
| 两段设备占用采样峰值 | 3,984 MiB / 23,034 MiB |

两段设备监控共2,198次采样，开始均晚于作业启动；57条轨迹的未返回token无法完整计数，不能按0计成本。80条实际checkpoint/adapter、冻结seed42–121、实际ModelInput与决策hash均已回读。无需工具类别8条中，7条完整首动作调用工具，1条未返回完整首动作；澄清类别8条完整首动作均为tool_calls，其中5条调用未提供的工具。

冻结提取器将80条非完成终态统一标为`nonsemantic_termination`并排除，缺失终态为0；这个标签不是“没有语义错误”的结论。有效池、lineage和seed42抽样已冻结为空，sample_size=0、误标率不定义、training_authorized=false；Q1须独立审核零对及解释，不能将空池记成偏好质量PASS。

## 监督覆盖与加载诊断

S1对原G3已绑定stage只读计数：5,938条train和213条validation的expected_action.kind及category均为tool_calls，来源均为Team-ACE/ToolACE。train中180条以tool observation结尾，validation有12条，但监督目标仍是下一次工具调用。stage manifest SHA256为`04d6765255bebfafc1e5c8e07ff5a5ad7752c01dbce4059cea1c3ef2b03864bd`；未改原数据/序列/选模身份，未重新编码或训练。

这说明已完成SFT的监督目标没有覆盖最终回答、无需工具和澄清动作；G3验证CE测量的是该工具调用目标集合的拟合。当前首动作分布与这一覆盖范围一致，尚不能单凭两者证明SFT造成行为退化，因果比较需要原始模型与SFT的同协议结果。

另做一次独立cProfile诊断，重用首个输入与seed42，保持30秒轨迹时限；采用不同run ID及`REAL_CUDA_SFT_PHASE_PROFILE_DIAGNOSTIC`身份，不进入正式80条或偏好池。诊断配置SHA256为`6b7b131977f607ad1c968ed1727d26a08550be0fd5f67ba1feedfafce82b7bc3`，脚本为`18d2e63633516e68057207245b812733ad25021b8efad1e8bc1a3119cde00a23`；整段上限90秒/64 MiB，实际30.946秒、终态超时、exit0，17份产物已回收。

插桩冷加载21.807秒；首次tokenizer/编码阶段约0.900秒，模型加载阶段约20.995秒。函数记录中，`validate_model_files`累计12.230秒，`_hash_file`累计11.696秒，SHA-256 update自身11.015秒；嵌套数值不能相加。两份模型权重合计4,063,515,592 bytes，每个child重新读取全部固定文件。profiler有开销，不能将该分解直接套到未插桩的19.083秒。

测量支持先实现[批次文件验证复用](../coordination/tasks/P05_G4_MODEL_VALIDATION_CPU_R2.md)：完整验证一次，child加载前后确认文件身份未变，预检成本进入整段预算，原模型、输入与deadline保持。它不支持声称动作选择已修复。Q1另判断原超时轨迹中是否存在已返回动作仍符合合法策略的候选，用于一次有区分力的运行时诊断。

## 当前处置

本次分配含安装、空闲、80条正式候选、1条独立诊断及回收，累计**3,758.929秒、余额观测消耗1.58 CU**；已停止并确认无活动实例。G4累计边界保持，当前剩余17,841.071秒/10.42 CU。

DPO CPU候选`982cc191`经R1 `32a031b`审核为REQUEST_CHANGES：原生SUM/mask/reference与CPU恢复获得支持，新增P2 `P05-DPO-OUTPUT-001`要求将最终summary计入完整输出上限。S1回读31份审核证据，登记首次未通过计1，交E1[定点修订](../coordination/tasks/P05_G4_DPO_FIX_R2.md)。正式DPO、DPO CUDA容量/恢复及G5独立评测仍未运行；当前0对偏好不放行训练。
