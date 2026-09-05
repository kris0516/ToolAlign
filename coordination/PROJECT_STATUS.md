# 项目真实状态

更新时间：2026-09-06。当前交付状态：**P00_READY_FOR_REVIEW**。

| 项目 | 当前记录 |
|---|---|
| 公开仓库 | `https://github.com/kris0516/ToolAlign` |
| 可见性 | public（GitHub connector read-back 已确认） |
| 规划 main 基线 | `0f152e287bbc0e1c3edfb3f6f3794eb8d36c422f` |
| 规划内容提交 | `a74b4e44b1be72c1fd254e1a24e91b28ee52639c` |
| 规划/协作基线 | plan-v0.1 / coordination.v1 |
| Supervisor | S0；本机独立 Codex 对话，已领取 |
| 领取时间 | `2026-09-05T21:19:08.074530+00:00` |
| 当前任务/分支 | P00 / `work/p00-bootstrap-contracts` |
| 当前契约 | toolalign.contracts.v1 候选；五类 wire schema + 六个 Protocol |
| 独立实现/reviewer 对话 | 0；原生 create/send/read/wait 能力已发现，尚未派发 |
| 派发模型 | gpt-6-astra / xhigh（极高）；仅独立对话 |
| 持久运行 | 长期 goal ACTIVE；本对话每 30 分钟跟进；电脑及 App 需保持运行 |
| 本地工具 | Python 3.14、uv、VS Code、Xcode 可用；P00 venv 实测 Python 3.14.7 |
| GitHub 写入能力 | 本机 Git push dry-run 成功；connector 确认 admin/push 权限 |
| 当前实现 | CPU Python 基础包、数据契约、模块 Protocol、共享 GPU 锁及测试 |
| 已实现训练/评测/服务 | 无；各任务待门槛 |
| 已运行模型实验 | 无（NOT_RUN） |
| 重 GPU 作业 | 无；仅 CPU 锁测试 |
| 费用/公开上传 | 无付费云资源；无模型/数据上传；无公网推理 |

精确本机路径、task ID、自动跟进 ID 和对话映射保存在 `.toolalign-local/`，不提交公开仓库。

## 当前门槛

P00 自测 → R1 独立审查精确 head → S0 合并 main → main 重验。全部满足后，第一批只派发 P01/T1 与 P02/D1；P03/E1 在实现并发名额释放后派发。所有 worker 使用独立 worktree。未返回真实 task ID 不写 DISPATCHED。

## 恢复入口

先读 AGENTS、BOARD、DECISIONS、当前任务包及最近 handoff，核对 Git 与 GPU 锁，再读取本地私有对话映射。未提交变更不能作为交接完成证据；R1 不批准自身实现。P00 自测证据已提交，下一步派发独立 R1 并等待精确提交的审查结论。
