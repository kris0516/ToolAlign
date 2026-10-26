# P06 G5 CUDA 评测 CPU 首包

2026-10-26，T1。基于 S1 授权提交 `b39d20d2d4f7ea87ff1f60bf7f4c9e10976d6d00`，并落实补充协议 `34f841d72cf3f570486779590dfe542ee09a53d4` 的交错顺序和 raw Action 门控。原样接入 E1 工具候选 `6027096baf382bb0e50bf3f7463dd11fca0e19d1`（本分支 cherry 为 `5e6459e`），其 R1 独立审核仍在进行。本包交付可供 R1 审查的 CPU 实现；真实 CUDA、模型容量、正式评测和官方 BFCL scorer 均为 **NOT_RUN**。

## 已支持的结果

原创随机 Qwen3 的真实 `DynamicCache` 使相同请求的首轮 forward 从 **12 tokens 降到 1 token**，命中 11 tokens。原默认 decode、带计时的 cache off、冷 cache 和热 cache 的生成 token 完全相同；每步末位置 logits 在运行前固定的 `atol=2e-6, rtol=2e-5` 内一致。裸模型和真实 PEFT Q/V rank8、alpha16 LoRA 均通过。该结果支持继续做 Colab 上的 A2 容量与耗时测量，不构成真实模型速度或任务成功率结论。

M0 和 M1 共用底座加载器及文件验证：M0 的 `adapter_hash=null`，不读取 SFT checkpoint，也不调用 adapter 挂载或恢复；M1 复用原 G4 的完整选中 checkpoint 校验与实际 adapter 参数 hash。原 SFT/DPO 加载默认值仍为 `with_adapter=True`。父进程构造后端和导入评测入口不导入 Torch、Transformers、PEFT 或 MLX。

action-only 的空字符串、坏 JSON、合法无需工具动作保持不同结果。原文、finish reason、运行状态、backend 解析视图和独立 raw Action 结构合法性同时保留；backend 的修复结果不替代原文。执行器不执行 action-only 输出中的工具调用，也不接收 oracle 字段。后续 E1 必须以 `status=completed AND raw_action_valid AND 官方判对` 计算严格成功，并另外保留官方原始分。

## 实现与边界

- `model_io/cuda_evaluation.py`：固定 M0/M1 懒加载后端，调用原 owned model child。M1 为 step743，checkpoint `cfb02aec2279138c01f8b336abc08a588d0ab11efa8db68fd61ba0b6150b5d14`、adapter `973c440e29090892ad11d6d56b94bad4c98a5398c223e2b4302d7dba7c4640ed`。两者底座均为 Qwen3-1.7B revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`。
- `model_io/prefix_cache.py`：同一 owned child 内单项精确 token 前缀。key 绑定完整模型/adapter/tokenizer/template 身份和 tenant；进程身份及实例内存限定生命周期。缓存只保留上一次 prompt 的前 `n-1` tokens，丢弃生成 token；至少重算最后一个 prompt token。非匹配前缀、错 key、跨进程、异常、截止、超长输出和坏 Action 均不能复用失败状态。不会落盘或跨 child 传递 KV。
- `evaluation/cuda_eval/`：固定输入 reader、plan、单次调用、journal、完整分母导出与 CLI。复用已有 `OutputStore` 和 `OwnedProcess`，不新增远端控制器、RPC 或 HTTP 服务。
- `LocalHarness.run(..., recovery_enabled=True)`：默认保留原行为。False 在首次 retryable 工具错误或工具超时之后结束，reason 为 `recovery_disabled:<error_code>`；真实 scripted 检查中 on 为 3 次决策/2 轮工具且成功，off 为 1 次决策/1 轮工具且失败。不可重试错误和全局 deadline 保持原路径。
- `scripts/colab/support.py`：只新增固定命令 `toolalign.evaluation.cuda_eval evaluate`。L1 最多104轨迹、action-only最多120请求，正式总计划上限224；replay最多8序列单元/24请求、capacity最多2请求单独计数。全 G5 14,400秒/8 CU 及跨分配累计由 S1 控制，控制器拒绝超过14,400秒的分配预算，capacity 段拒绝超过60秒。输出上限1 GiB，所有 summary 写入均经过同一个预算检查。

固定生成参数与原 decode kernel 一致：上下文2048，每次256新 tokens，temperature0.7、top_p0.9、top_k0，按 seed 每次决策重置，thinking 关闭。主比较 cache off、recovery on。L1 每条最多3决策/2工具轮/30秒；单次 Action 最多30秒；replay 同一 child 最多3请求/90秒，每请求最多30秒。子进程冷加载在请求内，父进程完整文件预检单列并计入段时限。底座在 child 加载前后复核父预检得到的受信文件 stat。

## 输入接口

所有 JSON 为普通数据文件，按精确 SHA-256 读取。reader 拒绝未知顶层或 entry 字段。`ModelInput` 严格只有 `messages`、`tools`，沿用冻结契约及历史调用规则。

### L1

顶层字段必须为：

```json
{
  "schema_version": "toolalign.evaluation-tasks.v1",
  "purpose": "heldout-model-evaluation",
  "catalog": "heldout-devops.v1",
  "registry_hash": "<完整所选catalog的registry_hash>",
  "tasks": ["<entry>"],
  "recovery_task_ids": ["<固定A1子集，最多8个task_id>"]
}
```

每个 entry 的精确字段为 `task_id, family_id, group_id, category, example, oracle_task, faults, tool_names`。`example` 为完整冻结 Example；`oracle_task` 为 `OracleTask` 的字典表示，包含 `task_id, group_id, split, expected_action, oracle_payload`。两者身份相同、split 相同且为 `test` 或 `ood_test`。`faults` 沿用固定 host-only 故障表，`tool_names` 为该项 subset 名称列表。reader 调用 `LocalToolRegistry(tool_names, catalog_id="heldout-devops.v1")`，核对 readonly `registry.catalog_id` 及全部 advertised spec；空 subset 可用于无需工具项。每个候选使用独立 executor 和重新构造的故障队列。

`tasks` 最多48项、task_id唯一；family/group/category 为非空字符串。恢复题列表必须是这份 tasks 的不重复子集，其语义和分组隔离由 D1/Q1 冻结。本包不修改旧 train-only reader。

**已完成一项真实 catalog 组合检查。** 按 S1 指定原样 cherry-pick E1 候选后，原创组件任务经新 reader、M0/M1 plan、owned model child 和真实 bound tool child 执行：两条 recovery-on 轨迹成功，recovery-off 在首次 transient 后失败，全部8个owned进程回收；新catalog manifest绑定和改写spec反例均通过。它验证接口衔接，不替代 E1 的独立审核，也不是最终L1题目或模型效果。早先旧catalog接口fixture证据保留。

### action-only / capacity

顶层精确字段为 `schema_version, purpose, inputs`：

- `schema_version="toolalign.evaluation-inputs.v1"`。
- action-only 的 purpose 为 `action-only-model-evaluation`；inputs 最多60项，category仅 `simple_python/multiple/irrelevance`，每类最多20项。
- capacity 的 purpose 为 `original-capacity-probe`；inputs 最多2项，每项另含 `model="M0"` 或 `"M1"`。

action-only 每项精确字段为 `task_id, family_id, group_id, category, model_input`。capacity 在此基础上增加 `model`。task_id唯一；不包含 expected answer、oracle、执行器或可执行模块。官方 BFCL pin、筛选记录与 scorer 产物由 E1 后续 adapter 包维护；此接口不自动下载 BFCL 或调用提供商 API。

### replay

顶层精确字段为 `schema_version="toolalign.evaluation-replay.v1", purpose="development-prefix-replay", sequences`。最多4个 sequence，每项精确字段 `sequence_id, tenant_id, requests`。每个 requests 必须为3项，各项精确字段 `request_id, model_input`；sequence_id 与各序列内 request_id 唯一。序列必须由开发输入预先冻结，不从正式输出挑选。

## Run 配置与固定 plan

run 的精确公共字段如下；只能额外包含成对的 `resume_from, resume_batch_sha256`：

| 字段 | 要求 |
|---|---|
| `schema, authorized_by, run_kind` | `toolalign.cuda-evaluation-run.v1`, `S1`, `evaluation` |
| `mode` | `l1`, `action-only`, `replay`, `capacity` |
| `run_id` | 简单非空标识符 |
| `source_commit, config_sha256` | 精确40位源码提交；冻结CUDA配置 hash |
| `input_path, input_sha256` | 输入文件绝对路径与字节 hash |
| `repository, lock_root` | 同一实际 Git 仓库绝对路径 |
| `model_root, checkpoint_dir` | 固定模型与选中 SFT 状态目录绝对路径；M0不读取后者 |
| `checkpoint_sha256, adapter_sha256` | 上述固定 M1 身份；不表示M0使用adapter |
| `dependency_lock, dependency_lock_sha256` | 既有锁绝对路径及精确 hash，运行前核对已装包 |
| `output_dir` | 新输出目录绝对路径，必须尚不存在 |
| `main_seed, sampling` | `42`；精确对象 `{"temperature":0.7,"top_p":0.9,"max_new_tokens":256}` |
| `plan` | 由下述 CPU plan 命令生成，运行时逐字段精确核对 |
| `stop_after_unit` | 本段授权的累计计划前缀长度，1到完整plan长度，非零基下标 |
| `max_wall_seconds, max_output_bytes` | 正整数；14400秒/1GiB上限，capacity段60秒上限 |

`plan` 每项精确包含 `unit_id, task_id, condition, model, seed, cache_enabled, recovery_enabled`。unit_id从0连续编号。L1和action-only按输入顺序配对：偶数项 M0→M1，奇数项 M1→M0，同题seed均为42+i。L1最后按 `recovery_task_ids` 顺序追加 M1-recovery-off，seed复用其原任务序号。replay第偶数个序列off→on，第奇数个on→off；model固定M1，序列首seed为42+3i，内部请求加0/1/2。capacity按输入顺序各执行一次。

```sh
python -m toolalign.evaluation.cuda_eval plan --mode action-only --input /absolute/inputs.json --input-sha256 INPUT_SHA256
python -m toolalign.evaluation.cuda_eval validate --run-config /absolute/run.json
python -m toolalign.evaluation.cuda_eval evaluate --run-config /absolute/run.json
```

`plan`/`validate` 不加载模型框架。`evaluate` 只提供固定 CUDA 后端，没有 CPU fallback。当前交付并未执行此生产命令。

## 单次调用与结果消费

供 E1 在 CPU fixture 中复用的调用为：

```python
one_decision(model_input, backend, root,
             model_identity=identity, seed=42,
             cancellation=token, expires_monotonic=expiry)
```

位于 `toolalign.evaluation.cuda_eval.decision`。root须是现有、已resolve的绝对 sandbox 目录。它只调用 backend 一次，并在返回前回收 owned child；生产入口不接受调用者指定 backend。`DecisionSession` 提供相同的 `generate(model_input, seed=...)` 和 `close()`，用于固定三请求回放，单个失败会关闭该生命周期，不重启它来继续后续请求。

结果含 `status, reason, output, raw_text, finish_reason, raw_action, raw_action_valid, raw_parse_failure, model_input, model_input_hash, generation_config, token_accounting_complete, timing, diagnostic, elapsed_seconds`；one_decision另含 `complete_wall_seconds, process_records, backend_metrics`。`output` 是原 `ModelOutput` 的完整字典，包括 backend 的 `parsed_action/parse_failure`、声明的模型身份、token计数；没有返回时为null。raw_action_valid只指结构合法，不表示工具选择或参数语义正确。

主要 status 为 `completed, parse_failure, timed_out, cancelled, budget_exhausted, infrastructure_error`。没有返回原文时 raw_text/finish_reason 为null，空字符串仍原样保留；不能把这些行转换成合法无需工具动作。超出 IPC 上限时保留有限诊断、raw hash/长度及可用 usage。

输出目录包括：

- `batch.json`：稳定身份、mode、输入hash、完整plan、sampling；绑定源码/依赖/预期M0/M1和checkpoint身份，时间统计不改变接续身份。
- `run.json`：本段授权与路径。
- `states/NNNN.started.json` / `terminal.json`：在构造后端前持久化started，终态原子写入。
- replay另有 `requests/NNNN-J.started.json` / `terminal.json`，记录各请求的seed、batch与实际ModelInput hash。
- `results.jsonl`：完整plan每单元一行，包括未启动项。每行有 `plan, batch_sha256, status, reason, result, elapsed_seconds`；已启动行另有开始/结束时刻与原run_id。L1的result为完整HarnessResult；单次模式为上面的结果；replay为 `requests, process_records, backend_metrics`。
- `summary.json`：完整分母、逐条件终态及原因、未启动数、已恢复数、已知token总量及完整性、实际返回模型身份、加载/生成/工具/队列/内存指标、输入/输出身份。正式统计和官方scorer始终另外标记运行状态，本模块不计算置信区间。

接续只导入 `resume_batch_sha256` 绑定的同一batch；已started单元永不再跑。没有terminal的单元变为interrupted。replay保存已完成请求，已started但无terminal的请求为interrupted，剩余未发出的请求为not_started；整个已started序列不重建缓存再跑。可接续后面的从未started单元。原终态文件逐字节继承。所有这些状态保留在分母，实际token缺失为unknown，不补成零。

## 计时范围

cache off/on采用同一 streamer、forward hooks、HF配置和同步方式。TTFT从cache lookup之前到首生成token进入streamer；prefill为首次forward，包括热cache剩余后缀；decode从首token到generate返回；generation另包含cache发布。`prefill_tokens/cache_hit_tokens/forward_calls` 为实际计算记录。原默认decode路径不启用这套可选插桩。

child generation包含tokenizer/懒加载和生成；queue从父提交到child开始generate；单次complete wall包含进程回收；L1工具时间由tool_execution至observing事件间隔给出。segment从输入/源码/依赖预检前开始，包含父文件完整hash。cold_load按既有口径从tokenizer加载到CUDA ready，明确排除父预检；不完整加载另记已耗时间。GPU allocated/reserved与父/child host RSS分开，缺失指标保持unknown；本包不报告CPU耗时为CUDA加速。

## 验证与证据

已有 CPU 环境：Python3.12.14、Torch2.8.0、Transformers4.57.6、PEFT0.18.1、NumPy2.2.6、pytest9.0.2；没有新安装、固定模型下载、真实模型加载或Colab操作。核对了该固定 Transformers 版本的 `DynamicCache.crop/get_seq_length` 与生成时 cache_position 行为。

定点检查 **231 passed, 1 skipped，退出码0**。跳过的是既有 `tests/colab/test_dpo_control.py` 中需要 `pip` 的安装参数检查，环境未装pip。命令范围为新增3个测试文件、原G4后端与batch、默认loader的3个文件核对检查、完整harness目录、已有SFT/G4/DPO Colab控制及cleanup检查。新增50项覆盖了真实小模型cache、M0加载分支、Action门控、recovery on/off、plan/预算、started接续、replay请求journal、实际owned进程和本地控制器回收。随后接入 E1 候选，新增1项真实heldout组合检查通过、退出码0；未重跑未受影响矩阵。231项记录绑定接入前源码，组合记录绑定候选与最终评测源码。

Torch/CUDA loader分支的文件/lease/HF加载/设备转移边界使用明确标记的MOCK_ONLY；小型随机Qwen和PEFT cache数值检查使用真实库和真实CPU张量。默认文件复核回归使用已有原创文件fixture，不以mock证明固定模型真实加载。heldout catalog的一项组合验证已通过，E1候选与本包的R1独立审核状态仍待接纳；Q1任务质量审核与S1真实GPU验证均由后续阶段完成。

全仓ruff、冻结契约检查与公开内容扫描均通过，退出码0。

实际 argv、退出码、日志、环境与受检源码身份保存在私有证据目录 `.toolalign-local/p06-g5-evaluation-r1/`，入口为 `evidence-index.json`。公开包只含源码、原创fixture、此报告与交接，不含输入语料、权重、原始产物或本机对话身份。
