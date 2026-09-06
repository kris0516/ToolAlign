# P01-fix-r4 · 启动初始化定点修复交接

2026-09-06；T1，gpt-6-astra / max；`work/p01-compatibility`。已交修复候选及CPU自测证据，等待S0/R1独立验收。

| 身份 | 精确SHA |
|---|---|
| 生产base | `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` |
| 原完整候选 | `ac8095faa58a98e143a8dc4d63042093e426feb0` |
| 原R1-r2 FAIL | `aaae5a4395dbdd73fd487f80174599ffd3ef9be3` |
| S0授权 | `cbb6d4614c3b8e8f584315ac3bdad434544c3984` |
| 非强制merge原review | `65437ea2323f21e6c4c1d7e5b916282209dbd25a` |
| 修复实现/回归 | `2efc7a55ea0dcc77a97cd7f5a82e95515c32de00` |

最终完整候选为包含本交接的后续证据提交，完整SHA由T1原生回报；实现、测试及包内容未再改变。已读取并私有保存授权AGENTS/P01/PROTOCOL/PROJECT_STATUS/GOAL，契约仍为plan-v0.1 / coordination.v1 / toolalign.contracts.v1。真实任务/worktree身份已核对，没有合并无关main/P02。

唯一R2-F1修复：将running尝试之后的环境准备、初始swap、stdout打开及Popen统一纳入收尾。没有child时不执行进程回收，保存`child_started=false`、真实child退出null、准确缺测与failed/ended_at，再抛原异常对象；不生成未执行的token/更新。已启动child的运行期监控错误仍保留实际退出和已完成工作。报告新增FAILED_INITIALIZATION和失败阶段，未测RSS/swap增长/pressure为null，已测0基线仍为0。

原始两个R1初始化反例在修复前 **2失败/20未选**，修复后全部通过；分别0/1次Popen调用、实际child均0，汇总从遗漏变为明确的failed尝试。原七项与新22项未修改探针 **29通过**；完整CPU/报告 **251通过**，合计 **280个不同pytest检查**。新增13项回归已包含在251中，开发重复运行不累计。正常wait、运行期错误、预算/取消、租约和首次RSS前实际child回收均有对应检查。lint/冻结/公开扫描退出0。

交付：

- [修复说明](../../reports/hardware/P01_FIX_R4_REPORT.md)：实际行为、测量缺失语义、失败与限制。
- [验证索引](../../reports/hardware/P01_FIX_R4_VALIDATION.json)：每条实际argv/源码HEAD/退出码/完整log hash、before/after观察、范围与历史身份、归档和安装证据。
- [原创启动回归](../../tests/training/compatibility/test_initialization_failures.py)与[报告检查](../../reports/hardware/P01_FIX_R4_REPORT_TESTS.py)。
- [当前Git归档/隔离安装检查](../../reports/hardware/P01_FIX_R4_PACKAGE.py)和[安装后启动/报告接口探针](../../reports/hardware/P01_FIX_R4_INSTALLED_PROBE.py)。

关键原始日志hash：before-init `f41beaf1db1bae1bb4b7b2d43c5fee540ad115bb3754d542fff89f79649e72fb`（exit1）；full-cpu `13411338f82daf738ceefeaaa09e7a0d9c08d7d8d5641d99dcc6718328195398`、final-r1 `33654704eebe886ac35b8d5e9779daf9f56b55b708f3c249d34bfa70de139efa`、package `baebad94cef638c6d304c70d0c4dfa39af8bd235d348a823273f7dcfdf5d41bf`（均exit0）。其余完整日志hash及原始观察文件hash见验证索引。

本轮真正离线新建sdist，随后**从该sdist生成wheel**：sdist116086bytes/49文件/48追踪项，SHA `649b0f757e321294f0a0b193d35c17f3e6785de831e69820e4a413df65241777`；wheel44830bytes/27文件/22追踪项，SHA `7c83931ab70668727f824df340ded0ce0530779d9058b8a3c4846aa1f4364ae2`。全部payload与当前Git及工作树逐字节一致、未知载荷0、八模块/schema齐全。本轮未跑直接wheel构建。14条隔离安装及接口命令通过，原始stdout/stderr均保留；其中实际启动失败和报告探针使用安装后的execution与已核对的checkout报告脚本。

相对aaae5a4仅九个允许文件；相对ac8095f另外六个文件就是原R1-r2审查。174个原review候选文件逐字节未变，包括原R1/fix-r3/各旧交接；公共依赖/锁/契约/配置/协调、fallback/core/numerical/model_probe/samples等只读文件保持。完整diff名称清单见索引。

历史身份已核对：原P01_RESULTS SHA仍为 `d0fb9deb067b1e3f6f8b85855a0d1509b3bc15569065bbfed22a5c95928f42bd`，十次历史run的已登记配置/manifest/摘要证据hash绑定不变；185项历史载荷与17组数学引用精确R1-r2独立证据，**本轮未重跑/全量重哈希**。F2/F3关闭及全部旧FAIL、模型/编译/pressure负结果原文保留。

仅CPU、离线复用原锁环境；私有新环境/制品实际快照低于2GiB，见索引。未运行MLX/模型/GPU、训练tokenizer、Torch数学、权重/新依赖下载或OS调整；P04/P05、accepted_sft、人审、完整真后端256-token、最终测试/BFCL、长期性能和部署均NOT_RUN。没有对全面不可写磁盘增加落盘保证。

T1提交并非强制推送已有分支后结束本轮，等待S0安排新完整候选的独立R1复审；不自行验收、合并或扩展训练范围。
