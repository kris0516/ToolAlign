# P05 G4 train 任务与决策偏好 CPU 包

状态：READY_FOR_REVIEW。D1 实现提交 `147d0450447a7ad543a7a913f2a9084b039b849d`；基线 `1267d1a33dfb08bfd9800b80ea97315730748952`，派发授权 `6d5df60591dda6c5e63b8d8c8b8f45bbb828d022`，采用协议补充 `8b84a524c55bdb31edc9425814ce8eb2575e9f48`。分支 `codex/d1-p05-g4-preference-r1`。公共 `toolalign.*.v1` 契约、P02/P03、工具实现、oracle、模型模板及训练代码均未改。

本包交付 20 个新原创 train 任务，12 个 family、10 类任务，全部暴露同一六工具 registry，因此只有 **1 个连通 group**。冻结 P02 元数据中未发现该新分量触及 validation/test/ood_test，保留 20、隔离 0。它们可用于后续受审的 train 候选生成；未来同组评测只能作为 seen-group 诊断。真实 SFT 候选、正式偏好质量、DPO 均为 NOT_RUN。

## 私有数据与分组

完整 recipe 的提示、参数、答案、允许策略、显式约束和 CPU 脚本位于私有 `authoring-input.json`，公开代码读取该输入。公开测试另用 5 个小型 synthetic 例，未包含正式 20 例。真值根据已有原创静态资源独立编写，验证时使用真实 CPU executor；工具实现的返回值不作为唯一真值来源。

| 类别 | 任务数 |
|---|---:|
| tool_confusion | 3 |
| object_parameters | 2 |
| date_parameters | 2 |
| version_parameters | 2 |
| argument_operation | 3 |
| numeric_units | 1 |
| no_tool | 2 |
| clarification | 2 |
| multi_step | 2 |
| fault_recovery | 1 |

来源为 `toolalign-original-g4-train`，revision 为 `p05-g4-task-families.v1`。实体变体保留 family；分组使用来源、family、冻结词法模板 key，以及 prompt 中全部工具的名称、schema 和规范化 schema，包含未调用工具。P02 使用既有 `assignments.jsonl`/`tool-lineage.jsonl` 元数据，核对原 manifest 的文件 hash；11,300 条来源分配中 train 10,033、validation 411、test 381、ood_test 475。未读取这些 held-out 样本的提示或答案。

新分量若连接任一 held-out P02 group，整个新增分量隔离，P02 的原 group/split 不变。词法模板检查沿用冻结索引，不宣称穷尽语义改写。P03 原 10 个开发例保留公开 validation 诊断身份；200 条新任务与开发例的比较均记录共享六工具/schema，未发现换 ID 或相同真值/策略的开发例副本，不宣称 schema 隔离。

| 冻结材料 | SHA256 |
|---|---|
| 私有 authoring 输入 | `919a6056464498291bdecf12545e14c53578d33e96c63d4857e721706ed0ad82` |
| 最终 tasks.json 文件 | `d9fc455fa667bc323249bc5907571f1e38b446bc97f4f4b3da24a813d9649030` |
| task list 规范 JSON hash | `270bd53db823baeb0ae9a1193a427313c9ad4a5b6947505c5e7658c0901d2803` |
| group-audit.json | `f8349fdee18988336ca64c6c0b8313fbd0f51e5315c6e63e1e2f43dd070dac8d` |

## 提取与审核接口

`tasks.json` 保持共享的 `toolalign.preference-tasks.v1` 结构。私有 authoring/manifest 为 P05 内部 sidecar，T1 不需要将其交给模型。构建、CPU 检查、提取和审核材料写出使用 `python -m toolalign.data.preferences`，输出必须位于私有目录。`build --authoring … --p02-manifest … --development … --output …` 不内置正式 recipe；输出含 tasks、authoring、group-audit、summary 和 manifest。

候选执行前用 `extract.freeze_plan(bundle, model_identity, candidates, synthetic=False)` 固定 P05 plan。`candidates` 是 task_id 到 `{candidate_id, generation_parameters}` 列表的映射，每任务 1–4 条；ID 的字典序决定配对顺序。该 sidecar 须与 T1 预先固定的执行 ID/采样参数一致，不在看到结果后补定。正式模型身份绑定 G3 选定的 Qwen3-1.7B revision 与 adapter 参数 hash；完整 model/tokenizer/template 身份由计划与实际候选逐条核对。

`extract --package … --plan … --candidates … --output …` 消费共享候选行，输出冻结 `preference.v1`、lineage、候选及配对 dispositions、summary 和未填写的 Q1 材料。实现规则为：

- 从初始 ModelInput、raw Action、对应 execution/observation 事件重建每轮请求，与实际 decision_inputs 及其 hash 核对。拒绝混合 trace、未来 observation、oracle 字段泄漏、raw/parsed 不一致和模型/采样身份不符。
- 重新计算整条 semantic oracle 判定；仅处理完整 finalized 的 success/failure。格式、长度、超时、基础设施、缺失和 interrupted 均保留处置及原分母，不产生正式负例。
- 只在完整实际前缀相同的首次语义分歧配对。JSON 排版/key 顺序/call_id 不单独形成偏好；call_id 已使后续历史不同的，不改写历史制造共同前缀。较早的合法不同策略为 tie，后续失败不能追溯把它变成负例。
- chosen 当前动作须有剩余合法策略，依赖调用还须在更早的 decision 中已有 observation。同一 decision 中列出两次依赖调用，即使原 flat oracle 判 success，也不能提供该证据。
- rejected 当前错误来自输入中明确的工具/参数/调用数量或结构化答案要求。未枚举且不能证明错误的动作是 unknown；开放任务的合法 min 转换反例保留为测试。
- 每任务按固定 ID 组合顺序取第一有效对。原始 completion 直接保留；preference 内参数绑定 chosen，lineage 保留双方实际参数、位置、完整前缀 hash、候选/trace hash、错误类别和原配对顺序。

Q1 材料按 seed 42 预先固定 pool、类别配额和样本。每个非空错误类别至少一对，其余按剩余类别数量比例向下取整，剩余名额按固定类别顺序分配；层内按 `hash([42, preference_id])` 排序。样本数为 `min(total,max(100,ceil(total*0.10)))`。结果 JSON 需提供 sample hash、实际 reviewer 和逐项 pass/fail/unknown 及理由；生成器不填写 Q1 结论。

`apply-review` 保留原抽审分母，unknown 计误标，严格大于 5% 阻断；已确认 fail/unknown 全部移出训练，即使批次未超阈值，也不换对回填。零对或缺审不能通过。synthetic 模式和 scripted 身份不能转换为正式训练池；正式质量门通过也不替代 S1 后续训练授权。

## 已运行的验证

环境为已有 Python 3.14.7，没有新增安装。完整 argv、时间、退出码、日志、源码文件 hash 和私有路径见 `.toolalign-local/p05-g4-preference-r1/commands.jsonl` 与 `handoff-index.json`。所有 pytest 使用本轮独占的新 basetemp。

| 实际命令范围 | 结果 | 退出码 |
|---|---|---:|
| `python -m pytest tests/data/preferences -q --basetemp …`，最终私有输入拆分版 | 42 passed | 0 |
| `python -m toolalign.data.preferences build --authoring …` | 20 train / 12 family / 1 group；隔离 0 | 0 |
| `python -m toolalign.data.preferences validate-cpu …` | 32 条正向替代策略及 20 条反例，52/52 符合预期；自有进程均已回收 | 0 |
| `python -m toolalign.data.preferences extract …`，最终私有包 | 40 条 scripted 测试候选全部保留，20 对 synthetic 偏好，Q1 未填写 | 0 |
| `ruff check .` | PASS | 0 |
| `python scripts/check_contract_freeze.py` | 4 个冻结契约文件 PASS | 0 |
| `python scripts/check_public_content.py` | index/工作文件扫描 PASS | 0 |
| `git diff --cached --check` | PASS | 0 |

测试覆盖 P02 全 split/未调用工具桥接、开发例改名排除、合法替代 tie、正确首步后错误答案、格式/call_id 差异、同前缀故障恢复错误、无需工具误调用、同轮依赖、未来/混合 trace、非 train、未知合法动作、不同 seed sidecar、缺失/重复/interrupted 分母，以及零对、少数类别、5%/6% 和 unknown 的 Q1 规则。

52 条 CPU 执行发生在 recipe 移出公开源码之前；拆分后 tasks、authoring、group-audit、summary 四文件逐字节不变，执行/提取/审阅/分组模块 hash 不变，故复用该执行证据，并重跑受影响的构建、CLI 和 42 项测试。检查记录为 `private-split-verification.json`。开发期 ruff 的导入排序/未使用导入已修正；没有剩余测试失败。全部历史输出留在原目录。

真实模型前向、真实 tokenizer 长度/吞吐、正式候选产率、Q1 正式偏好质量、DPO、模型语义评测均 NOT_RUN。没有 GPU 分配、模型/数据上传、付费 API 或服务部署。T1/S1 仍须在实际生成前检查 2048 上下文（含生成空间），保留超长及启动中断分母，并由 R1/Q1 独立验收代码和实际材料。
