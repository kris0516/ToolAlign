# <TASK-ID>｜任务包

状态：READY / CLAIMED / BLOCKED（由 S0 登记）

- owner alias：
- base commit：必须是实际完整 SHA
- branch / worktree：
- contract versions：
- 依赖与输入 artifact：
- 目标：
- 明确非目标：
- 允许修改文件：
- 禁止修改文件：
- 输出与 schema：
- GPU/内存/费用预算：
- 验收命令及预期：未实现的命令标记 PLANNED
- 正向测试：
- 负向/边界测试：
- 人工检查点：
- 交接路径：`coordination/handoffs/<TASK-ID>-r1.md`
- 阻塞与降级：

领取前确认没有另一 owner，不得自行改 shared contract。

模型与消息方向：S0 与全部独立子任务统一 gpt-6-astra / max（App 中文「最高」）。旧 xhigh/极高要求已废止。给 S0 的普通 send_message_to_thread 回报完全省略 model/thinking，只传目标身份与正文，保留 max。见 AGENTS 与 coordination/GOAL.md。
