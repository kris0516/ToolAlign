# S0 P02训练绑定交接核验

2026-09-06，D1完整候选为 `f4f73c9ac8e004b48a74a80ac00617a01c4da324`，tree `ed7437bf371671a6a01efd324bb8bc1e2d63e294`；work/p02-training-binding干净且远端一致，原生任务completed/idle。状态为READY_FOR_REVIEW，浏览器实际观察和kris人审仍待完成。本记录是S0交接核验，独立R1结论尚未产生。

候选仅新增获准13文件，337份已验证36b6988基线文件全部保持；两份新生产模块及对应测试/检查器在526f93d，package检查器在bc9db40。最终f4与bc9的346份实测文件逐字节相同。配置仍是S0原件579d3d9d，training_authorized=false。

12:55:03–12:55:12 UTC，S0只读检查实际exit0，8.78秒，核对3692个文件路径。证明SHA-256 `b3b42cbc64c61590487acbcb4d738cce2dcc493c187e7ffe0860b07aaf1e7cf8`；脚本SHA `6bc69a2dd2c31e71ac2f2bfc20ed00679adc46dac9e1b68e624abb0dd107b5f6`；原日志SHA `bd5c0787d6c0d4c86f751080e5f3cb649e7fa26c86bfd18125503ba7f834beee`。

| 核对范围 | 实际结果 |
|---|---|
| 最终封存 | completion 4b6467b2：350候选文件、1906本轮私有制品、32条完整命令及原日志 |
| 历史保全 | 原format-v1-r2的620制品/37命令、format-fix-r3的542/39；原两构建各18制品和audit字节保持 |
| CPU原始证据 | 844 passed/2 skipped、60 passed、2 passed三组实际调用、完整日志和346源码快照匹配bc9；合计906/2为D1自测，S0本次没有重跑测试 |
| 失败 | 四条D1原exit1/1/2/2及失败私有runner保持；先前观察到的12个自有进程当前均不存在 |
| 实际归档 | 直接解析sdist108成员、默认/显式重建wheel各54成员；107 Git输入、49生产文件、metadata与所有RECORD匹配最终f4 |
| 安装原始证据 | 本次默认wheel的4条实际安装/接口命令及stdout/stderr核对，49目标文件与17个已导入模块hash匹配；纯默认依赖隔离路径与-B/-I/-S启动器已读 |
| 资源 | D1封存新增私有制品、日志和保留成功测试目录共296367146 bytes；成功临时目录实际143221951 bytes，低于2GiB |

以上集合有重叠，不能相加为独立文件或测试数。归档默认/重建wheel全字节一致SHA `86adee698e490871894f2670d427e83617071b2a2c08c2f7d25cb3f7405bb1ec`；sdist SHA `6bf81574cace92a9e3734cc8790a47818e05534d5c033951b0477a456e84d431`。本次S0新build/install/tokenization均0，读取的是D1实际产物与原日志，不刷新其测量时间。源码直接wheel仍NOT_RUN。

S0此前独立计算选择预期、核对两次真实物化和13例两engine既有完整数组/静态HTML，见[先行参考与核验](S0_P02_TRAINING_BINDING_REFERENCE.md)。本次再次核对全部冻结制品，未重新物化原始数据或重跑8228行encoding。smoke1600/197与formal6013/217保持；原真实目标全为tool_calls，3条协议例没有进入训练产物。

S0读取元数据摘要时曾直接索引早期intake没有的finished_at_utc而得到KeyError；原记录有实际start/elapsed，后续检查按实际字段处理。该只读检查错误已登记，不修改D1证据，也不记为候选缺陷。最终独立核验脚本第一次实际运行通过。

12:55 UTC，语义填写副本100行、token/mask副本13行均0 reviewer/0 verdict。新13例请求已实际发送，原语义请求仍待答复。允许本人填写人工字段，身份列/JSON/HTML和reference/native冻结证据保持；初始空白CSV hash不作为拒绝合法人工填写的条件。

原浏览器file URL导航被URL安全策略拒绝，并明确禁止绕过；完整回执b2abc9c6已核验。实际渲染0页/NOT_RUN，静态检查不能关闭代表/最长/非ASCII页面观察及kris判断。原任务此项要求仍未完成。[R1审查范围](../coordination/tasks/P02_TRAINING_BINDING_REVIEW.md)保留该缺项，技术审查可继续。最终CI/main、G-DATA、P04真实trainer/collator、0.6B/1536容量与GPU授权均待对应门槛。

13:03 UTC，S0在R1原生旧轮completed/notLoaded、干净1531892及D1终态再次核验后，按完整5b553b4b7140f4e62209c904bc0b79e94dff8600实际派发精确f4独立审查，gpt-6-astra/max；原生新轮ACTIVE已核验。分支intake和审查结论仍待交付。

13:12 UTC，R1实际新分支review/p02-training-binding-r1位于精确f4，旧1531892审查分支保持；S0核对350份当前候选/Git/私有索引，以及13份授权副本与精确5b553b4的字节一致。R1任务身份、模型/推理、candidate/parent/tree相符；证明SHA `c48dfbdbc87ce0be374bc769d36cf3715d14ef1d7157cca6a44914950f65ece1`。这证明审查输入已正确接收，独立结论尚未产生，原生同一轮持续ACTIVE。

[Draft PR9](https://github.com/kris0516/ToolAlign/pull/9)已建立，精确head为f4f73c9、当时base为18674a2。[候选CI34035350180](https://github.com/kris0516/ToolAlign/actions/runs/34035350180)的Python3.11/3.14两个job各14步骤全部成功，每个job实际550 passed/48 optional-tokenizer skipped，另46项P00审查通过；48项跳过均因CI未提供私有真实tokenizer来源/依赖。两个Python重复执行不增加独立测试分母。

CI实际检出GitHub合并对象 `3e1e96eb8369125629faa6d497446961ef8b533a`，tree `036f09fd8e82f46dec5238b014f916b3a70a0bd7`，父分别为18674a2和f4f73c9。S0实际fetch该对象，13:17:55–13:18:02 UTC核对全部356 Git文件和完整CI日志：343份当时main文件保持，增加13候选文件；候选共享的10份较旧说明由main中的S0状态/规格更新替换，全部src/tests/configs及107 sdist输入/49生产包文件与候选一致。证明SHA `83601672630688c5ceb8f3a8843a1b25a1ef3bbbb7edc290ec6004924e329b8a`；实际检查exit0、7.30秒，日志SHA `f5c0afdafc7850a433d4c380fe22cff45735546d30b4ad6f46304d525ff58069`。

完整CI解码日志按实际UTF-8逐字节保留：Python3.11为28598 bytes/SHA `84ad4b4df24a1bbcebaadfebb81f596efc5751e92bebe07a4c249185025cd821`，Python3.14为28485 bytes/SHA `6d698cd423bd7ab48f4c38ad17f9f26c6a0e684d4cd82197a89b7da0e64d4213`。lint、4契约和356路径公开扫描通过；既有归档canary探针实际检查241私有canary被排除、18公开fixture保持，覆盖sdist/direct/rebuilt路线。这是CI探针范围，不改写D1普通包的默认构建路线或其源码直接wheel NOT_RUN。

首次S0只读合并映射检查误把所有共享说明差异限制为AGENTS/BOARD/PROJECT_STATUS三文件，实际还包含先前七份S0状态/规格更新，因此断言exit1；原输出/断言已保留。随后按完整实际diff明确十份说明文件、分别验证所有候选生产/测试/配置与包输入未变，得到上述独立成功记录。未修改候选或CI，也未重跑工作流掩盖失败。

PR9保持Draft，候选CI不替代R1独立审查和后续最终组合CI/main验收。浏览器实际观察、两项kris人工判断、G-DATA/P04门槛继续保持未完成。

14:13 UTC后续：R1原审查40252f8对精确f4正式CPU PASS/P0/P1/P2均0，原生completed/idle；S0核对5734路径/26命令和最终封存核验通过，普通集成0f3d04f实际919CPU/2跳过及新归档/默认安装通过，详见[新的集成记录](S0_P02_TRAINING_BINDING_INTEGRATION.md)。上文保留候选阶段的原时点与失败；PR9最终CI/main、实际页面及两项人审仍待完成。


2026-09-06主干补记：训练绑定已随[PR9](https://github.com/kris0516/ToolAlign/pull/9)合并42eaa50并完成最终双Python CI与main919CPU/2 HF-only skipped、现存三归档及49份安装包载荷绑定，CPU技术范围VERIFIED；原R1 PASS40252f8保持。见[本次主干证据](S0_P02_TRAINING_BINDING_MAIN_VERIFICATION.md)。smoke1600/197及formal6013/217现在为已物化并核验的训练绑定；本文件中的旧候选/算术/待验记录保留原时间。实际材料页面观察、kris语义/token-mask判断及P04实际trainer/collator、尾批/checkpoint/容量与正式训练仍待完成。
