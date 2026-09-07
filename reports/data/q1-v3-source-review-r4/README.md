# Q1-P02-v3-sources-r4：两个固定来源的独立语义审核

结论：`PASS_SOURCE_SEMANTICS_ONLY`。两个完整来源、三个有效决策及六个工具调用均通过；建议保留原来源和全部三个原 Example 身份，无新增隔离或问题建议。结论由独立 Codex-AI(Q1) 在 `gpt-6-astra` / `max` 下作出，不代表 kris 人工签字。

本轮仅审来源语义。冻结输入时尚无 v3 数据候选，本审阅也未绑定后续候选。`P02-Q-081` 仍为 `CHANGES_REQUESTED`、连续未通过计数 1；本轮不修改其状态或计数。v3 排除结果、token/mask、浏览器和 G-DATA 需由 S0 冻结实际候选后另行验收，`training_authorized=false`。

## 固定身份与范围

| 项目 | 精确值 |
|---|---|
| Task | `Q1-P02-v3-sources-r4` |
| Code base | `d3e56f68ebd67cc576d912b6f06636682b4170ab` |
| Authorization commit | `3e18145b66baa7bce498926869b2d52bd0503453` |
| Review branch | `review/q1-quality-v3-sources-r4` |
| Input manifest SHA-256 | `7d9ad0102b965a75071032d5be3e60dd1a91c09894a739ed852952c1ebbcfd2c` |
| Source context SHA-256 | `31f7c9bf7b72721492166bba97f4da1999a153f24894ac335ccc4132aff75161` |
| Q1 config SHA-256 | `4cc29d682681ad0467833f9a7ff2ff9cc6d86a68e7aab896c43454532b96c3aa` |
| Previous Q1 review | `8a738abc1f9485e072b87283cdd9003329d3524a` |

按[冻结任务](https://github.com/kris0516/ToolAlign/blob/3e18145b66baa7bce498926869b2d52bd0503453/coordination/tasks/Q1_P02_V3_SOURCE_REVIEW.md)和[精确配置](https://github.com/kris0516/ToolAlign/blob/3e18145b66baa7bce498926869b2d52bd0503453/coordination/tasks/Q1_P02_V3_SOURCE_REVIEW_CONFIG.v1.json)，只读取八份冻结输入副本。两个来源由原代表材料算法投影选定，均沿用原 train/group 身份，无重抽样；两个目标对应投影材料，第三个目标用于完整来源覆盖。本轮未生成或验收材料页面。

## 逐目标与完整历史结论

| 分母 | PASS | FAIL | UNKNOWN | 未判定 |
|---|---:|---:|---:|---:|
| 完整来源训练适用性 | 2 | 0 | 0 | 0 |
| 有效决策的当前 Action | 3 | 0 | 0 | 0 |
| 有效决策的训练前缀 | 3 | 0 | 0 | 0 |
| 逐工具调用及参数 | 6 | 0 | 0 | 0 |

已逐字读取全部八个原始 turn 和六份原始工具 schema，逐决定核对角色、历史顺序、当前输入可见性、工具用途与带类型的参数。完整历史和当前 Action 分别判定；较晚工具结果未用于倒推先前调用的合理性。对工具 schema 未声明的业务格式约束不自行补充，当前合理查询也不等同于真实服务执行成功。

逐来源、逐 turn、逐决定、逐调用的理由及原始 hash 绑定保存在私有封存中。脚本仅核对身份、哈希、覆盖范围和已写定结论的一致性；语义判定由 Q1 完成。公开文件仅含汇总，不含样本正文、来源标识、Example ID 或私有路径。

## 核验与证据

输入核验覆盖完整 source、原 JSONL 行、Example/Action/messages/lineage、原 group/split、source turn 及类型化参数。保留旧 1,804 份私有文件、532 份公开 Git/快照与三轮 seal 的 133/376/1,293 项绑定；本轮 553 份基线文件和 13 份授权副本均核对通过。

最终来源核验实际检查 3,560 个唯一文件路径，结论、分母、完整读取回执、事件建议和原 P02-Q-081 台账绑定均通过。来源审阅 seal 绑定 677 份文件、16,528,889 字节，并在写入后重读校验。当前封存及后续交付证据受 128 MiB 上限约束。

| 私有证据 | SHA-256 |
|---|---|
| 逐项语义裁定 | `b587209d593e0c96ccda4b90515b2c20c34954128d9ed77d3555c6df28f05db0` |
| 来源处置建议 | `cbea3d505163cacdc979be878979eba9391509a7b105e78af010f8ed953a952b` |
| 审核事件建议 | `66550642a2ff85f826a83d9160cd5955634158a903997e40c783fb7b34ab1426` |
| 最终来源核验 | `2d661abdce80873494c5cd38c62b18f0681f259d998f6ae81bf16a2b5aae827f` |
| 来源审阅 seal | `1602656ef4a5b3d2ef62734d428dae6dab3cb858ff46d8a28528b5fb9defaa9c` |

四次辅助核验非零退出均保留：旧终态文件映射断言、来源 packet 相对路径解析、seal 验证摘要多录一字符，以及公开草稿错误地将不在当前基线的前轮报告设为本地链接。前三项修正新辅助脚本，最后一项改为前轮精确提交链接；后续核验通过。另保留首次新 scope 不存在时的 `rg` 预期退出 1。原命令、源码版本、完整 stdout、实际退出码与时间均归档；早期界面输出截断由完整日志和定点重读补齐，未用空执行导出替代证据。这些辅助失败不增加正式质量问题计数。

来源 seal 排除自身和当次运行结束后才写出的外层回执/日志；后续最终交付 seal 覆盖这些外层文件、公开提交内容及余下发布验证。最终交付 seal 自身和其终端外层回执/日志的边界在私有交接中显式登记。

## 限制与接续

本轮只使用 Python 标准库、现有 CPU 读取/hash 和 Git 发布；未新增依赖或环境。生产测试、数据构建、序列生成、tokenizer、模型/框架/GPU、API/网页、浏览器和训练均 `NOT_RUN`。该来源语义通过不能转用为 v3 数据或材料验收。

向 S0 提交两个新增来源 PASS 事件及保留建议，新增问题 0，旧问题更新建议 0，台账未修改。S0 核验精确提交与 seal 后，决定 D1 编码和下一轮实际候选审核范围。原轮次裁定及其失败记录保持，参见[上轮审阅](https://github.com/kris0516/ToolAlign/blob/8a738abc1f9485e072b87283cdd9003329d3524a/reports/review/Q1-P02-v2-r3/README.md)、[结构化摘要](summary.json)及[本轮交接](../../../coordination/handoffs/Q1-P02-v3-sources-r4.md)。
