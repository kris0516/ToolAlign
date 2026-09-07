# S0｜扩展审计完整交接与后续范围

2026-09-07。E1完整候选`5270d1e9bdadb9db36deac7ba9b2e256b267b831`已本地交付、原生completed/idle；S0核验后普通发布原SHA，并于03:32 UTC建立[Draft PR13](https://github.com/kris0516/ToolAlign/pull/13)。完整10个新路径、428个基线文件不变；内容提交e5030e9和原采样器7298456保持。未把后来的文档提交冒写为早期运行HEAD。

S0于03:30:17–03:30:19 UTC核对4,536当前文件路径，证明`eb50aab537f8aba07a1930159656965e2555858fea33b00861c199dd7786a32a`。733份私有封存文件、10份公共文件、最终receipt及两条封存创建证据全部绑定；737个普通私有文件与一个不跟随的fixture链接合计30,667,535字节，低于1GiB。实际438份候选、428份不变基线、4880条原保全记录及26条原命令匹配；两次exit1和旧脚本/修正保留。本次S0新测试、分词、模型和框架运行0。

完整seal`adcf1a3ffd22a3803afc4cce7914f3bb37ee515a2eee282733521b05ff349889`、receipt`b4b9d5898594d2c9fc9026ea75a197c4b82ee67b78a6afaa745fbb93fcc9306c`保持。逐项导出222来源/251决策与各原判断、packet、真实目标字节匹配；87 Action问题为24 fail/63 unknown，另1个历史advisory和79个来源建议。12项取样fixture、43视图重建、分母/去敏核对是E1实际自查；R1整包技术审查尚未完成。

原固定180新增来源/200决策seal与[先前S0核验](S0_P02_Q1_ADJUDICATION.md)保持。随机120和定向60独立统计，不以合并比例外推全库。原32来源、10个追加材料来源及协议/staging分母分开；没有重抽样、改数据、重标或放行训练。

已冻结[Q1下一范围](../coordination/tasks/Q1_P02_EXPANDED_REVIEW.md)：50来源/60决策，46 train/4 validation；114文件、1,996,572字节，manifest`eebc74d745610b518df6ce377c69c50d1271e7aa5d70ba58e8289396cf4857fe`。只纳入49个Action待裁定来源和1个历史advisory来源的完整packet；54个问题/49份建议保持原次序与字段，派生筛选有原hash。旧Q1裁定供稳定问题参考，新的S0正式授权和原生派发尚待完成。

[R1完整技术复核](../coordination/tasks/P02_QUALITY_AUDIT_REVIEW.md)已READY，必须先完成其现有9b7cf01审查并核实原生终态再派发。Q1裁定、D1新版数据/选择/配置、最终CI/main和G-DATA/P04继续待完成；用户无需人工填写或签字。

03:41 UTC，S0按完整39cba8bc68edea00266f142dbdf0091da50bd9ec向原Q1实际派发新范围并确认ACTIVE；03:46:50–03:46:53 UTC直接核验934当前路径，证明`735d4883e79f35cc04c180eab230129f2843159bf1b874cf74978720445c64eb`。449基线、7授权、114载荷原件/副本与两项派生筛选、50来源/60决策、旧133封存文件及根级旧身份保持。Q1首版intake排序假设错误和修正后的集合/turn核对日志保留，不计数据修订失败。

PR13候选[CI34079966518](https://github.com/kris0516/ToolAlign/actions/runs/34079966518)已完成双Python各14步骤；各637 passed/48默认环境skipped，另46项P00通过。S0于03:44 UTC核对两份原日志及实际checkout`240ef2e9969f39adc8e18f49f1c0fc249fb9e290`、parents b63de05+5270d1e和459文件合并结果，证明`2d65014bca9352d8a7eb85c90890f5fc74ad84a6ad5ae671e02f7738e6685137`。候选CI不代替R1独立审查，PR13未合并。

R1原9b7技术审查已交付原PASS提交`1e45cf2c2ea07b703be548a112ef16e1ef134ee9`并原生completed/idle；S0尚需核验其完整最终封存后接续PR12集成与本审计技术复核。未提前复用旧框架额度或切换R1范围。
