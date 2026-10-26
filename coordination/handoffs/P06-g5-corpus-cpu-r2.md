# P06-g5-corpus-cpu-r2 交接

2026-10-27，D1；`READY_FOR_REVIEW`。基线 `5c859cbb59c808ba941ec89a85fcf8f22e19d888`，实现提交 `3206fbc49ffe126ea653006306a1edc9c1700583`，分支 `codex/d1-p06-g5-corpus-r2`。最终交付提交在回报及私有 evidence index 登记；实现提交之后只补本交接和[报告](../../reports/P06_G5_CORPUS_CPU_R2.md)。

新批次恰为 28 个已检查 ID，四域各 7 题、4 family、4 个真实连通组、8 个恢复题。分组和长度隔离均为 0。原 48 题及其完整历史组件永久排除，001/002 仍待 Q1 正式复验，连续未通过计数各 1；本交付不维护共享状态或关闭问题。

R1 代码预审的 3 项独立检查及 6 个 child 回收已由 S1 接纳；D1 核对 59 份预审产物和 18 份当前源码，记录于 `code-review-adoption.json`。最终语料审核仍为 `PENDING`。S1 已按本文 tasks/manifest hash 派发 R1/Q1，最终输入和 92 条轨迹保持原字节。

| 验收入口 | 实际证据 |
|---|---|
| `package/tasks.json`、`authored-task-inventory.json` | 28 题固定顺序与全部已检查 ID；没有额外筛选池 |
| `cpu/summary.json`、各 `result.json` | 36 正向成功、56 反例失败；216 owned child 回收，200 次合法 raw Action |
| `delivery-checks.json` | 36 个合法策略/答案组合逐一重评分；16 条预提交旧 v1 成功而新版失败；8 条实际观察派生参数、8 条恢复、8 条观察后澄清历史核对 |
| `semantic-review-input.json`、`truth-checks.json` | 全部 78 道可读旧题的比较、28 道新题关系依据、所有等价策略和独立算法作者复算；待 Q1 |
| `package/group-audit.json`、原完整 reference | 3,623 节点/1,923 边/3,510 组件，851 历史边完整继承；全部 3,595 旧节点组件保持 |
| `package/length-audit.json` | 28 初始与 84 合法历史输入；最长 1,334，加 256 为 1,590；completion 含 EOS 最长 67 |
| `plans/`、`model-input-projections.json` | 当前 G5 reader 实读；56 个 M0/M1 主单元、8 个 A1；原 A2 的 8 序列单元/24 请求；投影只有 messages/tools |
| `source-identity.json`、`intake.json` | 120 份源码/测试/依赖文件绑定；332 份原证据 hash 与字节数未变；旧 v1 全部 48 任务身份重建一致 |
| `logs/` | 实际 argv、退出码和完整输出；34 项受影响测试、定点 ruff、构造/CPU/长度/交付复核通过 |

最终 L1 tasks SHA 为 `a645b445d37a66522c39d83d110b6384abe8e0e93b15ad4ff8b208eb7eb2b54f`，package manifest SHA 为 `a22e820e82f5e2addbf52e2c20d2b58c07cef4fd168da6860eb95bd3349bff04`。原 A2 inputs SHA 保持 `ec282f4779deca1815af39e2c68c846e831c184965318f3550eeaff973d03166`；未生成新回放材料。当前 reader SHA 为 `a637bdbc7c5cb7fbea0929fb80a4226b97744df5962d018da4a72b2136ac3d0f`。

公开改动仅四个实现/测试文件、本交接和报告。旧工具、oracle、backend、contracts 与依赖不变；实现提交后源码字节未变，因此复用 34 项测试记录。原 48 题的失败及隔离证据单独保留，不并入新批次成功数。R1 审核技术接口和证据，Q1 逐题复验语义/分组及 001/002，S1 决定接纳、合并和正式输入冻结。固定模型推理、GPU、训练和 A1/A2 性能均为 `NOT_RUN`。
