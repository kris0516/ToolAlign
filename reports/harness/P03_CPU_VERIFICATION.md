# P03｜CPU 实现自测证据

日期：2026-09-06；owner E1；结论：**实现候选已自测，等待独立 R1**。此报告不授予阶段验收，不代表模型 benchmark。

## 精确身份与范围

- code base：`97466a20f599f68c511b9c8a71fe5f2cdfd9ad4b`。
- authorization commit：`e882594da84359b7f6ced7dd6aefdb9c7ce06209`；授权副本、真实任务身份与本机路径私存。
- 实现提交：`8afb114bd14e69d3a2138212ab423147809fed63`；Git tree：`c4230035c29dae8598504cb71d06b56a8fb12cba`；branch：`work/p03-execution-harness`。
- 契约：`toolalign.contracts.v1` / `toolalign.protocol.v1` / `coordination.v1`。公共 contracts/runtime/CLI/configs/依赖/CI/AGENTS/看板/ADR 未修改。
- 实测环境：CPython 3.14.7、macOS 26.5.1、arm64、Apple M5 Pro、51,539,607,552 bytes 物理内存。纯 CPU，未导入模型包、下载权重或申请 GPU。

## 实际命令、退出码与日志 SHA-256

原始 stdout/stderr、每条 argv、UTC 开始时间、退出码、head 与 index tree 写在本 worktree 的 `.toolalign-local/p03/checks/`，不提交原始日志。全仓与定向 pytest、registry、demo、冻结验证均在精确实现提交运行；lint 与源码公开扫描的索引树等于实现提交的 Git tree。同步与 help 在提交前运行，二者的依赖/入口随后没有变动。环境详情日志 SHA-256：`6fb8773ff291b0a4321e4be2c5796f1a3695e1f5ab63bdf2598be38eacfe2dc1`。

| 实际命令 | 退出码 | 结果 | 原始日志 SHA-256 |
|---|---|---|---|
| `uv sync --locked --python 3.14` | 0 | 环境同步（冻结依赖） | `9c778d73ab68fb80eaf6a4adbf5ea6b760119ec24acb029dbfcc5185a5fc034e` |
| `uv run --locked pytest -q` | 0 | 191 passed；全仓 CPU | `5d0830a9749a3df56744fb4a29858b0f6bf7684632e095e9ce10c4abb2be40b9` |
| `uv run --locked pytest -q tests/tools/ tests/evaluation/harness/` | 0 | 133 passed；P03 定向 | `9b135dfcfa9d4f702f34bfe71b3f6945296c8979631360cdf3c1366010a922a3` |
| `uv run --locked ruff check .` | 0 | 通过；实现提交同一索引树 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `uv run --locked python scripts/check_contract_freeze.py` | 0 | 通过；4 个冻结文件 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| `uv run --locked python scripts/check_public_content.py` | 0 | 通过；121 路径，实现提交同一索引树 | `5d9ff74e39c20e56944028aece9c284f7b3aed12854225b591bcd599af185365` |
| `uv run --locked python -m toolalign.tools --help` | 0 | 帮助入口正常 | `4218c41dbd8170b168755ec7fcc99b1c59c94d0b5e7d6ee45f0b6ff30c59d356` |
| `uv run --locked python -m toolalign.tools registry` | 0 | 6 个固定工具及完整 registry manifest | `4c7609506a86ea5d97ede24642f55c1645e1cd5c13235d28154f9986845967e5` |
| `uv run --locked python -m toolalign.tools demo --cases tests/fixtures/tools/development.json --output .toolalign-local/p03/demo-candidate` | 0 | 10/10 原创 scripted 开发任务 | `7491882e51f13f2b800834d17b155c5f7941187ba044fd00b5785487d4334396` |

最终全仓 191 项包含 P03 的 133 项与原有 58 项；没有用重复执行累加测试数。全仓日志为 191 passed / 21.82s，定向日志为 133 passed / 20.68s；这两个测试运行时长不作为模型性能或 SLO。

## 六类覆盖与语义证据

| 类别 | demo 场景 | 实际覆盖 |
|---|---|---|
| 版本文档 | dev-document | 正确版本、旧版本反例、缺参、等值单位与额外转换合法策略 |
| 构建/测试报告 | dev-report | 正确报告、错对象反例、相似工具混淆、虚假通过计数、缺参 |
| 日志过滤 | dev-logs | 精确日期与级别、错日期反例、缺参 |
| 结构化聚合 | dev-aggregate | 日期/字段/mean、schema 合法但错误 sum 策略、缺参 |
| 版本兼容 | dev-compatibility | 最低 runtime 规则、错误资源版本反例、缺参 |
| 单位/数值转换 | dev-conversion | KiB/MiB、错来源单位、数值边界/非有限/类型强转拒绝、跨维度执行错误、缺参 |

额外场景包括无需工具、缺版本应澄清、明确允许的拒绝、多步文档→报告依赖、暂时故障后恢复。模型即使提供正确的最终文字，只要工具选错对象/日期/版本或调用策略不被允许，oracle 仍失败；工具正常返回不能替代语义判定。未知/缺失/不支持的 oracle 真值计 unknown，保持总分母。

安全与预算负例实际覆盖：伪造/复制/跨 registry/修改后的 `ValidatedCall`、旧 hash/version、重复与冲突定义、重放、`ta_` 未绑定 schema、额外参数/schema 注入、路径遍历/宿主路径/URL/代码字符串、有界输出、同轮/跨轮 call ID 冲突、永久错误、后端错误、原始解析失败且后端声称修复、工具/模型真实阻塞后的 timeout/cancel、重试累计预算、墙钟读数倒跳时的单调截止保护、另一个进程不被误回收、真实业务文件不被写入。oracle metadata/expected_action/payload sentinel 未进入 ModelInput。

## Scripted demo 的实际计数

- 任务：10；success 10，failure/unknown/not_scored 均 0，排除 0。它们是公开原创开发样例，不是隐藏测试或泛化率证据。
- 90 条 trace，逐条通过冻结 trace 验证；所有持久 deadline 为 UTC。
- 累计模型决策 20、工具轮次 10；合成输入 token 220、合成输出 token 140。
- 工具尝试 10：completed 9、error 1；临时错误保留在调用记录，恢复后对应任务成功。
- 本次 demo 创建 20 个操作进程，20 个均记录 operation_started，20 个均确认 reaped。超时/取消的阻塞回收由定向测试另行验证。
- registry version：`toolalign.local-registry.v1`；tool version：`local-devops.v1`；oracle version：`toolalign.semantic-local.v1`。
- registry hash：`6cf0ff5e0b775068ddd9690e66414eee97725865d520e8df37072bc53d4085b8`。
- catalog 源文件 SHA-256：`8c89c7f2b4a4bc64952791b66954542cf328f814b07a9ba1c3f3e70b5e236792`。
- 原创 fixture SHA-256：`973a4a18c7a2372bd479a34a3df31300843737c293ab4f184170c85d94ce3b2d`。
- demo 汇总 SHA-256：`7491882e51f13f2b800834d17b155c5f7941187ba044fd00b5785487d4334396`；完整 case 文件 hash manifest 私存。

## 失败记录、限制与未运行项

最终检查退出码均为 0，没有留存的失败测试。开发阶段校正过一项计时断言：1.3 秒请求截止可能晚于一次 1 秒工具超时，第三次模型决策会合法开始；用 0.8 秒请求截止明确验证请求先到期，保留原有预算实现。

`256` 是每次响应 token 上限，`30s` 是统一 deadline 候选；未增加公共预算配置。raw 与后端解析诊断分开，修复器 DISABLED。超界 raw 只保留 hash/大小/截断标志及可用 usage；响应前终止的 token 计数标不完整，不冒充零消耗。

本 worktree 实测磁盘块占用 `.venv` 35,068 KiB、私有目录 648 KiB，远低于首轮 2 GiB；不改 OS 限制、不清理全局缓存。子进程只隔离受信实现的生命周期，不是任意代码的 OS 权限沙箱。具体构造条件见 [使用说明](README.md)。

NOT_RUN：Python 3.11；默认 build/sdist（遵守共享 PR4 修复等待）；wheel（本包非必要）；真实 MLX/Qwen backend 的加载、pickle/进程兼容性及 tokenizer 计数；权重下载、训练/GPU/付费 API；公网服务与模型/数据上传；正式隐藏最终测试、BFCL、P06 分组 bootstrap、TTFT/prefill/decode 性能。S0 尚未发已验证的新 main，当前未合入未审共享候选。
