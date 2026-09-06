# P03-fix-r3 收尾修复 checkpoint

日期：2026-09-06。状态：**E1 定点修复自测通过；等待 S0 提供原 R1 正式 review commit 与最终关闭项。** 本文不是整包交接、独立审查或验收。R1 原轮被审候选仍为 `79a15d990fc27a9a33d033983c94eb92cccfb268`。

| 绑定项 | 实际值 |
|---|---|
| 授权 | `243821a988a12a6ff9f20b5fbb5ba1ae374d63c9`；P03 收尾 IPC 及有具体反例的相邻清理逻辑 |
| 本轮父提交 | `79a15d990fc27a9a33d033983c94eb92cccfb268` |
| 已验证公共生产基线 | `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`；未合入后续 P01/P02 或协调文档 |
| 修复实现与测试提交 | `fde181d3319f36179298a4bec2a928a8354ee6b3` |
| 对应 tree | `4df73bc5a593610b65eb16ee3750f3c319f4184e` |
| 分支 | `work/p03-execution-harness` |
| 契约 | `toolalign.contracts.v1` / `toolalign.protocol.v1` / `coordination.v1`，冻结文件未改 |
| 实现改动 | `src/toolalign/evaluation/harness.py`、`src/toolalign/tools/isolation.py` |
| 新增回归 | `tests/evaluation/harness/test_finish_cleanup.py`，10 项 |

## 原实现反例与修复

先在未修改实现的 `79a15d9` 独立运行新探针，得到 **4 failed / 3 passed**。每个场景均由子进程在 `backend.generate()` 内写入进入标记；通过记录原进程对象和实际退出码确认生命周期，而非仅检查 future 或预调用标记。

| 场景 | 原实现实际结果 |
|---|---|
| 正常回答 / 无故障 | 返回 success，合法 finalized trace，子进程退出码 0、已回收 |
| 原始解析失败 / 无故障 | 返回 failure，合法 rejected trace，子进程已回收 |
| 后端抛错 / 无故障 | 返回 failure，合法 rejected trace，子进程已回收 |
| 正常回答或解析失败，stop 写入抛 OSError | stop 重试 2 次，最后由 finally 回收子进程，退出码 -15；调用方收到异常，没有 HarnessResult，trace 停在 parsing |
| 正常回答或解析失败，临时目录 cleanup 抛 OSError | 子进程已回收且 handle 已关闭；重入 cleanup 又读取 Process.pid，最终 ValueError 遮蔽结果；close 共 3 次，仍没有 HarnessResult/终态 trace |

原始探针 SHA256 为 `5b5d880907c1c88095eca4555041cac86f44acdc454e079810539c1db9ed149d`，原稿与 before 日志独立保留。该原稿先于实现修改，不是对 R1 未提交文件的复制或修改。

修复将“已经尝试收尾”与“实际回收成功”分开：stop 只尝试一次，无论信号写入是否成功都进入自有进程 close。捕获到收尾错误时，终态 `validation_failure` 固定为 `harness_cleanup_error`，正常 final 转为 rejected/failure；已有 timeout/cancel/budget 等终态类型保留。原失败原因保留在 `TaskScore.reason`，原解析错误仍在 `trace.parse_failure` 与决策的 `raw_parse_failure` 中。原始文本、final action、决策数、工具轮次、已知 token 及 token 完整性标记均保留，失败仍进入分母。

进程记录以 `cleanup_errors` 区分 stop 写入失败与 close 失败，不记录内部异常文本。`reaped` 和 `exitcode` 仍只由真实进程回收赋值。新增 `directory_cleaned` 仅在临时目录 cleanup 成功后为 true；目录失败可以表现为 `reaped=true`、退出码非空、`directory_cleaned=false`。`OwnedProcess.close()` 单独保存 process handle 已关闭状态，后续恢复文件系统访问后只重试未完成的目录清理。

最终测试按上述字段设计检查原失败原因位于 `score.reason`，并继续强制检查 `trace.parse_failure=invalid_raw_action`、raw 文本和预算；这一字段断言调整没有豁免原实现的异常出口。修复初版 7 项通过，随后补齐至 10 项：新增两个实际阻塞第二次 generate 后遇到 stop 失败的 timeout/cancel 场景，以及一个注入 close 无法回收的记录检查。

阻塞重试检查保留第一次响应的 13 input / 9 output 合成 token、2 次决策、1 次工具轮次，token 完整性为 false；明确独立的另一个进程保持存活。注入无法回收时，返回记录必须为 `reaped=false`、`exitcode=null`、`directory_cleaned=false`，测试记录此刻子进程仍存活，再由测试恢复真实 close 并回收。它不声称实际模拟了操作系统拒绝 SIGKILL。

## CPU 自测与来源绑定

复用既有 CPU 环境，不选 compatibility/dpo/replay extra。完整回归的 319 项为原 309 项加 10 项新收尾测试：P03 143 项、基础测试 58 项、P00 独立检查 46 项与 P00-r2 检查 72 项。未把历史单 compatibility extra 的共享快照再次计入当前结果。

| 实际命令 | 结果 | 退出码 | 日志 SHA256 |
|---|---|---:|---|
| `uv run --locked pytest -q -s tests/evaluation/harness/test_finish_cleanup.py`，原实现/原稿 | 4 failed / 3 passed | 1 | `b87624212b393863a8da0c8974e1e2065dc0029e0605db73894138230af2ca8d` |
| 同路径，修复初版 7 项 | 7 passed | 0 | `fd8e7282a9fbdd5e6ac53b5e096f4216cd746e3393437bad68b59059f5f4287d` |
| `uv run --locked pytest -q tests/evaluation/harness/test_finish_cleanup.py`，最终 10 项 | 10 passed | 0 | `ff72a0bcdcc48a829237a6e4f4022662c79709a2ac16462b6e8405f227ff2486` |
| `uv run --locked pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py` | 319 passed，无 skip | 0 | `6c7401b97a2279c3a83920a07f3076dfee1c3105066672c45ec6a792cae21aef` |
| `uv run --locked ruff check .` | PASS | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `uv run --locked python scripts/check_contract_freeze.py` | 4 文件冻结检查通过 | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| `uv run --locked python scripts/check_public_content.py`，实现提交 | 147 paths，通过 | 0 | `24b66178de1f8e827a6cdea5b08af6f874dd6c096a440904a019ae5aeab67b60` |

复现及开发中间检查的 Git HEAD 仍显示父提交，不能误写为父提交原字节已通过修复后测试。原稿独立保存；最终 10 项运行时三个变动文件的 SHA256 已另存，其字节与随后 `fde181d` 一致。完整 319 项、lint/冻结/公开扫描及下述构建/安装均直接运行于已提交的 `fde181d`。

| 当前源码/测试文件 | SHA256 |
|---|---|
| `src/toolalign/evaluation/harness.py` | `b4aff77d4adffea786d742d5c5aeeee72f99feaf3783ee0f01ad504aa84bb987` |
| `src/toolalign/tools/isolation.py` | `84a96791205488bad6bd3fe43a42f33f7abcbfb5fc8bb0b64f27aa13e5667f6f` |
| `tests/evaluation/harness/test_finish_cleanup.py` | `b81acd8bea492da2f4483c21f7e6e0c48c30d4168ff3a9dde62682c9e21d005b` |

## 新归档与隔离安装

新产物保存在本轮私有目录，未覆盖上一轮 `dist/` 或旧隔离环境。实际命令：

```bash
uv build --out-dir .toolalign-local/p03-fix-r3/dist
uv build --wheel --out-dir .toolalign-local/p03-fix-r3/rebuilt .toolalign-local/p03-fix-r3/dist/toolalign-0.0.1.tar.gz
python3 .toolalign-local/p03-fix-r3/inspect_archives.py
python3 .toolalign-local/p03-fix-r3/verify_install.py
```

四条命令退出码均为 0。对应日志 SHA256 依次为 `5f6e0fcb3668d106cf17fe7603c2a0b74db772e11aea316d6a67cdcdb697abb8`、`68e2b6e6f85aa042b1d436610b3a4549947b61129f24976474dca3d104c6658f`、`36cb4906aa78af802aa8f10bd280fb5832b6952c18fbb6c92fa65b4df7e42516`、`13d2286709426fd9780eba6a65035d4688f2b6849bd712f0aa4b86c68b0d6209`。

| 产物 | 字节数 | SHA256 | 逐成员结果 |
|---|---:|---|---|
| sdist | 115198 | `72b95cf7211f4906b1a646e52fcf0c2f7caf9fecf773f3ef14e060474f663b83` | 51 文件：50 个与当前追踪字节相同，1 个 PKG-INFO |
| 默认 `uv build` 生成的 wheel | 37378 | `0cee146112f6279d6621e00fc911a97411128e3c69b4fdb62683fd4690b21a7e` | 29 文件：24 个源码/资源字节相同，5 个已知 metadata |
| 显式从 sdist 重建 wheel | 37378 | 同上 | 同上 |

默认 `uv build` 输出明确是从 sdist 构建 wheel，本轮没有将其称为直接从工作树构建。三份归档均无未追踪载荷、缺失成员、符号链接或路径遍历。冻结 schema digest 为 `ce17b0a5bc4e8363e1d67bf125212444bab1103ddfc0c4e390bef82afce881cb`。归档检查沿用上一轮已纠正的 `.gitignore` 显式追踪字节核对，未更改公共打包规则；未重复扩大已通过且字节未变的共享私有文件 canary 调查，原证据见 [P03-base-r2](P03_BASE_R2_VERIFICATION.md)。

隔离安装包含 16 条实际子命令，均退出 0：锁定 runtime 依赖导出、全新 CPU venv、require-hashes 依赖安装、no-deps 重建 wheel 安装、依赖检查、冻结 digest、5 类 wire fixture、CLI help、registry、demo、4 项阻塞生命周期探针、4 项收尾失败探针。运行目录是本轮私有子目录，位于 worktree 内但不是项目根；清除 PYTHONPATH/PYTHONHOME 并使用 `python -I`，模块来源断言均位于新 venv。

安装后的 scripted demo 为 10/10、excluded=0，不是模型指标。原始四项工具/模型 timeout/cancel 检查均实际进入操作、停止并回收自有进程，4 started / 4 reaped。新增四项 installed 检查重新注入 stop/目录失败与正常 final/parse 两种返回，均确认实际进入 generate、仅一次收尾、失败计入分母、13/9 合成 token 及 parse 保留；目录错误恢复后只重试目录 cleanup。安装后的两个修改模块 SHA256 与 `fde181d` 逐字节相同。模块导入检查未出现 ML 依赖。

## 保留范围、限制与下一门槛

本轮对原 419 个公开交付/私有证据/归档文件做前后 hash 核对，仅两个授权源码文件变化；17 个其余旧公开文件和全部 400 个旧私有/归档文件未变。原 `85e0905`、`79a15d9`、[P03-r1](../../coordination/handoffs/P03-r1.md)、[P03-base-r2](../../coordination/handoffs/P03-base-r2.md) 及旧失败原始结果保留。新私有目录在安装验证后的磁盘快照为 4076 KiB，复用 CPU `.venv` 为 35068 KiB，未接近新增 2 GiB 上限。

原始命令、argv、退出码、时间、hash、探针和安装结果仅存本机本轮私有目录，具体绝对路径已单独交 S0。归档检查器 SHA256 `a21b2b64f12264526906a515515856943571dc08aa1c28da0c05343ace00aa8a`；安装驱动 `9e4c115f16525f86ab56660d3b99ba203ae37bd3bc3e2718d8372c6da15f20c5`；新 installed 收尾探针 `450c6054acde6a9861676a4917b30bb4d0c6f4502ce402b51997d411e8d17d75`。不提交原始日志或本机身份信息。

仍为受信本地实现的进程生命周期隔离，不是任意 Python 的 OS 沙箱。已加载 MLX/Qwen 对象跨 spawn 的兼容性、模型推理/训练/GPU、正式隐藏集/BFCL/P04/P06、吞吐及模型服务部署均为 **NOT_RUN**。本轮没有模型下载、费用、模型或数据上传、main 合并或状态看板修改。

正式原 R1 review commit 到达后，须由 S0 给出原 SHA 与最终关闭项，再以非强制方式接入该原 SHA，补齐授权项并提交 `P03-fix-r3` 整包交接。新精确候选仍须独立 R1 复核与 S0 合并/main 验证，本文所列自测不替代这些门槛。
