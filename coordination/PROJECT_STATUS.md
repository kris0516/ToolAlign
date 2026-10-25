# 项目真实状态

更新：2026-10-26（Asia/Shanghai）。当前入口：[toolalign.md](../toolalign.md)。生产代码基线 `abdc53d468a270cc1bfecbe56980dd34918480e1`；后续训练改用 Colab GPU。

| 阶段 | 已支持的结论 | 关键证据 |
|---|---|---|
| P00 | CPU 基础包、冻结契约与互斥 VERIFIED | [main 验证](../reports/P00_MAIN_VERIFICATION.md)，PR2 |
| P01 | Mac 受限 SFT 与唯一 DPO 备选兼容通过；首选 DPO 原 FAIL 保留。这是原平台结论 | [main 验证](../reports/S0_P01_MAIN_VERIFICATION.md)，PR6 |
| P02 | 冻结 v3 数据、来源处置、13 例材料通过技术与 AI 质量审核；G-DATA PASS | [技术 main](../reports/S0_P02_QUALITY_V3_MAIN_VERIFICATION.md)、[Q1](../reports/S0_P02_Q1_V3_ADJUDICATION.md)，PR15 |
| P03 | CPU 工具、oracle、scripted 执行器 VERIFIED；模型评测未运行 | [main 验证](../reports/S0_P03_MAIN_VERIFICATION.md)，PR7 |
| P04 准备 | CPU collator、MLX 原创 toy 数值、固定 Qwen CPU 接口通过 | [CPU](../reports/S0_P04_SFT_CPU_MAIN_VERIFICATION.md)、[toy](../reports/S0_P04_SFT_NATIVE_TOY_MAIN_VERIFICATION.md)、[模型接口](../reports/S0_P04_QWEN_CPU_MAIN_VERIFICATION.md)，PR10/11/17 |
| P04 v3 接口 | R1-r3 PASS；PR19 已合并，main 定点 163 passed | [main 验证](../reports/S0_P04_DATA_V3_MAIN_VERIFICATION.md) |
| P04 正式 SFT | NOT_RUN；CUDA 适配、依赖锁和容量实测待完成 | [下一任务](BOARD.md) |
| P05 DPO | NOT_RUN；偏好数据、CUDA reference/优化路径待建立 | [训练规格](../docs/03_TRAINING_SPEC.md) |
| P06–P09 | 模型对照、正式服务、最终复现与研究交付未完成 | [评测规格](../docs/04_EVALUATION_SPEC.md)、[审核规则](REVIEW_POLICY.md) |

已接收的 84 个问题当前全部关闭；原 FAIL、隔离样本和原始证据保留。数据质量或 toy PASS 都不是正式模型效果。

## 本次交接

合入已独立审查的 PR19；重写接续入口，转向 Colab；复用另一项目的 CLI/ADC/SSH/tmux 方法；整理本地技能；清理停用训练环境与可再生缓存。本机清单在 `.toolalign-local/handoff-2026-10-26/`，公开摘要见[整理记录](../reports/S0_COLAB_HANDOFF.md)。

本次无新模型下载、GPU 实例、训练、偏好生成或正式评测。ToolAlign CUDA 环境、checkpoint 恢复和跨实例续训待验证。

## 下一步

用户新开 Supervisor，按 [toolalign.md](../toolalign.md)准备 P04 CUDA 适配；先显存预算，后短容量验证，再 SFT。T1/D1/E1/R1 本次未重新派发；Q1 仅做本次交接材料的独立只读审核。长期目标未完成，此次交接不登记为 P00–P09 完成。

完整历史见[迁移前状态](https://github.com/kris0516/ToolAlign/blob/abdc53d468a270cc1bfecbe56980dd34918480e1/coordination/PROJECT_STATUS.md)和各阶段报告。旧 Mac 包的“待派发”状态不覆盖新路线。
