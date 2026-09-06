# P03-CI-DEADLINE｜请求截止时间测试的确定性复现与修复

状态：VERIFIED；E1完整947144f获[R1精确候选独立审查](P03_CI_DEADLINE_REVIEW.md)正式PASS，原review1531892已发布，S0封存核验通过；R1/E1均已结束；PR8已合并36b6988并通过最终CI/main验证。E1原授权仍为完整`fa1ea86361223171a06b5d082a3731b63a00a74a`，gpt-6-astra/max。仅此 CPU 测试问题；不重开已验收的 P03 实现或新格式实现。

| 字段 | 本轮值 |
|---|---|
| owner | E1，现有独立 Codex 任务及隔离 worktree |
| code_base | `4a1fa84d2d367ed037a1e39b1d4033f54a385e6a`，已验收 P01/P03 的当前 main |
| authorization_commit | S0 原生派发给出的本文件完整提交 SHA；切换前用 git show 读取并私有保存 |
| 新分支 | `work/p03-ci-deadline`，从精确 code_base 新建；保留原 work/p03-execution-harness 及其未改提交 |
| 模型 / 推理 | `gpt-6-astra` / `max` |
| 契约 | plan-v0.1 / coordination.v1 / toolalign.contracts.v1；公共契约/协议不变 |
| 正式交接 | `coordination/handoffs/P03-ci-deadline-r1.md` |

## 触发证据

新格式本身已获 R1 对 8c439f6 的正式 PASS，review 为 `b9f7567d7c1066eeb0bff7c47033bb2771eb9594`。S0 普通整合该原 review 与当前 main，最终候选为 `2b11b7fad69957324ecfa671bac71552ec3501b7`；PR8 仍 Draft，尚未合并。

[CI34024093376](https://github.com/kris0516/ToolAlign/actions/runs/34024093376) 的 Python3.11 全部步骤成功。Python3.14.7 / Ubuntu24.04.4 的 pytest 为 **1 failed / 484 passed / 48 skipped，86.61s**；唯一失败是 `tests/evaluation/harness/test_harness.py::test_monotonic_request_deadline_survives_tool_wall_clock_jump` 第709行。`timed_out`、latency<1500ms、一个 model decision/tool round 的断言已经通过，但 tool 的 `operation_started` 为 false。

该测试把 executor 的 utc_remaining 固定为10000，给整个请求0.6秒，却要求工具子进程已经进入执行。请求预算包含模型与工具 spawn，启动时间不受这项测试保证。上述日志本身未证明生产超时/回收错误；E1须独立核实，不预先把 CI 失败归为格式问题或平台故障。详见[S0证据](../../reports/S0_P02_FORMAT_CI_FOLLOWUP.md)。

code_base 与失败候选的以下文件字节完全相同：

| 路径 | SHA-256 |
|---|---|
| tests/evaluation/harness/test_harness.py | `f43ae42822cab11281e3a9b1d89c56e12d162a7582b32dfa679610563e58c467` |
| src/toolalign/evaluation/harness.py | `b4aff77d4adffea786d742d5c5aeeee72f99feaf3783ee0f01ad504aa84bb987` |
| src/toolalign/tools/executor.py | `28d321f0a2606df883c1d93ba96f7b875356c9323213ec2d77b737dae2d71e2d` |
| src/toolalign/tools/isolation.py | `84a96791205488bad6bd3fe43a42f33f7abcbfb5fc8bb0b64f27aa13e5667f6f` |

## 允许范围

允许修改 `tests/evaluation/harness/test_harness.py` 中该测试及其必要局部 helper；如 spawn 需要可导入 helper，可新增 `tests/evaluation/harness/deadline_cases.py` 或 `tests/evaluation/harness/test_request_deadline.py`。允许新增 `reports/harness/P03_CI_DEADLINE_VERIFICATION.md`、`reports/harness/P03_CI_DEADLINE_EVIDENCE.json` 及本轮交接单。

所有 `src/`、其他测试、fixtures、既有 reports/review、原报告/日志、公共契约/配置/依赖/CI/检查脚本/协调状态、其他 worktree 均只读。不要 merge 未验收的格式候选或随后 main；本轮基线已含相同 P03 代码。若发现需要生产修复，先给 S0 具体反例和建议路径，再等范围更新，不自行扩大。

## 要完成的验证

1. 在自己的新分支核对四文件身份与 CI 原日志，保存原测试。用明确受控的慢启动/阶段边界证明旧测试何时未进入工具执行仍正确到期；保存实际命令、结果、退出码、原始失败及进程状态。普通本机一次通过不算已解释该失败。
2. 修正不受保证的启动时序假设，继续验证真实工具阻塞、单调时钟限制请求、UTC跳变不能延长请求、明确自有进程真正停止/回收。区分“启动前预算耗尽”和“已经执行后到期”，不能将前者冒充后者。
3. 证明回归有效：正常控制通过，受控移除/绕过请求单调截止约束的负向控制会被测试拒绝；负向控制只能在本轮测试/私有副本，必须有独立有界结束与自有进程清理，不改生产源码或留挂起进程。可以合理设计测试时钟/同步点，但如使用替身须明确，不把假进程或假回收当作真实运行。
4. 不以仅重试 CI、skip/xfail、删除有意义断言、修改全局收集规则或任意放宽超时取得绿灯。若调整时间预算，须解释测试仍证明了哪条边界及负向控制如何失败；不要建立新的进程/时钟框架。
5. 在最终候选运行相关 harness/工具生命周期回归及当前基线适用的完整 CPU 检查，Ruff/冻结/公开扫描。复用既有纯 CPU 环境。测试文件会进入 sdist，核对实际新 sdist/默认及显式重建 wheel 的当前 Git 载荷；生产包字节必须保持。未变的安装/模型路径不无理由重复扩大。

## 资源、交接与下一步

只有一个 E1 实现；D1/T1/R1均无新工作。仅 CPU，新增私有制品累计上限2GiB；不新建 ML 环境、下载模型、导入模型框架、占GPU、运行正式评测/BFCL、写人审或发生费用。不 push 现有 P03/格式 PR 分支，不合 main，不改旧 refs。允许在完整交接后普通推送本轮新 `work/p03-ci-deadline` 分支，原始 SHA 和失败保持。

交接包含精确候选/parent/tree、允许路径差异、原/新测试各自 hash、实际正负控制/回归/归档命令与日志 hash、所有失败和 NOT_RUN。没有实际观察到的状态不签通过。提交后结束本轮，等待 R1 对该精确候选独立复核；S0随后普通集成该修复与已审格式，再运行最终CI/main验收。准备本任务不等于派发，R1原格式PASS也不自动批准此测试修订。


2026-09-06 S0主干验收：原候选947144f与原review1531892按原SHA随PR8普通合并36b6988，最终CI34029892077的Python3.11/3.14全部步骤成功，实际main843CPU/2 HF-only skipped及归档绑定通过。P03-CI-DEADLINE技术范围VERIFIED；旧CI失败、真实负向控制与全部原证据保持，见[主干记录](../../reports/S0_P02_FORMAT_MAIN_VERIFICATION.md)。E1/R1本轮已结束，无新派发。
