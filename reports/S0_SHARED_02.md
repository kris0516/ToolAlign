# S0-SHARED-02 自查与来源证据

日期：2026-09-06；base `97466a20f599f68c511b9c8a71fe5f2cdfd9ad4b`；branch `work/shared-backend-packaging`；结论：**两轮独立审查分别发现目录内部及大小写 P1；最新大小写修订已自查，待精确新 SHA 复审**。

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

S0 读取固定版 `BuilderConfig.load_vcs_exclusion_patterns` 并检查实际 config，确认 ignore_vcs=False、已找到 .gitignore，但绝对项目根匹配 `.codex/` 时返回空 VCS 规则。合成 App 路径构建独立复现相同行为：旧 pyproject 的实际 tar 含 `.toolalign-local` 模拟源数据/权重、data/raw、models 和未列名根文件；首轮显式 only-include 排除了这些已测试探针，tar 可重建 wheel。该首轮测试未覆盖允许目录内部的密钥、权重等忽略文件，不能证明完整打包边界已修复。

最初测试中的静态 canary 也出现在测试脚本源码，产生无效失败；已改为每次运行随机后缀，保留原日志。其后普通临时 worktree 只漏未列名根文件，.gitignore 对模拟私有目录有效；这使 S0 将触发条件继续定位到 `.codex` 祖先目录，避免错误归因于 .git 是文件。有效的最终测试使用 `.codex/worktrees` 下的真实 worktree，未修改断言掩盖缺陷。

| 源码包测试 | 退出码 | 原始日志 SHA-256 |
|---|---:|---|
| 旧配置，App 布局真实合成归档 | 1 | `0562094e21b971e09e1881ea151de1e3c310b62aefd609ca5819c87b250ccb25` |
| 显式边界，相同 App 布局 | 0 | `9ff114bccb481d6af684a9857c3759a65112a9f3d0d90dc30eef212b8c73e413` |

新脚本进入 CPU CI，实际检查内容而非只读配置文字；源码包保留公开代码、测试、配置和验证入口，包含完整冻结 schema。旧历史审查中绑定“恰一个 extra”的快照未改写，不宣称这些旧包结构断言适用于当前新增组。

## 首轮候选自查（55a330b）

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

首轮 GitHub CPU CI run 33999550982 成功，但 R1 的独立嵌套文件探针仍失败，绿色 CI 不覆盖这个漏测场景，不能据此合并。

## R1 发现后的修订

R1 对精确 `55a330b6a1c10d14959895f2a3617597962569f3` 复现 configs 下的 key/pem、tests 下的 safetensors 与 src 下的 pt 合成文件进入真实 sdist，且同一工作区的公开扫描仍通过。问题在于目录级 only-include 仍允许其内部文件，Hatchling 此时已丢弃 VCS 排除。

S0 保留原候选和失败证据，增加公共 Hatch build 显式排除，使源码包和直接 wheel 都排除密钥、模型、日志、私有映射、环境及运行目录。回归扩展至 85 个探针，分别检查 sdist、从 sdist 重建的 wheel、直接工作区 wheel 的实际字节。没有新增依赖或改动 ML 路径。

| 修订检查 | 退出码 | 原始日志 SHA-256 |
|---|---:|---|
| 原 55a330b 配置，扩展至 85 个探针 | 1 | `d3bdddbac552972efdee4aeb76c14f2b8762e12befb79decce6900daa34a9694` |
| 公共显式排除，实际三种归档检查 | 0 | `7207c38ecb12827ab40e7034dfb327d8e83e12d0ee9516911d862542cb2622a4` |
| Ruff | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| 冻结契约 | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| 176 项 CPU 回归（命令同首轮） | 0 | `e380866f7acd8bd8b213fd774c1ba26bb73230482de1e794e26214f2716b968d` |
| `uv build` | 0 | `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75` |
| 隔离 wheel 安装/契约验证 | 0 | `5d8d9f1957838b359448cd6d162bd1eee1bc1291da00ea12645a1c8ba303285e` |
| 公开内容扫描 | 0 | `4721869e33fb716057a896a0ae81b98aee85e2b492d8c38819f293d76214cb4e` |
| 原始 R1 `probe_sdist.py app-new-nested` 在修订配置重跑 | 0 | `6f3a88156e4464f47abbf306ef4920cd3630bbff44a4a303aca8543b97d874be` |

R1 首轮正式 FAIL 提交 `cfbc1529e9bc946c42a26a0070528217ab8eafff` 已通过非强制 merge 保留原 SHA；修订实现提交 `c175bc7`，随后同步了已发布 main `9d1cdfd` 的任务登记文档。S0 重跑原始 R1 探针时仍确认 Hatchling VCS 规则数为 0，但四个嵌套探针均被显式规则排除。此为 S0 复验，独立 R1 复审仍待完成。

D1 后来在旧基线构建出一次失败私有归档，107,953,843 bytes，6,792 个成员中 6,651 个为私有成员；已隔离为仅私有证据且没有上传。该事实更新了早先 T1/S0 未完成私有归档的时间快照，不删除早期失败记录，也不对 D1 的真实私有输入重复运行有缺陷打包。

## R1-r2 大小写发现后的修订

R1 对第二个精确候选 `81489292c7ba54875c7de1f156bd1696fe4ed0a7` 复验首轮小写反例已关闭，但本机 Git 自动检测 `core.ignorecase=true`，Hatch 的显式普通 glob 区分大小写。其独立 21 个大写/混合大小写合成文件仍被 Git 忽略，实际 sdist 泄入全部 21 个，直接与重建 wheel 各泄入 src 内 7 个；公开扫描仍通过。R1 原始日志 SHA-256 为 `2c0db872a93c150e42c38c8b1177c75992fa95a0162416d69aab85b34bbd3ac7`。第二候选 CI run 34000642796 的 Python 3.11/3.14 均成功，但尚未覆盖该反例，不能合并。

S0 将每个排除规则的 ASCII 字母展开为大小写字符类，覆盖相同类别的任意大小写组合，并保留 `.env.example` 公开例外。未改变实际 Git/系统配置、依赖或 ML 代码。公共回归在临时合成仓库设置该 Git 条件，241 个私有探针中 240 个先由 `git check-ignore` 核验，另 1 个未列名根文件由 only-include 排除；大小写变体使用独立父目录，避免在 Mac 上互相覆盖。另有 18 个正常公开对照，包括三种大小写 `.env.example`；实际 sdist、直接 wheel、重建 wheel 均检查内容，冻结 schema 保留。

| 大小写修订检查 | 退出码 | 原始日志 SHA-256 |
|---|---:|---|
| 原 8148929 配置，241 个探针的真实 sdist 泄漏断言 | 1 | `2228aafdf7d1534603a65680b6dc524d7e748f556b4fd08c241ece4f06a7226e` |
| 修订后三种归档，241 私有探针排除且 18 公开对照保留 | 0 | `59ef6b0077bfa3cec9beb83d95b7321bb5369d0f95d93e956780fd7fafbf1c98` |
| Ruff | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| 冻结契约 | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |

以上是 S0 自查。依赖/许可保持首轮 R1 审查字节，176 项 CPU 最近在第二候选由 S0 和 R1 均通过；本次修订只涉及打包选择和归档回归。未把历史测试或第三方声明改为当前正式模型验收。

**NOT_RUN**：本候选环境的模型/数学/吞吐重放、最新大小写修订候选的 R1 复审/最终 CI/main 验证、P01 本包验收、D1 人工质量门、P03 验收和 P04/P05 正式训练。
