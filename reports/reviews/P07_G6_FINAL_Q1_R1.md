# P07 G6 最终案例、模型说明与交接 Q1 审核 r1

2026-10-27（Asia/Shanghai）；实际审核者：Q1 AI。**PASS，最终受检候选为 `10f99b0b9f52d36b294a615e979a89dce77d7b1b`。** 真实服务的11次尝试、缓存隔离、取消重载和资源回收得到支持；10份完整模型响应均为 `tool_calls`，真实CLI两次工具换算正确后仍未给出最终答案。五类CPU scripted案例与这些模型观察已明确区分。本轮发现一处示例入口的状态错误，S1在正式结论出具前修正，Q1定点复核通过；当前未解决问题0。

依据[本轮任务](../../coordination/tasks/P07_G6_FINAL_REVIEW_Q1_R1.md)及[审核政策](../../coordination/REVIEW_POLICY.md)，本轮只读审阅已有数据、实际请求、轨迹及交付说明。新增固定模型推理、tokenizer编码、训练和GPU调用均为0；未修改生产实现、原始结果、评分或共享状态。不代签kris，也不声称其本人已掌握材料。S1可结合独立R1技术终验接纳本报告。

| 受检对象 | 精确身份 |
|---|---|
| 初始结果与说明候选 | `020953c87e973dd94ea16022e5d69de1ef5e4d7b` |
| 同轮部署/接手说明增量 | `739493a1c8381a1bca798344b993de08f4444e1e` |
| 示例状态修订及最终候选 | `10f99b0b9f52d36b294a615e979a89dce77d7b1b` |
| 实际CUDA服务源码 | `aaab0171246feaf307ad2c626108e94383e438d9` |
| S1原总索引SHA-256 | `06d5383eecf104f6927585defe2acc04383b3c9b32e4efb632c7561a229b8441` |
| 部署/接手增量索引SHA-256 | `26e35ea6b95f26defb341853d9292169a60f816b05f069130e78a311b0747d70` |
| 示例状态增量索引SHA-256 | `5341b615a8d281ffc050dc0081d5033d1ed93a31ba1e2500946a7652e7d1a6d4` |

原总索引的220份私有文件和11份公开文件已核对长度/hash，公开旧版本按初始候选回读；两次增量分别绑定。实际运行的132份包文件、48个依赖版本、七字段ModelIdentity、checkpoint、adapter、模板、冻结配置及11项计划均与请求/终态对应。M1保持Qwen3-1.7B固定revision加G3 step743，完整训练状态SHA-256为 `cfb02aec2279138c01f8b336abc08a588d0ab11efa8db68fd61ba0b6150b5d14`，adapter为 `973c440e29090892ad11d6d56b94bad4c98a5398c223e2b4302d7dba7c4640ed`。配置实际文件hash为 `8128aac4c67b2f6d7f46b39a562e2257b3568cc6a8fe09f5f78bf5586832787b`，冻结早于首个输出。

下表位置均按最终候选计；逐项证据和文件hash保存在私有 `document-review.json`。

| 材料位置 | 判定 | 核实内容 |
|---|---|---|
| [README](../../README.md)第7、27–33、65–81行 | PASS | 原分母、G6实际状态、scripted范围及公开交付边界 |
| [复现与交付](../../docs/19_REPRODUCTION_AND_DELIVERY.md)第17–119行 | PASS | CPU/真实入口、固定身份、鉴权、幂等、取消、计时与回滚范围 |
| 同文第123–152行 | PASS | 真实formal/train样本、EOS/因果mask、DPO SUM及固定SFT reference |
| 同文第156–166行 | PASS | 原G5/G6结果、真实失败与AI审核身份 |
| [最终说明](../../docs/10_LEARNING_DEFENSE.md)第3、9–16、24–30行 | PASS | 技术/内容审核职责、已支持结果与可选学习活动 |
| [S1服务报告](../S1_P07_G6_SERVICE_R1.md)第3–67行 | PASS | 全部实际尝试、语义观察、缓存/控制/回收与成本 |
| [部署路线](../../docs/06_DEPLOYMENT_ROADMAP.md)第3、30–42行 | PASS | 本次已运行状态、连接顺序及回滚未实测 |
| [仓库接手](../../docs/11_REPOSITORY_BOOTSTRAP.md)第5、9–19行 | PASS | 从当前证据接续，不重启首次建仓或P00 |
| [示例入口](../../examples/service/README.md)第3、15–25行 | PASS（同轮修正后） | 一个已运行真实输入、其余四个未运行完整案例与五类scripted结果分别表述 |

**同轮发现 `Q1-G6-DOC-001`（P2）保留。** `739493a`及更早候选的示例入口第3行称“真实 Colab/M1 对这些输入的表现为 NOT_RUN”。实际冻结的 `trajectory-input.json` 与公开 `normal-input.json` 逐字节相同，SHA-256均为 `fd71a22ca5f00498b590a702a9b38fcb64cee6658ed0a36e058280c22d713afc`；原说法会使读者遗漏该输入已运行且没有最终答案的事实。S1的 `10f99b0` 仅修改该段，准确写出三决策、两次1.5 MiB观察和第三次 `tool_round_limit`。Q1核对了五个输入的hash/JSON、原始轨迹及修订内容：另外四个输入与该轨迹不同，真实smoke的独立无需工具请求也不同于公开 `no-tool-input.json`。本轮未将其他四类标为已测。

该修订发生在Q1正式r1结论出具前，没有先行发布正式REQUEST_CHANGES。建议S1保留“发现已确认→S1同轮修订→Q1定点PASS”的事件链，接纳后记为已解决；新增正式未通过轮次0、当前连续失败数0。原错误版本和证据保留，不虚构或抹去审核历史。

五类原创CPU材料来自E1交付 `59b9c482e0faf93b1fbd5836db21933a6d7197a1`。其索引355份私有/24份公开文件已核对；Q1逐例阅读原始请求、Action、工具观察、终态并独立推导下表。复用R1 `00409b628af9fc2118cb547fd193d43752f77b44` 的七项独立CPU场景及干净环境结果，绑定173份当前源码/配置；未重复运行已通过且未改变的实现。

| CPU案例 | Q1独立推导 | 判定 |
|---|---|---|
| normal | 1536/1024=1.5；实际一轮换算观察后，脚本返回final=1.5 | 行为PASS，scripted语义success |
| no-tool | 2+3=5；直接final=5，工具child为0 | 行为PASS，scripted语义success |
| invalid-arguments | 构建编号999不在声明schema的允许集合，执行前拒绝，工具child为0 | 行为PASS，预期语义failure |
| recovery | 首次可重试失败后用新call_id、同工具/参数重试，观察中失败测试数为2，脚本final=2 | 行为PASS，scripted语义success |
| budget | 连续请求换算，前两轮得到1024 B=1 KiB；第三次在执行前因工具轮数上限拒绝，无final | 行为PASS，预期语义failure |

上述作者记录共15个fixture/工具child均已回收。原生产轨迹的 `semantic_outcome=not_scored` 保留；示例runner另行比较预期行为和答案。五项行为PASS包含两个预期失败，不能表述为模型100%成功。R1已有审查脚本错误及其定点修正记录保留，不计作候选修订失败。

真实GPU材料的11次尝试逐一匹配Mac原key/body、输入、seed42、远端accepted/started/terminal和模型身份。Q1独立解析10份完整raw Action，并重建真实CLI三次ModelInput，均与保存内容一致。

| 真实尝试 | Q1判定 |
|---|---|
| 1–5、7：单位转换及cache序列 | 6份raw逐字节相同，均请求正确的3.5 min→s换算；独立计算应为210 s。此组单决策请求实际执行工具数0，没有最终答案。 |
| 6：取消 | Mac读到running后取消，终态cancelled；原child回收、目录清理与lease释放有据。raw、生成token及内核执行进度未完成记录，保持缺失。 |
| 8：无需工具请求 | advertised工具为空，模型仍输出未声明的 `tool_0` 调用；未交给本地工具执行器。 |
| 9–11：真实CLI | 前两次实际工具观察均为1.5 MiB；第三次仍请求换算，执行前触及 `tool_round_limit`。CLI退出1，`budget_exhausted`、`final_action=null`，完整wall为14.378113秒，额外清理尾段0。 |

10次API completed表示模型响应返回，两个工具completed表示取得观察，均不等于完整任务成功。真实CLI的 `semantic_outcome=not_scored` 未改写，本轮开发观察也未加入G5正式分母。

真实命中来自第2、4次的 `cache_hit_tokens=580`、`prefill_tokens=1` 及一致的principal/输入/模型身份。跨principal、切回A和重载后均miss。已warm的B序列prefill为81.391→77.706毫秒，服务wall为3.678111→3.648646秒；首请求较大的prefill差包含首次CUDA执行效应。本轮支持缓存复用与隔离，不据此估计稳定吞吐或P95 SLO。

实际监听与两次SSH argv均限定loopback。原始HTTP确认同key/body回读不增生成、改seed为409、跨principal读/取消为404、改schema为400、错误token为401；最终accepted及尝试数仍为11。两个不同PID/epoch的CUDA worker均有prepare、回收和lease释放证据，epoch1回收后epoch2才启动/ready。`running`只是调度状态；第11次后先由次数上限回收child，再以SIGTERM结束HTTP父进程，不能把该信号写成再次清理活跃CUDA child。CUDA硬截止及部署回滚仍NOT_RUN。

71份远端载荷共137629 bytes逐项匹配回收manifest，manifest自身不计入71。两个CUDA child、两个Mac工具child、CLI父进程和两次SSH进程均有回收记录。完整分配837.615324秒、余额166.20→165.95 CU（观测差0.25）；安装、空闲、失败连接、传输和收尾计入总账。停止后的原始账户快照显示会话/活动分配为0。首worker cold load/prepare为6.765106/6.956720秒，重载为6.592775/6.783241秒；请求wall、生成阶段、清理尾段和完整分配的定义没有混用。原安装连接中断、SSH 429及S1审计脚本修正保持，不新增运行掩盖失败。

Q1从已验收真实v3/13例导出中回读 `effective-09` 的2048个位置。它属于formal/train，历史角色为system/user；prompt为1724、当前Action为108、EOS为1、pad为215。原监督位置1724–1832共109个；`loss_mask[1:]`对应因果监督位置1723–1831，仍为109。attention只覆盖前1833个位置，prompt/pad不计loss，EOS计loss，与SFT实现一致。原行/sequence及数组export身份与[19号文档](../../docs/19_REPRODUCTION_AND_DELIVERY.md)第123–134行相同；未复制原文或token IDs到公开材料。

两份完整G3训练状态、manifest和summary已按字节核对，未反序列化或重新加载模型。198/743次更新和验证CE约0.041494/0.024438的既有结论保持。M1为BF16未量化底座、28层Q/V LoRA rank8、alpha16、dropout0、FP32 adapter。实际监督目标全为 `tool_calls`，与已观察行为一致，但不能单独确定失败的唯一原因。

DPO原创例子按completion有效token（含EOS）的log-prob SUM计算，prompt/pad不参与。Q1以标准库独立复算相对policy/reference margin：同起点为0，loss为 `0.6931471805599453`；policy chosen SUM由−2提高到−1、其余保持时，margin为1，loss降至 `0.6443966600735709`。reference为独立加载且冻结的选中SFT模型，adapter保持启用；不得改成token mean或未加载adapter的原始底座。既有[R1数值审查](P05_G4_DPO_R1.md)及[r2输出预算修正](P05_G4_DPO_R2.md)复用，数学fixture没有被当作可训练偏好。G4实际80条候选为0有效偏好，DPO/M2保持NOT_RUN。

[此前Q1终验](P06_G5_FINAL_Q1_R1.md)中的真实G5 unit 6已按原结果行再次核对：两次动作各2个调用，第三输入1991加256预留超过2048，以 `backend_error/context_overflow` 结束，第三次raw未生成，5个owned child均回收。这个无需工具题说明格式与调用完成不足以保证停止/回答决策；没有补写final或公开隐藏题面。原M0/M1成功均0/28、A1恢复on/off均0/8、A2局部prefill收益保持。BFCL固定150条、227个函数根在严格契约下0合格，L2分数不定义，正式官方模型评分NOT_RUN。

两个官方固定revision的[Qwen3-0.6B LICENSE](https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/LICENSE)与[Qwen3-1.7B LICENSE](https://huggingface.co/Qwen/Qwen3-1.7B/blob/70d244cc86ccca08cf5af4e1e306ecf908b1ad5e/LICENSE)已回读，均为Apache-2.0；仓库原创代码/文档的MIT及其他来源边界分开保留。私有checkpoint、原始训练/隐藏测试、凭据和本机身份不进入公开交付。两份G3完整状态与原始证据通过私有索引定位；真实token文件为0600，已核查实际token值未进入Mac/远端运行回执。

首次G6之前的稳定代码 `98d642a116da94f2ab2b2aaeb6e931f79fd5cabc` 没有旧服务入口。回滚说明正确限定为停服、归档记录并恢复已验收代码/配置/G3制品，服务保持关闭；同模型worker重载不冒充部署回滚。

本轮新增实质发现1项，已在同轮修正并复核通过；无待修改项、无新增正式未通过轮次。后续如研究完整任务成功，应另设独立train/development材料验证最终回答、无需工具与停止决策，保持隐藏测试隔离；本报告不授权新训练。精确Q1提交与最终私有索引随[交接](../../coordination/handoffs/P07-g6-final-q1-r1.md)回报，阶段及问题台账由S1接纳后维护。
