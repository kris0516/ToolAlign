# 项目真实状态

更新时间：2026-09-06。当前交付状态：**P00、P01受限兼容校准与P03 CPU任务VERIFIED**，两个共享支持包已VERIFIED。P01/PR6合并d10722e，原始R1-r3 PASS 7e20706保持，最终双Python CI与main655CPU/21条隔离命令通过；G1-SFT与唯一DPO备选分项PASS，首选DPO仍FAIL。P02数据代码已MERGED且技术验证通过，整包/G-DATA仍待kris人审、新格式独立验收和训练绑定。D1完整新格式7bada2e已交付/空闲；R1按完整1de9078独立审该精确候选，新轮ACTIVE，gpt-6-astra/max、仅CPU。T1/E1空闲，P04训练未授权。

| 项目 | 当前记录 |
|---|---|
| 公开仓库 | `https://github.com/kris0516/ToolAlign` |
| 可见性 | public（GitHub connector read-back 已确认） |
| 规划 main 基线 | `0f152e287bbc0e1c3edfb3f6f3794eb8d36c422f` |
| 规划内容提交 | `a74b4e44b1be72c1fd254e1a24e91b28ee52639c` |
| 规划/协作基线 | plan-v0.1 / coordination.v1 |
| Supervisor | S0；本机独立 Codex 对话，已领取 |
| S0 模型/推理 | gpt-6-astra / max（最高）；已提交原生设置；普通回报省略 model/thinking |
| 领取时间 | `2026-09-05T21:19:08.074530+00:00` |
| 当前任务/分支 | S0 main；P01合并d10722e且主干验证通过，P03/P02既有技术验证保持 |
| 当前契约 | toolalign.contracts.v1 已冻结；五类 wire schema + 六个 Protocol |
| 独立实现/reviewer 对话 | 原7bada新格式正式FAIL/P2=1、公开review2942e56已核验/推送，R1原轮封存中；D1修复ACTIVE、接原review范围已准备；复审未派发，T1/E1无新任务 |
| 子任务派发模型 | gpt-6-astra / max（最高）；所有子任务与 S0 统一，旧极高规则废止 |
| 持久运行 | 长期 goal ACTIVE；本对话每 30 分钟跟进；电脑及 App 需保持运行 |
| 本地工具 | Python 3.14、uv、VS Code、Xcode 可用；P00 venv 实测 Python 3.14.7 |
| GitHub 写入能力 | 本机 Git push dry-run 成功；connector 确认 admin/push 权限 |
| 当前实现 | 已验收CPU基础包/契约/GPU锁、P01受限兼容校准、P03本地工具/oracle/scripted接口；P02数据流程技术验证通过，整包待审 |
| 已验收训练/数据/评测/服务 | P02代码技术集成通过；数据语义、训练、正式评测与服务均无整包验收 |
| 已运行模型实验 | 0.6B smoke 与 1.7B 长度校准的原始证据已独立核验并由S0限定验收；不作为正式P04/P05结果 |
| 重 GPU 作业 | P01历史校准已结束，当前未派发新GPU作业；任何后续加载仍须实际取得共享租约 |
| 费用/公开上传 | 无付费云资源；无模型/数据上传；无公网推理 |

精确本机路径、task ID、自动跟进 ID 和对话映射保存在 `.toolalign-local/`，不提交公开仓库。

## 当前门槛

P00和共享支持包验收保持。P02最终CI/main技术集成通过；整包VERIFIED仍需kris实际语义审查和训练配置/manifest/窗口绑定。P01已合并并验证main，G1-SFT与唯一DPO备选按ADR-0018分项PASS，首选DPO失败与校准边界保留。P03已在29a5e4c完成最终CI/合并/main验证，见[主干证据](../reports/S0_P03_MAIN_VERIFICATION.md)。训练与评测共同格式已按ADR-0017选择，尚未实现验收，见[衔接证据](../reports/S0_P04_READINESS.md)与[格式规范](../docs/16_MODEL_IO_FORMAT.md)。P04尚未授权，最多两个实现的约束保持。

## 恢复入口

先读 AGENTS、BOARD、DECISIONS、当前任务包及最近 handoff，核对 Git 与 GPU 锁，再读取本地私有对话映射。未提交变更不能作为交接完成证据；R1 不批准自身实现。首轮五项问题已修复；R1-r2 对 `5d30e1b4bd5e2284abbe59a5f16b2966f85feb87` 独立 PASS，剩余 P0/P1/P2 均为 0，审查提交 `441d31bebd5ca4d46755642f94966c07bbcc4ad1`。最终 PR head `7086424` 的 Python 3.11/3.14 CI 成功，PR #2 合并为 `cd091e3a53986b59b170baf5b746644f369135d1`；main 58 + 46 + 72 项检查及 lint/冻结/公开扫描/CLI 均通过。见 [独立复核](handoffs/P00-review-r2.md) 与 [main 证据](../reports/P00_MAIN_VERIFICATION.md)。

公共支持：S0-SHARED-01 已 VERIFIED，见 [main 集成证据](../reports/S0_SHARED_01_MAIN_VERIFICATION.md)。可选依赖/来源政策正式发布给 T1/D1；P01/P02/P03 候选尚待各包独立验收，不因公共支持通过而提前放行 P04。用户模型设置保护见 [GOAL](GOAL.md) 与 ADR-0014。

P01 精确候选 f97bb0de346c220871962a5689014a379fe19c83，274项CPU与模型校准仅为T1自测；下一批分别审完整P02/P01/P03。共享包R1-r3对f8ec7ff独立PASS，审查ad3b519保留原SHA整合，两轮FAIL保持原文；最终CI成功，PR4合并37c00de并验证，[新共享base现已发布](../reports/S0_SHARED_02_MAIN_VERIFICATION.md)。D1/T1先同步，E1待名额；不得在旧基线默认构建sdist。D1已隔离一次未上传的旧失败tar，细节私有保存。

P02 精确交接 `46f546504f73588caa2e71aac316c3c312306df6`，生产实现 `9be07a5`。D1 自测 355 项 CPU（包含 57 项旧共享快照），两次构建 18 项产物一致，最终 8,228 决策；这不构成独立验收。S0 已核对 100 来源/114 决策人审包及独立填写副本的 hash，判定字段全空，G-DATA 仍待审；实际渲染未验证。

P03 精确交接 `85e0905fc82da4504d73bf7eb489c1f1a0d227a7`，实现 `8afb114`。E1 自测191项CPU（133项P03）、scripted demo 10/10、90条trace与20个自有进程回收。S0已读取正式交接并核验原生任务终止；尚无独立R1、真实MLX/Qwen、正式隐藏集/BFCL或GPU验收。ModelBackend的spawn构造与轻量可序列化状态前提保留在交接中，不能从scripted成功推定已加载MLX对象可跨进程使用。

最新同步交接：T1候选59b3802c81aa6eceaf3609af88f288756bcb1581（merge17a003f）CPU217通过，新锁69/90环境metadata及PyTorch CPU参考通过，原模型实现/10次历史run未变。D1候选b0d8d83750c48cd951c16b50cfa28a7898976e72（merge9bbd7d7）CPU298含17真实tokenizer通过，data模块/两遍18产物/100来源114决策的人审包hash均未变。两者新sdist/wheel和隔离安装已自测，原始交接保留；S0核对新handoff及候选范围后安排R1，各包仍未VERIFIED。

已建立[Draft PR5/P02](https://github.com/kris0516/ToolAlign/pull/5)与[Draft PR6/P01](https://github.com/kris0516/ToolAlign/pull/6)。P02精确b0d8d83的[CI34003774338](https://github.com/kris0516/ToolAlign/actions/runs/34003774338)、P01精确59b3802的[CI34003775260](https://github.com/kris0516/ToolAlign/actions/runs/34003775260)，两个Python jobs所有步骤均成功；CI的默认测试范围不等同各worker完整CPU/真实tokenizer或模型验收。R1按S0授权c44739ac1e2fe282f5f51f80c5ea099687051ff3在隔离review/p02-r1审完整P02，已核验原生活跃；P01随后。E1已非强制merge86c5e8a并确认原17交付/63私有证据文件未变，继续CPU/pkg验证。

E1同步验证现已交付完整79a15d990fc27a9a33d033983c94eb92cccfb268，并读回远端相同SHA、核验原生空闲。[Draft PR7](https://github.com/kris0516/ToolAlign/pull/7)保留候选待R1；该精确候选的[CI34004701148](https://github.com/kris0516/ToolAlign/actions/runs/34004701148)已核对Python3.11/3.14全部步骤成功。309CPU、实际sdist/重建wheel/追踪字节核对与隔离安装均为E1自测通过；installed scripted demo10/10、20自有进程回收，另四个工具/模型阻塞timeout/cancel检查通过。初版私有归档检查器漏列已追踪.gitignore的失败记录保留，修正未改变公共实现。没有真实MLX/Qwen/P04/P06实验。S0已读取新handoff/report并独立核对原P03源码/测试/交接字节不变。以下实际审查派发以原生终态与消息回执为准，准备任务包不等于已启动。

P02最新技术验收：R1对完整b0d8d83750c48cd951c16b50cfa28a7898976e72给出PASS，P0/P1/P2均0；审查提交8e4fdbd7374130c77262a57e55049f9cef4bf651直接以该候选为父，只新增6个允许的审查文件。338CPU、全部调用/前缀/分组/18产物与226条独立分词通过，详见[正式交接](handoffs/P02-review-r1.md)。S0核对26份R1命令日志、4份私有结果、3份探针hash和原始SHA关系，非强制整合为bcc896e0912dde474f463f0407becbde2989c876；候选src/tests/manifests/公共锁/配置字节未变，待最终CI/PR合并/main验证。

kris人审请求已实际发出，材料为不变的100来源/114决策/34分层，先前冻结表与填写副本均空，尚未收到本人结果。R1新增的浏览器检查已实际完成：说明和一个展开样本可见、无横向溢出，500内容区另以解码值核对；不改写D1历史NOT_VERIFIED，也不声称逐页人工判定。来源61原turn5作为具体语义待决点交kris，不预设误标/通过。P05数值阈值未套用P02。

接续派发：R1在P02正式完成/原生IDLE后，按授权52f9c57a50eaf580a1a90bc5c4b8bd028c83b903收到完整P01候选59b3802c81aa6eceaf3609af88f288756bcb1581，gpt-6-astra/max；原生已确认新一轮活跃。仅CPU、历史模型证据只读，P01/P03仍未验收。

P02集成现已完成：[PR5](https://github.com/kris0516/ToolAlign/pull/5)以最终head71a50ba合并为2ec17673c18ffbc817b1ff8512e53e44a11766a5，GitHub已读回closed/merged，本机main tree与最终CI head完全相同。[CI34006711558](https://github.com/kris0516/ToolAlign/actions/runs/34006711558)双Python所有步骤成功；实际main338CPU无skip、241/18归档探针、真实sdist及默认/显式重建wheel、14条隔离安装/P02接口子命令通过。默认wheel按原始日志由sdist生成，先前direct标签已在报告校正，未增加一次未执行的源码直接构建。归档0未追踪载荷，24源码/资源字节一致；README导致的metadata差异已逐成员确认。完整命令/退出码/hash与限制见[主干技术证据](../reports/S0_P02_MAIN_VERIFICATION.md)。P02状态MERGED，人工语义与训练绑定仍未通过，P04保持未授权。

P01完整R1审查现已交接：`ac6bdf78d57c6753865a24a1d216b90dc4478646`直接以59b3802为父，8个新增审查文件、155个候选文件未变。结论FAIL（P0=0/P1=2/P2=1）：监控异常遗漏resources/run终态；备选DPO第8微步ln2失败漏记已经执行的更新；math-r2工作树源码与记录HEAD的说明需纠正。S0读取正式交接/反例，并核对24份命令日志、4份私有结果和5个探针hash，保留原SHA公开审查分支；[正式报告](https://github.com/kris0516/ToolAlign/blob/ac6bdf78d57c6753865a24a1d216b90dc4478646/reports/review/P01/README.md)。217CPU与17组独立数学对照通过，独立pytest4通过/3失败，不能抵消P1。原10个run和185项制品只读核对，历史受限模型结果不改写为本次重跑。

S0已准备T1的F1/F2定点修复及F3来源映射授权，原候选、FAIL和raw保持。R1该轮completed/idle已核验，按52f9c57和精确79a15d9实际派发P03并确认活跃；仅CPU、不启动模型。T1已按授权a0a800b原生派发并核验活跃，D1/E1空闲。P02人审请求继续等待本人结果，P04的10条token/mask人工核对属于后续训练验收，尚未执行。

P03审查中的稳定反例已由R1回报：stop.json写入失败后finish重复抛错，child被真实回收但缺HarnessResult/终态trace，正常和raw解析失败场景均复现。正式整包结论仍未提交。S0核对精确源码后授权E1在自己原79a15d9分支复现并定点修复，待实际派发；R1继续审冻结原候选，新修复另候复核。E1原生终态及干净HEAD已核验；派发后与T1合计两个实现，不新增第三个。

E1定点修复现已实际派发：授权243821a，gpt-6-astra/max，原生新轮次ACTIVE；已告知R1继续冻结79a15d9独立审查，不等待或混入修复。原始证据不变，最终R1报告到达后再把原SHA及剩余项交E1整合。当前恰有T1/E1两个实现，R1仅CPU；没有新GPU或P04派发。

最新交接：T1完整修复候选ac8095faa58a98e143a8dc4d63042093e426feb0已非强制推送，原生completed/idle；S0核对11个本轮授权改动、159个未变原文件、8份原R1证据及22份日志/探针/结果hash。自测245个不同pytest检查、17组CPU数学与双Python CI34010040450通过。新R1-r2范围已准备，尚未独立签通过。

R1对P03完整79a15d9正式FAIL，原review f34f7c5a4eac54b18a2b092495f4ce8eaa334f98以该候选为父，只新增7份文件，146份候选字节不变；S0读取完整报告/反例并核验29份日志/探针/结果hash。309CPU通过，新54项49通过/5失败，分别为收尾stop写入和目录cleanup的两个P1，以及oracle事件因果顺序的一个非阻断P2。原生终态已确认；原FAIL不能按E1后来代码改写。E1 checkpoint2195b2e含fde181d修复和10项自测，尚未接原R1且未最终交接。已准备同轮累计2GiB的最终修复范围，明确加入semantic.py的F3路径，不含真实后端或输出协议变更。

最新实际接续：完整授权fd67511ef4cb7853bb75b0b106ec4692a9d36be8已提交/推送，原review f34f7c5也已按原SHA推送。S0核验三者先前原生终态与各自候选后，分别派发R1对ac8095f的P01-r2、E1接原R1并关闭F1/F2/F3、D1输出格式CPU提案；均显式gpt-6-astra/max并已核验新轮次ACTIVE。D1仅新增提案/小探针/交接，不修改生产代码或原人审包，原本地b0分支暂不推送覆盖较新远端。当前两个实现加独立CPU R1，T1空闲，无新GPU或正式训练。

当前正式交接：R1对ac8095f的原始review `aaae5a4395dbdd73fd487f80174599ffd3ef9be3`为FAIL/P1=1；S0读取完整报告及两个初始化反例、独立核对26项日志/结果/探针hash，170份候选字节未变。245个不同现有pytest检查和17组CPU数学通过，新增22项20通过/2失败；两失败都没有创建child，原错误传播但登记的run永久running/summary遗漏。原F2/F3已关闭；历史模型证据及原FAIL保持。T1原生空闲核验完成，P01-fix-r4范围已准备，尚未派发。

E1最终候选 `3598cef2efb99e2990e384812a028902964cf494`已交付/非强制推送并核验原生completed/idle。S0完整读取最终交接/修复及原创回归，20项命令/归档/隔离结果hash、原7份R1文件、15个总差异路径已核验；389CPU自测与CI34011754142双Python全部步骤通过。原checkpoint及其53通过/1失败保持，尚不能称P03已独立通过。S0只读merge-tree预检无冲突，69个P02/契约/配置及P03源码/测试blob绑定正确；并未实际合并或运行组合后的候选测试。R1新3598复审范围已准备，待当前轮次原生终态后派发。

D1初版格式提案完整`c23b5136e596379000fcf4a9c2d1ce4bc9e27aec`（提案/探针429ff90）只新增3份文件，167个旧tracked文件未变；S0完整读取handoff/probe并独立核对45项hash。12个CPU原创/公开fixture通过值往返、原P03 raw parser、prefix/EOS/序列核对，不证明单一user envelope的模型角色行为等价。S0已在原提案范围内要求同12例与保留消息角色投影作有界CPU比较，D1原生任务仍活跃；无重复派发。原277-token completion例超过256响应上限，只作边界测试；未来序列审计须同时绑定生成可行性。没有正式格式ADR、生产默认切换或全量新序列生成；原数据/人审材料和未答请求保持。

最新实际派发：授权cbb6d4614c3b8e8f584315ac3bdad434544c3984已推送。S0核验T1原生空闲与干净ac8095f，及R1上轮completed/idle、原始aaae5a4审查后，分别原生发送T1的P01-fix-r4和R1对完整3598cef的P03-r2，均显式gpt-6-astra/max，并已确认新轮次ACTIVE。D1沿原fd67511范围继续CPU提案比较，E1等待复审结果；仍两个实现加独立CPU R1，未授权GPU或P04。原review aaae5a4按原SHA推送独立分支，未改写旧FAIL。

D1完整角色比较现已交付6c3d330e4b28be0fbc93c273bb2576f7317c69a8，S0核验原生completed/idle、完整报告与新增代码、68项文件/命令/实际结果hash及167份原文件不变。同12例A/B保持ModelInput值和C字节/IDs，B保留原system/assistant控制段、tool由官方模板转user/tool_response；小集prompt多39–93token，不构成模型质量或纯角色消融结论。S0按ADR-0017选择B并定正式v1标记，新P/sequence必须重算；D1新共用模块/完整8,228例序列审计授权已准备，尚未实际派发，原P02实现/数据/人审包及未答请求保持。

实际接续与新交接：D1在原生completed/idle及干净6c3d330再次核验后，S0按完整0c94ad58a78d30cd88a9ad86ac8e8d8c83b2442c原生派发P02-format-r2，gpt-6-astra/max，新轮次ACTIVE；原6c3d330已按原SHA发布proposal/p02-output-format，仅为提案证据保全。

T1新完整候选9fe3cbe3a067725c37dc213bbf38f9c90ceb5066普通推送/原生completed/idle，原review经65437ea普通merge保留；S0完整读取两处生产diff、新回归/报告/包探针和正式交接，核对85项hash与9个允许改动/174份不变原文件。原两初始化反例before确实2失败，after实际failed/ended_at/resources/summary齐备且异常对象、缺测/零已执行工作准确；280个不同pytest和14条隔离命令为T1自测。新P01-R1-r3精确候选范围已准备，旧FAIL/历史负结果不改写。

R1对3598cef正式P03-r2 PASS，review a78071bf6ac40f2729e090e1828a1c6022cd8d00严格以其为父，仅6份新增文件，全部158份被审文件不变。S0完整读取新报告/31项独立探针和核对/安装脚本，核验139项日志/结果/源码/安装流/归档hash。原54项及其余335项通过，无skip/xfail；新增31项源路径与安装路径重复验证通过、不重复计数，原三问题全关闭；新实际sdist及默认/显式重建wheel、16条安装命令和各旧FAIL/开发失败保持。R1原生completed/idle已核验；CPU代码达到ACCEPTED，待S0最终集成/CI/main验证，未运行真实MLX/Qwen或正式评测。

最新实际复审接续：S0重新核验R1的P03-r2已completed/idle后，以完整授权79814897340537c232ddc7e1814fc6d4ecb503bb和精确9fe3cbe3a067725c37dc213bbf38f9c90ceb5066原生派发P01-R1-r3，gpt-6-astra/max，新轮次已确认ACTIVE。原a78071b已按原SHA发布review/p03-r2；S0负责P03后续集成，R1继续独立P01不等待其合并。

P03实际主干验收：S0普通整合原a78071b和当前main为84084770bf07f32647af36ac748bf76326e74ed1，受保护公共路径及P03被审字节保持；CI34014772645双Python jobs所有步骤成功。[PR7](https://github.com/kris0516/ToolAlign/pull/7)实际合并29a5e4c6affa2b822717fd3184b25ccb756e1651，GitHub closed/merged与本机相同tree均已读回。实际main551CPU无skip、真实sdist/默认和显式重建wheel、18条新隔离命令及P02/P03组合接口通过，P03 CPU任务VERIFIED，见[主干证据](../reports/S0_P03_MAIN_VERIFICATION.md)。首跑因S0临时目录放置导致的550通过/1失败保留，仅更换basetemp后全过；未改实现/测试。新installed demo10/10为scripted，31项已有独立反例为安装复验，不重复计数。05:59:42UTC共享GPU锁为空闲，人审副本100行0判定/0reviewer未变。D1同轮同步已验证P03基线的范围现已准备，原0c94ad5格式规范和授权边界继续适用；尚待原生发送。

P01第三轮复审正式交接：原review 7e207060539df682691b4d149e68b7ab4ffc3175直接以9fe3cbe为父，只新增6份审查文件、183份候选字节未变。S0完整读取handoff/README/13场景探针/审计及包核验器，实际核对178项日志/结果/公开文件/子进程制品/归档hash；私有证明SHA-256为badf039e7a08908e1457d2a5423df89ce1eb0d2c0401336b5c88e062ad189b56。R2-F1及原F2/F3均关闭；原29反例+251适用CPU检查通过，新增13场景通过，安装重复13不再加计。17条命令保留两条遗漏PYTHONPATH导致的exit2；只修调用后通过。新实际三份包及15安装命令均通过；旧17数学/185载荷按不变身份沿用，92份历史小文件已由R1重核，不伪称重跑模型。R1原生completed/idle已核验，P01代码ACCEPTED待S0最终CI/合并/main验证。D1已实际收到5212b24同步授权并确认同轮普通merge已验证P03，原格式CPU交付继续，未签人审或启动模型。

P01实际主干验收：S0普通整合原7e20706与当前main为90b29363b4d2ba8003ed7af17fa359960702b33c，214个既有main路径与61个P01被审路径均未变。CI34016103173双Python所有步骤成功，PR6合并d10722e491d6a8efe26b8248efb9c19cc2216742，GitHub closed/merged与本机相同tree已读回。main655CPU无skip、实际sdist与默认/显式重建wheel、42源码字节和21条新隔离命令全部通过；13个P01和31个P03边界是安装重复验证，不再计为新增独立检查。见[S0主干/G1证据](../reports/S0_P01_MAIN_VERIFICATION.md)，摘要hash b1b603dc68763cbf89969dde2356d92335a992504e3fcba4a8085d7337149326。P01达到VERIFIED，G1-SFT与唯一mlx-lm-lora备选在原受限配置PASS，mlx-tune首选FAIL及所有旧失败保持，原数学/模型证据本轮未重跑。06:22:51UTC共享GPU锁空闲，人审副本100行0判定/0reviewer及原hash不变。D1仍做原格式CPU交付，P02/G-DATA与P04前提未因本次合并而跳过。

新格式正式交接与实际审查派发：D1完整候选7bada2e451d43dae4b3ed532d5efa310fc8e6a57（父9f4e7a3、tree fdf0c10）已普通推送并核验原生completed/idle。S0读取新模块/测试/审计/包探针和正式报告，独立核验713项checksum（completion1、公开18、私有620、37条命令的metadata/log共74），214个既有5212b24主干文件和3份原提案逐字节不变；证明SHA-256为06f72e150ac85e5703f163b718f1f755354495ac057aeb6c9f931cfb58e29d33。五个model_io实现/资源从唯一全量测量b33a55f至最终保持，原P03 parser身份一致，旧开发失败保留。D1最终664CPU无skip、实际三归档与10条默认CPU隔离命令通过；8,228行完整分母中总长>2048为1,351、C含EOS>256为269，统计交集6,685没有成为训练选集。这些为实现方证据，尚不构成新格式验收。S0再次确认R1上一轮completed/idle后，以完整授权1de90781e42a3693b112aafcf585a905bc052d63原生派发该精确candidate的P02-format-review-r1，gpt-6-astra/max，新轮ACTIVE。原数据、全部人审材料和填写副本保持；无新模型/GPU/P04授权。


新格式[Draft PR8](https://github.com/kris0516/ToolAlign/pull/8)已实际建立，head7bada2e、main为base；CI34017408825的Python3.11/3.14两个jobs全部步骤成功。S0只读merge-tree预检无冲突，276份当前main路径和21份候选新增路径完全保留，没有checkout合并或组合测试，证据hash1f769066149bfe4adc6d50964a0cf2a9acad990c8a1ef308710444b49984effb。R1仍在精确7bada独立审查。S0已从固定指标重算train/validation预算交集与尾批：2048/256条件为6013/217，train751组累积8后仍有5微步；1024条件train仅985。见[准备记录](../reports/S0_P04_READINESS.md)，没有训练选集/新模型运行或P04授权。


S0隔离组合预检完成：在本地单独worktree普通合并main4e04f2a与候选7bada2e，得到未推送的f600b9506b0fbc3fdfeed1d5c4dcc61452a3c7cf；276个原main文件和21个候选新增路径字节保持。768CPU无skip、实际sdist/默认及显式重建wheel、47安装源码和10条隔离命令通过，见[组合预检](../reports/S0_P02_FORMAT_PREFLIGHT.md)，摘要hash23094e442a3d04af88646d015db373901bb2da4e427076fd0c9a3690d83a1baf。首次lint选错无Ruff环境的exit1保留，只修命令后通过。该结果提前核验跨包组合，不代替仍在运行的R1、最终CI/main验收或G-DATA/P04；原candidate和主干实现均未改。


R1仍在冻结7bada2e的独立审查中，已用真实未替换的HF loader稳定复现来源身份绑定缺陷：私有来源同尺寸更新后恢复原hash，声明身份相同而感叹号token由0变30；native已核验buffer对照通过。S0完整读取当前探针/helper与结果，封存9项源码/原日志/命令/结果副本，证明hash d33051b56aea3fc8588c47aa26e713b20b0783aca0d4f74f0e631f1a1d836510。正式R1报告未到，不预写整包结论；D1已核验原生空闲和干净7bada，P02-format-fix-r3的CPU定点修复范围现已准备，尚未实际派发。原768CPU组合预检与候选CI通过保持为其实际范围，不能关闭此缺陷。


新格式定点修复已实际派发：完整授权c6c02a5af084afe92c6e9f05d9d1c51392e805d0已push/readback；S0重新确认D1原生completed/idle及干净7bada后发送P02-format-fix-r3，gpt-6-astra/max，新轮ACTIVE。R1原审查仍ACTIVE且冻结7bada，继续独立封存正式结论，不等D1或混入修复。[Draft PR8](https://github.com/kris0516/ToolAlign/pull/8)说明已实际更新并读回，保留原候选CI与临时组合预检，明确该来源绑定缺陷未关闭。没有新GPU/P04或人审代填。


新格式原候选正式审查为FAIL/P2=1。S0完整读取原报告、交接、8个探针和具名Ruff例外，独立核验839项文件hash、235份候选字节、源/默认wheel同一F1、原664及新增60 pytest、两engine同12场景、一次8,228行reference全量及原D1制品保全。证明SHA-256为5ddfdd75918be89160cc3e3cc2a680ad4ebba9cb94be3ae0b0932393a171450d。公开review2942e568eae91d0292ad9691af133bbd8c33dd02以7bada为唯一父，已普通推送并远端读回；原本地f708641含一处公开索引的临时路径遗漏，保留本地，按085a61c授权仅三份发布材料作去敏映射，原9探针/配置保持，f708不在公开祖先。该附件遗漏不增加候选问题数。R1当前原生轮仍在封存，并未派发复审；D1现有b4dc1cf修复checkpoint及自测保持，同轮普通merge精确公开2942的范围已准备，尚待原生发送。原数据/人审/P04门槛保持。
