# Q1｜G3 完整 SFT 数组增量审核

状态：ACCEPTED。Q1独立提交 `98cf0e1370ff68ca3306e157be1f7c95ac37a2e9` 已由S1在GPU分配前接纳，实际7,928行数组、训练和验证分母及13例材料身份通过，见[审核报告](../../reports/reviews/P04_CUDA_SFT_FULL_ARRAY_Q1_R1.md)。实际执行主干为 `2abbe7ac913661df1d5e430f285604b4ceb8ff4b`。以下保留原任务范围。

本轮核对完整数组与冻结v3选择的对应关系：smoke为1,583条train、194条validation，formal为5,938条train、213条validation。逐行读取实际数组，核对冻结ID、顺序、rank、长度bucket、token摘要、prompt/completion/EOS边界及causal mask；验证没有重复、漏选、截断或额外样本。按实际mask独立累计监督token，预期train分别141,211和536,238，validation分别21,226和23,841。

核对prepare/encode的实际来源提交、CUDA v2配置、固定模型和tokenizer revision、输入manifest和数组manifest，以及原始回执的退出、时限、产物和源码未变。完整数组仍只供既定SFT与验证使用；不读取测试集进行选择。

13例审核材料复用 `82f1e88`、`ed022da` 及G2终验 `847e0be` 的语义结论，先核对实际内容身份。无需重做未变化的531项旧检查或语义标注；若本轮新数组存在不一致，记录确切差异并按真实影响判断。数据审核PASS不表示训练或模型效果PASS。

允许新增 `reports/reviews/P04_CUDA_SFT_FULL_ARRAY_Q1_R1.md`、`coordination/handoffs/P04-cuda-sft-full-array-q1-r1.md` 和必要私有证据。只读流式检查大型数组，不复制整套历史私有输入。每命令≤300秒、2线程、新增私有产物≤256MiB；真实模型、GPU、SSH、新编码和安装均0。交精确审核提交、PASS/FAIL、完整分母与必要问题及原始证据摘要。共享状态由S1维护。
