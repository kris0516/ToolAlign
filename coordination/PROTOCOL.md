# 独立 Codex 对话协作协议

协议版本：coordination.v1。优先级：用户明确约束与 AGENTS.md → 冻结契约/ADR → 已发任务包 → 临时聊天。发现冲突先由 S0 记录解决，不让 worker 自行扩大范围。

## 1. 角色与权力

kris 是项目负责人，决定范围、费用、隐私、外部发布和学习目标。S0 是单一协调者，拆包、登记、分发、合并、检查证据。D1/T1/E1/I1 是独立实现对话。R1 是独立审查对话，不批准自己的代码。

“独立”要求每个对话可单独打开，有自己的上下文和工作区；不是同一个聊天内部扮演多个角色。禁止 sub-agent/Agents SDK/spawn_agent。

## 2. 能力发现与分发

S0 首先确认是否有**原生独立对话/线程**创建、消息、状态读取工具，以及这些工具是否真的创建 App 中可见的独立对话。没有这些工具时，不试图用 CLI 后台进程或嵌套代理代替；把 `coordination/prompts/` 的对应提示词填好后交由 kris 新建对话。

所有 worker/reviewer 的原生创建与后续消息统一指定 `model=gpt-6-astra`、`thinking=xhigh`（极高）。最多两个同时活跃的实现对话；R1 CPU 审查可独立进行。

原生工具调用成功返回 thread ID 才登记 `DISPATCHED`。只生成了 prompt 记作 `READY_FOR_MANUAL_DISPATCH`。用户手动建立后记录 alias，敏感 thread ID/本机绝对路径存 `.toolalign-local/`，不公开聊天全文。

App 创建 worktree 若只返回临时 client ID，保持等待设置状态，不能把它传给要求真实 thread ID 的工具。新对话先通过原生 `set_thread_title` 设置自身标题，将返回的真实 ID、角色、模型、推理等级与 cwd 写入自身 `.toolalign-local/task-identity.json`；S0 核对后登记并使用原生 wait/send。任务列表短暂不显示新对话时不重复创建，也不启用 CLI 后台代理。

分发区分 `code_base` 与 `authorization_commit`：前者是已合并并验证的代码基线，后者是 S0 写入领取状态/范围的精确协调提交。Worker 在切换基线前读取授权提交中的任务包，并保留私有副本；不能因为代码基线内任务包仍为未领取就自行改变授权。

## 3. 任务领取与状态机

`PLANNED → READY → CLAIMED → IN_PROGRESS → READY_FOR_REVIEW → ACCEPTED → MERGED → VERIFIED`。

审查不通过走 `CHANGES_REQUESTED`，缺外部前提走 `BLOCKED`；明确取消走 `CANCELLED`。不把 blocked 当 done。

S0 是 BOARD/PROJECT_STATUS/DECISIONS 的唯一写者。任务从 READY 变 CLAIMED 时写 task ID、worker alias、base commit、允许文件、分支、验收与预算；同一任务不能同时分给两个 worker。Worker 读取实际授权 commit，不能靠过期聊天开始。

一个 worker 的交接单只写到自己 `coordination/handoffs/<TASK>-<rev>.md`；它不直接修改其他人的状态。S0 基于最新 main 集成，避免不同分支都“抢到了任务”的假象。

## 4. 每包工作契约

任务包必须包含：目标、非目标、依赖、输入/输出契约、base commit、允许改动路径、禁止改动路径、需要的资源、验收命令、负向测试、交接文件名、阻塞时方案。

模板在 [templates/TASK.md](templates/TASK.md)。规划任务包里的 base commit 初始为 UNASSIGNED；S0 分发时必须填真实 SHA。测试命令如尚未实现，必须标计划命令，不能当成已跑证据。

## 5. worktree 与分支

所有 worker 从 S0 指定的已合并 commit 出发。创建命令示意：

```bash
git fetch origin
# <BASE_COMMIT> 必须由 S0 用真实 SHA 替换；新目录不得已存在。
git worktree add -b work/p02-data ../ToolAlign-P02 <BASE_COMMIT>
```

每个独立对话只打开自己的 worktree；不在同一工作目录共享 checkout。Codex App managed worktree 可以使用，但 S0 必须核对实际 branch/commit，而不是假定 App 创建的 detached HEAD 已关联分支。[S03/S16，见 docs/09_SOURCES.md]

worker 不执行其他 worktree 的 git reset/clean/stash，不 force push main，不删除未合并工作。依赖更新/公共 schema 修改向 S0 提出 request，由 S0 合并后发布新的 base。

worktree 是版本控制隔离，不是 OS 安全沙箱；脚本、数据和凭据权限仍需单独限制。

## 6. 冲突和集成

公共 contracts、lock files、顶层配置与协调文件由 S0 所有。两个 worker 都需要同一改动时，S0 先出最小公共变更，不能让它们各自复制一份不兼容类型。

worker 通过 PR（远端权限可用）或精确 commit/branch 交接。R1 对待合并 diff 复核后，S0 用非强制方式合并；集成后再跑关键测试，只有这个 commit 可作为下一任务的输入。

如采用 cherry-pick，记录来源 commit 与集成后 commit 的映射；不谎称二者 SHA 相同。工作未提交不能作为完成证据。

## 7. 资源调度

正式模型任务先申请 GPU 租约，见 [RESOURCE_LOCK.md](RESOURCE_LOCK.md)。数据清洗和纯 CPU 测试可并行；大规模 PyTorch CPU 作业也须考虑内存预算。默认两个实现任务活跃，不等于两个 GPU 训练活跃。

跨库 DPO 迁移、长序列、模型下载、缓存清理须提前登记预计占用。自动过期时间不是杀死未知进程的授权。

## 8. 独立审查

R1 读取 diff、运行必要测试、抽查原始证据和负向场景。R1 可新增独立复现说明/审查用小测试，但不能偷偷修实现后再以“原代码通过”验收。

审查输出固定为 PASS/FAIL/BLOCKED，并分 P0/P1/P2 说明。P0 未关闭不合并。非阻断建议不要求无限追求完美，避免把十天项目扩展成平台工程。

## 9. 中断与交接

对话失联/上下文耗尽时，最后已提交的 handoff、run manifest、BOARD 和 ADR 是恢复入口。S0 重新指派前确认上一 worker 没有正在运行的 GPU 作业，保护未合并 commit。新对话不能假定共享旧对话记忆。

## 10. kris 的参与

每日 S0 发一段状态简报：今天已验收什么、阻塞是什么、关键实验数字来自哪里、下一步是什么，以及最多一个需要 kris 决定的问题。既定约束不重复询问。

kris 负责数据语义抽查、关键算法讲解和范围确认；本机需要授权/登录时由本人完成。S0 不自动接受外部数据条款，不索取聊天中的 secret，不创建付费资源。
