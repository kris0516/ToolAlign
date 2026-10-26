# P06 G5｜原48题隔离与完整排除参考 CPU r2

owner D1；S1提供精确集成头后从该头新建 `codex/d1-p06-g5-quarantine-reference-r2`。先实际读取avoid-overkill、[Q1 r1](../../reports/reviews/P06_G5_CORPUS_Q1_R1.md)和[新候选边界](P06_G5_L1_REPLACEMENT_PLAN_R2.md)。本包落实Q1-G5-CORPUS-002的已确认处置，不构造新题，不修补原48题，不运行模型。

以原48题完整包及Q1的具体missing-field语义桥接为输入，重算已有传递闭包，生成独立r2处置包：retained=0、quarantined=48，保留全部原task/family/tool/schema/source/template身份、完整组件成员及连接理由。原包、答案、轨迹、检查和原FAIL保持原字节。不能只输出eligible=0，也不能删除桥接题后恢复其余题。

冻结后续新工具/语料可直接读取的完整排除参考。使用已经绑定的P02 policy-a metadata（所有split、仅读metadata）、P03十题、已接纳G4二十题和本次原48题；记录来源身份及实际节点/边。原48题的工具声明、schema/normalized-schema键、family、语义连接、组件成员必须保留，使任何一个新题连接原组件都导致整组隔离。catalog_id或函数改名不重置这些关系。新旧语义连接仍由作者和Q1按真实程序提供，不能声称词法检测穷尽语义重复。

优先复用现有audit和私有recipe输出；若当前audit无法把历史G5作为排除参考，只在 `src/toolalign/data/evaluation/audit.py` 增加最小显式历史参考参数及对应原创测试，保持原调用行为。不要改contracts、旧oracle、工具、后端、BFCL/analysis、依赖或共享状态。所有原题、全量参考与recipe留私有；公开只含必要代码、原创测试和本轮报告/交接。

验证完整48条均隔离、原包字节保持、完整参考可回读，并用一个原创新节点连接某个原G5节点确认隔离可经旧组件传导。无需重跑99条轨迹或固定模型tokenizer矩阵。交付精确commit、`reports/P06_G5_QUARANTINE_REFERENCE_CPU_R2.md`、`coordination/handoffs/P06-g5-quarantine-reference-cpu-r2.md` 和私有 `p06-g5-quarantine-reference-r2/evidence-index.json`。给下一工具/语料任务简洁的参考读取方式；本次不声称新语料通过或关闭002，最终由R1/Q1复核。
