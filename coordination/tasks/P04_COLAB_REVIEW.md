# R1｜P04 Colab 环境与控制独立复核

状态：READY。owner R1，协调者 S1。代码基线 `61c2176d556fd0e4cfc2af00b16242dddcfadfd3`；待审代码提交 `b6970f656c727b57e5e64422f88393b312e87e76`；authorization_commit 由原生派发给出。E1 的最终报告提交另由 S1 提供，报告变更不能替代代码差异复核。

目标：独立判定 E1 的依赖锁、Colab 控制和持久化回收是否可进入 S1 的有界真实验证。范围是 [E1 任务](P04_COLAB_ENVIRONMENT.md)，训练接口按 [CUDA 协议](../../configs/sft-cuda.v1.json)；T1 实现和真实 GPU 结果不在本次 verdict 内。不得将本地模拟写成 Colab 实测。

复用 R1 自己的干净 worktree，在待审提交上建立 `codex/review-p04-colab-environment-r1`，保留私有历史证据。先读取授权提交中的当前 AGENTS、PROTOCOL、GOAL、REVIEW_POLICY 和本任务，再切换分支。只写 `reports/reviews/P04_COLAB_ENVIRONMENT_R1.md`、`coordination/handoffs/P04-colab-environment-review-r1.md` 和本轮私有复现证据；不修生产代码、环境锁或共享状态。

检查精确 diff 和原始证据，运行必要的定点测试。重点覆盖：Linux 锁与原生 tokenizer/Qwen 接口；setup 不触发模型或训练；缺失 session 在 SSH 前拒绝；单一 train argv 与 run 身份；tmux/PID/退出码/超时；已运行及已回收 run 不重复启动；完整输出下载、逐文件读回及停止前快照一致性；只停止自有实例；同实例恢复与新实例恢复的证据边界。选择性核对失败记录，不复跑未受影响的旧全套检查。

CPU 命令使用 S1 已建共享 Python 环境，绝对路径由原生消息给出，`PYTHONPATH` 指向 R1 自己的 `src`。pytest 使用新的独占 `--basetemp`。本包 GPU 分配/SSH/下载模型/真实模型加载/训练均为 0；不新建环境、不安装 CUDA wheel。每次 CPU 命令至多 300 秒、2 线程，新增私有证据至多 200 MiB。若缺输入，给出具体缺口，继续不依赖它的审查。

交付 PASS/FAIL/BLOCKED、精确 reviewed commit、实际命令/退出码、关键证据与未验证项。发现阻断项给 P0/P1/P2、最小复现和稳定 issue ID 建议，不代改作者实现；S1 维护正式失败计数。审查通过后由 S1 集成，真实 Linux 安装、GPU 容量与跨实例恢复仍须后续实测。
