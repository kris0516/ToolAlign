# P01 复现入口

本文件给出与最终通过配置相同的受限重放步骤；历史运行的精确 commit、配置 hash、原始日志 hash 见 [结果](P01_RESULTS.json)，不是声称以下新 run 已执行。只在 S0 分配资源后按序运行；不自动进入正式训练。当前候选的公共 compatibility extra 不足以执行完整 replay，原因见 [报告](P01_REPORT.md)。

## CPU 基础检查

在 P01 checkout 根目录：

```bash
uv sync --locked --python 3.14
uv run --locked pytest -q
uv run --locked pytest -q tests/training/compatibility/
uv run --locked ruff check .
uv run --locked python scripts/check_contract_freeze.py
uv run --locked python scripts/check_public_content.py
uv run --locked python -m toolalign.training.compatibility --help
uv build --wheel
uv run --locked python reports/review/P00/verify_wheel.py
```

已有独立审查测试一起运行的本轮入口是：

```bash
uv run --locked pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py reports/review/S0-SHARED-01/test_boundaries.py
```

sdist 发现的只读复现（已知公共基线退出 1；不会创建 archive）：

```bash
uv run --locked --with hatchling==1.27.0 python reports/hardware/P01_CHECK_SDIST_SELECTION.py
```

S0 修复前不运行完整 sdist 构建。若要验证其 `.git` 文件场景，使用确实含私有标记文件的 worktree，不能只在干净主 checkout 枚举后宣称边界通过。

## 私有探索环境与下载

T1 实际环境是 `.toolalign-local/venv`，下面的 `replay-venv` 是新复现环境示例，未在本轮另建。完整精确清单固定所有 88 包，但未携带公共 uv lock 的所有制品 hash；已安装包源码/wheel/license 身份另存报告。正式分组待 S0 发布后使用其锁，禁止把这些命令叫作公共 locked 环境已验证。

```bash
uv venv --python 3.14 .toolalign-local/replay-venv
uv pip install --python .toolalign-local/replay-venv/bin/python -r reports/hardware/P01_EXPLORATION_REQUIREMENTS.txt
HF_HUB_DISABLE_IMPLICIT_TOKEN=1 .toolalign-local/replay-venv/bin/hf download Qwen/Qwen3-0.6B --revision c1899de289a04d12100db370d81485cdf75e47ca --include '*.json' --include '*.safetensors' --include '*.jinja' --include '*.txt' --include '*.md' --include LICENSE --local-dir .toolalign-local/models/qwen06 --dry-run
HF_HUB_DISABLE_IMPLICIT_TOKEN=1 .toolalign-local/replay-venv/bin/hf download Qwen/Qwen3-1.7B --revision 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e --include '*.json' --include '*.safetensors' --include '*.jinja' --include '*.txt' --include '*.md' --include LICENSE --local-dir .toolalign-local/models/qwen17 --dry-run
```

检查未 gated、许可、下载空间与 20GiB 总私有预算后，去掉对应 `--dry-run` 下载；已有缓存无需重复下载。保留 HF 下载 metadata，模型入口会核对 revision 和 LFS hash。不得依靠登录 token 下载不同权重。模型入口只从显式本地路径加载，并设置 HF offline/禁隐式 token/禁 telemetry/W&B disabled；`trust_remote_code=False`。

## 生成受限配置

下面只生成配置，不加载模型。实际输出目录必须尚不存在；新一次重放换 run_id/输出目录，保留旧证据。配置没有原始私有训练数据；samples.py 现场生成 32 条原创 smoke 内容。

```bash
python3 - <<'PY'
import json
from pathlib import Path

private = (Path.cwd() / '.toolalign-local').resolve()
config_root = private / 'replay-configs'
config_root.mkdir(parents=True, exist_ok=True)

def save(name, config):
    config.update(run_id='p01-replay-' + name,
                  output_dir=str(private / 'replay-runs' / name),
                  lock_timeout_seconds=0)
    (config_root / (name + '.json')).write_text(json.dumps(config, indent=2) + '\n')

budget = dict(max_wall_seconds=900, max_microsteps=40,
              max_processed_tokens=131072, max_mlx_bytes=24*1024**3,
              max_rss_bytes=30*1024**3, max_swap_growth_bytes=1024**3,
              max_disk_bytes=20*1024**3)
smoke = dict(mode='smoke', model_id='Qwen/Qwen3-0.6B',
             model_revision='c1899de289a04d12100db370d81485cdf75e47ca',
             model_dir=str(private / 'models' / 'qwen06'), budget=budget,
             sequence_length=1024, sft_steps=32, sft_accumulation=8,
             warmup_steps=8, dpo_steps=8, dpo_accumulation=1,
             dpo_backend='mlx-lm-lora', fallback_accumulation=8,
             fallback_disable_compile=True)
save('smoke06', smoke)
for length in (1024, 1536, 2048):
    config = dict(smoke, mode='calibrate', model_id='Qwen/Qwen3-1.7B',
                  model_revision='70d244cc86ccca08cf5af4e1e306ecf908b1ad5e',
                  model_dir=str(private / 'models' / 'qwen17'),
                  sequence_length=length, sft_steps=112,
                  fallback_grad_checkpoint=length >= 1536,
                  budget=dict(budget, max_microsteps=120,
                              max_processed_tokens=524288))
    save('calibrate17-' + str(length), config)
save('math', dict(mode='math', budget=dict(budget, max_wall_seconds=180,
     max_microsteps=1, max_processed_tokens=1, max_mlx_bytes=2*1024**3,
     max_rss_bytes=8*1024**3)))
PY
```

`dpo_accumulation=1` 仅为历史首选候选字段；所选备选实际使用 `fallback_accumulation=8`，每 8 微步一次更新，回调验证真实 optimizer.step。

## 顺序执行与验收

```bash
PYTHONPATH=src .toolalign-local/replay-venv/bin/python -m toolalign.training.compatibility audit --output .toolalign-local/replay-audit.json
PYTHONPATH=src .toolalign-local/replay-venv/bin/python -m toolalign.training.compatibility math --config .toolalign-local/replay-configs/math.json
PYTHONPATH=src .toolalign-local/replay-venv/bin/python -m toolalign.training.compatibility smoke --config .toolalign-local/replay-configs/smoke06.json
```

CPU 数值、真实训练初始 ln2、冻结/reference/scaling/重载和资源门槛都通过后，按 1024→1536→2048 逐次运行，下档不能在上档失败时自动开始：

```bash
PYTHONPATH=src .toolalign-local/replay-venv/bin/python -m toolalign.training.compatibility calibrate --config .toolalign-local/replay-configs/calibrate17-1024.json
PYTHONPATH=src .toolalign-local/replay-venv/bin/python -m toolalign.training.compatibility calibrate --config .toolalign-local/replay-configs/calibrate17-1536.json
PYTHONPATH=src .toolalign-local/replay-venv/bin/python -m toolalign.training.compatibility calibrate --config .toolalign-local/replay-configs/calibrate17-2048.json
```

真正的历史命令使用 `.toolalign-local/venv/bin/python` 与该 run 保存的配置。原始目录由 `config.json.run_id` 映射：T1 私有根 `.toolalign-local/runs/*/` 内含 `config.json`、`run.json`、`resources.json`、`stdout.log`、`result.json` 或 `partial-result.json`、`progress.json`、`failure.json`（如有）、逐步日志和 adapter。原始配置包含本机路径，不公开。R1 可只读本机证据并按结果 JSON 核对 hash；不能修改旧 config/output 后称为原始重现。

可在私有输出文件中重建去敏汇总，脚本会重新验证所有已冻结 manifest 的制品：

```bash
uv run --locked python reports/hardware/P01_BUILD_REPORT.py --private-runs .toolalign-local/runs --output .toolalign-local/rebuilt-summary.json
```

退出 0 不自动 PASS：例如历史 smoke06-r2 必须按真实训练 steps 降级。资源终止退出 124、其他失败通常为 2；核对 stop_reason/failure，而非把不完整 DPO 记成 8 微步。math 没有假造训练 manifest，其 JSON/日志/资源 hash 单独登记。
