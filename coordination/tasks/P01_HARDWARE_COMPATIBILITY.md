# P01｜Mac 校准与 SFT/DPO 兼容性

状态：READY_FOR_REVIEW（修复候选ac8095f）；T1已交付完整`ac8095faa58a98e143a8dc4d63042093e426feb0`并核验原生空闲，原R1对59b3802的FAIL（P1=2/P2=1、审查ac6bdf7）完整保留。修复自测和双Python CI通过，尚未独立复审。原候选`f97bb0de346c220871962a5689014a379fe19c83`及全部历史证据保留。S0于2026-09-06首次授权本任务并核对原生独立对话、code_base与工作分支。P00已在`cd091e3a53986b59b170baf5b746644f369135d1`合并并验证；本包原code_base为随后仅更新协调/证据文档的`ebcaf586f8e65f5306259f6b134e1c5cce30cf48`。

本文件所在的 S0 派发提交是 authorization_commit，由原生派发消息给出完整 SHA。Worker 在切换 code_base 前用 `git show <authorization_commit>:<本任务路径>` 读取并保存私有副本；公共任务文件只由 S0 更新。

- 模型：`gpt-6-astra`；推理：`max`（最高；按用户最新目标，旧 xhigh 配置废止）。只使用独立 Codex 对话，禁止 sub-agent、嵌套代理或自行创建新任务。
- 契约：`plan-v0.1` / `coordination.v1` / `toolalign.contracts.v1`；精确字节绑定 code_base 的 `contracts.v1.lock.json`。
- 公共所有权：contracts、runtime、configs、pyproject、uv.lock、CI/检查脚本、AGENTS/README、BOARD/PROJECT_STATUS/DECISIONS 均只读。依赖/契约申请提交 S0 后继续独立可做工作。
- 真实任务 ID 与 cwd 仅写本机 `.toolalign-local/task-identity.json`。新对话先通过原生 set_thread_title 设置自身标题，再核对 worktree/branch/base；不操作其他 worktree。
- 公开内容仅提交原创代码、小 fixtures、允许公开的元数据/统计及去敏报告。原始数据、权重、日志、模型制品和具体本机路径只留私有目录。
- 交付须为已提交精确 SHA + handoff + 命令/退出码/原始日志 hash + 失败项/NOT_RUN。自测后交独立 R1，只有 S0 合并 main。

## 领取与输入

- owner：T1。
- code_base：`ebcaf586f8e65f5306259f6b134e1c5cce30cf48`。
- branch：`work/p01-compatibility`；App 独立 worktree，实际私有路径由 S0 核验。
- 输入：已验收 P00 契约/共享 GPULease；`docs/03_TRAINING_SPEC.md`、`docs/05_APPLE_SILICON.md`、`docs/12_CONTRACTS_V1.md`、`coordination/RESOURCE_LOCK.md`。
- 允许修改：`src/toolalign/training/compatibility/`、`tests/training/compatibility/`、`reports/hardware/`、`coordination/handoffs/P01-r1.md`。

## 目标与输出

核实实际芯片、GPU 核数、内存、macOS、Python、Metal 和候选库版本。输出机器去敏清单、源码/API 兼容结论、可复现 CPU 数学检查、0.6B 冒烟、1.7B 校准与资源预算报告。

0.6B 先验证 32 条原创训练 smoke 样本的 token/mask、加载、微训练与 adapter 保存重载；不得把 P02 最终测试集用于此处。SFT completion-only、next-token shift、padding/EOS 和多轮边界须检查。MLX 与独立 PyTorch CPU 小张量 CE/DPO loss 及梯度对照，明确容差。policy=reference 的 ln(2)、reference/hash 冻结、只有声明 adapter 更新、跨库 target module/scaling/template/前向一致必须有证据。禁用全部 adapter 不等同于 SFT reference。

检查首选 MLX-LM SFT 和 mlx-tune DPO 的真实源码与固定版本；备选最多一次 mlx-lm-lora，不自建完整训练框架。正式依赖由 S0 集中锁定；探索环境只能在本 worktree 私有 venv，保存精确安装清单和来源。

1.7B 分长度 bucket 校准，先暖机，目标 100 个可测微步；预算到限则记录实际数量和外推限制。分别记录 SFT、reference 预计算、DPO、生成和完整任务推理可实际完成的测量；完整 P03 harness 未合并的测项标 NOT_RUN 并留后续入口，不伪造。本包不运行全量正式 SFT/DPO，不自行进入 P04/P05。

每次模型 smoke 使用冻结 run.v1 manifest；实际文件 hash、token/微步/optimizer step、计时同步、暖机与 checkpoint I/O 分开记录。人工小张量检查可用独立测试日志，不假装模型训练 manifest。

## 资源与停止条件

任何模型导入/加载到驻留结束均持同一仓库 GPULease；没有取得租约不能执行模型代码。默认 micro-batch 1、smoke 1024 tokens、rank 8；1536/2048 bucket 在前一档可行后逐档测试，不强截关键内容。

先登记公开原始模型 revision、许可、预计下载大小和缓存位置；不自动接受 gated 条款。T1 首轮下载/环境/模型制品规划上限 20GiB，全项目仍受 50GiB 上限约束。MLX peak 目标 24GiB、RSS 警戒 30GiB；每次作业前写明 step/token/最长 wall time、系统压力和 swap 增长阈值及恢复策略，超限保存并停止。不抬高系统 wired-memory 限制。仅本机免费计算，不调用付费 API 或云资源。

## 验收命令与边界

已存在的 CPU 回归入口：`uv sync --locked --python 3.14`、`uv run --locked pytest -q`、`uv run --locked ruff check .`、`uv run --locked python scripts/check_contract_freeze.py`、`uv run --locked python scripts/check_public_content.py`。

以下为 **PLANNED / NOT_RUN**，由本包实现；真实命令/参数在 handoff 固定，尚不存在不得写已通过：

- `uv run --locked pytest -q tests/training/compatibility/`：CPU loss/mask/reference 身份与资源控制正负例通过；如需新增依赖，先由 S0 合并锁文件。
- `python -m toolalign.training.compatibility --help`：提供硬件检查、CPU 数学核验、受控模型 smoke 的可复现入口；探索时使用私有已记录环境中的 Python。
- `python -m toolalign.training.compatibility <子命令> --config <私有配置路径>`：实施前先在本包报告记录具体参数、预算与预期；必须包含退出码、原始日志 hash、真实计数、保存重载及负例结果。

负向场景须覆盖 mask 错位、padding 被计入、reference 指向原始底座或变化、adapter scaling 不匹配、锁竞争/等待超时不加载、保存重载偏差。公共 GPULease 已有 P00 测试可复用；新增模型入口须证明真的使用它。

## 阻塞与交接

依赖请求提供精确版本、Python/平台要求、许可/来源和最小 reproducer，由 S0 批准实施公共更新。DPO 不通过时保存具体失败，最多一次备选；SFT 可行性继续核验，DPO 保持未通过，不能擅自改成成功。

交接：`coordination/handoffs/P01-r1.md`；包含个人应理解的 loss/reference/统一内存技术点。未完成测项逐项列出，待 R1 和 S0 验收。

2026-09-06 公共基线更新：S0 已授权采用已验证生产合并 `18fc8475476f6becf684ba817480caeb96a7cfb9` 及协调状态 `a6c8dd3c78b3674a242b4faacbb175f7b7c98303`。保留原 code_base/authorization 的历史记录，实际工作分支以非强制 merge 接入；新模型规则 gpt-6-astra/max 优先于首派任务副本。

2026-09-06 第二次公共基线更新：S0-SHARED-02 已独立审查/CI/合并/main验证，生产base `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`。收到S0原生同步消息后，保留f97bb0d及原环境/模型/失败证据，非强制merge本报告所在协调提交（完整SHA由消息给出）。仅CPU复核新base的测试、包构建/隔离安装与环境metadata，必要时在已锁环境运行原CPU数学检查；不重新跑未受影响模型校准，不加载模型或扩展P04。允许新增`coordination/handoffs/P01-base-r2.md`记录新完整候选、merge关系与实际结果，原P01-r1保留。

## 完整候选的独立技术审查范围

本段为准备好的范围，尚不表示原生派发。R1须先完成当前审查并经S0核验原生空闲，再依据S0消息给出的完整authorization_commit启动。在自己的隔离worktree新建`review/p01-r1`，审完整候选`59b3802c81aa6eceaf3609af88f288756bcb1581`；生产base为`37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`，同步目标f2a271b、实际merge17a003f。相对同步目标共27文件、6516新增行，不能只审base-r2的6个新增审计/报告文件。PR6精确候选双Python CI通过不替代本包审查。

仅允许新增`coordination/handoffs/P01-review-r1.md`与`reports/review/P01/`；原候选/实现、公共契约/配置/锁/状态/ADR与T1工作区全部只读。审查完整mask/shift/EOS/prefix、CE与DPO loss/梯度、首次真实梯度累积周期的ln(2)、SFT reference冻结与身份、adapter更新集合和跨库重载、局部编译/wired设置适配、全程GPU租约及真实停止回收。保留全部首选/备选失败、pressure停止和历史结论修订，SFT与DPO分别给出证据边界。

本轮仅CPU检查与按manifest只读核验T1历史模型证据；可在自己的私有环境用已锁CPU依赖，新增环境/审计制品预算2GiB。禁止模型导入/加载、GPU或无具体理由重跑长校准。若具体疑点必须GPU重现，先向S0提交最小命令、资源与停止预算，再另行授权。当前217项CPU、环境69/90与源码hash、包构建/隔离安装均为T1证据；R1需独立小反例和原始证据对应。1024/1536/2048容量结果不证明正式256-token完整harness或长时训练，P04/P05及kris人工核对仍未执行。

按精确候选输出PASS/FAIL/BLOCKED、P0/P1/P2、命令/退出码/loghash、独立review commit与NOT_RUN，提交报告后结束本轮等待S0；不修改实现后给自身修复签通过。

2026-09-06 实际派发：S0已收取P02技术PASS原始审查提交8e4fdbd并核验该轮终止/原生IDLE，随后以本范围授权`52f9c57a50eaf580a1a90bc5c4b8bd028c83b903`原生派发完整P01候选59b3802，gpt-6-astra/max；已确认R1新一轮活跃。P02人审由kris单独进行，不由本次审查代签。上述范围准备已转为实际派发，候选、预算与文件所有权不变。

## R1-r1退回后的T1定点修复授权

2026-09-06，R1正式审查提交为`ac6bdf78d57c6753865a24a1d216b90dc4478646`，父提交正是59b3802；只新增8个审查文件，原155个候选文件字节不变。S0已读取[报告及原始反例](https://github.com/kris0516/ToolAlign/blob/ac6bdf78d57c6753865a24a1d216b90dc4478646/reports/review/P01/README.md)，核对24份命令日志、4份私有结果与5个探针hash，并保留原SHA推送审查分支。217项适用CPU回归通过，独立pytest为4通过/3失败；两个P1阻断当前G1(SFT/DPO)，不是对未重跑模型的额外失败声明。

收到S0给出本段完整authorization_commit的原生消息后，T1在现有`work/p01-compatibility`从59b3802非强制接入上述R1原始提交，不reset/rebase或改写旧证据。沿用已验证共享生产base37c00de；读取最新授权即可，本次无需合并无关P02实现或反复追随协调文档。R1文件全部只读。模型gpt-6-astra/max；当前仅此一个拟派实现任务，最多两个实现并行的规则不变。

- F1/P1：资源采样异常时先可靠回收自有child，保留异常类型/原因、实际child退出码、resources和run.v1的failed终态及ended_at。覆盖sysctl命令失败和非整数压力读数；未知压力不得当正常，正常/预算/取消/租约路径不能失去原有回收或证据。只处理本任务明确拥有的进程。
- F2/P1：备选DPO回调第8微步前上游已经完成optimizer.update，ln(2)失败不能抹去该步实际loss、微步、token与optimizer计数。可靠记录已执行工作及失败事实后停止；保持首次真实累积周期的逐步门槛和2e-6容差，不改mask/reference/数学或校准配置来绕过问题。检查同一记账路径的非有限loss异常，输出保持标准JSON。
- F3/P2：澄清math-r2记录HEAD `aaab75ed5d993f9354f11f74b58edb67d0af45c3`与实际工作树源码的区别，全部8份实际源码hash映射到`47c03404bab043e85b417cd8a6d0432dc2f85479`。在当前去敏报告登记可恢复映射；原HEAD/source hash/raw及旧报告提交保持原样，不把历史run改写成修复代码实测。

允许修改仍为`src/toolalign/training/compatibility/`、`tests/training/compatibility/`、`reports/hardware/`，另允许新增`coordination/handoffs/P01-fix-r3.md`。原P01-r1/P01-base-r2和R1交接原文、公共契约/runtime/configs/依赖/检查脚本/README/AGENTS/协调状态均只读。只做必要修复及CPU反例、完整适用CPU回归、lint/冻结/公开扫描、实际新sdist/wheel追踪字节与隔离默认CPU安装核对。复用未变锁环境，新增私有制品/环境预算2GiB；不无理由重查依赖或重跑旧长校准。

本轮无MLX/模型导入或GPU重放，无权重下载、OS限制修改、费用或P04/P05扩展。具体疑点如必须GPU证明，先给S0最小命令及资源/停止预算，另行调度；本授权不包含该作业。交新完整candidate、两条基线的diff与文件清单、每项问题和命令/退出码/loghash、包成员/证据hash及FAIL/NOT_RUN。提交新handoff后结束本轮，S0安排R1对新候选复核；T1不自行合并或签验收。

2026-09-06 实际修复派发：S0再次核验T1上轮completed/notLoaded、工作树干净且HEAD59b3802后，以完整授权`a0a800b2a544cb25e7eccad2dce12173acc77ea1`原生派发本轮F1/F2/F3修复，gpt-6-astra/max；新轮次已确认活跃。读取授权范围即可，不要求同步后续状态文档。当前只有T1一个实现任务及R1的P03 CPU审查活跃。

## 修复候选的R1-r2复审授权范围

S0已读取新交接`P01-fix-r3`和报告，核验22份日志/探针/私有结果hash、11个本轮授权改动路径、159个未变原候选文件及全部8份原R1文件。完整候选为`ac8095faa58a98e143a8dc4d63042093e426feb0`，已测实现`5c32e8a72e957df100691e0096d1413eed8ce8f9`，最后提交仅增4份交接/包核验/证据文件。[CI34010040450](https://github.com/kris0516/ToolAlign/actions/runs/34010040450)双Python所有步骤成功；T1自测245个不同pytest检查及17组CPU数学通过，不替代独立复审。

本段仅准备范围，R1完成原P03报告并经S0核验原生空闲后，才按原生消息给出的完整authorization_commit启动。在自己的隔离worktree从上述完整候选建立`review/p01-r2`，仅新增`coordination/handoffs/P01-review-r2.md`和`reports/review/P01-r2/`。旧R1报告/探针、全部实现/配置/锁/协调及其他工作区只读，不修改原反例来取得通过。

逐项复核原F1/P1监控错误的实际回收、终态、原异常与真实退出码，包含压力读取TimeoutExpired与普通child轮询的区分；原F2/P1已完成微步/optimizer/token/loss和非有限值的标准JSON失败记账，保持原数学/门槛；原F3/P2全部8份源码身份映射且历史raw不变。运行未修改原反例，独立检查修复及必要相邻失败/正常对照、完整适用CPU回归、lint/冻结/公开扫描、新包追踪字节与隔离安装。根据实际变化复核已有数学/模型证据绑定，未变的历史长校准不重复运行或重算为新GPU通过。

gpt-6-astra/max，仅CPU，新增私有环境/制品2GiB；可复用自己已锁CPU环境。无MLX/模型导入、下载、GPU、P04/P05或费用。若具体问题必须GPU复现，提交最小命令和预算由S0另行调度。报告精确候选PASS/FAIL/BLOCKED、每项关闭或残留的P0/P1/P2、真实命令/退出码/loghash与NOT_RUN；提交新独立review commit后结束该轮等待S0，不自行改实现或合并。

2026-09-06实际复审派发：S0核验R1的P03轮次completed/idle后，以完整授权fd67511ef4cb7853bb75b0b106ec4692a9d36be8和精确ac8095f原生派发本P01-r2范围，gpt-6-astra/max，新轮次已确认ACTIVE。
