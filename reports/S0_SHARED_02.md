# S0-SHARED-02 自查与来源证据

日期：2026-09-06；base `97466a20f599f68c511b9c8a71fe5f2cdfd9ad4b`；branch `work/shared-backend-packaging`；结论：**自查通过，待独立 R1**。

本包加入可选备选依赖与 P01 首选失败重放环境，并修复 App worktree 的源码包选择边界。生产冻结契约、runtime 与 T1/D1 实现均未修改。具体职责和复现命令见 [环境/源码包说明](../docs/15_P01_ENVIRONMENT_AND_SOURCE_PACKAGES.md)。

## 实际安装与解析

S0 实际安装 compatibility+dpo 为 69 个 distributions，增加 p01-replay 后为 90 个；默认 CPU 环境为 12 个。两个环境的模型/数据/运行依赖版本均与 T1 已测清单一致，项目 editable 与 dev-only Ruff 0.15.0 单列。固定 uv.lock 的 93 个记录包含跨 Python 分支，不等于实际安装 93 个包。

没有导入 ML 后端或加载模型；metadata/pip check 成功不能证明训练。macOS arm64/3.14 解析完整重放组为 90 个；Linux x86_64 与 Intel macOS 各 13 个，只有 CPU 开发包与 psutil，没有 ML/CUDA。后两项是 dry-run，并非实机安装。默认 11 个第三方 CPU 分发记录逐条不变；可选 fsspec 从原 2026.7.0 改为实测 2025.3.0，numpy/scipy 的跨 Python 解析标记如实保留。

初次未 pin datasets 解出了 5.0.1 及对应较新依赖，未采纳。固定实际 3.6.0 后闭包与 T1 对齐。第一次环境对比脚本误要求 T1 模型环境包含项目 dev-only Ruff，断言失败；分离已批准 CPU linter 后确认运行依赖版本一致，原失败说明保留，未改依赖来隐藏失败。

## 固定版来源与许可

| PyPI JSON | metadata 字节 SHA-256 |
|---|---|
| [mlx-lm-lora-3.1.2](https://pypi.org/pypi/mlx-lm-lora/3.1.2/json) | `bf0b0664aed3da17be9ad7ac1a784d53709d5de6d6b1083123899d41d6de2056` |
| [datasets-3.6.0](https://pypi.org/pypi/datasets/3.6.0/json) | `4965e8aa815a8f1c8f05d35726a6d7787bcd94edcc56e0016c2b406341b61827` |
| [mlx-tune-0.6.0](https://pypi.org/pypi/mlx-tune/0.6.0/json) | `5c253c203318b6486127252a5bfedb0dfec9f61d53cc4937be5aa58dc5057f0d` |

新增直接锁定制品均与固定 PyPI metadata 的 URL/size/SHA 对照。mlx-lm-lora wheel SHA 为 `4cf4f4f965d24df7ec0734426631c2e314231ae3bd115113c26e12d455881f2a`，mlx-tune wheel 为 `920e7e14eaaef01efa0b3118152b405b3b67a9d5a3a5957a4fd9b9ecf6a0e4da`。

| 包 | metadata 许可 | 实装 wheel LICENSE / SHA-256 |
|---|---|---|
| mlx-tune 0.6.0 | Apache-2.0 | Apache License 2.0；`f45b671981baeeb94b5a5e2142d1df171c707035c7f05a99f83d63c77f3610f0` |
| datasets 3.6.0 | Apache 2.0 | Apache License 2.0；`cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |
| mlx-lm-lora 3.1.2 | MIT | Apache License 2.0；`c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`；**两处声明不一致** |

保留不一致，不替上游推定统一许可，不将依赖实现复制进本项目 MIT 源码包。P09 若分发依赖制品须复核差异并保留上游许可证。

## 源码包问题的独立复现

T1 报告其真实 App worktree 默认选择会包含私有文件。S0 以相同 Hatchling 1.27.0 对该目录只读枚举：29,256 个文件、7,128,425,751 bytes，其中 29,129 个为私有目录文件。数量随 T1 新增日志变化；该快照不与 T1 早一时刻的计数强行等同。S0 未对真实私有输入生成源码包；T1 原构建已停止，无完成的该类发行包或上传。

S0 读取固定版 `BuilderConfig.load_vcs_exclusion_patterns` 并检查实际 config，确认 ignore_vcs=False、已找到 .gitignore，但绝对项目根匹配 `.codex/` 时返回空 VCS 规则。合成 App 路径构建独立复现相同行为：旧 pyproject 的实际 tar 含 `.toolalign-local` 模拟源数据/权重、data/raw、models 和未列名根文件；显式 only-include 后全排除，tar 可重建 wheel。

最初测试中的静态 canary 也出现在测试脚本源码，产生无效失败；已改为每次运行随机后缀，保留原日志。其后普通临时 worktree 只漏未列名根文件，.gitignore 对模拟私有目录有效；这使 S0 将触发条件继续定位到 `.codex` 祖先目录，避免错误归因于 .git 是文件。有效的最终测试使用 `.codex/worktrees` 下的真实 worktree，未修改断言掩盖缺陷。

| 源码包测试 | 退出码 | 原始日志 SHA-256 |
|---|---:|---|
| 旧配置，App 布局真实合成归档 | 1 | `0562094e21b971e09e1881ea151de1e3c310b62aefd609ca5819c87b250ccb25` |
| 显式边界，相同 App 布局 | 0 | `9ff114bccb481d6af684a9857c3759a65112a9f3d0d90dc30eef212b8c73e413` |

新脚本进入 CPU CI，实际检查内容而非只读配置文字；源码包保留公开代码、测试、配置和验证入口，包含完整冻结 schema。旧历史审查中绑定“恰一个 extra”的快照未改写，不宣称这些旧包结构断言适用于当前新增组。

## 当前候选自查

| 命令 | 退出码 | 日志 SHA-256 |
|---|---:|---|
| `uv sync --locked --python 3.14` | 0 | `c1eb46aab57925fbaef75de85964c75d5d8bb98e98d5545c9fbf68c22c9fc957` |
| `uv run --locked pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py` | 0 | `a476fc1e8cf9e1f3503a873dcce6c18201a07d79f9ad31147f9899757e232a7c` |
| `uv run --locked ruff check .` | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `uv run --locked python scripts/check_contract_freeze.py` | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| `uv run --locked python scripts/check_source_distribution.py` | 0 | `dcf15f1de5ea1709f332e3824fe69269e843dd1c6c144268c418d4ea8f06e551` |
| `uv build` | 0 | `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75` |
| `uv run --locked python reports/review/P00/verify_wheel.py` | 0 | `5d8d9f1957838b359448cd6d162bd1eee1bc1291da00ea12645a1c8ba303285e` |
| `uv sync --locked --python 3.14 --extra compatibility --extra dpo --extra p01-replay --dry-run` | 0 | `c614dac8eaec6d6b1f24dfa8599af1a3ca47a1ea31325942f2f22784c4e0ee97` |
| `uv sync --locked --python 3.14 --extra compatibility --extra dpo --extra p01-replay --dry-run --python-platform x86_64-unknown-linux-gnu` | 0 | `5c4068ea8cf9e07b483c01943a7ee249cd804fcf04fef15bc6d4f28438ffbe39` |
| `uv sync --locked --python 3.14 --extra compatibility --extra dpo --extra p01-replay --dry-run --python-platform x86_64-apple-darwin` | 0 | `ee7cbc772b31168ea91ddd0d5ece2feab077aa210eb07305e0333531f483a2b5` |
| `uv pip check --python <private-replay-python>` | 0 | `06b5b5c69db249ba1ec22eb0d48b7262a24b1ab75101c1768291d577c0635f20` |

CPU 回归实际为 176 项（基础 58、P00 第一轮 46、P00-r2 72），全部通过；源码包回归、lint、冻结、真实构建与独立临时 wheel 安装也通过。没有把旧可选包结构快照算作新增候选通过。原始命令与日志保存在私有 `.toolalign-local/evidence/shared-dpo-support/`。

**NOT_RUN**：本候选环境的模型/数学/吞吐重放、R1 独立复核、最终 CI/main 验证、P01 本包验收、D1 真实适配验收/人工质量门、P03 执行器和 P04/P05 正式训练。
