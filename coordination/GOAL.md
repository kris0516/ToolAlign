# S1 分组目标与验收

2026-10-26。用户指定 Toolalign Supervisor S1 接班并从 P04 CUDA 继续；S0 只读答疑。每次只有一个活动 App goal，达到本组验收才 complete，随后进入下一组。本文记录计划，不代替 App 实际 goal 状态。

大目标：在固定模型、冻结数据与评测预算下，比较 Qwen3 原始 checkpoint、LoRA SFT、SFT 后 DPO 的工具语义成功率、无需工具判断、故障恢复和资源成本，交付可复现代码、checkpoint、评测与受限推理接口。0.6B 用于冒烟，1.7B 为主实验。效果方向由观测决定，不预承诺提升比例。

当前：G1–G3已complete；G3验收PR27主干 `1267d1a33dfb08bfd9800b80ea97315730748952`。G4为唯一active goal，已完成80条真实候选、0成功/0偏好，产物已回收且L4已停止。Q1 `5321842` 的零对处置已接纳；按[实际结果](../reports/S1_P05_G4_GENERATION_R1.md)继续模型文件验证复用的CPU修订、DPO输出预算r2独立复审及一次有区分力的运行时诊断；正式DPO仍NOT_RUN。

| Goal | 阶段任务 | 验收产物与结束条件 |
|---|---|---|
| G1 交接与执行准备 | 基线与已有证据、数据/来源/模型定位、旧工作区归属、Colab 接入和 CUDA 首包规格 | S0/S1 协调权明确；准备缺口闭合；首包可分发。无 GPU 分配或训练 |
| G2 CUDA 链路与容量/恢复 | 当前接口真实 v3 读取和 13 例 mask；CUDA 依赖锁；PyTorch/Transformers/PEFT SFT；R1 技术与 Q1 语义复核；有界 L4 容量和恢复 | 正确的损失、末批、LoRA 参数和数据身份；CPU 检查与独立审核；真实 forward/backward/optimizer/validation/save/reload 证据；完整 checkpoint 新进程及新实例恢复分别实测。G2 不以正式模型效果为验收 |
| G3 正式 SFT 与原始模型对照 | 固定配置/预算；0.6B 冒烟，1.7B 一轮正式 SFT；相同格式的原始模型/已选 SFT 初步比较 | 可恢复 checkpoint、训练曲线、验证集选模记录和可比较的初步指标。冻结 train 数量为 1583/5938，对应 198/743 个 optimizer update；不把验证结果当最终测试 |
| G4 偏好与 DPO | 仅 train 候选；Q1 审阅；锁定 TRL/标准 sigmoid 目标及已选 SFT reference；容量/恢复后正式 DPO | 偏好集及处置记录、reference 身份、数学/工程检查、DPO checkpoint 与全部失败记录。停用 adapter 不能替代 SFT reference |
| G5 独立评测与归因 | 原始/SFT/DPO 同协议；语义、无需工具、参数错误与恢复；成本/延迟/内存；不确定性与必要对照 | 固定测试分母、失败分类、效应和不确定性、可复算表格；无提升或退化同样保留。数据/预算足够才扩大 seed 或归因实验 |
| G6 受限推理、复现与交付 | Colab GPU 推理和 Mac 客户端/工具边界；必要的重试/cache验证；独立复现与最终交接 | 可运行接口与案例、复现说明、独立复核、GitHub 交付。公网开放或新增采购另需用户明确决定 |

G2 首次 1.7B SFT 按 6–12 GiB 规划，L4 24GB 优先；这不是实测保证。容量探针覆盖最长冻结序列、首次优化器状态和保存/恢复，实际保留约 20% 显存余量；不足时按同协议改用实测 A100 80GB。每次 GPU 运行前锁定 run ID、配置、步数/时限、资源和产物上限、退出与恢复条件。端到端耗时须由首个实测吞吐与安装/传输时间推算。

训练、偏好生成、模型容量检查和批量模型评测全部在 Colab；Mac 只编辑、做小型 CPU 检查、控制与分析。最多两个实现对话并行、一个重 GPU 作业；独立 Codex 对话与隔离 worktree，禁止 sub-agent；统一 gpt-6-astra / max。

R1 独立技术复核，Q1 承接语义、偏好和最终说明审核。保留真实身份和失败；同一问题连续第 5 次正式修订未通过才按 [REVIEW_POLICY](REVIEW_POLICY.md)整体暂停。既有账户资源授权不包括购买、充值或无关私有数据上传。旧 S0 自动跟进维持 PAUSED；当前工作由 S1 的有界 goal 推进。
