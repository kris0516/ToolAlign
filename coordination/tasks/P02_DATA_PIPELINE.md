# P02｜数据规范化、许可与分组隔离

状态：READY_FOR_REVIEW；候选 `46f546504f73588caa2e71aac316c3c312306df6` 已正式交付且任务空闲，尚待共享基线同步、独立R1与kris真实语义审查。S0 于 2026-09-06 授权本任务并核对原生独立对话、code_base 与工作分支。P00 已在 `cd091e3a53986b59b170baf5b746644f369135d1` 合并并验证；本包 code_base 为随后仅更新协调/证据文档的 `ebcaf586f8e65f5306259f6b134e1c5cce30cf48`。

本文件所在的 S0 派发提交是 authorization_commit，由原生派发消息给出完整 SHA。Worker 在切换 code_base 前用 `git show <authorization_commit>:<本任务路径>` 读取并保存私有副本；公共任务文件只由 S0 更新。

- 模型：`gpt-6-astra`；推理：`max`（最高；按用户最新目标，旧 xhigh 配置废止）。只使用独立 Codex 对话，禁止 sub-agent、嵌套代理或自行创建新任务。
- 契约：`plan-v0.1` / `coordination.v1` / `toolalign.contracts.v1`；精确字节绑定 code_base 的 `contracts.v1.lock.json`。
- 公共所有权：contracts、runtime、configs、pyproject、uv.lock、CI/检查脚本、AGENTS/README、BOARD/PROJECT_STATUS/DECISIONS 均只读。依赖/契约申请提交 S0 后继续独立可做工作。
- 真实任务 ID 与 cwd 仅写本机 `.toolalign-local/task-identity.json`。新对话先通过原生 set_thread_title 设置自身标题，再核对 worktree/branch/base；不操作其他 worktree。
- 公开内容仅提交原创代码、小 fixtures、允许公开的元数据/统计及去敏报告。原始数据、权重、日志、模型制品和具体本机路径只留私有目录。
- 交付须为已提交精确 SHA + handoff + 命令/退出码/原始日志 hash + 失败项/NOT_RUN。自测后交独立 R1，只有 S0 合并 main。

## 领取与输入

- owner：D1。
- code_base：`ebcaf586f8e65f5306259f6b134e1c5cce30cf48`。
- branch：`work/p02-data`；App 独立 worktree，实际私有路径由 S0 核验。
- 输入：冻结 example/tool.v1 和参数 schema 子集；`docs/02_DATA_GOVERNANCE.md`、`docs/12_CONTRACTS_V1.md`、来源登记与 `configs/protocol.v1.json`。
- 允许修改：`src/toolalign/data/`、`tests/data/`、`data/manifests/`、`reports/data/`、`coordination/handoffs/P02-r1.md`。

## 目标与输出

以 `Team-ACE/ToolACE` 为主完成可复现的来源获取、许可/revision/hash 记录、规范化、分组去重与 split、token 长度和质量审计。xLAM 仅为可选，不接受未授权 gated 条款。核对当前官方数据仓库内容和许可证，不能把规划文档的来源声明当成本次实证。

先读取小批真实格式再实现转换；每个受监督 assistant 决策产生一个合法输入前缀和 expected_action，原记录多轮保持相同 group。保留 source_record_hash → normalized_hash → group → split → augmentation_parent 追溯；时间字段不影响 ID。同输入、同参数重复重建必须一致。

先分组切分，再增强；group 覆盖来源记录、tool/schema 模板、业务任务模板与可识别语义近重复。train/validation/test 目标 80/10/10，隔离优先于比例；OOD 工具/schema 留组并单列。同组跨 split、改写跨 split、目标答案进入模型输入都必须被检测。最终集与 BFCL 不进入训练、挖负例或选模型。

严格使用 P00 验证器。超出闭合有界工具 schema 子集、格式不明、缺少真值或副作用分类不明的样本隔离并计数；不得悄悄改宽松 schema、补造答案或将生产写操作标成只读。兼容率过低时向 S0 提交代表样本和分母，由 S0 决策适配规则。

报告原始/过滤/最终数量、每项排除原因、工具/类别/语言分布、完全/近重复、split 交集、来源许可、P50/P90/P95/P99 token 长度与 prompt/schema/completion 占比。分桶或排除长样本，禁止损坏关键 schema/最终回答。只下载官方 tokenizer 的必要文件，记录 revision/template/non-thinking；不加载模型权重。

## 资源与验收

仅 CPU；首轮数据/tokenizer/探索环境总磁盘规划上限 5GiB。公共依赖由 S0 集中修改，私有探索环境只写本 worktree `.toolalign-local/`，记录精确包版本。原始/处理数据只存 gitignored 目录，公开仅下载代码、许可元数据、统计和原创小 fixtures。

已存在回归入口：`uv sync --locked --python 3.14`、`uv run --locked pytest -q`、`uv run --locked ruff check .`、`uv run --locked python scripts/check_contract_freeze.py`、`uv run --locked python scripts/check_public_content.py`。

以下为 **PLANNED / NOT_RUN**，由本包实现；完成时在 handoff 提供真实命令和参数：

- `uv run --locked pytest -q tests/data/`：同输入重建、group/split/OOD 隔离、改写继承、长样本处理、恶意 schema/解析、许可与排除计数、模型输入投影正负例通过。
- `python -m toolalign.data --help`：提供可复现导入/审计入口。
- `python -m toolalign.data <子命令> --config <私有配置路径>`：实施前记录具体参数、来源 revision、预算、预期输出；至少两次重建比较产物/分组/split hash，不能用人工复制同一文件冒充重建。

## 人工检查与交接

G-DATA 必须有 kris 的真实质量抽查。先准备可查看的分层样本包、来源索引、review 表和问题分类，再向 S0 报告等待人工；模型抽查不能记为 kris 通过。冻结的偏好抽检规则用于未来 P05，不把其误标结论虚构为已完成。人工审查未完成时可交 pipeline 的代码/自动证据给独立 R1，但 P02 与 G-DATA 不能宣称 VERIFIED。

交接：`coordination/handoffs/P02-r1.md`。附 command/exit/log hash、来源与转换许可、实际 group/split 计数、错误/排除清单、人工包位置和未完成项；不得提交原始数据/私有路径。长度或 schema 兼容问题提交 S0，继续可独立的审计，不能自行降低数据门。

2026-09-06 公共基线更新：S0 已授权采用已验证生产合并 `18fc8475476f6becf684ba817480caeb96a7cfb9` 及协调状态 `a6c8dd3c78b3674a242b4faacbb175f7b7c98303`。保留原 code_base/authorization 的历史记录，实际工作分支以非强制 merge 接入；新模型规则 gpt-6-astra/max 优先于首派任务副本。

2026-09-06 第二次公共基线更新：S0-SHARED-02 已独立审查/CI/合并/main验证，生产base `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`。收到S0原生同步消息后，保留46f5465及两次真实构建/有效人审包，非强制merge本报告所在协调提交（完整SHA由消息给出）。仅CPU复核新base测试、固定真实tokenizer、包构建/隔离安装与既有数据manifest/人审输入hash；未改变数据代码/参数时不无理由全量重建，不填写人工判定。允许新增`coordination/handoffs/P02-base-r2.md`记录新完整候选、merge关系与实际结果，原P02-r1保留。
