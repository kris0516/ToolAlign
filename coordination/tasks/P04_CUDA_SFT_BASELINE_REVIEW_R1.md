# R1｜G3 原始验证 CE 独立审查

状态：ACCEPTED（CPU）。R1提交 `fd4ad07cb4a6a083c5fc178ba30a5705cc2a9684`，P0/P1/P2均0，4项独立定点检查通过；S1已核对原始回执并接纳，见[报告](../../reports/reviews/P04_CUDA_SFT_BASELINE_R1.md)。候选 `c633bd70f4446bc8ea3ee80440944e6e6da7ff87`，实现授权 `7eb0ac97e394528d82533c6cc92c298aa5d305b0`，审查授权 `9bfb2b8467e9bfefd5b98c6de4557a38f4684d40`。以下保留本轮审查范围；实际完整数组及GPU训练仍待后续任务。

只新增 `reports/reviews/P04_CUDA_SFT_BASELINE_R1.md`、`coordination/handoffs/P04-cuda-sft-baseline-review-r1.md` 和必要私有证据。独立判断 [T1交付](../handoffs/P04-cuda-sft-baseline-r1.md) 是否正确补齐 [实现任务](P04_CUDA_SFT_BASELINE_R1.md)。不修生产、共享配置或状态。

核对 fresh SFT 在任何更新前用官方禁用adapter上下文和原验证聚合，结果覆盖完整冻结validation，绑定profile/source/data/model/config/dependency/runtime identity、step/cursor 0及实际分母。检查首段文件和summary关联、capacity/resume明确跳过、step0与SFT选模分离。运行上限仍包住该额外验证。

T1报告的模式变化是实际tiny反例：PEFT包装器与eval底座可能有不同的training值。审查逐模块还原是否保持原模式、adapter/可训练标志、权重、RNG和后续训练行为，包含验证异常路径；不需要没有观察依据的额外恢复层。

做最少充分的独立CPU数值/状态核验，使用既有环境和原创tiny。可复用现有fixture，但对原始函数与分母的关键判断须有独立依据；按风险选择新增或已有定点检查，不机械重跑T1全部8项，更不重跑G2旧全矩阵。v2数值策略、依赖锁、checkpoint schema与训练目标应无变化。

S1的G3计划固定完整profile、每100步/final验证、每25步checkpoint、每段外部回收及历史best传递；新加入的监督token预期来自原冻结sidecar，正式数组仍待后续编码和Q1审核。核对该计划与候选接口可衔接，不把CPU PASS写成G3实测完成。

每命令≤300秒、2线程、新增私有产物≤256MiB。真实模型/GPU/SSH/编码/安装均0。交精确审查commit、PASS/FAIL、必要问题与原始命令证据；S1按实际结论接纳和维护状态。
