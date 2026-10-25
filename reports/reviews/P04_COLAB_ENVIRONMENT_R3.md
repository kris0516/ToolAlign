# P04 Colab 清理完成确认 r3：R1 独立复核

**PASS：P0=0、P1=0、P2=0。建议关闭 `P04-COLAB-PROCESS-001`。** R1 在原 CPU 失败上下文中再次捕获 SIGKILL 成功后的 signal-0 EPERM；修订后的实现继续确认组已消失，原真实后代用例通过，终态记录 `timeout_cleanup_completed=true`。持续无法确认及实际终止信号发送失败的拒绝路径仍成立。

2026-10-26，独立 R1，gpt-6-astra/max。授权 **`173f7b1082c5edd0329786cd8a834ce24b8cd6da`**；E1 最终候选 **`6183870587f349bf56945e0709ab1488737a2556`**，实现 **`93a837e345856b1067d221f411b537b933fe7f89`**，修订基点 `172a462fc5f39283a3aea8b7d11062a3f8e7fcc6`；实际检出及执行的组合提交为 **`0eaad46e115d1296ce83cf22d5cc1f5aea86011c`**。最终候选相对实现只新增 E1 报告与交接两份文档，代码、测试及运行说明与组合逐字一致。

## PROCESS-001 的关闭依据

[remote.py](../../scripts/colab/remote.py#L253) 的修改限于 `terminate_owned_group()`：signal-0 探测返回 `PermissionError` 时，在当前期限内继续查询，未重置期限，也不将异常视为成功。仍须取得 `ProcessLookupError` 并回收直接子进程才能返回；两个确认阶段保留各自 10 秒期限。实际 SIGTERM/SIGKILL 的发送位于该异常处理之外，发送错误继续传播。持续未确认时保存错误，原 `worker()` / `export()` 保持拒绝导出的行为。

R1 执行新增的四项判别检查，**4 passed**：

- 短暂查询 EPERM 后必须继续取得 ESRCH，才能确认完成并回收直接子进程。
- 持续查询 EPERM 经两个模拟确认窗口后仍为未确认，终态保留错误，导出被拒绝。
- SIGTERM 和 SIGKILL 的发送错误分别保留为失败。

随后 R1 逐字复用 r2 信号记录脚本，在既有共享 Python 3.12.14 / Torch 2.8.0、两线程上下文中运行未修改的 `test_timeout_cleans_same_group_descendant_after_leader_exit`，得到 **1 passed / 6 deselected**。记录器实际转发系统调用，不替换返回值或异常。实测 TERM 成功；父进程退出、后代仍在同组；约 10 秒后 KILL 成功，紧接着 signal-0 返回 EPERM。实现继续检查并成功返回，原测试确认终态后心跳不再变化、进程组已不存在。finally 对已知后代的清理得到 ESRCH，R1 后续进程查询确认父、子均不存在。

本次沿用 Torch 已导入的失败上下文，不据此认定 Torch 为原因。修前和修后均观察到相同查询异常，区别是修订后有界继续确认，而非因本次未遇到异常才通过。R1 原 r2 失败记录保持不变；本轮信号记录 `signal-trace.jsonl` 的 SHA-256 为 `da92523999e3f1bbfad2916a111cbb052ecc9ad19119a6e9f85bd37468f40c50`。

## 精确证据与沿用范围

R1 核对 E1 14 份原命令回执的 stdout/stderr。002 在未改基点上真实复现失败，003 的新增检查为 2 failed / 2 passed；004–007 的实现、测试、说明摘要及实际源码 diff 与 `93a837e` 一致。005 修后真实用例通过，并再次捕获 KILL 成功后的查询 EPERM；006 lint 通过；007 为 **30 项控制检查通过**。这些作者结果按精确源码沿用，原失败保留。

与已验收的 [r2](P04_COLAB_ENVIRONMENT_R2.md) 相比，`control.py`、`common.py`、原 `test_revisions.py`、T1 CUDA 源码/测试/配置和两份依赖锁未变。`remote.py` 除本次清理函数外，其余顶层函数均未变，包括 `worker()`、`export()`、`stop_ready()`。因此沿用 r2 的 RECOVERY-001 关闭结论和实际 E1→T1 跨 session 组合 PASS；原 T1 14 项数值及 48/37 pins 证据也沿用。本轮未重跑不受影响的恢复、数据、数值或依赖检查。

## 本轮实际命令

`PY312` 为既有共享 CPU Python，`R1_PRIVATE` 为本轮私有目录。设置本 worktree 的 `PYTHONPATH=src`、HF/Transformers 离线、OMP/MKL 各 2 线程；每次 pytest 使用新的独占 basetemp，单命令上限 300 秒。时间取原回执的 wall time。

| 命令记录 | 实际命令摘要 | 退出码与结果 |
|---|---|---|
| discrimination-tests | `PY312 -B -m pytest -q tests/colab/test_cleanup_confirmation.py --basetemp NEW_TMP` | 0；4 passed，0.29 秒 |
| real-signal-context | `PY312 -B R1_PRIVATE/trace_signal_boundary.py` | 0；1 passed / 6 deselected，16.13 秒 |
| evidence-audit | `PY312 -B R1_PRIVATE/audit.py` | 0；14 份作者回执、修前/修后信号、候选绑定及自有进程退出确认，0.40 秒 |

原始 argv、UTC、退出码、输出、信号和终态文件均保留。公开文档检查、Git 提交及普通推送回执随最终交接提供。本轮仅新增本报告、交接和私有复核材料，未修改实现、测试、锁或共享状态。

本 PASS 覆盖 PROCESS-001 的 CPU 控制修订，真实 Colab/Linux/CUDA 运行及新实例 checkpoint 恢复仍待对应验收。GPU、SSH、真实模型、prepare、新编码、新环境和依赖安装均为 0。S1 接收后关闭稳定 issue 并维护正式次数；[原 r1 FAIL](P04_COLAB_ENVIRONMENT_R1.md)和 r2 FAIL 均保留。
