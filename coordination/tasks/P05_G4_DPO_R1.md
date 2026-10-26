# P05 G4｜原生 DPO CPU 独立技术审查

2026-10-26；owner R1；CPU-only。审核E1精确候选 `982cc1917d23b4004dbf9f683c685515eb390ea7`，基线 `f72bb5fc7343989efcfc01b305e690d0cddeb661`，按[实现任务](P05_G4_DPO_CPU.md)与[G4协议](P05_G4_PROTOCOL.md)判断，不扩大为真实CUDA验收。

S1已回读报告、交接、主要实现与控制器差异，逐字节核对24个交付文件和2,144份私有证据。E1报告原生数值/冻结/10对8+2完整恢复三项通过、70项输入/进程/Colab检查通过；原测试参考遗漏scheduler字段的失败保留。原始数值与命令由R1自行检查，不以S1或E1陈述替代证据。

R1复用独立worktree，从本授权提交新建审查分支，再cherry-pick上述E1候选；不要操作S1正在控制GPU的checkout。只允许新增 `reports/reviews/P05_G4_DPO_R1.md`、`coordination/handoffs/P05-g4-dpo-review-r1.md` 和私有原创CPU审核材料。禁止修实现、改冻结契约/数据/共享状态、安装或修改共享环境、下载真实模型、GPU或Colab操作、新聊天/sub-agent。

重点核对：

- 原生TRL sigmoid DPO的completion SUM、EOS/prompt/pad mask、logits_to_keep开关、两份启用同一SFT adapter且不共享存储的policy/reference；不能禁用adapter替代reference。
- D1/Q1六文件绑定、原误标分母、零对阻断、原始字符串与原生prepared IDs、超长明确排除；合成CPU输入不能冒充正式质量门。
- 原生AdamW/常数scheduler、一轮固定顺序、真实尾组除数；保存与段结束只在完整optimizer边界，完整checkpoint/游标/RNG与新进程恢复；容量和正式身份不互通。
- CUDA-only入口、完整输出/墙钟上限、owned进程回收、独立DPO环境/锁及原SFT/generation路径兼容。Linux dry-run与Mac CPU结果不算实际CUDA实装或恢复。
- 对原证据绑定到最终源码的关系进行核对。复用已通过且未受影响的检查；新增最少有区分力的独立CPU检查或原始数值重算，记录实际命令和结果，不把实现者断言复述为独立验证。

专用Mac CPU环境和证据索引由S1私下给定，可只读调用，不修改。R1交付精确review commit、PASS或具体问题及优先级、覆盖范围和私有证据索引。真实偏好、CUDA容量/跨实例恢复及正式DPO仍NOT_RUN；本轮通过不授权这些运行。S1仍须等待真实偏好池与Q1质量结果后另冻运行配置。
