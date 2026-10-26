# P05 G4 最终语义与说明审核 Q1 r1

2026-10-26，独立审核者 **Q1 AI**。**PASS（本轮语义与说明复核）；支持 S1 采用 `DATA_INSUFFICIENT_WITH_NO_DPO` 有据降级处置。** 新诊断在原三次输入不变的情况下返回了额外工具请求，未成功完成任务。原正式池仍为 80 条、0 成功、0 偏好，审核样本 0、误标率不定义，偏好质量门 BLOCKED。真实 DPO 容量、恢复、训练及 M2 checkpoint 保持 NOT_RUN；原 G4 验收中的 DPO checkpoint 条件未达成。

授权提交 `31dc871d0a4c8c2a04545dcfca684f483f1e0b4a`，新诊断执行源码为 PR29 主干 `3250f1b83ecbaccea535d74232d6c3f28ffe4df7`。范围见[本轮任务](../../coordination/tasks/P05_G4_FINAL_Q1_R1.md)，受检说明为[S1 生成与诊断报告](../S1_P05_G4_GENERATION_R1.md)。Q1 未修改 App goal 或共享状态，最终处置由 S1 裁定。

## 原结论复用与新诊断身份

固定输入索引的 111 份文件、55,616,193 bytes 全部核对 hash 和大小，其中原已审 42 份输入与 `5321842d3c457f2258485d406bebaa0cb7273399` 的证据索引完全一致。本轮复用原 80 条分母、前 12 条继承、零对提取、空审核门及 G3 监督覆盖结论，没有重跑全部旧审核或重复计数 G3 数据。原 `NO_ELIGIBLE_PAIRS`、`sample_size=0`、`error_rate=null`、`quality_pass=false`、`training_authorized=false` 保持。

新诊断仅执行原 ordinal 8、seed50 一次，使用独立 run ID、`REAL_CUDA_SFT_MODEL_VALIDATION_DIAGNOSTIC` 和 `formal_training_eligible=false`。固定任务、模型、checkpoint/adapter、采样及依赖身份与原样本一致；23 份回收产物与 manifest 对应，只有该候选的一组 started/terminal，未混入正式池。原正式 80 条仍为 PR28 执行结果；此前 profiler 与本次运行时诊断累计为两次单列诊断。

## 第三个动作的独立语义判定

三次完整 ModelInput 与原超时记录逐项相同。前两次完整 decision 记录，包括 raw text、解析动作、token 数和输入 hash，全部相同；两次 tool observation 也相同。原始任务明确要求依次执行文档查询和超时单位转换这两次调用，然后返回指定字段的最终 JSON。两次实际调用及结果符合原 oracle 的合法策略，第三次输入已经包含全部所需 observation。

新第三个动作在 **20.681 秒**完整返回 `filter_build_logs` 请求。该工具在提供的 schema 中，参数合法、Action JSON 解析成功；但它是完成明确两次调用之后的额外请求，违反当前任务约束。这个判断直接依据原提示与已完成的策略，不依赖“未匹配枚举”或全局预算失败来推断语义。

轨迹在执行该工具前以 `budget_exhausted / tool_round_limit` 终止，实际只有两次工具执行，没有第三次工具 observation，也没有 final。现有 `decision_verdict` 的三步交叉核对为 legal、legal、illegal；第三步归类 tool_confusion，因为该工具不在本题允许调用范围。对保存的实际轨迹作一次确定性 oracle CPU 重评分也为 failure，其通用原因是 `Execution terminated unsuccessfully`；实际 harness 终态原因仍是 `tool_round_limit`，两者不混写。

该诊断回答了原先的问题：校验移出逐轨迹预算后，第三次动作能够返回，但返回动作仍不符合终止要求。它没有产生可用 chosen。**原 ordinal 8 的第三动作未返回，仍为 unknown；原超时终态及其余 60 条超时记录均不重判。** 本轮没有补造 final、执行额外工具或制造偏好。

## 计时、资源与说明边界

| 项目 | 新诊断实测 |
|---|---:|
| 父进程完整文件预检 | 12.307 秒 |
| child 冷加载，不含预检 | 7.219 秒 |
| 上述两项合计 | 19.527 秒 |
| 轨迹耗时，含 child 冷加载 | 20.883 秒 |
| 完整段耗时，含预检 | 33.939 秒 |

原样本冷加载为 19.125 秒；新 child 计时移除了已计入父进程预检的成本，不能据 19.125→7.219 秒声称单请求整体加速。完整段仍包含预检，30 秒逐轨迹上限及 3 次决策、2 轮工具预算保持。单次诊断不估计批量吞吐提升或总体成功率。

外层 exit0 表示诊断程序正常结束，模型任务结果为 failure。3 条模型/工具进程记录均已回收；回收确认、停止记录及停止后的 usage 输出相互对应，活动分配为 0。新实例 718.631 秒、余额观测差 0.17 CU；与原记录相加，G4 为 **4,477.560 秒、1.75 CU**。剩余上限 17,122.440 秒、10.25 CU，数据不足不能写成预算耗尽。

G3 已核对的 5,938 train / 213 validation 监督目标全部为 tool_calls，原 CE 支持该目标集合的拟合。当前诊断不能证明 SFT 导致行为退化，也不能证明所有未返回动作或其他候选都无法成功。缺少原始模型同协议对照时，S1 保留这一解释边界是充分且准确的。

## 降级处置与后续比较

支持结束本轮固定候选方案并登记 `DATA_INSUFFICIENT_WITH_NO_DPO`：当前没有符合冻结规则的真实成功 chosen，已有 DPO CPU 数学/工程检查不能替代实际训练输入、CUDA 容量、恢复或 checkpoint。诊断使一个原未知动作可观测，仍未带来成功；无须为了得到正结果而改写失败、使用脚本轨迹或耗尽剩余预算。本结论针对当前冻结池，不是对所有后续采样方案的不可行性证明。

结束记录应保留原 G4 checkpoint 验收项未完成、零对及失败历史。随后冻结 G5 的 M0 原始模型与 M1 已选 SFT 对照，明确 M2 缺失；保持相同 runtime、工具、模板、解码、上下文、时限和 oracle，按固定分母报告失败分类、组隔离及不确定性。G4 同组材料若用于诊断，继续沿用 seen-group 身份。这个比较可以区分目标拟合与完整任务成功的变化；目前没有 G5 结果。

**新增审核问题 ID：无；不增加正式未通过计数。** 模型诊断失败是本次已如实保留的实验结果，不是新的实现审核失败。原 Q1-G4-CORPUS-001、P05-DPO-OUTPUT-001 的已接纳修订及首次失败历史保持；R1 技术终验和 S1 阶段裁定另行完成。

## 验证与证据

本轮使用既有 Python 3.14.7，命令 exit0。`Q1_PRIVATE` 为交付消息中的私有目录，`PYTHON` 为既有解释器，从审核 worktree 根目录执行：

```sh
PYTHONPATH=src "$PYTHON" "$Q1_PRIVATE/review_final.py"
```

| 证据 | SHA256 |
|---|---|
| S1 固定输入索引 | `e7e278dbe0a12f6dd51357612c0582c5253b9ae80a560cade1721d8bb61dede1` |
| 原选中 terminal 行 | `6738ac922ab2ab0c0a51bc8261afc40145cf854fd434ec727d41125df44716d0` |
| 新诊断 candidates.jsonl / terminal | `b1c4c7d1cf08ec1f52b7e7c56faa5a14bb4d8743534a1c992263fda077133f0e` |
| Q1 原始语义判断 semantic-verdict.json | `1af85c4549526c49f1d59de7e7b25f840bd6bca4578b8eca60538c1bb126a419` |
| Q1 review-result.json | `9b1089e8c1587edafed0e4a440e4efc2bda516ec02ebadfc28e87ae483b0abfb` |
| Q1 evidence-index.json | `4fcc6bfda5d33179f543156ae73bcbfcfe38aebf55b50024a305dd825df392b5` |

私有索引绑定 126 份文件，包含原始输入、复用审核输出、新旧比较、独立语义判断、计时/资源复算、脚本与实际命令记录。公开变更仅本报告及[交接](../../coordination/handoffs/P05-g4-final-q1-r1.md)。Q1 新模型调用、新轨迹、编码、训练和 GPU 作业均为 0；未修改生产实现、任务、标签、原候选或共享状态。
