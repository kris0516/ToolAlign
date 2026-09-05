# S0-SHARED-02｜独立审查交接

owner S0；base `97466a20f599f68c511b9c8a71fe5f2cdfd9ad4b`；branch `work/shared-backend-packaging`；状态 READY_FOR_REVIEW。精确 head 在原生派发消息中固定，审查者必须记录完整 SHA。

交付为 pyproject/lock 的可选备选及历史重放环境、显式 sdist 范围和 App 布局真实归档回归/CI、许可与环境说明。T1/D1代码和冻结接口未改。自查176CPU回归、包构建/从sdist重建wheel、默认/可选metadata、跨平台dry-run、lint/冻结/公开扫描见 reports/S0_SHARED_02.md。

R1 检查新可选依赖仅按平台/extra引入、实际tested版本闭包及真实fsspec变化；mlx-lm-lora metadata MIT与LICENSE Apache2.0不一致不得掩盖；p01-replay只能复现首选失败。亲自运行App .codex路径的源码包测试，并在小型合成fixture重放旧配置确认失败，不对真实私有目录进行有缺陷构建。只读T1枚举与S0原始证据可用于来源交叉核对。历史S0-SHARED-01精确包结构探针保持原候选意义，不能为了当前新增extra而改写旧PASS。

只允许 R1 新增 coordination/handoffs/S0-SHARED-02-review-r1.md 与 reports/review/S0-SHARED-02/；不修候选、不改状态、不加载模型或导入ML包。结论PASS/FAIL/BLOCKED并给P0/P1/P2，未审/CI/main验证前不发布新基线。P01完整代码/模型证据将另行审查。
