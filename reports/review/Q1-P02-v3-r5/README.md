# Q1-P02-v3-r5｜实际处置与材料独立审核

结论：**PASS_WITHIN_FIXED_Q1_SCOPE**。审核者为 **Codex-AI(Q1)**，独立 Codex 任务，实际模型 `gpt-6-astra` / `max`；本报告没有 kris 人工签字或真人审阅声明。

精确候选为 [5825d789ee89afedbfff31e828223608c6f435e2](https://github.com/kris0516/ToolAlign/commit/5825d789ee89afedbfff31e828223608c6f435e2)。审核 code_base `7a731c5f08a561f5941fcba5996004706f373392`，授权 `21f92107d03f776a3b81d4d61d39072e96d236d3`；其已验证生产基线仍为 `d3e56f68ebd67cc576d912b6f06636682b4170ab`。沿用 `plan-v0.1`、`toolalign.contracts.v1` 与角色保留 Action JSON v1 契约。固定输入 manifest `b2ae91538823c2e64af68deb871736134e488df00937df34e2cfd207470e4a8c`，包括 223 精确副本和 71 明确只读引用；出处路径不扩大读取范围。

## 实际数据处置

逐字核对 7,749 条原决策及 lineage，原字节全部保持；核对 7,928 条选择 sidecar 的 v1 父 rank、v2 上一版 rank 和 v3 连续 rank。旧 83 来源处置保持，3 项恢复仍使用原字节；同 group 的其他 5,551 决策、5,181 来源保持，staging 未晋升，过滤没有补选或重标。

| 处置 | 来源 | 决策 |
|---|---:|---:|
| 总处置 | 84 | 103 |
| 整来源排除 | 81 | 100 |
| 原字节恢复 | 3 | 3 |

| 当前有效集合 | train | validation |
|---|---:|---:|
| 有效数据 | 7,419 | 230 |
| formal 选择 | 5,938 | 213 |
| smoke 选择 | 1,583 | 194 |

P02-Q-081 的两条原决策均已在实际有效数据及两个 profile 中隔离，包括错误历史之前仍有局部 Action PASS 的目标。原来源 FAIL、两个局部 Action PASS 及历史失败均保留。Q1 提出该稳定 issue 的正式 **PASS / CLOSED / 连续失败 1→0** 事件，等待 S0 采纳；本任务未改台账、未恢复该来源、未把历史语义重标为 PASS。其他 issue 的正式修订次数增量为 0；新问题 0。

## 13 份材料与判定继承

两 engine 的 26 条完整记录对应 **13 个唯一例**：10 个实际 train 例和 3 个原创协议例。11 个沿用例由 8 个实际 train 例和 3 个协议例组成；逐类型确认其 Example、Action、messages、audit、完整 sequence、padding 和 token_texts 不变后，继承 [原 8a 审核](https://github.com/kris0516/ToolAlign/blob/8a738abc1f9485e072b87283cdd9003329d3524a/reports/review/Q1-P02-v2-r3/README.md)的明确 PASS。当前 case 别名、v3 修订与选择 rank 单独核对。原创协议例仅在其显式协议范围内 PASS，不进入有效训练，也不证明真实业务提示需要该种回复。

两新增材料的完整来源语义继承 [原 9c 审核](https://github.com/kris0516/ToolAlign/blob/9c12c47fd815f86992078313bac88dcec253f37f/reports/data/q1-v3-source-review-r4/README.md)：2 来源、3 原决策、6 调用。原输入字节、完整前缀、Action 和 lineage 已重新绑定；本轮新语义抽样及重复正式语义审核均为 0。另一个已覆盖来源目标没有新增编码额度。

Q1 对两新增 sequence 的实际完整数组独立判定 **token/mask PASS**：

| 当前材料 | P | C（不含 EOS） | N（含 EOS） | 右 padding | 因果监督位置 | 监督目标 |
|---|---:|---:|---:|---:|---|---:|
| effective-06 | 1,324 | 82 | 1,407 | 129 | 1,323–1,405 | 83 |
| effective-07 | 1,196 | 180 | 1,377 | 159 | 1,195–1,375 | 181 |

两者 bucket 均为 1,536。完整 P 保留已审角色、工具目录和前缀观察，C 与原 Action 逐类型一致；prompt 不计 loss，第 P−1 个因果位置开始预测 Action，最后监督目标是唯一追加 EOS。EOS 后与右 padding 不计 loss，padding attention 为 0。两 engine 完整记录一致；26 个静态页面的 208 个完整 pre 块、37,888 行 / 303,104 个 token 表格单元与 JSON 实物逐项一致。静态 HTML 检查没有记作浏览器实显。

## 编码来源、失败与边界

两次新增原命令均绑定 S0 精确放行 `1eeea3bd45daa8caf5d2867efa5859a446673888993aaaf9cc3a21b80ca555fd`、原 Q1 提交和两级 seal。核对每 engine 的 reservation、2 次 start / complete 事件及完整输出 hash：新增 sequence 总计 **4/4**，旧 11 例重编码 0，第三个来源覆盖目标编码 0，记录中的 sequence 失败 0。原编码和新增编码分别绑定其原始 argv、UTC、退出码及两个源码 epoch 的 16 / 18 份 consumer 文件；旧测量时间没有改写为本轮时间。

本轮保留 4 次辅助脚本读取类型守卫失败、3 次只读路径查找失败及所有修正后的实际结果。这些属于本地审阅工具错误，质量问题失败计数增量为 0。完整命令、未截断日志、源码时点、判定继承映射和原失败仅存本机证据。

Q1 新分词、生产测试、数据构建、依赖安装、框架/模型/GPU运行与业务 API 调用均为 0。浏览器实际观察、真实 trainer 消费均为 **NOT_RUN**。独立技术审查由 R1 另行承接；G-DATA 须由 S0 在两项独立审核与 main 验证之后决定，`training_authorized=false`。

## 封存与公开范围

审核 seal `d9da8add7457a253865462e59745f4ae8b29dc3d99ae3595ee8e2133bfea5117` 绑定 993 文件 / 63,870,668 bytes；封存自身及当次外层终端回执明确排除，外层回执由最终交接 seal 接续绑定。最终提交、普通推送和发布终态由本机最终 seal 及原生交接提供。

复核确认旧 2,571 份私有文件、旧 556 份公开 Git / 双快照、四份旧最终 seal、当前 581 份基线及 16 份授权副本保持。公开增量仅本报告、[汇总](summary.json)和[交接单](../../../coordination/handoffs/Q1-P02-v3-r5.md)，没有原始数据、材料正文、私有任务身份或绝对工作路径。
