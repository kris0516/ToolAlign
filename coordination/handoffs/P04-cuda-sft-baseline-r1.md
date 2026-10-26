# T1｜G3 原始 checkpoint 验证 CE 交接

候选实现完成，待R1独立审核。授权 `7eb0ac97e394528d82533c6cc92c298aa5d305b0`，代码基线 `75209551c8520e5c97ed5cb424a686657a6d9da4`，分支 `codex/p04-cuda-sft-baseline-r1`；精确提交由原生回报提供。

fresh SFT 首次更新前用官方 `disable_adapter()` 和既有完整validation聚合，写 `original-validation.json`，summary关联该文件；capacity与resume明确返回NOT_RUN。step0独立于训练checkpoint和SFT选模。tiny实测发现旧evaluate会统一子模块模式，因此仅补充逐模块模式恢复。

[检查报告](../../reports/experiments/P04_CUDA_SFT_BASELINE_R1.md)记录新增行为、原始命令和失败证据。8项定点CPU检查、三文件ruff通过；非零adapter与原始底座对照、分母、模式/权重/RNG/后续更新、跳过分支及step0不参与选模均有原创tiny证据。没有重跑未变的G2完整矩阵。

本轮真实模型、GPU、SSH、编码和安装均0；v2数值策略、共享配置、依赖、checkpoint schema及控制器未改。R1审核后由S1执行G3，首段独立记录由原控制器随完整输出目录回收，后续恢复段关联首段记录。CPU PASS不是正式G3结果。
