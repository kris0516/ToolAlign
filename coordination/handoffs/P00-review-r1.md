# P00｜独立审查 r1

reviewer：R1；审查日期：2026-09-06；结论：**FAIL**。

- 被审 base：`0f152e287bbc0e1c3edfb3f6f3794eb8d36c422f`。
- 被审 candidate head：`15706079c9516197b67dd59a19a0d0c4aa5adea8`。
- 被审来源：`origin/work/p00-bootstrap-contracts`，fetch 后读回与候选 SHA 一致。
- 审查分支：`review/p00-r1`，从上述 candidate 建立；App 独立 worktree 已核实。
- 契约：`plan-v0.1` / `coordination.v1` / `toolalign.contracts.v1` 候选。
- P0：未发现；P1：2 项阻断；P2：3 项非阻断缺陷。无外部前提导致的 BLOCKED。

## 审查范围

读取启动材料、候选 AGENTS/PROTOCOL/PROJECT_STATUS/P00 任务包、架构/数据治理/资源锁规格、`docs/12_CONTRACTS_V1.md`、S0 handoff 和 self-check；检查完整 base..head 的 45 文件 diff。涉及五类 wire schema、语义校验、六个模块 Protocol、CLI、GPU lease、两个检查脚本、fixtures/测试、依赖/CI、契约摘要及治理文档。self-check 仅用来了解实现方声称，未替代本次证据。

本次实际运行六条基础命令；原有 34 项测试通过。另写原创独立 CPU probes，结果 **36 passed / 10 failed**；10 个失败对应下表 5 类问题，未用 xfail 或改期待值掩盖。wheel 在新的临时 Python 3.14.7 venv 中按锁定依赖安装，离开源码目录后五类 CLI 验证、schema 摘要和依赖闭包检查全部通过，未安装 MLX/PyTorch。

逐命令退出码、相对日志索引、SHA-256 和复现入口见 [审查证据说明](../../reports/review/P00/README.md)。仅提交本交接单及 `reports/review/P00/` 的原创说明/小测试；实现、原有测试、契约、依赖及 S0 状态文件均未改动。

## 问题与证据

| ID | 优先级 | 文件/位置（候选行号） | 复现步骤与影响 | 最小修复 | 是否阻断 |
|---|---|---|---|---|---|
| R1-01 | P1 | `src/toolalign/contracts/validation.py:75–113` | 在闭合 object 参数 schema 加入 `items: {"$ref":"https://example.invalid/schema"}`，或在 string 子 schema 的 `properties` 中放引用，均通过；object 的 `items` 内正则也通过。`_tool_schema` 只递归当前 type 对应的分支，其他 schema 位置漏查。冻结候选声称拒绝 refs/正则，却批准这些内容进入合法 tool 及模型输入。3 个拒绝断言失败。 | 按 type 限定适用关键词，并递归校验所有被允许的 schema 位置；对不适用的 schema 关键词直接拒绝。保留 enum/description 中普通数据与 schema 的区分。补负例后由 S0 更新冻结摘要。 | 是；不能冻结与明确拒绝规则不符的契约 |
| R1-02 | P1 | `scripts/check_public_content.py:27–42,59–64` | 临时 Git repo 中暂存合成 token；扫描返回 1。随后只擦除工作副本，index 中 token 保留，扫描反而返回 0/PASS。路径来自 `git ls-files --cached`，内容却来自 `Path.read_text()`，未检验将被提交的 blob。可能在“扫描通过”后提交敏感内容。 | 对 index blob 扫描内容、模式和大小，同时检查未暂存/未跟踪候选；或明确拒绝 index 与工作树不一致并验证实际发布 tree。不要只增加 secret regex。 | 是；公开发布检查存在可复现漏扫 |
| R1-03 | P2 | `src/toolalign/contracts/validation.py:171–174`；`src/toolalign/cli.py:56–59` | 将 run 的 `dependency_versions` 设为 `{"synthetic_private_marker":123}`，CLI 退出 2，但 stderr 原样包含 marker。`absolute_path` 的自由键名属于输入数据，可以是秘密或私有路径；“不回显数据”注释不能覆盖这一情况。 | 只输出固定的契约字段/错误代码，对自由映射键统一脱敏；不要把任意 instance path 直接插入错误消息。 | 否；应修复的日志隐私缺陷，本次仅用合成标记 |
| R1-04 | P2 | `src/toolalign/contracts/v1.json:191,237,564,850` 等身份 pattern | 为合法 `run.git_commit`、`run.model.model_hash`、`tool.name`、`trace.trace_id` 各追加末尾 LF，4 个记录仍通过；这些值分别不再是 40/64 位 hash 或声明字符集内 ID。当前正则 `$` 可匹配末尾换行之前的位置，导致下游身份解析/关联不一致。 | 固定长度 hash 加精确长度约束；所有 ID/name/hash 使用真正的完整字符串约束并明确拒绝末尾换行。同步检查所有同类字段，保持导出 schema 与语义校验一致。 | 否；契约输入正确性缺陷 |
| R1-05 | P2 | `src/toolalign/contracts/validation.py:130–147,180–188` | 前缀已有 assistant `call-1` 和配对 observation，监督目标再次使用 `call-1`，example 被接受；把这个合法目标及 observation 拼入下一步前缀后，被同一校验器以重复 call ID 拒绝。当前只分别检查历史和目标内部，不检查二者交集。 | 将历史 call ID 与 `expected_action.tool_calls` 联合查重；新增“合法目标转为下一步历史”的一致性用例。 | 否；多步样本契约不一致 |

R1-01 的 payload 在当前 jsonschema 对应类型上是无效用的关键词；本次**没有观察到远程抓取、正则执行或任意代码执行**。问题是明确禁止内容仍获得契约批准，不能将它夸大为已经发生的联网漏洞。R1-02/R1-03 均使用临时原创标记，未发现候选提交含真实秘密；漏扫与回显能力不能等同于本次实际泄漏。

## 数据与指标

五类必填顶层字段、未知版本/额外顶层字段、model identity 必填字段检查通过；受检 TypedDict/dataclass 字段与 wire 定义一致，六个主要 Protocol 的调用接口存在。`ModelInput` 只含 messages/tools，oracle/task/expected_action 有独立类型；深拷贝投影的标签与可变对象隔离检查通过。

非 train preference、双方 unknown/tie/not_scored 标签拒绝；共享 prompt hash 覆盖 messages 和 tools，变化后旧 hash 拒绝。所有五类终止 trace 都要求 outcome，unknown/not_scored 可显式保留；四类 run 状态的终止字段检查通过。原有 tests 另覆盖 DPO 缺失 reference、时间倒序及 artifact 越界。

没有真实数据集、oracle 或模型实验，未发现本次实现引入训练/最终集混用或 oracle 自证。但样本自然语言中的答案泄漏、跨样本 group 隔离、真实 oracle 正确性、评测分母、SFT reference 身份、量化对照等均 **NOT_RUN**，由后续阶段验证。schema 接受合成 fixture 不是这些事项的 PASS。

## 安全与资源

常规位置的远程 ref/id、正则、组合 schema、未知关键词和越界参数 schema 均被拒绝；独立负例拦截 socket connect/DNS，未发生联网尝试，遗漏见 R1-01。P00 无工具执行器及模型加载实现，未发现数据经 eval/exec/shell 被执行。

原有 CPU 锁测试实际复现了跨进程/跨 worktree 竞争、超时、异常退出、SIGKILL 后释放、同 inode 和私有权限。新增独立临时 repo/worktree 再次验证互斥，并验证取得锁后元数据序列化异常仍释放锁。受检情形未发现锁失效；测试没有取得实际项目的 GPU 作业租约，没有 GPU 负载。跨独立 clone/不合作进程的全机互斥不在当前实现保证内。

契约四文件摘要检查通过，独立临时副本逐文件单字节变更均被检测。uv 锁中外部包来源为 PyPI，分发项均带 SHA-256；wheel schema 摘要与候选一致，基础包无 ML 后端。公共扫描在干净候选上通过，人工检查已审 diff 未发现秘密、原始训练数据、模型权重或私有路径；扫描完整性问题见 R1-02。

## 决议

**不建议合并候选 `15706079c9516197b67dd59a19a0d0c4aa5adea8`，P00 冻结审查未通过。** S0 修复 R1-01/R1-02 后提供新的精确 SHA，再交 R1 复核；P2 项应修复或由 S0 明确记录接受理由。R1 未自行修被审实现、修改 main、推送分支或向 GitHub 发评论。

复核范围限 P00：重跑基础命令与上述负例、确认冻结摘要和公开候选内容、按改动范围补查 wheel。GitHub CI、本机其他 Python 版本、main 集成后验收及 P01–P03 实现本次均未验收。审查 commit 和实际 worktree 位置通过任务最终回复交 S0 私有登记。
