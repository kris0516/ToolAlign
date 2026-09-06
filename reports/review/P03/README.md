# P03 / R1 完整候选独立审查

结论：**FAIL；P0=0、P1=2、P2=1**。两个 P1 阻断候选验收；P2 为非阻断的 trace 可靠性问题。日期：2026-09-06。完整结构化证据见 [evidence.json](evidence.json)，交接见 [P03-review-r1.md](../../../coordination/handoffs/P03-review-r1.md)。

## 候选与范围

| 身份 | 精确值 |
|---|---|
| 被审完整候选 | `79a15d990fc27a9a33d033983c94eb92cccfb268` |
| 生产 base | `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` |
| R1 authorization_commit | `52f9c57a50eaf580a1a90bc5c4b8bd028c83b903` |
| 同步协调提交 | `f2a271be616cdb53c01e8d671029f31ae140c037` |
| 非强制 merge | `86c5e8abaf0a6518fda0d33dba1b68eb6815737a` |
| 保留的原候选 | `85e0905fc82da4504d73bf7eb489c1f1a0d227a7` |
| 实现提交 | `8afb114bd14e69d3a2138212ab423147809fed63` |
| 首派 code_base / authorization_commit | `97466a20f599f68c511b9c8a71fe5f2cdfd9ad4b` / `e882594da84359b7f6ced7dd6aefdb9c7ce06209` |
| 审查分支 | `review/p03-r1`，直接从完整候选建立 |
| 读取的契约 | `plan-v0.1`、`coordination.v1`、`toolalign.contracts.v1`；冻结 lock 的四项 SHA-256 见 evidence |

按 AGENTS → 授权任务包 → PROTOCOL → PROJECT_STATUS/GOAL → docs/01、04、12、13、冻结 protocol/interfaces/lock 阅读。复核了相对同步基线的完整 19 文件、3263 新增/1 删除行，包括 11 个 P03 模块入口、测试、原创 fixture、原交接及 base-r2 证据；相对生产 base 的 30 文件还包含共享协调差异。merge 的父节点为原候选与指定同步提交。当前候选的 146 个已追踪文件逐字节绑定 Git blob。

本审查只新增四份原创 CPU 检查脚本、README、去敏 evidence 与交接单，共七个文件。候选代码、共享契约/配置/依赖、状态/ADR、E1 工作区保持只读。S0 在审查期间另行安排的修复未纳入本次审查。

## 需要修复的问题

**F1 — P1：停止通知写入失败，使已执行请求无法返回终止证据。**

位置：[harness.py:225–231](../../../src/toolalign/evaluation/harness.py)，以及外层异常/清理路径 413–417 行。`finish()` 在回收模型进程和生成终止 trace 之前写 `stop.json`；该写入遇到 `OSError` 后，外层 `except` 再次调用同一 `finish()` 并重复失败。`finally` 实际回收了进程，但 `LocalHarness.run()` 抛出异常，没有返回 `HarnessResult`。

独立探针仅在父进程写自己任务的 `stop.json` 时注入 EIO，分别使用正常 final 与原始 JSON 解析失败的原创 CPU 后端。两例均实际进入 `generate`，子进程标记与持有的 Process 身份相符；均尝试写停止通知两次、抛出 `OSError`，实际退出码均为 -15、关闭句柄前 `is_alive=False`。已消费的合成 input=13/output=9 及终止原因无法随结果交回。这破坏失败请求必须留下终止记录和用量的约定。

最小修复方向：停止通知失败后仍执行自有进程回收，返回带已知用量与失败原因的终止结果；收尾须幂等，不能以再次成功写入同一 IPC 文件为前提。本次直接证明的是结果缺失；从 CLI 控制流可推断它会在 case/summary 写出前退出，但未运行 CLI 故障注入，也未测得静默丢分母或成功率虚增。

**F2 — P1：目录清理异常发生在进程句柄关闭之后，重入清理掩盖原始错误。**

位置：[isolation.py:124–126](../../../src/toolalign/tools/isolation.py)，重入访问位于 107–111 行。`process.close()` → `_temporary.cleanup()` → `_closed=True` 的顺序使目录清理失败时句柄已关闭、幂等标志却仍为 False。harness 的后续 `finish()` / `finally` 再次调用 `close()`，访问 `process.pid` 时抛出 `ValueError: process object is closed`。

R1 对冻结候选独立编写两例真实 CPU 复现，分别以正常 final 和解析失败触发收尾，只在已创建的临时目录 cleanup 注入 EIO。两例子进程实际退出 0、句柄已关闭、候选 `_closed=False`，目录仍存在，最终没有 `HarnessResult`，原始 EIO 被 ValueError 覆盖。探针随后恢复原 cleanup 并移除自己持有的剩余目录；这一步仅是审查清场，不能算候选清理成功。S0 在本轮提供过同类问题线索；本证据来自 R1 自写探针，未读取 E1 未提交测试或修复代码。

最小修复方向：分别记录进程回收、句柄关闭、目录清理的状态，使部分失败后的重复 `close()` 仍合法；终止结果需保留真正的清理错误与已执行用量。仅调整停止通知不足以修复该独立失效点。

**F3 — P2，非阻断：oracle 将工具调用和观察分别收集后配对，未校验因果顺序。**

位置：[semantic.py:104–116](../../../src/toolalign/evaluation/oracles/semantic.py)。在 R1 原创、实际执行成功的报告查询例上，仅交换一次 `observing` 与 `tool_execution` 的位置，重新连续编号并保持延迟单调、身份一致；每条记录仍合法，但 oracle 返回 `success`。先出现结果、后出现调用的 trace 应视为不可靠真值并标 `unknown`。

建议按事件顺序维护待完成调用，再做允许策略匹配；无需扩大冻结 schema。本项涉及载入、损坏或未来适配器产生的 trace。当前 harness 的正常生成路径未发现该倒序；独立复算的历史 180 条和本次隔离安装 90 条事件均顺序正确。

## 独立检查覆盖与实际结果

原有适用测试 **309 passed**，组成是 core 58 + P03 133 + P00 审查 46 + P00-r2 审查 72。保留的 E1 原基线 191 计数属于历史证据；未将它与本次计数相加，也未计入 57 项针对旧共享快照的调查测试。

R1 新增检查 **54 项：49 passed / 5 failed**，无 xfail。生命周期 8 passed / 4 failed；语义、绑定和预算 41 passed / 1 failed。五个失败断言对应 F1 两例、F2 两例、F3 一例。早期分组运行仅保留演进证据，不重复累计到 54 项中。

| 领域 | 独立核验 |
|---|---|
| 六类工具的真实语义 | 版本文档检索、构建报告、日志过滤、结构化聚合、兼容性比较、单位转换；手工建立期望对象、日期、版本、字段、数值与允许策略。结构合法但错误的资源/版本/日期/运算/运行时/单位均失败；正确工具后伪造 final 字段亦失败；布尔值不能代替数值 1。 |
| 绑定与授权 | 固定实现、版本及 schema/registry hash；伪造、复制、跨 registry、旧 hash/版本、mapping 改写均拒绝；两个线程消费同一 issued call 仅执行一次。授权后原参数再次变化不改变已复制的执行参数。未知 `ta_`、来源 URL 与 dataset 声明不授予执行权限。 |
| 策略与信息隔离 | 两条合法单位转换策略、无需工具、缺参澄清、拒绝、有限恢复；真正读取上一轮工具 observation 的原创后端完成多步依赖，三次决策使用同一模型子进程。ModelInput 仅含 messages/tools；expected_action、来源修订、oracle 答案标记未进入请求；正常工具资源内容可返回。 |
| 预算与原始输出 | 三次决策、两轮工具和统一 deadline 累计；每响应 256 token 可累计到 768，257 单响应在计入用量后拒绝。160000 字节多字节原始输出的长度/hash、截断标志及已知 23/29 token 保留。raw 参与默认评分，backend parsed 仅诊断；未把 scripted token 当真实 tokenizer 计数。 |
| 输入与执行界限 | 复核有界 JSON、重复键/非有限值、16 KiB call/result、128 KiB model packet、512 KiB input、8192 节点/24 层深度；本地固定资源，无任意代码、SQL、宿主路径、外网或业务写入执行入口。 |
| 进程与时间 | 模型/工具 × timeout/cancel 四例都实际进入阻塞后才结束；模型忽略 SIGTERM，实测升级 SIGKILL=-9；工具退出 -15。实际 Process 的存活、exitcode、active_children、目录清理均核验，另外持有的无关睡眠进程仍存活。正常 final、解析失败、退出 17 的崩溃控制通过；工具 UTC 时钟回拨仍受同一单调 deadline 限制。 |
| trace 与计数 | 每事件 schema、连续 index、身份、UTC deadline、单调延迟、决策/轮次/token 累计、调用与观察绑定及终止 outcome；unknown 保留在 summary 分母。收尾故障例中的结果缺失单列为 F1/F2。 |

进程证明基于本轮实际持有的 `multiprocessing.Process`，不靠候选自报 `reaped=true` 或 PID 搜索后杀进程。取消条件只能在子操作 marker 出现后成立。父 registry 的锁不会随 backend pickle 传入子进程；子进程按固定 manifest 重建 registry。轻量可 pickle 配置与子进程 `generate` 已运行，真正的 MLX 懒加载/已加载模型可序列化性仍为 NOT_RUN，未发现需要扩大冻结 ModelBackend Protocol 的接口阻断。

## 原始证据与打包复核

只读核验原候选与当前候选共有的 17 份公开文件，以及 63 份原始私有文件的 SHA-256。审计原轮 19 + base-r2 16 = **35 条历史命令**，另逐项核验 15 条历史隔离安装子命令的 argv/退出码/log hash。历史中初次归档核验器遗漏 tracked `.gitignore` 的失败原样保留；修正核验器后才通过。历史 Git push/远端读回只是已记录数据，本审查没有执行它们。

没有调用候选 oracle、executor 或 scripted generator 来代替证据复算：审计器从原始 actions/trace 手工重建 ModelInput 与后续 prefix、registry 绑定、工具结果、允许策略和 final。两份历史 demo 各 10 例、90 条事件、20 次模型决策、10 轮工具、合成 input=220/output=140、9 次 completed/1 次可恢复 error、20 条已启动/已回收进程记录。它们是同一原创 demo 的重复验证，不能称为 20 个独立模型评测任务。历史日志只支持历史记录一致性，不能用于推断当前进程存活；本轮真实阻塞测试另行提供存活证据。

在 E1 后续构建前，按原记录 hash 将三个小归档保存到 R1 私有目录，随后全部对照冻结候选 Git blob 审核。R1 又实际构建 sdist、默认 wheel、从该 sdist 重建 wheel、直接源码 wheel。sdist 为 112760 字节、50 文件（49 tracked + 1 生成 metadata）；三个本轮 wheel 均为 37042 字节、29 文件（24 tracked + 5 metadata），未知载荷均为 0，字节与已核验的 E1 原包一致。

| 包 | SHA-256 |
|---|---|
| sdist | `a095ab30fbd3ffc35689253164be79b70dc0061d80078f80bb47c88d9a54178f` |
| 默认 / sdist 重建 / 直接 wheel | `e9d559cd0cfd17dc66b24f88455b1a138599a59faa476a34d3fb9d76c19a891c` |

本轮新建 CPU 隔离环境，实际执行 **15 条子命令**：导出锁定 default 依赖并校验 hashes、装重建 wheel、pip check、冻结 digest、五类 fixture CLI、tools help/registry/demo 和安装来源检查。`python -I` 从源码目录之外运行，11 个 P03 模块均来自安装 prefix，仅六个 runtime distributions，无 ML 包。新 demo 再独立复算 10/10、90 事件，与历史 summary 的字节 hash 一致。没有重复字节未变的共享 241/18 或 45/21 canary 调查。

本机为 macOS 26.5.1 arm64、Python 3.14.7；审查环境的 12 个 distributions 均与 lock 匹配。记录时新增私有 P03 目录分配 4444160 字节、复用基础 `.venv` 36245504 字节，合计约 38.8 MiB，低于 2 GiB 限额。这是磁盘分配记录，不是模型内存/性能实证。全部工作在 CPU 上完成。

## 可重复运行

在精确候选加本审查文件的独立 worktree 中执行：

```bash
uv sync --locked --python 3.14
uv run --locked pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py
uv run --locked pytest -q reports/review/P03/test_p03_semantics.py reports/review/P03/test_p03_lifecycle.py --basetemp=.toolalign-local/review-p03/reproduce
uv run --locked ruff check .
uv run --locked python scripts/check_contract_freeze.py
uv run --locked python scripts/check_public_content.py
```

候选上第三条命令的实测预期为退出 1、49 passed / 5 failed；默认 pytest discovery 不包含本目录。各问题可用 `-k stop_packet_write_failure`、`-k directory_cleanup_failure`、`-k observation_before_execution` 单独选择。

`audit_p03_evidence.py` 和 `verify_p03_package.py` 的完整实际参数、打包命令及每条日志 hash 均在 evidence 中；历史审计还需要已保留的 E1 私有证据目录及 R1 冻结归档，不应从缺失日志推断通过。原始 stdout/stderr、进程身份、测试临时目录和真实任务身份仅保留在私有目录。本报告的 `<R1_WORKTREE>` / `<E1_WORKTREE>` 是去敏占位符。

## 本轮日志索引

以下是 R1 实际命令的原始 stdout+stderr SHA-256。完整 argv、开始/结束时间、HEAD、当时 index tree、失败分类见 evidence；私有原日志在 `.toolalign-local/review-p03/logs/`。早期审查脚本的 I001 import-order 错误归属 R1，已仅修改新增文件并通过最终 lint，未列为候选问题。

<!-- COMMAND_TABLE_BEGIN -->

| 检查 ID | 退出码 | 完整日志 SHA-256 |
|---|---:|---|
| core-sync | 0 | `3e2716fdca7c983cacd74f3d76c02fa50f9488bd809edba89bcc66ccba287cc9` |
| cpu-regression | 0 | `815305d42ac69da6fd024a5b2b8695bb574256e2d52415f55d70dab9fea5b93f` |
| initial-lifecycle-probes | 1 | `cca06a0597b2eb3deba2477f11aff29f817c0940d58abb2b2b034fc0db6ca7fc` |
| real-blocking-reaping | 0 | `64f8ead942e548bb4d9c8c55daa6465daadcc8ab825e9ece6e1a885d4813e065` |
| semantic-and-binding-probes | 0 | `b86c96016498d2964535c51ef391fa4055263defa467672e48749823d94cf222` |
| expanded-semantic-budgets | 0 | `a9ba205058bd541f19ca2e87cfe7cdf7941d44caca0f39105fda4e544f628531` |
| trace-order-and-clock | 1 | `e414199cc8e0cc7c8640e0ca14ba07c511e1a5ac9ba5aa95c4cfaed2d55775a1` |
| freeze-historical-packages | 0 | `8ecb85f7ffe1d0715c7681034992e9cfe0dff7cf62db756fb674b3716591b838` |
| historical-evidence | 0 | `52f028c703d94ddfac7c15d9709c6f6e30e0436f0ede61ee2831a0c8307f2bfc` |
| cleanup-failure-probes | 1 | `5f645c1ed155d96c8cdd3ad035323a3635d0616592352a8135524a9fcdd91a7b` |
| package-build | 0 | `e17826860b152bcf563930df90acfc5022aac6fbdcce59a3dff86f3cdb7fe524` |
| wheel-from-actual-sdist | 0 | `6f38e4999039370a6dadc3fa345e976c8d366d82b7fec832b99bc0f5e04421cd` |
| direct-wheel | 0 | `32c27f9d09366eea43574a6682cdd8abb8d157d095e0ba75e84d8eb0281f6dc6` |
| review-lint-initial | 1 | `fa882f1e2734842eba8c5dacb97a233c3aaf435da9416e65b610f63ff0e95435` |
| isolated-package-verification | 0 | `762b6347d052d8ce0b44a0317944b93239c83b7085090d3143f3c8f8e83e78dc` |
| final-historical-audit | 0 | `52f028c703d94ddfac7c15d9709c6f6e30e0436f0ede61ee2831a0c8307f2bfc` |
| final-independent-probes | 1 | `f76c90afc0f3c80adcd20b7230db3d5d73b012ca61d20c4c209d0b5d5e7adbf5` |
| final-lint | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| contract-freeze | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| cpu-environment | 0 | `84f452a7a885c5adde2a72f2f3bbcf61a8b6bbf10c0a49762b7e9e6eb8e55c7b` |
| public-content | 0 | `1c7650d394be6ba16e102fb345bd345bebd3a84a551749fbfc3cf0300cfbf9e4` |
| scope-and-staged-diff | 0 | `a65bc7b5f0a55dc485eff6f08d60bce86e32c2e960b09d6e9d3427a324b645ad` |

<!-- COMMAND_TABLE_END -->

提交前执行公开内容扫描、staged diff 检查与范围校验；最终七个新增文件均纳入扫描，候选 146 个 tracked 文件保持相同字节，P01/P02 审查分支保留。自指 commit hash 由原生交接消息给出，报告不伪造自身提交 hash。

NOT_RUN：任何 MLX/Torch/Transformers、模型或 tokenizer 导入；权重下载、GPU 作业、真实吞吐/显存/长期稳定性；P04 真后端、P06/BFCL/最终隐藏评测；R1 本机 Python 3.11/3.12/3.13；E1 新修复候选；P02 的 kris 语义批准；付费云/API、业务写入、模型/数据上传、公网推理部署。S0 的 CI 记录不替代上述本机未测项。本轮交回 S0 后等待修订授权。
