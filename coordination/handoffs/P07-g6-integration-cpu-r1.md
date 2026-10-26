# P07 G6 服务与客户端 CPU 集成 R1 交接

2026-10-27，实际审核者 **R1 AI**。**PASS，新增实质问题 0。** 受检实现 `fa908839859b758ab2444845f9a2ad2c1eae6c57`，审核起点 `d259d85feb96ee8aaa5e4918e00c4f20973bf47d`。详见[独立报告](../../reports/reviews/P07_G6_INTEGRATION_CPU_R1.md)。

建议 S1 接纳 CPU 集成证据，主干核对后继续冻结有界真实服务 smoke。生产客户端与服务的实际 CPU loopback 链路完成工具调用、观察回传及 final；另一条包含非法参数的真实 Action 在客户端整批拒绝，零工具执行。排队/重载原截止、丢失 POST 回执、真实取消、SIGINT/SIGTERM 和正常父进程退出均取得证据。CUDA、SSH/Colab 链路和真实模型服务仍 NOT_RUN。

| 交付核对 | 结果 |
|---|---|
| 作者交付 | T1 `185d857e94c4187b8167515bf9cdadba248960b0`、E1 `59b9c482e0faf93b1fbd5836db21933a6d7197a1`；4,941 份私有文件和 44 份公共文件 hash/大小与候选绑定通过。 |
| 复用证据 | 179 项不同检查的通过记录；三项既有 pip parser 跳过保留。T1 的 35 个服务 child、一个 tiny CPU cache child及 E1 示例原回收证据保持。 |
| 新增执行 | 七项独立场景通过；全新 Python 3.14 CPU 环境的五类 CLI 示例符合预期，三成功、两预期失败；help、有效/错误配置均实跑。 |
| 生命周期 | 新增 28 个 owned child 全部回收，三个完整父进程 exit 0；包括保留的审查脚本失败运行。 |
| 公开包 | 实际 sdist 和其重建 wheel 均包含 18 个新模块，排除私有数据/权重；示例依文档从 Git checkout 取得。 |
| S1 辅助脚本 | 八个脚本只读检查完成；tunnel/stop 身份与预算、冻结接口、smoke 至多 11 次尝试无新增阻断项，全部未执行。 |

首轮独立检查五通过、两处审查脚本错误；修正观察字段和 CLI 退出码假设后，仅两项定点复验通过，生产源码未改。原作者失败、R1 原脚本与失败制品保留；不是正式候选修订失败。

私有入口 `.toolalign-local/review-p07-g6-integration-cpu-r1/evidence-index.json`；主要文件为 `intake-verification.json`、`reuse-verification.json`、`test_independent.py`、`commands/`、`independent-process-audit.json`、`package-verification.json` 和 `static-review.json`。精确审核提交、索引 SHA-256 与文件数随交付回报。未修改 BOARD/PROJECT_STATUS/DECISIONS、未创建或关闭 goal、未连接或分配 GPU。
