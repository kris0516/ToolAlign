# P04 Colab 控制修订 r2

2026-10-26，E1，**READY_FOR_REVIEW**。本轮仅修订 `P04-COLAB-PROCESS-001` 与 `P04-COLAB-RECOVERY-001`。最终 CPU 定点检查 **26 passed**，待 R1 独立复审。

修订基点 `8faa75e7010290a11f13a8006fba5d4b16ac44f9`；授权 `85b49e38f5410e87bf325c173891d8a778138cb5`；实现提交 **`a662567b9adf3c47d748b19e1c4bb8ca8689e4b9`**。原 [R1 正式 FAIL](https://github.com/kris0516/ToolAlign/blob/2f449452636712f2622d40a3040a45034e56228f/reports/reviews/P04_COLAB_ENVIRONMENT_R1.md)及原候选保留；本轮自测不替代独立 verdict 或改写正式失败计数。

## 两项修订

`P04-COLAB-PROCESS-001`：原 worker 在 SIGTERM 后只等待父进程，因此父进程退出会使仍活跃的同组后代被遗漏。现在按该次 `start_new_session=True` 产生的 PGID 清理整个自有组；父进程退出后仍继续确认成员，必要时升级 SIGKILL，最后 `wait()` 回收直接子进程。两个确认阶段各限 10 秒。正常失败仍返回原退出码；超时保留 124，并记录 `timeout_cleanup_completed`。未确认清理时保留错误，拒绝导出该 run。

`P04-COLAB-RECOVERY-001`：远端 `stop-ready` 现在返回该 endpoint 全部登记 run 的当前已回收快照，并禁止新增 setup/launch。Mac 按此清单逐个核对回执、清单、归档和解包文件；清单必须与远端当前快照 hash 相符。较早 run 的文件损坏、tar 缺失、被改写的本地清单或遗漏位置都阻止 CLI stop。再次回收失败 run 后可以正常停止。完整清单保存为 `stop-inventory.json`，停止响应不确定且实例已不存在时仍按它核对全部副本。

S1 的本地控制接口新增可选 `recovery_directories`：`{"EARLIER_RUN_ID": "/ABS/PRIVATE/.toolalign-local/colab/EARLIER_RUN_ID"}`。路径指向含 `recovered.json` 的 run 目录。当前 run 使用当前目录，其余 run 默认在同一 `local_root` 下；不同根目录必须显式映射，不能被静默忽略。字段不改变训练 run JSON/身份，五个外部操作不变；细节见 [运行文档](../../docs/18_CUDA_RUNTIME.md)。本地/远端控制脚本需作为同一候选部署。

## 实际复现与验证

使用 S1 的唯一 Python 3.12.14 CPU 环境，`PYTHONPATH` 指向 E1 自己的 `src`，OMP/MKL 各 2，HF/Transformers offline。每次 pytest 使用新独占临时目录；原始回执保留完整 argv、UTC、退出码、输出和运行前源码 hash/diff，单命令上限 300 秒。

| 私有命令编号 | 实际命令摘要 | 退出码与结果 |
|---|---|---|
| 002 | 在未改源码的 8faa 上执行逐字复制的 R1 `test_independent_control_v2.py` | 1；两项原断言均失败：后代继续写入、较早副本损坏仍停止，3.98s |
| 003 | 原 R1 同组后代复现，加入组清理后 | 0；1 passed，13.62s；终态后心跳不再变化 |
| 004 | 原 R1 多 run 复现，加入完整远端清单后 | 0；1 passed，0.99s；两个不同根目录中遗漏较早位置时拒绝停止 |
| 005 | `python -B -m pytest -q tests/colab --basetemp NEW_TMP` | 1；24 passed / 2 failed，暴露组消失后直接子进程尚未回收的竞态，以及旧手工回执 fixture 缺少 archive 字段 |
| 006、008 | `ruff check scripts/colab tests/colab` | 1；新测试的 fixture 导入被判为未使用导入重定义；006 同时有 import 排序项 |
| 007 | 对新测试执行 ruff import 排序 | 0；只调整 import 顺序 |
| 009 | 正常失败/超时直接子进程回收及当前副本损坏定点回归 | 0；3 passed，1.85s |
| 010 | `ruff check scripts/colab tests/colab` | 0；All checks passed |
| 011 | `python -B -m pytest -q tests/colab --basetemp NEW_TMP` | 0；**26 passed，22.64s** |

005 的直接子进程问题通过在组消失后仍执行有界 `wait()` 修正。原损坏副本测试只补入真实回收操作一直会产生的 `archive` 字段，其拒绝停止的断言保留。新测试显式复用原 fixture，消除了 lint 重定义。全部本轮失败输出和两项原复现输出分目录保留。

最终 26 项包含原 19 项及 7 项新增检查：父进程先退出、同组后代忽略 SIGTERM；较早 run 的 checkpoint 损坏、tar 缺失、两者同时损坏及伪造清单四种情况，每种都验证拒绝停止后重新回收可正常停止；不同 `local_root` 缺失/错误映射被拒绝、正确映射可停止；超时清理未确认时不可导出。正常失败退出码、超时码、回收后重复查询和其他原检查保持通过。

010 的 4 份代码/测试与 011 的 5 份代码/测试/文档均逐项匹配实现提交。原 R1 的四份私有输入、r1 分支及最终回执未改变；依赖锁、训练源码、共享配置与状态无修改。公开扫描结果及最终候选 SHA 随本轮交接回执给出。

## 边界

CLI/SSH/tmux 使用 CPU 替身；同组子进程、心跳、信号清理、归档与文件损坏/重新回收实际执行。已核验本轮证据及独占临时目录约 3.7 MiB，低于 200 MiB 预算。E1 本轮 GPU、SSH、新环境/依赖安装和真实模型/训练均为 0。

T1 另建 session 的外部 SIGTERM 清理由 T1 处理，本修订没有覆盖或验收它。组合运行、真实 Linux 安装、CUDA 容量和跨实例 checkpoint 恢复仍为 **NOT_RUN**；S1 在 R1 复审通过并集成后签发有界 Colab 验证。
