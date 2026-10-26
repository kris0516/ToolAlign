# P05 G4 真实候选与偏好处置 Q1 r1 交接

**NO_ELIGIBLE_PAIRS；0 成功 / 0 偏好 / 0 审核样本，误标率不定义，DPO 质量门 BLOCKED。** 80 条固定分母与零对处置核对一致，不是偏好质量 PASS。详细结论见[Q1 审核报告](../../reports/reviews/P05_G4_PREFERENCE_Q1_R1.md)。

授权提交 `3890349baeb7f262230873bd0f52b4d05deeca4e`；实际执行源码 `6e2f1d28a8e5163ef29515da5cdf3a2c432ec7cc`。原 20 题与 Q1 r2 已审包一致，复用 `50440298a909a509d4cf86185e58c1daa11c1c5d` 的语义、来源和分组结论，保留原语料失败历史。

- 完整 80 条终态为 61 timed_out、12 invalid_arguments、5 unadvertised_tool、2 no_records。前 12 条逐字节继承，后 68 条固定身份连续；无缺失或重复。158 个实际 ModelInput、101 个返回动作及 202 条进程回收记录已独立绑定。
- CPU 重提取与原 preferences、lineage、80 个 dispositions、summary 一致。空 Q1 review 绑定原 sample canonical hash `73cac9826205cde303c06bede01e93fcd091337e578aed0dcc42716436db0f66`，实际 `apply_review` 返回 error_rate=null、quality_pass=false、BLOCKED、training_authorized=false。`nonsemantic_termination` 不表示此前没有语义错误。
- 首个符合运行时诊断判据的是 **ordinal 8，第 9 条，seed 50**。两个合法调用及实际 observation 依赖成立，第三次请求在 27.688 秒已提交，随后超时且没有第三个返回动作。前 8 条的排除理由及完整选中材料均在私有证据中。未返回答案为 unknown；不重标或补成偏好。
- 原 G3 的 5,938 train / 213 validation 目标全部为 tool_calls，当前 79 条完整首动作也全为 tool_calls。这确定了监督覆盖范围，不能单独证明 SFT 导致退化。独立 profiler 的加载验证耗时支持性能修订；诊断身份与正式批次分开，计时含 profiler 开销。

建议 S1 在运行时 CPU 修订与 R1 验收后，按原输入、seed 和轨迹预算选择 ordinal 8 做一次独立诊断，区分第三次请求不能完成与返回动作语义错误。原正式分母及零对保持，不放行 DPO；实际新运行仍由 S1 绑定配置。

私有 `evidence-index.json` SHA256 为 `8b3de9181a8f01a314b2e995878586d86ec5eada52eb3749467f504d80505742`，绑定 55 份文件，位置见交付消息。核心输出为 `review-result.json`、`q1-review.json`、`q1-gate.json`、`candidate-audit.json`、`diagnostic-selection.json`、`diagnostic-candidate-0008.json`、监督覆盖与 profiler 核对；实际审核命令和退出码在 `audit-command-01.json`，exit 0。

本轮未改生产实现、原始输入、冻结抽样、任务/oracle、训练材料或共享台账，未运行模型、GPU、训练、新编码或新轨迹。公开变更仅审核报告与本交接。
