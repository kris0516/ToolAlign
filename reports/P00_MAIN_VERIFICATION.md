# P00｜main 集成验证

日期：2026-09-06；执行者：S0；结论：**VERIFIED**。

- 合并：[PR #2](https://github.com/kris0516/ToolAlign/pull/2)，main commit `cd091e3a53986b59b170baf5b746644f369135d1`。
- 独立 R1-r2 PASS 的实现候选：`5d30e1b4bd5e2284abbe59a5f16b2966f85feb87`；原 SHA 保留的审查提交：`441d31bebd5ca4d46755642f94966c07bbcc4ad1`。
- 合并前最终 PR head：`708642448395be91357275a9a26def981a9f4110`，其后仅有 GitHub merge。实现与被审候选一致。
- [CI run 33995402202](https://github.com/kris0516/ToolAlign/actions/runs/33995402202)：Python 3.11 / 3.14 全部步骤 success；CI 覆盖 58 项基础和 46 项原始探针。
- main 重验时间：`2026-09-05T22:17:00.141506+00:00`；58 项基础 + 46 项原始独立探针 + 72 项新增独立探针 = **176 PASS**。

## 本机命令证据

下列检查均在合并后的 main 执行，未加载模型。原始 stdout/stderr 留在本机私有证据目录，公开仅保留命令、退出码及原始日志 SHA-256。

| 命令 | 退出码 | 日志 SHA-256 |
|---|---|---|
| `uv sync --locked --python 3.14` | 0 | `f3ec7c136851e9b2f821d78de66af8954db55eb457f6c52ce82db722c26a64f6` |
| `uv run --locked pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py` | 0 | `4d5517a19ac248996a1990f3f424782d8496215a1c0af7bbc0e76ac2988adece` |
| `uv run --locked ruff check .` | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `uv run --locked python scripts/check_contract_freeze.py` | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| `uv run --locked python scripts/check_public_content.py` | 0 | `2da4533de232f72bce2075bc070276b8624c933ecc6ec69cf66f4a1299d2d132` |
| `uv run --locked toolalign validate tests/fixtures/contracts/example.json` | 0 | `df16404f52f1efe75f1cabaf219cbb7ea8e60f92cb6c5b9a135986b51e90247e` |

独立 wheel 安装、严格 schema 边界、离线安装与跨 worktree 锁证据见 [R1-r2 报告](review/P00-r2/README.md) 和 [交接](../coordination/handoffs/P00-review-r2.md)。公开扫描检查 index 和工作副本共 93 条路径，是启发式检查，不能证明任意数据不存在敏感内容。

## 交付边界

P00 的 CPU 契约基础已完成；它不代表训练、数据集审计、语义执行器、benchmark 或推理服务已经完成。P01–P03 的依赖门已通过；S0 第一批只分发 P01 与 P02，后续仍按独立审查、合并、main 验证推进。
