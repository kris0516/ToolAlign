# ToolAlign：新 Supervisor 出发点

更新：2026-10-26（Asia/Shanghai）。本文件取代旧 Mac 训练出发词。先读本文件和 AGENTS，按需打开证据，不必重读全部历史。

## 当前结论

ToolAlign 已完成数据治理、CPU 工具执行器、训练数据与固定模型的 CPU 接口，以及 MLX 小型数值验证。冻结 v3 数据通过独立质量审核。**正式 Qwen SFT、DPO、模型语义评测和服务结果均为 NOT_RUN。** 下一项工作是在 Colab 建立 CUDA 训练链路。

代码交接基线为 `abdc53d468a270cc1bfecbe56980dd34918480e1`（PR19 合并）。原 R1-r3 PASS、两轮 FAIL 和修复历史保留。合并后数据接口定点检查 **163 passed**，生产代码与已审 PR19 一致。各阶段证据见[项目状态](coordination/PROJECT_STATUS.md)。

## 每个对话如何开始

1. 实际读取并应用本机 `avoid-overkill/SKILL.md`，默认位置为 `${CODEX_HOME:-$HOME/.codex}/skills/avoid-overkill/SKILL.md`。尤其是代码、实验和审查：先明确交付与最小验收，不添加没有观察依据的检查、回退、抽象或重复全量验证。
2. 读 [AGENTS.md](AGENTS.md) 和[当前状态](coordination/PROJECT_STATUS.md)。研究接续用 `paper-research-workflow`；Colab 工作用 `colab-remote-training` 和 `experiment-readiness`；其余按[技能分工](docs/17_SKILLS.md)选用。
3. 核对实际分支、未提交改动与已有运行。接续现有项目，不重做 P00–P03、不重开已完成的数据抽审、不把历史状态当新许可。

## 研究目标与计算路线

在固定模型、数据和评测预算下，比较 Qwen3 原始 checkpoint、LoRA SFT、SFT 后 DPO 的工具语义成功率、无需工具判断与故障恢复，并报告质量、延迟和资源成本。0.6B 用于冒烟与容量对照，1.7B 为主实验。已有指令模型不能称为 pretrained base。

用户已切换到 **Colab GPU**：Mac 用于编辑、CPU 测试、SSH 控制和结果分析，后续不在 Mac 上训练、做模型容量检查或批量模型任务。优先 L4 24GB，不适配时使用 A100 80GB；实际型号和显存以远端 `nvidia-smi` 为准。

已向另一研究项目 Supervisor 咨询，找到现成 Colab CLI、ADC、OpenSSH、tmux 配置和 A100 同实例断线/续训工程证据；该项目也有 L4 真实模型诊断记录。接入方法可复用；**ToolAlign CUDA SFT/DPO 和实例回收后的重建续训仍待验证**。流程见 [Colab 工作流与显存预算](docs/16_COLAB_WORKFLOW.md)，本机索引为 `.toolalign-local/handoff-2026-10-26/LOCAL_HANDOFF.md`。

## 新 Supervisor 的第一项交付

准备一个有边界的 P04 CUDA 适配包：

- 复用冻结 v3 数据、角色保留 Action JSON、token/mask 规则和模型 revision；先用修复后的当前接口完成一次真实数据读取及 mask 数组核对，该实际消费仍未运行。保留完整工具 schema，不为显存静默截断、换样本或改变有效 batch。
- 用 PyTorch / Transformers / PEFT 实现 LoRA SFT；为 DPO 核验并锁定 TRL。单独生成 CUDA 依赖锁；Mac 的 `uv.lock` 和 MLX PASS 不代表 CUDA 兼容。
- 保持 Q/V、28 层、rank 8、dropout 0、有效 scale 2；标准 PEFT LoRA 对应 `lora_alpha=16`、`use_rslora=False`。核对实际 trainable count、目标层、dtype、loss 分母、末批累积和恢复行为。优化器、注意力和 checkpointing 的新选择须显式登记并验证语义，不能照搬新框架默认值当作与旧方案等价。
- 申请 GPU 前记录显存预算；按冻结 batch/长度做一轮短容量验证，覆盖 forward、backward、optimizer step、验证和保存/重载。通过后再完整 epoch。启动前明确 run ID、配置、步数/时限、已有账户资源、输出与退出条件。
- R1 独立技术复核；Q1 独立审阅数据语义、偏好与交接说明。合并后按改动风险验证。

本次没有启动 Colab 实例或训练。旧 `configs/sft-qwen-runtime-cpu.v1.json` 及未派发 MLX runtime 任务只是历史协议参考，不是 CUDA 运行许可；新建任务和版本化配置，不直接翻转旧冻结授权字段。

## 长期约束

S0 与全部独立 worker/reviewer 使用 `gpt-6-astra / max`；只用独立 Codex 对话与隔离 worktree，禁止 sub-agent。最多两个实现任务、一个重 GPU 作业。用户后续新开 Supervisor，本次不创建下一 Supervisor 或派发实现任务；Q1 按既有授权只读审核本次交接。

Q1 承接后续原需人工审核的事项，不等待用户填表、签字或答辩。同问题连续第 5 次正式修订未通过才整体暂停并通知用户，第 1–4 次自主整改，见[审核规则](coordination/REVIEW_POLICY.md)。

Colab 路线及 L4/A100 选择已获用户指示；使用既有账户资源，不据此购买套餐、充值、开放公网服务或上传无关私有资料。远端仅处理训练所需的已批准数据，原始数据和凭据不进公开 GitHub。P00–P09 尚未完成，此次交接不能登记为研究完成。
