# 17｜技能分工与热门技能取舍

2026-10-26 查阅 [skills.sh All Time 排行](https://skills.sh/)。下表取当次页面前 10，数值为平台展示的累计安装量；它不是独立质量评测，也不是“本日新增”。[Hot 页面](https://skills.sh/hot)变化很快且前列包含低计数钱包/抓取/应用框架项，不用瞬时热度替换研究工作流。

| 排名 | Skill / 展示安装量 | ToolAlign 取舍 |
|---|---|---|
| 1 | find-skills / 4.0M | 有明确能力缺口时可查；已有内置发现工具，暂不重复安装 |
| 2 | grill-me / 1.4M | 适合用户主动要求设计问答；当前不装，避免每任务反复追问 |
| 3 | agent-browser / 1.2M | 网页操作有用；已具备浏览器工具，暂不另装 CLI |
| 4 | hyperframes-cli / 1.2M | 视频制作，与当前训练迁移无关 |
| 5 | grill-with-docs / 1.2M | 文档驱动设计问答；现有研究入口和 ADR 已覆盖，不新增依赖链 |
| 6 | hyperframes / 1.2M | 视频制作，不加入训练技能组 |
| 7 | improve-codebase-architecture / 1.2M | 广泛架构改造超出本轮；其并行 sub-agent 方式不适用于本项目 |
| 8 | tdd / 1.1M | 采纳面向公开行为的回归测试原则；原版逐项确认要求不作默认流程 |
| 9 | media-use / 1.1M | 媒体工作流，当前不需要 |
| 10 | reddit-automation / 1.1M | 社区内容自动化，当前不需要 |

具体审阅了 [grill-me](https://skills.sh/mattpocock/skills/grill-me)、[grill-with-docs](https://skills.sh/mattpocock/skills/grill-with-docs)、[架构技能](https://skills.sh/mattpocock/skills/improve-codebase-architecture)及 [tdd](https://skills.sh/mattpocock/skills/tdd)。结论是复用已装能力，补充真正缺失的 Colab 操作知识，不按榜单批量安装。

## 本项目实际使用

| 场景 | 本地 skill | 使用边界 |
|---|---|---|
| 每个新/接续任务 | avoid-overkill | 首先读取；抑制无依据防御、重复验证与流程膨胀 |
| 阶段盘点、研究接续 | paper-research-workflow | 已补 ToolAlign 项目指引；按需选择下列技能 |
| Colab 接入、训练作业、恢复 | colab-remote-training | 本次新增；复用官方 CLI 与已有本机配置 |
| 实验就绪和运行边界 | experiment-readiness | 代码、环境、容量、恢复、正式结果分别登记 |
| 具体 bug / 失败 | systematic-debugging | 先复现和定位，不为假想故障建立流程 |
| 声称通过、提交/交付 | verification-before-completion | 本次调整为与改动风险相称；可复用相同未变版本证据 |
| 文献与来源 | literature-evidence | 核验原文及新颖性，不凭记忆写结论 |
| 消融与组件归因 | research-factorial-design | 需要比较组件贡献时使用 |
| 不确定性与统计 | research-statistical-analysis | 明确独立单位、效应、配对及区间 |
| 论文叙述 | ml-paper-writing | 依据真实实验结果写作 |

theory-audit、research-peer-review、brainstorming-research-ideas 和格式类插件按需使用。法律、PhysicsNeMo 及其他项目技能保留，不因当前项目不用就卸载。

本机 skill 根的 `SKILLS_INDEX.md` 给出分组；全局 AGENTS 已要求每对话先读 avoid-overkill。修改前的三个指令文件有本机备份。本轮未新增通用技能市场工具，也未启动 Colab。
