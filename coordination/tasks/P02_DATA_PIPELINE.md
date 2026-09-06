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

2026-09-06实际提案派发：S0核验D1原轮completed/notLoaded、干净HEAD b0d8d83750c48cd951c16b50cfa28a7898976e72后，以完整授权fd67511ef4cb7853bb75b0b106ec4692a9d36be8原生派发本范围，gpt-6-astra/max，新轮次已确认ACTIVE。仅提案，暂不推送原本地分支覆盖S0已整合的较新远端，不重复向kris发人审请求。

## P02-format-r2｜共用 v1 格式与新序列审计授权

状态：READY_FOR_REVIEW；D1已交付完整`7bada2e451d43dae4b3ed532d5efa310fc8e6a57`且原生completed/idle，R1实际派发见末段。原提案和角色比较已交付为 `6c3d330e4b28be0fbc93c273bb2576f7317c69a8`，比较实现 `ac3c99b10e46deef745b624be14acfacff2cb369`；S0核验正式handoff、68项hash、167份不变原文件及D1原生completed/idle。原A结果、失败、比较及其SHA保留。

- owner仍为D1、同一独立任务/`work/p02-data`/原worktree；gpt-6-astra/max，不创建新任务或sub-agent。
- 已验证生产输入为P02合并 `2ec17673c18ffbc817b1ff8512e53e44a11766a5`；本次协调基线为main `201e3a1f697a567f843754e465e57d8227660264`。先读取并保存本次完整授权中的AGENTS/协议/本任务/ADR-0017/格式规范；从干净6c3d330以普通merge接入本次授权提交，保留所有父提交和原提案，不reset/rebase/cherry-pick，不改写较新远端。
- 本次允许新增 `src/toolalign/model_io/`、`tests/model_io/`、`reports/data/P02_FORMAT_V1*`、`coordination/handoffs/P02-format-r2.md`，以及只含去敏身份/hash/统计的新 `data/manifests/model-io-sequences.v1.json`。原三份提案文件只读，使用新报告交接实现。
- 原11个 `src/toolalign/data/` 模块、旧tests/data/、原manifest及data-build模块清单、所有18项原产物、100来源/114决策人审包和填写副本只读。其余公共路径包括contracts/runtime/训练/执行器、configs/locks/依赖/CI/检查脚本、S0状态/ADR全部只读；必要公共申请交S0。不能替换旧LocalTokenizer默认格式、原长度表、标签或切分。

实现严格遵循 [最终v1规范](../../docs/16_MODEL_IO_FORMAT.md) 和其精确描述文件。共用入口独立接收并验证ModelInput，不伪造Example或目标值来通过validator，不导入tokenizers/Transformers/MLX/Torch。冻结schema和关联语义是实际边界，历史调用参数不能自行增加冻结规则之外的当前catalog约束。完整Action编码与prompt入口分开；训练Example另经冻结完整验证。有限原生JSON、额外键/历史关联/重复ID、合法内容保留、控制标记转义和不修改调用者输入须有实际正负例。

模块在wheel隔离安装后应自足；若复制规范为包资源或常量，必须校验与S0描述及instruction精确字节/hash一致，不能依赖源码cwd。纯序列接口使用显式renderer/encoder/EOS，或独立可选CPU适配器；不把0.22.2门禁强加0.23.2调用者，不加载模型或实现训练backend。编码P+C、核对P前缀、一个追加EOS、completion-only与next-token shift边界需可复核；异常身份不符直接失败，不静默回退。

只复用D1已有固定tokenizer环境及reference环境。本次显式允许离线tokenizer-only AutoTokenizer（local_files_only=True、trust_remote_code=False；导入前禁用Torch/TF/Flax并核对实际模块无MLX/Torch）；禁止模型类/权重/GPU/联网下载或新环境。使用与固定0.6B/1.7B一致的三个已有小来源文件与只读来源metadata，记录各revision/文件与原模板hash。对最终v1同12个原创/公开fixture重新做0.22.2与实际reference Transformers/tokenizers路径对照，逐项比较完整P/C/IDs/sequence/EOS/mask；不把旧提案或旧16例结果当作本次结果，不声称模型行为通过。

本次显式授权对原固定8,228个Example做一次新的CPU格式/序列全量审计：先核对原data-build canonical hash及实际输入文件hash，逐例保留example/source/ModelInput/Action身份、各split和原目标值，不重新转换来源、分组、筛选或截断。产物写到新的私有版本目录，禁止覆盖已存在输出。新manifest绑定格式描述/指令/源码、模型/tokenizer/模板/渲染参数/协议、原数据及各新产物hash；逐例字段和统计按docs16，含prompt/C含不含EOS/总token的P50/P90/P95/P99、raw字节/节点/深度与原P03 parser状态、1024/1536/2048上下文与256响应预算分别计数。失败和超限仍计入完整8,228分母，明确每个原因，不把成功子集偷偷用作训练集合。最终测试集仅做固定表示层审计，不运行模型评分或据此选格式/训练参数。

原P03 parse_action可用S0提供的精确只读源码副本在私有审计脚本核对（源码hash须先匹配）；不把未验收P03分支合入D1、不复制替代parser进生产、不引入由数据指定Python路径的执行接口。合法Action经转义后仍可能触及既有raw限制，如实保留原parser错误和完整分母，不放宽限制。若P03已通过并由S0发布新合并基线，再按S0明确同步消息采用，不能自行提前集成。

资源：仅CPU，复用现有环境，新增私有制品累计2GiB，不加载模型、不联网下载、无新费用。全量新序列审计只有这次格式改变所需的一遍；确定性以同一原创/允许开发小集复跑和独立逐项校核证明，不重复旧两遍数据构建。保留原输出/失败/命令；任何原始身份不匹配立即报告，继续独立可做的纯代码检查。

验收入口由实现交接给出实际命令，以下仍为PLANNED：新model_io正负例、同12例真实跨实现CPU对照、新全量序列审计、适用完整既有CPU/真实tokenizer回归、lint/冻结/公开扫描、当前实际sdist/default wheel/显式sdist重建wheel与成员字节绑定、新默认CPU隔离安装的导入/投影/编码/序列接口。默认wheel的构建来源如实记录，未做源码直接构建就写NOT_RUN。原data模块、全部产物、人审包及填写副本hash保持证据必须可复查。

完成时交精确候选SHA/父提交/范围、所有命令退出码/日志hash、旧证据保全、新manifest/统计和失败/NOT_RUN；只推送普通可快进分支并结束该轮待独立R1。此授权不批准正式格式验收、训练选集、G-DATA人审、P04/P05或真实推理；P04至少10条token/mask人工检查仍需后续完成。

2026-09-06 P02-format-r2实际派发：S0再次核验D1原生completed/idle、干净HEAD6c3d330后，按完整授权0c94ad58a78d30cd88a9ad86ac8e8d8c83b2442c原生派发本范围，gpt-6-astra/max，新轮次已确认ACTIVE。该授权内的规范/范围保持，以原精确提交为准，无需因随后S0状态更新自行merge新main。

### 已验证 P03 的同轮同步授权

P03现已在`29a5e4c6affa2b822717fd3184b25ccb756e1651`完成独立审查、最终双Python CI及main551CPU/归档/18条隔离命令验证，见[S0证据](../../reports/S0_P03_MAIN_VERIFICATION.md)。收到S0本段精确授权SHA的原生消息后，D1在当前P02-format-r2同一活动轮次于安全提交点普通merge该提交，保留当前格式实现、原提案及所有既有证据；不重启任务，不reset/rebase/cherry-pick或替换工作树。

新main只提供已验收P03与S0记录，不扩大D1文件所有权。原0c94ad5的最终格式规范/描述、原data模块及人审材料边界保持。CPU审计可以直接导入此已验证的`toolalign.tools._json.parse_action`，源码SHA-256仍为`15f67a014fc1f2a044b8a180f425ab2cde1d668939c55a96d937e4a23373211b`，与先前允许的私有副本完全相同；报告记录实际来源，不篡改旧记录。已完成的新序列审计在源码/输入/hash均相同的情况下可以沿用，不因本次merge重复8,228例或另造全量输出。最终组合CPU/包/隔离接口验证须绑定新完整候选；没有模型/GPU/P04/P06授权。此处为准备好的同步范围，实际派发单独登记。

2026-09-06实际同轮同步：S0重新核验D1原活动turn仍inProgress后，已原生发送完整授权5212b24c0ef2d5442e190ed791a9b7008d8e0724。D1确认保存授权、将当前范围内实现提交b33a55f并普通merge已验证P03，继续原格式交付；没有重启或新增任务。新全量序列审计已报告完成一遍但尚未正式交接/独立复核，不据进度消息宣布新格式验收。

## P02-format-review-r1｜独立审查准备范围

本段只准备范围，尚未派发。S0须先收到D1已提交的最终完整candidate与handoff并核对范围/证据，同时确认R1原生空闲；随后原生消息给出精确candidate和完整authorization_commit。R1在自己的隔离worktree从该候选新建`review/p02-format-r1`，gpt-6-astra/max，不接入随后无关main/P01变化。只新增`reports/review/P02-format/`和`coordination/handoffs/P02-format-review-r1.md`；全部被审实现/测试/提案/manifest/规范/原R1文件以及其他worktree只读。不能先修候选再给自身修复签通过。

审完整新model_io实现、可选CPU适配器、新tests/审计与包检查器、派生manifest及其真实结果，不仅审最终报告。绑定ADR-0017、完整描述/指令、官方模板与固定0.6B/1.7B tokenizer来源；三份原提案证据和旧P02技术PASS按原SHA保留，不把旧格式证据写成新格式验收。

用独立原创正负例核对standalone ModelInput的冻结结构/原生有限JSON与历史关联，拒绝额外标签或未完成调用但保留合法历史工具和值；禁止伪造expected_action、word blacklist或静默加强当前catalog约束。核对完整Action的四种kind、call_id/参数、无变更输入、孤立副本、异常文本边界。实际呈现消息控制段与可逆JSON内容，验证tools/native tool_calls未送官方模板、system/assistant角色和tool_response分组、历史无kind不猜造、控制标记与非ASCII/转义键值安全往返。期望值/评分/split元数据不得进入prompt，合法content中的同名字词应保持。

序列独立检查P与encode(P+C)的前缀、精确C解码、一个EOS、completion-only/causal shift和右侧padding；拒绝错误来源、边界变化或偷偷截断。区分应用提供的可信callbacks声明与可选适配器实际核验的来源；不要把声明的template hash当作已读取的真实模板证明。核对两种engine的实际本地加载状态和影响它们的全部文件/参数；以必要的来源篡改、附加tokenizer文件/override及正常邻例检查，避免仅核对三份文件名便断言已加载状态相同。导入纯模块和默认wheel不得加载tokenizer或模型，真正tokenizer操作只在允许的CPU验证环境中进行。

独立检查同12例最终v1的原始文本、完整IDs/sequence/EOS/mask与两条实际渲染/编码路径。对新完整8,228行派生审计，先核对原Example/18制品和source/group/split/目标值均未变，再绑定每行身份、格式/源码/模板/配置和输出；独立复算分母、上下文与响应两个预算及其交集/分层统计。因为本次改变所有训练序列，允许一遍有界CPU的独立全量逐行序列/长度核对，使用独立reference渲染/编码判断，不重复旧来源转换/分组/两遍构建。错误和超限保留在完整分母，不偷换为可训练子集；只做固定表示核验，不运行最终测试模型评分或据此调参。原P03 raw字节/复杂度限制与错误类别保持，转换成功不自动授予registry执行权。

运行未修改的适用旧CPU/真实tokenizer/原独立检查和必要新反例，按实际计数区分独立场景、同场景安装重复和命令数。核对真实新sdist/default wheel/显式重建wheel的当前Git载荷及默认安装的自足包资源/投影/编码/序列接口；明确源码直接wheel未执行时为NOT_RUN。旧P02数据模块/manifest、100来源114决策人审包和填写副本只读；其身份核对不代签kris语义结论。原代码/候选CI不代替本轮独立审查。

仅CPU，新增私有环境/证据累计2GiB。优先复用自己已有适用固定CPU环境；若需要额外reference环境，只用本机缓存离线安装与交接清单/现有锁核对的必要CPU tokenizer依赖并保存实际版本/hash，不修改旧环境身份，不下载权重或新依赖。reference允许tokenizer-only Transformers5.16.1/tokenizers0.23.2/Jinja3.1.6，导入前禁用Torch/TF/Flax并启用离线限制、实际断言未加载模型模块。禁止MLX/Torch/模型类/权重/GPU/训练/P04/P05/P06/BFCL及费用；pure callbacks不应强制0.22.2版本。

输出精确候选的PASS/FAIL/BLOCKED、P0/P1/P2、规范与源/安装路径逐项证据、命令/退出码/hash、原失败和NOT_RUN。提交新的独立review SHA后结束该轮等待S0。格式技术PASS仍不等于G-DATA、人审、训练选集或模型质量通过，不能自行改ADR/状态或合并main。

2026-09-06实际独立审查派发：S0收到并核对D1最终7bada2e451d43dae4b3ed532d5efa310fc8e6a57及正式handoff，713项checksum和217个原公共文件字节匹配。重新确认R1上一轮completed/idle后，按完整授权1de90781e42a3693b112aafcf585a905bc052d63原生派发精确7bada的新格式独立审查，gpt-6-astra/max，已确认新轮ACTIVE。D1随后原生completed/idle核验完成；本轮仅CPU新格式审查，不授权P04或替代kris语义判断。

## P02-format-fix-r3｜参考 tokenizer 的已核验字节绑定

状态：CHANGES_REQUESTED；D1已按完整c6c02a5实际原生派发并核验新轮ACTIVE，见末段。R1继续冻结完整候选`7bada2e451d43dae4b3ed532d5efa310fc8e6a57`，正式整包报告尚未提交。S0已读取并封存稳定反例及未提交探针的精确字节：同尺寸替换原目录的tokenizer.json，在校验后、真实HF加载前交换`!`与`?`的vocab ID，最终来源文件恢复原hash，声明身份完全相同但`encode("!")`从`[0]`变成`[30]`。参考路径exit1，native从已核验buffer构造的对照exit0。探针只控制私有来源副本的文件打开时序，未替换loader方法、返回值或identity；这证明加载状态与来源声明脱节，不是一般同用户OS攻击隔离保证。S0封存证明SHA-256为`d33051b56aea3fc8588c47aa26e713b20b0783aca0d4f74f0e631f1a1d836510`，不把未提交源快照称为正式R1交接。

- owner为D1，同一原生独立任务/隔离worktree/`work/p02-data`，gpt-6-astra/max。先核验干净完整7bada2e，读取并私有保存原生消息给出的完整authorization_commit中的AGENTS/协议/本段；从原候选继续，不自行merge随后main/P01，不reset/rebase/cherry-pick。原R1正式提交到达后，只有收到S0精确SHA同步消息才普通merge原review，全部原FAIL与父提交保持。
- 只允许修改`src/toolalign/model_io/offline.py`、`tests/model_io/test_offline.py`，必要时新增`tests/model_io/test_snapshot.py`；新增`reports/data/P02_FORMAT_FIX_R3*`及`coordination/handoffs/P02-format-fix-r3.md`。其他format/sequence/资源/fixtures/旧测试、原三个提案、原审计报告与manifest、data模块/18产物、人审材料与填写副本、全部P01/P03/既有R1、公共规范/锁/依赖/配置/S0状态只读。需要超出范围先提交具体申请，继续可独立工作。
- 修复目标是让真实HF tokenizer使用本次已核验的完整字节快照，或等价绑定其全部实际加载状态；可从buffer或独立受控快照构造，须说明额外文件/override的处理。不能用增加若干原路径重查次数、关闭reference功能、放宽身份检查或伪装native实现来让反例通过。维持普通固定来源上的官方模板、token值、渲染参数、EOS、模型revision与真实包版本。

先在精确7bada上以S0提供的只读探针副本自行复现before：真实参考路径失败、native对照通过，保存原始命令/退出码/loghash。再在新实现上复跑相同探针，证明声明相同就实际状态相同，或明确fail closed；主回归不得mock loader方法、库返回值、identity或期望hash。补充与改动相关的同尺寸/不同尺寸来源变化、附加文件/实际加载状态、正常来源、异常与临时资源清理检查；探针只操作本次新私有副本，不修改R1或旧来源目录。

同12个原fixture须在两个真实CPU engine重新检查P/C/完整IDs/sequence/EOS/mask，并精确比较原最终v1输出；双模型身份行不冒充新增独立场景。旧8,228行native审计和本轮R1独立reference全量核验保留其原源码/输入/hash/时间，不改写成修复后运行。新报告给出加载代码变化与不变格式/算法/普通fixture输出的映射；没有具体表示变化，不重复旧来源构建或自动重跑8,228行。若实现确实改变正常表示，立即提交差异给S0决定范围，不自行选集/截断/更新manifest。

在最终完整修复候选运行适用全部旧CPU/真实tokenizer检查、新反例、lint/冻结/公开扫描，以及当前实际sdist/default wheel/显式sdist重建wheel、成员源码hash和默认隔离安装接口。安装环境仍不得加载可选tokenizer/模型依赖；真实tokenizer验证在已允许的CPU环境单列。命令数、不同场景、安装重复分开；源码直接wheel若未运行记NOT_RUN。所有旧失败和自己开发失败保留，不按新结果覆盖原报告。交接中记录精确候选/父提交/授权范围、各结果和来源hash、原数据/人审身份保持及剩余项。

资源限纯CPU，新增私有制品累计2GiB，复用D1已有native/reference环境，不新建环境、不联网下载。使用真实tokenizer-only Transformers5.16.1/tokenizers0.23.2/Jinja3.1.6，导入前设置离线和禁用Torch/TF/Flax，实际断言无模型模块；禁止模型/GPU/费用/上传/P04及正式训练。完成后普通推送精确候选并结束该轮，等待独立R1复审。S0的768CPU临时组合预检与候选CI通过不关闭本缺陷；新格式、G-DATA、训练绑定均未验收。

2026-09-06实际修复派发：S0再次核验D1上一轮completed/idle和干净7bada2e后，按完整授权`c6c02a5af084afe92c6e9f05d9d1c51392e805d0`发送P02-format-fix-r3，显式gpt-6-astra/max，已核验原生新轮ACTIVE。R1继续原7bada完整审查，不混入D1修复；T1/E1无新派发。Draft PR8说明已更新为待修复/独立复审，原CI与临时组合结果保持，未合并。

## P02-format-review-r2｜修复后的独立复审准备

状态：IN_PROGRESS；S0已按完整41233633ac9aeaf72e66b280908bc0156149c0f2原生派发并核验新轮ACTIVE，见末段实际记录。待审精确candidate为`8c439f683b9d6b04919ff1f7184d8924ccf82f9f`，已由D1正式交接/普通推送，包含修复b4dc1cf和以6c82d29普通merge保留的公开原review2942e568。S0已核对原报告全部发现、完整修复范围、真实before/after、最终验证及封存；原7bada FAIL/P2=1保持。R1原轮completed/idle及干净公开2942已核验，完整authorization_commit和该精确candidate已由原生消息送达。R1在自己的隔离worktree从该候选建立`review/p02-format-r2`，gpt-6-astra/max；不自行接随后main/P01，不重启仍活跃的旧轮次。

只新增`reports/review/P02-format-r2/`及`coordination/handoffs/P02-format-review-r2.md`。全部候选实现/测试/描述/提案/旧数据及manifest、人审材料、原review/失败证据、公共状态/ADR/依赖/配置和其他worktree只读；不能自行修实现后签通过。复核D1实际差异是否仅属c6c02a5及后续S0精确同步范围，原review以普通merge保留，原P01/P03和data材料没有夹带改动。

独立复审原完整报告所有发现，重点证明真实HF加载确实消费已核验缓冲或等价完整状态。核对可变原目录与实际消费目录/文件/参数的关系、未绑定附加文件/override的处理、模板/EOS/包/revision身份、正常构造后实际render/encode/decode仍自足，以及临时资源成功/异常清理。安全边界是绑定普通来源目录更新，不扩张成任意同用户OS攻击隔离。保持真实HF功能，不接受多次路径重查、关闭reference、放松声明或native假扮reference。

先核对D1在原精确7bada的真实before日志、原R1失败探针及source/wheel证据；在新精确candidate的源路径和实际默认wheel安装路径独立复跑未改原同尺寸探针及native对照。主反例不能mock loader方法、返回值、identity或期望hash；证明原F1关闭且正常固定输入没有变化。补充与实际改动相关的不同尺寸/静态来源/额外文件/异常邻例，报告独立场景与安装重复，不把同一反例多跑算作多项缺陷。

同12个原fixture通过两条真实CPU路径重新核对完整P/C/IDs/sequence/EOS/mask/shift，明确两个模型身份共享来源，保持四种Action和历史角色/转义/原parser行为。旧8,228行native测量及原R1一次reference全量核验保持其原commit/hash/环境/时间；新的代码绑定映射应承认offline.py变化，不能把旧全量manifest悄悄换成新源码或伪称本次重跑。正常表示无差异时读原全量证据、逐项核对保全和小集即可，不重复来源两遍构建或全量8,228。若发现实际表示变化，保留差异并报告S0，由S0决定后续范围。

运行适用的未改旧CPU/真实tokenizer和原R1独立结构/统计检查、新复审反例、lint/冻结/公开扫描；精确候选的新sdist/default wheel/显式重建wheel、成员源码hash及默认安装自足接口须有实际证据。纯/default安装不加载可选tokenizer/模型；安装版真实HF反例另用允许的CPU环境并核对实际ToolAlign导入路径。区分独立场景、安装重复和命令数，保留自己的失败尝试；源码直接wheel未运行记NOT_RUN。

仅CPU，新增私有制品累计2GiB，复用R1已有native/reference环境，不新建环境、不联网下载。原固定Transformers5.16.1/tokenizers0.23.2/Jinja3.1.6与native0.22.2环境分别记录，运行前禁用Torch/TF/Flax并设置离线，实际核对无模型模块。禁止模型/GPU/训练/评分/费用/上传/P04；不代签kris人审。交精确candidate与原独立review commit、PASS/FAIL/BLOCKED及P0/P1/P2、完整命令/退出码/hash和历史证据映射。提交新的独立review后结束该轮；PASS仍需S0最终CI/普通合并/main验证，新格式通过不等于G-DATA或模型质量通过。

### 原R1未公开附件的去敏发布映射

S0在发布前读取到R1本地原review `f7086413a9fedd9e2a473ac6d2869efff74ddad5` 的公开evidence.json中，一条安装命令仍带实际系统临时路径；远端尚无本轮review分支。该遗漏只属于R1发布附件，不增加7bada候选的缺陷数。F1正式等级保持P2=1、整包FAIL；原候选、8个探针、具名Ruff例外及原始命令/日志/结果只读。

收到S0原生消息给出的本段完整授权SHA后，R1在同一活动轮次完成公开角色占位符映射，扫描12份新增公开文件和公共历史载荷，保留全部原始私有字节与原review提交。**不得push f708641或其任何后代**，因为只修最新tree仍会在公开历史留下原路径。允许在自己的原worktree建立新的`review/p02-format-r1-public`，以原精确被审candidate `7bada2e451d43dae4b3ed532d5efa310fc8e6a57`为唯一父提交，提交同一份已核验审查的去敏发布tree；原`review/p02-format-r1`及其私有修正历史保留，不reset/rebase/amend/cherry-pick或force push任何分支。

新公开tree相对原review只允许更新`reports/review/P02-format/evidence.json`中的路径占位符/发布映射及因此变化的公开文件hash、`reports/review/P02-format/README.md`和`coordination/handoffs/P02-format-review-r1.md`中的去敏来源说明。原F1结论/等级、候选、实际测试数字和所有已执行探针字节保持；不重跑或改写原测量。README/交接明确“原本地审查SHA → 去敏公开review SHA不同，私有原记录未改”；最终公开SHA可由原生handoff提供以避免自引用。独立核对新tree的235份候选文件及9份探针/配置与原提交相同，重新运行适用lint、公开扫描和diff检查即可。

此项是未公开附件的去敏发布映射，不能伪称保留相同SHA。S0核验新公开commit的父关系、受保护字节、去敏差异与原私有证据后，才推送该新分支并把其精确SHA授权给D1普通merge；原含路径commit只留本地，不进入D1或main的公开祖先。后续独立复审绑定这个已核验公开review及原候选；旧FAIL与完整原始证据仍保留。

### D1同轮接入已核验的正式原审查

S0已完整读取R1正式报告、交接、8个探针及Ruff配置，并独立核对12个公开文件、原始日志/结果/安装流/归档/源码等839项文件hash和235份候选字节。公开review为`2942e568eae91d0292ad9691af133bbd8c33dd02`，唯一父为原7bada；相对本地原f708仅三份发布材料有去敏映射差异，9份探针/配置保持，原f708不在公开祖先。S0已普通推送并读回`review/p02-format-r1-public`为相同SHA，原含路径分支未推送。S0证明SHA-256为`5ddfdd75918be89160cc3e3cc2a680ad4ebba9cb94be3ae0b0932393a171450d`。正式结论FAIL、P0=0/P1=0/P2=1；原664 pytest与新增60独立检查通过，一次独立reference全量8,228行及分层统计相同，但F1未在原候选关闭。

收到S0本段完整授权SHA的原生消息后，D1在当前P02-format-fix-r3同一轮于安全提交点普通merge**精确公开2942e568**，保留已提交b4dc1cf及本轮全部修复/失败。禁止merge本地`review/p02-format-r1`、f708或其后代；不接无关main/P01，不改12份原公开review文件，不reset/rebase/cherry-pick或force push。该同步只增加已核验原审查历史，不扩大生产修复所有权。

F1按原P2等级关闭，不另造P1或把源/安装重复记为两个问题。新最终候选须绑定合并后的完整SHA、保持原报告/探针及数据/人审身份，并实际运行新增原R1的60项结构/统计检查和适用完整CPU回归。原回归启动器必须有multiprocessing主入口保护；真实native环境的两项HF专属cleanup跳过与reference中实际通过分开登记，不写成单次全套0skip。原公开full-audit/evidence脚本固定7bada与历史源码，只读其已核验结果，不修改其常量或因预期旧身份不匹配重复全量审计。

对最终默认wheel再用真实允许的HF/native环境验证原同尺寸反例，逐模块确认ToolAlign来自实际安装target；它与无可选依赖的纯默认接口检查分开。保持未改原探针、真实loader和完整原始before/after。若合并只新增原审查且新包成员字节不变，可明确列出相同成员/来源与原已执行制品的关系；最终报告仍须准确说明实际构建/安装对应的完整SHA，不捏造新运行。其余c6c02a5的两engine12fixture、全量历史映射、CPU/2GiB/无新环境与模型边界保持。完成后交新的正式P02-format-fix-r3候选/handoff并结束该轮，等待独立复审；当前复审仅准备，未派发。

2026-09-06实际同轮同步：S0按完整授权6272ad512b947b9cf14c5f7201b7807f7f188e13原生发送精确公开review2942e568并收到D1确认，D1沿原活动轮次准备安全提交后普通merge，未重启或新增任务。R1原轮随后实际completed/idle已核验，仍未派发复审。最终原completion与去敏completion、42条原验证及发布日志、新12个可达历史blob已由S0补核；附加证明SHA-256为773eb35c36c2e1d65fac041af882111d856f96312082b9119a64bafd8ee38dd9，原839项证明保持。


2026-09-06修复交接核验：D1最终8c439f6、三份公开证据和completion已正式收到，S0范围证明e3e71a50486d12f4b0b11a3b3a148b1a24ebbcfeb0b12f4043692e0671ce6e3b及封存附证5212c4c81a4a82909e6cd261ddd1e81db05308d77969ea49f91ccc0ba0a0ca31均为实际检查结果。修复只有一个生产文件和一个新测试，原234候选文件与12份公开R1材料保持，f708不在公开历史；最终8c只在已测6c82上更新三份本轮证据。39组本轮原始命令和542私有制品封存保持，CI34021506781两个Python jobs所有步骤通过。R1复审仍按上段完整独立范围执行，不因D1自测或S0证据核对直接签PASS；原同名test_independent检查可按已有两组分开调用，保留各组实际分母，勿改旧测试/全局规则。


2026-09-06实际复审派发：D1原轮completed/idle已确认；S0再次核验R1原轮completed/idle和干净2942后，按完整授权41233633ac9aeaf72e66b280908bc0156149c0f2原生发送精确8c439f683b9d6b04919ff1f7184d8924ccf82f9f的P02-format-review-r2，显式gpt-6-astra/max，已核验原生新轮ACTIVE。分发词与真实任务映射仅私有保存；原准备范围全部保持，不接随后main/P01、不修改旧原探针/失败、不新建环境或重跑无差异的全量。PR8继续Draft，等待正式独立结论与S0最终集成。


## 新格式复审接受与最终CI跟进

R1已正式交接b9f7567d7c1066eeb0bff7c47033bb2771eb9594，对精确8c439f6 PASS，P0/P1/P2均0，原F1关闭及旧FAIL保持；S0范围/证据/最终封存与原生completed/idle核验通过。原SHA已发布并普通整合当前main为2b11b7f。格式代码ACCEPTED，最终CI34024093376的Python3.14旧P03截止时间测试失败，PR8保持Draft、main尚未验收。由[E1限域CPU跟进](P03_CI_DEADLINE.md)修正测试时序假设并独立复核；D1保持空闲，无新格式或数据改动。原人审/训练绑定门槛保持，见[S0记录](../../reports/S0_P02_FORMAT_CI_FOLLOWUP.md)。
