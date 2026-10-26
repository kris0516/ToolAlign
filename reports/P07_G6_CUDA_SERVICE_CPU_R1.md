# P07 G6｜受限服务 CPU r1

2026-10-27，T1。基于授权头 `ef885c035f2b08a5ad781f040d4ee8867f2c79ba` 完成[服务任务](../coordination/tasks/P07_G6_CUDA_SERVICE_R1.md)。固定 M1 服务的 prepare、真实 child 生命周期、loopback HTTP、鉴权、队列、幂等、截止、取消及 Colab 白名单已实现。最终 25 项服务检查通过，24 个原创 CPU 服务运行共 35 个 child 全部实际回收；其中两项在完整父服务进程上分别发送 SIGINT、SIGTERM，确认退出、summary 与 GPU lease 释放。

另有 2 项 backend 检查、14 项服务控制器检查，以及 108 项既有受影响检查通过；3 项既有 pip parser 检查因环境未安装 pip 跳过。共 149 项不同检查取得通过证据。源码与测试由本报告所在的 Git 提交定位，具体命令和受检文件哈希保留在私有索引。本包交 S1 与 E1 客户端集成、R1 独立审核；实际 CUDA 服务仍 **NOT_RUN**。

## 实现与边界

`CUDAGenerationBackend.prepare()` 抽出原 tokenizer 初始化及加载路径，仅允许父进程构造的 backend 在 owned model child 内执行。prepare 不生成假请求或做 warmup。`CUDAServiceBackend` 固定 M1/G3 step743，沿用原 CUDA 解码与单项 `PrefixCache`，lease 身份为 `P07-G6-SERVING/serving`。初次启动的 120 秒包含父进程文件预检；重载各自最多 120 秒，均计入服务总预算。

服务父进程运行短 HTTP 控制面和一个串行调度线程，后者独占 child 的启动、等待与回收。只有当前 epoch 的真实加载回执、固定模型身份和存活进程同时成立才 ready。HTTP 单连接有 2 秒绝对处理上限；慢连接不能拖住调度器的请求截止或停服清理。SIGINT/SIGTERM 进入同一停服流程：停止接受、结束待执行项、回收 active child、确认 lease 不再由旧 PID 持有、写 summary。

[冻结 HTTP 契约](../docs/18_RESTRICTED_CUDA_SERVICE.md)的字段保持不变。输入只接受 `local-devops.v1` 原样工具子集，允许空集；服务不执行工具。principal 来自私有 token 映射，通过 IPC 进入 cache 身份。同 run/principal/key 的相同 body 回读先于容量拒绝；不同 body 冲突。按 key 的 GET 查询始终只读，未知或越权均 404。

一个 active、最多两个 pending、64 条累计记录；实际派发尝试上限由配置限定为至多 12，失败和取消同样消耗尝试额度。接受时固定单调时钟截止，队列和重载等待计入原截止，重复提交不延长。queued 取消/过期不执行模型、不杀 active。active 取消/超时先进入 stopping，确认回收后才写终态；未确认时保持 stopping/cleanup_unconfirmed 并停止接受。

完成要求原文独立 Action parse、固定身份、完整合法 usage、finish=stop 和截止共同通过。`completed` 不评分工具语义或任务答案。失败仍保留可得 raw/usage；整个 backend packet 超限时沿用原 SHA/字节数诊断，诊断保留的完整原文也独立 parse。未知 token、TTFT、prefill、decode 和 cache 计数为 null。旧 `DecisionSession` 只复用纯结果 gate，原 3 次/90 秒限制不变。

## 启动和制品

固定入口：

```sh
python -m toolalign.service validate --run-config <private-run.json>
python -m toolalign.service serve --run-config <private-run.json>
```

`validate` 只验证配置和私有 auth 文件，不加载模型。生产 `serve` 复用 source/dependency 身份验证及批次模型文件验证，固定使用 CUDA M1；没有可选任意 backend、CPU fallback 或 HTTP 管理接口。

`toolalign.service-run.v1` 精确字段如下，完整实际值由 S1 冻结在私有 JSON：

| 组 | 字段与要求 |
|---|---|
| 授权 | `schema`, `authorized_by="S1"`, `run_kind="serving"`, `run_id`, `source_commit`, `config_sha256` |
| 模型 | `model_root`, `checkpoint_dir`, `checkpoint_sha256`, `adapter_sha256`；固定当前 M1/G3 常量 |
| 环境 | `dependency_lock`, `dependency_lock_sha256`, `repository`, `lock_root`；两个 repository 路径指向同一 checkout |
| 私有输出与认证 | `output_dir`, `auth_file`；新输出目录，auth 文件权限不得向组或其他用户开放 |
| 监听与 cache | `listen_host="127.0.0.1"`, `listen_port`, `cache_enabled`；端口整数 0–65535，0 由 OS 分配并写入 listening 制品 |
| 上限 | `max_generations` 1–12、`max_wall_seconds` 6–900、`max_output_bytes` 至多 256 MiB |

所有路径必须为绝对路径。auth 文件为 `{"schema":"toolalign.service-auth.v1","tokens":{"principal":"private-token"}}` 的结构；1–8 个 principal，名字 1–64 位字母/数字/下划线/短横线，token 为互不相同的 32–256 位同类 ASCII 字符。示意字符串不是可用凭据。token 值不进入 argv、HTTP 返回、模型输入或制品。

私有输出含 `run.json`、`identity.json`、`listening.json`；每条请求的原始 `input.json`、`accepted.json`、实际 `started.json`、必要的 `stopping.json`、`terminal.json` 或 `cleanup-unconfirmed.json`；每个 worker 的 started/ready/closed 记录；最终 `summary.json`。summary 的 `generation_attempts` 统计已派发尝试，不将 queued 取消计为生成。所有模型任务分数均为 NOT_SCORED。

不可变 journal 按写入字节计账；每个接收记录、worker 元数据、活跃 IPC 和最终 summary 均预留预算。warm child 的已确认 IPC 被删除，预算计数不与删除动作并发扫描同一文件。容量拒绝不占 key、request ID 或尝试额度。总截止前 5 秒开始清理；输出目录不能自动续跑，控制器继续约束 run 身份。`scripts/colab/support.py` 仅新增固定 `toolalign.service serve` 白名单和 900 秒/256 MiB/12 次分支，G6 分配上限 7,200 秒；其他 controller 文件没有改动。

## 验证与失败保留

使用既有 Python 3.14 CPU 环境和既有 Python 3.12 tensor CPU 环境，没有安装依赖、下载或加载固定模型、访问 GPU 或启动 Colab。证据入口为 `.toolalign-local/p07-g6-cuda-service-r1/evidence-index.json`，包含逐次命令、退出码、stdout/stderr、源码哈希、实际请求/终态、进程与 lease 制品。

| 回执 | 结果及范围 |
|---|---|
| `service-tests-05` | exit 0，25 passed；真实 loopback、prepare/ready、鉴权与越权、原样 schema、队列/64 记录/生成/输出上限、幂等、排队及重载截止、active 回收、完整父进程两种信号退出 |
| `final-process-evidence.json` | 最终 24 个服务运行、35 个实际 child 均 reaped/directory_cleaned，交付前 PID 不再存在；一个 MOCK_ONLY 回收确认故障保留未确认状态 |
| `focused-tests-02` | 124 passed、1 failed、3 skipped；通过部分含 2 个 backend、14 个服务控制器及 108 个既有 CUDA generation/evaluation、DecisionSession、Colab 检查。失败是下述测试客户端 principal 错误，最终服务矩阵已覆盖修正 |
| `idempotency-03` | exit 0，1 passed；定点确认测试修正，不重复计入 149 项 |
| 原创真实 tensor cache | 原创随机小 Qwen3，少于 4,096 参数，CPU 实际 DynamicCache；五请求 principal 顺序 alice/alice/bob/bob/alice 的命中为 0/11/0/11/0、prefill 为 12/1/12/1/12，输出一致；真实 owned child 回收 |
| 静态交付检查 | Ruff、冻结契约、公开内容及 diff 空白检查，具体命令/输出保存在索引 |

cache 检查只把原创模型设备设为 CPU，实际调用 service child 的 principal 绑定与既有 `_decode` 的身份 key；没有以 MOCK_ONLY 数据代替真实 cache 命中。真实 CUDA 加载、CUDA latency、Mac/SSH/Colab 全链路与模型语义效果未运行。

保留三类开发失败及原退出码：`service-tests-01` 的 1 failed/20 passed 是原文与重新序列化 JSON 字段顺序比较错误；`focused-tests-02` 的失败是测试用 alice 查询 bob 记录，服务正确返回 404。两项只修测试断言/调用。`edge-tests-04` 为 1 failed/3 passed，确认 backend packet 超限但保留完整 raw 时漏做独立 parse；修正生产服务后最终 25 项通过。没有改写模型输出或放宽 Action gate。

回收未确认检查显式注入“真实 child 已回收之后，close 确认抛错”，核对状态仍为 stopping、finished 为 null、无 terminal 文件且停止接受。它证明故障处理分支，不能当作真实无法回收进程的实测。上述 CPU 证据也不替代 R1 独立审核或 G6 实际服务验收；G5 的两模型 0/28、无 DPO checkpoint 和无 L2 官方模型分数保持。
