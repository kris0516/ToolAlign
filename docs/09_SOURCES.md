# 09｜一手来源与核实边界

核实日期：**2026-09-06**。网页可访问、项目 README 声称支持和本机验证成功是三种不同状态。本文件只确认来源内容；依赖/model/data 的具体 revision 由 P01/P02 锁定，不能把 `main` 当永久可复现版本。

| ID | 一手来源 | 用途与限制 |
|---|---|---|
| S01 | [MLX-LM 官方仓库](https://github.com/ml-explore/mlx-lm) | 推理、量化与 prompt-cache 能力入口；不是本机性能证据 |
| S02 | [MLX-LM LoRA 说明](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md) | LoRA/量化 LoRA、数据与训练配置；恢复语义需查实现 |
| S03 | [Codex worktrees](https://developers.openai.com/codex/app/worktrees) | 独立 Git worktree 工作流；不据此假定 supervisor 有线程控制工具 |
| S04 | [Team-ACE/ToolACE 数据卡](https://huggingface.co/datasets/Team-ACE/ToolACE) | 上游标注 Apache-2.0；保存下载时实际版本和条款 |
| S05 | [Salesforce/xlam-function-calling-60k 数据卡](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k) | 标注 CC-BY-4.0，有访问条件确认；不是首期强依赖 |
| S06 | [Qwen3-1.7B 模型卡](https://huggingface.co/Qwen/Qwen3-1.7B) | 模型身份、模板与 non-thinking 配置；不叫同名 Base 模型 |
| S07 | [Qwen3-0.6B 模型卡](https://huggingface.co/Qwen/Qwen3-0.6B) | 小模型对照，必须独立锁定 tokenizer/revision |
| S08 | [mlx-tune 维护者仓库](https://github.com/ARahim3/mlx-tune) | 社区 DPO 候选；README 声称支持不替代数值/硬件验收 |
| S09 | [mlx-lm-lora 维护者仓库](https://github.com/Goekdeniz-Guelmez/mlx-lm-lora) | 社区备选；只允许一次受控切换，避免无休止迁移 |
| S10 | [DPO 原论文](https://arxiv.org/abs/2305.18290) | 偏好优化理论来源 |
| S11 | [TRL DPO Trainer 官方文档](https://huggingface.co/docs/trl/dpo_trainer) | reference、数据和 loss 实现核查入口；不自动等于 MLX API |
| S12 | [BFCL 官方入口](https://gorilla.cs.berkeley.edu/leaderboard.html) | 固定官方 evaluator/data，标注子集；不宣称完整榜单成绩 |
| S13 | [QLoRA 原论文](https://arxiv.org/abs/2305.14314) | 与 MLX 实际量化 LoRA 的工程区别需要明示 |
| S14 | [MLX Metal 官方文档](https://ml-explore.github.io/mlx/build/html/python/metal.html) | 设备与内存 API 版本核查 |
| S15 | [MLX-LM generate 源码](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/generate.py) | KV/draft-model 等参数支持检查，收益需实测 |
| S16 | [Git worktree 官方文档](https://git-scm.com/docs/git-worktree) | 工作目录隔离，共享 Git 元数据，不等于权限沙箱 |
| S17 | [Codex AGENTS.md 官方文档](https://developers.openai.com/codex/guides/agents-md) | 仓库指令发现入口，不让单个文件无限增长 |
| S18 | [GitHub CLI repo create](https://cli.github.com/manual/gh_repo_create) | 本机创建用户指定的新公开仓库 |
| S19 | [LoRA 原论文](https://arxiv.org/abs/2106.09685) | 低秩适配的理论与实现讨论 |

## 本方案主动避免的未经证明假设

不把此前回答里的单卡训练时间或推理 tok/s 当成本机训练数据；不以其他型号 benchmark 按 GPU 核数线性换算。没有实际租用/运行 NVIDIA GPU，不声称 CUDA、多卡或 DeepSpeed 项目经验。

不把官方 LoRA 说明当作官方 DPO 支持证明；不把社区项目标记 stable 当作本机兼容。也不把公开 BFCL 数据天然当作“保证底座从未见过”的无污染数据。

不引用未经核实的面经通过率、岗位匹配分数作为项目验收依据。本项目面向可检验工程与学习结果，不预测录取概率。

## 来源变更记录

Supervisor 每次升级依赖或数据时，在 `coordination/DECISIONS.md` 登记新版本和回归结果；旧报告仍保留旧来源身份。访问失败、许可疑义或无官方说明时，标为 unresolved，不用搜索摘要补造结论。
