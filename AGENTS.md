# ToolAlign — 工作指令

当前路线：2026-10-26 Colab 交接版。默认解释语言中文，代码/接口名英文。接续入口：[toolalign.md](toolalign.md)。

## 每次开始

- 每个新对话或接续任务必须先实际读取并应用本机 `avoid-overkill/SKILL.md`，默认位于 `${CODEX_HOME:-$HOME/.codex}/skills/avoid-overkill/SKILL.md`。代码、实验、研究、审查与写作尤其遵守：工作与结果/证据成比例，不添加猜想驱动的防御代码，不反复重跑已通过且未受影响的检查。
- 读 [PROJECT_STATUS](coordination/PROJECT_STATUS.md) 与当前范围，按需读证据。旧任务包、reports 和 ADR 是历史，不自动产生新运行授权。
- 研究结论先给具体发现及下一决定。未支持预想结果时报告确切结果和下一项有区分力的验证，不能编造提升或隐去反证。

## 运行与协作

- 后续训练、偏好生成、模型容量检查和批量模型评测使用 Colab GPU；Mac 做开发、CPU 测试、远程控制和分析。优先 L4 24GB，不够用 A100 80GB，先估算、后一次短容量验证。见 [Colab 工作流](docs/16_COLAB_WORKFLOW.md)。
- 当前 Supervisor S1 和全部 worker/reviewer 一律 `model=gpt-6-astra`、`thinking=max`（最高）；旧 xhigh 指令失效。
- 仅用独立 Codex 对话与隔离 worktree，禁止 sub-agent。最多两个实现任务并行，R1 可独立 CPU 审查；一个活动重 GPU 作业。普通回报省略模型参数以保持已有设置。
- 实现者交付精确提交，R1 审核，S1 合并与验证。S1 独占 BOARD/PROJECT_STATUS/DECISIONS 的状态维护，共享契约与依赖由 S1 协调。S0 已交班，仅只读答疑；历史文档中 S0 的协调职责由 S1 承接，原审核身份不改写。
- 后续原需人工参与的语义、偏好与最终说明审核由独立 Q1 AI 承接，不等待 kris 填表/签字/答辩。保留真实审核身份和失败历史。同问题连续第 5 次正式修订未通过才整体暂停，第 1–4 次自主整改，见 [REVIEW_POLICY](coordination/REVIEW_POLICY.md)。
- 既有 Colab 资源使用不等于购买/充值授权。远端只处理训练所需已批准数据；公开仓库禁止凭据、私人聊天、原始数据、模型权重与本机任务身份。

## 当前完成与接续

P00 契约、P01 Mac 兼容历史、P02 冻结 v3 质量、P03 CPU 执行器及 P04 CPU/MLX toy/固定模型接口均有独立证据。PR19 合并为 `abdc53d468a270cc1bfecbe56980dd34918480e1`，main 定点检查 163 passed；正式 SFT/DPO/模型评测/服务仍 NOT_RUN。下一步新建 P04 CUDA 适配任务，不恢复旧 Mac runtime 任务。

PR20 交接文档已合入 `61c2176d556fd0e4cfc2af00b16242dddcfadfd3`，生产代码保持 PR19。2026-10-26 用户指定 Toolalign Supervisor S1 接班并继续 P04 CUDA；按 [分组目标](coordination/GOAL.md)依次推进，每次只有一个活动 goal。原逐轮完成表保留在 [迁移前 Git 版本](https://github.com/kris0516/ToolAlign/blob/abdc53d468a270cc1bfecbe56980dd34918480e1/AGENTS.md)和对应 reports。
