# P03｜本地工具执行器与语义 oracle

状态：IN_PROGRESS（CPU基线同步，授权f2a271b；T1原生空闲后已派发并核验E1活跃）；owner E1；原候选`85e0905fc82da4504d73bf7eb489c1f1a0d227a7`保留，尚待新完整候选与独立R1。原code_base`97466a20f599f68c511b9c8a71fe5f2cdfd9ad4b`；原authorization_commit`e882594da84359b7f6ced7dd6aefdb9c7ce06209`；branch`work/p03-execution-harness`。真实原生任务身份和隔离worktree/分支已核验；首派时T1已停止，E1与D1并行。最多两个活跃实现任务。保留首派授权副本和原始基线。

模型统一 gpt-6-astra / thinking=max（最高）；仅 App 独立任务与 worktree，禁止 sub-agent、嵌套代理或自行创建其他任务。第一步 set_thread_title 并保存真实身份到私有 task-identity.json。给 S0 的普通回报省略 model/thinking。

## 依赖与范围

P00 冻结接口、S0-SHARED-01 来源政策均已合并验证。读取 AGENTS/GOAL/PROTOCOL、docs/01/04/12/13、configs/protocol.v1.json、contracts.v1.lock.json 与 src/toolalign/contracts/interfaces.py。公共 contracts/runtime/CLI/configs/pyproject/lock/CI/AGENTS/状态/ADR 只读，改动请求由 S0 处理。

允许修改：src/toolalign/tools/、src/toolalign/evaluation/oracles/、src/toolalign/evaluation/harness.py、tests/tools/、tests/evaluation/harness/、tests/fixtures/tools/、reports/harness/、coordination/handoffs/P03-r1.md。只提交原创小 fixtures、代码、去敏统计与证据摘要。正式隐藏任务/答案、原始日志、运行制品只在私有目录。

当前存在已知 App worktree sdist 私有文件选择问题，S0-SHARED-02/PR4 正在独立审查。**不要在本旧基线运行默认 uv build 或 sdist；CPU 实现/测试可继续，必要时只构建 wheel。** S0 发出修复后已验证 main SHA 再非强制 merge，不能自行采用未审共享候选。

2026-09-06 更新：该共享包已在 `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` 合并并验证，见 [main证据](../../reports/S0_SHARED_02_MAIN_VERIFICATION.md)。E1先保持空闲，待S0核验并发名额并发送原生同步消息后，非强制merge指定协调提交，保留85e0905与原始P03-r1；仅复核CPU/harness和当前包构建/隔离安装，不加载MLX/Qwen或扩展P04/P06。允许届时新增`coordination/handoffs/P03-base-r2.md`交新完整候选，旧基线禁止sdist的限制仍保留历史效力。

## 要交付的行为

实现与冻结 ToolRegistry、ToolExecutor、TaskOracle 和 ModelBackend 相接的本地 harness。Registry 绑定明确的实现、版本和 schema hash，拒绝重复/冲突名称。ValidatedCall 是可伪造且内含可变 mapping 的 dataclass，execute 前重新核验当前 registry/hash/version、参数与策略，避免修改后继续执行。未知或未绑定的 ta_ 历史工具必须拒绝；dataset schema、sandbox_only 字段和来源 URL 都不提供执行权限。

实现六类原创开发运维工具：版本文档检索、构建/测试报告查询、日志过滤、结构化记录聚合、版本兼容比较、单位/数值转换。优先固定资源 ID 查表；若提供路径则严格绑定隔离根并拒绝遍历/符号链接逃逸。无任意宿主路径、外网、shell/Python/SQL/eval/exec、真实业务写入或数据动态注册。输入/输出须有界。

Oracle 验证任务目标的对象、日期、版本、数值与允许策略集合；工具正常返回或答案自称成功不足以判通过。至少包含合法多解、多步依赖、相似工具混淆、无需工具、缺参应澄清、故障后的有限恢复。OracleTask/expected_action/评分标签不传给 ModelBackend；任务本来允许通过工具获取的资源内容可正常返回。可公开原创开发用 fixtures，不提前公开正式最终测试答案，也不能为训练偷看测试 oracle。

使用明确命名的 scripted CPU ModelBackend 提供可运行 demo，证明接口和状态机可工作；不把脚本回放当作 Qwen 推理或 benchmark。P04 真实 ModelBackend、P06 正式指标/分组 bootstrap/BFCL 与 GPU 评测不在本包。

预算沿用最多3次模型决策、2次工具轮次；256 max_new_tokens 按架构定义是每次响应上限，30秒为统一请求 deadline，二者仍是待模型验证配置。累计报告 token、决策、轮次与耗时，重试和修复不能重置；不能额外免费生成。UTC expiry 可序列化，执行耗时用单调时钟。超时/取消必须真正结束本任务创建的阻塞操作，不能只丢弃 future 却留后台执行；只回收身份明确的自有进程。若需要额外公共配置先请求 S0。

每次事件输出合法 trace.v1；覆盖解析、验证、unknown tool、执行错误、timeout、cancel、budget、final 等终止路径。raw output 和可选 repaired output 分开，默认评估原始结果；失败保留在分母，unknown/排除如实登记。scripted token 数仅用于实现预算测试，不能当真实 tokenizer 吞吐。

## 实际验证和交接

现有命令：uv sync --locked --python 3.14；uv run --locked pytest -q；uv run --locked ruff check .；uv run --locked python scripts/check_contract_freeze.py；uv run --locked python scripts/check_public_content.py。

PLANNED/尚未实现：uv run --locked pytest -q tests/tools/ tests/evaluation/harness/；python -m toolalign.tools --help 与其 CPU demo 子命令。先固定实际 CLI 参数再记录结果，不能把计划命令写成已跑。

必要负例：参数结构合法但选错对象/版本判失败；无工具任务却调用；伪造或修改后的ValidatedCall、旧registry/hash/版本、ta_未知工具；schema注入/超界输出；timeout/cancel/retry不重置预算且没有遗留自有进程；oracle标签不进入ModelInput；所有等价合法答案可通过。报告六类覆盖、真实计数/退出码/日志hash与未测项。

仅 CPU，无模型导入、权重下载或费用；首轮私有制品/环境预算2GiB，不改变OS限制。提交授权文件的精确SHA和P03-r1 handoff，请S0安排独立R1；不自行merge、改看板或签验收。无法可靠判定的任务标unknown，不用模型自评补真值。
