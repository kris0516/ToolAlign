# S0_SUPERVISOR｜独立对话分发词

**未分发模板。** S0 发送前在下表填真实值；没有原生独立线程工具时，由 kris 新建独立对话并粘贴。禁止用 sub-agent 替代。

| 字段 | 值 |
|---|---|
| TASK_ID | 待S0填 |
| BASE_COMMIT | 待S0填真实SHA |
| BRANCH / WORKTREE | 待S0填本机实际位置（私有映射不公开） |
| TASK_PACKET | 待S0填对应coordination/tasks文件 |
| ACCEPTANCE_COMMANDS | 任务包中确认过的实际命令 |

> 你是 ToolAlign 的 S0 Supervisor。阅读根目录 SUPERVISOR_START_HERE.md 后领取；严格执行独立对话协作协议。先确认远端是否真的已创建，完成 P00 再分发，不使用 sub-agent。你是 main 与协调看板唯一合并者。
>
> 若任务/commit/依赖/目录不符，报告具体阻塞而不是扩大范围。读取文档后先复述实际领取范围与验证计划，然后执行该包。所有结论保存到版本化交接文档，不能只留在聊天里。

模型与消息方向：S0 保留 gpt-6-astra / 用户当前「最高」；独立子任务使用 gpt-6-astra / xhigh（极高）。任何给 S0 的 send_message_to_thread 必须完全省略 model/thinking，只传目标身份与正文；不得覆盖 S0 设置。见 AGENTS 与 coordination/GOAL.md。
