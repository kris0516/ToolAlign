# P04-CUDA-SFT｜CUDA SFT 首包

状态：READY。owner T1；协调者 S1；code_base `61c2176d556fd0e4cfc2af00b16242dddcfadfd3`；authorization_commit 由原生派发提供。分支 `codex/p04-cuda-sft-r1`，复用 T1 干净隔离 worktree，保留私有模型与旧证据。先保存授权中的任务/配置/AGENTS/GOAL，再从 code_base 建分支。

目标：交付可在 Colab 运行的最小 PyTorch/Transformers/PEFT SFT 链路，保持冻结 v3、角色保留 Action JSON、模型 revision、completion 与单 EOS 监督及完整恢复。协议见 [sft-cuda.v1.json](../../configs/sft-cuda.v1.json)。非目标：正式训练、DPO、批量模型评测、修改旧 MLX runtime 或旧授权字段。

允许新增 `src/toolalign/training/cuda_sft/`、`tests/training/test_cuda_sft*.py`、必要的同名原创小 fixture、`reports/experiments/P04_CUDA_SFT.md` 和本包 handoff。唯一共享配置例外：逐字节复制授权中的 `configs/sft-cuda.v1.json` 到代码基线并提交；修改建议先回 S1。不得改共享状态、旧数据/模型配置、契约、默认依赖/uv.lock、来源数据或 E1 的环境路径。

输入：`configs/sft-data-v3.v1.json`、`configs/qwen-models.v1.json`、`coordination/approvals/P02_DATA_V3.json`。S1 先用当前接口完成真实 prepare/rebind/export/readback，私下提供精确回执和固定数组。旧 manifest 的本机绝对引用不上传 Colab；新增有限 portable train/validation array bundle，绑定四个选择 view 身份、原行/audit、模型/tokenizer/格式和生成源码。旧 `authorization=false` 保持；最终测试/BFCL和三个 protocol-only 材料不得进入训练。

数据准备与训练是两个显式入口，import 不编码/下载/训练。复用 `prepare_v3`、`OfflineQwenTokenizer`、`collate_selected` 和 `Batch`；先无框架核验冻结输入/13例，再在独立无模型进程做已批准profile有限编码，保留旧prepare框架禁入规则。训练只消费已核验数组。首个接口回报明确包格式和命令供 E1 接线，不建通用数据平台。

数值契约：Q/V 28层、56模块、rank8、alpha16、use_rslora=False、dropout0；0.6B/1.7B trainable参数1,146,880/1,605,632。BF16底座、FP32 adapter；标准torch AdamW bias correction、lr1e-4、betas(.9,.999)、eps1e-8、weight_decay0、固定LR、无裁剪。SDPA、use_cache=False、non-reentrant gradient checkpointing。此为新CUDA方案，不宣称等价旧MLX。

训练为每样本completion+EOS token mean，再对当前累积组取mean。microbatch1、accumulation8；末批按实际样本数7/2除，不丢弃或按8除。验证为总completion CE/总监督token，完整有序validation，选最小有限CE再最早step。无shuffle/packing/truncation；causal arrays与forward仅一次shift。

checkpoint包含adapter、optimizer、scheduler或固定LR状态、step/数据游标、Python/NumPy/Torch CPU/CUDA RNG、配置/源码/数据/模型/依赖身份；原子写本地再持久化，保留best/last/一个回滚。比较新进程恢复与连续执行的后续loss/参数/RNG；跨实例在G2实测，不由toy推定。真实CUDA入口先核验有界run配置并获取共享 `GPULease` 再加载模型；CUDA不可用明确失败，不回落Mac。

本包资源：GPU分配/真实模型加载/训练/偏好/生成为0。默认stdlib CPU检查；可在S1/E1锁定的专用CPU测试环境用原创tensor fixture（参数≤4096、序列≤16、更新≤3、单次≤300秒、2线程）。新增私有证据≤1GiB。真实数据消费/全profile编码由S1另行有界执行，worker先交代码和原创测试，不重建退役Mac训练环境。

验收命令（PLANNED）：`python -m pytest -q tests/training/test_cuda_sft*.py --basetemp=NEW_EXCLUSIVE_TEMP`；定点ruff、契约/公开扫描。有效测试覆盖独立手算CE/梯度、长短样本损失权重、mask/EOS/右pad/shift、末批7/2、adapter更新与冻结权重、完整resume；错误身份/不完整checkpoint/缺失CUDA/重复运行锁须在执行前拒绝。复用旧检查，不重复全量验证。真实数组与CUDA消费者对应由Q1/R1审核。

交付精确提交、实际命令/退出码/版本、失败记录、可运行命令、未验证项与 `coordination/handoffs/P04-cuda-sft-r1.md`。R1独立技术复核，Q1核对数据/mask和说明；S1合并后签发GPU run。问题按既有稳定issue和五次规则处理，缺依赖先给具体接口需求，不自行扩展范围。
