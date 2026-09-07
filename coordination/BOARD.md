# ToolAlign 任务看板

规划基线 plan-v0.1；S0 已领取。只有 S0 可以更新此文件。P00 独立审查、合并和集成验证前不分发 P01–P03。

| 任务 | 负责人角色 | 依赖 | 当前状态 | 基线/证据 |
|---|---|---|---|---|
| [P00](tasks/P00_BOOTSTRAP_CONTRACTS.md) 仓库与契约 | S0 | 远端/本地环境可用 | VERIFIED | R1-r2 PASS `5d30e1b`；审查 `441d31b`；合并 `cd091e3`；main 176 项 CPU 检查通过 |
| [S0-SHARED-01](tasks/S0_SHARED_01.md) 公共依赖/来源政策 | S0 | P01/P02 实际申请 | VERIFIED | R1 PASS `e4127d9`；审查 `8ceea3f`；合并 `18fc847`；main 233 项 CPU 检查及 wheel 通过 |
| [S0-SHARED-02](tasks/S0_SHARED_02.md) P01环境/归档边界 | S0 | P01共享申请及实际打包缺陷 | VERIFIED | R1-r3 PASS `f8ec7ff`；审查 `ad3b519`；合并 `37c00de`；main176CPU、归档与隔离安装通过 |
| [P01](tasks/P01_HARDWARE_COMPATIBILITY.md) 本机校准与兼容 | T1 | P00 | VERIFIED | R1-r3 PASS 7e20706；[PR6](https://github.com/kris0516/ToolAlign/pull/6)合并d10722e，最终双Python CI与main655CPU/21条隔离命令通过；[G1分项证据](../reports/S0_P01_MAIN_VERIFICATION.md)，首选DPO旧FAIL保留 |
| [P02](tasks/P02_DATA_PIPELINE.md) 数据治理 | D1 | P00 | MERGED；质量CHANGES_REQUESTED | 原技术PASS与PR5验收保持；kris委托AI副本已收到，32个问题来源待新版本处理，G-DATA未通过；[交接](../reports/S0_P02_DELEGATED_REVIEW_INTAKE.md) |
| [P02-FORMAT-v1](tasks/P02_DATA_PIPELINE.md) 共用格式与序列 | D1；R1审查 | P02代码、ADR-0017 | VERIFIED | 原R1 b9f7567 PASS，PR8合并36b6988；最终双Python CI、main843CPU/2 HF-only skipped及归档绑定通过，见[主干证据](../reports/S0_P02_FORMAT_MAIN_VERIFICATION.md)；旧FAIL保持 |
| [P02-TRAINING-BINDING](tasks/P02_TRAINING_BINDING.md) 训练选择与人工序列材料 | D1；R1审查 | 已验证36b6988、ADR-0019 | VERIFIED（CPU） | 原R1 PASS40252f8及[PR9](https://github.com/kris0516/ToolAlign/pull/9)合并42eaa50的main919CPU/2跳过/归档证据保持。本批AI审阅已接收，实际页面NOT_RUN；修订版绑定/G-DATA/P04未完成 |
| [P02-QUALITY-REMEDIATION](tasks/P02_QUALITY_REMEDIATION.md) 来源暂挂与新版本候选 | D1 | 已验证86b80ba、ADR-0022 | IN_PROGRESS | 按2aa0cf4原生派发/新轮ACTIVE；01:30 UTC分支/输入intake核验通过，候选待交付 |
| [P02-QUALITY-AUDIT](tasks/P02_QUALITY_AUDIT.md) 扩展语义审计 | E1 | 已验证86b80ba、ADR-0022 | IN_PROGRESS | 新分支/输入及固定180新来源/200决策已由S0重算核对；32旧来源/40决策单列，语义判断待交付 |
| [P03](tasks/P03_EXECUTION_HARNESS.md) 工具与 oracle | E1 | P00 | VERIFIED | R1-r2 PASS a78071b；[PR7](https://github.com/kris0516/ToolAlign/pull/7)合并29a5e4c，最终双Python CI及main551CPU/18条隔离命令通过，见[主干证据](../reports/S0_P03_MAIN_VERIFICATION.md)；真实模型/正式评测NOT_RUN |
| [P03-CI-DEADLINE](tasks/P03_CI_DEADLINE.md) 截止时间测试稳定性 | E1；R1独立审查 | 最终CI实际失败；main4a1fa84 | VERIFIED | 原R1 1531892对947144f PASS；随PR8合并36b6988并完成最终CI/main验证，旧失败保留；E1/R1空闲 |
| [P04-SFT-CPU](tasks/P04_SFT_CPU_PREPARATION.md) SFT数据/collator与数值衔接 | T1；R1独立审查 | 技术基线42eaa50、ADR-0020 | VERIFIED（CPU部分） | 原R1 PASS800480b保持；[PR10](https://github.com/kris0516/ToolAlign/pull/10)合并e28f1db，最终双Python CI、main1014CPU/2跳过及三归档/57安装包文件绑定通过，见[证据](../reports/S0_P04_SFT_CPU_MAIN_VERIFICATION.md)。原CPU上游入口KeyError保留 |
| [P04-SFT-NATIVE-TOY](tasks/P04_SFT_NATIVE_TOY.md) 原生尾周期与状态绑定 | T1；独立R1；S0验收 | CPU已验证50867c0、ADR-0021 | VERIFIED（固定原创数值） | 原R1 PASS67976fd保持；[PR11](https://github.com/kris0516/ToolAlign/pull/11)合并b2247d8，最终双Python CI与main1084CPU/2跳过、三现存归档/58安装包字节绑定通过；[证据](../reports/S0_P04_SFT_NATIVE_TOY_MAIN_VERIFICATION.md)。正式模型与人工仍待完成 |
| [P04](tasks/P04_SFT_BASELINES.md) 原始模型/SFT | T1 | P01,P02,P03 | BLOCKED | NOT_RUN |
| [P05](tasks/P05_PREFERENCE_DPO.md) 偏好与 DPO | T1；D1 配合 | P04 | BLOCKED | NOT_RUN |
| [P06](tasks/P06_EVALUATION_ABLATIONS.md) 固定协议评测 | E1 | P04；DPO 对照需 P05 | BLOCKED | NOT_RUN |
| [P07](tasks/P07_LOCAL_SERVING.md) serving/cache | I1 | P01,P03,P04 | BLOCKED | NOT_RUN |
| [P08](tasks/P08_INDEPENDENT_REVIEW.md) 独立复核 | R1 | 分阶段；最终需 P06/P07 | BLOCKED | NOT_RUN |
| [P09](tasks/P09_RELEASE_HANDOFF.md) 发布与交接 | S0 | 对应级别验收通过 | BLOCKED | NOT_RUN |

## 分发批次

第一批：P00 完成后，先 P01 与 P02；P03 在资源允许时与 CPU 数据处理并行。依赖图允许并行不等于必须同时开全部对话。

第二批：P04 的 baseline/训练；T1 占 GPU 时 E1 继续 CPU oracle 检查。

第三批：P05 偏好（S0 拆成 D1 数据子包和 T1 训练子包，不使用子代理）、P07 非 GPU 服务骨架。

第四批：P06/P07 GPU 实验串行；R1 独立复核；P09 按实际验收级别发布。

公共跟进：原PR11固定原创数值VERIFIED与CPU入口KeyError历史证据保持。最新kris委托AI审阅已接收，不能用原空白表继续宣称本批未审；D1/E1两个CPU任务已按完整2aa0cf4原生派发并确认新轮ACTIVE，01:30 UTC合计6125条当前文件路径核验通过，候选/新审计仍待交付。浏览器显示仍NOT_RUN，页面体验待办独立保留。G-DATA质量整改、独立复核、真实0.6B容量及正式P04仍未完成，不由AI副本或toy结果放行训练；GPU空闲。
