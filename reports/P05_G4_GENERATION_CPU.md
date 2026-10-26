# P05 G4 CUDA 候选生成：CPU 实现

2026-10-26；T1；状态：**CPU 实现与定点验证完成，待 R1 独立审查**。

实现已覆盖固定候选顺序、完整请求留存、失败处置和断线恢复。CPU fixture 证实：已有成功和失败候选均不重复；有 started 而无终态的候选记 interrupted；下一候选重新获得初始故障队列。真实 Qwen 前向、CUDA 冷加载、L4 吞吐和真实 SFT 候选生成均 **NOT_RUN**。

授权为 `6d5df60591dda6c5e63b8d8c8b8f45bbb828d022`，基于 PR27 `1267d1a33dfb08bfd9800b80ea97315730748952`；同时落实恢复补充 `6deeb0c9b32b6f8dcfd0149b6972ba1f68b0dd43` 和 Q1 协议补充 `8b84a524c55bdb31edc9425814ce8eb2575e9f48`。参见[任务](../coordination/tasks/P05_G4_GENERATION_CPU.md)与[共享协议](../coordination/tasks/P05_G4_PROTOCOL.md)。

## 交付行为

- `CUDAGenerationBackend.generate(ModelInput, GenerationConfig)` 在 LocalHarness 的 owned child 内按需加载，同轨迹复用。先构造冻结的原生 tokenizer，再取得 GPU lease、导入 Torch、验证选中状态和本地模型文件。BF16 底座、FP32 Q/V LoRA、rank 8、alpha 16、scale 2；逐键核对 adapter 的集合、shape、dtype、有限值和参数 hash。复用已审 `cuda_sft.engine.load_model`，没有改动 SFT 生产实现。
- 选中 G3 1.7B step743；完整状态 SHA256 为 `cfb02aec2279138c01f8b336abc08a588d0ab11efa8db68fd61ba0b6150b5d14`，adapter hash 为 `973c440e29090892ad11d6d56b94bad4c98a5398c223e2b4302d7dba7c4640ed`。核对原 SFT source、revision、v2 config、step743/cursor5938 及 manifest 的选模身份。只恢复生成所需 adapter，不恢复优化器或执行更新。
- 复用固定 `prompt_messages` 和 `OfflineQwenTokenizer`，完整保留 schema 与历史。输入 token 数加 256 超过 2048 时记录 `context_overflow`，不加载模型或截断输入。推理采用 eval/no_grad、SDPA、KV cache，关闭训练用 gradient checkpointing。HF generation config 显式设置 top_k=0、repetition_penalty=1、单束单输出，避免原 checkpoint 的附加解码默认值改变采样。
- 只去掉生成文本末尾的结构性 EOS；该 EOS 仍计入 output_tokens。其余字节原样保留，parsed_action 不代替 raw text。长度、deadline、加载错误均保留。GPU lease 一直由该子进程持有；原有 OwnedProcess 负责终止和回收。
- LocalHarness 新增可选 `SamplingParameters(seed, temperature, top_p)`，默认仍为 seed0、greedy、top_p1。3 次决策、2 轮工具、每次 256 token、原 30 秒整轨迹 deadline 不开放覆盖。新增 `HarnessResult.decision_inputs`，从实际发送的请求逐次复制；现有 decisions 的 hash 对应相同位置的输入。最后一次请求若超时而没有返回，inputs 可比 decisions 多一项，不伪造模型输出。
- 冷加载统计通过 owned child 的私有 sidecar 回收；完整加载耗时包括 tokenizer、首次 prompt 编码、checkpoint 检查及模型加载。未完成加载记录已观察耗时，不能当作完整加载性能。统计文件损坏仅登记诊断错误，仍关闭并回收子进程。

`model_identity.model_hash` 是原始 safetensors 文件名到 SHA256 映射的 canonical hash；`tokenizer_hash` 是固定 tokenizer.json 的文件 hash；模板和 adapter 使用各自固定 hash。完整 checkpoint SHA 另存候选行及 batch identity。

## 批次接口与恢复

输入严格采用共享 `toolalign.preference-tasks.v1`；只接受 train、当前 registry 身份、任务/Example/OracleTask 一致的清单。Oracle、expected_action、faults 均留在父进程。每个 candidate 独立创建 LocalToolExecutor，保留实际 observation 与原始 call_id。

全顺序为任务文件顺序，随后每任务 `candidate-0` 至 `candidate-3`；实际 seed 为 `42 + 全局零起始 ordinal`，每次 decision 重置为该候选 seed。清单最多 128 个任务、512 个候选，采样固定 temperature0.7/top_p0.9。完整 candidate_plan 必须先写入 run config；runner 验证其精确值。

`max_trajectories` 表示本次获准执行的完整计划前缀上界，包含已恢复的候选。例如 pilot 上界 4，后续上界 512，前 4 条仍在总分母并保持原终态。每个新候选启动前原子写入并 fsync `states/NNNN.started.json`，返回后写 `states/NNNN.terminal.json`。恢复使用新 output_dir、旧输出快照 `resume_from` 和旧 `batch.json` 的 `resume_batch_sha256`；固定 source、输入、模型、环境身份和全计划必须一致。已有终态按原字节保存；started 缺终态则写 interrupted，保留原分母，不执行该 ID。未完成的原子写入文件也保留作证据。

输出：

| 文件 | 内容 |
|---|---|
| `batch.json`、`run.json` | 完整计划、source/package hashes、输入及模型身份、具体运行边界 |
| `states/*.started.json`、`*.terminal.json` | 固定 ID 的持久化启动与终态，含原轨迹和错误 |
| `candidates.jsonl` | task_id、candidate_id、generation_parameters、model_identity、harness_result（asdict）、decision_inputs、status；另含 ordinal、checkpoint/batch hash、时间及 execution_kind |
| `summary.json` | 全计划分母、已启动/未启动/恢复数量、状态与失败原因、候选文件 hash、已记录耗时和可测显存峰值 |

普通终态 status 为 oracle/harness 的 success、failure、unknown 或 not_scored；无确认终态为 interrupted，宿主异常为 infrastructure_error，后二者可没有 harness_result。超时、长度与 context_overflow 的细节保留于真实 harness_result。summary 不把未测显存写成 0；interrupted 的未知耗时明确使 `trajectory_time_complete=false`。GPU 分配时间和 CU 的跨段累计仍由 S1 的 Colab 控制证据登记。

单段墙钟上限 21,600 秒，输出上限 1 GiB。开始下一候选前为完整结果和 JSONL 副本预留 32 MiB，另留 1 MiB 元数据空间；空间不足则停止并报告未启动数量。完整 raw 数据不因输出上限被改写。

## 命令与控制器

复用已有 CUDA lock，不新增依赖或环境安装。本包没有新增已授权的真实 run config。S1 在独立审查后冻结私有配置：

```sh
python -m toolalign.training.cuda_generate plan --tasks /absolute/tasks.json --tasks-sha256 TASKS_SHA256
python -m toolalign.training.cuda_generate validate --run-config /absolute/run.json
python -m toolalign.training.cuda_generate generate --run-config /absolute/run.json
```

`plan` 与 `validate` 是 CPU 数据/参数检查；`validate` 不验证 CUDA 环境或模型实物。生产 generate 另核对执行 source、SFT 协议及完整依赖锁。

run config 使用 `schema=toolalign.cuda-generation-run.v1`、`authorized_by=S1`、`run_kind=generation`。必需字段分为：

- 身份：run_id、source_commit、config_sha256、tasks_sha256、checkpoint_sha256、adapter_sha256、dependency_lock_sha256。
- 绝对路径：repository、lock_root、output_dir、tasks_path、model_root、checkpoint_dir、dependency_lock。checkpoint_dir 内为选中 G3 状态的 state.pt 与 manifest.json。
- 计划/预算：candidate_plan、main_seed42、sampling（temperature0.7/top_p0.9/max_new_tokens256）、max_trajectories、max_wall_seconds、max_output_bytes。
- 恢复时额外提供 resume_from、resume_batch_sha256。

Colab 控制器以固定 schema 映射到 `toolalign.training.cuda_generate generate`；拒绝未知 schema、错误 kind 和越界预算。生成配置不填 max_optimizer_steps 或 SFT 的 persistent_dir。原有 SFT 模块、安装、tmux、超时终止、完整输出导出、Mac 回读和 stop-ready 路径保留；没有任意 module/shell 参数。G4 全阶段 21,600 秒/12 CU 累计预算继续由 S1 协调。

## 验证与边界

使用已有 Python 3.12.14、Torch 2.8.0、Transformers 4.57.6、PEFT 0.18.1、pytest 9.0.2 的 CPU 环境；测试设置 OMP/MKL/OPENBLAS_NUM_THREADS=2，每条 pytest 命令最多 300 秒。CPU 数据均为公开的小型原创 fixture；adapter 校验使用 2×2 Linear 加 rank8 LoRA，模型生成核用返回固定 token 的 fixture。没有读入真实 Qwen 权重、真实 tokenizer 文件或新增训练语料，没有模型前向、优化器更新、GPU、SSH、安装或 Colab 分配。

```sh
python -m pytest -q tests/model_io/test_cuda_generation.py tests/evaluation/harness tests/training/test_cuda_generation_batch.py tests/colab
# exit 0: 170 passed, 2 skipped, 75.88 s
python -m pytest -q tests/evaluation/harness/test_sampling_inputs.py tests/evaluation/harness/test_finish_cleanup.py tests/model_io/test_cuda_generation.py::test_cold_load_deadline_reaps_child_and_preserves_incomplete_cost
# 最后一次统计读取修补后：exit 0, 18 passed, 8.29 s
```

两项跳过均为既有 `tests/colab/test_install_indexes.py`：当前 CPU 环境没有 pip parser，未为此安装依赖；锁和安装命令没有修改。Ruff 对本次 Python 范围检查 exit 0；`python scripts/check_contract_freeze.py` exit 0（4 文件）；`python scripts/check_public_content.py` exit 0（812 路径）；`git diff --check` exit 0。精确 argv 与日志保存在私有交接索引。

本地失败历史保留：初始测试文件重名导致收集失败；导出 fixture 缺少 launch 记录；成功 fixture 的 1 秒进程启动预算出现超时，调整成功分支为 5 秒，超时分支仍为 1 秒；新统计 sidecar 的非对象 JSON 曾触发 AttributeError，补充实测回归后已关闭。前述均为本地开发检查，未登记为真实模型或独立审核结果。

| 阶段 | 当前证据 |
|---|---|
| 协议与代码 | 已实现授权任务及两次补充，待 R1 |
| CPU 环境与检查 | 上述有界检查通过；两项既有 pip parser 检查跳过 |
| 持久化/恢复 | CPU 固定 ID、原终态保留、interrupted 处置与真实子进程回收通过 |
| Colab 控制 | CPU 本地可执行 fixture 的固定入口、终止、导出与回读通过 |
| 真实 CUDA 环境/加载/生成/跨实例恢复 | 本实现 NOT_RUN；既有 G3 锁和证据不替代本次实测 |
| 偏好质量、DPO、模型效果 | 本包未运行；由后续独立审查与授权作业取得证据 |

下一决定：S1 回读本提交并交 R1；通过后冻结包含完整任务顺序的小 pilot，测量冷加载、吞吐和有效对产率，再决定原预算内的剩余前缀。30 秒预算如需调整，依据实际 pilot 另立最小修订。
