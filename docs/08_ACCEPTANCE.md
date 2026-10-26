# 08｜验收、发布与证据等级

2026-10-27。以下质量门采用名称，避免与 [App分组目标G1–G6](../coordination/GOAL.md)混用。App G2是CUDA容量/恢复、G3是SFT、G4是偏好/DPO、G5是评测、G6是受限服务与交付；这些编号不等于某个质量门已通过。

## 1. 质量门

| Gate | 验收内容 | 必要证明 |
|---|---|---|
| G-CONTRACT | 契约与协作治理 | 版本、所有权、隔离工作区、资源锁 |
| G-COMPAT | 运行平台兼容 | 对应硬件/依赖、加载保存、损失/reference数学、容量/恢复 |
| G-DATA | 数据治理 | 来源、许可、分组隔离、长度/质量报告、独立Q1审核 |
| G-TRAIN | 模型训练 | 真实run、完整checkpoint、loss/mask、选模与恢复 |
| G-EVAL | 评测有效 | 冻结协议、原分母、oracle反例、实际结果与失败、BFCL范围 |
| G-SERVICE | 受限服务 | 固定工具、身份/鉴权、截止/取消、cache、loopback与真实回收 |
| G-RELEASE | 独立复核与交付 | R1技术复现、Q1说明审核、精确版本、许可、未完成项 |

SFT与DPO分别验收。CPU、历史MLX与CUDA证据注明实际平台；SFT通过不代表DPO训练通过。当前状态以 [PROJECT_STATUS](../coordination/PROJECT_STATUS.md)为准。

## 2. 发布条件

`v0.1.0-core`要求G-CONTRACT、G-DATA、SFT的G-TRAIN、G-EVAL和G-RELEASE；须有真实原始模型对照。没有语义改善时报告确切结果与失败原因。

`v0.2.0-preference`另要求DPO的实现、有效数据、真实训练与对照证据。G4已按无有效偏好有据结束，不能据此声明已获得DPO checkpoint。

`v0.3.0-serving`另要求G-SERVICE、Mac→SSH→Colab实际链路、启停/恢复与资源记录。客户端CPU示例通过仍不等于真实CUDA服务验收。上述为版本条件，实际tag/release发布须有GitHub读回记录。

## 3. 证据与完成层次

状态使用PASS / FAIL / BLOCKED / NOT_RUN / NOT_APPLICABLE，保留失败命令和原分母。交付至少包含精确commit、环境与依赖锁、输入manifest、模型/adapter身份、命令与原始日志索引、指标/失败、资源、审核交接和许可。大日志、权重、凭据及原始数据留私有；公开聚合结论可沿hash与独立审核追溯。

- 实现完成：源码存在，相关自测已经运行。
- 实验完成：真实模型按冻结输入与预算执行，结果完整回收。
- 独立验收完成：R1技术审核/复现、Q1语义或说明审核，经S1接纳。

CPU fixture不能补齐真实模型运行，AI审核不能替代未发生的执行。远端发布还须读回GitHub URL、commit、可见性及CI。

## 4. 独立Q1最终材料检查

按 [REVIEW_POLICY](../coordination/REVIEW_POLICY.md)，后续原需人工参与的语义、偏好与最终说明由独立Q1 AI承担，明确真实身份，不等待kris填表、签字或答辩。当前协调与验收职责由S1承接，历史S0审核记录保持原身份。

材料包括正常调用、无需工具、错误参数、故障恢复与预算终止；一条绑定真实证据的token/mask样本；DPO的SUM、EOS和冻结SFT reference数值说明；一条真实失败边界。实际偏好为0时使用已验证原创数学案例并明确无DPO训练，不制造训练对。当前入口见 [19号文档](19_REPRODUCTION_AND_DELIVERY.md)。

缺项由S1组织补充。同问题第1–4次正式未通过自主整改，第5次才整体暂停并通知用户；保留原失败，不因重复回读增加修订计数。
