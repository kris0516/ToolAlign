# P04-SFT-DATA-V3-review-r2 交接

**FAIL；P0=0、P1=0、P2=1。** 精确候选 `1769046468eb2ebfdd9e982ba4938833760e3fe0`，tree `1373bd4c838a1af395a1ede4f7c4d7029ffad271`，直接父 `53d86109f18e4131cff1ddcb905086892580d136`，原始候选 `f3b7f1a1abb23cce3bdccb74ddc6d2e0477bb2aa`。R1 沿独立任务/隔离分支 `codex/review-p04-sft-data-v3-r2`、gpt-6-astra/max，按完整授权 `1cb1b0a6ffc157edcb53b41f21cef883f4729d13` 复审；没有修改被审实现/测试/配置或 S0 台账。

原 F1 无 writer FIFO 阻塞已通过修订验证，建议单独关闭。新 **P04-SFT-DATA-V3-F2 / P2**：预检查后的目录替换使 `os.open` 成功而 `os.fdopen` 构造抛错，留下 1 个 FD。拒绝及时；长生命周期调用方可捕获错误后重复尝试，模块没有清理或重试限制，存在累积耗尽风险。一次残留已实测，循环耗尽仅据源码推论/NOT_RUN。当前子进程均回收，最小观察主动关闭了自有残留 FD；不能据本次生命周期把生产缺陷降级。原代码已有该路径，但既有事实不决定严重度。

完整判断、修订建议与边界见[审查报告](../../reports/review/P04-sft-data-v3-r2/README.md)，SHA `7229be63d9a845cd6c83e4ee0627543d799f77bb611c56375259d55989ecfc3b`；[结构化证据](../../reports/review/P04-sft-data-v3-r2/verification.json) SHA `475774ab508dea907be81d92281355f9a582dd8a57b224e4dc6640aecae9b9e5`。相关模块一次147 PASS；补充原创检查一次5 PASS/1 FAIL，原FAIL不改写。未修改f44 probe源/新target各一次均及时拒绝、无writer、child exit0/reaped。最小目录观察独立确认缺陷，无实物调用。

实际三归档及构建时点、65包文件/metadata/entry/LICENSE/完整RECORD通过；只离线安装已绑定wheel一次，复用五个旧默认依赖。新target外部cwd、`-B -I -S`，32已加载ToolAlign模块来源核验。唯一固定prepare1及13例组1成功：609输入、四view7,928原行/rank、13例两engine26完整记录逐字段/类型、所有IDs/mask/causal/padding/EOS/token_texts保持。

新导出2,030,656B SHA `4c261560f3e27842d1cad0fce16220c8073df8a35a9592c4526c61f64a5a738c`；唯一变化是CPU consumer的data_v3模块hash，等于执行前冻结预期。旧导出9b711与原T1当前修订NOT_RUN历史保持。Ruff和契约通过；公开/差异、精确review/tree/parent、普通推送与终态seal由最终原生回报给S0。

原bdebe模型review/完整scope、旧b99正式FAIL、20原模型stat-only、全部旧FAIL/PASS/root identity、30文件/1链接缺失例外及等字节封存保持，私有f708不进入公开祖先。原特殊节点不打开/hash；本轮新普通/链接/特殊节点分开封存。自身辅助失败与目录原FAIL均保留，不增加或代改正式counter。

建议S0对原F1关闭与新FD-lifetime发现作独立去重登记并派限域修订；R1不自行判定台账轮次或暂停整体目标。本候选尚有P2，不建议验收/合并。所有新安装/原probe/固定消费额度已用尽；新build、编码、框架、模型/GPU、优化/生成、业务API、浏览器、费用和上传0。真实trainer/容量/正式训练/评测/服务仍NOT_RUN。

本审查提交应以完整1769046为唯一parent，仅新增本交接单及审查目录；完整SHA/tree/parents和私有终态索引在commit/push后交付，文件不伪造自引用SHA。普通推送并交付后本轮结束，等待S0新明确范围。
