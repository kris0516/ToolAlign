# P05 G4｜偏好 CPU 实现 R1 技术审核

状态：READY；owner R1。候选实现提交 `147d0450447a7ad543a7a913f2a9084b039b849d`，修改限于 `src/toolalign/data/preferences/` 和 `tests/data/preferences/`，共8文件。S1 已回读差异、私有输入和日志，核对8个源码/test blob与42项通过的测试运行逐字节一致；当前只是待审集成，未合入 main。

从 S1 派发的精确授权提交，在 R1 既有隔离 worktree 建 `codex/r1-p05-g4-cpu-r1`，与[生成器审核](P05_G4_GENERATION_R1.md)共用本次独立审查分支，分别给出结论。按 [G4协议](P05_G4_PROTOCOL.md) 和 [D1任务](P05_G4_PREFERENCE_CPU.md) 独立技术审查。完整20任务/12family/10类别/1group的语义审核由 Q1 同时进行；本任务不代替 Q1，也不验收真实模型偏好。

重点：固定计划和候选分母；任务/模型/实际 ModelInput/trace 的身份链；首分歧的当前语义错误与后续失败严格区分；合法替代、call_id与格式差异不误作负例；多步依赖有 prior observation 证据；每任务固定顺序最多1对；原始completion和双方采样参数保留；所有已知误标排除，Q1抽样/严格大于5%以原分母裁定，不删后重算或回填。

核对分组审计覆盖全部 advertised tools 和 P02 train/validation/test/ood_test、连通分量整体隔离、公开开发资料身份披露；原始任务私有化后的CLI与输入hash有效。重点检查枚举之外动作被错误判负的可能性。用独立的小型反例验证实际行为，复用未受影响的已有测试，不追求覆盖率或重复全部历史检查。真实CUDA、模型、偏好和DPO保持NOT_RUN。

只允许自己的私有审查证据和公开 `reports/reviews/P05_G4_PREFERENCE_R1.md`、`coordination/handoffs/P05-g4-preference-review-r1.md`；禁止修改生产实现、数据、共享状态、依赖、GPU，禁止sub-agent/新聊天。不得将完整任务、原始轨迹、本机身份或私有路径写入公开摘要。

交付精确review commit、PASS/REQUEST_CHANGES、可复现实质问题与定点独立检查。S1按既有REVIEW_POLICY保留失败及修订；没有真实偏好池时不能登记偏好质量或DPO放行。
