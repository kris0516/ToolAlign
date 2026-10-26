# P06 G5｜观察后决策 oracle CPU r2

2026-10-27，T1。基于授权头 `7e1f04172339c5f18af0268b68f44d1c3388b498` 完成[任务](../coordination/tasks/P06_G5_OBSERVATION_ORACLE_CPU_R2.md)。Q1 原有的依赖调用预提交、恢复调用预提交两条真实反例，在新版本下均从 success 改判为 failure；对应合法分轮轨迹仍为 success。两种允许策略及数值等价答案继续通过，布尔值不能冒充数值。此结果支持交 R1/Q1 独立复验 Q1-G5-CORPUS-001。

原 48 题继续整组隔离。本次只在私有副本中添加新评分约束并重新评分既有轨迹，没有恢复其独立测试身份；Q1-G5-CORPUS-002 的重构由 D1 负责。问题计数与关闭由 S1 维护，原首次未通过及原始 CPU 记录保留。

## 原因与实现

原 `SemanticOracle` v1 将执行与观察配对后比较平展步骤。两条错误轨迹的两次调用分别具有相同的 `model_decisions=1, tool_rounds=1`，但调用、结果与正确策略一致，因而被判成功。最后再生成答案不会证明第二个调用是在第一次观察之后才决定的。

新增 `evaluation/oracles/observation.py`，版本为 `toolalign.semantic-observation.v1`。复用原 v1 的真值验证、trace 身份与执行/观察绑定、答案及调用语义匹配，额外检查被任务声明的观察依赖。每条依赖要求：

- 源调用与其匹配观察的模型决策数、工具轮数一致。
- 在该观察之后、后继调用之前，存在生成、解析这一对新决策事件。
- 新决策的计数与后继调用一致：`generating.model_decisions + 1 = parsing.model_decisions = successor.model_decisions`，且大于源观察计数；生成/解析时的工具轮数相同，等于后继执行轮数减一，后继轮数大于源观察轮数。

v1 负责核对完整真值，包括没有匹配的其他策略。只有同一个策略的全部步骤与其全部依赖同时满足，才可成功；不能借用另一个策略的空依赖。缺少约束、非法索引或未知版本均为 unknown。显式空依赖允许独立 batch，不全局禁止同轮调用。

G5 `cuda_eval.runner` 通过 `select_oracle(task)` 显式选择版本。旧 `SemanticOracle` 源码与 `LocalHarness` 默认 oracle 未改；旧 v1 结果、Action/Trace/ModelInput 契约、工具实现、模型后端与依赖均保持。新模块不会导入模型框架。

## 给 D1 的格式与入口

`answers` 和 `strategies` 的形状完全沿用 v1。顶层仅增加 `after_observation`，并使用新版本。以下示例说明结构；`first_step` 等仍为 v1 的六字段步骤对象：

```python
payload = {
    "version": "toolalign.semantic-observation.v1",
    "answers": [{"kind": "final", "value": expected_answer}],
    "strategies": [
        [first_step, dependent_step],
        [alternate_first_step, alternate_dependent_step],
    ],
    "after_observation": [
        [[0, 1]],
        [[0, 1]],
    ],
}
```

`after_observation` 与 `strategies` 长度严格相同，每个元素是对应策略的依赖列表。`[i, j]` 使用该策略中从零开始的**工具步骤索引**，要求 `0 <= i < j < len(strategy)`，二者必须为整数，不能为布尔值。它表示第 j 个调用必须来自第 i 个调用观察之后的新模型决策，索引不是决策号或轮号。只有显式写出的依赖生效；没有依赖的策略写 `[]`。无需工具的允许答案可写 `strategies=[[]], after_observation=[[]]`。

步骤对象仍含 `name, arguments, status, output, error_code, retryable` 六字段。错误/超时观察到重试同样用 `[i, j]` 表达。最终答案仍由原 harness 在单独的最终模型决策中产生；无需额外的最终答案依赖语法。

```python
from toolalign.evaluation.oracles import select_oracle, validate_observation_task

validate_observation_task(task)  # 返回验证后的深复制；非法新版本真值抛 ValueError
harness = LocalHarness(registry, executor, oracle=select_oracle(task))
```

D1 构造与 CPU 作者验证须显式使用这一入口；不传 oracle 的历史 `LocalHarness` 仍是 v1。G5 runner 已接入选择。任务顶层、`OracleTask`、输入 reader 及 `oracle_payload.strategies` 均未变，E1 当前按步骤读取策略的分析接口可继续使用。隐藏 payload 不进入 `ModelInput`；生成进程只收到 `messages/tools`。

## 验证与证据

使用既有 Python 3.14.7/pytest 9.0.2 CPU 环境，没有安装依赖、固定模型加载、GPU、训练或正式模型评测。私有目录 `.toolalign-local/p06-g5-observation-oracle-r2/` 保存精确 argv、退出码、stdout/stderr、源码哈希与实际产物，入口为 `evidence-index.json`。

| 证据 | 结果与范围 |
|---|---|
| `baseline-reproduction.json`、`baseline-reproduction.log` | 修订前重现两条 v1 假阳性；期望 failure 的断言 exit 1，原失败保留 |
| `q1-revalidation-final.receipt.json`、`q1-revalidation.json` | exit 0；8 条原记录重新评分全部符合预期：两反例失败、两正确分轮成功、两种合法策略成功、数值等价成功、布尔反例失败；新模型/工具执行为 0 |
| `affected-regressions.receipt.json` | 141 passed，exit 0：含 26 项新 oracle 检查、完整 harness 目录及 G5 L1 受影响入口；未运行模型/cache 数值矩阵 |
| 最终回归中的原创 G5 实际入口 | 两个原创组件任务共 4 条 scripted CPU 轨迹：依赖 batch 失败、依赖分轮成功，独立调用的 batch/分轮均成功；12 个 owned child 全部回收，sandbox 清空 |
| 原创边界检查 | 删除或移动生成/解析事件、计数不对应时失败；不完整真值、其他策略损坏、版本未知、混合 trace 身份为 unknown；显式无需工具答案与答案类型检查通过 |
| `ruff.receipt.json`、`freeze.receipt.json`、`public-final.receipt.json` | 全仓 Ruff、4 份契约文件冻结核对、930 路径公开内容扫描均通过，exit 0 |

原始 Q1 evidence-index SHA256 为 `f53c050cd6847654836c943a6f74a82287817d81232960354f712b87fbe1aa6d`。重新评分前逐文件验证输入字节与该索引一致，不运行原完整 99 条作者轨迹。早期原型结果 `first-fixed-rescore.json` 仅作历史记录，最终接口以顶层 `after_observation` 与本轮最终回执为准。

最初新增检查将 `HarnessResult.budget` 属性误当成序列化字段，导致 1 failed / 22 passed，重新评分记录脚本也因此出现 KeyError；已改为读取真实序列化 trace 终态的 `budget_consumed`。两个错误日志及退出码均保留，没有改变生产评分规则或伪造预算字段。

未重跑未受影响的 CUDA/模型/cache 数值矩阵。本包交独立 R1/Q1 复验，不把 CPU 通过写成正式模型效果或独立审核通过。
