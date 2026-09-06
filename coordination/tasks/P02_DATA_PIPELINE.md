# P02｜数据规范化、许可与分组隔离

状态：MERGED；完整候选`b0d8d83750c48cd951c16b50cfa28a7898976e72`获R1技术PASS（审查`8e4fdbd7374130c77262a57e55049f9cef4bf651`），PR5合并为`2ec17673c18ffbc817b1ff8512e53e44a11766a5`，最终CI及main技术验证通过，见[集成证据](../../reports/S0_P02_MAIN_VERIFICATION.md)。kris真实语义审查请求已发，整包/G-DATA仍待审及训练配置绑定，不能标VERIFIED。原候选`46f546504f73588caa2e71aac316c3c312306df6`保留。S0于2026-09-06首次授权本任务并核对原生独立对话、code_base与工作分支。P00已在`cd091e3a53986b59b170baf5b746644f369135d1`合并并验证；本包原code_base为随后仅更新协调/证据文档的`ebcaf586f8e65f5306259f6b134e1c5cce30cf48`。

本文件所在的 S0 派发提交是 authorization_commit，由原生派发消息给出完整 SHA。Worker 在切换 code_base 前用 `git show <authorization_commit>:<本任务路径>` 读取并保存私有副本；公共任务文件只由 S0 更新。

- 模型：`gpt-6-astra`；推理：`max`（最高；按用户最新目标，旧 xhigh 配置废止）。只使用独立 Codex 对话，禁止 sub-agent、嵌套代理或自行创建新任务。
- 契约：`plan-v0.1` / `coordination.v1` / `toolalign.contracts.v1`；精确字节绑定 code_base 的 `contracts.v1.lock.json`。
- 公共所有权：contracts、runtime、configs、pyproject、uv.lock、CI/检查脚本、AGENTS/README、BOARD/PROJECT_STATUS/DECISIONS 均只读。依赖/契约申请提交 S0 后继续独立可做工作。
- 真实任务 ID 与 cwd 仅写本机 `.toolalign-local/task-identity.json`。新对话先通过原生 set_thread_title 设置自身标题，再核对 worktree/branch/base；不操作其他 worktree。
- 公开内容仅提交原创代码、小 fixtures、允许公开的元数据/统计及去敏报告。原始数据、权重、日志、模型制品和具体本机路径只留私有目录。
- 交付须为已提交精确 SHA + handoff + 命令/退出码/原始日志 hash + 失败项/NOT_RUN。自测后交独立 R1，只有 S0 合并 main。

## 领取与输入

- owner：D1。
- code_base：`ebcaf586f8e65f5306259f6b134e1c5cce30cf48`。
- branch：`work/p02-data`；App 独立 worktree，实际私有路径由 S0 核验。
- 输入：冻结 example/tool.v1 和参数 schema 子集；`docs/02_DATA_GOVERNANCE.md`、`docs/12_CONTRACTS_V1.md`、来源登记与 `configs/protocol.v1.json`。
- 允许修改：`src/toolalign/data/`、`tests/data/`、`data/manifests/`、`reports/data/`、`coordination/handoffs/P02-r1.md`。

## 目标与输出

以 `Team-ACE/ToolACE` 为主完成可复现的来源获取、许可/revision/hash 记录、规范化、分组去重与 split、token 长度和质量审计。xLAM 仅为可选，不接受未授权 gated 条款。核对当前官方数据仓库内容和许可证，不能把规划文档的来源声明当成本次实证。

先读取小批真实格式再实现转换；每个受监督 assistant 决策产生一个合法输入前缀和 expected_action，原记录多轮保持相同 group。保留 source_record_hash → normalized_hash → group → split → augmentation_parent 追溯；时间字段不影响 ID。同输入、同参数重复重建必须一致。

先分组切分，再增强；group 覆盖来源记录、tool/schema 模板、业务任务模板与可识别语义近重复。train/validation/test 目标 80/10/10，隔离优先于比例；OOD 工具/schema 留组并单列。同组跨 split、改写跨 split、目标答案进入模型输入都必须被检测。最终集与 BFCL 不进入训练、挖负例或选模型。

严格使用 P00 验证器。超出闭合有界工具 schema 子集、格式不明、缺少真值或副作用分类不明的样本隔离并计数；不得悄悄改宽松 schema、补造答案或将生产写操作标成只读。兼容率过低时向 S0 提交代表样本和分母，由 S0 决策适配规则。

报告原始/过滤/最终数量、每项排除原因、工具/类别/语言分布、完全/近重复、split 交集、来源许可、P50/P90/P95/P99 token 长度与 prompt/schema/completion 占比。分桶或排除长样本，禁止损坏关键 schema/最终回答。只下载官方 tokenizer 的必要文件，记录 revision/template/non-thinking；不加载模型权重。

## 资源与验收

仅 CPU；首轮数据/tokenizer/探索环境总磁盘规划上限 5GiB。公共依赖由 S0 集中修改，私有探索环境只写本 worktree `.toolalign-local/`，记录精确包版本。原始/处理数据只存 gitignored 目录，公开仅下载代码、许可元数据、统计和原创小 fixtures。

已存在回归入口：`uv sync --locked --python 3.14`、`uv run --locked pytest -q`、`uv run --locked ruff check .`、`uv run --locked python scripts/check_contract_freeze.py`、`uv run --locked python scripts/check_public_content.py`。

以下为 **PLANNED / NOT_RUN**，由本包实现；完成时在 handoff 提供真实命令和参数：

- `uv run --locked pytest -q tests/data/`：同输入重建、group/split/OOD 隔离、改写继承、长样本处理、恶意 schema/解析、许可与排除计数、模型输入投影正负例通过。
- `python -m toolalign.data --help`：提供可复现导入/审计入口。
- `python -m toolalign.data <子命令> --config <私有配置路径>`：实施前记录具体参数、来源 revision、预算、预期输出；至少两次重建比较产物/分组/split hash，不能用人工复制同一文件冒充重建。

## 人工检查与交接

G-DATA 必须有 kris 的真实质量抽查。先准备可查看的分层样本包、来源索引、review 表和问题分类，再向 S0 报告等待人工；模型抽查不能记为 kris 通过。冻结的偏好抽检规则用于未来 P05，不把其误标结论虚构为已完成。人工审查未完成时可交 pipeline 的代码/自动证据给独立 R1，但 P02 与 G-DATA 不能宣称 VERIFIED。

交接：`coordination/handoffs/P02-r1.md`。附 command/exit/log hash、来源与转换许可、实际 group/split 计数、错误/排除清单、人工包位置和未完成项；不得提交原始数据/私有路径。长度或 schema 兼容问题提交 S0，继续可独立的审计，不能自行降低数据门。

2026-09-06 公共基线更新：S0 已授权采用已验证生产合并 `18fc8475476f6becf684ba817480caeb96a7cfb9` 及协调状态 `a6c8dd3c78b3674a242b4faacbb175f7b7c98303`。保留原 code_base/authorization 的历史记录，实际工作分支以非强制 merge 接入；新模型规则 gpt-6-astra/max 优先于首派任务副本。

2026-09-06 第二次公共基线更新：S0-SHARED-02 已独立审查/CI/合并/main验证，生产base `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`。收到S0原生同步消息后，保留46f5465及两次真实构建/有效人审包，非强制merge本报告所在协调提交（完整SHA由消息给出）。仅CPU复核新base测试、固定真实tokenizer、包构建/隔离安装与既有数据manifest/人审输入hash；未改变数据代码/参数时不无理由全量重建，不填写人工判定。允许新增`coordination/handoffs/P02-base-r2.md`记录新完整候选、merge关系与实际结果，原P02-r1保留。

## 完整候选的独立技术审查授权

R1以S0下一条原生消息的精确授权提交为准，在自己的隔离worktree新建`review/p02-r1`，审完整候选`b0d8d83750c48cd951c16b50cfa28a7898976e72`；生产base37c00de、同步授权f2a271b、D1受测merge9bbd7d7。S0已核对新增范围、正式P02-base-r2及旧数据实现/任务包字节不变；D1自测298CPU与真实包/隔离安装通过，不替代R1。

只允许R1新增`coordination/handoffs/P02-review-r1.md`与`reports/review/P02/`。冻结契约、政策、候选实现、公共配置/状态/ADR及D1工作区全部只读，不先修被审实现再签通过。复核完整数据转换/工具与历史关联/prefix泄漏/分组及schema规范化隔离/tokenizer和长度/18产物与manifest一致/来源与许可/最终有效人审包；用独立原创反例及真实对应核查补充生产脚本，不能仅复用D1 parser作独立证明。

仅CPU，新增私有环境和证据预算2GiB；允许在自己的私有环境按`reports/data/tokenizer-audit-environment.txt`固定清单安装CPU tokenizer依赖，原D1制品只读，绝不加载模型/GPU。两遍稳定数据已真实构建，不无理由重跑两遍；有具体疑点可做必要重现。100来源/114决策人审包需保持实际身份hash、内容转义与未填写状态，不能签kris判断；P02技术PASS仍不代表G-DATA通过。输出精确候选、PASS/FAIL/BLOCKED、P0/P1/P2、实际命令/退出码/完整loghash、独立review commit与NOT_RUN，提交后停止等待S0。

## P02至P04输出格式的CPU方案准备授权

P02代码已在2ec1767合并并完成main技术验证；G-DATA仍待kris实际人审和训练配置绑定。S0用公开契约fixture证明当前Qwen原生tool-call completion无法由冻结P03的Action JSON raw parser直接解析，且相同content的final/clarify/refuse序列相同。见[衔接证据](../../reports/S0_P04_READINESS.md)。这是正式训练前尚未定义的跨包格式绑定，不推翻原数据语义审查或伪称模型已生成失败。

收到S0原生消息的完整授权SHA后，D1可在原隔离worktree/分支进行**报告和私有CPU原型**：以保留四种Action及call_id/arguments/content的显式JSON输出为优先方案，给出可供S0定稿的版本名、prompt/history/tool-schema编码、训练与推理共用投影入口以及兼容影响。只新增`reports/data/P02_OUTPUT_FORMAT_PROPOSAL.md`、必要原创公开小探针`reports/data/P02_OUTPUT_FORMAT_PROBE.py`和`coordination/handoffs/P02-format-proposal-r1.md`；当前不修改src/tests/manifest/依赖/冻结契约，不重建或覆盖原18产物及人审包/填写副本。无需合并新main或共享代码，本轮读取授权和已合并代码的精确blob即可。

必须基于实际固定Qwen模板及P03 parser做小型CPU可复现证明：四种action和非ASCII/换行/引号/嵌套参数往返；多工具call_id和observation关联；多轮assistant历史、没有kind的历史Message不能猜造kind；工具schema仅来自ModelInput，expected_action/oracle不得进入prompt。检查原模板tools参数会插入原生tool_call指令、assistant中的字面think标记/控制token会触发模板处理等边界，并提出可逆编码和不相互冲突的prompt设计。优先保持官方chat_template原字节与non-thinking，只在显式版本化输入投影/输出序列中改变格式，禁止把生成后修复包装当raw格式通过。

在已有固定本地tokenizer环境用公开/原创fixtures测prefix稳定、一个追加EOS、completion-only边界与序列hash。原0.22.2和P01 0.23.2的旧16例对齐已审过，不重复旧比较；新格式应明确后续需要的新跨实现对照、全量长度/序列manifest更新以及语义数据/人审hash能否保持。这里只准备新格式方案，不擅自切默认训练格式或截断/筛选数据，不根据测试集模型得分选择方案。

gpt-6-astra/max，纯CPU，无模型/GPU/下载/费用，新增私有制品2GiB，复用现有环境。实际命令、退出码、源码/模板/样例/loghash、失败和限制写入报告，形成精确提案提交后结束该轮等待S0正式ADR/实现授权。该CPU准备不授权P04训练，也不替kris填写人审。
