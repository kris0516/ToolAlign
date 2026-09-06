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

状态：IN_PROGRESS；S0已按下述完整授权实际派发并核验新轮次ACTIVE。原提案和角色比较已交付为 `6c3d330e4b28be0fbc93c273bb2576f7317c69a8`，比较实现 `ac3c99b10e46deef745b624be14acfacff2cb369`；S0核验正式handoff、68项hash、167份不变原文件及D1原生completed/idle。原A结果、失败、比较及其SHA保留。

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
