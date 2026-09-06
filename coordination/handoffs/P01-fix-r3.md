# P01 · R1-r1 定点修复交接 r3

2026-09-06；T1，gpt-6-astra / max；分支 `work/p01-compatibility`。这是定点修复候选交接，等待 S0/R1 独立复审，不自行签 G1 通过或合并 main。

- 共享生产 base：`37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`；契约 plan-v0.1 / coordination.v1 / toolalign.contracts.v1。
- 修复前候选：`59b3802c81aa6eceaf3609af88f288756bcb1581`；原 FAIL：`ac6bdf78d57c6753865a24a1d216b90dc4478646`，8 个审查文件不变。
- S0 授权：`a0a800b2a544cb25e7eccad2dce12173acc77ea1`；原审查通过非强制 merge `f020046055717f4fc5a821a61fb2664d989e6875` 接入。
- 已测修复实现/测试/F3 提交：`5c32e8a72e957df100691e0096d1413eed8ce8f9`。最终完整候选为含本交接的后续证据提交，完整 SHA 由 T1 原生回报；实现与归档内容未再调整。
- 已读授权 AGENTS、P01 任务、PROTOCOL、PROJECT_STATUS、原 R1 报告/证据/反例及冻结契约；本轮不合并无关 P02 实现。

## 逐项修复

| 问题 | 本轮实现和证据 |
|---|---|
| F1/P1 | 监控异常先可靠回收自有 child，再保存异常、真实 child 退出码、resources 和 failed/ended_at manifest，最后传播原异常。未知压力不会当正常；原 R1 两种异常现均保留退出 1 / child -9 与终态。新增压力超时/预算/取消/成功/worker 退出 2/无关 child 保护验证 |
| F2/P1 | 上游已执行的第 8 微步/optimizer 更新先入日志与 progress，再传播 ln(2) 失败；原 R1 反例现在记录 40 总微步/5 总更新、404 监督 token、1006 处理 token及真实失败 loss。非有限值以标准 JSON 的 null + 类别保存；门槛仍为逐步 2e-6 |
| F3/P2 | math-r2 原 HEAD aaab75e 与实际工作树分开说明；8 份源码 hash 映射到47c0340，原配置、source hash 与历史制品未改 |

实际运行顺序解释：DPO loss 属于更新前评分，但回调在上游更新后才收到它；发现失败不能将已经发生的更新计成零。reference 仍须绑定 SFT 参数，未借本修复改变 reference、mask、数学、编译或训练配置。

## 交付与验证

- [修复报告](../../reports/hardware/P01_FIX_R3_REPORT.md)：问题、验证、失败及 NOT_RUN。
- [验证索引](../../reports/hardware/P01_FIX_R3_VALIDATION.json)：实际命令、退出码、原始日志 hash、每基线 diff/完整文件清单、代码/证据/包 hash。
- [来源映射](../../reports/hardware/P01_FIX_R3_SOURCES.json)：math-r2 全部 8 份源码的工作树/HEAD/可恢复提交比对。
- [新增默认 CPU 回归](../../tests/training/compatibility/test_failure_accounting.py)、[失败汇总检查](../../reports/hardware/P01_FIX_R3_REPORT_TESTS.py)、[当前包与隔离安装核验](../../reports/hardware/P01_FIX_R3_PACKAGE.py)。

完整适用 CPU 回归 **235 通过**，原 R1 探针加报告检查 **10 通过**，合计245个不同pytest检查；原 R1 独立 CPU 数学17组通过。修复前同一未修改 R1 探针的4通过/3失败日志保留，修复后7通过；不重复累计开发中运行。lint、冻结、公开扫描均退出0。原 shared01 旧57项结构快照未改、未计入当前通过。

关键原始日志 SHA-256：

| 命令标识 | 退出码 | 原始日志 SHA-256 |
|---|---:|---|
| fix-r3-before-r1 | 1 | `9a72a5d40e46803e8276d5ff41f5b1bf59b17b8eec17639c70a2b82cd286ccb7` |
| fix-r3-full-cpu | 0 | `c79aacc6ff80eaee075f51a58d3585b1264b971fe34641f85b3bf92a0a2253b9` |
| fix-r3-final-r1-probes | 0 | `a5013ca3f620c4c2960168f527d6773e1d802a531a175690f55a692aa6a0ece1` |
| fix-r3-r1-cpu-math | 0 | `17307b5921a3e9089effd2d824e287b872ce23ea8e2a0b0fe6522f3cea8cc26e` |
| fix-r3-build | 0 | `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75` |
| fix-r3-package | 0 | `06cc35c40bab12ea778231d3cbed48024fb9c04394d108b08636090a079ee6b3` |

本轮新 sdist/wheel 的 SHA-256 为 `024126435a5065ddae8e12c86272cc530ed4a8ae09eddd1fa2b0b0916d6ccf2e` / `941a1efb88b48cb8479ec9b5869c4db90984fd266e209933ef128b0792fa34e1`。全部源码成员与追踪字节一致；分别47/22项，未追踪payload为0；8个P01模块/schema完整。默认CPU隔离安装的13项子命令均通过。新的包 hash 不套用原 R1 审计的旧归档预期。

历史10个run/185项manifest制品只读重验，重建摘要与原文件逐字节一致，SHA-256 `d0fb9deb067b1e3f6f8b85855a0d1509b3bc15569065bbfed22a5c95928f42bd`。原 P01-r1/P01-base-r2 交接、R1 FAIL/原始反例、首选与备选失败、pressure停止及旧证据均保留。

相对 ac6bdf7 仅本轮授权路径变化；相对59b3802另外保留8份原 R1 新文件；相对37c00de的完整包差异含原P01交付和来自S0的旧协调同步，不能将那些公共差异归为本轮新修改。所有完整名称清单/统计见验证索引。公共依赖/契约/锁/配置/协调文件与原审查候选相同，原候选159个未修改文件已逐字节核验。

## 限制与下一步

复用已有锁环境，只做CPU；惰性测试child和临时安装环境均已回收。新增私有证据与归档为小型文件，预算2GiB；没有模型下载、MLX/模型导入、GPU作业或OS限制调整。没有触发需要另行GPU复现的具体疑点。

**NOT_RUN**：本轮GPU/完整math重放与故障注入，P04/P05正式训练、accepted_sft reference、kris token/mask人工核对、正式偏好生成、完整harness/256-token协议、最终测试/BFCL、长时稳定性及服务部署。模型历史通过不等于本轮代码的GPU实测；CPU自测也不等于独立验收。

T1提交并非强制推送该完整候选后结束本轮，等待S0安排R1复审。只有S0决定集成与后续阶段授权。
