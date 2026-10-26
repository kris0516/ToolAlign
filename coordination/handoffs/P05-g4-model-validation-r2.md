# P05 G4｜T1 批次模型文件验证复用 r2 交付

授权：`3890349baeb7f262230873bd0f52b4d05deeca4e`。分支：`codex/t1-p05-g4-model-validation-r2`。精确交付 commit 与私有证据索引随最终交付提供；报告见 [P05_G4_MODEL_VALIDATION_R2](../../reports/P05_G4_MODEL_VALIDATION_R2.md)。

生产 execute 先完整验证一次，向各 owned child 传递内存中的 `ModelFiles`；child 加载前后核对固定绑定、目录和文件 stat。复用原 FileIdentity/O_NOFOLLOW 检查，包含 ctime，因此同大小改写并恢复 mtime 仍拒绝。无持久缓存、无模型服务；原 SFT/DPO 默认 loader 仍完整验证。

预检成本单列 `summary.model_file_preflight_seconds`，并进入原 segment/分配预算。`batch_full_hash_child_stat.v1` 作为固定执行身份进入 batch hash；动态耗时/stat 不进入。child 冷加载增加范围标签，明确排除本批完整文件预检；后续诊断须通过生产 execute 或显式传入本次完整验证结果才能使用复用路径。

改动文件范围：`model_io/qwen_model.py`、`model_io/cuda_generation.py`、`training/cuda_sft/engine.py`、`training/cuda_generate/runner.py`、两份对应定点测试及本报告/交接。未改共享状态、固定 config/contracts/模板、依赖、DPO 或 Colab 控制器。

实际 CPU 检查：14 项文件/加载边界、16 项批次、17 项接口，共 47 passed，退出码均 0；Ruff exit 0。测试的真实文件检查与 MOCK_ONLY 模型边界在报告中分开说明，修订前失败保留。私有证据入口：`.toolalign-local/p05-g4-model-validation-r2/handoff-index.json`。

新真实模型加载、GPU 分配、模型调用、正式候选/DPO 均未运行；原 80 条不重跑或覆盖。本包交 R1 独立验收，性能和实际动作比较由 S1 后续另冻诊断。
