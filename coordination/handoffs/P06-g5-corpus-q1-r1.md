# P06 G5 L1 语料与 A2 输入 Q1 r1 交接

**REQUEST_CHANGES；A2 开发输入 PASS。** Q1 AI 已审核完整 48 题/23 family；[详细报告](../../reports/reviews/P06_G5_CORPUS_Q1_R1.md)绑定逐题判定、两项实质问题和反例。受检集成头 `2b47be95bc685e1ec11e99b8171d5b2a7d11e1ea`，D1 实现 `72b18ad9c47da4932857cb53400b6a3c9ead6aad`，D1 交付 `d4c4251a0e676d39f30c62c6c767f274987501ca`。

- **Q1-G5-CORPUS-001，P1，首次未通过建议计 1。** 8 条多步和 8 条恢复题的 oracle 未检查模型先收到观察再提交后继调用。两条独立真实反例把两次调用放在同一 Action，分别得到正常观察和真实 timeout 后的成功观察，均被误判 success。关闭时应让这两条失败，同时保持原分轮正向和等价策略通过；修订范围由 S1 协调。
- **Q1-G5-CORPUS-002，P1，首次未通过建议计 1。** 新旧缺参题存在字段/实体改名后的同一作答程序，作者未登记语义 family 连接。补入一条有据连接后，现有闭包将全部 48 题连到 P03/G4 旧组件，按冻结规则应保留 0、隔离 48。需保存全部检查过的 ID 与原失败，不通过删题或改组掩盖连接。原候选仍为保留 48/隔离 0，Q1 未改写数据。
- 答案值/类型与调用限制分项全部通过；执行语义分项 32 PASS / 16 REQUEST_CHANGES，隔离分项整组未通过。复用 99 条原 CPU 轨迹与 199 个回收记录；新增 4 条真实 CPU 轨迹、10 个 child 全部回收。152 条实际 tokenizer 测量身份核对通过，最长输入加预留 1,596。
- A2 四组三请求均来自 P03 开发资源，重复/不同请求顺序、tenant、seed 和输入身份通过，最长 1,299 tokens。此项只接纳固定回放输入；正式 cache 性能和模型输出仍 NOT_RUN。

私有 `evidence-index.json` 绑定 **203** 份文件，SHA256 为 `f53c050cd6847654836c943a6f74a82287817d81232960354f712b87fbe1aa6d`；目录位置及精确审核提交见交付消息。主要结果为 `per-task-review.json`、`family-review.json`、`probe-results.json`、`q1-semantic-bridge.json`、`q1-connected-group-audit.json`、`audit-summary.json` 和 `review-result.json`。逐题判定 SHA 为 `c1e33dd615ef88850836393028f924949f9d5b26c93eee423a2e9bc2a14c7db8`，最终结果 SHA 为 `c1e2135a3723c84413dacc368b7486b24d598cf03367856a9d139d3d79a3a53f`。

原 L1 tasks SHA 保持 `10a842b4a0c2d15470ba9d61e010621a8dc0807ce5a9e4c0cc552b994b67d70e`，A2 inputs SHA 保持 `ec282f4779deca1815af39e2c68c846e831c184965318f3550eeaff973d03166`。本轮仅提交报告/交接，未改生产实现、工具、候选、P02 分组、配置、依赖或共享台账；未分配 GPU、加载真实模型、训练或生成偏好。两项均为第一轮，交由 S1 接纳并按现有政策自主处理，不触发整体暂停。
