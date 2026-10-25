# E1｜P04 Colab 控制修订 r2

状态：READY。owner E1，协调者 S1。原代码基线 `61c2176d556fd0e4cfc2af00b16242dddcfadfd3`，本轮修订基点 `8faa75e7010290a11f13a8006fba5d4b16ac44f9`；R1 正式审查 `2f449452636712f2622d40a3040a45034e56228f`，S1 仅移入审查材料的映射提交 `81cb0be1f12cd9312035f00a378ea63dce52dbf6`。authorization_commit 由原生派发给出。复用 E1 自己的干净 worktree，建立 `codex/p04-colab-environment-r2`，保留 r1 分支、报告和私有失败证据。

目标：关闭 [R1 报告](../../reports/reviews/P04_COLAB_ENVIRONMENT_R1.md) 的两项 P1。本次各计第一次正式未通过；自主修订，未到整体暂停阈值。原 [E1 任务](P04_COLAB_ENVIRONMENT.md) 的模型/数据/资源边界不变。

- `P04-COLAB-PROCESS-001`：超时后父进程先退出、同组后代忽略 SIGTERM 仍写入。需有界清理自有进程组，再记录完成；保留正常失败退出码与超时记录。不要把整个系统进程树作为清理目标。T1 另建 session 的外部 SIGTERM 清理由 T1 修复，双方最终组合仍需独立验证。
- `P04-COLAB-RECOVERY-001`：停止时只重读当前 run 的 Mac 副本，较早 run 的文件损坏且 tar 缺失仍能停止。需在停止前核对该 endpoint 所有需保留 run 的当前完整持久副本，并与远端当前快照绑定；任一缺失或损坏须拒绝停止并支持重新回收。

先复现原候选的两个失败，再作针对性修复。可读取 R1 精确私有复现脚本和结果，路径由原生消息给出；不得改写 R1 证据或把修复后的结果覆盖原失败。至少用两个 run 验证较早副本损坏会拒绝停止，重新回收后能够停止；进程检查包含父进程先退出且后代仍存活。R1 重读同一候选不重复增加失败计数。

允许修改 `scripts/colab/`、`tests/colab/`、必要的 `docs/18_CUDA_RUNTIME.md`，新增 `reports/experiments/P04_COLAB_ENVIRONMENT_R2.md` 与 `coordination/handoffs/P04-colab-environment-r2.md`。不改训练源码、共享配置、环境锁或协调状态；不引入通用进程管理框架。

复用 S1 已建立的唯一 CPU 环境，`PYTHONPATH` 指向自己的 `src`，每次 pytest 使用新独占 basetemp；单命令至多 300 秒、2 线程，新增私有证据至多 200 MiB。GPU、SSH、新环境/依赖安装、真实模型/训练均为 0。定点测试、ruff、公开扫描后交精确提交、实际命令、原失败与未验证项；依赖锁和未受影响的旧验收沿用已有证据。S1 再派 R1 独立复审，通过后才推进真实 Colab 验证。
