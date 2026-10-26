# P05 G4｜真实候选及偏好处置 Q1 审核 r1

owner Q1，独立AI语义审核。S1在完整80条回收、偏好提取及抽样池冻结后派发，提供本任务的精确授权commit和私有输入索引。复用既有独立worktree，新分支 `codex/q1-p05-g4-preference-r1`；先实际读取avoid-overkill。只读输入，生产执行源码固定为PR28主干 `6e2f1d28a8e5163ef29515da5cdf3a2c432ec7cc`。

本轮审阅[执行协议](P05_G4_PROTOCOL.md)与[实际生成报告](../../reports/S1_P05_G4_GENERATION_R1.md)对应的真实候选、偏好池和处置。20题语料的Q1 r2 PASS `5044029`继续适用；tasks SHA256 `b9c6f18995579d8af1a58d137cafe9cc1c9f2f40279d9434aa85e2c7769eb015`。复用已审语义、分组和来源结论，核对身份而不重做无变化的语料审核。原语料r1失败历史保留。

核对完整20任务×4候选的冻结分母、seed42–121、真实SFT/模板/工具身份、实际ModelInput及终态。前12条pilot的终态应逐字节继承，后68条只执行此前未启动ID；超时、失败、interrupted及unknown均不能从分母消失。对照实际输出检查提取处置，确认成功chosen来自整条真实成功轨迹、共享完整前缀、rejected当前分歧本身的语义错误及合法多解/tie规则。无需重复已有实现测试；有具体疑点时使用最小CPU重评分或反例，不调用模型。

若有效池非空，按预先冻结的pool/分层/seed42审核 `min(total,max(100,ceil(total*0.10)))` 对，unknown计误标，严格大于5%阻断。已确认误标或unknown一律不进入训练，保留原审核分母，不换对回填。审核JSON使用当前apply-review输入格式并绑定原sample hash；交付逐对判断与证据。

若有效池为零，给出明确的 `NO_ELIGIBLE_PAIRS` 处置，检查零对结论是否由实际终态及冻结规则支持；审核样本数为0，误标率不定义，不能写成0%或偏好质量PASS。区分最终超时与此前已返回动作的语义错误，不能推测未返回答案，也不能将脚本补完轨迹当作真实成功。零对不放行DPO。

独立加载性能诊断若存在，以不同run ID和 `REAL_CUDA_SFT_PHASE_PROFILE_DIAGNOSTIC` 单列，不能替换正式80条失败或混入偏好池；它只支持加载耗时归因，计时包含profiler开销。审核报告应指出具体受支持的结果及下一项有区分力的工作，不编造效果提升或忽略反证。

实际提取已得到0对、80个 `nonsemantic_termination`。这个统一排除标签不能解释成80条均无语义错误。S1还读取原G3已绑定stage：5,938 train及213 validation的expected_action.kind均为tool_calls；核对原文件hash及计数，判断其支持的监督覆盖结论，不能据此单独证明SFT导致了行为退化。正式生成79条完整首动作也均为tool_calls；无需工具类为7条工具调用、1条无完整首动作。

为区分运行时不足与已确定语义错误，可在原80条中按ordinal从小到大指出首个“所有已完整返回动作仍符合至少一个合法剩余策略、最终因超时未完成”的候选，给出完整输入/轨迹引用与判据，供S1选择一次独立运行时诊断；存在unknown时保留unknown，若没有符合项直接报告没有。该选择只用于诊断，不重标偏好、不补造成功、不改变原分母。性能修订与后续运行由T1/R1/S1另行处理。

仅允许新增 `reports/reviews/P05_G4_PREFERENCE_Q1_R1.md`、`coordination/handoffs/P05-g4-preference-q1-r1.md` 及本轮私有审核JSON/证据。交付精确commit、实际命令和退出码、输入/输出索引及逐项结论。禁止修改生产实现、共享状态、原始候选、任务/oracle、冻结抽样、训练材料；不下载模型/新依赖、不运行GPU、不建新聊天或sub-agent。S1核对证据后决定接纳与后续执行，无需人类签字。
