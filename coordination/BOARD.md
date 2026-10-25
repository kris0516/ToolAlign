# ToolAlign 当前看板

更新：2026-10-26。证据见 [PROJECT_STATUS](PROJECT_STATUS.md)，接续见 [toolalign.md](../toolalign.md)。原十天安排保留为历史计划。

| 工作 | 状态 | 下一动作 |
|---|---|---|
| P00 契约、P02 v3 数据、P03 CPU 工具 | VERIFIED | 复用已验收输入 |
| P01 Mac 兼容、P04 CPU 与 MLX toy | VERIFIED（原范围） | 留存证据，不再启动 Mac 训练 |
| P04 v3 数据接口 / PR19 | VERIFIED | 主干 abdc53d，定点 163 passed |
| G1 交接与执行准备 | 准备核对完成，首包待派发 | S1 接班；基线/数据/工作区/接入定位闭合，见 GOAL |
| P04 CUDA SFT 首包 / T1 | READY | 按 P04_CUDA_SFT 实现数据接口、损失与完整 checkpoint |
| P04 CUDA 依赖与 Colab / E1 | READY | 按 P04_COLAB_ENVIRONMENT 锁环境、准备启动/持久化/恢复入口 |
| P04 L4 容量与短 SFT | PLANNED | 适配、复核和显存预算后，一轮短验证 |
| P04 正式 SFT | NOT_RUN | 容量通过、明确配置与预算后运行 |
| P05 偏好与 DPO | NOT_RUN | 已验收 SFT 起点；Q1 偏好审核；CUDA DPO 验证 |
| P06 固定协议对照 | NOT_RUN | 原始/SFT/DPO 同协议，训练与评测分开 |
| P07–P09 服务、复现、交付 | NOT_RUN | GPU 在 Colab，Mac 可做客户端和分析 |

S1 独占当前状态维护。旧未派发 MLX runtime CPU 任务由 Colab 路线取代，不能自动恢复。G1 不运行 GPU；G2 两个实现首包先做 CPU 准备，GPU 执行须待精确候选、独立复核和有界配置。[历史看板](https://github.com/kris0516/ToolAlign/blob/abdc53d468a270cc1bfecbe56980dd34918480e1/coordination/BOARD.md)。
