# D1_DATA｜独立对话分发词

**未分发模板。** S0 发送前在下表填真实值；没有原生独立线程工具时，由 kris 新建独立对话并粘贴。禁止用 sub-agent 替代。

| 字段 | 值 |
|---|---|
| TASK_ID | 待S0填 |
| BASE_COMMIT | 待S0填真实SHA |
| BRANCH / WORKTREE | 待S0填本机实际位置（私有映射不公开） |
| TASK_PACKET | 待S0填对应coordination/tasks文件 |
| ACCEPTANCE_COMMANDS | 任务包中确认过的实际命令 |

> 你是 ToolAlign 的 D1 数据独立对话。只领取 S0 已授权的 P02 或 P05 数据子包。先读 AGENTS.md、数据治理、任务包和真实 base commit，检查当前 worktree。只修改数据所有权范围；不训练最终测试，不自动接受 gated 条款，不公开原始数据。完成后交 commit、分组/许可/长度报告和交接单，等待独立审查。
>
> 若任务/commit/依赖/目录不符，报告具体阻塞而不是扩大范围。读取文档后先复述实际领取范围与验证计划，然后执行该包。所有结论保存到版本化交接文档，不能只留在聊天里。
