# P04-SFT-DATA-V3-R1｜冻结数据与数组衔接独立审查

状态：IN_PROGRESS，R1，已于2026-09-07 19:40:27 UTC按完整授权 `4ea69e1339c6b0efb14d0149b77b2442601ddd9c` 原生派发并核验新轮 ACTIVE；新分支/身份与完整 intake 已交付，19:57:46 UTC经S0核验64,645路径；16授权/609输入、原571公开Git映射及30文件/1链接缺失例外保持，S0证明 `1c8cda1a12488dc2994815f2e2b92254c00c0c78eeb591dc6c933ca06240c8cf`。完整 candidate / 审查 checkout base 为 `f3b7f1a1abb23cce3bdccb74ddc6d2e0477bb2aa`，tree `1cd40f093c17da1c5a1f1399117c29eb3c1d9547`；生产基线 `48be4352bbad53ced5af84186edac036dd0ff2ca`、生产 checkpoint `bfdf2a256065d5396e6f7a4860fd7c7506f5c278`。完整 authorization_commit 为包含本次冻结范围的 S0 协调提交，由原生分发给出精确 SHA。T1 已 completed/idle，S0 接收 10,935 路径/40 原命令及实际归档，证明 `6eec52c12fe6a97a04f167a636fee7813efa22a5d96728dc80273ffe8aabd190`；见[完整接收](../../reports/S0_P04_DATA_V3_CPU_HANDOFF.md)。下述独立额度只随本轮精确原生派发生效。

沿用原独立 R1 App 任务和隔离 worktree，gpt-6-astra/max；拟建 branch `codex/review-p04-sft-data-v3-r1`、私有 scope `review-p04-sft-data-v3-r1`。遵循 plan-v0.1、coordination.v1、toolalign.contracts.v1、ADR-0026 及 REVIEW_POLICY。上一轮原 R1 `dbd11d03e69c650efdb330f79ec380dd9914fa89` 已接收；新派发前由 S0 再核验原生 completed/idle 和旧封存。新 identity 仅写新 scope，原根身份与所有旧 FAIL/PASS、原始运行和私有 f708 保持，不将 f708 加入公开历史。

先读届时完整授权中的 AGENTS/GOAL/PROTOCOL、REVIEW_POLICY/REVIEW_FAILURES、RESOURCE_LOCK、ADR-0026、本任务、[T1 任务](P04_SFT_DATA_V3_CPU.md)、[精确 CPU 配置](../../configs/sft-data-v3.v1.json)、[G-DATA 批准](../approvals/P02_DATA_V3.json)和 S0 完整交接报告，再读取精确候选的全部授权 diff、T1 报告/handoff 及私有实物。S0 的验收数字和 T1 的自测结论是审查输入，R1 自行判断。

只新增 `reports/review/P04-sft-data-v3-r1/` 中的审查报告、去敏索引、必要原创小探针，以及 `coordination/handoffs/P04-sft-data-v3-review-r1.md`。被审实现、配置、测试、依赖/CI、S0 台账/看板和其他 worktree 只读。不合入更新 main、不修完实现后给原候选签通过；发现问题先交最小证据，仍对冻结候选给出完整结论。

审查边界：

1. 完整 diff 仅在 T1 授权路径，原 `data.py/config.py/CLI`、collator/plan/model_io、数据 v1–v3 生产器和 toy/runtime 守卫保持。新增配置必须逐字等于 S0 授权 SHA `e27a7d4bcdd378944af56559833c3bcd10f601b689a75f1daec96b884bd780c1`；不存在接受任意配置、任意 seal 或任意实数据的生产旁路。
2. `prepare_v3` 在解析成员前验证固定 manifest `08e865ff98bd476c94153033bc192664d72cee64443184576532c0289a610dd7` 及全部 609 成员的大小/hash/类型；603 原引用只读，6 份副本共 320,921 bytes。新外层 manifest 与原 D1 verifier 根的职责明确，不能用新目录冒充 D1 原完整输入。v3 verify、quality/selection/training-binding、四组身份、R1/Q1/S0 批准均接入；原历史 pending 与新的 S0 批准分别保留。
3. 四个不可变 view 必须逐原行、Example/sidecar、split/group 与 v1/v2/v3 rank 核对。formal 为 5,938/213，smoke 为 1,583/194；有效全集为 7,419/230。`parent_selection_rank` 指 v1，`previous_selection_rank` 指 v2，当前 rank 连续。不得补选、重排、晋升 staging 或误删同 group 的其他来源；原 JSONL 字节与内存规范化表示明确区分。最终 test/ood/BFCL 只 hash，不创建内容 view，不依其答案生成测试 fixture。
4. 固定 13 个唯一例、两 engine 26 记录逐类型核对 Example、Action/messages/audit、case/profile/rank、quality revision、P/C 文本和完整 ID/attention/loss/causal 数组、EOS、右 padding 与所有 token_texts。用既有 `Sequence`、`Batch` 和 `collate_sequence` 转换；没有 `training_sequence`、`collate_selected` 或 tokenizer/renderer/encoder/decoder 调用。11 个旧例和两个新例沿各自原 producer/run/source/Q1 链保留；重新封装不冒充重测。三个 protocol fixture 不进入训练或验证 view。
5. 有限数组导出和回读绑定完整原 sequence、Batch、原行、rank、Q1 判定、producer/source epoch 和实际 CPU consumer。只接受这 13 例，明确 `REVIEW_ARRAY_ADAPTATION_ONLY`、`new_sequence_calls=0` 和 `optimization_authorized=false`。输出覆盖、部分发布、symlink/路径逃逸、重复 JSON 键、NaN/Infinity、bool/float 冒充整数、错误 consumer 或可变结果必须拒绝；默认导入不加载框架。检查从磁盘回读的每个数组，不能只比较 writer 自己的摘要。
6. 一遍计划复用已审 kernel，smoke 为 197×8+7=198，formal 为 742×8+2=743，实际更新为 0。新 CPU 模块不改旧两段 validator 或把后续四段评分方案当作本包已实现。G-DATA 当前批准成立，实际 trainer、容量、baseline/SFT 和浏览器实显仍分别为 NOT_RUN。

独立验证优先使用少量原创反例，覆盖错 revision/旧配置和审核绑定、遗漏或重复成员、原行/rank 错配、整来源排除回流、错 Example 复用、类型/EOS/shift/padding、protocol/staging/final split 越界、可变 view、输出覆盖/中断发布和错误 consumer。可用原创桩确认失败早于真实编码/框架导入，但不得靠全局放宽生产常量让实际材料通过。T1 自测不代替 R1 反例；无需机械重跑未变更的历史 HF/真实 tokenizer/原生 toy 数值组。

本轮使用现有默认 CPU 环境，新增制品 ≤1 GiB；独立实际固定消费最多一次 `prepare_v3` 和一次完整 13 例转换/导出/回读，优先在新安装 target 执行。该额度随本轮精确派发生效，派发前保持 0 次。先核对 T1 实际 sdist、wheel、从 sdist 重建 wheel 的成员、源载荷、metadata/entry points/LICENSE/RECORD 和实际构建时点；可直接使用已完整绑定的默认 wheel，一次离线 `--no-deps` 安装到 R1 新 target。默认外部 cwd 验证模块来自该 target、无源码回退，完成新入口和完整数组核验。新归档构建、新持久环境/依赖/下载、真实 tokenizer、全数据 build、框架/模型/GPU/优化/生成/API 均为 0。原创小 fixture 不计固定实际消费。

运行与本次改动有关的 CPU 测试、独立反例、ruff、契约和公开扫描；重复用例与独立新增数分开，不凑累计测试总数。每次使用新临时目录，保留实际 argv/UTC/exit/stdout/stderr、源码时点、失败及旧 seal。核对 T1 源/安装的全部实际prepare尝试、原失败、S0追加批准、各次保留记录及最多各一次成功的完整转换/导出/回读；同时绑定原命令、归档和消费者身份。原source缺失终态counter不可补造，traceback/源码推定与installed实际counter分别记录。原生工具日志中的截断不能被写成完整输出已显示。

正式输出精确 candidate 的 PASS/FAIL/BLOCKED 与 P0/P1/P2。审查提交直接以该 candidate 为 parent，只含本轮审查目录和 handoff；普通推送并原生向 S0 交付完整 SHA、tree/parents、原始失败、实物索引与 seal 后结束。普通回报省略 model/thinking。PASS 后仍需 S0 整合、最终 CI/main 验证；真实 runtime 和模型额度另行冻结。同问题第五次规则由 S0 按正式问题台账执行，不把非阻断建议扩展成无限整改。

T1中间复测按S0完整8c8aff8300bfa564db7d47be79e6c3f764360a8b原生激活，精确批准[本轮CPU复测](../approvals/P04_DATA_V3_PREPARE_RETRY_R2.json)。R1 intake需保存该批准与原失败/所有修订证据；不能将135自测或S0重试前置核验当作正式技术PASS。实际最终候选和两条新复测终态均已由 S0 完整接收；独立 R1 verdict 仍 NOT_RUN。

R1旧证据保全补充：S0证明 `94054f2922bf7d75c883bff3f3ab52c6c7f4fdea0d371bf9ea16ca05c4818b90` 核对571旧公开Git/快照、989旧scope文件和1,234现存链接；原全局pytest临时fixture的30文件路径及1链接缺失，30份内容与既有封存副本hash/大小一致并已另存。按[S0实际记录](../../reports/S0_P04_REVIEW_EVIDENCE_PREPARATION.md)和私有精确缺失/映射清单继承，不恢复成原件、不写成全部原路径仍在；旧PASS/FAIL和counter保持。首次intake保存本报告及该保全proof/精确清单，后续pytest用独占新basetemp。

本轮精确实物：T1 terminal seal `3dbad95bd7cd5309f736cc3a2dd0d0d63374f78f2f9c9aaf9eb1226c5e716017`、receipt `a1f2e37762cb71eef49d4ac1af88d5cefe631df4f8486577525cbbbd43c86fb6`；直接与 rebuilt wheel `8070c4954dfb9a60a689b76ccfe46694b35d9dc056a262381de0e26a72aef3dc`、sdist `be725d44fa290eb13072e6f360999c7b9a13edbd5e2b67aa222a0115f1a80ffe`。从私有分发路径读取原实物，intake 核对 S0 proof 与 T1 seal 的全部本轮条目、609 输入、40 原命令和两种日志 schema；旧历史跨基线公开路径按已封存 Git/快照解析。新安装及固定消费各使用独立新目录并先落真实 reservation；失败即停止该项新增实物消费，保留原失败并交具体请求，不因 CPU 无 GPU 而无限复跑。
