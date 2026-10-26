# P06 G5 BFCL 固定范围零题处置 Q1 r1

2026-10-27，独立审核者 Q1 AI。结论：**PASS，接纳固定范围的 `NO_ELIGIBLE_INPUTS` 处置。** 三类各前 50 题，共 150 题，全部缺少冻结契约要求的显式对象闭合声明，无法按本轮允许的无损映射保留。L2 coverage 为 **0/150**；模型评测与正式官方评分均为 **NOT_RUN**，模型成功率不定义。S1 可接纳零题处置，当前无需生成 L2 计划或分配 L2 推理预算。

受检 E1 候选为 `7e56244c0d0cb5b07da48ee6585f31a3f04acc71`，审核基线为 `63d3fac94485f04c6a0ad38a6d997743f2235d02`。范围见[审核任务](../../coordination/tasks/P06_G5_BFCL_DISPOSITION_Q1_R1.md)和[G5 协议](../../coordination/tasks/P06_G5_PROTOCOL.md)；核对对象为[E1 报告](../P06_G5_BFCL_ANALYSIS_CPU_R1.md)及实际筛选产物。此 PASS 限于 BFCL 答前排除与说明，不代替 R1 的实现及官方 checker 技术审核。

固定来源为 [gorilla f7cf7359b7ac615a0b294831c5ba2bc95ee4a000](https://github.com/ShishirPatil/gorilla/tree/f7cf7359b7ac615a0b294831c5ba2bc95ee4a000/berkeley-function-call-leaderboard)。实际三份问题文件的 SHA256、长度和 Git blob 与固定提交一致；各取原序前 50 条，逐题 ID、ordinal、canonical hash 与 ledger 全部匹配，未扩大范围。输入索引中本审核所需的 20 份 E1 产物和 15 份交付文件身份核对一致；未将 E1 索引的全部 288 份产物计作 Q1 独立复核。

| 类别 | 已检查 / 保留 | 缺少显式对象闭合 | 字符串缺少支持上界 | 数组缺少支持上界 | 已知分组重合 |
|---|---:|---:|---:|---:|---:|
| simple_python | 50 / 0 | 50 | 22 | 2 | 8 |
| multiple | 50 / 0 | 50 | 32 | 9 | 11 |
| irrelevance | 50 / 0 | 50 | 26 | 6 | 9 |

排除原因可同时成立。直接检查 150 题中 **227 个函数声明**：所有根对象均未提供 `additionalProperties:false`；字符串、数组及嵌套对象的具体排除路径也与账本一致。逐字段检查六个关键实例，覆盖纯整数参数、无界字符串、默认值、多函数和嵌套任意键对象。纯整数参数实例已经足以确认：对象闭合要求本身可决定排除，无需依赖重合或长度理由。

227 个参数 schema 的投影仅改变 `dict→object`、`float→number`，逆映射恢复原值；函数名字映射可逆且无碰撞。原始默认值和不支持字段保留，不能为取得覆盖而删除。代码及产物没有补加对象闭合或长度约束。150 项 `length_status` 均为 `NOT_APPLICABLE_UNREPRESENTABLE`、`input_tokens=null`，没有将其描述为通过 2048 token 预检。

P02 参考绑定到 policy-a manifest `c728dfe385e340fadf1e5949976c012709fc10a1dbca9010548edf74785259e5`，实际读取 assignments/tool-lineage，共 11,300 条、3,517 个既有组，覆盖全部 split；未读取 held-out prompt 或答案。G4 为已接纳的 20 题、1 个组，tasks SHA256 为 `b9c6f18995579d8af1a58d137cafe9cc1c9f2f40279d9434aa85e2c7769eb015`；另纳入 10 个 P03 开发项。复用既有键提取与 metadata reader，以独立广度优先遍历复算所有候选的传递连接，得到 **111 个 component；7 个 component 的 28 题连接 P02，P03/G4 连接题数均为 0**，全部 assignment 与原 isolation.json 一致。所有 150 题均先参与连接，包括 schema 已不合格的题。本结论使用现有 tool/schema、规范化 schema、词法 template 和 source 键，不构成穷尽语义去重。

实际 selection SHA256 为 `4014d0c8d3ca46dc2def17f32b38cc1bbb3b67f0889f0fd48820fa7e93b24b69`。manifest、selection 及目录内容一致：selected 为空、selected_groups=0、inputs_sha256=null，目录仅有五份筛选和来源文件，没有 inputs.json 或空模型计划。问题读取和答案入口分离，空 selection 在答案读取前被拒绝；实际命令记录中的评分操作指向另一份原创 fixture。Q1 未读取官方答案。

复用并核对 E1 已执行的 19 个原创官方 scorer 案例，没有重跑 scorer。其中 8 个案例的 official raw 为真而严格成功为假，覆盖坏 Action、空输出、未启动，以及带合法 final 的超时、取消、基础设施错误和中断。严格成功须同时满足 completed、独立 Action 合法、官方判定为真。另一个 6 行原创 CPU fixture 明确标记 `ORIGINAL_SCRIPTED_CPU_FIXTURE`，两条件各严格 1/3、raw 2/3，单组区间为 NOT_ESTIMABLE；其 selection 身份与真实零题包不同。这些记录支持评分和说明的区分，不提供 M0/M1 模型效果。

Q1 本轮新增一次 CPU 产物核对，exit 0；没有模型、GPU、官方 scorer 或全库测试运行。私有 `review-p06-g5-bfcl-disposition-q1-r1/evidence-index.json` 绑定 37 份输入、审核脚本、逐题结果和命令记录，SHA256 为 `b2f06526fce5f54aed7a6af15f969cc622ddc74bbf4994654bccbba38e4715bf`；逐题结果 SHA256 为 `fad55817513d7c13d6f9762d7b1482991897020002ae8fc36143f4b32763b3a3`。公开交付仅本报告及[交接](../../coordination/handoffs/P06-g5-bfcl-disposition-q1-r1.md)。

本轮无新增整改问题。`Q1-G5-CORPUS-001/002` 不在本次审核范围，各自首次未通过和原失败历史保持，不据此关闭或改变计数。后续若要扩大 BFCL 范围或 schema 可表达范围，应在新结果产生前另行冻结协议；当前证据支持继续独立推进 L1/A1/A2 验收。
