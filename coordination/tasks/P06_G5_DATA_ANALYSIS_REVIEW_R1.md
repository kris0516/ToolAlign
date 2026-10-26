# P06 G5｜语料接口与官方评分分析独立技术审核 R1

owner R1；S1提供精确D1/E1候选、集成头及私有索引后，从该头建立 `codex/r1-p06-g5-data-analysis-r1`。先读取avoid-overkill；遵守[共同协议](P06_G5_PROTOCOL.md)、[语料范围](P06_G5_CORPUS_CPU.md)、[BFCL及分析范围](P06_G5_BFCL_ANALYSIS_CPU.md)和[审核政策](../REVIEW_POLICY.md)。只做CPU审查与有区分力的原创反例，不修改生产实现或原始语料，不运行固定模型、GPU或训练。

核对源码、输入和命令记录的实际对应。语料包须由已接纳的评测reader直接消费，ModelInput只含模型可见字段；按真实tool/schema/source/template/family关系核对闭包及旧组件桥接隔离，缺少元数据不能写成排除交集。核对tokenizer预检、恢复题预算、A2开发来源、固定ID/顺序和实际group数。全部保留题目的语义另由Q1审核；复用D1绑定的正反CPU轨迹，独立检查关键消费或隔离边界，不重跑完整矩阵。

BFCL按固定官方revision、三类各前50条与预定lossless转换/长度/交集规则核对实际eligibility及排除原因。不得通过补充更严格schema、扩大扫描范围或换题制造覆盖。若零题合格，区分协议覆盖为0和模型成功率未定义，不能记成0分；保留可复算扫描与NOT_RUN状态。核对官方源码/依赖隔离、原始Action解码、可逆别名、官方checker真实调用及版本身份，使用原创合法/错误fixture验证官方路径，不冒用其他模型的行为配置。

分析须保留完整计划分母和所有终态，官方raw score与按时完成且raw Action合法的严格成功分列；timeout、not_started、解析或基础设施失败不可因irrelevance空输出被记为严格成功。scorer未运行保持NOT_RUN。核对M0/M1同题配对、L0/L1/L2分开、M2缺失、预定group bootstrap与leave-one-group-out；不足2个独立group时区间和敏感性不可估，不能以题目数量替代group数。A1与A2按各自固定配对输入计量，缺失token/时延保持unknown，全部GPU分配与请求测量范围分明。错误案例和图表不得省略改变结论的失败。

复用实现者受检源码对应的已有测试，新增最少量能推翻评分、配对或隔离结论的独立检查。交付明确PASS/REQUEST_CHANGES、稳定issue ID与真实失败历史，公开只提交 `reports/reviews/P06_G5_DATA_ANALYSIS_R1.md` 和 `coordination/handoffs/P06-g5-data-analysis-review-r1.md`，私有证据留 `.toolalign-local/review-p06-g5-data-analysis-r1/` 并给精确commit及evidence-index。S1接纳、Q1语义通过和主干集成后才可冻结实际GPU运行。
