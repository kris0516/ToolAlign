# 08｜验收、发布与证据等级

## 1. 阶段门

| Gate | 验收内容 | 必要证明 |
|---|---|---|
| G0 | 契约与独立对话治理 | schema version、任务 owner、branch/worktree、资源锁 |
| G1 | 本机兼容与校准 |真实硬件/依赖，加载训练保存，DPO reference/数学测试 |
| G2 | 数据治理 | 来源/许可、分组隔离、长度/质量报告、人工抽查 |
| G3 | 模型训练 | 完整 run manifest、checkpoint、loss/mask、adapter reload |
| G4 | 评测有效 | 冻结协议、分母、oracle 反例、BFCL 子集标注、未调测试集 |
| G5 | 服务/安全 | 白名单、超时、预算、取消、cache 身份、loopback |
| G6 | 独立复核与发布 | R1 检查、干净环境复现、release notes、已知局限 |

对 G1 的 SFT 与 DPO 分开打勾。SFT 通过不代表 DPO 通过。

## 2. 什么结果允许发布

`v0.1.0-core`：G0/G2/G3(SFT)/G4/G6。模型改善不是硬性数字门，但若没有改善，要清楚写失败分析；必须有真实 baseline。

`v0.2.0-preference`：在 core 基础上，DPO 的实现、数据、训练与对照证据全部通过。不能仅因为存了名为 dpo 的 adapter 就发布。

`v0.3.0-serving`：增加 G5、本机 API 复现与优化结果；只证明本地范围。

计划包标记 `plan-v0.1`，不冒用功能 release 标签。P01受限兼容性smoke与容量校准不等同正式模型训练或功能release；当前实测及未完成项见[项目状态](../coordination/PROJECT_STATUS.md)。

## 3. 不采用虚假百分制

不存在“代码 80 分即可证明工业级”的统一标准。验收按阻断项和证据完成度：PASS / FAIL / BLOCKED / NOT_RUN / NOT_APPLICABLE。安全、数据泄漏或错误指标不能靠 UI、代码量、文档长度弥补。

## 4. 发布证据包

最低文件：精确 commit、环境与依赖锁、数据 manifest、模型/adapter hashes、复现命令、原始日志索引、分类指标、失败分析、资源表、review handoff、已知限制、许可。

大日志/模型本机保留并记录 hash；公开副本只含安全允许材料。可校验 hash 不能单独证明结果真实，所以还要有命令、版本、抽样轨迹和独立复核。

## 5. 三层“完成”分开写

- 实现完成：代码存在，自测已运行。
- 实验完成：真实模型在固定数据/配置上运行，记录完整。
- 独立验收完成：R1 与 S0 检查证据并复现关键结果。

只到第一层，不得把后两层默认为完成。远端发布还需实际 GitHub URL、commit、public 状态读回验证。

## 6. kris 的最终检查

用新的任务展示正常调用、无需工具、错误参数、故障恢复、预算终止。用一条具体训练样本解释 token/mask，用一对 preference 解释 oracle 和 DPO reference，用一条失败样本解释无法解决的边界。

若不能脱离提示词讲清这三件事，先补理解，不继续加新框架。
