# S0｜Q1两来源正式接收与v3编码放行

2026-09-07。Q1完整审阅`9c12c47fd815f86992078313bac88dcec253f37f`已普通推送、原生completed/idle，S0已核验正式交接并以普通merge `eab828ff81ec18beb03d65117b0427ee320cc706`保留原SHA整合。结论为`PASS_SOURCE_SEMANTICS_ONLY`；14:48:51 UTC已原生通知D1执行原定两例的CPU编码。

| 范围 | 实际结论 |
|---|---|
| 两个固定完整train来源 | 2 PASS；FAIL/UNKNOWN/未判0 |
| 当前Action与完整训练前缀 | 各3 PASS |
| 工具调用、原始历史、schema | 6调用PASS；8原turn与6份schema全覆盖 |
| 新增材料身份 | 2个被选目标，另1个只供完整来源覆盖 |
| 处置与问题建议 | 保留两来源/三个原决策；新增问题、隔离及旧issue更新均0 |
| P02-Q-081 | CHANGES_REQUESTED，连续失败仍1；本轮未复核其实际排除 |
| v3数据/材料与正式训练 | 后续R1/Q1/S0待验，training_authorized=false |

独立审阅者为Codex-AI(Q1)，gpt-6-astra/max，无kris代签。固定input manifest `7d9ad0102b965a75071032d5be3e60dd1a91c09894a739ed852952c1ebbcfd2c`、source context `31f7c9bf7b72721492166bba97f4da1999a153f24894ac335ccc4132aff75161`与原S0授权`3e18145b66baa7bce498926869b2d52bd0503453`相符。没有重抽样、重标或用后继模拟结果补证当前调用；检索工具的下一步适用性不记为真实业务成功。

S0接收证明`53c22b3f69a3d16173bea85c53fac5d462a6f71f6c61e62a30cc2dd0ba313f90`于14:45:53 UTC通过：3,671当前路径、556公开文件/553不变基线、532旧公开Git/快照、1,804旧私有文件、8固定输入和13授权副本保持。34原始命令及4个辅助非零退出保存；32个原生执行封装/49条真实exec调用与47份原命令源码逐项核对，包含终端033/034边界和034实际exit0。核验过程不导入框架、不重跑语义脚本或编码。

原来源seal `1602656ef4a5b3d2ef62734d428dae6dab3cb858ff46d8a28528b5fb9defaa9c`绑定677文件/16,528,889 bytes；最终seal `dc0b470b3c827d3e8aa7c6b1d719efad928d5688f358fac96da22a6ee97f1de0`绑定767文件/21,086,175 bytes。最终seal自身与运行返回后才写出的034外层回执/日志明确排除，S0另已核验它们的实际字节、原生工具结果和结束状态。Q1四个辅助失败、首个scope不存在的预期非零查询及S0首次接收脚本把`tool_calls`字段写成`calls`的失败均保留；修正未改变输入、裁定或质量计数。

S0放行JSON SHA `1eeea3bd45daa8caf5d2867efa5859a446673888993aaaf9cc3a21b80ca555fd`，3,723 bytes，明确绑定原配置、347项输入、Q1精确提交/两级seal和S0接收证明。授权仅为两个既定Example在transformers/tokenizers各生成两份新sequence，总计最多4次；第三个来源覆盖目标不编码，11旧例（含3协议例）复用完整原数组和原运行身份。放行文件单列保存，不修改冻结生产input manifest/配置。D1新编码执行结果尚待交付。

D1已回报两次完整数据输出一致，实际manifest `f4569b8b16a6c42bd500cc7c977561b770435954e42ced177e36e857b9776437`、quality revision `919ee616fd11993f39bbab6d38146ea827f4bbc3d7bafc07aae0e2c7dd95e5c8`，有效7419/230、formal5938/213、smoke1583/194；42项定点自测及11例两engine复用通过。这些是中间交付回报，完整候选/封存和S0接收尚未完成；两份完整输出目录构建额度2/2已用，不增加第三份全量构建。

[Q1原交接](../coordination/handoffs/Q1-P02-v3-sources-r4.md)、[D1范围](../coordination/tasks/P02_QUALITY_EXCLUSION.md)和[后续R1范围](../coordination/tasks/P02_QUALITY_EXCLUSION_REVIEW.md)保持各自边界。当前82个issue仍81关闭/1待修，未触发第五次暂停；浏览器实显NOT_RUN，真实trainer消费、G-DATA及P04尚未验收。本次S0新增数据构建、分词、框架、模型和GPU均0，无新环境、下载、费用、模型/数据上传或公网服务。

15:00前中间补核：S0证明`95f041fe2cbd35afb0a326f1acff2c512ffa8e3e178072f8179b4b87ed35136f`核验150个实际路径、两份各29稳定制品、15,577次v2原逐行字节与7,928条sidecar的v1/v2/当前rank绑定，新增两决策均已排除。两engine各11例（含3协议）完整sequence/padding/token_texts与原记录相同，原实际编码时间保持，D1放行副本逐字匹配。两次S0字段/摘要解释辅助失败已保留并修正，数据和数组未改。此为中间实物绑定，完整候选与新两例结果未接收，尚不关闭P02-Q-081；[Q1后续实际复核范围](../coordination/tasks/Q1_P02_V3_REVIEW.md)已PLANNED未派发。
