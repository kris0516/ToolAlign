# 项目真实状态

更新：2026-10-26（Asia/Shanghai）。当前入口：[toolalign.md](../toolalign.md)。交接主干 `61c2176d556fd0e4cfc2af00b16242dddcfadfd3`，生产代码基线 `abdc53d468a270cc1bfecbe56980dd34918480e1`；当前唯一协调者 S1，后续训练使用 Colab GPU。

| 阶段 | 已支持的结论 | 关键证据 |
|---|---|---|
| P00 | CPU 基础包、冻结契约与互斥 VERIFIED | [main 验证](../reports/P00_MAIN_VERIFICATION.md)，PR2 |
| P01 | Mac 受限 SFT 与唯一 DPO 备选兼容通过；首选 DPO 原 FAIL 保留。这是原平台结论 | [main 验证](../reports/S0_P01_MAIN_VERIFICATION.md)，PR6 |
| P02 | 冻结 v3 数据、来源处置、13 例材料通过技术与 AI 质量审核；G-DATA PASS | [技术 main](../reports/S0_P02_QUALITY_V3_MAIN_VERIFICATION.md)、[Q1](../reports/S0_P02_Q1_V3_ADJUDICATION.md)，PR15 |
| P03 | CPU 工具、oracle、scripted 执行器 VERIFIED；模型评测未运行 | [main 验证](../reports/S0_P03_MAIN_VERIFICATION.md)，PR7 |
| P04 准备 | CPU collator、MLX 原创 toy 数值、固定 Qwen CPU 接口通过 | [CPU](../reports/S0_P04_SFT_CPU_MAIN_VERIFICATION.md)、[toy](../reports/S0_P04_SFT_NATIVE_TOY_MAIN_VERIFICATION.md)、[模型接口](../reports/S0_P04_QWEN_CPU_MAIN_VERIFICATION.md)，PR10/11/17 |
| P04 v3 接口 | R1-r3 PASS；PR19 已合并，main 定点 163 passed | [main 验证](../reports/S0_P04_DATA_V3_MAIN_VERIFICATION.md) |
| P04 真实 v3 消费 | 当前接口一次 prepare 与13例数组转换/导出/回读 PASS；0新编码/模型更新 | [S1消费记录](../reports/S1_P04_DATA_V3_CONSUMPTION.md) |
| P04 CUDA CPU 实现 | 4342af8 经独立R1审查 PASS；17项定点检查及独立数值/恢复通过，真实CUDA待运行 | R1原审查提交 `7d460f2054201c00055a1f924c5c4984be8e6988` |
| P04 CUDA mask 预审 | 13例真实材料与CUDA消费者对应PASS；423项检查、26条原证据绑定通过 | [Q1预审](../reports/reviews/P04_CUDA_MASK_Q1_R1.md)，`82f1e88` |
| P04 Colab CPU 控制 | r3独立PASS；两项控制问题均关闭，S1原失败上下文5项定点检查通过 | [R1-r3](../reports/reviews/P04_COLAB_ENVIRONMENT_R3.md)、[S1集成](../reports/S1_P04_CUDA_INTEGRATION.md) |
| P04 正式 SFT | NOT_RUN；CUDA 适配、依赖锁和容量实测待完成 | [下一任务](BOARD.md) |
| P05 DPO | NOT_RUN；偏好数据、CUDA reference/优化路径待建立 | [训练规格](../docs/03_TRAINING_SPEC.md) |
| P06–P09 | 模型对照、正式服务、最终复现与研究交付未完成 | [评测规格](../docs/04_EVALUATION_SPEC.md)、[审核规则](REVIEW_POLICY.md) |

现有86项问题全部关闭；Colab的RECOVERY-001经r2、PROCESS-001经r3独立复审关闭，原r1/r2 FAIL和全部失败历史保留。数据质量、CPU或toy PASS都不是正式模型效果。

## 本次交接

合入已独立审查的 PR19；重写接续入口，转向 Colab；复用另一项目的 CLI/ADC/SSH/tmux 方法；整理本地技能；清理停用训练环境与可再生缓存。本机清单在 `.toolalign-local/handoff-2026-10-26/`，公开摘要见[整理记录](../reports/S0_COLAB_HANDOFF.md)。

本次无新模型下载、GPU 实例、训练、偏好生成或正式评测。ToolAlign CUDA 环境、checkpoint 恢复和跨实例续训待验证。

## 当前接续

S1 已实际读取入口并与 S0 核对交接：交接时主干干净，生产路径未变；既有五个 worker worktree 干净，私有证据与数据保留；冻结输入 manifest 和 609 成员路径、D1 v3/来源根、Qwen 两个模型缓存均已定位。现有 Colab CLI 0.7.4 的认证查询成功，当次无活动实例。G1准备已完成；G2已完成上表真实数据消费，T1/E1已原生派发。模型缓存完整字节与CUDA尚未新验。

按 [GOAL](GOAL.md)依次推进。T1 CUDA和E1 Colab控制均已获得独立R1 PASS；Q1的13例mask预审通过。S1原组合检查42通过/1失败的现场保留，r3修后原失败上下文的5项定点检查通过。下一步以[PR21](https://github.com/kris0516/ToolAlign/pull/21)最终CI和合并回执冻结源码，执行固定20例容量数组的生成及Q1增量核对，再签发有界L4配置。GPU尚未分配，正式SFT/DPO/模型评测仍NOT_RUN。旧未派发Mac runtime不恢复。

完整历史见[迁移前状态](https://github.com/kris0516/ToolAlign/blob/abdc53d468a270cc1bfecbe56980dd34918480e1/coordination/PROJECT_STATUS.md)和各阶段报告。旧 Mac 包的“待派发”状态不覆盖新路线。
