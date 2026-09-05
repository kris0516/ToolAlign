# P00 修订二自测证据

日期：2026-09-06；执行方 S0。相对于独立审查候选 `15706079c9516197b67dd59a19a0d0c4aa5adea8`，本修订修复 R1-01 至 R1-05 全部问题，尚需新的独立 PASS，不能以本报告代替。

原始 R1 审查提交 `66521f8`，S0 cherry-pick 后为 `5fe2536`，内容保留在 `coordination/handoffs/P00-review-r1.md` 和 `reports/review/P00/`；两个 SHA 的映射如实登记。

## 修复与回归

- Tool schema 按 type 限制关键词，拒绝不适用位置中的 schema；不改变 enum/description 作为数据的性质。
- 发布扫描实际 Git index blob 及工作副本，分别核对内容/模式/大小；暂存敏感内容后只清理工作副本仍失败。合成凭据值不出现在输出。
- 校验错误仅给受信 schema 路径，避免输出输入自由字典键。
- v1 所有身份/时间 pattern 采用兼容 JSON Schema 的完整字符串约束，末尾 LF/CRLF/Unicode 行分隔符都拒绝。
- 历史与目标 call ID 联合查重；换用新 ID 的目标可继续下一轮前缀。

结果：基础 **58 passed**；原始 R1 独立 probes **46 passed**（本次执行方是 S0）。ruff、冻结摘要、公开扫描、构建及独立临时 wheel 环境检查均退出 0。Python 3.14.7；wheel 中五类 schema/CLI、无源码路径导入、无 MLX/PyTorch 和依赖闭包检查通过。冻结摘要已按 ADR-0010 更新；未合并契约保持 v1 候选。

| 检查 | 命令 | 退出码 | 原始日志 SHA-256 |
|---|---|---|---|
| pytest | `uv run --locked pytest -q` | 0 | `6c89339bf43bcf266aba432c0548e7a83dd402ef774bb808ce11d1dca5d96a5e` |
| r1-probes | `uv run --locked pytest -q reports/review/P00/test_independent.py` | 0 | `9c717a990d25b5bb9875df2c98b03f903a52d8235fbff31fc7999faf883985a3` |
| ruff | `uv run --locked ruff check .` | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| freeze | `uv run --locked python scripts/check_contract_freeze.py` | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| public-scan | `uv run --locked python scripts/check_public_content.py` | 0 | `3adcb6f5049f62d8000d5b4f4a999b384861690ab525799b8e981d489d0c4b80` |
| build | `uv build` | 0 | `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75` |
| wheel | `uv run --locked python reports/review/P00/verify_wheel.py` | 0 | `d162c8df2a10a2e887cfe940e0cad6575b336825424f264f910502909b1fbfb5` |

原始日志分别保存于本机 `.toolalign-local/evidence/p00-r2/`，首轮日志没有覆盖。日志 hash 用于本机取证关联，不能独立证明结果正确。GitHub CI 在此修订推送后另读回；P01–P03、模型/数据下载、训练、正式评测和服务部署均未进行。下一步对精确新 SHA 安排独立复核。
