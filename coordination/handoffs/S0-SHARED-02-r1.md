# S0-SHARED-02｜独立审查交接

owner S0；base `97466a20f599f68c511b9c8a71fe5f2cdfd9ad4b`；branch `work/shared-backend-packaging`；状态 READY_FOR_REVIEW。精确 head 在原生派发消息中固定，审查者必须记录完整 SHA。

交付为 pyproject/lock 的可选备选及历史重放环境、显式 sdist 范围和 App 布局真实归档回归/CI、许可与环境说明。T1/D1代码和冻结接口未改。自查176CPU回归、包构建/从sdist重建wheel、默认/可选metadata、跨平台dry-run、lint/冻结/公开扫描见 reports/S0_SHARED_02.md。

R1 检查新可选依赖仅按平台/extra引入、实际tested版本闭包及真实fsspec变化；mlx-lm-lora metadata MIT与LICENSE Apache2.0不一致不得掩盖；p01-replay只能复现首选失败。亲自运行App .codex路径的源码包测试，并在小型合成fixture重放旧配置确认失败，不对真实私有目录进行有缺陷构建。只读T1枚举与S0原始证据可用于来源交叉核对。历史S0-SHARED-01精确包结构探针保持原候选意义，不能为了当前新增extra而改写旧PASS。

只允许 R1 新增 coordination/handoffs/S0-SHARED-02-review-r1.md 与 reports/review/S0-SHARED-02/；不修候选、不改状态、不加载模型或导入ML包。结论PASS/FAIL/BLOCKED并给P0/P1/P2，未审/CI/main验证前不发布新基线。P01完整代码/模型证据将另行审查。

## 首轮 P1 修订交接

首轮精确候选 `55a330b6a1c10d14959895f2a3617597962569f3` 的目录内部 ignored 文件泄入已复现，不能沿用其自查或 CI 成功作为完整通过。修订将完整私有类别的显式排除应用于公共 Hatch build 层，同时保护 sdist 和直接 wheel；实际归档探针扩展至 85 项。对原配置的新探针真实失败，修订后 sdist/重建 wheel/直接 wheel 均通过。176 项 CPU、冻结、lint、构建和独立安装通过，原始 hash 见最新报告。修订没有改依赖闭包或 ML 实现。

R1 完成首轮正式报告后，对 S0 下一条原生消息固定的新完整 SHA 复审；保留首轮 FAIL，新增复审记录，不覆盖或改变旧失败探针含义。D1 在旧配置生成的失败归档已私有隔离、未上传，文档已补充这一后续事实。

## 大小写修订交接

第二候选 `8148929` 的小写反例已关闭，但 R1-r2 实际复现 Mac Git 忽略的大写/混合大小写文件进入 sdist 和两种 wheel。S0 修订实现 `ea05131` 使用显式 ASCII 大小写字符类，保留 `.env.example` 公开例外。实际 241 个私有探针排除、18 个公开对照和冻结 schema 在对应的三种归档中完整保留；临时合成仓库的 ignorecase 设置不会修改实际仓库或用户配置。新精确 SHA 在正式派发中固定，允许 R1 写 r3 handoff 和同目录新证据；r1/r2 的 FAIL、脚本与原始结果保持原含义。
