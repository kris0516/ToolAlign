# I1_INFERENCE｜独立对话分发词

**未分发模板。** S0 发送前在下表填真实值；没有原生独立线程工具时，由 kris 新建独立对话并粘贴。禁止用 sub-agent 替代。

| 字段 | 值 |
|---|---|
| TASK_ID | 待S0填 |
| BASE_COMMIT | 待S0填真实SHA |
| BRANCH / WORKTREE | 待S0填本机实际位置（私有映射不公开） |
| TASK_PACKET | 待S0填对应coordination/tasks文件 |
| ACCEPTANCE_COMMANDS | 任务包中确认过的实际命令 |

> 你是 ToolAlign 的 I1 推理独立对话，只领取 P07。读 AGENTS.md、架构、Mac资源与部署路线。实现受限loopback API、有限队列/预算/取消、exact-prefix缓存与失效，不公开服务，不抢占训练GPU，不在普通Linux Docker中假设Metal可用。先固定模型与口径测cold/warm，投机解码不在本包。交测试、实测条件、风险和commit。
>
> 若任务/commit/依赖/目录不符，报告具体阻塞而不是扩大范围。读取文档后先复述实际领取范围与验证计划，然后执行该包。所有结论保存到版本化交接文档，不能只留在聊天里。

模型与消息方向：S0 与全部独立子任务统一 gpt-6-astra / max（App 中文「最高」）。旧 xhigh/极高要求已废止。给 S0 的普通 send_message_to_thread 回报完全省略 model/thinking，只传目标身份与正文，保留 max。见 AGENTS 与 coordination/GOAL.md。
