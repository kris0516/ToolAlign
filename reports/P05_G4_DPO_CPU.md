# P05 G4 原生 TRL DPO：CPU 实现与验收

2026-10-26；E1；状态：**CPU 实现与验收完成，待 R1 独立技术审查**。

原生 TRL sigmoid DPO 已通过独立逐 token 数值与梯度检查。10 对原创随机 fixture 的两次更新，与第 1 步完整保存后新进程恢复的结果一致：4 个 adapter 张量、12 个 Adam 张量和 4 个尾组梯度张量的最大绝对差均为 0，scheduler 与 Python/NumPy/Torch CPU RNG 完全一致。真实 Qwen 前向、正式偏好编码、Linux/CUDA 安装、容量与跨实例恢复、正式 DPO 均 **NOT_RUN**。

实现起点 `f72bb5fc7343989efcfc01b305e690d0cddeb661`，分支 `codex/e1-p05-g4-dpo-r1`。执行 [E1 任务](../coordination/tasks/P05_G4_DPO_CPU.md)和 [G4 协议](../coordination/tasks/P05_G4_PROTOCOL.md)；S1 在 `421cda11c1cd8b8cf606faf19dc46de0d9abc5f3` 明确解除 Colab 控制器保留后才编辑相应文件。该协调提交不合入本实现分支。

## 实现与输入

新增 `src/toolalign/training/cuda_dpo/`、独立配置与 DPO 依赖锁，以及对应测试。控制器只需修改 `scripts/colab/remote.py`、`support.py`；现有 `control.py` 已通过白名单分派，不需编辑。复用 cuda_sft 与 model_io 的只读帮助函数；冻结契约、SFT 生产代码与依赖锁、生成器、D1 偏好逻辑和共享状态没有修改。

`bind-input` 将 D1 提取目录的 `preferences.jsonl`、`lineage.jsonl`、`q1-sample.json`，Q1 的 `q1-review.json`，以及审核输出的 `training-preferences.jsonl`、`review-result.json` 绑定为六文件输入包。重新执行 D1 `apply_review`，核对质量门、正式 train 身份、原分母、训练顺序及 lineage，再生成逐文件 hash 的 `input-manifest.json`。这一步不产生运行授权。拒绝 synthetic 标记的正式输入和零有效对。

`prepare` 使用冻结的 non-thinking renderer 与离线 tokenizer，保留完整 ModelInput 和原始 chosen/rejected Action JSON 字符串。检查 prompt prefix、分别编码与拼接编码的一致性、原始文本回读及 EOS；两侧完整序列含 EOS 均须不超过 2048。超长对以 `context_overflow` 排除，保留原分母与逐对 disposition。原生 TRL 再编码后的三段 IDs 必须逐项等于该结果；目前没有覆盖原生 dataset preparation。

policy/reference 分别加载原始 Qwen3-1.7B 底座和 G3 step743 adapter，reference 全冻结/eval；不使用 disable-adapter 充当 reference，不复用 SFT optimizer。核对原 SFT 完整 state/manifest、step743/cursor5938、adapter 键/形状/FP32/有限值/hash 及两个模型的独立存储。固定状态 SHA256 为 `cfb02aec2279138c01f8b336abc08a588d0ab11efa8db68fd61ba0b6150b5d14`，adapter SHA256 为 `973c440e29090892ad11d6d56b94bad4c98a5398c223e2b4302d7dba7c4640ed`。

## 原生训练与恢复

数值计算、梯度累积、训练循环、保存和恢复均调用 TRL 0.26.2 / Transformers 4.57.6 的原生实现。薄层适配负责 SequentialSampler、输入 ID 观察、optimizer 边界、完整状态标记和身份检查。

- sigmoid DPO，beta=0.1、label_smoothing=0、reverse KL，completion logprob 含 EOS 求和。reference_free、RPO、长度重加权、reference 同步、缓存 reference logprob、Liger 均关闭；`peft_config=None`，三个长度参数均为 None。
- `use_logits_to_keep=True` 保留完整输入注意力，只减少 LM-head 输出。独立 fixture 核对开关前后的监督位置、逐 token logprob、SUM、loss 与梯度。
- BF16 底座与显式 BF16 AMP，FP32 Q/V LoRA，28 层、rank8、alpha16、dropout0；SDPA、确定性算法和 `CUBLAS_WORKSPACE_CONFIG=:4096:8` 沿用已验收配置。实际 Accelerate 包装后的 logits/logprob/loss dtype 写入 `precision.json`，CUDA 执行还须确认实际 device/AMP。
- AdamW lr=5e-6，betas=(0.9,0.999)，eps=1e-8，weight_decay=0，foreach/fused=False，常数 scheduler、零 warmup、max_grad_norm=0。seed42，一轮，microbatch1，累积8；尾组使用实际微步数。
- 全局 `max_steps=ceil(N/8)` 始终指完整一轮。`stop_after_optimizer_step` 只控制本段结束；在 `on_step_end` 完成更新后保存，不缩短全局步数。`save_only_model=False`、`ignore_data_skip=False`，保留最近两个完整 checkpoint。
- 原生保存完成后的 `on_save` 才写 `dpo-manifest.json`，绑定源码、依赖、模型、配置、输入、顺序、全局步数、游标和 checkpoint 文件 hash。恢复前检查 adapter/Adam/scheduler/RNG 的完整性，再交原生 Trainer 恢复。reference 每段从原 G3 SFT 重建。

生产入口 CUDA-only，持有共享 GPULease，要求单 GPU、20% 显存余量。父进程通过真实 spawn/Pipe 监督完整输出目录及墙钟，超限终止并回收 worker，记录原始失败；子进程保留外层控制器的进程组。单段上限 21,600 秒、1 GiB；G4 跨阶段累计时长和 CU 仍由 S1 汇总。`durability_verified=false`，实例本地输出须经既有 export/recover/ack 流程回收到 Mac 才能认定已回收。

`dpo_capacity` 使用 S1 冻结的至多 24 个 pair occurrence，第一项必须是最长真实有效对，可以重复已接纳的 pair 来检查三步容量及恢复；原文不变。其身份与正式 `dpo` 分开，容量 checkpoint 无法用于正式训练。正式 DPO 必须消费全部有效对的固定顺序，并从原选中 SFT 新建 optimizer。

## 独立依赖

Mac 新建专用 Python 3.12.14 环境，58 项锁定包均实际安装并核对版本，`pip check` exit 0。实际平台为 macOS 26.5.1 arm64；Torch 2.8.0、TRL 0.26.2、Transformers 4.57.6、PEFT 0.18.1、Accelerate 1.12.0。原 SFT 共享环境未修改。

| 文件 | 包数 | SHA256 |
|---|---:|---|
| `configs/dpo-cuda.v1.json` | — | `fafb91a32e75cfbb15e452d528aa30c9e3db4e3149d0684834f459564c679ce3` |
| `requirements/dpo-macos-cpu-py312.lock.txt` | 58 | `b0c0b1e6aa67a5db488f132326d564d76b425ffb02d5658b18aafbe17a25022d` |
| `requirements/dpo-linux-py312.lock.txt` | 69 | `632e82eb75d856ab7f7c22d1519a959eb0ceab6f12e7e8931cb89924f3bab25a` |

两平台既有依赖只有 `fsspec` 从 2026.9.0 改为 2025.10.0：datasets 4.4.1 的上界要求与原版本冲突。其余已有锁定版本全部保留，没有移除包。除新固定的 trl/datasets 外，新增 19 项传递依赖如下；全部版本及每项 hash 在锁中。

```text
aiohappyeyeballs==2.7.1    aiohttp==3.14.5       aiosignal==1.4.0
anyio==4.15.1            dill==0.4.0           frozenlist==1.8.0
h11==0.16.0              httpcore==1.0.9       httpx==0.28.1
multidict==7.2.1         multiprocess==0.70.18 pandas==3.1.0
propcache==0.5.4         pyarrow==26.0.0       python-dateutil==3.0.0
six==1.17.0              tzdata==2026.5        xxhash==4.0.2
yarl==1.25.1
```

Linux 锁固定 Torch 2.8.0+cu128，经显式 Python 3.12、x86_64 Linux 目标、`--require-hashes --only-binary :all:` 的 uv dry-run 解析通过；未安装 Linux/CUDA 包。生成锁后只规范化注释，包、索引、hash 行保持不变，变换前后身份保存在证据中。

Colab 根据固定 DPO schema 选择 `.toolalign-local/dpo-env`、DPO lock 和独立环境就绪记录。安装使用 `pip --isolated`、显式 PyPI 与 CUDA index，防止环境变量改变索引。已有环境锁不符或部分环境存在时保留现场并失败；SFT/generation 仍选择原环境和原安装命令。

## CPU 验收证据

模型为原创随机初始化的单层 Qwen3 类 fixture，hidden_size8、vocab259、总参数少于4096，使用直接生成的非零 synthetic adapter；未下载或加载预训练权重。正式格式输入 fixture 的审核身份与理由明确标 synthetic，不代表真实 Q1 接纳。

| 验收 | 实际结果 |
|---|---|
| 不等长 completion 数值 | 独立无 padding forward，逐 token FP64 logsumexp 参考；prompt/pad 梯度严格为0，含 EOS；原生 SUM、sigmoid loss、全部 adapter 梯度及 logits_to_keep 两条路径在 atol=2e-6、rtol=2e-5 内通过 |
| 初始化与更新边界 | synthetic adapter 原始/两份加载前向完全相等、存储独立；初始 loss=0.6931471824645996；一次更新仅 policy adapter 改变，policy 底座及 reference 全参数不变 |
| 10 对完整/恢复 | 实际组大小8、2；游标8、10；新进程仅消费第9、10对；adapter 4、Adam 12、尾梯度4个张量差值均为0；scheduler/RNG一致，独立均值梯度参考也通过 |
| dtype 实测 | CPU AMP=no、SDPA，policy/reference logits、logprob、loss 均 FP32；CUDA BF16 AMP 下的实际归约 dtype 待测 |
| 输入、进程与全部 Colab 控制回归 | Python3.12：70 passed，27.70秒，包括原 SFT/generation 控制、DPO 环境/索引、真实 CPU 子进程墙钟/输出限制与回收 |
| 最后边界检查增补后 | 仅重跑受影响的10对保存/恢复验收：1 passed，10.81秒；原数值/单步检查未改未重跑 |
| 基础 Python3.14.7 接口兼容 | 新增协议/进程/DPO控制：29 passed、1 skipped，3.25秒；缺少 pip parser 的一项已在专用3.12环境通过 |

主要复现命令如下，`DPO_PY` 指新建专用 CPU 环境；详细 argv、源码快照/hash、退出码、stdout/stderr 和测试产物均在私有证据索引中。

```sh
PYTHONPATH=src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 "$DPO_PY" -m pytest -q tests/training/test_cuda_dpo_native.py
PYTHONPATH=src "$DPO_PY" -m pytest -q tests/training/test_cuda_dpo_protocol.py tests/training/test_cuda_dpo_process.py tests/colab
"$DPO_PY" -m pip check
uv --no-config pip install --dry-run --python "$DPO_PY" --target /absolute/linux-wheel-plan --python-version 3.12 --python-platform x86_64-unknown-linux-gnu --default-index https://pypi.org/simple --index https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match --only-binary :all: --require-hashes -r requirements/dpo-linux-py312.lock.txt
```

本地失败原记录保留：第一次两平台解析因 fsspec 上界冲突失败；首轮原生测试为2 passed/1 failed，失败发生在独立参考 optimizer 的最终 metadata 比较，参考遗漏常数 scheduler 加入的 `initial_lr`，此前实际恢复比较均已通过。给独立参考补齐相同 scheduler 后定点通过，没有修改生产损失或放宽容差。首轮 Ruff 的4项导入/未使用项已修正。首次 Linux dry-run 虽指定目标3.12，显示的默认解释器为3.14，随后显式绑定专用3.12解释器再次通过。

提交检查通过：全仓 Ruff、4文件契约冻结、846路径公开内容扫描、CLI基础环境入口与 diff check 均 exit 0。源码打包实测覆盖 sdist、直接 wheel 与从 sdist 重建的 wheel，241个私有 canary 均排除，18个公开 fixture 与冻结schema保留（sdist 217文件、523887字节）。最终 commit 与实际检查记录在 `.toolalign-local/p05-g4-dpo-r1/handoff-index.json`；`evidence-summary.json` 保存上述数值、全部实际版本及逐包差异。私有索引和 fixture checkpoint 不进入 Git。

## 给 S1 的运行入口

R1 审查通过、真实 Q1 训练清单接纳后，先在受控路径绑定并准备输入：

```sh
python -m toolalign.training.cuda_dpo bind-input --extraction /absolute/extraction --reviewed /absolute/reviewed --review /absolute/q1-review.json --output /absolute/dpo-input
python -m toolalign.training.cuda_dpo prepare --repository /absolute/toolalign --input-root /absolute/dpo-input --input-manifest-sha256 INPUT_SHA256 --model-root /absolute/qwen3-1.7b --output /absolute/preparation.json
python -m toolalign.training.cuda_dpo validate --run-config /absolute/run.json
```

`prepare` 返回原/有效/排除对数、逐对 token 数及 `prepared_data_sha256`，没有模型加载或更新。`validate` 验证请求与审核输入，不替代真实 tokenizer/CUDA 验收。S1 将以下字段写入独立私有 run config，再使用现有 Colab 控制流程运行固定入口 `python -m toolalign.training.cuda_dpo train --run-config /absolute/run.json`：

| 字段 | 值或来源 |
|---|---|
| schema / authorized_by / run_kind | `toolalign.cuda-dpo-run.v1` / `S1` / `dpo_capacity` 或 `dpo` |
| run_id / source_commit / config_sha256 | 独立运行ID、经R1接纳的40位源码提交、上表DPO配置hash |
| repository / lock_root / model_root / sft_checkpoint_dir / input_root / output_dir | 绝对路径；repository 与 lock_root 解析为同一共享锁；output_dir 为尚不存在的新目录，父目录须存在 |
| input_manifest_sha256 / prepared_data_sha256 | bind-input / prepare 的实际输出 |
| dependency_lock / dependency_lock_sha256 | repository 下 DPO Linux lock 绝对路径及上表hash |
| pair_count / total_optimizer_steps | 正式有效对数 N / ceil(N/8)，不是本段对数/步数 |
| stop_after_optimizer_step / checkpoint_every_steps | 本段最终全局 optimizer step / 正整数保存间隔；结束边界始终保存 |
| max_wall_seconds / max_output_bytes | S1 在剩余全阶段预算内冻结；分别不超过21600、1073741824 |
| capacity_pair_ids | 仅容量：明确的完整 occurrence 顺序，至多24项，首项最长；pair_count 等于该长度 |
| resume_from / resume_checkpoint_sha256 | 仅恢复：已回收完整 checkpoint 目录及其 manifest 中的 checkpoint_sha256；全轮总步数、输入顺序和保存间隔保持一致 |

控制 payload 仍通过现有控制器生成；不传 SFT 的 `max_optimizer_steps` 或 `persistent_dir`。正式训练省略 `capacity_pair_ids`，首次正式段省略恢复字段。后续段只提高停止步，使用新输出目录与上段完整 checkpoint；不能跨容量/正式身份恢复。

下一决定：S1 回读本提交并交 R1 独立审查；通过后依据真实 Q1 输入冻结最长对容量计划，实测双模型显存、首次 Adam 状态、保存及新进程/新实例恢复。容量验收完成后，正式 DPO 从原 G3 SFT 开始。
