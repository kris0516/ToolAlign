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

P00–P03 与 P04 原CPU/MLX证据保留。当前执行主干为 PR24 `eb73fbcdb5f053509a396c59092e28d7c317cdd9`；CUDA v2 在同规格 L4 完成三步容量、新进程与新实例完整恢复，S1比较1,883项通过、672个张量比较差为0，R1/Q1独立终验已接纳，G2验收通过。见 [实测报告](reports/S1_P04_CUDA_V2_RECOVERY.md)。正式SFT/DPO/模型评测/服务仍NOT_RUN，不恢复旧Mac runtime任务。

2026-10-26 用户指定 Toolalign Supervisor S1 接班并继续推进；按 [分组目标](coordination/GOAL.md)依次推进，每次只有一个活动goal。G1、G2验收已完成，下一阶段G3。原逐轮完成表保留在 [迁移前Git版本](https://github.com/kris0516/ToolAlign/blob/abdc53d468a270cc1bfecbe56980dd34918480e1/AGENTS.md)和对应reports。
