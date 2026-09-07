# S0｜固定 Qwen CPU 接口独立审查接收

**ACCEPTED（CPU 技术）**。独立 R1 对完整候选 `01eeb74d1bce3c3a3c41d84575d4d706e246e818` 正式 PASS，P0/P1/P2 均为 0。原 review `bdebe4c2bddf927995a6c15124fab75ad04ba5de` 已普通推送，2026-09-07 22:06:02 UTC 原生 completed/idle；S0 于 22:10:52–22:11:01 UTC 完成实物接收。隔离集成、[PR17](https://github.com/kris0516/ToolAlign/pull/17) 最终 CI 与 main 验证尚待完成。

审查遵循 plan-v0.1 / coordination.v1 / toolalign.contracts.v1、Action JSON v1 与 ADR-0027，真实独立对话使用 gpt-6-astra/max。review tree 为 `9cfaad151f216fb3298a899d7a0fb2399e393a38`，唯一 parent 为原 candidate；授权为 `9a29a72f9c418ff5c18c12f0065eae4f311aa3ec`。候选 623 文件不变，review 仅新增四份审查文件及对应 handoff，共 628 个公开文件。S0 已保留逐字快照，原 SHA 不改写。

S0 核验 **90,442 条文件路径、1,664 个不跟随的链接、4 个仅 lstat 的 FIFO、3,693 项 Git 字节绑定**。计数含旧保全与新证据，不能相加为独立测试覆盖。完整证明 SHA256 为 `28593f448e1197711a6a9f9d8604c58d7c30ced54f7d0890812e7eb0771da890`。

| 接收范围 | 实际结果 |
|---|---|
| 正式结论 | [R1 报告](https://github.com/kris0516/ToolAlign/blob/bdebe4c2bddf927995a6c15124fab75ad04ba5de/reports/review/P04-qwen-model-r1/README.md)、[交接](https://github.com/kris0516/ToolAlign/blob/bdebe4c2bddf927995a6c15124fab75ad04ba5de/coordination/handoffs/P04-qwen-model-review-r1.md)：精确 01ee 的 CPU PASS，P0/P1/P2 均 0 |
| 原始命令 | 23 条实际 recorder 调用、argv、UTC、exit、完整日志与源码时点逐项绑定；另核对最终关闭调用的实际 exit0、review/tree/parent 和 envelope hash |
| CPU 测试 | 原相关 suite 120 passed；R1 原创 14 passed，含 7 个有界 I/O child、2 个完整参数映射推导和 5 个字节模拟检查 |
| 进程与 I/O | suite 90 个 subprocess/1 个 fork、独立探针 7 个 subprocess 均回收；hash/read/header 的无 writer FIFO、symlink 替换及时拒绝，父目录 FD 替换未读到外部哨兵 |
| 固定输入与来源 | 42 项输入、E1 34 条原命令、20,862 份源码时点保持；另 3,142 项旧出处按原已接收证明绑定，不扩大 R1 读取范围 |
| 参数身份边界 | 两模型各 311 序列化叶，仅移除固定 `lm_head.weight` 后预期 310 底座叶；28 层 q/v 的 56 个模块和 112 个 FP32 A/B 名称、shape、映射完整核对，属于源码/header 推导与原创模拟 |
| 实际安装 | 一次离线 no-deps 安装；外部 cwd 的 `-B -I -S` 检查通过，65 个包文件、69 个未改 wheel 成员、75 条安装 RECORD、9 个 ToolAlign 模块来源绑定 |
| 固定模型文件 API | 每模型先 reservation，再各一次 `validate_model_files`；0.6B 9 文件/1.7B 11 文件通过。剩余安装/API 均 0，真实模型没有加载 |
| 旧证据 | 原 b99 数据 FAIL、counter、旧 PASS/FAIL、根身份和私有 f708 边界保持；30 文件/1 链接原路径缺失及等价封存保持，未恢复成原件 |

最终 seal 为 27,689,877 bytes，SHA `17fe9b621357eeaea31b31483be55164fd26d1b8a017760a433fd4a301cf9671`；envelope 为 2,302 bytes，SHA `a8e4f84de6ff628d28b5aca9865da7f17b1f4e33d74a0ed44dfbc9aa2db35196`。seal 收集 22 条已结束命令，envelope 补绑第 23 条 seal-final 的实际 stdout/stderr/receipt；未封存仍在变化的日志。新 scope、独占测试目录、seal/tail/envelope 和五份公开审查文件共 120,250,494 bytes，低于 1 GiB。

原 sdist 144 成员、两个 wheel 各 70 成员、源码/metadata/LICENSE/entry points 与 RECORD 保持。三归档 SHA 分别为 `73ee4795ca39d81021b3eed1eb1ed4b8a9e9d3caf5899469e91cfd75f5f7e1cf` 与两份相同的 `117f74f92aad166aceb16336771ec4d4bf9f98e7ac6142fb0592d2c1246373d6`。65 个已安装生产包文件与候选逐字相同。

本次 S0 对 20 份模型文件仅核对完整 stat token 与原已验 hash/metadata 的绑定；未重新读取权重或调用文件 API。R1 的真实 loader、LoRA 装配/重载、tensor 值解码、tokenizer、forward、优化、生成及 GPU 均为 0；本次 S0 新 build/install、模型文件 API、模型读取、框架与 GPU 同为 0。CPU PASS 不认证真实驻留参数、容量或正式训练。

E1 原 006/007 非零、R1 原 native-audit 辅助失败和只读展示 KeyError 保持。S0 原两次命令接收脚本失败也保留：原生调用对两组已观察的有限 label 数组拼接命令，初版仅支持完整字面量，补齐这两种实际调用后 23 条全部绑定；候选和原消费未变，无新增正式问题轮次。

下一步由 S0 保留原 SHA 集成模型 CPU 包并完成最终 CI/main。R1 的[数据特殊文件修订复审](../coordination/tasks/P04_SFT_DATA_V3_NONREGULAR_REVIEW.md)已具备接续前提，由新精确授权单独激活。原数据 F1 连续失败仍为 1；G-DATA 冻结 v3 保持 PASS，真实容量、SFT/DPO、正式评测与服务继续 NOT_RUN，无需 kris 操作。
