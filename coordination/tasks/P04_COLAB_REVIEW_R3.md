# R1｜P04 Colab 清理完成确认 r3 复核

状态：READY。owner R1，协调者 S1。E1 r3 实现提交 `93a837e345856b1067d221f411b537b933fe7f89`，相对 r2 `172a462fc5f39283a3aea8b7d11062a3f8e7fcc6`；实际组合提交 **`0eaad46e115d1296ce83cf22d5cc1f5aea86011c`**。E1 正在整理报告/交接，后续若仅文档变化，由 S1 提供最终候选，核对后沿用相同实现检查。authorization_commit 随原生派发提供。

从组合提交在 R1 既有 worktree 建 `codex/review-p04-colab-environment-r3`，保留 r2 审查分支、原失败和私有证据。只新增 `reports/reviews/P04_COLAB_ENVIRONMENT_R3.md`、`coordination/handoffs/P04-colab-environment-review-r3.md` 及必要私有复现；不改实现、测试、锁或共享状态。

本轮只复核 `P04-COLAB-PROCESS-001` 的实际差异及同组超时清理边界。确认 signal-0 短暂EPERM在既有时间界内继续查询，必须得到组消失的证据才完成；持续不确定仍拒绝导出；实际TERM/KILL发送异常仍失败。核对新增4项判别检查，并用真实原CPU后代用例验证修后执行。可复用已有信号转发记录器，保留原r2失败。考虑S1原集成和R1诊断均已导入共享Torch的上下文，复现时沿用该已观察上下文，但不把Torch认定为原因。

沿用r2 `65ffcc31dd51d2b54475a446c74015265e719b61` 中RECOVERY-001和实际E1→T1跨session组合的PASS，核对相关实现未变即可；不重做全部数据、数值、依赖解析或不受影响的恢复测试。E1作者30项控制检查的实际命令及修前/修后证据按最终交接核对。

共享Python 3.12 CPU环境不变，PYTHONPATH指向R1自己的src，OMP/MKL各2，每命令≤300秒、新证据≤200MiB，pytest独占新basetemp。真实prepare/新编码/模型/GPU/SSH/新安装均0。最终给精确候选/组合、独立裁定、保留失败和未验证边界；S1接收后更新正式次数。
