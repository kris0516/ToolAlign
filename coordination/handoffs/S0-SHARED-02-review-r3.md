# S0-SHARED-02｜独立复审 r3

reviewer：R1；日期：2026-09-06；结论：**PASS**。剩余 P0：**0**；P1：**0**；P2：**0**。

- 精确完整候选：`f8ec7ff040053f11e073b6858e1f849e888d4ac2`，fetch 后与 `origin/work/shared-backend-packaging` 一致；本轮审完整候选，不只审生产修订 `ea051317c14d5db23349e565196985b67e8037d6`。
- 任务 base：`97466a20f599f68c511b9c8a71fe5f2cdfd9ad4b`；上一候选 `81489292c7ba54875c7de1f156bd1696fe4ed0a7`；上一审查 `f4af080e80380023ecac9c5262754faedb344b05`。
- 分支：`review/shared-02-r3`，从精确候选新建；原 r1/r2 分支及两轮 FAIL、探针原文保留。
- 已读：新候选 AGENTS、任务包、`coordination.v1`、PROJECT_STATUS、handoff、ADR-0016 修订及 docs/15。冻结 `toolalign.contracts.v1` 未改变。

## 两轮 P1 的关闭证据

公共 `[tool.hatch.build].exclude` 保留现有私有类别，并以显式 ASCII 字母大小写字符类同时匹配文件名和目录；`*.py[cod]` 的末尾集合包含两种大小写，`.env.example` 的否定例外采用相同大小写语义。规则同时用于 sdist 和直接 wheel，sdist 的公开目录范围未扩大。R1 没有修改候选实现。

**原失败探针未经修改独立重跑。** 在本机 Git 自动检测的 `core.ignorecase=true`、Hatch VCS 规则数仍为 0 的相同条件下，r2 的 `case-variants` 和 `lowercase` 均退出 0。此前实际泄入 sdist 的 21 个大小写变体、两种 wheel 中的各 7 个文件，现在三种归档均无泄入；公开文件对照保持 30／15。此次未由 R1 强制设置 Git ignorecase，前轮失败结果原样保留。

**候选完整归档回归独立通过。** R1 亲自运行新 `check_source_distribution.py`：241 个私有合成探针全部排除，18 个公开对照在对应归档中保留，冻结 schema 相同。该生产检查仅在临时合成仓库设置 ignorecase，以便 Linux CI 复现 Mac 条件；不改实际仓库或用户配置。240 个探针先由 Git 验证忽略，未列名根文件另由 sdist 范围排除；不同大小写变体使用独立父目录，避免 Mac 上覆盖同一个文件。

**补充边界独立通过。** 新 r3 探针增加 45 个 Git 忽略输入，覆盖大小写混合的缓存/工作目录、`.coverage`、`.DS_Store`、三种 py[cod] 后缀、根级私有 data 路径，以及接近公开例外但仍应排除的 `.ENV.EXAMPLES`、`.eNv.ExAmPlE.private`。另有 21 个公开对照，包括三种大小写 `.env.example`、`.PYI` 和以 `.example` 结尾的模型/密钥扩展名近似文件。

新探针在本机自动 Git 条件下，实际检查 sdist、由 sdist 重建的 wheel、直接 wheel：私有内容均为 **0**；现有公开源码/config/test 的 26 个文件加 21 个公开对照在 sdist 内共 **47** 个文件字节相同，wheel 内现有 14 个源码/资源加 7 个公开对照共 **21** 个相同。全部使用小合成 worktree，无真实私有输入。各组探针存在重叠，不把数量相加为独立覆盖率。

## 正常产物、CPU 与未变化输入

新候选在只复制 Git 追踪公开文件的干净合成 worktree 中实际构建，并运行未修改的 P00 隔离安装脚本：CPU 依赖 hash/check、安装后的 schema、五类 CLI fixture、隔离源码路径及 no-ML 全部通过。

| 正常公开产物 | bytes | SHA-256 |
|---|---:|---|
| sdist | 87,889 | `7d1e53cd0a824846abd4b679526e53d80eaa22c849b843284cd89245c7723a1f` |
| wheel | 18,422 | `8eaf706a2d3f24bb7d902f8ccda453a28431bc0783a02c882588b38848033ec2` |

wheel 与前两轮正常公开产物字节相同。**本轮 176 项 CPU 回归实际通过**，冻结摘要、最终 lint 和公开扫描通过。没有把 S0 自查、旧测试或绿色 CI 当作本轮执行证据。

`git diff --exit-code` 确认源码、configs/tests、uv.lock、第三方说明、.gitignore、CI、docs/14、冻结摘要、PROTOCOL/GOAL 和完整旧审查证据未变。TOML 对照确认打包 exclude 之外的项目、依赖、extra 与构建工具字段相同。因此前轮 69／90 依赖环境、默认 CPU/平台 marker、固定上游制品和许可结论可沿用；本轮未重复 ML 安装或来源下载研究。mlx-lm-lora 的 MIT metadata 与 Apache LICENSE 差异仍保留。

一次初始 lint 非零来自 R1 新增探针的导入分组空行；仅修正该新审查文件，候选未动。最终 lint 与补充归档探针重跑通过，初次输出和修正前脚本摘要保留在本轮证据中，不计为产品缺陷。

逐命令、退出码、完整日志 hash 和复现方法见 [r3 说明](../../reports/review/S0-SHARED-02/README-r3.md) 与 [r3 索引](../../reports/review/S0-SHARED-02/evidence-r3.json)。

## 可交接范围与 NOT_RUN

本 PASS 仅接受该精确候选的共享依赖/源码包边界修订。S0 仍须完成最终 CI、合并和 main 集成验证后才发布新共享基线；不以此批准 P01/P02/P03 或后续正式训练。

**NOT_RUN**：ML/模型/张量/GPU/训练，完整 ML extras 重新安装及 69/90 环境再次审计，上游制品重新下载，跨平台实机安装，P01/P02/P03 全包验收，D1 私有归档/解包日志，最终 GitHub CI、main 合并与集成验证。

本轮仅新增指定 r3 handoff、r3 说明/索引和一个小探针。未改旧 FAIL/脚本、生产实现、正式看板、其他 worktree 或全局 Git 配置；未推送、合并、发布、建立新任务或嵌套代理。审查 commit 通过私有回报交给 S0，随后等待下一包。
