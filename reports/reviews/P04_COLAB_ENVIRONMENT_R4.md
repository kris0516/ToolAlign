# P04 Colab pip 索引修复：R1 增量复核

**PASS：P0=0、P1=0、P2=0。建议关闭 `P04-COLAB-INDEX-001`。** 同一真实 pip 24.0 解析探针在旧锁上丢失 CUDA 源，在修订锁上保留 PyPI 与 CUDA 两源；48 个包及 894 条 SHA-256 声明保持不变。真实 Linux 完整安装与 CUDA 结果仍由 S1 后续验收。

2026-10-26，独立 R1，gpt-6-astra/max。授权 **`e88982217ea7ccbfb9567a19eed4f64bb0f019be`**；最终 reviewed candidate **`99b8116ad985c999f3cf4fb3c918eeadf50f8814`**，实现 **`2ecb7a8b1ca73386f68d79d34896a3aedeb2658e`**，基线 **`920c41551f0f7f2be8a5a8dcced23cc080ac1f27`**。R1 在实现提交上执行修后检查；最终候选只新增 E1 报告与交接，源码、锁及测试未变，检查结果沿用。

## 已复现的原因与修正

S1 两次真实 run 均止于 setup。第一次因缺少配套 `python3.12-venv` 而无法运行 ensurepip；补齐系统包后 ensurepip 成功提供 pip 24.0。第二次安装报 `torch==2.8.0+cu128` 无匹配版本，但当次直接查询 CUDA 源能找到该版本。实际 `handle_option_line()` 在读取 requirements 内的 `--index-url` 时替换整个索引列表，删除了此前由 CLI 加入的 extra index。

R1 核对了这组失败、修复、诊断和停止的 6 份原命令回执；相关生产文件与基线字节一致。两次 run 的 8 个 Mac 回收文件、2 个 tar 及 manifest/摘要绑定均通过，停止回执确认当次实例已不存在。R1 没有重新连接或分配实例。

实现只在 [Linux 锁](../../requirements/cuda-linux-py312.lock.txt) 的 PyPI 主源后增加 CUDA extra index，并更新头部和[生成说明](../../docs/18_CUDA_RUNTIME.md)，明确这是原 uv 输出之后的后处理。没有重新运行 uv，也没有升级 pip 或改动安装参数。文档补入 Ubuntu 的 `python3.12-venv` 前置条件；系统包仍由运行前置准备处理。

## 独立解析与锁身份

R1 从私有 `pip-24.0-py3-none-any.whl` 直接导入解析器，不安装到共享环境。wheel 为 2,110,226 字节，SHA-256 `ba0d021a166865d2265246961bec0152ff124de910c5cc39f1156ce3fa7c69dc`，与 E1 保存的官方下载记录一致；函数源码与 S1 现场诊断的打印输出一致。

独立 `parser_probe.py` 使用当前 `remote.setup_commands()` 生成的实际安装参数，调用真实 pip command parser、PackageFinder 和 `parse_requirements()` 解析完整锁。修前、修后使用同一探针；禁止网络请求且实际请求数均为 0。

| R1 实际观察 | 解析前索引 | 解析完整锁后 |
|---|---|---|
| 基线，实际 setup 参数 | PyPI、CUDA | 仅 PyPI；两源断言失败 |
| 实现，实际 setup 参数 | PyPI、CUDA | PyPI、CUDA；通过 |
| 新回归的 lock-only 入口 | PyPI | PyPI、CUDA；通过 |

修前与修后的 48 个 requirement 及其全部解析 hash 集合完全相同；锁文件整个包定义正文也逐字相同，包含 894 条 SHA-256 声明。`--require-hashes`、`--only-binary=:all:` 保持有效。R1 另外执行新增两项参数化回归，**2 passed / 0 skipped**，JUnit 记录实际 pip 24.0、模块位置、两源及 48 个解析条目；保留 1 条上游 `pkg_resources` 弃用警告。

| 锁身份 | SHA-256 |
|---|---|
| 原 Linux 锁 | `14e8724b9d78e7bcabc270aa2c0cfe05ea5a5d855fffda08dad7aa0a93c20fb4` |
| 新 Linux 锁 | **`6a793bfd46af168b2df581f19ce8f23f97af239a12ac95b436e99baff080b2ea`** |

Mac 锁、全部 `src`、`scripts/colab` 和配置均未变。原清理、恢复、数值和数据结论沿用，本轮未重复运行这些检查。S1 后续运行须绑定新锁哈希与精确源码。

## 原始记录与验收边界

R1 核对 E1 16 份原命令回执及 JUnit：旧锁 003 为 2 failed；中间 004 的索引已正确，但两项 Torch requirement 原文比较未考虑 pip 保留的尾部空格，结果为 2 failed / 2 passed。测试修订只将该 requirement 去除首尾空格，索引断言不变；007 的最终源码绑定通过，实际 **4 passed / 0 skipped**，另两项是原安装计划及 Mac 拒绝安装检查。008 lint 通过。原失败均保留。

本轮使用既有 Python 3.12.14，OMP/MKL 各 2 线程、离线环境和本 worktree 的源码；pytest 使用新建独占 basetemp，单命令上限 300 秒。`R1_PRIVATE` 指本轮私有目录，时间为原回执的 wall time。

| 命令记录 | 检查 | 退出码与结果 |
|---|---|---|
| baseline-parser | `PY312 -B R1_PRIVATE/parser_probe.py baseline` | 1；原两源断言失败，1.05 秒 |
| candidate-parser | 同一探针，参数 `candidate` | 0；两源、48 包及原 hash 约束通过，0.99 秒 |
| index-regressions | `PY312 -B R1_PRIVATE/run_index_tests.py` | 0；2 passed / 0 skipped，1.12 秒 |
| s1-evidence-audit | S1 原始证据核对 | 1；辅助源码比较遗漏 `print` 添加的末尾换行，0.94 秒 |
| s1-evidence-audit-corrected | 精确计入该一个换行后核对 | 0；6 回执、8 文件、2 归档及停止记录通过，0.94 秒 |
| author-evidence-audit | 最终候选、作者回执及 JUnit 绑定 | 0；16 回执与实现绑定通过，0.32 秒 |

辅助比较的初始脚本及失败输出保留；差异仅为打印结果多出的一个换行，不改变 pip 解析逻辑或本轮裁定。R1 只新增本报告、交接及私有复核材料，未修改实现、测试、锁或共享状态。GPU、SSH、CUDA wheels/模型下载、真实数据、新编码、新环境及共享依赖安装均为 0。

本报告是 INDEX-001 对精确修订候选的一次独立正式结论；基线复现失败不另计正式修订轮次，r4 包名也不表示第四次同问题失败。S1 接收后维护问题计数，并完成新实例上的真实 Linux 安装验收。
