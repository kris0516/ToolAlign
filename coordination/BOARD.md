# ToolAlign 当前看板

更新：2026-10-26。证据见 [PROJECT_STATUS](PROJECT_STATUS.md)，接续见 [toolalign.md](../toolalign.md)。原十天安排保留为历史计划。

| 工作 | 状态 | 下一动作 |
|---|---|---|
| P00 契约、P02 v3 数据、P03 CPU 工具 | VERIFIED | 复用已验收输入 |
| P01 Mac 兼容、P04 CPU 与 MLX toy | VERIFIED（原范围） | 留存证据，不再启动 Mac 训练 |
| P04 v3 数据接口 / PR19 | VERIFIED | 主干 abdc53d，定点 163 passed |
| G1 交接与执行准备 | COMPLETE | S1 接班；基线/数据/工作区/接入定位闭合，见 GOAL |
| P04 CUDA SFT 首包 / T1 | ACCEPTED（CPU） | 4342af8；PR21合并回执将固定后续执行源码 |
| P04 CUDA 依赖与 Colab / E1 | ACCEPTED（CPU） | 6183870；30项检查及独立复核通过，S1原失败上下文5项通过 |
| P04 Colab 独立复核 / R1 | r3 PASS | 7825216；两项问题均已关闭，原r1/r2 FAIL保留；跨session组合PASS |
| P04 CUDA SFT 独立复核 / R1 | PASS | 7d460f2；14项核心、3项进程及独立数值通过 |
| P04 CUDA mask 与说明 / Q1 | PASS（13例预审） | 82f1e88；423项检查及26条原证据绑定通过，20例容量数组后续增量核对 |
| P04 容量数组 / Q1增量 | PASS | ed022da；20条、531项检查通过，验证分母335 |
| P04 Linux 实装索引 / E1、R1 | ACCEPTED（CPU） | 99b8116经c4b5c1c独立PASS；48 pins/894 hashes未变，S1两项集成通过 |
| P04 L4 容量与恢复 v1 | 原FAIL保留 | PR22主干实装/3步通过；第2步恢复后更新超容差，见原实测报告 |
| P04 CUDA恢复定位 / T1、R1 | 重复backward差异已实测 | [同状态诊断](../reports/S1_P04_CUDA_RESUME_DIAGNOSTIC_R1.md)：开/关checkpointing均约0.86%梯度差；下一步核查确定性路径，原恢复FAIL保留 |
| P04 CUDA严格确定性 / T1、R1 | ACCEPTED | [v2实测](../reports/S1_P04_CUDA_V2_RECOVERY.md)：两种恢复均逐值一致，R1 be756a1独立PASS；恢复问题已关闭 |
| G2 实际结果终验 / R1、Q1 | 验收PASS | R1技术PASS、Q1 847e0be数据与说明PASS；65文件已回收、两实例已停止 |
| P04 正式 SFT / G3 | PREPARING，训练NOT_RUN | [固定计划](tasks/P04_CUDA_G3_SFT.md)；T1补充原始验证CE，随后完整数组增量审查；198/743次更新 |
| P05 偏好与 DPO | NOT_RUN | 已验收 SFT 起点；Q1 偏好审核；CUDA DPO 验证 |
| P06 固定协议对照 | NOT_RUN | 原始/SFT/DPO 同协议，训练与评测分开 |
| P07–P09 服务、复现、交付 | NOT_RUN | GPU 在 Colab，Mac 可做客户端和分析 |

S1 独占当前状态维护。旧未派发 MLX runtime CPU 任务由 Colab 路线取代，不能自动恢复。G1、G2验收已经完成；后续GPU执行继续绑定精确候选、独立复核和有界配置。[历史看板](https://github.com/kris0516/ToolAlign/blob/abdc53d468a270cc1bfecbe56980dd34918480e1/coordination/BOARD.md)。
