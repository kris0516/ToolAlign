# P06 G5｜观察后决策评分修订 CPU r2

owner T1。S1指定精确集成头后建立 `codex/t1-p06-g5-observation-oracle-r2`，先实际读取avoid-overkill与systematic-debugging。对应[Q1 r1](../../reports/reviews/P06_G5_CORPUS_Q1_R1.md)的稳定问题Q1-G5-CORPUS-001，首次正式未通过计数1；本轮不是重做训练、模型或cache实现。

Q1已在真实轨迹中证明：同一Action预先提交依赖调用或恢复调用，v1展开后的步骤仍与正确分轮策略相同，因而误判success。先读取两条原反例和原正确轨迹，再实现显式版本的G5评分。复用原v1答案/调用匹配，增加题目要求的“前次观察→新模型决策→后继调用”约束。必须实际依据trace事件及预算边界，不能仅检查调用数量、最终轮数或是否出现过某条观察。允许其他题目合法的同轮独立调用，不增加全局禁止。

保留原 `SemanticOracle` v1 源码、默认行为和历史结果。新增小型独立oracle及明确的payload/version，G5 runner按已验证任务版本显式选用；未知或不完整的真值仍为unknown，不能隐式退回更宽松判定。输入依旧使用现有OracleTask和Action/Trace契约，隐藏oracle不进入ModelInput。公开可修改范围仅 `src/toolalign/evaluation/oracles/` 的新增模块/必要导出、`src/toolalign/evaluation/cuda_eval/runner.py` 的显式选择、对应原创测试，以及本轮报告/交接。不要改旧v1文件、contracts、工具目录、模型后端、D1构造包或依赖。

给D1交付简洁明确的新payload格式及选择入口，支持同题的多个合法策略和题目特定的观察依赖。采用最小表示，不引入通用规则引擎。原48题已被Q1要求整组隔离；可在私有修订副本上复验两条已知反例和正确轨迹以验证评分，但不得恢复这些题的独立测试身份。

验证原两个预提交反例在新版本失败、合法分轮执行与等价策略继续通过，另以原创独立调用证明合法batch不被全局误伤。至少一项真实owned harness/G5入口检查确认实际选择了新oracle，保留进程回收。复用未受影响的现有证据，只运行受影响的oracle/harness检查和发布检查，不重跑CUDA/模型数值矩阵。

交付精确commit、`reports/P06_G5_OBSERVATION_ORACLE_CPU_R2.md`、`coordination/handoffs/P06-g5-observation-oracle-cpu-r2.md`、真实命令/退出码与私有evidence-index。原失败保留，计数由S1维护；R1技术和Q1语义复验后才可关闭。仅CPU；禁止固定模型推理、GPU、训练或依赖安装。
