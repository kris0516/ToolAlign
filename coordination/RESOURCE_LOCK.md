# Mac 全局 GPU/内存资源互斥

## 1. 目的

多个 Git worktree 有不同文件，但共享同一 GPU 和统一内存。每个目录各自放一个 `gpu.lock` 会失效；不能允许 T1 训练、E1 跑整套评测、I1 启动常驻模型同时争抢内存。

## 2. 锁位置与实现要求

P00 候选实现：`src/toolalign/runtime/gpu_lock.py` 的 `GPULease`、`lock_path` 与 `inspect_gpu_lock`。CPU 竞争/异常/跨 worktree 测试位于 `tests/runtime/test_gpu_lock.py`；使用方法见 `docs/12_CONTRACTS_V1.md`。这些测试不加载模型。

P00/P01 实现时，锁根使用该仓库的**共享 Git common directory** 下 `toolalign-runtime-locks/`，或 S0 指定的本机共享私有目录。通过 Git 查询真实 common dir，而不是假定每个 `.git` 都是目录。[S16]

所有训练、偏好生成、reference 预计算、批量评测和驻留 serving 入口必须获取同一 `gpu0` 锁。锁使用 OS 文件锁或等价原子机制，单靠写一个 Markdown 状态不是互斥。

拥有锁的进程记录：task/run ID、worker alias、host fingerprint、PID、进程启动时间、获得时间、预计作业、内存策略。敏感本机信息不提交 public repository。

## 3. 释放/异常恢复

正常完成或异常退出自动释放 OS 锁。租约时间过期不意味着旧训练已退出；回收前检查 PID、启动时间及 host，避免 PID 重用或另一主机冲突。不得自动 kill 未归属本项目的进程。

检查不到进程状态时转为 BLOCKED，由 S0 协调；禁止另起第二个大模型进程“试试看”。重新接手对话必须先检查当前锁与未完成 run。

## 4. 资源与状态分开

BOARD 是计划状态，锁是运行时约束，两者不能互相替代。某任务 IN_PROGRESS 可以没有占 GPU，例如数据清洗；服务进程只要模型驻留就持有锁，不能空闲时假装释放。

P01 的故障测试须包括：两个独立进程竞争仅一个成功；持锁退出后可再次获得；不同 worktree 使用同一锁；超时等待不启动模型；锁信息不含凭据。
