# E1｜P04 Colab 真实安装索引修复 r4

状态：READY。owner E1，协调者 S1。code_base 为已合并 `920c41551f0f7f2be8a5a8dcced23cc080ac1f27`；在自己的既有 worktree 建 `codex/p04-colab-environment-r4`，保留全部旧分支与证据。authorization_commit 随原生派发提供。

真实 L4 上两次 setup 均未进入模型或训练。第一次缺 Ubuntu `python3.12-venv`，S1 已保留失败环境并安装实际候选 `3.12.3-1ubuntu0.17`，ensurepip 通过。第二次 pip 24.0 找不到 `torch==2.8.0+cu128`。实际 pip `handle_option_line` 在读取锁内 `--index-url https://pypi.org/simple` 时重置全部 finder index_urls，覆盖命令行的 CUDA extra index；直接查询 CUDA 源明确包含该版本。S1 保留两次日志并回收、停止实例，后续重试仍由 S1 签发。

本轮只修复此已定位的索引解析问题，并在环境说明中明确 `python3.12-venv` 前置条件。保持 48 个 Linux 包的版本及全部 wheel hashes、Mac 锁、模型/训练协议不变；不要升级 pip 以绕开现象。优先最小而可复现的锁内索引或安装参数修正；记录锁生成命令/后处理（如适用），不假称未执行的 uv 输出。若实现会改锁哈希，明确交接新值。

允许修改 `requirements/cuda-linux-py312.lock.txt`、其直接生成说明、`scripts/colab/remote.py` 中直接相关安装参数、直接相关 `tests/colab`、`docs/18_CUDA_RUNTIME.md`；新增 `reports/experiments/P04_COLAB_ENVIRONMENT_R4.md` 与 `coordination/handoffs/P04-colab-environment-r4.md`。生产训练、数组、其他配置、共享状态和旧报告不改。

以最小真实 pip 解析/小型离线安装检查区分“命令行 CUDA 源被覆盖”与“解析后两源同时存在”。先保留旧失败，再验证修正；不下载 CUDA wheels 到 Mac，不重复进程清理或模型数值测试。共享环境/现有系统 pip 可读；确需 pip 24.0 解析器时只允许下载其小型纯 Python wheel 到私有目录供 CPU 检查，不变更共享环境。每命令≤300秒、2线程、新增≤200MiB。GPU、SSH、模型、真实数据、新编码均0。

交精确实现/候选提交、实际检查与新锁哈希；R1独立增量审查。S1 后续以修正的精确源码/锁在新 Colab 实例验收真实安装，再进行容量与恢复。本次是新安装索引问题，不能把 r4 包名当作同一问题第4次正式失败。
