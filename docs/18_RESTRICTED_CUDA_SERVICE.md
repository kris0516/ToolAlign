# 18｜受限 CUDA 服务与 Mac 客户端契约

G6 r1，2026-10-27。S1冻结共享HTTP接口，T1实现服务和Colab接缝，E1实现Mac客户端。本文替代旧P07的MLX本机worker与FastAPI设想，不改变`toolalign.*.v1`已有Action、ModelInput或ModelIdentity。正式GPU运行仍须CPU、独立R1与具体运行配置通过。

服务只在Colab `127.0.0.1`监听；Mac经已存在命名会话的OpenSSH本地转发访问。单个固定M1/G3 step743模型返回Action建议，Mac独立校验后执行`local-devops.v1`固定只读工具。原始模型失败原样保留，接口完成不等于完整任务成功；G5两模型0/28、M2与L2的处置继续适用。

GPU lease由真实CUDA child持有，服务父进程负责短HTTP处理与串行调度，复用既有OwnedProcess与CUDA/cache。新增服务专用child循环，不扩大旧DecisionSession/harness的默认次数或时间。prepare只做加载/身份核对/CUDA同步，无隐含warmup生成；取得当前child的ready证据后才接受请求。

服务最多一个active、两个pending、64条已接受记录，一个cache entry。启动/重载每次最多120秒，总服务墙钟900秒，输出上限256MiB。每请求至多30秒是包含排队与重载等待的**决策截止**；取消/截止后的回收尾段另计complete wall。服务总截止前5秒停止接受/生成并开始回收，既有Colab外层900秒硬限负责最终收尾。回收未确认不能伪记cancelled/timed_out终态，保持stopping与cleanup_unconfirmed并停止接受。所有安装、启动、请求、失败、传输和清理计入分配账目。

模型版本仅通过完整停止后重新启动切换，旧制品保留；进程重启销毁cache。client不能选择路径/模块/温度/tenant。token只在私有文件及HTTP header内，认证映射决定principal；不进入argv、公共日志或返回。不存在服务crash自动重放：新启动必须新run_id/新输出目录，旧started无终态记录保持interrupted/unknown。

## HTTP JSON


以下统一 `schema="toolalign.service-http.v1"`。端点对象只接受列出的字段，不改变冻结的 Action/ModelInput/ModelIdentity 定义。UTF-8 普通有限 JSON，重复 key 拒绝。HTTP body 上限 524288 bytes；raw model packet 沿用 131072 bytes。无 streaming、WebSocket 或兼容供应商 API。

除 `/healthz` 外都要求 `Authorization: Bearer <token>`。token 只在私有文件及 header 中；接口不接受 `tenant/principal/model_path/checkpoint_path/temperature/cache_enabled/oracle` 等附加字段。principal 不出现在 URL，不用 token 字符串作为 cache key。

### 接收一个决策

`POST /v1/tool-decisions`，必需 header `Idempotency-Key`：1–128 位 `[A-Za-z0-9_-]`。

```json
{
  "schema": "toolalign.service-http.v1",
  "service_run_id": "S1-frozen-run-id",
  "model_input": {"messages": [], "tools": []},
  "seed": 42,
  "timeout_ms": 30000
}
```

上例 messages 只占位，实际须满足已有 ModelInput 历史校验。seed 是整数 `0 <= seed < 2**63`；timeout_ms 是整数 `1..30000`，布尔值不算整数。`payload_hash=canonical_hash(完整上述 body)`；`input_hash=canonical_hash(model_input)`。实际 deadline、principal 和采样参数由服务确定。M1、step743、temperature=.7/top_p=.9/top_k=0、256 输出 token、thinking=false 均由启动配置固定。输入编码长度 + 256 必须 <=2048，超出保留 context_overflow，不截断 schema/history。

新接收或幂等回读的非终态返回 202；幂等回读终态返回 200。JSON 精确字段：

```json
{
  "schema": "toolalign.service-http.v1",
  "service_run_id": "S1-frozen-run-id",
  "request_id": "server-generated-id",
  "status": "queued",
  "replayed": false
}
```

status 是该请求当前状态，不保证 handler 返回前仍未开始。`request_id` 由服务器生成；replayed 只表示是否已有同 key 同 payload 记录。认证/契约/容量拒绝不占用请求 ID、key 或模型尝试数。

### 查询与取消

`GET /v1/tool-decisions`使用同一`Idempotency-Key` header只读查询当前认证principal的已有请求，返回200及下述RequestState；不存在或越权均为404 `request_not_found`。该接口不创建记录、不刷新deadline、不触发生成，客户端还须核对返回的service_run_id和payload_hash。客户端丢失POST响应时可在原截止内按原key重读；本地截止后只允许此只读查询和cancel，不能重POST以避免原请求未到达时意外新建。

`GET /v1/runs/{request_id}` 返回 200；`POST /v1/runs/{request_id}/cancel` body 必须为 `{}`。取消 queued 请求立即返回 200/cancelled；取消 active 请求先返回 202/stopping；取消已终态请求返回 200 原记录，不能再杀已用于另一请求的 worker。

两者共用下表的 **RequestState** 精确字段。非本人 request_id 与不存在 ID 都返回 404，不能先泄露是否存在。

| 字段 | 类型与含义 |
|---|---|
| `schema, service_run_id, request_id` | 固定版本、固定服务 ID、该请求 ID |
| `input_hash, payload_hash` | 两个 canonical SHA256 |
| `status` | 非终态 `queued/running/stopping`；终态 `completed/parse_failure/budget_exhausted/cancelled/timed_out/infrastructure_error` |
| `reason` | null 或稳定代码，如 `invalid_raw_action/context_overflow/response_token_limit/queue_deadline/request_deadline/cancel_requested/worker_exited/worker_start_failed/service_stopping/cleanup_unconfirmed`；不返回异常文本或本机路径 |
| `accepted_at_utc, deadline_utc` | 服务端记录的 UTC 字符串；执行判断用单调时钟 |
| `started_at_utc, finished_at_utc` | UTC 字符串或 null；started 是实际派发时间，未派发不能填写 |
| `worker_epoch` | 服务内从 1 递增的生命周期编号或 null，不能由客户端指定 |
| `worker_cleanup` | `not_started/live/reaped/unconfirmed`；completed 可以 live 以保留 warm/cache；active 取消/超时不得以 live 标为终态 |
| `result` | null 或下述 Result；即使失败，收到的真实 raw/usage 仍保留 |
| `timing` | 下述 Timing；不可得字段为 null |

**Result** 精确字段：

- `raw_text`: string/null；空字符串与 null 区分。
- `finish_reason`: 原 ModelOutput 的 `stop/length/timed_out/cancelled/error` 或 null。
- `raw_action`: 原文独立 parse 得到的 Action/null；`raw_action_valid`: bool；`raw_parse_failure`: null 或稳定代码。backend parsed/repaired 结果不能替代原文。
- `model_identity`: 原七字段 ModelIdentity 或 null；完成必须等于启动固定身份。
- `input_tokens, output_tokens`: 非负整数/null；`token_accounting_complete`: bool。未知不能填 0。
- `diagnostic`: null 或 `{raw_sha256, raw_size_bytes, raw_truncated}`，复用原 oversize 原文诊断；字段无可用值时为 null，raw_truncated 为 bool。

**Timing** 精确字段均为非负数/null：`queue_seconds`（接受至派发或排队终止），`child_generation_seconds`，`ttft_seconds`，`prefill_seconds`，`decode_seconds`，`cleanup_seconds`，`complete_wall_seconds`（接受至终态，含队列/清理）；另有非负整数/null `cache_hit_tokens, prefill_tokens`。TTFT/prefill/decode 沿用 decode kernel 的口径，不含 startup/queue。完成时固定这些值，非终态尚未完成的量保持 null。

`completed` 要求真实身份、有效 usage、finish=stop、raw Action gate 和 deadline 均满足；它不判断工具语义或任务答案正确。返回的 Action 即使使用错误参数，也只能由 Mac 固定工具桥接按原规则拒绝/记录。

### 存活、就绪和身份

| 端点 | 精确 JSON 字段与 HTTP 状态 |
|---|---|
| `GET /healthz` | 200 `{schema, status:"alive"}`；只说明 HTTP 控制面存活 |
| `GET /readyz` | `{schema, service_run_id, ready, accepting, worker_epoch, reason}`；ready/accepting 为 bool；已加载且 live 为 200，否则 503；busy/队列满不把 loaded 改成 false，accepting 可为 false |
| `GET /v1/model-info` | 200 `{schema, service_run_id, source_commit, model_identity, checkpoint_sha256, dependency_lock_sha256, catalog_id, registry_hash, sampling, limits, cache}`；固定声明身份，是否实际 loaded 以 readyz 为准 |

model-info 子对象精确字段：

- `model_identity` 沿用 `model_id/model_revision/model_hash/adapter_hash/tokenizer_hash/template_hash/quantization`；catalog_id 固定 `local-devops.v1`，registry_hash 为完整 catalog manifest hash。
- `sampling={temperature:0.7, top_p:0.9, top_k:0, max_new_tokens:256, enable_thinking:false, seed_policy:"per_request"}`。
- `limits={context_tokens:2048, max_request_ms:30000, max_pending:2, max_records:64, max_body_bytes:524288, max_service_seconds:900}`。
- `cache={enabled:<启动固定bool>, max_entries:1, scope:"principal"}`。

客户端在提交前核对 S1 固定的 service_run_id 与 ModelIdentity，服务不能自行热换模型。loaded ready 必须还绑定当前 worker_epoch；前一 child 的 ready 文件不能给替换 child 使用。启动/重载使用单独有限时限并计入 900 秒；启动/每次重载上限为120秒，包含在服务总预算内。重载期间不接受新请求，已有未派发项仍按原 deadline 排队/过期，不补跑已 started 项。

### 统一拒绝

普通 API 拒绝对象精确为 `{schema, error}`，error 为稳定字符串；不包含全局日志、路径、token、其他 principal 的请求信息。唯一状态探针例外是已认证的 readyz：未就绪时仍返回上表的完整 readiness 对象并用 503。

| HTTP | error 示例及边界 |
|---|---|
| 400 | `invalid_json/invalid_request/invalid_model_input/unbound_tool_schema/invalid_idempotency_key` |
| 401 | `unauthorized` |
| 404 | `request_not_found`（含越权）或 `endpoint_not_found` |
| 409 | `service_run_mismatch/idempotency_conflict` |
| 413 | `request_too_large` |
| 429 | `queue_full/record_limit`；已有 key 可继续回读 |
| 503 | `not_ready/service_stopping/service_budget_exhausted/output_budget_exhausted` |

每个接口错误只是 HTTP 拒绝；已接收后发生的模型/worker 失败通过 RequestState 表示，不能用一次 500 替代持久终态。启停仍走既有 CLI/Colab 控制面，不新增 HTTP 管理/任意执行接口。
