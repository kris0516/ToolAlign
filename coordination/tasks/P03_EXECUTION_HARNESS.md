# P03｜本地工具执行器与语义 oracle

状态：IN_PROGRESS（正式退回，待E1最终修复）；R1对完整`79a15d990fc27a9a33d033983c94eb92cccfb268`正式FAIL，审查`f34f7c5a4eac54b18a2b092495f4ce8eaa334f98`，P1=2/P2=1。E1已有收尾修复checkpoint2195b2e，原生空闲，尚非完整交接/独立验收；最终授权见本文件末尾。原79a15d9及`85e0905fc82da4504d73bf7eb489c1f1a0d227a7`完整保留。owner E1；原code_base`97466a20f599f68c511b9c8a71fe5f2cdfd9ad4b`；原authorization_commit`e882594da84359b7f6ced7dd6aefdb9c7ce06209`；branch`work/p03-execution-harness`。真实原生任务身份和隔离worktree/分支已核验，最多两个活跃实现任务。保留首派授权副本和原始基线。

模型统一 gpt-6-astra / thinking=max（最高）；仅 App 独立任务与 worktree，禁止 sub-agent、嵌套代理或自行创建其他任务。第一步 set_thread_title 并保存真实身份到私有 task-identity.json。给 S0 的普通回报省略 model/thinking。

## 依赖与范围

P00 冻结接口、S0-SHARED-01 来源政策均已合并验证。读取 AGENTS/GOAL/PROTOCOL、docs/01/04/12/13、configs/protocol.v1.json、contracts.v1.lock.json 与 src/toolalign/contracts/interfaces.py。公共 contracts/runtime/CLI/configs/pyproject/lock/CI/AGENTS/状态/ADR 只读，改动请求由 S0 处理。

允许修改：src/toolalign/tools/、src/toolalign/evaluation/oracles/、src/toolalign/evaluation/harness.py、tests/tools/、tests/evaluation/harness/、tests/fixtures/tools/、reports/harness/、coordination/handoffs/P03-r1.md。只提交原创小 fixtures、代码、去敏统计与证据摘要。正式隐藏任务/答案、原始日志、运行制品只在私有目录。

当前存在已知 App worktree sdist 私有文件选择问题，S0-SHARED-02/PR4 正在独立审查。**不要在本旧基线运行默认 uv build 或 sdist；CPU 实现/测试可继续，必要时只构建 wheel。** S0 发出修复后已验证 main SHA 再非强制 merge，不能自行采用未审共享候选。

2026-09-06 更新：该共享包已在 `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` 合并并验证，见 [main证据](../../reports/S0_SHARED_02_MAIN_VERIFICATION.md)。E1先保持空闲，待S0核验并发名额并发送原生同步消息后，非强制merge指定协调提交，保留85e0905与原始P03-r1；仅复核CPU/harness和当前包构建/隔离安装，不加载MLX/Qwen或扩展P04/P06。允许届时新增`coordination/handoffs/P03-base-r2.md`交新完整候选，旧基线禁止sdist的限制仍保留历史效力。

## 要交付的行为

实现与冻结 ToolRegistry、ToolExecutor、TaskOracle 和 ModelBackend 相接的本地 harness。Registry 绑定明确的实现、版本和 schema hash，拒绝重复/冲突名称。ValidatedCall 是可伪造且内含可变 mapping 的 dataclass，execute 前重新核验当前 registry/hash/version、参数与策略，避免修改后继续执行。未知或未绑定的 ta_ 历史工具必须拒绝；dataset schema、sandbox_only 字段和来源 URL 都不提供执行权限。

实现六类原创开发运维工具：版本文档检索、构建/测试报告查询、日志过滤、结构化记录聚合、版本兼容比较、单位/数值转换。优先固定资源 ID 查表；若提供路径则严格绑定隔离根并拒绝遍历/符号链接逃逸。无任意宿主路径、外网、shell/Python/SQL/eval/exec、真实业务写入或数据动态注册。输入/输出须有界。

Oracle 验证任务目标的对象、日期、版本、数值与允许策略集合；工具正常返回或答案自称成功不足以判通过。至少包含合法多解、多步依赖、相似工具混淆、无需工具、缺参应澄清、故障后的有限恢复。OracleTask/expected_action/评分标签不传给 ModelBackend；任务本来允许通过工具获取的资源内容可正常返回。可公开原创开发用 fixtures，不提前公开正式最终测试答案，也不能为训练偷看测试 oracle。

使用明确命名的 scripted CPU ModelBackend 提供可运行 demo，证明接口和状态机可工作；不把脚本回放当作 Qwen 推理或 benchmark。P04 真实 ModelBackend、P06 正式指标/分组 bootstrap/BFCL 与 GPU 评测不在本包。

预算沿用最多3次模型决策、2次工具轮次；256 max_new_tokens 按架构定义是每次响应上限，30秒为统一请求 deadline，二者仍是待模型验证配置。累计报告 token、决策、轮次与耗时，重试和修复不能重置；不能额外免费生成。UTC expiry 可序列化，执行耗时用单调时钟。超时/取消必须真正结束本任务创建的阻塞操作，不能只丢弃 future 却留后台执行；只回收身份明确的自有进程。若需要额外公共配置先请求 S0。

每次事件输出合法 trace.v1；覆盖解析、验证、unknown tool、执行错误、timeout、cancel、budget、final 等终止路径。raw output 和可选 repaired output 分开，默认评估原始结果；失败保留在分母，unknown/排除如实登记。scripted token 数仅用于实现预算测试，不能当真实 tokenizer 吞吐。

## 实际验证和交接

现有命令：uv sync --locked --python 3.14；uv run --locked pytest -q；uv run --locked ruff check .；uv run --locked python scripts/check_contract_freeze.py；uv run --locked python scripts/check_public_content.py。

PLANNED/尚未实现：uv run --locked pytest -q tests/tools/ tests/evaluation/harness/；python -m toolalign.tools --help 与其 CPU demo 子命令。先固定实际 CLI 参数再记录结果，不能把计划命令写成已跑。

必要负例：参数结构合法但选错对象/版本判失败；无工具任务却调用；伪造或修改后的ValidatedCall、旧registry/hash/版本、ta_未知工具；schema注入/超界输出；timeout/cancel/retry不重置预算且没有遗留自有进程；oracle标签不进入ModelInput；所有等价合法答案可通过。报告六类覆盖、真实计数/退出码/日志hash与未测项。

仅 CPU，无模型导入、权重下载或费用；首轮私有制品/环境预算2GiB，不改变OS限制。提交授权文件的精确SHA和P03-r1 handoff，请S0安排独立R1；不自行merge、改看板或签验收。无法可靠判定的任务标unknown，不用模型自评补真值。

## 完整候选的独立技术审查范围

本段为准备好的范围，须前项审查已正式结束、S0核验R1原生空闲并发送精确authorization_commit后才启动。R1在自己的隔离worktree新建`review/p03-r1`，审完整候选`79a15d990fc27a9a33d033983c94eb92cccfb268`；生产base`37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`、同步目标f2a271b、实际merge86c5e8a。完整差异19文件、3263新增/1删除行；原85e0905、P03-r1及全部原始证据保留。不能仅审base-r2的两个新文档，也不以PR7双Python CI替代独立审查。

仅允许新增`coordination/handoffs/P03-review-r1.md`与`reports/review/P03/`；候选实现、公共契约/配置/锁/状态/ADR和E1工作区全部只读。独立原创反例须覆盖六类工具的实际语义、registry/hash/version和可变ValidatedCall执行前重验、多解/澄清/无工具/有限恢复、错对象/日期/版本/数值、oracle标签不进入模型、单请求决策/轮次/token/deadline累计，以及实际进入阻塞后的timeout/cancel与自有进程回收。

仅CPU，新增私有环境与审查制品预算2GiB。核验新309CPU计数口径、原始10/10 scripted demo和归档/隔离安装证据；scripted合成token不可写为Qwen/BFCL或吞吐实证。父进程轻量可pickle后端与子进程generate/懒加载只是接口构造前提，已加载MLX对象仍NOT_RUN；不自行扩大为P04真实后端或P06正式评测。必要包检查应绑定当前追踪字节与冻结资源，避免无限重复已经通过且字节未变的共享调查。

输出精确候选、PASS/FAIL/BLOCKED、P0/P1/P2、实际命令/退出码/loghash、独立review commit和未测项；不先修被审实现再签通过，提交报告后结束本轮等待S0。

2026-09-06 实际审查派发：S0收到P01正式FAIL审查ac6bdf7并核验该轮completed/idle后，按原范围授权`52f9c57a50eaf580a1a90bc5c4b8bd028c83b903`向现有R1原生派发完整P03候选`79a15d990fc27a9a33d033983c94eb92cccfb268`，gpt-6-astra/max，已确认新一轮活跃。候选、仅CPU/2GiB预算、只增审查文件的范围不变；P01由T1另行定点修复，不由R1修改实现。

## 收尾IPC反例的E1并行定点修复授权

2026-09-06，R1报告了稳定反例，但**尚未提交整包审查结论**：`finish()`写`stop.json`抛OSError后，外层异常分支再次调用finish并重复失败；finally实际回收child，调用方却收不到HarnessResult和终态trace。正常回答与raw解析失败两种场景均由R1用已进入generate的真实CPU child复现，三个正常/解析/崩溃对照通过。S0另已读取精确79a15d9的harness.py223–242、413–417及OwnedProcess.close控制流，确认该异常出口需要处理。

E1上轮原生completed/notLoaded、工作树干净且HEAD79a15d9已核验。收到S0给出本段完整authorization_commit的原生消息后，在原`work/p03-execution-harness`从79a15d9继续；仅此定点修复与必要回归。不要改变或移动原候选，不merge无关P01/P02或后续协调文档。R1继续在自己的冻结79a15d9审查分支复核整包，E1新代码不成为本轮被审候选。

本轮应先在E1自己的CPU环境复现上述两种失败并保留原始结果，再修复：收尾信号写入失败仍可靠关闭/回收明确自有进程，返回有失败事实的合法HarnessResult/trace、完整分母和已消耗预算。不能反复重入同一失败写入、遗失原parse_failure或已有raw/计数，不能把未回收进程写成reaped，不能影响无关进程。保存正常终态/解析错误/后端崩溃及实际阻塞timeout/cancel的原行为。相邻清理错误如需处理，给出具体反例及范围；不泛化为新IPC框架。

允许修改`src/toolalign/evaluation/harness.py`、必要的`src/toolalign/tools/isolation.py`、`tests/evaluation/harness/`、必要的`tests/tools/`、`reports/harness/`，允许新增`coordination/handoffs/P03-fix-r3.md`。原P03-r1/P03-base-r2、全部R1文件、原始私有交付、其他worktree、公共contracts/runtime/configs/依赖/检查脚本/状态/ADR只读。原公开报告可追加准确修订范围；旧证据不得被覆盖成修复后实测。

仅CPU、gpt-6-astra/max；新增私有环境/制品2GiB，优先复用现有环境；无模型导入/下载/GPU/正式P04/P06或费用。当前T1另有一个CPU实现任务，派发后为两个实现加独立CPU R1，不再新增实现任务。按必要反例、适用完整CPU回归、lint/冻结/公开扫描、实际新包字节与隔离安装验证，未变共享调查不重复扩大。

可先交独立复现或修复checkpoint，但不得把R1整包审查写成已结束或当前修复写成已验收。R1正式报告到达后，由S0给出原始review_commit及最终需关闭项；E1保留并非强制接入该原SHA，补齐所有授权项，再交最终完整candidate及P03-fix-r3。随后仍需R1对新精确候选独立复核，S0合并/main验证；不得直接按旧CI合并。

2026-09-06 实际修复派发：S0已按完整授权`243821a988a12a6ff9f20b5fbb5ba1ae374d63c9`向现有E1原生派发本轮定点IPC复现/修复，gpt-6-astra/max，新轮次已核验活跃。R1已收到范围分离通知，继续完成冻结79a15d9的完整审查，不等待或混入E1新代码。原证据保持；目前T1/E1两个实现和独立CPU R1活跃。

## 正式R1结果与E1最终修复授权

R1正式review commit为`f34f7c5a4eac54b18a2b092495f4ce8eaa334f98`，严格以79a15d9为父，仅新增7个审查文件，146个原候选文件字节不变。S0已读完整报告和反例、核验22份命令日志、3份私有结果与4份探针hash；R1原生completed/idle已核验。结论FAIL：F1/P1停止通知EIO导致终态结果缺失，F2/P1目录清理EIO后访问已关闭Process覆盖原错误，F3/P2非阻断的oracle因果次序遗漏。原309项CPU通过，新增54项49通过/5失败；不把已回收误写成进程泄漏或实测CLI分母虚增。

E1已交付`fde181d3319f36179298a4bec2a928a8354ee6b3`实现及`2195b2e4ea3219884c3a8c1eed26d413141daa65`checkpoint报告，S0读取两个实现diff、10项新测试与报告，确认原生空闲。自测319CPU、包/隔离安装通过不是独立验收。收到本段完整authorization_commit的原生消息后，在现有分支保留两提交，非强制merge原R1完整SHA；不改写原FAIL/探针/私有证据，不merge无关P01/P02。

关闭F1/F2并运行原R1未修改的对应反例及正常/阻塞/预算对照，保留真实回收、目录状态、原parse失败、raw与已消耗用量。另明确授权关闭F3：仅对`src/toolalign/evaluation/oracles/semantic.py`增加必要的事件因果顺序/待完成调用核验，对先观察后执行等不可靠trace返回unknown，合法多解、多步恢复和实际失败含义不变；不泛化成新状态机。允许必要原创回归写入既有`tests/evaluation/harness/`。这是在原243821a范围外增加的具体oracle路径，其他原授权和只读边界不变。

仅CPU、gpt-6-astra/max；新增私有环境/制品仍按本修复轮累计2GiB，复用已有环境。无需重复未变共享包调查；原checkpoint的测试如源码变化会受影响，则在最终提交复验对应完整CPU、原R1探针、lint/冻结/公开扫描及实际新包/隔离接口。保留修复前和checkpoint证据，旧报告不覆盖；新增最终`P03-fix-r3`及报告必须给出精确候选、各问题、实际命令/退出码/hash和NOT_RUN。无ML/模型/GPU/下载/P04/P06或费用，不因另行准备输出格式而混入真实后端或解析协议改动。最终结束该轮等待新精确候选的R1复审，E1不自行验收或合并。
