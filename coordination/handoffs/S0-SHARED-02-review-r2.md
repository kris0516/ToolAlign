# S0-SHARED-02｜独立复审 r2

reviewer：R1；日期：2026-09-06；结论：**FAIL**。剩余 P0：**0**；P1：**1**；P2：**0**。

- 精确候选：`81489292c7ba54875c7de1f156bd1696fe4ed0a7`；本轮 fetch 后 `origin/work/shared-backend-packaging` 与之相同。
- 任务 base：`97466a20f599f68c511b9c8a71fe5f2cdfd9ad4b`；前轮候选 `55a330b6a1c10d14959895f2a3617597962569f3`；前轮审查提交 `cfbc1529e9bc946c42a26a0070528217ab8eafff`。
- 本轮分支：`review/shared-02-r2`，直接从精确候选新建；原 `review/shared-02-r1` 和首轮 FAIL/探针字节均保留。
- 已读：新候选 AGENTS、任务包、`coordination.v1`、PROJECT_STATUS、handoff、ADR-0016 修订及 docs/15。冻结 `toolalign.contracts.v1` 未变。

## 判定：小写反例已关闭，大小写变体仍泄入三种归档

**首轮具体反例已关闭。** 不改原文重跑 `probe_sdist.py app-new-nested` 退出 0，仍确认 Hatchling VCS 规则数量为 0、四个原始嵌套文件均排除。候选自带的 85 项源码包/两种 wheel 检查也独立运行通过。公共 build 排除确实生效，不能把本轮失败写成首轮修复毫无效果。

**剩余 P1：公共排除与本机 Git 的大小写行为不一致。** 位置 `pyproject.toml:42–49`；相应覆盖缺口为 `scripts/check_source_distribution.py:25–41`。本机文件系统上 `git init` 自动检测 `core.ignorecase=true`，因此 Git 会忽略 `.PEM`、`.ENV`、`.PT`、`MODELS` 等变体；候选的显式 Hatch pattern 仍按小写匹配，在 `.codex` 布局丢失 VCS 规则时遗漏这些文件。

R1 新探针在微型真实 Git worktree 中，只读而未设置 `core.ignorecase`。在 configs、tests、src/toolalign 三处，各植入七种随机合成文件：`.KEY`、`.PEM`、`.PT`、`.SAFETENSORS`、`.ENV`、`private-SERVICE-ACCOUNT.JSON`、`fixture/MODELS/private.json`。全部 **21** 个文件被 `git check-ignore` 命中，同一 fixture 公开扫描退出 0，但实际结果为：

| 构建路径 | 实际收入的合成私有文件 |
|---|---:|
| sdist | 21 |
| 从 sdist 重建 wheel | 7（源码目录内） |
| 直接从 worktree 构建 wheel | 7（源码目录内） |

新探针安全断言退出 **1**，完整日志 SHA-256：`2c0db872a93c150e42c38c8b1177c75992fa95a0162416d69aab85b34bbd3ac7`。这不是仅通过选择器枚举推断，也没有强制设置 Git 配置来制造场景；三个真实归档均已检查。源文件名大小写是本机正常可出现的输入，因此当前私有归档边界仍应阻断放行。

请 S0 让公共私有排除覆盖目标文件系统/Git 的大小写行为，在 sdist 与两种 wheel 中检查混合大小写的密钥、环境、模型扩展名和目录，同时保留公开 `.env.example` 例外。本 R1 未修改生产规则或旧测试。S0 已确认当前精确候选保持不变，后续修订另行固定 SHA；本轮不审尚未发布的修复。

## 通过的回归与沿用证据

R1 的额外 **21 个小写对照**在三种归档中均无泄入；26 个现有公开源码/config/test 文件及四个公开控制文件（含 `.env.example`）在 sdist 内保持字节一致，wheel 内的 14 个现有源码/资源及一个公开模块控制文件也保持一致。原 55a330b 配置仅写入合成 fixture，旧缺陷在实际 sdist 和直接 wheel 中重新复现，未对真实私有输入构建。

**176 项 CPU 回归、lint、冻结、公开扫描通过。** 另在仅复制已追踪公开文件的干净合成 worktree 中实际 `uv build`，新 sdist 为 87,008 bytes，SHA-256 `4f10d65fab25c51ddaf29439d4d53780a87b290ae4fb149a399a44a22712369e`；wheel 为 18,422 bytes，SHA-256 `8eaf706a2d3f24bb7d902f8ccda453a28431bc0783a02c882588b38848033ec2`，与首轮正常公开 wheel 相同。原 P00 隔离安装脚本在该新 fixture 内运行，默认 CPU 依赖、schema、CLI 五类 fixture、隔离导入/no-ML 均通过。

`git diff --exit-code` 确认 uv.lock、第三方许可说明、docs/14、.gitignore、src/configs/tests、冻结摘要、协议、CI 和首轮完整审查证据均未变。TOML 结构对照确认 pyproject 只迁移/扩展打包 exclude，依赖/extra/构建工具声明未变。只读重查现存 69／90 环境 metadata 和 locked export，通过，与首轮原始输出 hash 相同；未重新下载库、安装 ML extras 或重复来源研究。固定制品/许可证结论在这些相同字节基础上沿用，MIT metadata 与 Apache LICENSE 的既有差异仍保留。

候选新增的 P03 登记、P01/P02 已交接状态和 D1 历史归档说明仅作为协调文档审阅；未引入这些任务的生产实现。没有以状态文档或 S0 自查/CI 成功代替本轮独立复审。

逐命令、退出码、完整日志 hash、复现方法和范围见 [本轮说明](../../reports/review/S0-SHARED-02/README-r2.md) 与 [本轮索引](../../reports/review/S0-SHARED-02/evidence-r2.json)。

## NOT_RUN 与交接

**NOT_RUN**：任何模型/ML 导入、张量/GPU/训练、P01 数学和功能验收、P02/P03 实现验收、D1 私有归档/解包日志、跨平台实机安装、重新下载上游制品、最终 GitHub CI、main 合并与集成验证，以及 S0 尚未发布的新修复。

本轮仅新增指定 r2 handoff、本目录中的 r2 说明/索引及两个小探针；旧分支、FAIL 报告和探针原文保持不变。未改生产实现、正式看板、其他 worktree、全局 Git 配置或远端，未建立新任务/嵌套代理。审查 commit 通过私有回报交给 S0。当前候选结论为 FAIL，等待下一精确修订复审。
