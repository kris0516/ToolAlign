# S0-SHARED-01 main 集成验证

日期：2026-09-06；结论：**VERIFIED**。

[PR #3](https://github.com/kris0516/ToolAlign/pull/3) 合并为 `18fc8475476f6becf684ba817480caeb96a7cfb9`。独立 R1 PASS 精确生产候选 `e4127d9a0e6e30b091cba9b9e22a5fbb7091e9a2`，报告提交 `8ceea3fbdd476ef0a5583e82e38473f1038dc650`，剩余 P0/P1/P2 为 0。最终 head `e9b33b0e279b64c55f5d78220c7c79c62738a3f5` 仅在报告后增加 S0 协调文档和用户模型设置保护，未改依赖/政策/冻结代码。

[最终 head CI](https://github.com/kris0516/ToolAlign/actions/runs/33997792354) 的 Python 3.11 与 3.14 jobs 每一步均 success。CI 执行基础测试与 P00 第一轮独立探针；本机 main 集成额外执行 P00-r2 和 S0-SHARED-01 独立探针，共 **233 项全部通过**。不把 CI 的测试范围扩大描述成 233 项。

## 在合并 main 上实际执行

| 命令 | 退出码 | 原始日志 SHA-256 |
|---|---:|---|
| `uv sync --locked --python 3.14` | 0 | `39a1fa63d6e6c900ccea999e458cd100046d3c7bf3d335534c2b56151da3a974` |
| `uv build` | 0 | `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75` |
| `uv run --locked pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py reports/review/S0-SHARED-01/test_boundaries.py` | 0 | `c2fc8f54f47e247ad725e7829beecc7e2c9f3eddedb444827e3f0779bb95dfda` |
| `uv run --locked ruff check .` | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `uv run --locked python scripts/check_contract_freeze.py` | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| `uv run --locked python scripts/check_public_content.py` | 0 | `94b2e45bc18d2df975cc74e0ba4deeba26992f0df77395f3d69e699de140279d` |
| `uv run --locked python reports/review/P00/verify_wheel.py` | 0 | `3f96f340c368d61c660017289bba9ff17ff591449c8b3abd31e548d0f63e8153` |

原始日志和 summary 在私有 `.toolalign-local/evidence/shared-support/main/`，各命令记录真实时间、完整参数、退出码与字节摘要。新 wheel 的 SHA-256 为 `b2e4f5b81d63721e248e066476432b524939bd82a0214b586f53b21c15edcb98`，与 R1 独立构建一致；临时 Python 3.14.7 环境离开源码验证五类 schema、CLI、依赖与无 ML 后端导入，全部通过。

合并前 S0 首次跑新增探针时遗漏 `uv build`，旧 P00 dist wheel 缺少新 extra metadata，56 PASS / 1 FAIL；旧 wheel 与失败说明已私有保留。构建当前候选后未修改探针，57 项通过。本次 main 先 build 后完整回归，无失败。

## 可使用范围

T1/D1 可合并此已验证基线及后续 S0 协调状态提交，采用 compatibility extra 与固定 ToolACE 来源政策。政策字节 SHA-256 仍为 `b8c4cd238bbf27d3378dadcd4130ac44c4c991ace6315bf385f104c4f98f72f7`，冻结契约未变。保留原 code_base、授权、worker checkpoint 与实际整合提交，非强制合并，不覆盖其未提交工作。

本验收不批准备用 DPO 包、P01 模型/数学结果、P02 normalizer/人工质量门或 P03 执行器；这些继续各自独立审查。默认环境/本次验证仅 CPU，没有加载模型或修改系统内存限制。当时仅同步了 S0/子任务区分的文档和自动跟进，未核验 UI 设置保护实际生效；用户随后指出再次降级，该规则已由 ADR-0014 的全任务 gpt-6-astra/max 取代。
