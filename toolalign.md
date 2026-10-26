# ToolAlign：新 Supervisor 出发点

更新：2026-10-26（Asia/Shanghai）。本文件取代旧 Mac 训练出发词。先读本文件和 AGENTS，按需打开证据，不必重读全部历史。

## 当前结论

冻结v3数据、CPU工具执行器和CUDA容量/完整恢复均已独立验收，G2完成。G3已在同规格L4完成0.6B冒烟198次更新和1.7B正式SFT 743次更新；各自完整验证CE从0.739884/1.145230降至0.041494/0.024438。196个产物文件已回收，实例已停止，见[结果与曲线](reports/S1_P04_CUDA_G3_SFT.md)。G3通过R1 `300af3f`、Q1 `34331c2`终验，随PR27合入主干 `1267d1a33dfb08bfd9800b80ea97315730748952`，App goal已complete。当前[G4](coordination/tasks/P05_G4_PROTOCOL.md)的CUDA生成与train偏好CPU包已交付R1/Q1审查，E1开始原生TRL DPO的CPU实现。

G3实际执行主干为 `2abbe7ac913661df1d5e430f285604b4ceb8ff4b`（PR26），双Python CI 40271208505成功。原始验证CE实现经R1 `fd4ad07` 审核，完整数组经Q1 `98cf0e1` 逐行核对后才分配GPU。**DPO、模型语义评测和服务仍NOT_RUN。** 原v1恢复FAIL及所有修订历史保留；见[G2实测](reports/S1_P04_CUDA_V2_RECOVERY.md)与[项目状态](coordination/PROJECT_STATUS.md)。

## 每个对话如何开始

1. 实际读取并应用本机 `avoid-overkill/SKILL.md`，默认位置为 `${CODEX_HOME:-$HOME/.codex}/skills/avoid-overkill/SKILL.md`。尤其是代码、实验和审查：先明确交付与最小验收，不添加没有观察依据的检查、回退、抽象或重复全量验证。
2. 读 [AGENTS.md](AGENTS.md) 和[当前状态](coordination/PROJECT_STATUS.md)。研究接续用 `paper-research-workflow`；Colab 工作用 `colab-remote-training` 和 `experiment-readiness`；其余按[技能分工](docs/17_SKILLS.md)选用。
3. 核对实际分支、未提交改动与已有运行。接续现有项目，不重做 P00–P03、不重开已完成的数据抽审、不把历史状态当新许可。

## 研究目标与计算路线

在固定模型、数据和评测预算下，比较 Qwen3 原始 checkpoint、LoRA SFT、SFT 后 DPO 的工具语义成功率、无需工具判断与故障恢复，并报告质量、延迟和资源成本。0.6B 用于冒烟与容量对照，1.7B 为主实验。已有指令模型不能称为 pretrained base。

用户已切换到 **Colab GPU**：Mac 用于编辑、CPU 测试、SSH 控制和结果分析，后续不在 Mac 上训练、做模型容量检查或批量模型任务。优先 L4 24GB，不适配时使用 A100 80GB；实际型号和显存以远端 `nvidia-smi` 为准。

已向另一研究项目 Supervisor 咨询，找到现成 Colab CLI、ADC、OpenSSH、tmux 配置和 A100 同实例断线/续训工程证据；该项目也有 L4 真实模型诊断记录。接入方法可复用；**ToolAlign CUDA SFT容量及新实例恢复已验收，正式SFT已完成并通过独立终验，DPO尚未运行**。流程见 [Colab 工作流与显存预算](docs/16_COLAB_WORKFLOW.md)，本机索引为 `.toolalign-local/handoff-2026-10-26/LOCAL_HANDOFF.md`。

## G2实现与后续约束

已建立有边界的P04 CUDA链路，后续沿用以下契约：

- 复用冻结 v3 数据、角色保留 Action JSON、token/mask 规则和模型 revision；修复后当前接口的一次真实数据读取及13例mask数组核对已由S1完成，见[消费记录](reports/S1_P04_DATA_V3_CONSUMPTION.md)。新CUDA消费者的独立审核与实际运行已通过。保留完整工具 schema，不为显存静默截断、换样本或改变有效 batch。
- 用 PyTorch / Transformers / PEFT 实现 LoRA SFT；为 DPO 核验并锁定 TRL。单独生成 CUDA 依赖锁；Mac 的 `uv.lock` 和 MLX PASS 不代表 CUDA 兼容。
- 保持 Q/V、28 层、rank 8、dropout 0、有效 scale 2；标准 PEFT LoRA 对应 `lora_alpha=16`、`use_rslora=False`。核对实际 trainable count、目标层、dtype、loss 分母、末批累积和恢复行为。优化器、注意力和 checkpointing 的新选择须显式登记并验证语义，不能照搬新框架默认值当作与旧方案等价。
- 申请 GPU 前记录显存预算；按冻结 batch/长度做一轮短容量验证，覆盖 forward、backward、optimizer step、验证和保存/重载。通过后再完整 epoch。启动前明确 run ID、配置、步数/时限、已有账户资源、输出与退出条件。
- R1 独立技术复核；Q1 独立审阅数据语义、偏好与交接说明。合并后按改动风险验证。

初始交接准备没有启动Colab实例或训练，后续G2实际运行见本页当前结论。S1 首包见 [CUDA SFT](coordination/tasks/P04_CUDA_SFT.md)和 [Colab 环境](coordination/tasks/P04_COLAB_ENVIRONMENT.md)。旧 `configs/sft-qwen-runtime-cpu.v1.json` 及未派发 MLX runtime 任务保留为历史协议参考；新建任务和版本化配置，不直接翻转旧冻结授权字段。

## 长期约束

当前 S1 与全部独立 worker/reviewer 使用 `gpt-6-astra / max`；只用独立 Codex 对话与隔离 worktree，禁止 sub-agent。最多两个实现任务、一个重 GPU 作业。用户已指定 S1 接班并继续推进；S0 只读答疑，S1 承接任务派发、协调文档与集成。阶段目标、产物和验收见 [GOAL](coordination/GOAL.md)。

Q1 承接后续原需人工审核的事项，不等待用户填表、签字或答辩。同问题连续第 5 次正式修订未通过才整体暂停并通知用户，第 1–4 次自主整改，见[审核规则](coordination/REVIEW_POLICY.md)。

Colab 路线及 L4/A100 选择已获用户指示；使用既有账户资源，不据此购买套餐、充值、开放公网服务或上传无关私有资料。远端仅处理训练所需的已批准数据，原始数据和凭据不进公开 GitHub。P00–P09 尚未完成，此次交接不能登记为研究完成。
