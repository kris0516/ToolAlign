# P00 自测与构建证据

日期：2026-09-06；实现方 S0；基线 `0f152e287bbc0e1c3edfb3f6f3794eb8d36c422f`。

这份是实现方自测，**不是独立审查**。当前 34 项 CPU 测试通过，覆盖五类 schema 正反例、训练集偏好约束、模型输入隔离、参数 schema 范围、UTC/退出状态和 artifact 路径、跨进程竞争、异常退出与跨 worktree 锁一致性。

实测 Python 3.14.7 / uv 0.12.5。运行时间/设备路径等原始输出留在本机 `.toolalign-local/evidence/`，R1 可本机复核。下表 SHA-256 对应每项完整原始 stdout+stderr；哈希本身不替代复现。

| 检查 | 退出码 | 原始日志 SHA-256 |
|---|---|---|
| pytest | 0 | `7b39c9b2a80d4255d19e8a52e880560278af39219d368269c21dcbd9e9768e94` |
| ruff | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| contract-freeze | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| public-scan | 0 | `2cbb72217041e1d7a5ee3a0183f02275c8700d7fbbad83564974640747a1ce45` |
| build | 0 | `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75` |
| runtime-export | 0 | `d7b86dcfa1a13f8ef0d2a624d8e1f582e22e545fc9043f3c504baf3cbace0319` |
| wheel-venv | 0 | `3d71356eee3da2dfa9c7e32a633e59eb7821d94f0535e248e3b7c52d6a71df07` |
| wheel-dependencies | 0 | `95bec7f68fb3f0ba93c14ac5ed6d117e1a24a6a448c57d0246185915df3cb983` |
| wheel-install | 0 | `0dfaaba171da1d02155a1404d805bae00f9a1d04dd282ea818b5e3718712959b` |
| wheel-validate | 0 | `df16404f52f1efe75f1cabaf219cbb7ea8e60f92cb6c5b9a135986b51e90247e` |
| wheel-no-mlx | 0 | `15c82806f415a6846ad07794914b46e8fd58a85426ae63cb3327ab0a9392faec` |

## 重建入口

`uv sync --locked --python 3.14`；`uv run --locked pytest -q`；`uv run --locked ruff check .`；`uv run --locked python scripts/check_contract_freeze.py`；`uv run --locked python scripts/check_public_content.py`；`uv build`。

Wheel 检验：导出锁定的非 dev 依赖到本机临时 requirements，创建独立临时 Python 3.14 venv，按 hash 安装依赖，再用 `uv pip install --no-deps` 安装构建 wheel。离开源码目录执行 `python -m toolalign.cli validate` 校验 example fixture，成功；同时确认 MLX/PyTorch 未安装而可加载随 wheel 分发的 schema。

## 未完成/限制

- GitHub CI 在 push 后读回，当前此报告不声称远端 CI 已跑。
- 没有加载、训练、评测或部署任何模型；吞吐、内存、语义任务结果全部 NOT_RUN。
- 偏好 oracle 标签是原创 schema fixture，不是实际训练对或有效率证明。
- GPU 锁是同仓库 worktree 间的 advisory flock；跨 clone/非协作 GPU 进程需 S0 统一调度。
- 公共内容扫描为启发式，需 R1 和 S0 复核，不声明完全无隐私风险。
