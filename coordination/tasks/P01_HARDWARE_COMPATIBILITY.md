# P01｜Mac 校准与 SFT/DPO 兼容性

状态：READY_FOR_REVIEW；候选 `f97bb0de346c220871962a5689014a379fe19c83` 已正式交付且任务空闲，尚待共享基线同步与独立R1。S0 于 2026-09-06 授权本任务并核对原生独立对话、code_base 与工作分支。P00 已在 `cd091e3a53986b59b170baf5b746644f369135d1` 合并并验证；本包 code_base 为随后仅更新协调/证据文档的 `ebcaf586f8e65f5306259f6b134e1c5cce30cf48`。

本文件所在的 S0 派发提交是 authorization_commit，由原生派发消息给出完整 SHA。Worker 在切换 code_base 前用 `git show <authorization_commit>:<本任务路径>` 读取并保存私有副本；公共任务文件只由 S0 更新。

- 模型：`gpt-6-astra`；推理：`max`（最高；按用户最新目标，旧 xhigh 配置废止）。只使用独立 Codex 对话，禁止 sub-agent、嵌套代理或自行创建新任务。
- 契约：`plan-v0.1` / `coordination.v1` / `toolalign.contracts.v1`；精确字节绑定 code_base 的 `contracts.v1.lock.json`。
- 公共所有权：contracts、runtime、configs、pyproject、uv.lock、CI/检查脚本、AGENTS/README、BOARD/PROJECT_STATUS/DECISIONS 均只读。依赖/契约申请提交 S0 后继续独立可做工作。
- 真实任务 ID 与 cwd 仅写本机 `.toolalign-local/task-identity.json`。新对话先通过原生 set_thread_title 设置自身标题，再核对 worktree/branch/base；不操作其他 worktree。
- 公开内容仅提交原创代码、小 fixtures、允许公开的元数据/统计及去敏报告。原始数据、权重、日志、模型制品和具体本机路径只留私有目录。
- 交付须为已提交精确 SHA + handoff + 命令/退出码/原始日志 hash + 失败项/NOT_RUN。自测后交独立 R1，只有 S0 合并 main。

## 领取与输入

- owner：T1。
- code_base：`ebcaf586f8e65f5306259f6b134e1c5cce30cf48`。
- branch：`work/p01-compatibility`；App 独立 worktree，实际私有路径由 S0 核验。
- 输入：已验收 P00 契约/共享 GPULease；`docs/03_TRAINING_SPEC.md`、`docs/05_APPLE_SILICON.md`、`docs/12_CONTRACTS_V1.md`、`coordination/RESOURCE_LOCK.md`。
- 允许修改：`src/toolalign/training/compatibility/`、`tests/training/compatibility/`、`reports/hardware/`、`coordination/handoffs/P01-r1.md`。

## 目标与输出

核实实际芯片、GPU 核数、内存、macOS、Python、Metal 和候选库版本。输出机器去敏清单、源码/API 兼容结论、可复现 CPU 数学检查、0.6B 冒烟、1.7B 校准与资源预算报告。

0.6B 先验证 32 条原创训练 smoke 样本的 token/mask、加载、微训练与 adapter 保存重载；不得把 P02 最终测试集用于此处。SFT completion-only、next-token shift、padding/EOS 和多轮边界须检查。MLX 与独立 PyTorch CPU 小张量 CE/DPO loss 及梯度对照，明确容差。policy=reference 的 ln(2)、reference/hash 冻结、只有声明 adapter 更新、跨库 target module/scaling/template/前向一致必须有证据。禁用全部 adapter 不等同于 SFT reference。

检查首选 MLX-LM SFT 和 mlx-tune DPO 的真实源码与固定版本；备选最多一次 mlx-lm-lora，不自建完整训练框架。正式依赖由 S0 集中锁定；探索环境只能在本 worktree 私有 venv，保存精确安装清单和来源。

1.7B 分长度 bucket 校准，先暖机，目标 100 个可测微步；预算到限则记录实际数量和外推限制。分别记录 SFT、reference 预计算、DPO、生成和完整任务推理可实际完成的测量；完整 P03 harness 未合并的测项标 NOT_RUN 并留后续入口，不伪造。本包不运行全量正式 SFT/DPO，不自行进入 P04/P05。

每次模型 smoke 使用冻结 run.v1 manifest；实际文件 hash、token/微步/optimizer step、计时同步、暖机与 checkpoint I/O 分开记录。人工小张量检查可用独立测试日志，不假装模型训练 manifest。

## 资源与停止条件

任何模型导入/加载到驻留结束均持同一仓库 GPULease；没有取得租约不能执行模型代码。默认 micro-batch 1、smoke 1024 tokens、rank 8；1536/2048 bucket 在前一档可行后逐档测试，不强截关键内容。

先登记公开原始模型 revision、许可、预计下载大小和缓存位置；不自动接受 gated 条款。T1 首轮下载/环境/模型制品规划上限 20GiB，全项目仍受 50GiB 上限约束。MLX peak 目标 24GiB、RSS 警戒 30GiB；每次作业前写明 step/token/最长 wall time、系统压力和 swap 增长阈值及恢复策略，超限保存并停止。不抬高系统 wired-memory 限制。仅本机免费计算，不调用付费 API 或云资源。

## 验收命令与边界

已存在的 CPU 回归入口：`uv sync --locked --python 3.14`、`uv run --locked pytest -q`、`uv run --locked ruff check .`、`uv run --locked python scripts/check_contract_freeze.py`、`uv run --locked python scripts/check_public_content.py`。

以下为 **PLANNED / NOT_RUN**，由本包实现；真实命令/参数在 handoff 固定，尚不存在不得写已通过：

- `uv run --locked pytest -q tests/training/compatibility/`：CPU loss/mask/reference 身份与资源控制正负例通过；如需新增依赖，先由 S0 合并锁文件。
- `python -m toolalign.training.compatibility --help`：提供硬件检查、CPU 数学核验、受控模型 smoke 的可复现入口；探索时使用私有已记录环境中的 Python。
- `python -m toolalign.training.compatibility <子命令> --config <私有配置路径>`：实施前先在本包报告记录具体参数、预算与预期；必须包含退出码、原始日志 hash、真实计数、保存重载及负例结果。

负向场景须覆盖 mask 错位、padding 被计入、reference 指向原始底座或变化、adapter scaling 不匹配、锁竞争/等待超时不加载、保存重载偏差。公共 GPULease 已有 P00 测试可复用；新增模型入口须证明真的使用它。

## 阻塞与交接

依赖请求提供精确版本、Python/平台要求、许可/来源和最小 reproducer，由 S0 批准实施公共更新。DPO 不通过时保存具体失败，最多一次备选；SFT 可行性继续核验，DPO 保持未通过，不能擅自改成成功。

交接：`coordination/handoffs/P01-r1.md`；包含个人应理解的 loss/reference/统一内存技术点。未完成测项逐项列出，待 R1 和 S0 验收。

2026-09-06 公共基线更新：S0 已授权采用已验证生产合并 `18fc8475476f6becf684ba817480caeb96a7cfb9` 及协调状态 `a6c8dd3c78b3674a242b4faacbb175f7b7c98303`。保留原 code_base/authorization 的历史记录，实际工作分支以非强制 merge 接入；新模型规则 gpt-6-astra/max 优先于首派任务副本。

2026-09-06 第二次公共基线更新：S0-SHARED-02 已独立审查/CI/合并/main验证，生产base `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`。收到S0原生同步消息后，保留f97bb0d及原环境/模型/失败证据，非强制merge本报告所在协调提交（完整SHA由消息给出）。仅CPU复核新base的测试、包构建/隔离安装与环境metadata，必要时在已锁环境运行原CPU数学检查；不重新跑未受影响模型校准，不加载模型或扩展P04。允许新增`coordination/handoffs/P01-base-r2.md`记录新完整候选、merge关系与实际结果，原P01-r1保留。
