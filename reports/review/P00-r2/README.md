# P00 / R1 修订二独立证据

日期：2026-09-06；执行方：本次独立 R1 对话；结论：**PASS**。精确 candidate 为 `5d30e1b4bd5e2284abbe59a5f16b2966f85feb87`，规划 base 为 `0f152e287bbc0e1c3edfb3f6f3794eb8d36c422f`，首轮 candidate 为 `15706079c9516197b67dd59a19a0d0c4aa5adea8`。完整关闭情况、优先级、G0 范围及 NOT_RUN 见 [交接单](../../../coordination/handoffs/P00-review-r2.md)。

## 复现

在该 candidate 加入本目录审查文件后执行：

```bash
uv sync --locked --python 3.14
uv run --locked pytest -q
uv run --locked pytest -q reports/review/P00/test_independent.py
uv run --locked pytest -q reports/review/P00-r2/test_revision_boundaries.py
uv run --locked ruff check .
uv run --locked python scripts/check_contract_freeze.py
uv run --locked python scripts/check_public_content.py
uv build
uv run --locked python reports/review/P00/verify_wheel.py
uv run --locked python reports/review/P00-r2/verify_revision_scope.py
```

默认 pytest 只发现 `tests/`，必须显式执行两个 review 探针文件。本轮实测分别为 **58 / 46 / 72 passed**，没有 xfail/skip。新探针全部使用合成记录、临时 Git repo/markers；不执行工具业务、模型或 GPU 工作，不下载模型/数据。

`verify_revision_scope.py` 只读 Git 历史，检查精确 candidate 的祖先、src 修复范围、未改的 wire 结构/接口/锁/依赖、原始审查证据字节、现有测试前缀与冻结摘要。它需要本仓库已有的首轮审查 commit `66521f8aad1a2ed529660b18aa099208c2e0bb09`；只含远端候选历史的新 clone 也可能缺少此本地对象，不能将脚本无法比较误写为通过。

`verify_wheel.py` 在新临时 Python 3.14 venv 以带 hash 的锁定依赖安装 wheel，离开源码目录验证五类 CLI、安装后 schema 摘要与依赖闭包，确认导入来自 venv 且无 MLX/PyTorch。此轮构建在新增审查文件之前完成，因此 wheel 对应精确 candidate；报告文件不进入 wheel 源包。

## 本轮实际命令

原始 stdout+stderr 保存在本审查工作区私有目录 `.toolalign-local/review-r2/logs/`，索引为 `.toolalign-local/review-r2/index.jsonl`。下表日志名相对此目录；hash 是本轮原始字节摘要。相同输出可能产生与 S0 相同 hash，不能据此推断复用日志。日志 hash 用于关联证据，不单独证明结论正确。

| 命令 | 退出码 / 实测 | 日志名 | SHA-256 |
|---|---|---|---|
| `uv sync --locked --python 3.14` | 0；干净 venv，Python 3.14.7 | `sync.log` | `18ca9e0867cb165fa1f6cd8d68ad751352010ddd7d91cfcd258d77df812b881c` |
| `uv run --locked pytest -q` | 0；58 passed | `pytest.log` | `7c2cae2b1d1d30691368a57f565ff0c67fc8acdd52e176ba314259eb36701158` |
| `uv run --locked pytest -q reports/review/P00/test_independent.py` | 0；46 passed | `r1-probes.log` | `402b37eb60fbcf4267bd0f82de9fe9335845f3faca28bd7b13fa25c62e42f48a` |
| `uv run --locked ruff check .` | 0；干净候选 | `ruff-candidate.log` | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `uv run --locked python scripts/check_contract_freeze.py` | 0；4 files | `freeze.log` | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| `uv run --locked python scripts/check_public_content.py` | 0；干净候选 89 paths，index 与工作副本 | `public-candidate.log` | `1d01607972747b89fb06d31de3628956c0baccc976b643df6f4355b78ceb0878` |
| `uv build` | 0；sdist + wheel | `build.log` | `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75` |
| `uv run --locked python reports/review/P00/verify_wheel.py` | 0；所有内部步骤退出 0 | `wheel.log` | `d162c8df2a10a2e887cfe940e0cad6575b336825424f264f910502909b1fbfb5` |
| `uv run --locked pytest -q reports/review/P00-r2/test_revision_boundaries.py`（初次） | 1；69 passed，3 setup errors；见下文 | `r2-probes.log` | `b6118def4b2e8347b50e7e2886410a81be0abe768736bade6881554f8e309b3e` |
| `uv run --locked pytest -q reports/review/P00-r2/test_revision_boundaries.py`（最终） | 0；72 passed | `r2-probes-final.log` | `66784a44a979016318def1ad73f4cfabcc5acb7898e42b2220ba673a1579e687` |
| `uv run --locked python reports/review/P00-r2/verify_revision_scope.py` | 0；范围/字节/祖先检查 | `scope-audit.log` | `60a743024f18d0019739b01148e3947270aade15e29eae7f47ca47d4ca2b2693` |
| `uv run --locked ruff check .`（新增探针后） | 0 | `ruff-final.log` | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `uv run --locked python scripts/check_public_content.py`（审查文件暂存后） | 0；93 paths，index 与工作副本 | `public-staged-review.log` | `2da4533de232f72bce2075bc070276b8624c933ecc6ec69cf66f4a1299d2d132` |

提交范围检查确认精确 candidate/分支、仅四个允许新增文件、index 与工作副本一致、没有其他改动，以及身份文件私有且被 Git 忽略。该本机检查日志为 `submission-audit.log`，退出 0，SHA-256 为 `05d345ecc3a95e1547e5bcc9a9e68bda1f2988716291b81ec2f019a9854669ba`；脚本位于私有目录，不含在交付代码中。

初次新增探针的三个 setup errors 发生在临时仓库 `git init` 前：pytest 自动参数名包含约 1 MiB 的 bytes payload，进入 `PYTEST_CURRENT_TEST` 后子进程创建报 `OSError: [Errno 7] Argument list too long`。只为该参数组增加短 `ids`，未改测试输入、断言或候选实现；随后 72 项全部通过。初版探针留私有副本，SHA-256 为 `4aa1c1c60ece1a023a7d7175fe827204ed3f2ad5cb2e67f95f04920befbb68e4`。此错误如实保留，不计作候选产品缺陷或静默丢弃的测试。

## 产物摘要

| 对象 | SHA-256 |
|---|---|
| 精确 candidate 构建 wheel | `66a238292f0aeb622eadf1e40b65af6aead9dcb1379e568097e511f38a0549b0` |
| candidate / 安装后 schema | `ce17b0a5bc4e8363e1d67bf125212444bab1103ddfc0c4e390bef82afce881cb` |
| 本目录最终 `test_revision_boundaries.py` | `3954bafab52b3dd5584bf775e929da75e2dd4f3c29795cc6e6976ccadf80b9b9` |
| 本目录 `verify_revision_scope.py` | `398aeb6193c860561d75ba897a1d813ee8bd8499d28b52a42539f8bd1867313b` |

## 新探针覆盖

| 原问题 | 新增检查 | pytest 项数 |
|---|---|---:|
| R1-01 | 七种 type × 两种层级的隐藏 schema 拒绝；enum/description 数据正控 | 15 |
| R1-02 | 三来源 × 三类坏内容；大小边界/两种普通模式；symlink/gitlink；冲突 stage；父目录 symlink；敏感文件名脱敏 | 16 |
| R1-03 | 五类自由键的 ContractError 文本及 JSONL CLI 隐私 | 5 |
| R1-04 | 导出 bundle 全部 35 个 pattern 节点，含有效/越界/末尾字符断言 | 35 |
| R1-05 | 两轮调用的合法延续、全部历史 ID 冲突及目标内部重复 | 1 |

公开目录仅含本说明和两个原创小脚本；原始日志可能含临时路径，不提交。真实任务 ID、worktree 绝对路径及任务身份文件也不提交。剩余 P0/P1/P2 均为 0；PASS 仅建议 S0 集成上述 P00 candidate，main 重验与后续阶段仍是 NOT_RUN。
