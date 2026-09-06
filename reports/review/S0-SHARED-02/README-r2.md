# S0-SHARED-02：R1 复审 r2 证据

日期：2026-09-06；精确候选 `81489292c7ba54875c7de1f156bd1696fe4ed0a7`；分支 `review/shared-02-r2`；结论 **FAIL（P1 × 1）**。正式判定见 [r2 handoff](../../../coordination/handoffs/S0-SHARED-02-review-r2.md)。首轮 [FAIL 报告](README.md)、[证据索引](evidence.json) 和探针保持原文，未覆盖。

## 本机大小写反例

```bash
uv run --locked --with hatchling==1.27.0 python reports/review/S0-SHARED-02/probe_case_boundaries_r2.py case-variants
```

在本机 macOS 26.5.1 / arm64、Python 3.14.7 上，实际退出 **1**。Git 在临时仓库自动检测 `core.ignorecase=true`；探针只读取该值，未强行设为 true，也未修改全局 Git 配置。此探针明确要求该本机文件系统条件；不能把它在大小写敏感文件系统上的前置条件失败写成归档缺陷或通过。

只复制已追踪公开文件，在临时 `.codex/worktrees` 下通过 `git worktree add` 创建真实 worktree。configs/tests/src/toolalign 中各植入 `.KEY`、`.PEM`、`.PT`、`.SAFETENSORS`、`.ENV`、`private-SERVICE-ACCOUNT.JSON` 和 `fixture/MODELS/private.json`，共 **21** 个随机合成文件。全部被 Git 忽略，同一 fixture 公开扫描退出 0；Hatchling 的 VCS 规则数仍为 0。

| 归档路径 | 原始公开/控制文件保持字节一致 | 合成私有内容实际进入 |
|---|---:|---:|
| sdist | 30 | **21** |
| 从 sdist 重建 wheel | 15 | **7** |
| 直接从 worktree 构建 wheel | 15 | **7** |

所有归档均检查实际成员字节，不只是读取选择配置。没有接触真实私有数据、密钥或权重。合成归档随临时目录清理，完整输出仅私有保留；日志 SHA-256 为 `2c0db872a93c150e42c38c8b1177c75992fa95a0162416d69aab85b34bbd3ac7`。

问题位于 `pyproject.toml:42–49` 的小写 glob：本机 Git 忽略大小写，而当前 Hatch 显式排除仍区分大小写。源码包和两种 wheel 均受影响，因此当前 P1 不能整体关闭。修订应覆盖大小写变体并保留公开 `.env.example` 例外；本轮未实现或审查后续修订。

## 对照与必要回归

| 运行标签 | 实际结果 |
|---|---|
| `original-r1-probe` | 首轮 `probe_sdist.py app-new-nested` 原文退出 0，四个原始小写反例已关闭 |
| `source-boundary-85` | 新候选自带的 85 项实际 sdist/重建 wheel/直接 wheel 检查退出 0 |
| `lowercase` | 本轮同一脚本的 21 个小写输入，三种归档均无泄入，退出 0 |
| `case-variants` | 21 个 Git 忽略变体进入 sdist，源码目录 7 个进入两种 wheel，退出 1 |
| `old-control` | 仅在合成 fixture 恢复 55a330b 的 pyproject；旧配置 sdist/重建 wheel/直接 wheel 分别收入 18/6/7 个合成文件，退出 0 表示旧缺陷对照成立 |
| `cpu-sync` | 默认环境为 12 个 distributions，退出 0 |
| `cpu-regression` | 176 passed，退出 0 |
| `lint` / `freeze` | 退出 0，冻结 `toolalign.contracts.v1` 四个文件相同 |
| `public-candidate` / `public-review` | 本轮公开扫描，逐次实际路径数与 hash 见日志索引；不能替代被忽略内容的归档检查 |
| `public-install` | 新建仅公开输入的独立 worktree，实际构建并通过原 P00 隔离安装/CLI 验证 |
| `unchanged-inputs` / `pyproject-scope` | 依赖、冻结实现、来源和旧审查证据字节未变；pyproject 结构仅有打包排除变化 |
| `metadata-recheck` | 仅读取 S0 现存 69/90 环境的 dist-info，再核对 locked export/T1 清单，退出 0 |

三个场景使用同一探针，将末尾参数替换为 `lowercase` 或 `old-control` 即可复现。下列入口仅在复制公开追踪文件的合成 worktree 中构建/安装；不会对真实工作目录中的私有输入打包：

```bash
uv run --locked python reports/review/S0-SHARED-02/verify_public_install_r2.py
uv run --locked python scripts/check_source_distribution.py
uv run --locked pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py
```

176 项不包含旧 S0-SHARED-01 的“恰一个 extra”快照，不改历史断言来制造当前通过。新探针不是 176 项测试的一部分；三种归档检查和其失败结果单列。

## 正常公开产物与沿用依据

干净公开 fixture 中新执行 `uv build` 得到：

| 产物 | bytes | SHA-256 |
|---|---:|---|
| sdist | 87,008 | `4f10d65fab25c51ddaf29439d4d53780a87b290ae4fb149a399a44a22712369e` |
| wheel | 18,422 | `8eaf706a2d3f24bb7d902f8ccda453a28431bc0783a02c882588b38848033ec2` |

该 wheel 与首轮正常公开产物相同。原 P00 `verify_wheel.py` 在这个新 fixture 内运行，使用临时隔离环境验证依赖 hash/check、安装后的 schema digest、五类 CLI fixture、无源码树依赖和无 ML 后端，均通过；本轮未修改旧安装验证脚本。

`unchanged-inputs` 对前轮审查 commit 与精确新候选执行 `git diff --exit-code`，检查 uv.lock、THIRD_PARTY_NOTICES、docs/14、.gitignore、src/configs/tests、冻结摘要、PROTOCOL、GOAL、CI 和首轮完整审查目录；退出 0。TOML 结构对照在移除新旧 exclude 项后完全相等，证明直接依赖、extra、构建工具和其他项目字段未变。

原 metadata 小脚本只读再查现存环境，得到 69/90 个包，与当前 locked export 和已固定 T1 88 项清单相等（项目/Ruff 单列），输出 hash 与首轮相同。其读取的本地 wheel 已核对为上表同一字节产物。默认 CPU、三平台 marker/export 和库许可证结论在相同锁定制品与声明字节基础上沿用；没有重新获取 PyPI JSON/库 wheel 或安装完整 ML 环境。上轮 `mlx-lm-lora` 的 MIT metadata / Apache LICENSE 差异未消失。

候选中的 P03 登记和 P01/P02/D1 历史状态仅按协调文档阅读；没有把这些任务的自测或交付状态签为实现验收。D1 历史私有归档说明已补充，本轮未重新读取其归档或解包日志。

## 记录与范围

[evidence-r2.json](evidence-r2.json) 记录实际完整命令（私有路径使用占位符）、退出码、完整原始日志 SHA-256、两个新脚本的 hash 及未执行项。原始 stdout/stderr 保存在本机私有证据中，未提交本机绝对路径、任务 ID 或真实私有文件名。当前唯一产品失败为 `case-variants`，其安全断言保持失败；没有测试器错误被改写为产品通过。

**NOT_RUN**：ML 包导入、模型/张量/GPU/训练，P01/P02/P03 完整验收，跨平台实机安装，重新下载上游制品，D1 私有归档内容，最终 GitHub CI/main 集成，以及 S0 下一轮未发布修复。R1 只新增指定 r2 证据文件，不改生产实现、首轮 FAIL、旧分支或其他 worktree。
