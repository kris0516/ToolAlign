# S0-SHARED-01｜第一批公共依赖与来源政策

状态：READY_FOR_REVIEW；owner S0；base `4cfbe1a5b8d93c20d7b11ec14b31757a574d0903`；branch `work/shared-compat-source-policy`。

P01/P02 仅从已合并并验证的 P00 出发；本包解决其实际提交的公共申请，不取代两个独立实现任务。S0 允许改动 pyproject.toml、uv.lock、configs/source_toolace.v1.json、docs/01/12/13/14、THIRD_PARTY_NOTICES、正式 ADR/本包状态与 handoff、reports/S0_SHARED_01.md；其余尤其冻结 schema/validator/Protocol/runtime 和 worker 所有目录只读。

交付：可选 compatibility extra、明确可审计的 ToolACE 历史监督适配规则、来源与包元数据证据。非目标：不实现 D1 normalizer、不运行模型、不批准 DPO、不修改原始日志或替代 kris 质量审查。

验收：uv locked 默认和可选环境；default 无 MLX/Torch，platform markers 不引入 Linux CUDA；package metadata 固定版本；原 CPU 回归、lint/冻结/公开检查；独立 R1 检查精确候选的规则和依赖。全部 CPU、无 GPU 租约/模型下载，私有额外环境来自免费公开依赖。

S0 交接 `coordination/handoffs/S0-SHARED-01-r1.md`。R1 只允许提交 `coordination/handoffs/S0-SHARED-01-review-r1.md` 和 `reports/review/S0-SHARED-01/`，不能修候选后自签 PASS。S0 收到独立 PASS、CI 成功、合并与 main 验证后，才发布完整新基线给 T1/D1；此前它们继续已授权的私有探索/CPU 工作。
