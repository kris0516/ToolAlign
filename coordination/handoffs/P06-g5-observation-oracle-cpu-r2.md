# P06 G5｜T1 观察后决策 oracle CPU r2 交付

授权头：`7e1f04172339c5f18af0268b68f44d1c3388b498`。分支：`codex/t1-p06-g5-observation-oracle-r2`。精确 commit 与私有索引随最终交付提供；[完整报告](../../reports/P06_G5_OBSERVATION_ORACLE_CPU_R2.md)。

新版本 `toolalign.semantic-observation.v1` 在原 v1 语义匹配之上，按任务显式检查观察之后的新模型决策及工具轮边界。G5 runner 已使用 `select_oracle(task)`；`SemanticOracle` v1 源码与 harness 默认值未改。未知版本/不完整真值保持 unknown。

D1 接口保持 `answers/strategies` 原形状，新增与策略一一对应的 `after_observation`。每个 `[i, j]` 指同一策略的工具步骤索引，要求观察 i 后再决定调用 j；依赖/恢复例为 `[[[0, 1]]]`，独立策略为 `[[]]`。多个合法策略各有自己的依赖列表，允许无工具策略。构造时调用 `validate_observation_task(task)`；作者 CPU harness 显式传入 `oracle=select_oracle(task)`。E1 按 `oracle_payload.strategies` 读取步骤的接口不变。

两条 Q1 预提交反例已重评分为 failure；对应正确分轮、两种允许策略和数值等价仍 success，布尔值反例仍 failure，共 8 条重新评分符合预期且没有新模型/工具执行。受影响回归 141 passed，exit 0，含 26 项新 oracle 检查。最终回归中的原创 G5 入口真实运行 4 条 scripted 轨迹，依赖 batch 失败，独立 batch/分轮与合法依赖分轮成功，12 个 owned child 全回收。

全仓 Ruff、契约冻结及公开内容扫描均通过，exit 0。受影响回归及发布检查的精确命令、日志与退出码在 `.toolalign-local/p06-g5-observation-oracle-r2/`，入口为 `evidence-index.json`。最初检查代码使用未序列化的 budget 属性导致的失败、修订前 v1 假阳性及早期原型记录均保留。

公开改动只含新 oracle 模块、必要导出、runner 选择、原创测试、本报告和交接。未改 D1 数据包或共享状态；原 48 题继续整组隔离，不恢复测试身份。Q1-G5-CORPUS-001 待独立 R1/Q1 复验，计数由 S1 维护。本轮无 GPU、固定模型、训练、正式模型评测或依赖安装。
