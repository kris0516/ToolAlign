# R1｜P04 CUDA SFT r1 交接

对最终精确候选 `4342af87615197c7947d001f462d3d31500cd501` 独立技术审查 **PASS**，P0/P1/P2 均为 0。代码/测试提交 `95cf14224ceb2ea3a3e817826aeef0e651eb459d`；基线 `61c2176d556fd0e4cfc2af00b16242dddcfadfd3`；授权 `6ed2f020f923a8faafc21d4175ca5750aaaa5b23` 与 S1 同轮最终候选追加。完整结论见 [R1 报告](../../reports/reviews/P04_CUDA_SFT_R1.md)。

实际复核：核心 14 项通过，最终新增 3 项真实 CPU 进程检查通过；核心数值/数组/checkpoint 源码与原两份测试在最终候选中逐字保持。最终 SIGTERM、内部 deadline、正常退出均回收自有 child 并恢复 handler；只读回查三个 child 均不存在。没有重跑旧 163 项。

独立四参数解析模型验证 CE、梯度、一次 shift、prompt/pad mask、单 EOS、训练样本均权与验证 token 加权，以及尾组 7/2 两步标准 AdamW；全部在既定 FP32 容差内。新进程恢复的后续 loss、adapter 与 RNG 一致；best/last/rollback 的本地及第二副本完整性通过。真实模型 LoRA 参数/显存和 CUDA RNG 恢复仍待 Colab 实测。

最终 73 个包文件源码绑定、31 份作者原始记录、Linux 48/Mac 37 依赖 pins、定点 ruff 通过。作者 `pytest-06` 原 SIGTERM FAIL 保持，`pytest-07` 配置/源码/测试字节与最终候选一致。R1 两次辅助脚本失败分别为非法 toy profile 名称、重复统计 pytest `current` 链接；原脚本与输出均保留，纠正后通过，未修改生产实现或放宽断言。

私有交接 scope 为 `review-p04-cuda-sft-r1`；完整绝对位置与 review commit 由原生交接提供。数值结果 SHA256 `d764f3400bbcc347f1d933683e54f4147ee5448f478d1405f733c7cf5b0ffb87`；审计结果 `23511dd01bb1208c5bd360817bc84ff74a7152eb68dfe078bfa0134eef6b7c22`；测试制品索引 `bc5bea8bcad49fa810470d955d6bcf51e6a85de94b133ba88798f05432be04ff`。作者原始检查与本轮普通文件制品已有私有副本，特殊节点仅登记类型，符号链接仅登记目标。

本 review 只新增本交接与 R1 报告，不修改训练实现、配置/锁、共享状态或其他 worktree。旧 Colab review 与失败历史保持，E1 的两项独立 FAIL 不由此关闭。S1 负责集成、实际冻结数组/Q1 对应检查以及修订通过后的有界 Colab 容量和新实例恢复。本轮真实 prepare/新编码、真实模型、GPU、SSH、训练均为 0。
