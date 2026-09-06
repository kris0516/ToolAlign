# 项目真实状态

更新时间：2026-09-06。当前交付状态：**P00_VERIFIED**；P01/T1 与 P02/D1 均已交付候选等待独立审查，P02 另需 kris 实际数据语义审查；P03/E1 正在进行 CPU 实现。

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
| 当前任务/分支 | S0 main；公共支持包合并 `18fc8475476f6becf684ba817480caeb96a7cfb9` 并验证 |
| 当前契约 | toolalign.contracts.v1 已冻结；五类 wire schema + 六个 Protocol |
| 独立实现/reviewer 对话 | T1/P01、D1/P02 已交付/空闲；E1/P03 进行中；R1 正在审 S0-SHARED-02 |
| 子任务派发模型 | gpt-6-astra / max（最高）；所有子任务与 S0 统一，旧极高规则废止 |
| 持久运行 | 长期 goal ACTIVE；本对话每 30 分钟跟进；电脑及 App 需保持运行 |
| 本地工具 | Python 3.14、uv、VS Code、Xcode 可用；P00 venv 实测 Python 3.14.7 |
| GitHub 写入能力 | 本机 Git push dry-run 成功；connector 确认 admin/push 权限 |
| 当前实现 | CPU Python 基础包、数据契约、模块 Protocol、共享 GPU 锁及测试 |
| 已验收训练/数据/评测/服务 | 无；P01/P02 候选已交付，均尚无本包验收 |
| 已运行模型实验 | T1 已报告 0.6B smoke 与 1.7B 长度校准；尚未独立验收，不作为正式 SFT/DPO 结果 |
| 重 GPU 作业 | 由 T1/P01 在共享租约内进行；实时状态查私有租约记录，不能从本表推断锁空闲 |
| 费用/公开上传 | 无付费云资源；无模型/数据上传；无公网推理 |

精确本机路径、task ID、自动跟进 ID 和对话映射保存在 `.toolalign-local/`，不提交公开仓库。

## 当前门槛

P00 自测、R1 精确 head 独立审查、S0 合并与 main 重验均已满足。第一批为 P01/T1 与 P02/D1；T1 交付且原生状态空闲后，已派发并核验 P03/E1（code_base `97466a2`，授权 `e882594`）。D1 随后也已完成交接并核验空闲，当前实现任务为 E1；后续反馈修订仍最多两个并行。未返回真实 task ID 不写 DISPATCHED。

## 恢复入口

先读 AGENTS、BOARD、DECISIONS、当前任务包及最近 handoff，核对 Git 与 GPU 锁，再读取本地私有对话映射。未提交变更不能作为交接完成证据；R1 不批准自身实现。首轮五项问题已修复；R1-r2 对 `5d30e1b4bd5e2284abbe59a5f16b2966f85feb87` 独立 PASS，剩余 P0/P1/P2 均为 0，审查提交 `441d31bebd5ca4d46755642f94966c07bbcc4ad1`。最终 PR head `7086424` 的 Python 3.11/3.14 CI 成功，PR #2 合并为 `cd091e3a53986b59b170baf5b746644f369135d1`；main 58 + 46 + 72 项检查及 lint/冻结/公开扫描/CLI 均通过。见 [独立复核](handoffs/P00-review-r2.md) 与 [main 证据](../reports/P00_MAIN_VERIFICATION.md)。

公共支持：S0-SHARED-01 已 VERIFIED，见 [main 集成证据](../reports/S0_SHARED_01_MAIN_VERIFICATION.md)。可选依赖/来源政策正式发布给 T1/D1；P01/P02 原任务仍 IN_PROGRESS，不因公共支持通过而提前放行 P04。用户模型设置保护见 [GOAL](GOAL.md) 与 ADR-0014。

P01 精确候选 f97bb0de346c220871962a5689014a379fe19c83，274项CPU与模型校准仅为T1自测；R1先关闭公共打包边界问题，再分别审完整P01/P02。共享候选两轮发现的嵌套/大小写P1及FAIL报告均保留，最新修订实现为ea05131；尚未发布已验证新基线。旧sdist选择可纳入私有目录，源码包发行暂停；D1已隔离一次未上传的失败tar，细节私有保存。P03先CPU实现，修复后再同步新base。

P02 精确交接 `46f546504f73588caa2e71aac316c3c312306df6`，生产实现 `9be07a5`。D1 自测 355 项 CPU（包含 57 项旧共享快照），两次构建 18 项产物一致，最终 8,228 决策；这不构成独立验收。S0 已核对 100 来源/114 决策人审包及独立填写副本的 hash，判定字段全空，G-DATA 仍待审；实际渲染未验证。
