# S0-SHARED-02：R1 独立审查证据

日期：2026-09-06；结论 **FAIL（P1 × 1）**。审查对象固定为 `55a330b6a1c10d14959895f2a3617597962569f3`，base 为 `97466a20f599f68c511b9c8a71fe5f2cdfd9ad4b`；审查分支 `review/shared-02-r1`。

正式判定见 [handoff](../../../coordination/handoffs/S0-SHARED-02-review-r1.md)。[evidence.json](evidence.json) 保存逐命令退出码和完整原始日志 SHA-256；原始日志、真实参数路径和任务身份私有保存，不提交到公开仓库。JSON 中的路径占位符仅用于说明，实际命令不是直接复制占位符执行。

## 阻断复现

在精确候选检出后运行：

```bash
uv run --locked --with hatchling==1.27.0 python reports/review/S0-SHARED-02/probe_sdist.py app-new-nested
```

候选实际退出 **1**，原因是四个被 `git check-ignore` 命中的随机合成文件仍全部进入真实 sdist：

```text
configs/synthetic.key
configs/synthetic.pem
src/toolalign/synthetic.pt
tests/synthetic.safetensors
```

同一 fixture 的 `scripts/check_public_content.py` 退出 0；Hatchling 的 VCS 忽略规则数量为 0。首次复现归档为 41 个文件、86,695 bytes。这里记录的是实际归档内容检查，不是配置文本推断。归档由微型合成 worktree 生成并在退出时清理；没有枚举或复制任何真实私有目录。

| 独立场景 | 实际行为 | 判定 |
|---|---|---|
| `plain-old` | 普通路径真实 worktree，39 条 VCS 规则；仅未列名根文件进入旧包 | 对照成立，退出 0 |
| `app-old` | `.codex` 祖先目录下规则为 0；旧包收入四类合成私有文件，内置 `.venv` 排除仍生效 | 修正对照后退出 0，确认旧缺陷 |
| `app-new` | 新配置排除根级合成私有文件；37 文件归档可重建 wheel，冻结 schema 相同 | 退出 0 |
| `app-new-nested` | 新配置仍收入四个目录内忽略文件，公开扫描同时通过 | **退出 1，P1** |
| 候选自带 `check_source_distribution.py` | 根级及字节码 canary 均排除 | 退出 0，但覆盖不到上行 |

`plain-old`、`app-old`、`app-new` 使用相同入口替换末尾场景参数即可重放。旧配置仅写入临时合成 fixture；R1 不修改当前候选。探针通过真正的 `git worktree add` 创建 `.git` 为文件的目录，并读取固定 Hatchling 1.27.0 的实际配置。既有公开文件保留，不使用真实权重、日志、环境或数据。随机标记仅在运行时生成，避免静态 canary 出现在源码中造成误报。

建议 S0 在 `pyproject.toml:43–57` 修正整个递归目录的公开选择边界，并为配置、测试和源码目录中的忽略文件增加实际归档负例。R1 的失败断言保留原意，没有把泄入改为可接受结果。

## 其他独立结果

本机为 macOS 26.5.1 / arm64、CPython 3.14.7。原生构建/CPU 检查和只读安装元数据可验证本包环境配置，不能证明模型或训练可用。

| 检查 | 实际结果 |
|---|---|
| 默认 `uv sync --locked --python 3.14` | 退出 0，12 个 distributions，无 ML 后端 |
| 基础测试 + P00 + P00-r2 回归 | 176 passed，退出 0；不包含旧 S0-SHARED-01 的精确 extra 快照 |
| 候选 lint / freeze / public scan | 全部退出 0；初次公开扫描 112 个路径 |
| 最终审查文件 lint / public scan | 退出 0；公开扫描包含 index 与 working tree 的 118 个路径 |
| `uv build` | 退出 0，wheel 从 sdist 构建 |
| P00 `verify_wheel.py` | 临时隔离安装、依赖 check、五类 CLI fixture、schema/no-source/no-ML 全通过 |
| `verify_dependencies.py` | 11 个 CPU 锁记录逐项不变；新锁 93 条；CPU/dev/compatibility/build pins 不变；只读实际依赖闭包通过 |
| 可选环境 metadata | compatibility+dpo 为 69 包；完整 replay 为 90 包，与独立 locked export 完全一致 |
| T1 清单对照 | 固定 T1 提交的 88 项清单与 replay 除项目/Ruff 后完全相等，dpo 子集对应版本相等 |
| 三平台 locked export / dry-run | 原生 Darwin arm64 完整 replay 90 包，Linux x86_64 / Intel macOS 各 13 包，无 ML/CUDA |
| wheel METADATA | 三个 extra 均保留，新增 ML 根仅在 extra 激活且 Darwin arm64 时生效 |
| 上游直接制品与许可 | 三份新取 PyPI JSON、锁内 URL/size/hash、三个下载 wheel 的 hash 与 LICENSE、实装 LICENSE 字节一致 |
| S0 原始证据 | 11 项最终命令日志、历史合成构建前后及无效初测的字节 hash 与索引一致 |

依赖检查命令（两个私有路径由 S0 提供，以 R1 的 CPU Python 仅读取 dist-info）：

```text
uv run --locked python reports/review/S0-SHARED-02/verify_dependencies.py --dpo-site-packages <private-dpo-site-packages> --replay-site-packages <private-replay-site-packages>
uv run --locked python reports/review/S0-SHARED-02/verify_artifacts.py --replay-site-packages <private-replay-site-packages> --evidence-dir <private-review-upstream>
```

两个脚本都不导入 ML 库、不运行被查环境的 Python。许可证检查只下载三个小型公开库 wheel，不安装它们或获取模型/数据。锁内 fsspec 从 2026.7.0 变为 2025.3.0，与显式固定 datasets 3.6.0 和 T1 清单一致；不是 CPU 环境漂移。numpy/scipy 的跨 Python 记录也保留，93 个锁记录不等于实际装了 93 个包。p01-replay 仅为失败首选和跨库审计提供依赖。

正常公开输入构建产物摘要：

| 产物 | bytes | SHA-256 |
|---|---:|---|
| `toolalign-0.0.1.tar.gz` | 86,336 | `92ea9c70f1f96a7e02600a37738c7bd78b30311b9abb16678241ce6588cef913` |
| `toolalign-0.0.1-py3-none-any.whl` | 18,422 | `8eaf706a2d3f24bb7d902f8ccda453a28431bc0783a02c882588b38848033ec2` |
| 冻结 `toolalign/contracts/v1.json` | — | `ce17b0a5bc4e8363e1d67bf125212444bab1103ddfc0c4e390bef82afce881cb` |

## 固定版上游许可证据

| 包及 PyPI JSON 来源 | wheel SHA-256 | 实际 LICENSE SHA-256 |
|---|---|---|
| [mlx-lm-lora 3.1.2](https://pypi.org/pypi/mlx-lm-lora/3.1.2/json) | `4cf4f4f965d24df7ec0734426631c2e314231ae3bd115113c26e12d455881f2a` | `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4` |
| [mlx-tune 0.6.0](https://pypi.org/pypi/mlx-tune/0.6.0/json) | `920e7e14eaaef01efa0b3118152b405b3b67a9d5a3a5957a4fd9b9ecf6a0e4da` | `f45b671981baeeb94b5a5e2142d1df171c707035c7f05a99f83d63c77f3610f0` |
| [datasets 3.6.0](https://pypi.org/pypi/datasets/3.6.0/json) | `25000c4a2c0873a710df127d08a202a06eab7bf42441a6bc278b499c2f72cd1b` | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |

三份独立获取的 JSON hash 均与 S0 报告相同，完整值记录于 `artifacts` 原始日志。mlx-lm-lora metadata 写 MIT，实装和独立下载 wheel 的 LICENSE 均写 Apache License 2.0；另外两包两处均声明 Apache 2.0。该不一致不替上游作许可裁决，也不将库实现重新标为本仓库 MIT。

## 保留的失败与历史补充

- R1 首次 `app-old` 对照退出 1，因为审查脚本错误地预期 `.venv` 也会泄入；实际存在 Hatchling 内置排除。仅修正该旧配置对照预期并重跑通过。初版探针私有副本 SHA-256 为 `56ba81bd903264600bdaff4544f65d9d47a9ccfbfe0ba1533ffb0c3e831d0d58`。原失败日志保留，当前候选负例仍失败。
- R1 额外显式指定通用 `aarch64-apple-darwin` 时，uv 默认采用 macOS 13 目标，MLX 0.32.2 无对应 wheel，退出 2。原生 macOS 26.5.1 的相同 extras dry-run 通过；没有声称支持 macOS 13，也没有改依赖来使该额外目标变绿。
- S0 的初始静态 canary 失败是测试器误报；之后普通路径只漏未列名根文件，再以 App 布局实际定位 VCS 规则丢失。原失败/修正日志已逐份核 hash。T1 实际目录的 S0 只读枚举报告为 29,256 文件、7,128,425,751 bytes、29,129 私有文件；该动态快照是 S0 来源证据，不是 R1 重新枚举或构建。
- S0 初次环境对照把 dev-only Ruff 错计入 T1 模型清单，失败记录保留。R1 独立排除项目/Ruff 后核对完整 88 项，未忽略其他运行依赖差异。
- D1 审查期间补交旧构建事件。R1 只读 audit JSON 的 SHA-256 为 `d8e89a7909333ab9d14374468861671739d46360702f16fced78ee762527c372`。其中记录旧归档 107,953,843 bytes、6,792 成员／6,651 私有成员、`uploaded=false`，记录的归档 SHA-256 为 `5154c83cbf57482ecab0375dbc064edaf195bb9d47f73a24d2a0d1088cca5026`。归档本体检查 **NOT_RUN**，该 hash 未通过读取归档独立计算。D1 转交的解包失败日志 hash `80f8d5204516e15a775f58318f1babc7abe4475c447f8b9e06ae995b44160433` 也仅作为来源声明，R1 未读取该日志或解包。该事件应由 S0 在后续状态记录补充。

没有将上述测试器错误、未承诺支持的目标或历史来源差异计为第二个产品缺陷。P1 依据是本轮独立实际归档负例。

## NOT_RUN 与改动边界

R1 全套 ML extras 自建安装、模型/张量/ML 导入、数学/吞吐/训练/GPU、P01 全包、D1 适配质量与私有归档内容、跨平台实机运行、最终 GitHub CI 和 main 集成均为 **NOT_RUN**。本报告不批准模型后端或下游训练。

R1 只新增本目录的说明、三个小脚本与摘要索引，以及指定的 handoff；旧 S0-SHARED-01 探针保持其原候选含义，不修改旧 PASS 或生产实现。日志中的非零退出全部保留在索引，不以“全绿”概括本轮。最终只提交审查文件，由 S0 决定修复与再次派发。
