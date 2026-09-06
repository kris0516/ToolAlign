# P03 CPU harness 使用与边界

本包实现 L0/本地 L1 开发验证。公开 fixture 全部为原创、虚构开发运维资源；`ScriptedCPUModelBackend` 回放显式脚本，输入/输出 token 计数是测试值。Qwen 推理、BFCL、正式隐藏最终测试、训练与 GPU 性能均为 **NOT_RUN**。实际命令与结果见 `P03_CPU_VERIFICATION.md`。

## 入口

```bash
uv sync --locked --python 3.14
uv run --locked python -m toolalign.tools --help
uv run --locked python -m toolalign.tools registry
uv run --locked python -m toolalign.tools demo \
  --cases tests/fixtures/tools/development.json \
  --output .toolalign-local/p03/demo
uv run --locked pytest -q tests/tools/ tests/evaluation/harness/
```

`--output` 必须是尚不存在的私有目录。CLI 只读取标为 `public-original-development` 的小型开发清单，固定为 validation split；不提供正式测试答案生成入口。每项保存完整开发 trace、原始输出、预算、oracle 判定、registry manifest 与自有进程回收记录；汇总包括 success/failure/unknown/not_scored，分母保留所有传入任务。

公共基础 CLI 没有修改；入口是 `python -m toolalign.tools`。CPU 基线的已知旧 sdist 选择问题由 S0 处理，本任务未运行默认 `uv build` 或 sdist。

## 六类固定工具

| 工具 | 输入与语义 | 资源边界 |
|---|---|---|
| `lookup_version_document` | 指定资源的对象、版本、发布日期、timeout、report ID | 固定 atlas/beacon 版本文档 |
| `query_build_report` | 指定报告的对象、版本、日期、测试通过/失败数 | 固定构建报告 ID |
| `filter_build_logs` | 精确日期与级别筛选，返回有界行与计数 | 固定日志资源 ID |
| `aggregate_run_records` | 精确日期、字段、sum/mean/count；空集合返回错误 | 固定结构化记录 |
| `compare_version_compatibility` | 按版本文档的最低 runtime 比较，保留比较依据 | 固定资源与 runtime 枚举 |
| `convert_numeric_units` | 有界数值、时间或字节单位；跨维度返回错误 | 固定单位表，无表达式解释器 |

六类均有成功执行、缺参拒绝与 schema 合法但语义错误的测试。无需工具/缺参澄清由独立任务覆盖；多步任务查文档再查其报告，故障恢复任务在同一预算内重试。工具表和资源表只由源码绑定，没有数据驱动注册接口。

## 冻结接口与执行授权

`LocalToolRegistry`、`LocalToolExecutor`、`SemanticOracle`、`ScriptedCPUModelBackend` 对接冻结的 `ToolRegistry`、`ToolExecutor`、`TaskOracle`、`ModelBackend`。`LocalHarness.run(example, task, backend, sandbox_context, model_identity=...)` 返回 `HarnessResult`，每个 trace 事件均先通过 `validate_record(..., "trace")`。

Registry manifest 包含明确的 registry version、完整 tool spec、参数 schema hash、源码实现名与 catalog 源文件 SHA-256；整体 canonical hash 绑定所选工具集合。重复名称、冲突描述和未知名称不能注册。对模型展示的已绑定同名 schema 必须与 registry 完全一致。`ta_` 历史 schema 可以作为数据展示，但无本地实现时仍拒绝；`sandbox_only`、URL、描述与来源声明不授予执行权。

`validate()` 保存一次性对象身份和原始调用 hash，返回独立参数副本。`execute()` 消费该身份并重验调用快照、当前 registry/hash/version、参数与 read-only 策略。即使字段完全相同，调用者自己构造/复制的 `ValidatedCall` 也不被接受；修改已验证 mapping、旧身份与重放均拒绝。子进程重新构造固定 registry，核对相同 hash 后才运行绑定实现。

工具参数没有文件路径、shell、Python、SQL、URL 执行或业务写入接口。JSON 拒绝重复键、非有限数值、非原生类型及过深/过大的结构；单调用参数上限 16 KiB、工具结果上限 16 KiB、模型响应 envelope 上限 128 KiB、模型输入/IPC 上限 512 KiB。冻结 action 已限制每批最多 16 个调用；同批按顺序执行，算一轮，总轮数仍为 2。

## 隔离、预算与记录

模型在一个由本请求创建的 spawn 进程中保留跨决策状态；每个工具调用另建一个自有 spawn 进程。IPC 是专属临时目录内的有界 JSON，通过原子发布结果避免父进程阻塞在管道读取。调用结束、超时或取消后，父进程只操作自己持有的 `multiprocessing.Process`，先 join，再在需要时 terminate/kill/join，并记录 PID、退出码与 reaped 状态。不会扫描或终止未知 PID；测试同时保留另一个独立进程，验证其不受影响。

这是**受信本地实现的进程与生命周期隔离**，不是运行任意不受信 Python 的 OS 权限沙箱。`SandboxContext.root` 是调用方提供的既有、解析后绝对目录，不能是符号链接别名；每次只在其下创建专属临时子目录。工具只访问源码中的固定资源。未来真实 backend 必须适配 spawn 生命周期；本包只实测可序列化的 CPU backend，不承诺 MLX 对象可直接跨进程传递。

构造前提具体如下：调用方先在父进程构造 `ModelBackend` 实例；其类必须可导入、状态必须支持 spawn 序列化。子进程导入模块并重建该实例状态，`generate()` 仅在该子进程执行，连续决策共用该实例。没有把父进程中的已加载 MLX 权重、C 扩展句柄、锁或 lambda/局部闭包跨进程传递的兼容证据。P04 可评估仅携带配置、在子进程首次 generate 时加载的 adapter，但模型/GPU 租约与工厂接口设计不在本包擅自扩展。

`LocalToolRegistry` 在父进程构造，内部有 `threading.Lock` 与一次性调用记录，**不会被 pickle 到子进程**。工具子进程收到的仅是固定名称列表、registry hash、已验证原生调用快照和受限 host-only 故障枚举；它在子进程重新构造 registry 并重新绑定源码。`LocalToolExecutor` 与 oracle 留在父进程。Python spawn 对受信 backend 状态使用其正常序列化机制，工具数据与模型生成的文本没有 pickle/代码加载入口。

严格沿用 `protocol.v1`：最多 3 次模型决策、2 次工具轮次，`max_new_tokens=256` 是**每次响应**上限；三次有效响应可累计 768 个输出 token。统一 deadline 为调用方 UTC expiry 与候选 30 秒上限的较早者，不在重试时重置。执行等待用单调时钟；同一个单调截止信号也传给工具取消检查，防止执行期间墙钟变化延长请求。回收所需的小段终止/join 时间包含在最终 latency 内。

只有显式 `retryable` 的工具错误/工具自身超时允许下一次模型决策；永久错误立即终止。原始完成文本独立解析，后端 `parsed_action` 只作诊断，不能覆盖 raw failure；修复器 **DISABLED**，没有额外免费生成。超界 raw 内容不继续保留全文，但记录其 SHA-256、字节数和截断标志，并保留可用 token 计数。进程在响应前被结束时，已收到的累计 token 不变，`token_accounting_complete=false` 标记未收到的计数，不能据此声称零成本。

## 语义 oracle

`OracleTask` 保留在评测父进程。模型子进程只收到 `ModelInput` 的 messages/tools 和 `GenerationConfig`；不收到 source/split、`expected_action`、评分标签或 oracle payload。公开 demo 的 `scripted_responses` 与语义真值分别声明；禁止用隐藏 oracle 构造脚本或训练答案。

`toolalign.semantic-local.v1` payload 包含 `version`、允许的最终 `{kind, value}` 列表、允许的执行序列列表。每一步明确 name、arguments、status、output、error_code、retryable。Oracle 比较对象、日期、版本、数值和完整允许策略，数值采用数学等值，布尔值不会被当作数字；已列出的单位等值/多种合法策略均可通过。自然语言自称成功、调用正确但最终数字错误、选错对象/日期/版本均失败。缺少/不支持的真值或无法解释的 trace 返回 unknown，仍留在分母。

这里使用有限、明确的结构化答案集合；没有模型自评或通用自然语言裁判。正式隐藏任务、P06 指标/分组 bootstrap、BFCL 适配、TTFT/prefill/decode 计时与真实性能结论留待相应任务验收。
