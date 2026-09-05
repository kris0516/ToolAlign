# P00｜独立复核 r2

reviewer：R1；任务：P00-review-r2；日期：2026-09-06；结论：**PASS**。

- 规划 base：`0f152e287bbc0e1c3edfb3f6f3794eb8d36c422f`。
- 首轮被审 head：`15706079c9516197b67dd59a19a0d0c4aa5adea8`。
- 本次精确被审 candidate：`5d30e1b4bd5e2284abbe59a5f16b2966f85feb87`。
- 来源：`origin/work/p00-bootstrap-contracts`；本次 fetch 后远端引用与 candidate 一致。
- 审查分支：`review/p00-r2`；已核实为 App 创建的独立 worktree；仅使用本工作区。
- 契约：`plan-v0.1` / `coordination.v1` / `toolalign.contracts.v1` 冻结候选。
- 剩余问题：P0 **0**，P1 **0**，P2 **0**；本轮无外部阻塞。

## 复核范围与证据

读取候选 AGENTS、P00 任务包、PROTOCOL、PROJECT_STATUS、架构/数据治理/资源锁/G0 规格、冻结说明、原始 R1 handoff/probes 与 S0 修订二说明。分发消息中的任务包实际路径为 `coordination/tasks/P00_BOOTSTRAP_CONTRACTS.md`，已读取此文件。

逐项检查旧 candidate 到新 candidate 的修复 diff，并针对完整 base..candidate 的 52 文件变更做 G0 回归抽查：五类 wire records、六个 Protocol、语义校验与 CLI、资源锁、契约摘要、依赖/构建/CI 配置、公开候选内容。原始 R1 报告/探针与首轮审查提交逐字节相同；现有 contract tests 保留原断言。修订二在 src 下仅修改 validator/schema；schema 除 pattern 外的结构、interfaces、runtime、协议配置及依赖未变。

本 R1 在精确候选独立运行：**58 项基础测试、46 项原始 R1 探针、72 项新增边界探针全部通过**。lint、冻结摘要、公开内容扫描、构建、独立 wheel 安装与修订范围检查均退出 0。Python 为 **3.14.7**。全部 CPU；测试锁只在临时合成仓库运行，没有取得实际项目 GPU 作业租约。

逐命令退出码、原始日志 SHA-256、wheel/schema 摘要、初次探针搭建错误及复现步骤见 [本轮证据说明](../../reports/review/P00-r2/README.md)。原始日志和真实任务身份仅存本机私有目录。S0 自测与旧绿色 CI 未被作为本轮 PASS 的证据。

## 原问题关闭情况

| ID | 原优先级 | 本轮独立观察 | 状态 |
|---|---|---|---|
| R1-01 | P1 | 原来三个隐藏 schema 负例均拒绝。新增覆盖七种 primitive type 的不适用关键词，直接/嵌套两种位置共 14 项均拒绝；合法外围 schema 先通过正控。enum/description 内的 schema 样式字面数据仍可通过，未过度递归普通数据。socket connect/DNS 拦截没有记录调用。 | CLOSED |
| R1-02 | P1 | 原始“index 保留合成 token、只擦除工作副本”仍被拒绝。新增 index/工作副本/未跟踪内容三来源各测超限大小、非 UTF-8 和合成 token；1 MiB 边界及普通/可执行模式通过，index symlink/gitlink、冲突 stage 和被替换的父目录 symlink 拒绝；敏感文件名脱敏。 | CLOSED |
| R1-03 | P2 | 原始自由 dependency 键不再出现在 CLI stderr。新增 dependency、未知嵌套字段、工具参数、schema property/keyword 五类合成键；ContractError 消息及 JSONL CLI 输出均不回显标记，CLI 返回 2。异常对象中的 cause 不构成公开日志的脱敏保证。 | CLOSED |
| R1-04 | P2 | 原有身份/时间记录负例通过；新增逐一检验全部 35 个导出 pattern 节点：有效边界通过，LF/CR/CRLF/Unicode 行分隔符/NUL/空格后缀及前置 LF 拒绝；hash/ID/name 长度与字符集边界同样通过。 | CLOSED |
| R1-05 | P2 | 原始历史/目标冲突拒绝。新增两轮工具调用、每轮两个 ID、逆序配对 observation：合法目标成为下一轮历史后仍合法，任一更早 ID 重用或目标内部重复均拒绝，最终 final 决策通过。 | CLOSED |

未发现候选含真实秘密、训练数据/权重或业务执行器；以上拒绝测试全部使用原创合成输入。没有观察到远程 schema 获取或数据驱动的任意执行，不把 schema 入口缺陷夸大成已发生的利用。

## G0 抽查与限制

五类记录的必填/未知字段、版本、model identity，Python 接口字段与 wire 定义，ModelInput 仅 messages/tools 的深拷贝投影，train-only preference/共享 prompt hash/非明确标签拒绝，run 终止字段、DPO 缺失 reference、artifact 越界及各类终止 trace outcome 均在本轮基础/原始探针中实际重跑。

CPU 锁回归重现跨进程、跨 worktree 互斥、超时、不删除 inode、异常/测试自有子进程 SIGKILL 后释放及元数据写入失败时释放。此锁的保证仍限同一 repository 的合作 worktree；不宣称跨独立 clone 或任意进程的全机强制互斥。没有实际 GPU 性能或内存测试。

冻结四文件摘要通过，临时副本单字节变更检测通过。新 wheel 离开源码目录安装，在临时 Python 3.14 环境中五类 CLI 校验、schema 摘要、依赖闭包及隔离导入通过，mlx/torch 均不存在。公开扫描覆盖干净候选的 89 条路径及实际 index blob；它仍为启发式检查，不能证明任意秘密模式均被检测。

**NOT_RUN**：GitHub CI/仓库权限与可见性本轮读回；本机 Python 3.11/3.12/3.13；S0 main 合并与集成后验收；P01–P03 实现；模型/数据下载、MLX/PyTorch 后端、训练、BFCL/真实 oracle/正式评测、性能与面试效果、服务部署。自然语言中的答案泄漏、真实数据 group 隔离、评测分母正确性、真实 SFT reference 身份须后续阶段另验。

## 可合并范围与交接

**建议 S0 接受该精确 candidate 的 P00 复核，并按协议集成 P00 与本审查证据；合并后仍须在 main 重跑关键检查，才可发布下一任务 base。** 本 PASS 不授权 P01–P03 在集成验证前启动，也不代表任何模型/业务 release。

本 R1 仅提交 `coordination/handoffs/P00-review-r2.md` 与 `reports/review/P00-r2/` 下的审查说明/小测试；未修实现、改旧测试期待值、契约/摘要/依赖、BOARD/PROJECT_STATUS/DECISIONS。未合并 main、推送分支、创建新任务/代理或发送 GitHub 评论。审查 commit、正式任务身份及 worktree 位置由最终回复交 S0 私有登记；任务保持可接收后续消息。
