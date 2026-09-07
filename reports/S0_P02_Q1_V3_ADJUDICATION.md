# S0｜Q1 v3 实际处置、材料与数据门验收

状态：**Q1 审核已接收；G-DATA PASS（冻结 v3 范围）**。S0 于 2026-09-07 17:18:09 UTC 完成接收，随后采纳问题关闭事件。审核者为独立 **Codex-AI(Q1)**，gpt-6-astra/max；原 review `7941f1f56519ea2eac437c669ac2c6445a0329f6` 对精确候选 `5825d789ee89afedbfff31e828223608c6f435e2` 给出 `PASS_WITHIN_FIXED_Q1_SCOPE`。Q1 已原生 completed/idle，原 SHA 通过普通合并 `10a22a08c3c3e2eccfc469d1a29a950ced33af18` 保留。[原独立报告](review/Q1-P02-v3-r5/README.md)。

## 已核对的实际结果

81 个来源/100 条决策已整来源排除，3 个来源/3 条原决策恢复，共核对 84 个来源/103 条决策处置。7,749 条原决策与 lineage、7,928 条选择 sidecar 的三代 rank 保持；同 group 其他来源保留，staging 无晋升，无补选、重标或重新切分。

| 有效集合 | train | validation |
|---|---:|---:|
| 全部有效数据 | 7,419 | 230 |
| formal 选择 | 5,938 | 213 |
| smoke 选择 | 1,583 | 194 |

固定 13 唯一材料/两 engine 26 记录全部 semantic 与 token/mask PASS。11 例在完整载荷不变后继承原 8a 明确判断；两新增材料继承原 9c 来源语义，Q1 独立审查其本次实际数组。3 原创协议例保持训练外。两新增例的 P/C/N 为 1324/82/1407 和 1196/180/1377，含 EOS 的监督目标分别 83/181；右 padding 129/159。完整静态 HTML 的 37,888 行、303,104 单元及 208 pre 块与 JSON 一致；浏览器实显仍 NOT_RUN。

原两次新编码命令及放行 `1eeea3bd45daa8caf5d2867efa5859a446673888993aaaf9cc3a21b80ca555fd` 已绑定：每 engine 两例，总新 sequence 4/4；旧 11 例和第三来源覆盖目标新增编码均 0。Q1 与 S0 本次均无新分词或语义抽样。

## 接收证据与台账裁定

S0 直接核对 5,115 路径，含 584 公开文件/581 不变基线、16 授权副本、223 输入副本/71 只读引用，以及旧 2,571 私有文件和 556 公开 Git/双快照。两级 seal 的 993/1,107 成员、42 条日志化命令、54 个原执行包装调用中的 73 个实际 shell 调用均已交叉绑定；71 份原 shell 源码保留，最终外层执行实际 chunk `4bf715`、exit 0。原第 017 条显示被截断，其 exact wrapper hash/bytes、命令与退出和完整本机日志分别保留，不声称原显示完整。

接收证明 `48aae102b248963b95537c688214c0871c4ed995315e059077cbc6be7869c496`；原审核 seal `d9da8add7457a253865462e59745f4ae8b29dc3d99ae3595ee8e2133bfea5117`；最终 seal `c272ffa263786086a5d83c057408aac0baabb82f8608e948b6fdbc0495bb74e9`。Q1 原 4 次辅助类型守卫失败/3 次只读查找失败保持；S0 接收脚本的日志标签、heredoc argv 和台账关闭枚举三处辅助假设失败也保留，均不计质量修订次数。

S0 采纳 P02-Q-081 第 2 次正式审核的 PASS：两条原决策实际整来源隔离，连续失败 1→0，状态为 `CLOSED_TRAINING_USE_DISPOSITION_PASS`。原首次 FAIL、整来源不适用与两个局部 Action PASS 均不重标。其他 81 个问题及全部旧事件逐字保持；当前 82 问题均关闭，最高连续失败 0，无问题达到第五次暂停阈值。

台账新文件 SHA `022356d8dc6fdf273804d0f78e58416677799e303b0dc1b6a46b1e7b1ffcb992`；S0 采纳/数据门证明 `26f30c21390105f082a6aaefeb3366318353feee70a8f3460a2795f585fadf77`。历史 D1 冻结台账与 candidate manifest 的 pending 字段保持原字节；当前批准使用独立的 [S0 v3 数据批准记录](../coordination/approvals/P02_DATA_V3.json)，文件 SHA `1edb1e889b91dbde5dc6208b8dff2afdaa4b4a20a0ba5c166e9b55750429ec44`。

## G-DATA 的证据与限制

| 条件 | 已满足的固定证据 |
|---|---|
| 来源许可/访问 | ToolACE 官方固定 revision `6bda777c88d21e5a204703c1ee45597a8fa4f734` 的原许可/访问 lock、README 和原文件 hash 保持；发布方 README 标 Apache-2.0，无独立 LICENSE，xLAM 未使用 |
| 分组隔离 | 原结构检查各类 split intersection 均 0；v3 只过滤并保持原 lineage/group/split，不声称检测所有语义近重复 |
| 独立质量及问题处理 | 用户委托 AI 的固定审核、后续 Q1 实际处置与 13 材料通过；全部已登记问题处理，不认证未审全库 |
| 配置/manifest 绑定 | v3 manifest `f4569b8b…`、selection `d765493c…`、training-binding `588c94b6…` 精确连接原选择配置 `579d3d9d…` 及 v3 质量政策 `784aa699…`；完整值见批准记录 |
| 最终集使用边界 | 无最终集/BFCL 训练、选样或调参；正式模型实验尚未运行 |
| 独立技术与主干 | 原 R1 PASS `dbd11d0`，PR15 合并 `90c4da9`、最终双 Python CI 及实际 main 检查通过；[主干证据](S0_P02_QUALITY_V3_MAIN_VERIFICATION.md) |

G-DATA 只批准这一冻结数据、选择和审阅材料。真实 trainer 的 CPU 数据衔接、容量实测、明确 P04 运行配置及 GPU 预算仍待后续授权；`training_authorized=false`、`optimization_authorized=false`。正式 baseline/SFT/DPO、评测和 serving 均无验收结论。无需 kris 填表或签字；费用、隐私和公开范围保持。
