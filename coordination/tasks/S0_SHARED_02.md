# S0-SHARED-02｜P01 依赖重放与源码包边界

状态：READY_FOR_REVIEW；owner S0；base `97466a20f599f68c511b9c8a71fe5f2cdfd9ad4b`；branch `work/shared-backend-packaging`。

处理 T1 的具体共享申请：唯一备选 mlx-lm-lora 3.1.2、完整 P01 重放所需失败首选 mlx-tune 0.6.0，以及实际发现的 sdist 私有文件选择问题。保留默认 CPU 环境，复现已测传递依赖，明确安装与后端验收的区别。所有任务继续 gpt-6-astra/max；不新增实现对话。

允许 S0 修改：pyproject.toml、uv.lock、源码包验证脚本/CI、THIRD_PARTY_NOTICES、docs/14/15、AGENTS/README 与本包协调状态/ADR/报告。冻结 schema/validator/Protocol/runtime、T1/D1 实现和旧审查探针只读。完整 P01 仍由 T1 提交后另经独立审查。

验收：默认 CPU 依赖不漂移；可选组实际安装和 metadata 与 T1 实测清单一致，开发工具单列；Linux/Intel 的带 extra 解析不引入 ML/CUDA；固定 PyPI 制品及随包许可分别记录；`.codex` 下真实 worktree 的旧源码包可泄入合成私有文件，新选择排除并可从 sdist 建 wheel；CPU 回归、lint、冻结/公开扫描和独立 R1。

R1 只允许编辑 `coordination/handoffs/S0-SHARED-02-review-r1.md` 与 `reports/review/S0-SHARED-02/`。不修候选、不加载模型、不导入 ML 后端、不改正式状态。默认 CPU 安装与跨平台静态解析不等同于模型验收；有问题按具体 P0/P1/P2 报告。

S0 交接：`coordination/handoffs/S0-SHARED-02-r1.md`。精确候选在完成自查后固定，R1 PASS、最终 CI 和 main 集成验证前不发布新共享基线。
