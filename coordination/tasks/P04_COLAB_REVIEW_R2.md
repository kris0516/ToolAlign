# R1｜P04 Colab r2 与 CUDA 组合复核

状态：READY。owner R1，协调者 S1。E1 最终候选 `172a462fc5f39283a3aea8b7d11062a3f8e7fcc6`，实现 `a662567b9adf3c47d748b19e1c4bb8ca8689e4b9`，修订基点 `8faa75e7010290a11f13a8006fba5d4b16ac44f9`。S1 已在待审工作分支组合该候选与已审 T1，精确组合提交 **`ddc4aef8b332c5f30db84e84c29bd571a8439a0e`**；未合并 main。authorization_commit 由原生派发提供。

复用 R1 自己的干净 worktree，从组合提交建 `codex/review-p04-colab-environment-r2`，保留两份旧审查分支与私有证据。先保存本次授权。只新增 `reports/reviews/P04_COLAB_ENVIRONMENT_R2.md`、`coordination/handoffs/P04-colab-environment-review-r2.md` 和必要私有复现；不得修生产实现、锁或共享状态。

核对 E1 r2 差异与原 `P04-COLAB-PROCESS-001`、`P04-COLAB-RECOVERY-001` 复现：父进程先退出的同组后代应被有界清理；停止前必须校验全部登记 run 的当前完整 Mac 副本与远端快照。覆盖不同 local_root 的显式 recovery_directories、缺失/错误映射、较早副本损坏或 tar 缺失拒绝停止，以及重新回收后能够正常停止。保留原 FAIL，不改其统计；最终由 S1 接收一次正式复审事件。

组合中 T1 仍是已审 `4342af87615197c7947d001f462d3d31500cd501` 的同一源码，已有独立 PASS `7d460f2054201c00055a1f924c5c4984be8e6988`。核对组合文件一致性，并用原创小型 CPU actor 验证 E1 外层 timeout 触发实际 T1 supervise 的 SIGTERM 清理，最终两层自有进程都退出；不要把同进程组用例代替跨 session 组合。仅替换原测试的模型/数据工作负载，不加载真实模型。原 14 项数值和未变依赖证据沿用。

运行本轮必要的定点检查与两项独立复现；复用既有共享 Python 3.12，PYTHONPATH 指向自己的 src，OMP/MKL各2，pytest使用新的独占basetemp。单命令≤300秒，新增私有证据≤200MiB。真实prepare/新编码、模型、GPU、SSH、新环境/依赖安装均0。最终裁定明确列出E1候选、组合SHA、两项issue结论与组合边界，交精确review提交、实际命令/退出码、保留失败及未验证项。
