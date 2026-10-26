# P06 G5 评测 CPU 首包交接

T1，2026-10-26。交付分支 `codex/t1-p06-g5-evaluation-r1`，基于授权 `b39d20d2d4f7ea87ff1f60bf7f4c9e10976d6d00`；已落实补充协议 `34f841d72cf3f570486779590dfe542ee09a53d4`。精确交付提交由本交接所在的 Git commit 及私有 evidence-index 绑定。

交付 M0/M1 CUDA 后端、单项真实 prefix cache、L1/action-only/replay/capacity 固定入口、恢复关闭开关、started/terminal接续与完整分母、Colab固定白名单。详细输入/run/output接口见[报告](../../reports/P06_G5_EVALUATION_CPU_R1.md)。T1自身提交不改契约/模板/锁/语料/工具目录或共享协调状态；按S1通知另原样接入E1候选 `6027096baf382bb0e50bf3f7463dd11fca0e19d1`（本地cherry为`5e6459e`），该工具依赖已获R1 `c6c81db24feda5986436facd66cc0757bb44e269` PASS并由S1接纳。

CPU结果：231项通过、1项既有DPO检查因缺pip跳过，退出码0。原创随机Qwen和真实PEFT LoRA中，热cache首轮forward由12 tokens降到1，命中11；输出token一致、逐步logits满足预设atol2e-6/rtol2e-5。完整失败分母、空/坏Action独立门控、恢复开关、超时回收、started不重跑与replay请求保存通过。接入E1后另做1项真实新catalog组合检查：两条on成功、off在首次transient结束，8个owned进程回收，改写spec被拒绝；退出码0，未重复未受影响矩阵。

私有证据入口：`.toolalign-local/p06-g5-evaluation-r1/evidence-index.json`，保存完整实际命令、退出码、日志、环境和受检文件hash。缓存真实数值与MOCK_ONLY CUDA加载边界在报告中分别列出。

S1/R1后续事项：

1. E1工具依赖已独立接纳；本评测执行器仍需R1单独审核。实现提交 `d674bdda3166836e8f41d60b763f23374aaa1e8d` 以E1 cherry为直接父提交，随后只追加依赖接纳说明。S1已有依赖时接入T1实现及说明更新即可。
2. D1/Q1冻结L1任务、恢复子集、replay开发输入；E1 adapter输出本报告规定的无oracle action-only输入。严格BFCL成功须同时满足按时完成、raw Action合法及官方判对，官方原始分另报。
3. R1独立CPU审核通过、S1冻结源码/input/plan/run之后，才能由S1发出Colab容量及正式评测授权。冷加载、父预检和全部失败/未启动项继续计账。

真实CUDA、官方BFCL、正式模型效果均 **NOT_RUN**；M2仍NOT_RUN。本包没有Colab运行或GPU授权扩展。
