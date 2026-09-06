# P02-TRAINING-BINDING-R1｜固定训练选择与序列材料独立审查

状态：READY；D1完整候选f4f73c9已交付、远端一致且原生completed/idle。S0已核对最终交接，R1上一轮截止时间审查已结束；本范围等待原生派发。浏览器实际观察和kris人工判断仍未完成。

| 字段 | 本轮值 |
|---|---|
| owner | R1，既有独立Codex任务及隔离worktree |
| 精确被审候选 / code_base | `f4f73c9ac8e004b48a74a80ac00617a01c4da324` |
| candidate tree / parent | `ed7437bf371671a6a01efd324bb8bc1e2d63e294` / `bc9db40bc3d5a26b73b5f2e7dd308f1bb35be6f5` |
| 实现基线 / D1授权 | `36b6988af6b4e0125b59fb81b1cea142233e14a2` / `5d2c6b66421a47ee71d3b5d0d3c3892354b10512` |
| authorization_commit | S0原生消息给出的本文件完整协调提交SHA，切换前以git show读取并私有保存 |
| 新branch | `review/p02-training-binding-r1`，从精确被审候选新建，保留旧review/p03-ci-deadline-r1与全部既有refs |
| 模型 / 推理 | `gpt-6-astra` / `max`，不创建新任务或sub-agent |
| 契约 / 协作 | toolalign.contracts.v1 / coordination.v1 / plan-v0.1 / ADR-0019 |
| 交接 | `coordination/handoffs/P02-training-binding-review-r1.md` |

先读本授权的AGENTS、PROTOCOL、PROJECT_STATUS、本文件、[原D1任务](P02_TRAINING_BINDING.md)、[S0配置原件](P02_TRAINING_BINDING_CONFIG.v1.json)、ADR-0019、docs02/03/16和[S0交接核验](../../reports/S0_P02_TRAINING_BINDING_HANDOFF.md)。随后读取精确候选的完整diff、D1交接、VERIFICATION/EVIDENCE与两份生产模块/测试/公开检查器；不要依赖旧任务聊天或把准备状态误当成已派发。

## 所有权与证据

只允许新增 `reports/review/P02-training-binding-r1/` 下审查说明、去敏证据索引和必要小型独立探针，以及本轮交接单。候选350文件全部只读，包括新增配置、manifest、两个生产模块、原测试及所有旧报告/审查；不修改实现后签PASS。依赖/锁/CI、协调/ADR、其他worktree及所有既有私有文件只读。不得将未去敏旧f708审查作为公开祖先；不reset/rebase/force-push，不合后续main或其他候选。

D1候选仅新增13文件，337份基线和346份bc9实测文件保持。S0于12:55 UTC核对3692个实际文件路径，包括本轮1906份封存制品/32条命令、旧620/37及542/39、350份候选字节和实际归档/安装记录；集合有重叠，不相加为测试分母。S0证明SHA `b3b42cbc64c61590487acbcb4d738cce2dcc493c187e7ffe0860b07aaf1e7cf8`，D1最终completion SHA `4b6467b2ddc97abdbc7684db28bf7e6a8f31252e132f568d8a756db3810b419c`。私有路径由S0原生消息提供，读取原件但不执行会写回D1目录的辅助脚本。

## 独立验收问题

1. 核对实际配置逐字节等于S0原件，hash `579d3d9d9436f4374e7e808dc5b787213157d7ee477bfffd48dac02d35e70a4c`、training_authorized=false、CPU_PREPARATION_ONLY保持。固定data/表示/audit/descriptor/protocol与历史测量身份、当前消费身份分别对应实际字节。输入不是可执行配置，不允许数据驱动导入/回调。
2. 原train7515/validation234与历史audit逐例绑定是否完整，错身份/source/split/重复/缺失/额外行和错误结构必须失败；严格整数/成功flags/P+C+EOS/response含EOS/raw边界不能只看budgets布尔值。最终test/ood_test只识别split后跳过，不参与选择、统计或参数决定。全文件hash保全不等于使用其内容训练。
3. 以独立小型正负探针检查seed42固定canonical排名、打乱输入不变、smoke1600无放回、formal全部合格、各split子集关系、原字段/group不改、最小padding桶和完整互斥排除。实测1536/2048及response含EOS256边界和失败保留；P+预留256只单列统计，不增加筛选条件。核对S0先于交付计算的预期与D1两次真正物化的完整身份/字节/调用时间；无需再次物化原始大数据来重复既有确定性证据。
4. 独立核对实际smoke1600/197、formal6013/217与分母/排除；同一Example跨profile不增加独立来源数。两份稳定manifest均eb4bbfe6、运行元数据分开。完整输出字段、sidecar、原audit和当前consumer源码/包来源绑定，verify应拒绝输出或输入篡改。至少在新私有目录运行必要的原创小输入/异常入口，不改原产物。
5. 对13例材料核对10条不同真实已选train及3条单列原创final/clarify/refuse协议例。原数据目标全为tool_calls，3条协议例不得进入实际选择。核对真实CPU参考/native来源、主要profile、三文件模型来源hash、P/C/全IDs/EOS/causal shift/有效监督和右padding；10例须对应历史audit。可在自己的新私有输出目录对这同13例执行必要的真实两engine独立对照，每engine最多13例，不全量重跑8228行；重复engine不增加独立13例分母，不加载模型。
6. 静态核对HTML对原文/完整数组/单token辅助文字的正确转义、完整表格、不可执行数据和独立空白review副本。原browser URL安全策略拒绝回执必须保留，实际渲染0页/NOT_RUN；不得换浏览器、文件URL、localhost服务器、代理、raw CDP或间接执行绕过相同导航限制。可以读取HTML/JSON做静态检查，但不能将其写成实际页面观察。原D1页面观察要求仍未满足，不能静默删除或以CPU PASS关闭。
7. 在精确候选实际运行适用完整CPU回归和新增独立探针，保留命令、源码来源、失败/跳过与过程清理。D1的844+60+2=906 passed / 2 HF-only skipped是其自测；新增63例已在844组内，不重复相加。四条原失败完整保留：HTML断言、ruff、缺psutil收集exit2、错误私有启动器导致spawn/私有basetemp前提失败并中断exit2；检查最终私有runner的main保护和系统临时目录。不要修改原测试或全局收集绕过。
8. 新增两个生产模块实际进入可安装包。核对本次真实sdist107份Git输入+PKG-INFO、默认wheel/显式sdist重建wheel各49生产文件+5metadata、完整RECORD/依赖/隐私边界，以及bc9到最终f4的字节映射。独立验证必要的新接口来自默认wheel隔离target，纯默认依赖可导入而可选tokenizer/model包不可导入；真实tokenizer测试单列。分别记录实际构建、既有归档解析、安装和未运行路线，不能借旧包或源码cwd证明新wheel。

Ruff、冻结契约和公开内容扫描必须通过。测试应针对本次实际边界，不重开已验收P01/P03/共用格式整包，不引入通用框架或额外产品功能。

## 人工、资源与交接边界

已向kris发送原语义和新13例token/mask请求。人工填写副本仅reviewer/verdict/reviewed_at_utc/notes允许本人修改，case_id/category等身份列及13份JSON/HTML不变；reference/native冻结副本全部只读。人工manifest记录的是初始空白CSV hash，合法填写不能自动判成制品损坏。R1不填字段、不代签语义或视觉判断；实际页面观察及两项人审保持PENDING。

仅CPU，复用既有纯CPU/纯tokenizer环境及已核验本地来源；路径由S0私有提供。使用-B/PYTHONDONTWRITEBYTECODE=1，测试basetemp放系统临时目录，避免私有目录名改变原测试前提。默认wheel安装target是本轮新私有目录，依赖只读复用，不创建新解释器环境或下载/安装新依赖。新增私有制品上限2GiB。无模型加载、GPU租约、训练、正式评测/BFCL、费用、公网或模型数据上传授权。

输出明确PASS/FAIL/BLOCKED及P0/P1/P2，注明结论适用于CPU代码和可复核材料的范围，单列未完成的实际页面观察/kris判断，保留原任务全部缺项。给出精确candidate/review commit/parent/tree、真实命令/UTC/退出码/日志hash、来源/制品身份、失败/跳过与NOT_RUN。完成允许的审查文件及交接后结束，等待S0验收/普通集成。R1技术PASS不自动关闭P02/G-DATA、P04真实trainer/collator检查、模型容量、最终CI或main验证。
