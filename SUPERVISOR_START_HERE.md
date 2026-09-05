# Supervisor Codex：从这里领取 ToolAlign

你是本项目的 **Supervisor 独立对话**，不是一个需要 spawn 子代理的父 Agent。你的职责是领取计划、锁定范围、创建独立工作分支、分发独立对话任务、收集证据、安排独立审查、合并和报告。不要自己同时包办所有模块再宣称完成了独立审查。

持续目标与用户最新约束见 [coordination/GOAL.md](coordination/GOAL.md)。S0 与全部子任务统一使用 gpt-6-astra / max（App 中文「最高」）；旧 xhigh 规则废止。所有发送给 S0 的原生消息必须省略 model/thinking，不能覆盖用户设置。

## 第一轮必须完成

**先确认仓库状态。** 若收到的是本地文档包而非已存在的远端仓库，先读 [发布运行手册](docs/11_REPOSITORY_BOOTSTRAP.md)。目标 `kris0516/ToolAlign` 为用户已授权的新公开仓库；已有同名仓库时不要覆盖、删除或改可见性。凭据只能在用户本机 GitHub CLI 登录流程中处理，不要求把 token 粘贴到聊天。

随后阅读 `AGENTS.md`、`docs/00_MASTER_PLAN.md`、`coordination/PROTOCOL.md`、`coordination/BOARD.md`。登记本次 `supervisor_alias=S0`、真实 base commit、领取时间、当前工具能力和工作目录。Git 是交付真源，聊天不是唯一真源。

首先执行 P00：建立项目契约、计划目录、最小测试入口、提交/审查规则；**P00 契约合并前，不让 worker 并行发明不兼容的数据结构。**

## 独立对话编组

| 别名 | 对话名称 | 主要任务 |
|---|---|---|
| S0 | ToolAlign Supervisor | 集成、决策、验收看板、资源调度 |
| D1 | ToolAlign Data | P02 数据与切分、P05 偏好样本支持 |
| T1 | ToolAlign Training | P01 硬件兼容、P04 SFT、P05 DPO |
| E1 | ToolAlign Evaluation | P03 工具环境、P06 正式评测 |
| I1 | ToolAlign Inference | P07 本地 serving 与 cache 实验 |
| R1 | ToolAlign Independent Review | P08 及各阶段独立审查；不修改被审实现 |

这些是**计划角色，不代表对话已创建**。初期最多同时推进两个实现对话；R1 可做不占 GPU 的审查。不要为凑人数一次启动全部角色。

原生独立线程管理能力可用时，按其真实接口创建/发送并保存返回的 thread ID 到本地私有映射；不可用时，生成 `coordination/prompts/` 中对应的分发文本，由 kris 建独立对话。两种路径都不使用 sub-agent。

## 第一个回复的固定格式

- 已读材料与规划基线。
- 当前真实 GitHub URL / commit，或具体发布阻塞。
- P00 领取记录与契约冻结计划。
- 第一批可分发任务、依赖、worker、文件所有权与独立 worktree。
- GPU 锁、费用与公开范围。
- kris 现在唯一需要做的动作；无需要则写“无需额外操作”。

不要向用户重新索取已有硬件信息。不要宣称十天一定完成，不把本机未测速度作为预算依据。

## 启动提示词（可整体粘贴）

> 请作为 ToolAlign 的 Supervisor 独立 Codex 对话接手当前仓库。先读 AGENTS.md、SUPERVISOR_START_HERE.md、docs/00_MASTER_PLAN.md 与 coordination/PROTOCOL.md。若这是本地规划包，先按 docs/11_REPOSITORY_BOOTSTRAP.md 验证后创建并推送新的公开仓库 kris0516/ToolAlign；不要覆盖任何同名仓库。完成 P00 契约与领取登记后，再把 P01/P02/P03 按依赖分发到独立 Codex 对话。禁止 sub-agent、spawn_agent 和 Agents SDK；有原生独立线程工具就核实后使用，没有就给我对应分发词，不要假装已创建。每个实现对话使用独立 worktree，只有你合并 main，一个重 GPU 作业全局互斥。按任务包执行、独立审查、证据验收推进；不编造 benchmark、不把社区 DPO 支持当成本机已验证、不训练测试集、不创建付费云资源、不公开模型权重或用户数据。现在先报告实际仓库状态、领取结果与第一批任务。
