# S0-P04-DATA-V3-INTEGRATION-r1

- 状态：隔离组合 PASS，PR19 最终 CI/main 待验收。
- 基线：`40974f3e1ad1d6cca4d4d7d917487bcd7af3008f`；组合：`3a5c90803be5b750773bb46b04101b7de83466a2`。
- 分支：`codex/s0-p04-data-v3-r3-external`；契约：plan-v0.1 / coordination.v1 / toolalign.contracts.v1，ADR-0026–0029。
- 影响：合入原数据候选、三轮原审查与交接；S0 未改生产实现，本次仅新增本交接和集成报告。
- 原 R1：`f2f11e04a94cebb0ad658851d4e22a8452180556` PASS，旧 b99a644/58212d2 FAIL 保持。
- 验证：原1,135通过/1目录上下文失败/48跳过，单项换目录1通过；不重跑旧成功。三归档147/71/71成员、66安装包文件、76 RECORD行，安装I/O六项与无租约守卫通过。
- 封存：3,399文件/218链接/7 FIFO仅lstat，证明 `04fc2a58e365f03a3b391451a05b5d2a465e8862319a6576320c52bc515f1d52`。
- 失败与限制：原失败/fixture完整保留；新增真实数据/编码/模型/框架/GPU/训练为0。

完整原命令形式、安装隔离与限制见[集成证据](../../reports/S0_P04_DATA_V3_INTEGRATION.md)。后续只有最终 CI/main 验证后的提交可作为运行 CPU 实现基线。
