# P03-base-r2｜共享基线同步与 CPU 包验证

日期：2026-09-06；owner E1；候选仍**等待独立 R1，未验收 P03**。本轮不修改 P03 实现，只同步已验证共享基线并补充实际 CPU/归档/隔离安装证据。

## 提交与保留证据

- 原完整 P03 候选：`85e0905fc82da4504d73bf7eb489c1f1a0d227a7`；原实现：`8afb114bd14e69d3a2138212ab423147809fed63`。
- S0 生产 code_base：`37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`；同步授权与 merge 目标：`f2a271be616cdb53c01e8d671029f31ae140c037`。
- 非强制 merge：`86c5e8abaf0a6518fda0d33dba1b68eb6815737a`；父提交恰为原候选与指定授权目标；tree：`969724e49233c44bd282694f973095a4cec0d3b0`；分支仍为 `work/p03-execution-harness`。
- 逐文件 SHA-256 核对：原 P03 17 个公开交付文件与 63 个本任务私有证据文件全部不变。原 `P03-r1.md` SHA-256：`a310b8b67ece8d610ffaec2b0aeba85ded6f3cb5309e388373db7ef731428486`。P01/P02 源码相对同步目标的差异为 0，未混入其实现或测试计数。
- 本轮在上述 merge 后仅新增本文与 `coordination/handoffs/P03-base-r2.md`。原 r1 报告的历史 NOT_RUN、禁止旧基线 sdist、旧检查结果均不改写。真实身份、授权副本与路径私存。

读取并保留了授权提交的 AGENTS/GOAL/PROTOCOL/PROJECT_STATUS、P03 同步段与 [S0 main 验证报告](../S0_SHARED_02_MAIN_VERIFICATION.md)。契约仍为 contracts.v1 / protocol.v1，未手改公共代码、依赖、配置、CI、看板或 ADR。

## 当前实际命令与日志

以下在精确 merge 提交运行。Python 3.14.7、macOS、Apple Silicon、纯 CPU；新锁文件 93 条解析记录不等于安装全部可选依赖。本轮未选择 compatibility/dpo/p01-replay extra。原始输出、UTC、argv、head/tree 与退出码私存 `.toolalign-local/p03-base-r2/checks/`。

| 实际命令 | 退出码 | 实际结果 | 日志 SHA-256 |
|---|---:|---|---|
| `uv sync --locked --python 3.14` | 0 | 默认 CPU 环境同步 | `1bf0a7707bd4636ea27da8dde5f7dc742a55e834aa1ec6b97b33705b76f438d0` |
| `uv run --locked pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py` | 0 | 309 passed = 133 P03 + 58 默认 + 46 P00 + 72 P00-r2 | `cfa7ec544f2552516dcaf8a812b049c693e8461e141d84175c0b1b70457472c1` |
| `uv run --locked ruff check .` | 0 | 通过 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `uv run --locked python scripts/check_contract_freeze.py` | 0 | 4 个冻结文件通过 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| `uv run --locked python scripts/check_public_content.py` | 0 | 144 个路径通过（新增本轮文档前） | `ad4e3c8d6e3deb619f9ac0f34b5e45707f44b4589c4147424d01c7d2362b9095` |
| `uv run --locked python scripts/check_source_distribution.py` | 0 | 241 私有 / 18 公开对照，三条构建路线通过 | `e08abd64a116a575ce2a993a45d0e84c05f0f359e3d60dfa192247308410fd72` |
| `uv run --locked --with hatchling==1.27.0 python reports/review/S0-SHARED-02/probe_additional_boundaries_r3.py` | 0 | 原 R1-r3：45 私有 / 21 公开对照，通过 | `7e0cf34222b4a5b45d2e9d5129cd149fa89289b70598e582b876719101a04537` |
| `uv build` | 0 | 默认 sdist + wheel 成功 | `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75` |
| `uv build --wheel --out-dir .toolalign-local/p03-base-r2/rebuilt dist/toolalign-0.0.1.tar.gz` | 0 | 从实际 sdist 重建 wheel 成功 | `f9190e2a692506b39af139d8c5152550e3e4f160f09e173a6bb27387c9ec2d11` |
| `uv run --locked python .toolalign-local/p03-base-r2/inspect_archives.py` | 0 | 全部追踪字节匹配，未跟踪载荷 0 | `7109107e593c049a0d6d065a180dbff465aef461c85df79204f54543d2a1162c` |
| `uv run --locked python .toolalign-local/p03-base-r2/verify_install.py` | 0 | 15 条子命令退出 0；demo 10/10；4 项阻塞回收通过 | `15948e3c943ffa303a4a77e090b5c69948d047ce45ee44e54797af1e663e5346` |

309 是本轮实际 pytest 收集/通过数，不按重复运行累加。未运行、未改写旧 shared01 的“只有一个 extra”57 项历史结构快照；未计入 P01/P02 测试。原共享 canary 按原文件重跑，没有新增私有路径扫描或读取其他 worker 的私有环境；241/18 与 45/21 两组有重叠，不相加成覆盖率。

## 实际归档

正常 `uv build` 在同步修复后才执行，产出源码包及其 wheel；随后以该实际源码包显式重建第二份 wheel。

| 路线 | bytes | 归档文件数 | 与 Git 追踪字节匹配 | 生成 metadata 文件 | SHA-256 |
|---|---:|---:|---:|---:|---|
| sdist | 112760 | 50 | 49 | 1 | `a095ab30fbd3ffc35689253164be79b70dc0061d80078f80bb47c88d9a54178f` |
| default-wheel | 37042 | 29 | 24 | 5 | `e9d559cd0cfd17dc66b24f88455b1a138599a59faa476a34d3fb9d76c19a891c` |
| rebuilt-wheel | 37042 | 29 | 24 | 5 | `e9d559cd0cfd17dc66b24f88455b1a138599a59faa476a34d3fb9d76c19a891c` |

sdist 的 49 个实际追踪文件逐项与 merge 提交的 Git blob 比较，只额外允许生成的 `PKG-INFO`。wheel 的 24 个源码/资源文件逐项匹配，只额外允许项目 dist-info 的五个固定 metadata 文件。三份实际产物的未跟踪载荷、缺失预期文件、字节不一致均为 0；无符号链接或路径逃逸成员。两份 wheel 实际摘要相同。

第一次核对脚本漏列构建器保留的、已被 Git 追踪的 `.gitignore`，导致预期集合断言退出 1；没有发现私有文件泄漏。初版脚本和失败日志保留，日志 SHA-256 `f5dcc5fe9b300c43f1c6c26a62e6e6cd38eddc1c6f9f6b7d067e8b7941c94b71`。修正仅把该已知追踪文件加入精确字节核对，仍拒绝所有未跟踪载荷；修正版实际通过，见表中 `artifact-inspection-corrected`。

## 隔离安装与 P03 执行

使用锁文件导出 `--no-dev --no-emit-project` 的默认 CPU 依赖，`uv pip install --require-hashes` 安装闭包，再以 `--no-deps` 安装从源码包重建的 wheel。环境位于本任务私有制品目录，cwd 为其中的隔离子目录；清除 PYTHONPATH/PYTHONHOME，实际命令使用 `python -I`。验证了导入模块路径位于独立 venv，未使用源码目录作为包导入来源。

15 条实际子命令均退出 0：依赖导出、venv、哈希依赖安装、wheel 安装、pip check、installed contract digest、example/tool/preference/run/trace 五类 CLI fixture、tools help、registry、scripted demo、自有阻塞进程探针。每条完整 argv 和日志 hash 保存在 `isolated-verification.json`，详细输出位于私有 `isolated/`。

- 安装后的冻结 schema SHA-256：`ce17b0a5bc4e8363e1d67bf125212444bab1103ddfc0c4e390bef82afce881cb`。
- 安装后的 registry hash：`6cf0ff5e0b775068ddd9690e66414eee97725865d520e8df37072bc53d4085b8`，与原 P03 相同；6 类工具完整可用。
- 安装后的 scripted demo：10/10，90 条合法 trace，20 个真实启动的自有进程均回收。仍是合成 token/脚本接口验证，不是模型实验。
- 安装后的专门阻塞探针：tool timeout、tool cancel、model timeout、model cancel 四项均进入实际操作后终止；4 个自有进程均记录 started/stopped/reaped、实际 exitcode，active_children 无这些 PID，自己的临时操作目录被移除。
- `toolalign`、catalog、harness、oracles 四个模块来源均在独立 venv；mlx/torch/mlx_lm 不可导入，运行中无模型包导入。

本轮探针代码未修改公共模块，只私存可复核的检查程序。SHA-256：归档核对 `5b5b62e9e5b2f6b36f6c02b4a3db1c78c68564c87b4e216ff028504777b331d0`；隔离安装驱动 `b68a2a70bda4a97c5c044705c04ff91fae88ba2c16fedc87f8dbb2584c32617e`；阻塞进程探针 `a868913030db0d2ac997b2bc8a0a032aca05374acbbec5e3a34e3a4f6beec44f`。

## 构造限制、资源与交接

保留 P03-r1 的构造边界：父进程先持轻量、可导入且可 pickle 的 backend 状态；实际 generate 在一个持续的自有模型子进程执行。带锁与签发记录的 registry 留在父进程，不 pickle；工具子进程按固定名称/hash/调用快照重新构造 registry。oracle 与标签不进入 ModelInput。所有回收仅基于本任务亲自创建的 Process，不扫描或回收未知 PID。

真实已加载 MLX/Qwen 对象、张量/句柄的 spawn 兼容性仍 NOT_RUN。冻结 ModelBackend 并未承诺任意已加载对象可 pickle；本轮 wheel 安装与 scripted 成功也不能作此推断。预算仍为最多 3 决策/2 工具轮次/每次 256 token/候选统一 30 秒，重试与修复不重置；无新增公共预算配置。

本轮磁盘块快照：`.venv` 35,068 KiB；本 worktree 所有 `.toolalign-local` 4,396 KiB；`dist` 156 KiB。制品保留本地 ignored 路径，未上传发行包、数据或模型，未更改 OS 限制。

NOT_RUN：Python 3.11 本机重复验证；MLX/Qwen 加载、GPU/训练/权重下载、付费 API；真实 tokenizer/吞吐/性能；正式隐藏最终测试、BFCL、P04/P06 新功能；旧 shared01 57 项历史快照。当前同步基线上的 sdist/wheel/重建/隔离安装已经实际验证，旧基线禁令的历史记录保持原文。
