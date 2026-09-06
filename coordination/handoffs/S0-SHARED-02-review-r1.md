# S0-SHARED-02｜独立审查 r1

reviewer：R1；日期：2026-09-06；结论：**FAIL**。剩余 P0：**0**；P1：**1**；P2：**0**。

- 精确 base：`97466a20f599f68c511b9c8a71fe5f2cdfd9ad4b`。
- 精确被审 candidate：`55a330b6a1c10d14959895f2a3617597962569f3`，来源 `origin/work/shared-backend-packaging`，领取时读回一致。
- 审查分支：`review/shared-02-r1`；沿用同一个独立 R1 worktree。
- 已读契约：`coordination.v1`、冻结 `toolalign.contracts.v1`、任务包 S0-SHARED-02、ADR-0015/0016 及 docs/14/15；保留既有来源政策和冻结接口边界。
- 审查覆盖候选全部 11 文件 diff、S0 自查/原始日志、已安装 dist-info 和许可。T1 只读提交 `f97bb0de346c220871962a5689014a379fe19c83` 的实测依赖清单与源码包枚举脚本。

## P1：sdist 的目录白名单仍收入目录内的忽略文件

位置：`pyproject.toml:43–57`；相应覆盖缺口位于 `scripts/check_source_distribution.py:16–24`。

候选把 `src/toolalign`、`configs`、`tests` 整个目录纳入 `only-include`，但显式排除只有缓存、字节码及环境文件。Hatchling 1.27.0 在本项目 `.codex/worktrees` 布局下仍返回空 VCS 忽略规则，导致这些目录内部的 `.gitignore` 规则失效。

R1 在仅含公开追踪文件的微型 Git worktree 中植入四个随机合成文件：`configs/synthetic.key`、`configs/synthetic.pem`、`tests/synthetic.safetensors`、`src/toolalign/synthetic.pt`。四者均被 `git check-ignore` 识别；同一 fixture 的公开扫描退出 0，但实际 sdist 包含全部四个合成内容。新增独立探针的安全断言退出 **1**。候选自带源码包检查同时通过，因为其目录内部负例只检查已显式排除的 `__pycache__`。

这是当前“源码包私有内容边界”交付的阻断问题：只要开发者在被递归纳入的配置、测试或源码目录留下忽略文件，正常构建就可能把密钥或模型类文件写入可分发归档。此次复现仅使用随机合成字节，不含真实密钥、模型或原始数据；没有上传。

请 S0 使这些目录的归档选择也独立遵守公开文件边界，并把目录内的忽略文件加入实际 tar 内容负向检查，再核对由 sdist 重建的 wheel。可以采用明确的公开文件清单或等效的构建选择机制；不能仅以根目录白名单及 Git 公开扫描作为证明。R1 没有修改候选配置或生产检查脚本。

最小复现及全部退出码、日志 SHA-256 见 [审查证据](../../reports/review/S0-SHARED-02/README.md) 与 [证据索引](../../reports/review/S0-SHARED-02/evidence.json)。

## 已通过的独立检查

**依赖与安装元数据：通过。** 默认实际 CPU 环境为 Python 3.14.7、12 个 distributions；原 11 个第三方锁记录逐条相同，默认依赖、dev、四个 compatibility 直接 pin、构建工具版本不变。新锁共有 93 条记录；optional fsspec 的 `2026.7.0 → 2025.3.0` 是已说明的真实改动，numpy/scipy 的 Python 分支也已检查。

R1 用自己的 CPU Python 只读 S0 两个现存环境的 dist-info，独立比较锁定导出、实际版本及激活的传递依赖，得到 **69／90** 个包。完整重放环境除项目本身与 dev-only Ruff 外，逐项等于 T1 的 **88** 项实测清单；备选环境的对应子集也一致。没有启动 S0 环境的 Python 或导入 ML 包。新 wheel 的三组 extra 与 Darwin arm64 marker 保持正确。Darwin arm64 的原生 dry-run 为 90 个包，Linux x86_64／Intel macOS 各 13 个，无 ML/CUDA；这是静态解析，不是跨平台实机安装。

**来源与许可：通过，差异保留。** R1 重新获取三个固定版 PyPI JSON，逐项核对锁内直接制品的 URL、size、SHA-256，并独立下载三个小型库 wheel 仅读取 metadata/LICENSE。许可证字节与 S0 实装文件相同；mlx-lm-lora 的 metadata MIT 与随包 Apache License 2.0 不一致，候选已如实保留。安装成功不批准 mlx-tune 为正式 DPO 后端。

**CPU 与正常公开产物：通过。** 176 项 CPU 回归通过；lint、冻结摘要、公开扫描、候选自带源码包检查、实际 `uv build` 及临时隔离 wheel 安装/CLI/五类 fixture 验证均退出 0。正常公开输入的 sdist 可重建 wheel，schema 摘要保留，安装环境没有 ML 后端。上述正向结果不能覆盖本轮 P1 负例。

**历史触发条件：独立复现。** 普通真实 worktree 中 VCS 规则非空，只泄入未列名根文件；`.codex` 祖先目录下规则为空，旧配置的真实合成 tar 收入模拟私有目录内容。候选新配置排除了这些根级负例，但未排除本轮新增的目录内负例。没有把 `.git` 为文件本身当作根因。

## 失败保留与来源限定

S0 原始自查日志 hash 已逐份核对。其初始静态 canary 与脚本源码冲突、普通布局归因修正和 dev-only Ruff 对比错误均保留，不作为当前产品缺陷。R1 初次旧配置对照也误要求内置排除的 `.venv` 泄入；修正这一对照预期后重新运行，原日志未覆盖。当前候选的“私有内容不得进入归档”断言保持失败，没有修改为接受泄入。

R1 额外指定通用 `aarch64-apple-darwin` 的 dry-run 选择了 macOS 13 目标，因现有 MLX 无该平台 wheel 而退出 2；在本机 macOS 26.5.1 的原生目标重新解析通过。该额外目标失败保留，未将未声明支持的 macOS 13 归为本包新增缺陷。

审查期间收到 D1 的历史补充：其旧构建曾生成含私有成员的本地归档。R1 仅独立读取被授权的 audit JSON：107,953,843 bytes、6,792 个成员，其中 6,651 个标为私有，`uploaded=false`。归档 hash 是审计文件提供值；**没有打开归档、枚举成员或解包**。D1 关于解包因 symlink 退出 2、制品已隔离的说明属于转交证据，不能写成 R1 实际运行。S0/T1 先前未完成该类归档的说明只能保留对应主体与历史时点，S0 后续事件记录应补入 D1 情况。

## NOT_RUN 与交接

**NOT_RUN**：R1 重新安装完整 ML extra、任何 ML 后端导入/张量/模型/训练/大推理/GPU 作业、P01 数学或功能重放及完整验收、D1 真实适配与人工质量门、D1 私有归档检查、跨平台实机安装、最终 GitHub CI 读回、main 合并和集成验证。

本轮仅新增本交接单及 `reports/review/S0-SHARED-02/` 中的审查说明/小探针/摘要索引。未修改被审实现、旧测试、正式状态或其他 worktree，未推送、合并、发布或创建新对话/嵌套代理。审查 commit 通过私有任务回报交回 S0；精确候选不能按 R1 PASS 放行。S0 修复 P1 后应提交新的精确候选复审。
