# T1_TRAINING｜独立对话分发词

**未分发模板。** S0 发送前在下表填真实值；没有原生独立线程工具时，由 kris 新建独立对话并粘贴。禁止用 sub-agent 替代。

| 字段 | 值 |
|---|---|
| TASK_ID | 待S0填 |
| BASE_COMMIT | 待S0填真实SHA |
| BRANCH / WORKTREE | 待S0填本机实际位置（私有映射不公开） |
| TASK_PACKET | 待S0填对应coordination/tasks文件 |
| ACCEPTANCE_COMMANDS | 任务包中确认过的实际命令 |

> 你是 ToolAlign 的 T1 训练独立对话。只执行 S0 指定的 P01/P04/P05 当前任务，不自行跨阶段。先读 AGENTS.md、训练规格、Mac资源方案和GPU锁协议。先做数值/reference/模板/保存加载测试，再申请GPU运行。不得把disable adapter等同SFT reference；不得用第三方速度填本机数据。交真实run manifest和commit，不合并main。
>
> 若任务/commit/依赖/目录不符，报告具体阻塞而不是扩大范围。读取文档后先复述实际领取范围与验证计划，然后执行该包。所有结论保存到版本化交接文档，不能只留在聊天里。
