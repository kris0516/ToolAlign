# P00｜仓库启动与契约冻结

状态：CHANGES_REQUESTED；S0 已领取。P01–P03 保持 BLOCKED，R1 独立审查与 main 集成验证前不解锁。

| 字段 | 初始值 |
|---|---|
| owner 角色 | S0 |
| 依赖 | 无；先确认本地/远端真实状态 |
| base commit | 0f152e287bbc0e1c3edfb3f6f3794eb8d36c422f |
| branch/worktree | `work/p00-bootstrap-contracts`；S0 主项目 checkout；R1 使用 App 独立 worktree |
| 契约 | `toolalign.contracts.v1` 候选，包含 example/tool/preference/run/trace.v1；摘要见 `contracts.v1.lock.json` |
| 交接 | `coordination/handoffs/P00-r1.md` |

## 目标

创建或验证用户授权的新公开仓库；建立可安装最小 Python 项目、shared contracts、测试入口、资源锁接口、目录与分支规则。

## 允许修改范围

`src/toolalign/contracts/`、`src/toolalign/runtime/`、顶层 Python/CLI 基础文件、模块空目录、`pyproject.toml`/`uv.lock`、`configs/`、CPU 测试/CI、检查脚本、最小原创 fixtures、coordination、AGENTS/README 与 P00 契约说明。后续模块实现不在 P00 范围。

除此之外文件默认只读；公共契约、依赖锁和main合并权归S0。路径尚未创建时，先核对P00结构，不能各自发明一套。

## 非目标

不训练正式模型，不自动创建付费资源，不在未冻结接口时并行展开全部模块。

## 验收

新仓库 URL/public/commit 读回；contracts 正反样例；CPU 测试可在无 MLX 环境启动；锁位置跨 worktree 一致；公开内容扫描。

已落实的命令与预期：

- `uv sync --locked --python 3.14`：干净虚拟环境安装成功，不引入 MLX/PyTorch。
- `uv run --locked pytest -q`：contracts 正反例、train-only 偏好、oracle 投影隔离、锁跨进程/跨 worktree/异常退出全部通过。
- `uv run --locked ruff check .`：无 lint 错误。
- `uv run --locked python scripts/check_contract_freeze.py`：schema、validator、interfaces、protocol 配置与摘要一致。
- `uv run --locked python scripts/check_public_content.py`：候选公开文件无阻断命中；人工复核补充。
- `uv build` 后在独立临时 venv 从 wheel 安装，`toolalign validate` 能离开源码目录执行。

R1 读取明确 base/head，复现必要正负测试，只提交审查证据；S0 根据 PASS 再合并并在 main 重跑核心检查。

## 资源

任何模型加载/训练/大批生成都先申请全局GPU锁。默认零外部付费；具体token/内存/时间预算使用P01实测。不要把其他worktree的空闲误认为GPU空闲。

## 阻塞处理

现有同名仓库、错误 GitHub 身份、无写权限时停止远端写入，保留本地状态；不要重建或覆盖。

## 交接要求

使用../templates/HANDOFF.md；附关键输入输出、个人应理解的技术点、真实commit、未完成项和独立审查请求。自测通过不自动变成MERGED/VERIFIED。

## 领取登记

S0；领取时间 `2026-09-05T21:19:08.074530+00:00`；规划基线 `plan-v0.1` / 协议 `coordination.v1`；工作目录和真实 task ID 记录在本机私有映射。无模型加载，零外部费用。
