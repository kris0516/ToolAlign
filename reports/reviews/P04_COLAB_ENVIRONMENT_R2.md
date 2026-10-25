# P04 Colab r2 与 CUDA 组合：R1 独立复核

**FAIL：P0=0、P1=1、P2=0。** `P04-COLAB-PROCESS-001` 尚不能关闭：本机 CPU 回归中，SIGKILL 成功发送后，进程组的 signal-0 探测返回 EPERM，清理被记录为未确认，阻断后续导出。`P04-COLAB-RECOVERY-001` 的修订通过；E1 外层 timeout 与实际 T1 supervise 的跨 session 清理通过。

2026-10-26，独立 R1，gpt-6-astra/max。授权 **`5b80ddf1cdf884d66af755f38bffd111e85929dc`**；E1 最终候选 **`172a462fc5f39283a3aea8b7d11062a3f8e7fcc6`**，实现 `a662567b9adf3c47d748b19e1c4bb8ca8689e4b9`，差异基线 `8faa75e7010290a11f13a8006fba5d4b16ac44f9`；本轮实际检出及执行的组合提交为 **`ddc4aef8b332c5f30db84e84c29bd571a8439a0e`**。本报告不改写[原 r1 FAIL](P04_COLAB_ENVIRONMENT_R1.md)。

## P1：PROCESS-001 的清理完成确认仍会失败

位置：[remote.py](../../scripts/colab/remote.py#L253)，`terminate_owned_group()` 第 253–257 行；影响传播至 `worker()` 第 289–293 行及 `export()` 第 326–329 行。

r2 已改为等待自有进程组，并在 SIGTERM 后仍存活时升级 SIGKILL。R1 首次运行 26 项控制测试及原同组后代复现都通过；随后 S1 在生产源码相同的 `5b80ddf` 组合检查中得到 **42 passed / 1 failed**，失败项为 `test_timeout_cleans_same_group_descendant_after_leader_exit`，终态为 `timeout_cleanup_completed=false`、`[Errno 1] Operation not permitted`。S1 的该次记录没有定位到具体信号调用。

R1 在冻结的 `ddc4aef` 上做了一次独立诊断：先导入共享环境中已有的 Torch 2.8.0，再运行上述原测试；只给 `os.killpg` / `os.kill` 加入转发原调用、保留原返回值和异常的记录器，未改生产代码或测试断言。结果为 **1 failed / 6 deselected**。实际调用顺序是：

1. 向自有组发送 SIGTERM，调用成功。父进程退出，同组后代仍在运行。
2. 等待约 10 秒后向该组发送 SIGKILL，调用成功。
3. 随后的 `os.killpg(pgid, 0)` 抛出 EPERM；该异常直接离开有界等待循环。
4. fixture 的 finally 再向已知后代发送 SIGKILL 时得到 ESRCH，进程查询也已为空。最终复查确认本次父、子进程均不存在。

这次证据支持的是**SIGKILL 后的完成确认失败**，不支持“SIGKILL 被拒绝”或“仍有活跃后代”的描述。未确定 EPERM 的内核原因；本轮也没有以对照实验认定 Torch 导入是成因。S1 原失败与 R1 诊断的测试上下文分别保留。

由于探测仅处理 `ProcessLookupError`，EPERM 会使 `worker()` 保持 `timeout_cleanup_completed=false` 并写入终态。`export()` 随后按既有规则拒绝该 run；即使后代已退出，也不能通过正常回收与停止流程。因此，必需的清理完成契约尚未满足，沿用原 P1 issue，本轮不予关闭。实跑范围是 Mac CPU 控制回归，未据此声称真实 Colab/Linux 已复现同一现象。

建议最小修订：区分实际终止信号的发送失败与 signal-0 探测失败，在原有时间界内确认自有组是否仍有活跃成员。不能把任意 EPERM 当作组已消失，也不能吞掉 SIGTERM/SIGKILL 的真实发送失败；无法确认清理时继续拒绝导出。新增回归应覆盖本次探测边界，并保留原父进程先退出的真实后代用例。

关键私有证据为 `commands/trace-s1-signal-boundary/`、`trace_signal_boundary.py`、`signal-trace.jsonl` 和 `signal-boundary-adjudication.json`；原 S1 回执及测试文件保存在 `s1-integration-failure/`。信号原始记录 SHA-256 为 `d62f3baec16b9d8ef6ff3fbdc87b87485f2b6505fed4014130a184290b6abdbd`。

## RECOVERY-001：通过，建议关闭

[control.py](../../scripts/colab/control.py#L211) 现在验证当前 tar 的长度与摘要、manifest 与远端快照的绑定以及解包文件；`stop()` 逐一验证远端返回的完整 run 清单，并支持不同 `local_root` 的显式 `recovery_directories`。[remote.py](../../scripts/colab/remote.py#L369) 在持有登记锁时确认全部 run 已回收、输出未变，并阻止新的 setup/launch 进入待停止实例。

R1 复用原两个 run 的独立复现，仅补充新接口要求的正确目录映射，并保留原损坏操作和拒绝停止断言：较早 run 的 Mac checkpoint 被改写且 tar 被删除，较新 run 的副本完整。实际结果为针对较早 run 的完整性错误，具名 `stop` 调用数为 **0**；重新回收较早 run 后，同一流程成功返回 `STOPPED_AND_ABSENCE_VERIFIED`，`stop` 调用数为 **1**，endpoint 确认消失。

本轮实际通过的 26 项控制测试还覆盖 checkpoint/tar/两者损坏、伪造 manifest、缺失或错误目录映射、正确跨目录映射、修复后停止及已停止实例的保存清单复核。原较早副本损坏仍能停止的反例已关闭。CLI/SSH/tmux 使用本地替身；导出、tar、复制、损坏、读回和停止条件检查为真实文件操作。

## 跨 session 组合：通过

组合中 E1 文件与精确 `172a462` 一致，T1 源码、测试和配置与已审 **`4342af87615197c7947d001f462d3d31500cd501`** 一致；沿用其独立 PASS **`7d460f2054201c00055a1f924c5c4984be8e6988`**。

R1 使用实际 E1 `worker()` 调用实际 T1 CLI 与 `runtime.supervise()`，只将模型/数据工作负载 `runtime.execute` 替换为原创 CPU 心跳函数。原 supervisor、spawn、子进程 session、SIGTERM handler 和清理路径均执行；恢复真实 E1 源码校验，未以同进程组替身代替组合边界。

实测外层 3 秒预算先触发，T1 actor 收到 SIGTERM 并以 143 退出，其实际后代具有不同 PGID/SID。返回时两层 PID 和进程组均不存在，心跳停止，handler 已恢复；E1 记录 124、`timed_out=true`、`timeout_cleanup_completed=true`。两个 actor 均未加载模型框架。该组合结果单独通过，不抵销上一节的进程组确认失败。

## 执行记录与复用证据

`PY312` 指既有共享 CPU Python 3.12.14，`PY_LINT` 指既有 lint Python，`R1_PRIVATE` 指本轮私有目录。执行使用本 worktree 的 `PYTHONPATH=src`，HF/Transformers 离线，OMP/MKL 各 2 线程。所有 pytest 都使用新的独占 basetemp，单命令上限 300 秒；下表时间为原命令回执的 wall time。完整绝对 argv、UTC、退出码及 stdout/stderr 原位保留。

| 命令记录 | 实际命令摘要 | 退出码与结果 |
|---|---|---|
| author-suite | `PY312 -B -m pytest -q tests/colab --basetemp NEW_TMP_1` | 0；26 passed，28.64 秒 |
| independent-and-combined | `PY312 -B -m pytest -q -s R1_PRIVATE/test_independent_control.py R1_PRIVATE/test_combined_timeout.py --basetemp NEW_TMP_2` | 0；3 passed，18.18 秒 |
| evidence-audit | `PY312 -B R1_PRIVATE/audit.py` | 0；18 份 E1 原回执、复现来源和当时通过结果核对，0.34 秒 |
| ruff | `PY_LINT -B -m ruff check scripts/colab tests/colab` | 0；0.04 秒 |
| trace-s1-signal-boundary | `PY312 -B R1_PRIVATE/trace_signal_boundary.py` | 1；1 failed / 6 deselected，15.06 秒；上述真实信号探测反例 |

早期 `evidence-audit.json` 的 PASS 只表示其当时检查通过；后收到的 S1 失败及 R1 独立诊断已纳入本报告最终 FAIL，未覆盖旧记录或以再次通过替换失败。原独立复现文件与 r1 副本逐字一致；新增接口适配另存 diff。

E1 的 18 份命令回执及 stdout/stderr 已核对，最终 lint/26 项测试的源码摘要与候选一致。原基点复现失败、修订期间父进程等待/手工 receipt 缺字段失败及 lint 失败均保留。未变的 Linux 48 pins、Mac CPU 37 pins 和原元数据证据，以及 T1 原 14 项数值证据沿用，未重复解析依赖或运行数值全套。

本轮只新增本报告、交接和私有复现；未修改生产代码、锁、main 或协调状态。真实 prepare、新编码、模型下载/加载、GPU、SSH、新环境及依赖安装均为 0；自有测试进程已确认退出。真实 Linux 安装/CUDA 运行及新实例 checkpoint 恢复不属于本轮实跑结论。

S1 可接收 RECOVERY-001 和跨 session 组合的分项通过，针对 PROCESS-001 组织下一精确修订复审。本报告仅作为一次正式 r2 复审事件，问题计数由 S1 维护；E1 后续 r3 不并入本冻结候选。
