# P04 Colab 环境与控制：R1 独立复核

**FAIL：P0=0、P1=2、P2=0。** 两个已复现的控制缺陷需要在 S1 的真实 Colab 验证前修订：超时后可能留下活跃后代进程；停止实例前没有重新核对全部已登记 run 的 Mac 副本。

2026-10-26，独立 R1，gpt-6-astra/max。授权 `e138ee0cc901619f4cbed73f25b94d3733b27a98`；最终 reviewed candidate **`8faa75e7010290a11f13a8006fba5d4b16ac44f9`**，实现 `b6970f656c727b57e5e64422f88393b312e87e76`，差异基线 `61c2176d556fd0e4cfc2af00b16242dddcfadfd3`。8faa 在 b697 后仅增加 E1 报告与交接。本审查采用 coordination.v1 与授权中的 CUDA 协议；没有改实现、锁或共享状态。

## P1：父进程退出后，超时清理遗漏仍活跃的后代

建议稳定 issue ID：`P04-COLAB-PROCESS-001`。

位置：[remote.py](../../scripts/colab/remote.py)，`worker()` 第 262–270 行。向进程组发送 SIGTERM 后，代码只等待直接父进程；仅当该父进程继续存活时才升级为 SIGKILL。父进程先退出、同组后代尚未退出时，控制器立即写入 `exit_code=124`，不再清理剩余进程组。它因此不能保证作业在超时后停止，残留进程可能继续写输出或占用资源。

最小复现使用原 `run` fixture 和原 `worker()`：

1. 在独占临时 Git 根创建原创假训练入口，预算 3 秒。
2. 入口启动一个**同进程组**的真实 Python 后代；后代忽略 SIGTERM 并持续写心跳，父进程保留默认 SIGTERM 行为。入口记录后代 READY。
3. 调用 `worker()`。实际返回 **124**、写入终态后，后代心跳继续变化；独立断言失败。R1 在 finally 中清理该后代，后续进程查询确认父进程和后代均不存在。

私有证据：`commands/03-independent-control-v2/`、`descendant-result-v2.json` 和 `test_independent_control_v2.py::test_timeout_terminates_descendant_after_leader_exits`。这是真实 CPU 子进程行为，没有模型或 GPU。

建议修订：父进程退出不能替代自有进程组结束；超时清理应有界确认并清理剩余成员，再记录完成。新增回归须包含“父进程先退出、后代仍存活”，保留原正常退出和超时检查。本条证据只覆盖 E1 的同组后代；T1 草稿中另建 session 的行为及 S1 所报组合案例不作为本候选的正式实跑证据，组合验收另做。

## P1：停止时只重新读取当前 run 的 Mac 副本

建议稳定 issue ID：`P04-COLAB-RECOVERY-001`。

位置：[control.py](../../scripts/colab/control.py)，`stop()` 第 211–223 行；相关远端检查为 [remote.py](../../scripts/colab/remote.py) 第 350–359 行。本地仅检查当前 `directory/recovered.json` 指向的文件。远端虽遍历所有 run，却只检查历史 recovery acknowledgement 和仍在实例上的输出，无法知道其他 run 的 Mac 副本是否仍完整。

最小复现：在同一 endpoint 登记两个终态 run，分别执行真实文件归档、Mac 复制、完整读回和远端确认；随后损坏 run 1 的 Mac checkpoint 文件并删除其下载 tar，保留 run 2 完整。从 run 2 调用原 `stop()`，实际仍向伪 CLI 发出一次具名 `stop`，返回 **`STOPPED_AND_ABSENCE_VERIFIED`**。检查期望拒绝停止的断言失败。真实实例在此条件下停止，会使较早 run 缺少可验证的完整持久副本。

私有证据：`commands/03-independent-control-v2/`、`all-runs-recovery-result-v2.json` 和 `test_independent_control_v2.py::test_stop_revalidates_every_registered_run_copy`。仅 CLI/SSH/tmux 是本地替身；两个 run 的导出、复制、清单、读取、损坏及 stop 条件判断均实际执行。

建议修订：停止前应取得并逐一验证该 endpoint 所有需保留 run 的当前持久副本，并把结果与远端当前快照绑定；任一副本缺失或损坏时保留实例并要求重新回收。回归应使用至少两个 run，证明较早 run 的副本损坏也会阻止从较新 run 停止。

## 已支持的分项结果

- R1 在最终候选上复跑 `tests/colab`：**19 passed**，exit 0。覆盖缺失 session 在 SSH 前拒绝、其他 endpoint 拒绝、安装与训练分离、已有/已回收 run 不再启动、失败/超时记录、单 run 完整回收以及当前副本损坏拒绝停止。
- Linux 48 个固定包及 hash 与 E1 原解析 stdout 逐字一致；Mac CPU 37 个固定包与 S1 已有共享环境逐包匹配。8 份已保存的官方 PyPI 元数据中，37 条适用的 Linux 依赖约束满足；原生 tokenizer 需要的 `tokenizers=0.22.2`、`Jinja2=3.1.6` 符合既有守卫。
- 抽查 E1 的 10 条原始命令，核对 stdout/stderr 与回执。最终 lint/3.14 测试的源码摘要与候选一致；原 3.12 的 19 项测试直接绑定 b697，8faa 的后继差异仅为报告。复用这些精确证据，没有重新解析依赖或重跑旧全套检查。
- E1 原 CPU Qwen3/PEFT/tokenizer 导入记录与共享环境版本一致；它证明接口可导入和 LoRA 配置可构造。该记录发生在最后两份控制文件修改前，只作为外部依赖接口证据，不冒充最终控制代码测试。

## 本轮命令与失败记录

`PY312` 为 S1 已建立的唯一 CPU Python；`R1_PRIVATE` 为本轮私有证据目录。全部执行设置本 worktree 的 `PYTHONPATH=src`、`HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`、OMP/MKL 各 2 线程。每次 pytest 使用不同且此前不存在的独占 basetemp；单命令上限 300 秒。原始回执保留完整绝对 argv、UTC、退出码和输出。

| 命令记录 | 实际命令摘要 | 退出码与结果 |
|---|---|---|
| 01-suite | `PY312 -B -m pytest -q tests/colab --basetemp NEW_TMP_1` | 0；19 passed，4.64 秒 |
| 02-independent-control | `PY312 -B -m pytest -q -s R1_PRIVATE/test_independent_control.py --basetemp NEW_TMP_2` | 1；较早副本损坏仍停止已复现；最初 1 秒 fork 探针未得到 READY，不作为进程缺陷证据 |
| 03-independent-control-v2 | `PY312 -B -m pytest -q -s R1_PRIVATE/test_independent_control_v2.py --basetemp NEW_TMP_3` | 1；2 个阻断断言失败，4.09 秒；已确认后代 READY，并覆盖较早 tar 也缺失 |
| 04-evidence-audit | `PY312 -B R1_PRIVATE/audit_evidence.py` | 1；R1 将早期纯依赖导入记录误套最终控制源码一致性断言，原失败保留 |
| 05-evidence-audit-r2 | `PY312 -B R1_PRIVATE/audit_evidence_r2.py` | 0；10 条原回执、48/37 pins、37 约束、两条复现和进程清理确认 |

E1 的 CA、候选索引解析、unused import、回收后重启四类原失败已抽查并保留。R1 初次探针和辅助核对错误也保留，不计作新的候选问题或重复正式失败轮次。公开材料检查和 Git 提交回执随最终交接保存。

## 验收边界与下一步

本次 verdict 只针对 E1 环境与控制候选。GPU 分配、SSH 连接、新环境/依赖安装、模型下载/加载及训练均为 0。真实 Linux 安装/pip check、CUDA 容量、T1 完整 checkpoint 语义、新进程及新实例恢复仍须在修订通过与集成后验证。

S1 按稳定 issue ID 组织最小修订和复审，再决定有界 Colab 运行；正式失败计数由 S1 维护。本轮不批准 T1 草稿或真实 GPU 结果，也不因已有 19 项通过而忽略上述两项阻断。
