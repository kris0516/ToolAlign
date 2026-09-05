# 01｜架构、接口与工程边界

状态：P00 已建立契约与 Protocol 候选，详见 [冻结说明](12_CONTRACTS_V1.md)。实现模块仍为后续任务；不能把目录骨架视为训练/执行/服务实现。

## 1. 两条独立链路

```text
训练链路
sources → normalizer → license/de-dup/split audit → tokenizer/length audit
        → SFT backend → validated SFT snapshot
        → train-only negative generation → semantic oracle → preference pairs
        → DPO backend → candidate model → immutable evaluation → release decision

运行链路
request → schema/auth/budget gate → tool-policy model → safe parser
        → registry allowlist → schema validator → local tool executor
        → observation → bounded next step → final structured result
                               ↓
                  trace + task oracle（评测侧，不给模型看）
```

训练代码与线上服务不共享隐式可变全局模型。主机 GPU 是稀缺资源；正式训练时停掉驻留推理 worker，而不只减少并发。

## 2. 目标代码目录与所有权

| 目录（P00 后创建） | 唯一主责任角色 | 内容 |
|---|---|---|
| `src/toolalign/contracts/` | S0 | 版本化 schema、shared types |
| `src/toolalign/data/` | D1 | 导入、规范化、切分、审计 |
| `src/toolalign/training/` | T1 | SFT/DPO backend adapter、参考损失 |
| `src/toolalign/evaluation/` | E1 | 指标、协议、BFCL 适配 |
| `src/toolalign/tools/` | E1 | 白名单工具、沙箱、oracle |
| `src/toolalign/inference/` | I1 | 模型加载、cache、generation |
| `src/toolalign/service/` | I1 | API、队列、生命周期与权限 |
| `configs/`, `pyproject.toml`, lock files | S0 | 集中合并 worker 的依赖请求 |
| `tests/<module>/` | 对应 worker；R1 审查 | 测试，不允许修改已有期待值只为让测试通过 |
| `reports/` | 产出方；S0 发布 | 去敏实测摘要、实验索引 |

## 3. 公共数据契约

`toolalign.example.v1` 包含：`example_id`、`source`、`source_revision`、`license_id`、`source_record_hash`、`group_id`、`split`、`messages`、`tools`、`expected_action`、`category`。`expected_action` 仅训练/评测侧可见，不送入推理输入。

`toolalign.tool.v1` 包含：`name`、`description`、`parameters_json_schema`、`tool_version`、`side_effect_class`、`timeout_ms`。首版只允许 `read_only` 与严格隔离的 `sandbox_only`；生产写操作不在允许集合。

`toolalign.preference.v1` 包含：共享 prompt/工具 schemas、`chosen`、`rejected`、双方验证结果、`preference_reason`、来源 task/group、生成模型 revision、生成参数、oracle version。不允许把两个不同问题的回答配成 preference pair。

`toolalign.run.v1` 包含：run ID、Git commit、数据/模型/adapter/tokenizer/template hash、backend/dependency versions、seed、硬件、资源策略、训练 token 与 step、resume 语义、时间、退出状态、artifact manifest。

`toolalign.trace.v1` 每条包含：trace ID、event 序号、model identity、tool call/result、parse/validation failure、预算消耗、deadline/latency、最终 task outcome。只公开脱敏摘要；完整失败样本也要过来源/隐私审查。

## 4. 统一调用界面

由 P00 冻结 Protocol，具体实现不能夹带 evaluator：

```text
ModelBackend.generate(request, generation_config) -> ModelOutput
ToolRegistry.validate(call) -> ValidatedCall | Rejection
ToolExecutor.execute(validated_call, sandbox_context) -> ToolResult
TaskOracle.score(task, trace, final_result) -> TaskScore
TrainingBackend.train(config, data_manifest) -> TrainingArtifact
ArtifactStore.resolve(immutable_id) -> VerifiedArtifact
```

`ModelOutput` 同时保存 raw text 和解析后的结构。解析失败不是自动“修成功”；修复器若存在必须作为独立配置记录和消融。

返回成功状态前必须区分：语法合法、schema 合法、执行完成、目标达成。第四项由独立 oracle 确定，不能仅靠模型自评或工具 HTTP 200。

## 5. 受限运行状态机

`RECEIVED → VALIDATED → GENERATING → PARSING → TOOL_EXECUTION → OBSERVING → FINALIZED`。

失败分支包括 `REJECTED`、`BUDGET_EXHAUSTED`、`TIMED_OUT`、`CANCELLED`。只有被声明为可重试的工具错误才能进入恢复循环。首版上限：3 次模型决策、2 次工具执行轮次、每次响应 token 上限与统一 wall-clock deadline；具体数字由 P01 实测后确认并写入配置，禁止运行中无限扩展。

状态的 deadline 使用可序列化 UTC expiry；进程内单调时钟只用于本次耗时计量。重新执行不能重置总预算。工具错误和传输错误分开归因。

## 6. 并发、幂等与恢复

首版模型进程 concurrency=1，CPU 数据加工可以并行。相同 idempotency key 绑定相同 request hash；key 相同、payload 不同必须拒绝。模型推理可重新计算，但未来涉及写操作时必须有持久化 journal 与权限验证，不能以“模型请求幂等”推导“工具副作用 exactly-once”。

训练 checkpoint 保存是否包括优化器、RNG、数据顺序决定恢复级别：`weights_only_restart` / `full_state_resume`。没有完整状态就不能称精确断点续训。

## 7. 未来扩展的预留点

backend adapter 允许 MLX 与可选 PyTorch/CUDA；不假定权重格式可直接互换。工具采用版本化 registry；服务 API 与 CLI 复用 contracts；评测 manifest 随 release 固定。未来引入数据库、外部工具、身份隔离时，走新 ADR 和独立安全验收，不在首版留无限权能接口。
