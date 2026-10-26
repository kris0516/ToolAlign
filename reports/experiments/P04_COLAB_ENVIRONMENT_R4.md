# P04 Colab 安装索引修复 r4

2026-10-26，E1，**READY_FOR_REVIEW**。pip 24.0 的真实解析复现表明，旧锁会删除命令行提供的 CUDA 索引；在锁中明确声明两个源后，解析完整 48 个包仍保留 PyPI 和 CUDA 源。最终 **4 passed，0 skipped**，待 R1 增量复审及 S1 的新实例安装验收。

基点 `920c41551f0f7f2be8a5a8dcced23cc080ac1f27`；授权 `b1a1af1c059f1d0fd6e8db36b42cfe2d4c55dd1d`；实现提交 **`2ecb7a8b1ca73386f68d79d34896a3aedeb2658e`**。r4 是本轮包名，不表示同一问题的第四次正式失败。

## 修正与锁身份

S1 的第二次真实 setup 使用 pip 24.0，最终报 `torch==2.8.0+cu128` 无匹配版本；直接查询 CUDA 索引则包含该版本。其实际 `handle_option_line()` 在处理锁内 `--index-url` 时替换整个索引列表。E1 使用官方 pip 24.0 wheel 核对，函数内容与 Colab 诊断一致，仅日志多一个末尾换行。

本轮在 Linux 锁的 PyPI 声明后增加 `--extra-index-url https://download.pytorch.org/whl/cu128`，并在头部及[生成说明](../../docs/18_CUDA_RUNTIME.md)明确这一步后处理。**未重新运行 uv 解析**；原始生成命令保留，整个包定义部分逐字不变，包含 48 个固定版本及 894 条 SHA-256 声明。Mac 锁逐字不变。现有 setup 安装参数保持原样。

| Linux 锁 | SHA-256 |
|---|---|
| 基点 | `14e8724b9d78e7bcabc270aa2c0cfe05ea5a5d855fffda08dad7aa0a93c20fb4` |
| 修正后 | **`6a793bfd46af168b2df581f19ce8f23f97af239a12ac95b436e99baff080b2ea`** |

S1 后续运行配置须绑定新锁哈希。运行文档同时补入 Ubuntu 的 `python3.12-venv` 前置包，以提供创建专用环境所需的 ensurepip；本轮不安装系统包或升级 pip。

## 实际检查

只下载[官方 pip 24.0 纯 Python wheel 元数据](https://pypi.org/pypi/pip/24.0/json)指定的 `pip-24.0-py3-none-any.whl`，大小 2,110,226 字节，SHA-256 `ba0d021a166865d2265246961bec0152ff124de910c5cc39f1156ce3fa7c69dc`。通过私有 `PYTHONPATH` 加载该 wheel，复用 S1 的 Python 3.12.14 CPU 环境，不安装到共享环境。测试调用真实 pip 解析器，不执行依赖解析器、包下载或安装。

| 私有命令 | 检查 | 结果 |
|---|---|---|
| 003 | 旧锁：现有 setup 参数及去掉 CLI extra index 两种入口 | **2 failed，1.13s**；完整解析 48 个包后均只剩 PyPI；前者解析前确有两个源 |
| 004 | 加入锁内 CUDA 源后的初次回归 | 两个索引断言均通过；**2 failed / 2 passed**，新测试的 torch 原文比较未考虑 pip 保留的续行空格 |
| 006 | 原锁/新锁的包定义字节及实际解析结果核对 | **PASS**；48 个 pins、894 条 hashes、Mac 锁保持，pip handler 与实际 Colab 内容一致 |
| 007 | 修正测试的无意义尾部空格比较后，重跑两种解析入口及原安装计划/Mac 拒绝安装检查 | **4 passed，0 skipped，1.00s**；保留 1 条上游 `pkg_resources` DeprecationWarning |
| 008 | `ruff check tests/colab/test_install_indexes.py` | **PASS** |

004 的原始 requirement 为 `'torch==2.8.0+cu128    '`，按 PEP 508 解析的名称与版本均正确；测试改用去除首尾空格后的相同精确版本比较，索引断言未改变。原失败和 S1 两次 setup 的历史记录保留。JUnit 记录了实际 pip 版本、模块位置、前后索引及 48 个解析条目；007、008 的文件字节与实现提交匹配。

新增解析测试需要可用的 pip 模块；未提供时会明确跳过。本轮通过上述官方 wheel 执行，实际零跳过。完整 argv、环境、开始结束时间、输出和绑定核对保存在私有回执中，每条命令不超过 300 秒，OMP/MKL 各 2 线程。

本轮 GPU、SSH、CUDA wheel/模型下载、真实数据、训练、新环境及共享依赖安装均为 0，没有重跑进程清理或模型数值测试。解析验收不替代真实 Linux 安装；S1 在新实例上以精确源码和新锁完成后续验收。
