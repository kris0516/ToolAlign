# P06-g5-corpus-q1-r2 交接

2026-10-27；实际审核者 Q1 AI。**PASS：28 题逐题通过；Q1-G5-CORPUS-001/002 各自正式复验 PASS。** 建议 S1 回读接纳后关闭两项问题、连续计数各 1→0，保留原 r1 REQUEST_CHANGES。Q1 未改共享状态。

审核分支 `codex/q1-p06-g5-corpus-r2`，起点 `60ba22de5c39e9305dfc9a21d7cd3c4766e23645`。D1 实现 `3206fbc49ffe126ea653006306a1edc9c1700583`，最终交付 `32bc19cd4e767ac730b059ba7d70d9f5610d68d5`，S1 文档集成 `3433d3c0ab8e19b12256f174dff7bb2244cc216e`；后续已接纳 R1 技术报告 `bb4fc2764b5525282f4af769ca1597bc60565cfa` 不改变输入。精确 Q1 提交与总索引 hash 随回报给出。

| 入口 | 内容 |
|---|---|
| [Q1 正式报告](../../reports/reviews/P06_G5_CORPUS_Q1_R2.md) | 两项稳定问题的独立结论、逐题判定矩阵、程序比较及实际验收范围 |
| 私有 `semantic-review.json` | 全部 28 个 ID、逐题计算依据、32 个答案变体/32 个策略、合法选择枚举及 78 个旧程序比较 |
| 私有 `group-review.json` | 3,623 节点/1,923 边记录/3,510 组件；新四组各7题、无旧连接；旧48题所在78节点组件永久隔离 |
| 私有 `trajectory-and-input-review.json` | 92 条复用轨迹重评分、200 次输入/Action、216 child、112 行长度及 M0/M1/A1/A2 绑定 |
| 私有 `fresh-probes-summary.json`、`fresh-probes/` | 3 条真实 scripted CPU 轨迹；合法等价顺序成功，两条预提交失败，9 child 全部回收 |
| 私有 `r1-final-adoption.json` | 同一输入的 R1 历史重建与独立 tokenizer 复算证据，已核对所用文件和最终索引 |
| 私有 `review-result.json`、`evidence-index.json` | 结论、建议台账事件、精确文件 hash/长度及公开交付绑定 |

私有根为 `.toolalign-local/review-p06-g5-corpus-q1-r2/`。D1 最终 208 份私有文件及 6 份公开交付绑定通过；本轮复用全部原轨迹，独立新增三条有区分力的 CPU 检查。初次审核脚本的节点顺序差异及其修正日志保留，不计作语料失败轮次。

冻结输入仍为 tasks SHA `a645b445d37a66522c39d83d110b6384abe8e0e93b15ad4ff8b208eb7eb2b54f`，manifest SHA `a22e820e82f5e2addbf52e2c20d2b58c07cef4fd168da6860eb95bd3349bff04`。初始/历史最长 970/1,334 tokens，历史加256为1,590；原 A2 SHA `ec282f4779deca1815af39e2c68c846e831c184965318f3550eeaff973d03166` 不变。主计划56单元，A1为8单元；新28题保留、分组及长度隔离均0，原48题没有恢复资格。

公开改动仅本交接和报告；没有生产、语料、图、依赖、BOARD、PROJECT_STATUS、DECISIONS 或失败台账变更。固定模型推理、GPU、训练、正式评测和 A1/A2 性能均未执行。下一步由 S1 接纳、登记与冻结输入，再按已授权协议推进后续阶段。
