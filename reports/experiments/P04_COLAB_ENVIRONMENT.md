# P04 Colab 环境与运行控制交付

日期：2026-10-26。E1 提交 CPU 准备候选，状态 **READY_FOR_REVIEW**。实现提交 `b6970f656c727b57e5e64422f88393b312e87e76`；code_base `61c2176d556fd0e4cfc2af00b16242dddcfadfd3`；S1 派发授权 `04415938c749ea2e8dc1ef5e8ab7e30b777aeb47`。

已形成 Linux/Python 3.12 CUDA 锁和可检查的五步控制流程：安装、启动、查询、完整回收、停止。**没有分配实例、建立 SSH 连接、下载真实模型或执行训练。** 版本解析和本地 fixture 通过，真实 Linux 安装与 CUDA 运行仍为 NOT_RUN。

## 交付与接口

- [CUDA 锁](../../requirements/cuda-linux-py312.lock.txt)：48 个精确包及 hash，Torch `2.8.0+cu128`、Transformers `4.57.6`、PEFT `0.18.1`、Accelerate `1.12.0`。
- [Mac CPU 锁](../../requirements/cuda-macos-cpu-py312.lock.txt)：37 个精确包及 hash，Torch `2.8.0`；与 S1 管理的已安装 CPU 环境逐包比对，无版本差异。本轮复用该环境，不另建训练环境。
- [本地控制器](../../scripts/colab/control.py)、[实例控制器](../../scripts/colab/remote.py)及共用 helper：固定入口、具名 endpoint 所有权、同 run 不重复提交、失败退出、完整归档/读回/确认以及停止检查。
- [操作文档](../../docs/18_CUDA_RUNTIME.md)：版本选择的官方来源、完整安装和五个控制命令、私有配置占位符、目录及恢复语义。

运行入口已按 S1/T1 对齐为 `python -m toolalign.training.cuda_sft train --run-config /ABS/run.json`；恢复仍使用此入口，在 run JSON 中提供完整 checkpoint 路径和状态 SHA。控制器不实现训练算法或重写 T1 的数据/模型验证。

固定 `repository = lock_root = /content/toolalign`，环境和登记文件在该 checkout 的 `.toolalign-local/`，避免污染精确源码检查。`persistent_dir` 指向 `/content/toolalign-staging/RUN_ID`，只是实例内副本。Mac 下载、逐文件读回、远端确认完成后才允许停止；同名会话换了 endpoint 时拒绝连接/停止。

Linux lock SHA-256：`14e8724b9d78e7bcabc270aa2c0cfe05ea5a5d855fffda08dad7aa0a93c20fb4`。Mac CPU lock SHA-256：`7e0e79a1f02da2cccb0cec0e33184ccec40ff33e99264efb7741d33c38fbf28b`。

## 实际验证

以下命令编号对应本轮私有 `commands/NNN-*/result.json`，其中保存完整 argv、UTC、退出码和输出。公开表省略私有绝对路径，`TMP` 表示每次新建的独占临时目录；精确依赖解析命令也写在锁文件头部。

| 编号 | 实际动作/命令 | 退出码与结论 |
|---|---|---|
| 002 | 现有 CLI 的 help/version | 0；`google-colab-cli 0.7.4`，未升级/重认证 |
| 004 | 获取固定版本 PyPI JSON，显式使用系统 CA | 0；9 份元数据，来源链接见操作文档 |
| 005 | 现有包装 `sessions` | 0；当时没有活动会话，未连接或创建 |
| 006 | `uv pip compile requirements/cuda-linux.in`，Python 3.12 / Linux x86_64 / cu128 / hashes | 0；48 个包解析成功 |
| 007 | `uv pip compile requirements/cuda-macos-cpu.in`，Python 3.12 / Mac arm64 / hashes | 0；37 个包解析成功 |
| 010 | Python 3.14 `pytest -q tests/colab --basetemp TMP` | 0；初轮 18 passed |
| 012 | 同范围，加入回收后禁止重启和快照变化检查 | 0；19 passed |
| 013 | S1 共享 Python 3.12 环境导入 Qwen3/PEFT/原生 tokenizer 接口，构造 LoRA 配置 | 0；接口与版本通过，无模型实例/权重 |
| 014 | `ruff check scripts/colab tests/colab` | 0；All checks passed |
| 015 | Python 3.14.7 `pytest -q tests/colab --basetemp TMP` | 0；最终实现 19 passed，3.98s |
| 016 | `python -m py_compile` 三个脚本及控制测试 | 0 |
| 017 | `python scripts/check_public_content.py` | 0；当时 699 个公开路径扫描通过 |
| 020 | S1 共享 Python 3.12.14 `pytest -q tests/colab --basetemp TMP` | 0；同一实现 19 passed |

实现提交中的 9 份相关锁/脚本/测试文件与 014–017 的运行前文件 hash 逐项相符。020 直接绑定实现提交。这里只运行了 `tests/colab`；没有重跑整个历史测试集，也没有建立 wheel/模型服务发布。

控制测试覆盖：缺失实例即使 CLI 返回 0 仍拒绝 SSH；其他项目及被替换 endpoint 拒绝；setup 仅安装且拒绝 Mac CUDA 安装；部分安装失败留存；tmux 已有/失败启动不重复提交；真实原创子进程退出 7 或超时 124 后保存日志并回收；SSH 超时留存不确定状态；完整 checkpoint 原创字节下载、读取、确认与具名停止；缺失/损坏副本、遍历成员、缺失成员、symlink、活动 GPU 锁和已变化快照拒绝停止/恢复。

CLI、SSH、tmux 和安装计划使用本地替身。子进程执行/终止、Git 根共享文件锁、归档下载复制、SHA-256 和文件读回在本机真实执行。fixture 的 checkpoint 字节是原创测试内容，不是模型 checkpoint，也不能证明新实例续训。

## 保留的失败与修订

| 编号 | 实际失败 | 处理与证据 |
|---|---|---|
| 003 | Python 默认 CA 路径导致 PyPI HTTPS 校验失败 | 004 显式使用系统 CA 成功；原失败保留，未修改全局信任/认证 |
| 008 | 尝试将 CUDA wheel 索引作为普通 uv 优先索引时，固定时间截点下 NumPy 候选不能解析 | 保留 006 已成功的 `--torch-backend cu128` 锁；安装明确提供 CUDA extra index，原失败未覆盖 |
| 009 | ruff 检出测试文件未使用的 `json` import | 删除未使用 import，014 通过 |
| 011 | 已回收 setup 的 run 仍可启动，复现测试未得到预期拒绝 | launch 禁止已回收 run；停止前重新计算各 run 的清单 hash；012、015、020 回归通过 |

旧任务及旧失败证据保留原位。本轮只在授权的新目录记录命令，没有复制旧证据树或修改共享协调状态。

## 下一项实测

R1 对本候选独立复核，S1 与 T1 训练入口集成后签发真实有界配置。需要在 Colab 检查 Linux 安装/`pip check`、实际 GPU/显存、冻结最长 cohort 的 forward/backward/optimizer/validation/save，并从完整 checkpoint 在新进程及新实例恢复一步。当前这几项均为 **NOT_RUN**。

安装和运行受分配预算约束，最终记录包含安装、空闲、失败、传输总时长；回收/停止可在预算用尽后继续，控制器不提供断网后的自动停机服务。TRL 仅登记 `0.26.2` 元数据兼容候选，DPO 环境与 reference 仍需 G4 锁定验证。
