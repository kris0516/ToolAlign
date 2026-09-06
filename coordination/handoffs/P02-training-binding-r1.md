# P02-TRAINING-BINDING｜r1交接

Owner D1；独立任务、隔离分支 `work/p02-training-binding`；gpt-6-astra/max。状态：**CPU候选交付，浏览器实际观察缺项，等待独立R1与人工检查。** 未修改看板、ADR或其他任务状态，训练授权保持false。

基线 `36b6988af6b4e0125b59fb81b1cea142233e14a2`，授权 `5d2c6b66421a47ee71d3b5d0d3c3892354b10512`；契约plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / ADR-0019，docs02/03/16。父关系为36b6988 → 实现/选择测量 `526f93d4e0878365a6748c593b3e685b9a395384` → 包检查器/组合验证 `bc9db40bc3d5a26b73b5f2e7dd308f1bb35be6f5` → 本次仅文档与manifest的最终提交。最终完整candidate SHA由普通推送后的原生回报及私有completion登记；不以缩写替代精确审查对象。

仅新增授权13路径：2个data模块、2个测试文件、2份原创fixture文件、固定配置、2个公开检查器、公开选择manifest、验证报告/证据和本交接。原337文件、data/model_io/P01/P03、旧报告/审查/锁/配置保持。旧本地work/p02-data仍为8c439f6；未reset/rebase/force、未合main或未去敏review f708。

- 实际选择：smoke train1600/validation197；formal6013/217。smoke合格train3618，排名排除2018。原分母train7515/validation234；固定seed、所有原字段/值及split/group保持，smoke分别是formal子集。
- 两次独立build的13稳定文件相同。配置文件SHA `579d3d9d9436f4374e7e808dc5b787213157d7ee477bfffd48dac02d35e70a4c`；私有选择manifest文件SHA `eb4bbfe66966d95fb3a77126e4b3ee248faa66db587422846421e25b7a8242bd`。
- 13个独立材料样例：10个实际选定train，另3个原创协议例不入训练；两engine共26次材料序列构建，完整记录一致，10例全匹配历史audit。真实目标仍全为tool_calls，非tool_calls不冒充真实标签覆盖。
- CPU三组实际906 passed/2 HF-only skipped，含63个新增原创测试；全库lint/4契约/350路径公开扫描通过。三份实际归档、49份包源码/资源和4条默认wheel隔离安装/接口命令通过。
- 保留4条已记录验证失败及全部原日志，含缺psutil、私有启动器main保护/临时目录问题；最终修正后组合通过，不修改既有生产或测试边界。原输入、人审材料和旧失败末次hash保全通过。

详细计数、互斥排除、保留响应空间差异、完整归档hash、命令/时间/环境、历史与当前loader映射见[验证报告](../../reports/data/P02_TRAINING_BINDING_VERIFICATION.md)和[机器证据](../../reports/data/P02_TRAINING_BINDING_EVIDENCE.json)；[公开manifest](../../data/manifests/training-selection.v1.json)没有原文、逐例IDs或token数组。精确机器路径/原始日志/逐例绑定通过本机交付给S0，不进入公开Git。

**浏览器渲染观察NOT_RUN，用户人工检查未完成。** CUA本地页面导航在2026-09-06 12:20:01.467Z发起，12:20:01.593Z被URL安全策略拒绝，明确禁止间接或替代绕过；停止该路径，无重试。完整原回执JSON hash `b2abc9c609ccac06554e9a802a7dc3d382aec8c4f8bf7e6e8339f902a75c929e`，文字原件hash `57a5937c612587bc11865727fe56934cefedbfe41d2286047c9e0fafb2606b93`。S0已明确指示继续可做部分并如实交接缺项。13页、19968 token行及完整JSON的静态检查不代表浏览器或人工PASS；独立人工包manifest hash `a4681bb8370d5225839913ea6b9f7726c1145af7bdbe6d63edb950b9379187b0`，13行review字段全空。

请R1独立核对精确最终SHA、固定输入/选择身份、失效反例、真实HF/native字节、归档与隔离接口，以及上述未完成边界。后续实际页面观察、G-DATA语义人审、token/mask人审、P04配置/GPU预算与0.6B/1536容量预检不得由本候选代替；模型加载/训练/生成/最终集/BFCL及实际trainer/collator梯度验证均NOT_RUN。普通推送新分支后D1结束本轮，等待R1/S0。
