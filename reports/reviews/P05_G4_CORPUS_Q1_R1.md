# P05 G4 生成前语料 Q1 审阅 r1

结论：**REQUEST_CHANGES**。20 条任务的目标、数值、对象、日期、调用限制、合法调用策略及来源分组均已逐项审阅；18 条通过，2 条存在同一个答案类型约束问题。修订这 2 条的提示或答案接纳规则后，重新冻结受影响的数据身份即可。本轮没有真实模型候选或正式偏好，不能据此计算偏好误标率或宣告 G4 偏好质量 PASS。

审核者为独立 Q1 AI。授权提交：`fbd4056baf25f3ce65e0ec70823a4ecbbcbeb96c`；范围遵循 [任务包](../../coordination/tasks/P05_G4_CORPUS_Q1_R1.md) 和 [G4 协议](../../coordination/tasks/P05_G4_PROTOCOL.md)。实现技术验收仍由 R1 承担。

## 需要修订的实质问题

**Q1-G4-CORPUS-001 / P2：版本答案的 JSON 类型没有在提示中规定，封闭答案标注却只接纳字符串。**

影响固定 `tasks.json` 的 `tasks` 数组第 10、13 项，按 1 起算。两项分别返回版本字段和版本列表；提示规定了返回字段、数量、布尔值及列表形式，却没有规定版本值或列表元素必须是字符串。工具参数中的字符串 schema 约束调用参数，不能自动成为最终回答的类型约束。

独立 CPU 反例保留全部正确调用、版本值、顺序和其余答案，仅把这些版本值从 JSON 字符串改为同值数字。两个实际结果均为 `failure / Final semantic value mismatch`。authoring 同时将两项设为 `closed_answer=true`，因此不能用当前封闭枚举证明这类回答有语义错误。这里确认的是提示与判定规则之间的缺口；尚未生成任何真实 rejected，也没有测得真实误标率。

最小整改：在两项提示中明确要求版本字段及版本列表元素使用 JSON 字符串；或者将相应等价答案纳入接纳范围。若保留开放表示，无法证明错误的答案须为 unknown/tie，不能成为 rejected。整改后复核受影响任务的提示、authoring、oracle 和清单 hash；不需重做未受影响的 P02/P03 数据。

定位时除数组序号外，核对任务对象的 canonical SHA256：

| 序号 | 任务对象 canonical SHA256 |
|---|---|
| 10 | `fee82cde634a18faa0cd47c747fca5095de8a0395b096705c9e7a8854fa0e72f` |
| 13 | `fa18b64766c4f91cf678bb403cab8d2e41fa221fe1d45aaf4c48a550ea4b9a41` |

## 已支持的语料与分组结论

- 20 条任务包含 12 个 family、10 个类别，全部为新原创 train。逐项核对了答案算式、字段、版本、日期、对象以及调用限制的提示依据。对照 10 个 P03 公开开发例，任务目标或所需推导发生变化，没有发现仅换 ID 的复用。family 数不代表独立统计单元。
- 每条提示均暴露相同的全部 6 个固定工具/schema，20 条组成 **1 个 train 连通组**。与 P03 的共享 schema 已披露；P03 保持公开 validation 开发诊断身份，未来同组任务只能报告 seen-group 诊断。
- 独立检查 P02 全部 11,300 条 assignments 和 16,650 条 tool-lineage 元数据，覆盖 train 10,033、validation 411、test 381、ood_test 475 条，对应各 split 的 2,561、317、293、346 个 group。来源、工具名、原 schema、规范化 schema、冻结模板键均未检出新任务交叉；无需隔离新增分量。模板结论限于冻结词法规则，不声称穷尽语义近重复。
- 分组根与冻结 v3 的关系已由 v3 selection manifest 的 `inherited_input_binding` 独立核对：原数据 manifest 的 canonical hash 及完整 artifacts 映射一致，两份分组元数据文件 hash 一致。没有读取 held-out prompt/答案；原 P02/P03 文件未修改。
- 三项依赖任务的现存正向轨迹均在后续调用前获得所需 observation，包含可重试错误。独立探针也确认：提前把依赖调用或重试放进同一 decision，现有 oracle 仍可能返回 success。因此后续必须执行已登记的 `observation_dependencies` 与真实 `decision_inputs` 检查。这是协议已覆盖的消费者边界，不另列语料缺陷。

## 实际 CPU 核对与证据

复用固定的 32 条正向替代策略及 20 条反例 CPU 摘要，没有重跑这 52 条轨迹。索引提供的 40 条原始轨迹已重新绑定任务、oracle、完整 ModelInput hash 和进程回收记录，并用原 oracle 重评分，得到 20 success / 20 failure；其余 12 条替代策略复用已提供摘要，并逐项检查 authoring 中的合法性，不声称重新执行或回读其原始轨迹。

本轮另执行 **5 条合成 CPU 探针**：2 条版本表示反例均返回 failure；2 条提前合并依赖调用的边界探针返回 success；1 条合法调用逆序且分成两轮的替代策略返回 success。全部进程已回收。脚本轨迹仅为审核证据，不登记为真实 chosen 或正式偏好。

实际检查命令如下。`Q1_PRIVATE` 为交接给 S1 的私有证据目录，`PYTHON` 为本机已有 Python 3.14.7 环境；从本审核 worktree 根目录运行，三条最终命令均 exit 0，无安装、模型加载、编码或 GPU 使用。

```sh
PYTHONPATH=src "$PYTHON" "$Q1_PRIVATE/audit_corpus.py"
PYTHONPATH=src "$PYTHON" "$Q1_PRIVATE/probe_boundaries.py"
PYTHONPATH=src "$PYTHON" "$Q1_PRIVATE/record_verdicts.py"
```

| 固定输入或私有证据 | SHA256 |
|---|---|
| S1 快照索引 | `3bf2f4664fb185e9595dad044b57691ef5979519a0e89d2402fec3b274c6fea0` |
| tasks.json 文件 | `d9fc455fa667bc323249bc5907571f1e38b446bc97f4f4b3da24a813d9649030` |
| 任务包 canonical hash | `270bd53db823baeb0ae9a1193a427313c9ad4a5b6947505c5e7658c0901d2803` |
| package manifest | `41284ee99539c9eebb8ba8eec53e50f4811a4ee48aa4b3f4ba1f069ca0d577d0` |
| 冻结 v3 selection manifest | `d765493c156d047cfaadce9c49e7edf25b973907d6a764f3272090786693efbc` |
| evidence-index.json | `b85529e78e4c45adb379a809c25e64614b5434fb74c008be7205e86b18a2254a` |
| semantic-verdicts.json，20 项逐条判断 | `7fd03531e49bda35fa18190381b351314213bdf93fa41ce3dc1fabe3c1e067a4` |
| static-audit.json，绑定与分组检查 | `17f2207c3bea1dbd5913338bf9297616e000cc097b4d73e5eaaf929ba5eff351` |
| cpu-probes.json，5 项独立探针 | `3a4975cacfb6c36cf28c3df7ce54c5cf3d012b8379bbbd22f4dfeba5352f3f5d` |

任务原文、oracle、authoring、逐项算式和原始轨迹均留在私有证据目录。公开交付仅本摘要与[交接](../../coordination/handoffs/P05-g4-corpus-q1-r1.md)。正式偏好池冻结后的 Q1 分层审核与严格大于 5% 阻断规则仍须另行实际执行。
