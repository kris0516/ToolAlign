# P04 CUDA SFT：CPU 首包

代码与测试提交：`95cf14224ceb2ea3a3e817826aeef0e651eb459d`。本轮 17 项定点 CPU 测试全部通过：独立 CE/梯度参考、样本均权与 token 加权验证、末组 7/2、官方 PEFT 的原创微型 Qwen、完整新进程恢复、checkpoint 选择和退出时的子进程回收。可交给 R1/Q1 审查，再由 S1 执行冻结容量数组的准备与 Colab 验证。真实数据准备/编码、真实模型加载、CUDA 训练、跨实例恢复和正式 SFT 在本 worker 中均为 `NOT_RUN`。

基线 `61c2176d556fd0e4cfc2af00b16242dddcfadfd3`；授权 `04415938c749ea2e8dc1ef5e8ab7e30b777aeb47`。新增模块在 `src/toolalign/training/cuda_sft/`。共享变更为逐字节复制的 [sft-cuda.v1.json](../../configs/sft-cuda.v1.json)，SHA256 `3d4785e1e130dd04990abb3767c23d92cdb7b18dad1d30cc6991f976cd44c9c4`。默认依赖、旧 MLX 路径及旧数据配置未修改。

## 准备与 portable arrays

三个命令均有独立子进程和墙钟上限；import 不编码、下载或训练。

```sh
python -m toolalign.training.cuda_sft prepare --request PREPARE_JSON
python -m toolalign.training.cuda_sft encode --request ENCODE_JSON
python -m toolalign.training.cuda_sft train --run-config RUN_JSON
```

`prepare` 在未导入框架的进程中复用 `prepare_v3`、13 例 rebind/export/readback。输出需位于 `.toolalign-local` 下，保留旧入口规则。它只写已选原行、sidecar 和核验身份，不重新编码。`encode` 在另一个无模型进程中使用原生 `OfflineQwenTokenizer` 与 `collate_selected`，输出经 `Batch`、audit、EOS、顺序和覆盖检查的数组；它不需要旧 input manifest 的绝对引用。

以下是待 S1 填入精确提交、输入和哈希的模板，示例路径不指向本机证据，也不构成运行授权。输出父目录需已存在，输出目录本身需不存在。

```json
{
  "schema": "toolalign.cuda-sft-prepare.v1",
  "authorized_by": "S1",
  "run_kind": "capacity",
  "profile": "formal",
  "source_commit": "REPLACE_WITH_CHECKED_OUT_COMMIT_40HEX",
  "config_sha256": "3d4785e1e130dd04990abb3767c23d92cdb7b18dad1d30cc6991f976cd44c9c4",
  "repository": "/workspace/toolalign",
  "input_manifest": "/workspace/toolalign/.toolalign-local/approved-input-manifest.json",
  "output_dir": "/workspace/toolalign/.toolalign-local/capacity-stage",
  "max_examples": 20,
  "max_wall_seconds": 300,
  "max_output_bytes": 134217728
}
```

```json
{
  "schema": "toolalign.cuda-sft-encode.v1",
  "authorized_by": "S1",
  "run_kind": "capacity",
  "profile": "formal",
  "source_commit": "REPLACE_WITH_SAME_COMMIT_40HEX",
  "config_sha256": "3d4785e1e130dd04990abb3767c23d92cdb7b18dad1d30cc6991f976cd44c9c4",
  "repository": "/workspace/toolalign",
  "stage_dir": "/workspace/toolalign/.toolalign-local/capacity-stage",
  "stage_manifest_sha256": "REPLACE_WITH_PREPARE_MANIFEST_FILE_SHA256",
  "tokenizer_root": "/workspace/toolalign/.toolalign-local/approved-tokenizer",
  "output_dir": "/workspace/toolalign/.toolalign-local/capacity-arrays",
  "max_examples": 20,
  "max_wall_seconds": 300,
  "max_output_bytes": 134217728
}
```

最终 portable 目录只有 `manifest.json`、`train.jsonl`、`validation.jsonl`。每行含 `original_line_sha256`、完整 sidecar/audit 和 Batch 的六组数组及边界。manifest 绑定四个完整 view、选择与数据配置、生成源码、模型 revision、tokenizer 文件/版本/参数、格式和本次 cohort；文件哈希按实际字节计算。训练入口再次核验数组与其原 audit，消费已有 causal arrays，不传 HF `labels`。

容量 cohort 固定为 formal 中长度降序、原 rank 升序选出的 18 条 train 与 2 条 validation，再按原 rank 消费；完整 cohort SHA256 为 `48d66f48010dc0d0ce6db5bc64ac5e7223aa79fe7824f7ca623e6449f4adedeb`。调用者不能提供自由 rank 列表。`run_kind=sft` 则要求完整冻结 profile：smoke 为 1,583/194 条、正式为 5,938/213 条，对应 `max_examples=1777/6151`。这些是冻结契约中的数量；本轮未执行真实数组生成。最终测试、BFCL 和三个 protocol-only 材料均无训练入口。

## CUDA 与恢复接口

E1 唯一训练 argv 为 `python -m toolalign.training.cuda_sft train --run-config FILE`。容量配置模板如下：

```json
{
  "schema": "toolalign.cuda-sft-run.v1",
  "authorized_by": "S1",
  "run_id": "g2-capacity-continuous",
  "run_kind": "capacity",
  "profile": "formal",
  "source_commit": "REPLACE_WITH_MERGED_COMMIT_40HEX",
  "config_sha256": "3d4785e1e130dd04990abb3767c23d92cdb7b18dad1d30cc6991f976cd44c9c4",
  "array_manifest_sha256": "REPLACE_WITH_VERIFIED_ARRAY_MANIFEST_FILE_SHA256",
  "dependency_lock_sha256": "REPLACE_WITH_E1_LINUX_LOCK_FILE_SHA256",
  "repository": "/content/toolalign",
  "lock_root": "/content/toolalign",
  "array_dir": "/content/toolalign-private/capacity-arrays",
  "dependency_lock": "/content/toolalign/requirements/cuda-linux-py312.lock.txt",
  "model_root": "/content/toolalign-private/models/Qwen3-1.7B",
  "output_dir": "/content/toolalign-private/runs/g2-continuous",
  "persistent_dir": "/content/toolalign-private/checkpoint-copies/g2-continuous",
  "max_optimizer_steps": 3,
  "max_wall_seconds": 600,
  "max_output_bytes": 536870912,
  "validation_every_steps": 2,
  "checkpoint_every_steps": 2
}
```

`max_optimizer_steps` 是累计停止步数。容量执行 `8+8+2`；第 2 步与最终第 3 步都验证并保存。恢复仍用同一 argv，使用新 `run_id`、新输出及副本目录，并新增：

```json
{
  "resume_from": "/content/toolalign-private/retrieved-checkpoint/step-000002-HASHPREFIX",
  "resume_checkpoint_sha256": "REPLACE_WITH_MANIFEST_CHECKPOINT_SHA256"
}
```

从第 2 步恢复到第 3 步时 `max_optimizer_steps` 仍为 3。`checkpoint_sha256` 定义为该目录 `state.pt` 的文件 SHA256。恢复身份绑定源码提交及实际包字节、数组/cohort、`run_kind/profile`、模型版本、配置、依赖锁及实际安装版本、GPU 类型/运行库和验证/保存节奏；路径、运行编号和本次资源上限可改变。容量状态不能作为 SFT 起点。

真实入口取得同一 Git common-dir 的 `GPULease` 后才使用 CUDA 和加载模型；没有 CUDA/BF16 支持即失败。父进程的内部截止时间或外部 SIGTERM 均会回收自有子进程组，不自动重试。SIGTERM 在清理后产生 `SystemExit(143)`，清理期间忽略重复 SIGTERM，随后恢复原信号处理器；启动阶段的 SIGTERM 等待自有 PID 登记后再进入清理。模型用固定本地文件、BF16 底座、FP32 Q/V LoRA、28 层/56 模块及已冻结参数数量；SDPA、关闭 cache、non-reentrant checkpointing。损失为每样本 completion+EOS token mean 后按实际组长取 mean；验证累计全部指定 validation 的 CE sum/token count。AdamW 使用冻结参数和恒定 LR。

`events.jsonl` 记录逐步 loss、数据游标、optimizer step 时间、验证及 CUDA peak allocated/reserved。容量 summary 还核对初始化 LoRA B 为零、adapter 前后内容变化，以及各一次实际 frozen parameter 内容 hash。容量标记 `diagnostic_only=true`、`validation_scope=capacity_cohort`、`epoch_complete=false`。

完整 checkpoint 目录含 `manifest.json`、`state.pt` 及必要时的 `best.pt`。state 保存 adapter、全部 Adam moments/步数、固定 LR、游标、Python/NumPy/Torch CPU/CUDA RNG 和上述身份。validation score 与历史 best 引用也受 `state.pt` 哈希覆盖；缺失 moments、错误计数或无效 RNG 在模型加载前拒绝。`torch.load` 使用 `weights_only=True`。目录在本地原子发布后再复制并读回第二目录，保留 best、last、最近一个不同的已评分 rollback；历史 best 的核心状态随 checkpoint 携带，恢复到新目录后可继续正确选模。

`persistent_dir` 是第二副本位置。远端 `/content` 中的第二份副本仅产生 `remote_copy_verified=true`，`durability_verified=false`。E1 必须回收完整目录到 Mac 专属私有位置、读回验证，再终止旧实例并上传到新实例恢复；外部持久化和跨实例结果由 S1/E1 记录。

## 实际验证与失败记录

在 S1 提供的专用 Mac CPU 环境运行，未安装或修改训练环境。Python 3.12.14；Torch 2.8.0、Transformers 4.57.6、PEFT 0.18.1、Accelerate 1.12.0、NumPy 2.2.6、tokenizers 0.22.2、Jinja2 3.1.6、safetensors 0.6.2、pytest 9.0.2。

| 检查 | 实际结果 |
|---|---|
| 三个 `test_cuda_sft*.py` 模块 | 17 passed，16.13 秒，exit 0 |
| 原创 tensor 范围 | 参数不超过 4,096、序列 8、每条训练轨迹不超过 3 updates、2 线程 |
| 新进程恢复 | 32 参数原创模型，连续 3 步与从第 2 步恢复 1 步，后续 loss/参数/Python、NumPy、Torch CPU RNG 一致；CUDA RNG 为空列表 |
| 非法恢复 | 空 Adam state、计数不符、失效 RNG、错误身份、缺失 manifest/完整标记及 score 替换被拒绝 |
| 运行入口 | lazy import/help 无框架导入、无 CUDA 明确失败、重复共享 lease 拒绝 |
| 真实 CPU 进程回归 | 外部 SIGTERM、内部超时、正常完成三种路径均回收自有子进程并恢复原信号处理器；未导入模型框架 |
| E1 真实依赖锁 | Linux hashed lock 48 pins 成功解析；Mac hashed lock 37 pins 与实际安装逐项匹配 |
| 提交源码绑定 | 提交 `95cf142` 的 73 个包文件与正在执行的包字节相符；核验过程无框架导入 |
| 静态与契约 | 定点 ruff、公开内容扫描通过；4 项冻结契约检查沿用本轮未受后续修改影响的成功记录 |

复现定点测试，`CUDA_CPU_PYTHON` 须指向 S1 锁定的环境：

```sh
cuda_sft_temp=$(mktemp -d "${TMPDIR:-/tmp}/toolalign-cuda-sft.XXXXXX")
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
  PYTHONPATH=src "$CUDA_CPU_PYTHON" -B -m pytest -q \
  tests/training/test_cuda_sft*.py \
  --basetemp="$cuda_sft_temp/pytest"
python -m ruff check src/toolalign/training/cuda_sft tests/training/test_cuda_sft*.py
python scripts/check_contract_freeze.py
python scripts/check_public_content.py
```

保留的开发期失败：首次数值运行 `11 passed, 1 failed`，独立 FP64 CE 与 FP32 sum 的差为 `6.81e-7`、即 `0.714 ULP`，原绝对容差 `6e-7` 小于一个 ULP；改为 2 FP32 ULP 后该测试通过，生产数值未改。另一个新增反例证实空 Adam moments 曾被接受，补齐状态与 RNG 检查后定点 2 项通过。两次初稿 F401 未使用 import 已移除。

初版 `6392f3c` 的 14 项测试通过后，S1 的进程边界反例指出外部 SIGTERM 会绕过默认清理。新增测试用实际 `supervise` 和独立会话中的原创 CPU 子进程再次复现：父进程退出码 `-15`，子进程仍存活，`1 failed, 2 deselected`；该测试随后只终止捕获到的自有子进程组。修复后新增三种进程路径与原数值测试共 17 项通过，原失败和成功运行中的四个子进程 PID 均已确认不存在。原日志和本轮精确命令/退出码保留在私有交接索引；这些开发期记录不冒充独立 R1 审核。

实现参考官方 [Torch 2.8 AdamW](https://docs.pytorch.org/docs/2.8/generated/torch.optim.AdamW.html)、[non-reentrant checkpoint](https://docs.pytorch.org/docs/2.8/checkpoint.html)、[PEFT 0.18.1 LoRA](https://github.com/huggingface/peft/blob/v0.18.1/src/peft/tuners/lora/config.py) 和 [Transformers 4.57.6 Qwen3](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3/modeling_qwen3.py)。本轮 Torch/PEFT 接口实际验证使用上述原创 CPU fixture。
