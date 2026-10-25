# 18｜CUDA 环境与 Colab 作业控制

本包提供独立依赖锁和 `setup / launch / status / recover / stop` 控制入口。当前证据为依赖解析、Mac CPU 接口检查和本地 fixture；真实 Linux 安装、CUDA 容量和新实例恢复由 S1 的有界运行配置验收。训练协议见 [Colab 工作流](16_COLAB_WORKFLOW.md)；本包不申请实例。

## 依赖选择

| 组件 | Linux x86_64 / Python 3.12 | Mac arm64 / Python 3.12 |
|---|---|---|
| PyTorch | `2.8.0+cu128` | `2.8.0`，供 CPU fixture 使用 |
| Transformers / PEFT / Accelerate | `4.57.6 / 0.18.1 / 1.12.0` | 相同 |
| tokenizers / Jinja2 | `0.22.2 / 3.1.6` | 相同 |
| safetensors / NumPy / huggingface-hub | `0.6.2 / 2.2.6 / 0.36.0` | 相同 |
| 完整锁 | [48 个包](../requirements/cuda-linux-py312.lock.txt) | [37 个包，含 pytest](../requirements/cuda-macos-cpu-py312.lock.txt) |

[PyTorch 官方历史版本页](https://pytorch.org/get-started/previous-versions/)列出 2.8.0 的 macOS 与 CUDA 12.8 wheel。所选 [Transformers 4.57.6 元数据](https://pypi.org/pypi/transformers/4.57.6/json)要求 `tokenizers>=0.22.0,<=0.23.0`，因此这里选择 `0.22.2`。它同时满足仓库原生 tokenizer 的既有守卫；Jinja2 保持 `3.1.6`。旧 Transformers reference 路径的 `5.16.1/0.23.2` 守卫保持原样，不能用本锁运行该旧 reference 路径。

固定版本包含 [Qwen3Config](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3/configuration_qwen3.py)和 [PEFT LoRA 配置](https://github.com/huggingface/peft/blob/v0.18.1/src/peft/tuners/lora/config.py)。共享 CPU 环境已实际导入这些接口以及 `Tokenizer.from_file`、Jinja2 sandbox，并构造 `r=8, lora_alpha=16, use_rslora=False, target_modules=[q_proj,v_proj]` 配置。此检查没有构造模型或读取模型权重，模型/数据语义由 T1 与 S1 验收。

[TRL 0.26.2 元数据](https://pypi.org/pypi/trl/0.26.2/json)要求 Transformers ≥4.56.1、Accelerate ≥1.4.0、datasets ≥3.0.0，可作为 G4 的候选。当前 SFT 锁不安装 TRL/datasets；DPO 锁、reference 与数值行为留给 G4。

锁由 `uv 0.12.5` 解析，截止时间固定为 `2026-10-26T00:00:00+08:00`；每个锁的头部保留完整生成命令。Linux 命令为：

```bash
uv pip compile requirements/cuda-linux.in --python-version 3.12 --python-platform x86_64-manylinux_2_28 --torch-backend cu128 --default-index https://pypi.org/simple --generate-hashes --only-binary :all: --no-python-downloads --exclude-newer 2026-10-26T00:00:00+08:00 --emit-index-url --output-file requirements/cuda-linux-py312.lock.txt
```

安装时保留全部 `--hash` 行，并同时提供 PyPI 与 CUDA wheel 索引。`setup` 使用以下固定安装计划，随后检查 Python 3.12、全部包版本和额外包：

```bash
python3.12 -m venv /content/toolalign/.toolalign-local/cuda-env
/content/toolalign/.toolalign-local/cuda-env/bin/python -m pip install --disable-pip-version-check --require-hashes --only-binary=:all: --extra-index-url https://download.pytorch.org/whl/cu128 -r /content/toolalign/requirements/cuda-linux-py312.lock.txt
/content/toolalign/.toolalign-local/cuda-env/bin/python -m pip check
```

无需修改 `pyproject.toml` 或旧 `uv.lock`。Mac 使用 S1 管理的单个专用 CPU 环境；不在 Mac 安装 CUDA wheel。

## 私有配置与目录

S1 先显式分配本任务的 `toolalign-*` 命名会话，读取实际 GPU/显存和分配时间，再部署已审精确 Git commit。实例需要 Git、tmux、控制端 `python3`（≥3.11）及 `python3.12`。这些是运行前置条件，`setup` 不安装系统包、模型或训练数据。

| 用途 | 路径/约束 |
|---|---|
| 唯一源码 checkout 与 GPU 锁根 | `repository = lock_root = /content/toolalign` |
| 依赖锁 | `/content/toolalign/requirements/cuda-linux-py312.lock.txt` |
| 专用 Python 环境 | `/content/toolalign/.toolalign-local/cuda-env` |
| 运行配置、日志、PID、退出记录 | `/content/toolalign/runs/RUN_ID/` |
| T1 输出 | `output_dir = /content/toolalign/runs/RUN_ID/output` |
| T1 的实例内复制目标 | `persistent_dir = /content/toolalign-staging/RUN_ID` |
| 会话登记与导出归档 | `/content/toolalign/.toolalign-local/colab/` |
| 已批准的 portable arrays | 私有 `array_dir`，仅 `manifest.json / train.jsonl / validation.jsonl` |
| Mac 持久副本 | 控制配置 `local_root/RUN_ID/recovered/download-*/files/` |

`toolalign-staging` 与源码都在实例本地盘。它证明一次本地复制/读回，实例回收时会一起丢失。持久恢复证据是下载到 Mac 后按完整清单读回的字节；停止实例前必须完成该步骤。

S1 另外冻结 T1 的 `toolalign.cuda-sft-run.v1` JSON：`authorized_by=S1`、run ID/kind/profile、精确 source/config/array-manifest/dependency-lock 身份、模型与数组路径、上表目录，以及 `max_optimizer_steps / max_wall_seconds / max_output_bytes / validation_every_steps / checkpoint_every_steps`。数据、模型 revision、训练预算由该配置决定；控制器不补默认训练参数。

Mac 控制配置使用以下结构。所有占位符必须替换，`max_allocation_seconds=0` 不能执行，需由 S1 填入本次预算；时间使用实际分配时刻。配置和身份文件放本机私有目录，不提交 Git。

```json
{
  "schema": "toolalign.colab-control.v1",
  "cli": "/ABS/EXISTING_ADC_PROXY_WRAPPER",
  "ssh_identity": "/ABS/EXISTING_SSH_IDENTITY",
  "run_config_file": "/ABS/PRIVATE/run.json",
  "run_config_sha256": "REPLACE_WITH_SHA256_OF_EXACT_RUN_JSON_BYTES",
  "run_id": "RUN_ID",
  "session": "toolalign-SESSION_NAME",
  "local_root": "/ABS/PRIVATE/.toolalign-local/colab",
  "allocated_at_utc": "REPLACE_WITH_ACTUAL_ALLOCATION_TIME_WITH_TIMEZONE",
  "max_allocation_seconds": 0
}
```

同一 endpoint 的不同 run 可以使用不同 `local_root`。停止时，当前 run 使用自己的目录，其余 run 默认查找当前 `local_root/RUN_ID/recovered.json`。若较早 run 存在其他位置，在执行 `stop` 的控制配置中加入显式映射；值是含 `recovered.json` 的本机 run 目录：

```json
{
  "recovery_directories": {
    "EARLIER_RUN_ID": "/ABS/OTHER_PRIVATE/.toolalign-local/colab/EARLIER_RUN_ID"
  }
}
```

该字段不改变训练 run JSON 或它的 SHA。任何已登记 run 缺少正确映射或完整副本都会阻止停止，不会被省略。

复用已安装的官方 CLI 及 ADC/proxy 包装。当前检查版本为 `google-colab-cli 0.7.4`。控制器使用独立 SSH 参数和私有 `known_hosts`，不改已有其他项目的 SSH alias、认证或环境。官方 [SSH 说明](https://github.com/googlecolab/google-colab-cli/blob/main/docs/06_ssh_access.md)提示代理可自动创建缺失实例，因此每次连接前检查具名会话及 endpoint；CLI 的“not found”即使退出码为 0 也视为不存在。

## 五个操作

从本地 checkout 执行，每一步检查返回结果后再进行下一步：

```bash
python3 scripts/colab/control.py --spec /ABS/PRIVATE/control.json setup
python3 scripts/colab/control.py --spec /ABS/PRIVATE/control.json launch
python3 scripts/colab/control.py --spec /ABS/PRIVATE/control.json status
python3 scripts/colab/control.py --spec /ABS/PRIVATE/control.json recover
python3 scripts/colab/control.py --spec /ABS/PRIVATE/control.json stop
```

`setup` 登记该实例/run 的所有权，安装或重新核对同一锁的环境，保存 `setup-exit.json`。它不导入框架、不运行模型或训练。已有部分环境或失败的同一 run 保留现场，不自动重装。

`launch` 核对精确源码/依赖锁和剩余预算，用 tmux 执行唯一训练命令：

```bash
/content/toolalign/.toolalign-local/cuda-env/bin/python -u -m toolalign.training.cuda_sft train --run-config /content/toolalign/runs/RUN_ID/run.json
```

训练保持离线环境变量，由 T1 获取同一真实 Git 根的 GPULease。控制器记录启动请求、PID、即时日志、真实退出码。超时后先向自有进程组发送 SIGTERM，父进程退出后仍继续确认组内成员；10 秒宽限后向残留成员发送 SIGKILL，再有界确认并回收直接子进程。两个确认阶段各至多 10 秒。`timeout_cleanup_completed=true` 才表示该次超时清理已确认；未确认时保存错误并拒绝导出，保留实例。T1 另建 session 的子进程由 T1 清理，组合行为另验。控制器不接受任意远程 shell 命令；已有启动声明、tmux 作业或已回收的 run 均不能重新提交。

断连或 SSH 超时后先 `status`。本地 `events/` 保留 SSH 输出和退出/超时记录，远端的 tmux 与退出文件决定作业状态。没有终态记录时不从“连接断了”推断运行完成，也不自动换实例或再启动训练。

`recover` 只导出终态 run 的完整目录，包含失败记录和 T1 全部 checkpoint 文件。远端生成文件大小/SHA-256 清单；Mac 下载归档后检查归档、清单、全部文件及目录边界，再回执远端。失败的下载尝试仍留在私有目录。该步骤不解析或执行 checkpoint；训练恢复的语义验证由 T1 负责。

`stop` 以远端该 endpoint 的全部登记 run 为完整清单。远端确认当前输出与各次回收快照一致、tmux 不活跃、共享 GPU 锁空闲，并禁止新 setup/launch。Mac 随后逐一匹配快照，校验每个 run 的归档 hash、清单 hash 和解包文件；较早 run 损坏或 tar 缺失也会阻止停止。对失败 run 使用其原控制配置再次 `recover`，再执行 `stop` 即可。确认全部副本后才停止具名会话，并读回“会话不存在”。本地 `stop-inventory.json` 保留完整远端清单，用于停止响应不确定而实例已消失时的再次核对。同名 endpoint 变化会拒绝停止。`stopped.json` 记录从实际分配到停止的总时长，包含安装、空闲、失败和传输；它不是费用账单。

运行与 setup 会使用剩余分配预算，S1 须为回收留出时间。回收/停止在预算到期后仍可执行，以保存数据并释放资源；控制器没有离线自动停机服务。关闭本地终端也不会释放实例。

## 同实例与新实例恢复

同实例重连只执行 `status`，不产生第二份训练。新进程续训使用新的 run ID、输出目录和 staging 目录，并在 run JSON 内指定 `resume_from`（完整 checkpoint 目录）及 `resume_checkpoint_sha256`（checkpoint manifest 中的 `checkpoint_sha256`，对应状态文件）；训练入口参数不变。

新实例恢复必须先在旧实例执行 `recover`，取得 Mac 上完整 checkpoint 并验证，再停止旧实例。S1 显式建立新命名实例，以同一 source/config/data/model/dependency 身份重建环境，只上传本次所需的已批准 arrays、模型及已验证 checkpoint；为新 run 重新冻结控制配置与分配时间。

首个 formal 容量探针计划采用固定最长 cohort 的 18 train + 2 validation，按 8+8+2 形成三次 optimizer update，验证/保存 cadence 为 2。从 step 2 checkpoint 恢复时 `max_optimizer_steps` 仍为累计 3，不能解释为额外三步；capacity 不能切成 sft。实际 run ID、cohort 身份和预算由 S1 提供。只有真实新实例恢复成功后才能登记为通过。

本地复现控制测试：

```bash
python -m pytest -q tests/colab --basetemp /ABS/NEW_EXCLUSIVE_TMP_DIRECTORY
ruff check scripts/colab tests/colab
```

`--basetemp` 必须使用新建独占临时目录，不指向既有证据目录或其祖先。fixture 中的 CLI/SSH/tmux 替身不是 Colab 实测；测试使用原创小文件，失败/超时子进程和归档读写在 CPU 上真实执行。
