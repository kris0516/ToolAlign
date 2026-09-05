# 12｜P00 契约冻结说明

版本：`toolalign.contracts.v1`，包含五类 `toolalign.{example,tool,preference,run,trace}.v1`。P00 分支上的文件是冻结候选；只有 R1 独立审查通过、S0 合并且 main 验证后，才成为 P01–P03 可使用的契约。精确字节登记在根目录 `contracts.v1.lock.json`，Git commit 是交付真源。

## 安装与验收

```bash
uv sync --locked --python 3.14
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked python scripts/check_contract_freeze.py
uv run --locked python scripts/check_public_content.py
uv run --locked toolalign contract-digest
uv run --locked toolalign validate tests/fixtures/contracts/example.json
uv run --locked toolalign schema example
uv build
```

Python 声明范围为 3.11–3.14；本机 P00 使用 3.14.7。CPU 包仅依赖锁定的 jsonschema 及其传递依赖，不引入 MLX、PyTorch、模型下载或付费 API。CI 检查 Python 3.11 和 3.14，未取得运行结果前不声称 CI 已通过。`uv.lock` 由 S0 所有；P01 提交 backend 依赖申请，由 S0 实际核验后集中修改。

`toolalign validate` 成功返回 0，输入错误返回 2；支持 `--kind` 与 `--jsonl`。空输入、重复 JSON key、非有限数值、类型强制转换和未知 schema version 均拒绝。诊断只输出受信 schema 路径，输入的自由字典键名不回显；所有身份/时间 pattern 使用完整字符串匹配，末尾换行不能绕过。源码直接调用 `validate_record` 时同样必须传原生 JSON 类型。序列顺序有意义，哈希使用 UTF-8、排序对象键、无空白、有限 JSON 数值的 SHA-256；不把这个规则叫作 RFC 8785。

## Wire records

JSON Schema Draft 2020-12 定义位于安装包内 `src/toolalign/contracts/v1.json`。`schema_for(kind)` 输出可离线使用的完整 schema，`validate_record` 还检查跨字段语义。**只运行第三方 JSON Schema validator 不等于完整验收**。

| Record | 必填信息与主要规则 |
|---|---|
| example | ID、source/revision/license/source hash、group/split、messages/tools、expected_action/category；标签调用必须指向声明工具且参数合法 |
| tool | name/description、闭合参数 schema、tool_version、side_effect_class、timeout_ms；仅 read_only/sandbox_only |
| preference | 单份共享 messages/tools 与 prompt_hash、chosen/rejected 原始 completion、双方 oracle 验证记录、task/group、train split、生成身份/参数、oracle version |
| run | Git/data/model/adapter/tokenizer/template 身份，backend/dependency/seed/hardware/resource policy，token/step、resume、UTC 时间/状态/退出码、artifact manifest |
| trace | trace/request ID、event_index、model identity、call/result、parse/validation failure、累计预算、deadline/latency、task outcome |

所有列出的 wire 字段都显式存在，可空字段写 JSON null；未声明字段拒绝，禁止悄悄扩展。模型/数据/trace hash 只提供身份关联，schema 不能证明文件真实存在、许可正确、没有数据泄漏或 oracle 判定正确，后续任务必须另验。

Messages 是**下一次 assistant 决策之前的输入前缀**，不能包含目标 completion。每条 message 显式包含 role、content、tool_calls 和 tool_call_id。输入最后角色为 user 或 tool；历史工具 observation 必须匹配 pending call，所有 observation 结束后才能开始下轮。标签在 `expected_action`，动作种类固定为 `tool_calls`、`final`、`clarify`、`refuse`；调用含 call_id/name/arguments；目标 call_id 不能与输入前缀历史重复，保证合法目标可以成为下一步历史。需要多步轨迹时，每个受监督 assistant 决策由 P02 单独产生一个前缀样本，保持相同 group，不能跨 split。

`model_input_from_example` 返回**仅** messages/tools 的独立副本。`OracleTask` 与模型输入类型分开。投影只保证不携带元数据字段，不能发现有人把答案或秘密藏在自然语言 content 中；P02/P03 仍必须审查样本与 oracle 隔离。

Preference 只能为 train split。chosen 必须 success、rejected 必须 failure，两条 completion 不得相同；unknown/tie 不能进入有效 pair。prompt_hash 覆盖共享的 messages 和完整 tools（含版本）。chosen/rejected 保存原始 completion 字符串以容纳格式错误负例；不得嵌入不同问题的 prompt。R1 和人工抽样仍需查看 trace 验证这些声明。

Run 的 reference_model_hash 在 DPO 时必填，但 schema 无法证明它属于已验收 SFT，P01/P05 负责实际验证。running 的 ended_at/exit_code 必须均为 null，终止运行必须都有值且时间非倒序。artifact_id 等于内容 sha256，relative_path 必须在私有 run root 下；实际解析器还需阻止 symlink 逃逸并核验大小/哈希。成功执行和成功完成语义任务是不同状态；所有终止 trace 都必须带 outcome，允许 not_scored/unknown 并由评测规则处理，不能从分母静默删除。

## 工具参数 schema 子集

首版每个工具参数根是闭合 object（additionalProperties=false）；嵌套只接受显式单个 object/array/string/integer/number/boolean/null 类型。支持 properties/required、items 与长度/范围/enum 限制，最长深度 12，每个对象最多 128 个属性。array 必须声明 maxItems ≤ 1000，string 必须声明 maxLength ≤ 16384。工具 timeout 为 1–60000ms。

关键词还必须适用于当前 type，例如 object 不允许 items、string 不允许 properties；不能利用 JSON Schema 默认忽略无关关键词的行为隐藏 schema。禁止 `$ref`、远程 `$id`、组合 schema、正则与未声明关键词；不下载远程 schema，不执行模板或内容。P02 遇到超出子集的来源条目必须隔离、计数并请求 S0 决策，不能降低约束或自动扩大工具能力。这个校验器是数据入口，真正的 registry/executor、沙箱路径、取消和 deadline 由 P03 实现，P00 没有执行任意工具。

## 模块接口与所有权

`src/toolalign/contracts/interfaces.py` 定义同步 Protocol；同步意味着调用方负责进程/队列隔离，不承诺阻塞调用天然可取消。

| 接口 | 输入 → 输出 | 实现负责人 |
|---|---|---|
| ModelBackend.generate | ModelInput + GenerationConfig → ModelOutput | T1/I1 |
| ToolRegistry.validate | ToolCall → ValidatedCall 或 Rejection | E1 |
| ToolExecutor.execute | ValidatedCall + SandboxContext → ToolResult | E1 |
| TaskOracle.score | OracleTask + trace + final_result → TaskScore | E1 |
| TrainingBackend.train | TrainingConfig + DataManifest → TrainingArtifact | T1 |
| ArtifactStore.resolve | immutable_id → VerifiedArtifact | 由 S0 在后续任务明确分配 |

TypedDict/dataclass 只声明 Python 接口，不能替代输入校验和权限边界。executor 必须把 ValidatedCall 与当前 registry_hash/tool_version 重新绑定并检查策略，不能把任意构造的 dataclass 当作授权。ModelOutput 保存 raw_text 和解析动作/错误；修复输出单独配置与评测。SandboxContext 携带 UTC deadline 和显式取消信号，进程内用单调时钟计时；未来重试不能重置累计预算。

公共 contracts/runtime、configs、顶层配置、lock files、CI/检查脚本、正式 ADR 和看板归 S0。D1 只负责 data，T1 负责 training，E1 负责 tools/evaluation，I1 负责 inference/service；各自测试与交接文件随任务包授权。当前模块目录里的说明不代表后续实现已经完成。

## 资源接口与预注册参数

```python
from toolalign.runtime import GPULease

with GPULease(task_id="P01", worker_alias="T1", run_id="unique-run-id",
              expected_job="compatibility smoke", memory_strategy="P01 declared budget"):
    # 模型导入/加载及驻留生命周期必须在租约内；此处没有模型实现。
    pass
```

GPULease 使用 `git rev-parse --git-common-dir` 得到共享目录并规范化路径，锁为 common dir 下 toolalign-runtime-locks/gpu0.lock。使用非阻塞 POSIX flock，等待有上限；到时失败，不进入模型代码。锁文件保留同一 inode，不以删除文件释放锁。正常结束/异常/进程退出由 OS 释放；不根据时间到期强制解锁或 kill 未知进程。

`toolalign lock-status` 读取当前本机私有 owner 或 last_owner；打印内容不可提交公开仓库。PID、进程开始时间、host fingerprint、run/task/worker、取得时间和预计作业写在私有锁文件中。该锁是**同一 repository worktree 间的协作锁**，不是阻止任意进程使用 GPU 的安全沙箱；独立 clone 或其他项目需要 S0 统一安排，不能默认有全机跨仓库互斥。

`configs/protocol.v1.json` 预注册 non-thinking、concurrency=1、最多 3 次模型决策/2 次工具轮次。256 output tokens/30 秒是未实测的保守配置候选，P01 核准前不当作吞吐/内存结论。偏好人工抽样为 min(total, max(100, ceil(total×10%)))，误标率严格大于 5% 阻断正式 DPO，unknown 计为误标；这项阈值在观察结果前确定。

## 冻结、审查与恢复

版本冲突或公共依赖变化由 worker 向 S0 提交请求；S0 先写 ADR、更新契约/hash/test，再经审查合并，才能发布新 base。不能只改 hash 让检查通过。P00 的后续基础修复若不改变 wire/接口语义可保留 v1，并记录新 commit；不兼容变更须新版本或明确迁移方案。

公开内容扫描同时检查 Git index blob 与工作副本/未跟踪候选（内容、模式、大小），避免“暂存敏感内容后只清理工作副本”的漏扫；并对秘密、私有路径/对话 ID、大文件与模型/数据文件做启发式筛查；不替代独立审查。原始日志、环境绝对路径和任务映射留在 .toolalign-local。项目长期 goal 与 30 分钟对话跟进负责唤回 S0；本机须开机且 App 运行。恢复时依据 Git、看板和 handoff，不依赖别的对话记忆。

实现依据：[jsonschema 验证接口](https://python-jsonschema.readthedocs.io/en/stable/validate/)、[Python flock](https://docs.python.org/3.14/library/fcntl.html)。
