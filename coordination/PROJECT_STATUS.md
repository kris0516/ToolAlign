# 项目真实状态

更新时间：2026-09-06。当前交付状态：**P00_VERIFIED**，两个共享支持包已VERIFIED；P02数据代码已MERGED且main技术验证通过，整包/G-DATA仍待kris实际语义审查和训练配置绑定。P01修复候选ac8095f已交接并空闲、待独立复审；P03原79a15d9正式FAIL，审查f34f7c5，R1已结束并空闲。E1已有2195b2e修复checkpoint，最终修复授权及D1的格式衔接CPU提案范围已准备，尚未实际接续派发。

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
| 当前任务/分支 | S0 main；P02合并2ec1767且主干技术验证通过 |
| 当前契约 | toolalign.contracts.v1 已冻结；五类 wire schema + 六个 Protocol |
| 独立实现/reviewer 对话 | T1已交ac8095f并空闲；D1空闲；E1已交2195b2e checkpoint并空闲；R1已交P03原始review f34f7c5并空闲。准备下一范围不等于已派发 |
| 子任务派发模型 | gpt-6-astra / max（最高）；所有子任务与 S0 统一，旧极高规则废止 |
| 持久运行 | 长期 goal ACTIVE；本对话每 30 分钟跟进；电脑及 App 需保持运行 |
| 本地工具 | Python 3.14、uv、VS Code、Xcode 可用；P00 venv 实测 Python 3.14.7 |
| GitHub 写入能力 | 本机 Git push dry-run 成功；connector 确认 admin/push 权限 |
| 当前实现 | 已验收CPU基础包/契约/GPU锁；P02数据流程已合并并验证技术集成，尚未整包验收 |
| 已验收训练/数据/评测/服务 | P02代码技术集成通过；数据语义、训练、正式评测与服务均无整包验收 |
| 已运行模型实验 | T1 已报告 0.6B smoke 与 1.7B 长度校准；尚未独立验收，不作为正式 SFT/DPO 结果 |
| 重 GPU 作业 | P01历史校准已结束，当前未派发新GPU作业；任何后续加载仍须实际取得共享租约 |
| 费用/公开上传 | 无付费云资源；无模型/数据上传；无公网推理 |

精确本机路径、task ID、自动跟进 ID 和对话映射保存在 `.toolalign-local/`，不提交公开仓库。

## 当前门槛

P00自测、R1精确head独立审查、S0合并与main重验均已满足。P02最终PR5 CI/main技术集成已通过，代码为MERGED；整包VERIFIED仍需kris实际语义审查和训练配置/manifest/窗口绑定。P01修复仍待独立R1确认关闭原P1；P03两个P1与一个非阻断P2已正式退回，E1需最终交接并复审。训练输出与评测raw语法的共同格式尚未定义，见[只读衔接证据](../reports/S0_P04_READINESS.md)，D1仅CPU提案范围已准备。P04尚未授权，后续仍最多两个并行实现。

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

P02集成现已完成：[PR5](https://github.com/kris0516/ToolAlign/pull/5)以最终head71a50ba合并为2ec17673c18ffbc817b1ff8512e53e44a11766a5，GitHub已读回closed/merged，本机main tree与最终CI head完全相同。[CI34006711558](https://github.com/kris0516/ToolAlign/actions/runs/34006711558)双Python所有步骤成功；实际main338CPU无skip、241/18归档探针、真实sdist/direct+rebuilt wheel、14条隔离安装/P02接口子命令通过。归档0未追踪载荷，24源码/资源字节一致；README导致的metadata差异已逐成员确认。完整命令/退出码/hash与限制见[主干技术证据](../reports/S0_P02_MAIN_VERIFICATION.md)。P02状态MERGED，人工语义与训练绑定仍未通过，P04保持未授权。

P01完整R1审查现已交接：`ac6bdf78d57c6753865a24a1d216b90dc4478646`直接以59b3802为父，8个新增审查文件、155个候选文件未变。结论FAIL（P0=0/P1=2/P2=1）：监控异常遗漏resources/run终态；备选DPO第8微步ln2失败漏记已经执行的更新；math-r2工作树源码与记录HEAD的说明需纠正。S0读取正式交接/反例，并核对24份命令日志、4份私有结果和5个探针hash，保留原SHA公开审查分支；[正式报告](https://github.com/kris0516/ToolAlign/blob/ac6bdf78d57c6753865a24a1d216b90dc4478646/reports/review/P01/README.md)。217CPU与17组独立数学对照通过，独立pytest4通过/3失败，不能抵消P1。原10个run和185项制品只读核对，历史受限模型结果不改写为本次重跑。

S0已准备T1的F1/F2定点修复及F3来源映射授权，原候选、FAIL和raw保持。R1该轮completed/idle已核验，按52f9c57和精确79a15d9实际派发P03并确认活跃；仅CPU、不启动模型。T1已按授权a0a800b原生派发并核验活跃，D1/E1空闲。P02人审请求继续等待本人结果，P04的10条token/mask人工核对属于后续训练验收，尚未执行。

P03审查中的稳定反例已由R1回报：stop.json写入失败后finish重复抛错，child被真实回收但缺HarnessResult/终态trace，正常和raw解析失败场景均复现。正式整包结论仍未提交。S0核对精确源码后授权E1在自己原79a15d9分支复现并定点修复，待实际派发；R1继续审冻结原候选，新修复另候复核。E1原生终态及干净HEAD已核验；派发后与T1合计两个实现，不新增第三个。

E1定点修复现已实际派发：授权243821a，gpt-6-astra/max，原生新轮次ACTIVE；已告知R1继续冻结79a15d9独立审查，不等待或混入修复。原始证据不变，最终R1报告到达后再把原SHA及剩余项交E1整合。当前恰有T1/E1两个实现，R1仅CPU；没有新GPU或P04派发。

最新交接：T1完整修复候选ac8095faa58a98e143a8dc4d63042093e426feb0已非强制推送，原生completed/idle；S0核对11个本轮授权改动、159个未变原文件、8份原R1证据及22份日志/探针/结果hash。自测245个不同pytest检查、17组CPU数学与双Python CI34010040450通过。新R1-r2范围已准备，尚未独立签通过。

R1对P03完整79a15d9正式FAIL，原review f34f7c5a4eac54b18a2b092495f4ce8eaa334f98以该候选为父，只新增7份文件，146份候选字节不变；S0读取完整报告/反例并核验29份日志/探针/结果hash。309CPU通过，新54项49通过/5失败，分别为收尾stop写入和目录cleanup的两个P1，以及oracle事件因果顺序的一个非阻断P2。原生终态已确认；原FAIL不能按E1后来代码改写。E1 checkpoint2195b2e含fde181d修复和10项自测，尚未接原R1且未最终交接。已准备同轮累计2GiB的最终修复范围，明确加入semantic.py的F3路径，不含真实后端或输出协议变更。
