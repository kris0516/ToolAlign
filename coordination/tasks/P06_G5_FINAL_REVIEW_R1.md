# P06 G5｜实际评测与分析技术终验 R1

owner R1；仅在S1提供精确主干、已回收运行和分析索引后派发。先读avoid-overkill，遵守[冻结协议](P06_G5_PROTOCOL.md)和[审核政策](../REVIEW_POLICY.md)。在独立worktree只读核对实际证据，复用已接纳实现和语料检查；不修改生产实现、原结果或测试清单，不运行固定模型/GPU。

核对实际源码、模型/adapter、输入、采样、plan及输出身份，逐项确认所有冻结单元的终态和失败分母。容量探针单列，不能进入效果估计；恢复仅接续未启动ID，原已启动失败保持。核对真实owned child回收、产物回读、实例停止，以及全部分配时间和CU观测账目。核对两模型同协议、M2 NOT_RUN和L2 NO_ELIGIBLE_INPUTS；官方模型分数及评分未运行时保持NOT_RUN。

从实际逐条记录独立复算主效应分子/分母、配对差值、实际group数、冻结cluster bootstrap和leave-one-group-out敏感性；复算A1对应8题与A2固定序列的配对结果。区分完整分配/段/单元成本、模型冷启动、TTFT/prefill/decode与工具时间；缺失token或时延保持unknown。原始输出相同与cache实际命中分别核对，不从请求序列相似推定命中。图表、失败分类和主要文字结论须能回指实际记录。

只新增能够改变验收结论的定点检查，不重跑已绑定且未改变的CPU矩阵。交付明确PASS/REQUEST_CHANGES及稳定issue ID；公开仅提交 `reports/reviews/P06_G5_FINAL_R1.md` 和 `coordination/handoffs/P06-g5-final-review-r1.md`，私有材料留 `.toolalign-local/review-p06-g5-final-r1/`，报告精确提交和证据索引。S1维护共享状态并决定接纳。
