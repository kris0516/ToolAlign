# E1｜P04 Colab 清理确认 r3

状态：READY。owner E1，协调者 S1。从 r2 精确候选 `172a462fc5f39283a3aea8b7d11062a3f8e7fcc6` 在自己的既有 worktree 建 `codex/p04-colab-environment-r3`；保留 r1/r2 分支和全部失败现场。authorization_commit 随原生派发提供。

本轮针对稳定问题 `P04-COLAB-PROCESS-001`。S1 的组合检查为42通过/1失败，`exit.json` 为超时后清理未确认、EPERM。R1 本轮独立定位到 SIGKILL 已成功发送，随后 `killpg(pgid, 0)` 查询返回 EPERM，子进程随后已不存在。当前实现对该查询异常立即退出，因此拒绝导出。正式 r2 报告及计数由 S1 后续接收，不因本次派发提前或重复累计。

先核对 E1 自己的信号级复现，再作最小修复：已观察的存活查询 EPERM 应在既有有界确认窗口内继续确认；不能将 EPERM 直接视为清理成功，不能忽略实际 SIGTERM/SIGKILL 发送错误，也不能取消超时后未确认就拒绝导出的边界。只有取得组已消失的确切证据才能标记完成；持续不确定必须保留失败和实例。优先复用当前等待逻辑，不添加通用进程管理层或无关平台适配。

允许修改 `scripts/colab/remote.py`、直接相关 `tests/colab`，新增 `reports/experiments/P04_COLAB_ENVIRONMENT_R3.md`、`coordination/handoffs/P04-colab-environment-r3.md`。必要时修正 `docs/18_CUDA_RUNTIME.md` 的直接相关说明。锁文件、T1/数据/配置、共享状态和历史报告不改。

用有鉴别力的 CPU 检查证明短暂查询 EPERM 不再提前终止、持续无法确认时仍拒绝导出；保留真实同组后代退出用例及原失败。无需重跑未变的全部数据和数值检查。共享 CPU 环境不变；每命令至多300秒、2线程、独占新私有输出目录，总新增证据至多200MiB。GPU、SSH、模型、真实数据和新安装均0。

交精确实现/候选提交、源码和实际命令证据、原失败保留情况。R1随后独立复审，E1不能自行关闭正式问题。
