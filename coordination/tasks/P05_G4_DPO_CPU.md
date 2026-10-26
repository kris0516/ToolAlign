# P05 G4｜原生 TRL DPO 与依赖 CPU 实现

状态：ACTIVE；owner E1，已从 `f72bb5fc7343989efcfc01b305e690d0cddeb661` 在现有独立 worktree 建 `codex/e1-p05-g4-dpo-r1` 执行。2026-10-26 S1已回读并接纳R1生成/偏好CPU审查 `fac9ec52a7dbb0b28c6d767ea13fcdeb13ccc9fa`；生成器无代码修订，现解除下述Colab控制器三文件保留，E1可按原范围加入独立DPO入口/环境。真实GPU运行仍由S1另冻配置。

目标：按 [G4 协议](P05_G4_PROTOCOL.md)交付可复现的 TRL 0.26.2 标准 sigmoid DPO、独立依赖锁、有界 Colab 入口及完整 checkpoint 恢复。本包只安装专用 Mac CPU 测试环境、运行小型随机初始化 fixture，不加载真实模型、不训练正式数据、不分配 GPU。真实偏好数量及 Q1 结果尚未确定，零有效对不启动 DPO。

## 修改范围

- 新增 `src/toolalign/training/cuda_dpo/`、独立 `configs/dpo-cuda.v1.json`、`requirements/dpo-*.in` 和 Linux/Mac Python 3.12 哈希锁。
- 在已交付的 `scripts/colab/{control,remote,support}.py` 中增加明确 DPO 白名单及专用环境选择；保持原 SFT 和 generation 路径的行为。生成器当前处于R1审查，E1先做依赖与trainer，控制器文件须等S1明确解除保留后再编辑，避免与审查修订重叠。
- 对应 `tests/training/`、`tests/colab/` 定点检查，报告 `reports/P05_G4_DPO_CPU.md` 与交接 `coordination/handoffs/P05-g4-dpo-r1.md`。
- 复用现有 model_io、cuda_sft 的公开只读帮助函数；不改冻结模板、模型描述、SFT 协议和依赖。若真实接口缺口要求编辑生成器或 SFT 核心，先向 S1 提出具体文件和原因。

禁止改 contracts、P02/P03 数据/工具/oracle、D1 偏好逻辑、共享状态及历史授权；不建 sub-agent 或新聊天。沿用 gpt-6-astra/max。

## 依赖与输入

固定 `trl==0.26.2`、`transformers==4.57.6`，保留当前共享直接依赖及 Torch 2.8.0（Linux cu128）的版本。为 TRL/datasets 解析独立、可安装的完整哈希锁；必要的传递依赖差异逐项说明，不覆盖原 SFT 锁或环境。Linux 轮子只解析/验证可获得性；实际 Linux/CUDA 安装仍须以后在 Colab 实测。Mac 新建专用 CPU 环境，保存实际版本及 pip check，不改正在使用的共享 CPU 环境。安装计划继续显式使用 PyPI 与 CUDA index，防止本机环境变量改变索引。

输入绑定正式 preference.v1、lineage 和 Q1 已接纳的训练清单及其 hash；CPU fixture 显式 synthetic。policy/reference 都从 G4 协议指定的 G3 step743 SFT 初始化，验证完整 state/manifest、adapter 名称、形状、FP32 dtype 和 hash；不把 SFT optimizer 状态作为新 DPO optimizer 起点。reference 从同一原始底座与已选 SFT adapter 独立加载，全冻结/eval。两份模型应具有相同初始前向和 adapter 参数，且存储独立。

逐对保留真实完整 ModelInput 与原始 chosen/rejected Action JSON，不改写 completion。使用冻结 non-thinking renderer 和 tokenizer：传入已渲染字符串 prompt、未附 EOS 的原始 completion，显式 `peft_config=None` 以及独立 reference model。TRL 会分别编码三段并给 completion 加 EOS；核对实际 prepared token IDs、共享 prefix、EOS 及拼接编码边界与本项目规则一致。三个长度截断参数全为 None，外部检查每侧完整序列含 EOS ≤2048，超长明确排除并保留原分母；不得截 schema 或 response。若原生编码与冻结 token 身份不符，先报告实际差异，再采用仅覆盖 dataset preparation 的最小适配，不能静默改编码。

## 训练与恢复

复用原生 DPOTrainer 的 loss、训练、累积和保存/恢复循环；只为冻结顺序、边界控制、输入身份增加薄层适配。

- 标准 sigmoid，beta=0.1，label_smoothing=0，reverse KL，reference_free=False，completion logprob 含 EOS 求和。RPO/IPO/length desensitization/weighting/reference 同步/Liger 均关闭，不注入缓存 ref logprob 列。实际数值 dtype 和 attention 路径明确记录。
- 使用原生 `use_logits_to_keep=True`，仅计算 completion 所需的 LM-head 输出；固定 Qwen3 forward 支持此参数。将开关前后的 mask、logprob、loss 和梯度等价核对纳入下述数值 fixture，保留完整输入注意力，不截上下文。BF16 mixed precision 显式配置，核对 Accelerate 包装后实际 logits/logprob 的 dtype；不因底座是 BF16 就推定归约精度。
- BF16 底座、FP32 Q/V LoRA、28 层、rank8、alpha16、dropout0；沿用已验收 CUDA 确定性设置，不静默降精度或换模型。只有 policy adapter 可训练。
- AdamW 显式 betas=(0.9,0.999)、eps=1e-8、weight_decay=0、foreach=False、fused=False，常数 lr=5e-6、零 warmup、max_grad_norm=0。seed42、一轮、microbatch1、累积8。SequentialSampler 保持冻结输入顺序，尾组使用真实对数。
- 全局训练步数始终为完整一轮的 ceil(N/8)。分段边界只在 on_step_end 完成 optimizer update 后保存并停止，不能重定义分段 max_steps 或重复消费样本。原生完整保存 optimizer/scheduler/RNG/Trainer state，save_only_model=False、ignore_data_skip=False。恢复 reference 仍从原 G3 SFT 加载。
- checkpoint 附路径无关的源码、依赖、模型、输入与配置身份和文件完整性记录；只有完成保存的 checkpoint 可恢复。沿用已有可核对回收方式，不把实例本地 staging 称为持久备份。
- 专用 CUDA-only 生产入口必须具有 GPULease、外部墙钟/输出限制、明确 run_kind/总步数/本段停止步、失败记录和可回收产物；不提供 CPU 实际模型回退、任意 shell 或公网服务。DPO 环境与 SFT/generation 环境分开，不能在原环境上换锁。

容量配置由 S1 在 Q1 接纳真实输入后另冻；须支持最长真实偏好对、首次 optimizer state、保存、新进程和新实例恢复。容量更新不得混入正式 DPO 一轮；正式训练从原选中 SFT 重新开始。

## CPU 验收与交付

至少覆盖以下三个有区分力的检查，并保存实际命令、环境、退出码与证据索引：

1. 不等长 completion：逐 token 独立参考核对 prompt/pad/EOS mask、completion SUM logprob、sigmoid DPO 标量和梯度。不能用被测 loss 充当唯一参考。
2. 初始 policy=reference 的 loss≈ln2；一次更新后仅 policy adapter 改变，reference 的底座和 adapter 均不变。覆盖 SFT adapter 加载前向一致及两个模型不共享参数存储。
3. 10 对小型随机 fixture 完整两步，对比第1步完整保存后新进程恢复第2步；覆盖尾组2、输入游标、adapter、Adam、scheduler 与 RNG。比较实际数值及预定容差，不能只比较“进程完成”。

控制器只验证新环境/入口选择、身份/预算和原路径兼容。真实 Qwen 前向、正式偏好编码、CUDA 安装/容量/恢复及正式 DPO 在报告中标 NOT_RUN。交付精确 commit、差异范围、环境/测试证据及运行示例；S1 回读后交 R1 独立技术审查，真实数据仍由 Q1 审阅。
