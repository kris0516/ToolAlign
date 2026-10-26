# 项目真实状态

更新：2026-10-26（Asia/Shanghai）。当前入口：[toolalign.md](../toolalign.md)。G2验收已随PR25合入主干 `75209551c8520e5c97ed5cb424a686657a6d9da4`；实际G2执行源码为PR24 `eb73fbcdb5f053509a396c59092e28d7c317cdd9`。当前唯一协调者S1，活动goal为G3，后续训练使用Colab GPU。

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
| P04 CUDA 容量输入 | 主干920c415的20条编码/回读PASS；独立Q1 531项检查通过，13例身份不变 | [Q1增量](../reports/reviews/P04_CUDA_CAPACITY_ARRAY_Q1_R1.md)，`ed022da` |
| P04 Colab 真实安装 | PR22锁在L4真实安装PASS；48包/pip check通过 | [实测](../reports/S1_P04_CUDA_CAPACITY_R1.md)，原安装失败保留 |
| P04 CUDA容量/恢复 v1 | 最长2048 token三步容量PASS、采样峰值5180MiB；新进程恢复后更新超容差，跨实例未运行 | [实测与数值FAIL](../reports/S1_P04_CUDA_CAPACITY_R1.md)；两份输出已回收，实例已停止 |
| P04 CUDA恢复诊断 | 新实例初始状态严格一致；同进程重复backward差异约0.86%，关闭checkpointing仍存在；零更新 | [实际诊断](../reports/S1_P04_CUDA_RESUME_DIAGNOSTIC_R1.md)，29文件已回收、实例已停止；不构成更新恢复PASS |
| P04 CUDA确定性v2 / G2 | 验收PASS；实际三步、新进程及新实例恢复1,883项通过，672个张量比较差为0；R1/Q1独立终验通过 | [实测及接纳](../reports/S1_P04_CUDA_V2_RECOVERY.md)；65文件已回收、实例已停止 |
| G3 原始验证 CE | CPU实现及独立技术审核PASS；8项实现检查、4项独立检查通过，未改变SFT选模 | [R1审核](../reports/reviews/P04_CUDA_SFT_BASELINE_R1.md)，候选c633bd7、审核fd4ad07 |
| P04 正式 SFT / G3 | PREPARING，训练NOT_RUN；下一步冻结主干、生成完整数组并由Q1增量核对 | [执行计划](tasks/P04_CUDA_G3_SFT.md) |
| P05 DPO | NOT_RUN；偏好数据、CUDA reference/优化路径待建立 | [训练规格](../docs/03_TRAINING_SPEC.md) |
| P06–P09 | 模型对照、正式服务、最终复现与研究交付未完成 | [评测规格](../docs/04_EVALUATION_SPEC.md)、[审核规则](REVIEW_POLICY.md) |

88项问题全部关闭。CUDA-RESUME-001经R1 `be756a1` 的实际完整恢复独立验收关闭，正式修订失败计数0；Q1 `847e0be` 已确认数据身份与说明范围。原FAIL和全部失败历史保留。数据质量、CPU、toy或容量PASS都不是正式模型效果。

## 原 S0 交接记录

合入已独立审查的 PR19；重写接续入口，转向 Colab；复用另一项目的 CLI/ADC/SSH/tmux 方法；整理本地技能；清理停用训练环境与可再生缓存。本机清单在 `.toolalign-local/handoff-2026-10-26/`，公开摘要见[整理记录](../reports/S0_COLAB_HANDOFF.md)。

该次交接没有新模型下载、GPU实例、训练、偏好生成或正式评测。其后S1完成的CUDA实测以上表为准。

## 当前接续

S1 已与 S0 完成协调权和证据交接，冻结数据、来源根及模型缓存已定位；G1准备完成。G2通过当前接口读取真实v3数据，完成CUDA实现、锁定环境和实际容量/恢复；独立审核均已接纳。

按 [GOAL](GOAL.md)依次推进。PR24主干的v2三步容量、新进程和新实例恢复已通过R1技术终验与Q1数据/说明终验；1,883项S1检查无失败，672个adapter/Adam张量比较最大绝对差0，RNG与游标等完整状态一致。65个产物文件已回收校验，两实例已停止，G2累计占用3,640.213026/5,400秒。原v1 FAIL及诊断保留，详见[实际报告](../reports/S1_P04_CUDA_V2_RECOVERY.md)。下一阶段为G3：0.6B冒烟、1.7B一轮正式SFT及相同验证口径的原始模型对照。正式SFT/DPO/模型评测仍NOT_RUN。

完整历史见[迁移前状态](https://github.com/kris0516/ToolAlign/blob/abdc53d468a270cc1bfecbe56980dd34918480e1/coordination/PROJECT_STATUS.md)和各阶段报告。旧 Mac 包的“待派发”状态不覆盖新路线。
