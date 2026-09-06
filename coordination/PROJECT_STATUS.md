# 项目真实状态

更新时间：2026-09-06。当前交付状态：**P00_VERIFIED**，两个共享支持包已VERIFIED。T1/D1已交付同步后的新完整候选，E1正在CPU基线同步；各包尚待独立审查，P02另需kris实际数据语义审查。

| 项目 | 当前记录 |
|---|---|
| 公开仓库 | `https://github.com/kris0516/ToolAlign` |
| 可见性 | public（GitHub connector read-back 已确认） |
| 规划 main 基线 | `0f152e287bbc0e1c3edfb3f6f3794eb8d36c422f` |
| 规划内容提交 | `a74b4e44b1be72c1fd254e1a24e91b28ee52639c` |
| 规划/协作基线 | plan-v0.1 / coordination.v1 |
| Supervisor | S0；本机独立 Codex 对话，已领取 |
| S0 模型/推理 | gpt-6-astra / max（最高）；已提交原生设置；普通回报省略 model/thinking |
| 领取时间 | `2026-09-05T21:19:08.074530+00:00` |
| 当前任务/分支 | S0 main；S0-SHARED-02 在 `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` 合并并验证 |
| 当前契约 | toolalign.contracts.v1 已冻结；五类 wire schema + 六个 Protocol |
| 独立实现/reviewer 对话 | T1已交付59b3802并原生空闲；D1已交付b0d8d83；E1已派CPU同步并核验活跃；R1待派完整P02技术审查 |
| 子任务派发模型 | gpt-6-astra / max（最高）；所有子任务与 S0 统一，旧极高规则废止 |
| 持久运行 | 长期 goal ACTIVE；本对话每 30 分钟跟进；电脑及 App 需保持运行 |
| 本地工具 | Python 3.14、uv、VS Code、Xcode 可用；P00 venv 实测 Python 3.14.7 |
| GitHub 写入能力 | 本机 Git push dry-run 成功；connector 确认 admin/push 权限 |
| 当前实现 | CPU Python 基础包、数据契约、模块 Protocol、共享 GPU 锁及测试 |
| 已验收训练/数据/评测/服务 | 无；P01/P02/P03 候选已交付，均尚无本包验收 |
| 已运行模型实验 | T1 已报告 0.6B smoke 与 1.7B 长度校准；尚未独立验收，不作为正式 SFT/DPO 结果 |
| 重 GPU 作业 | P01历史校准已结束，当前未派发新GPU作业；任何后续加载仍须实际取得共享租约 |
| 费用/公开上传 | 无付费云资源；无模型/数据上传；无公网推理 |

精确本机路径、task ID、自动跟进 ID 和对话映射保存在 `.toolalign-local/`，不提交公开仓库。

## 当前门槛

P00自测、R1精确head独立审查、S0合并与main重验均已满足。三个原候选均已交付；共享base37c00de和授权f2a271b发布后，先派D1/T1同步。T1交付且原生空闲才派E1接名额，现E1已核验活跃，D1新候选已收到；后续仍最多两个并行实现，不从文档推定运行状态。

## 恢复入口

先读 AGENTS、BOARD、DECISIONS、当前任务包及最近 handoff，核对 Git 与 GPU 锁，再读取本地私有对话映射。未提交变更不能作为交接完成证据；R1 不批准自身实现。首轮五项问题已修复；R1-r2 对 `5d30e1b4bd5e2284abbe59a5f16b2966f85feb87` 独立 PASS，剩余 P0/P1/P2 均为 0，审查提交 `441d31bebd5ca4d46755642f94966c07bbcc4ad1`。最终 PR head `7086424` 的 Python 3.11/3.14 CI 成功，PR #2 合并为 `cd091e3a53986b59b170baf5b746644f369135d1`；main 58 + 46 + 72 项检查及 lint/冻结/公开扫描/CLI 均通过。见 [独立复核](handoffs/P00-review-r2.md) 与 [main 证据](../reports/P00_MAIN_VERIFICATION.md)。

公共支持：S0-SHARED-01 已 VERIFIED，见 [main 集成证据](../reports/S0_SHARED_01_MAIN_VERIFICATION.md)。可选依赖/来源政策正式发布给 T1/D1；P01/P02/P03 候选尚待各包独立验收，不因公共支持通过而提前放行 P04。用户模型设置保护见 [GOAL](GOAL.md) 与 ADR-0014。

P01 精确候选 f97bb0de346c220871962a5689014a379fe19c83，274项CPU与模型校准仅为T1自测；下一批分别审完整P02/P01/P03。共享包R1-r3对f8ec7ff独立PASS，审查ad3b519保留原SHA整合，两轮FAIL保持原文；最终CI成功，PR4合并37c00de并验证，[新共享base现已发布](../reports/S0_SHARED_02_MAIN_VERIFICATION.md)。D1/T1先同步，E1待名额；不得在旧基线默认构建sdist。D1已隔离一次未上传的旧失败tar，细节私有保存。

P02 精确交接 `46f546504f73588caa2e71aac316c3c312306df6`，生产实现 `9be07a5`。D1 自测 355 项 CPU（包含 57 项旧共享快照），两次构建 18 项产物一致，最终 8,228 决策；这不构成独立验收。S0 已核对 100 来源/114 决策人审包及独立填写副本的 hash，判定字段全空，G-DATA 仍待审；实际渲染未验证。

P03 精确交接 `85e0905fc82da4504d73bf7eb489c1f1a0d227a7`，实现 `8afb114`。E1 自测191项CPU（133项P03）、scripted demo 10/10、90条trace与20个自有进程回收。S0已读取正式交接并核验原生任务终止；尚无独立R1、真实MLX/Qwen、正式隐藏集/BFCL或GPU验收。ModelBackend的spawn构造与轻量可序列化状态前提保留在交接中，不能从scripted成功推定已加载MLX对象可跨进程使用。

最新同步交接：T1候选59b3802c81aa6eceaf3609af88f288756bcb1581（merge17a003f）CPU217通过，新锁69/90环境metadata及PyTorch CPU参考通过，原模型实现/10次历史run未变。D1候选b0d8d83750c48cd951c16b50cfa28a7898976e72（merge9bbd7d7）CPU298含17真实tokenizer通过，data模块/两遍18产物/100来源114决策的人审包hash均未变。两者新sdist/wheel和隔离安装已自测，原始交接保留；S0核对新handoff及候选范围后安排R1，各包仍未VERIFIED。
