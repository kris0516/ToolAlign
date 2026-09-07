# ToolAlign 任务看板

最新审核参与方式：全部后续人工环节由独立Q1 AI承接；同一问题连续第5次正式修订审核未通过才整体暂停并通知kris，[规则/台账](REVIEW_POLICY.md)。

规划基线 plan-v0.1；S0 已领取。只有 S0 可以更新此文件。P00 独立审查、合并和集成验证前不分发 P01–P03。

| 任务 | 负责人角色 | 依赖 | 当前状态 | 基线/证据 |
|---|---|---|---|---|
| [P00](tasks/P00_BOOTSTRAP_CONTRACTS.md) 仓库与契约 | S0 | 远端/本地环境可用 | VERIFIED | R1-r2 PASS `5d30e1b`；审查 `441d31b`；合并 `cd091e3`；main 176 项 CPU 检查通过 |
| [S0-SHARED-01](tasks/S0_SHARED_01.md) 公共依赖/来源政策 | S0 | P01/P02 实际申请 | VERIFIED | R1 PASS `e4127d9`；审查 `8ceea3f`；合并 `18fc847`；main 233 项 CPU 检查及 wheel 通过 |
| [S0-SHARED-02](tasks/S0_SHARED_02.md) P01环境/归档边界 | S0 | P01共享申请及实际打包缺陷 | VERIFIED | R1-r3 PASS `f8ec7ff`；审查 `ad3b519`；合并 `37c00de`；main176CPU、归档与隔离安装通过 |
| [P01](tasks/P01_HARDWARE_COMPATIBILITY.md) 本机校准与兼容 | T1 | P00 | VERIFIED | R1-r3 PASS 7e20706；[PR6](https://github.com/kris0516/ToolAlign/pull/6)合并d10722e，最终双Python CI与main655CPU/21条隔离命令通过；[G1分项证据](../reports/S0_P01_MAIN_VERIFICATION.md)，首选DPO旧FAIL保留 |
| [P02](tasks/P02_DATA_PIPELINE.md) 数据治理 | D1 | P00 | MERGED；质量CHANGES_REQUESTED | 原技术PASS与PR5验收保持；kris委托AI副本已收到，83来源新版技术已VERIFIED，Q1确认旧处置并新增P02-Q-081待整改，G-DATA未通过；[交接](../reports/S0_P02_DELEGATED_REVIEW_INTAKE.md) |
| [P02-FORMAT-v1](tasks/P02_DATA_PIPELINE.md) 共用格式与序列 | D1；R1审查 | P02代码、ADR-0017 | VERIFIED | 原R1 b9f7567 PASS，PR8合并36b6988；最终双Python CI、main843CPU/2 HF-only skipped及归档绑定通过，见[主干证据](../reports/S0_P02_FORMAT_MAIN_VERIFICATION.md)；旧FAIL保持 |
| [P02-TRAINING-BINDING](tasks/P02_TRAINING_BINDING.md) 训练选择与人工序列材料 | D1；R1审查 | 已验证36b6988、ADR-0019 | VERIFIED（CPU） | 原R1 PASS40252f8及[PR9](https://github.com/kris0516/ToolAlign/pull/9)合并42eaa50的main919CPU/2跳过/归档证据保持。本批AI审阅已接收，实际页面NOT_RUN；修订版绑定/G-DATA/P04未完成 |
| [P02-QUALITY-REMEDIATION](tasks/P02_QUALITY_REMEDIATION.md) 来源暂挂与新版本候选 | D1；R1/S0验收 | 已验证86b80ba、ADR-0022 | VERIFIED（CPU） | PR12普通合并6c81dfc；原R1 PASS1e45cf2、最终双Python CI及main1,186CPU/2跳过，见[主干证据](../reports/S0_P02_QUALITY_MAIN_VERIFICATION.md) |
| [P02-QUALITY-ADJUDICATION](tasks/P02_QUALITY_ADJUDICATION.md) 裁定后新数据版本 | D1 | 已验证6c81；ADR-0024 | VERIFIED（CPU） | PR14普通合并d3e56f6；原R1 PASS d5b8、最终双Python CI/main62测试与三归档绑定通过；质量整改继续 |
| [P02-QUALITY-ADJUDICATION-R1](tasks/P02_QUALITY_ADJUDICATION_REVIEW.md) 新版技术审查 | R1 | 精确1c47e6a | VERIFIED（CPU） | 原d5b8 PASS/原生空闲；随PR14普通合并并完成最终CI/main验证 |
| [P02-QUALITY-EXCLUSION-v3](tasks/P02_QUALITY_EXCLUSION.md) 定点来源排除与材料复用 | D1 | 已验证d3e56f6；ADR-0025 | IN_PROGRESS | 两份数据/11例复用及42项自测已回报；Q1来源PASS已接收，14:48:51 UTC原两例编码已精确放行，完整候选待交付 |
| [Q1-P02-v3-sources-r4](tasks/Q1_P02_V3_SOURCE_REVIEW.md) 两替换来源提前审核 | Q1 | 固定2来源/3目标/8原turn | ACCEPTED（来源） | 原9c12c47正式交付/原生空闲；S0核验3,671路径/34命令，2来源/3Action及前缀PASS，旧issue计数不变；实际v3材料待后续审核 |
| [P02-QUALITY-REVIEW](tasks/P02_QUALITY_REVIEW.md) 修订技术独立审查 | R1 | 精确9b7cf01 | VERIFIED（CPU） | 原PASS1e45cf2保持；随PR12普通合并并完成最终CI/main验证，质量门槛保持 |
| [Q1-AI-REVIEW](tasks/Q1_AI_REVIEW.md) 后续委托AI审核 | 独立Q1 | ADR-0023 | ACCEPTED（首轮与r2） | 原5100/42d9保留SHA整合；两轮已接收/空闲，新版候选已交付，新Q1范围准备中 |
| [Q1-P02-r2](tasks/Q1_P02_EXPANDED_REVIEW.md) 扩展发现独立裁定 | Q1 | 固定50来源/60决策 | ACCEPTED | 原42d9/S0核验1,643路径及41命令；[接收](../reports/S0_P02_Q1_R2_ADJUDICATION.md) |
| [Q1-P02-v2-r3](tasks/Q1_P02_V2_REVIEW.md) 新版处置与固定材料审核 | Q1 | 精确1c47/346冻结输入 | ACCEPTED（审核交付） | 原8a738ab/原生空闲；旧83处置及13 mask PASS，新P02-Q-081首次FAIL1，S0核验3,135路径/80命令；质量待下一版 |
| [P02-QUALITY-AUDIT-REVIEW](tasks/P02_QUALITY_AUDIT_REVIEW.md) 原审计技术复核 | R1 | 精确5270d1e | CHANGES_REQUESTED | 原9645055 FAIL/P2=1、S0核验9,673路径/27命令；原生空闲 |
| [P02-QUALITY-AUDIT-TYPE-FIX](tasks/P02_QUALITY_AUDIT_TYPE_FIX.md) 审计JSON类型保真 | E1 | 已验证6c81/原5270 | VERIFIED（CPU） | PR13普通合并1887feb；原R1 PASS0cefe771、最终双Python CI与main55pytest/15页面检查通过 |
| [P02-QUALITY-AUDIT-TYPE-REVIEW](tasks/P02_QUALITY_AUDIT_TYPE_REVIEW.md) 类型修复复审 | R1 | 精确da22 | VERIFIED（CPU） | 原0cefe771 PASS/原生空闲；随PR13合并并完成main验证，原9645055 FAIL保持 |
| [P02-QUALITY-AUDIT](tasks/P02_QUALITY_AUDIT.md) 扩展语义审计 | E1 | ADR-0022 | VERIFIED（CPU技术） | PR13合并1887feb，最终CI/main通过；[证据](../reports/S0_P02_AUDIT_MAIN_VERIFICATION.md)，原判断/FAIL保持 |
| [P02-QUALITY-MATERIAL-REVIEW](tasks/P02_QUALITY_MATERIAL_REVIEW.md) 修订后16例审阅 | E1当前任务追加 | 精确1c90材料/新修订manifest | READY_FOR_REVIEW | 16例AI判断已交付/S0核验138路径；语义14/1/1、mask16 pass；质量未放行 |
| [P03](tasks/P03_EXECUTION_HARNESS.md) 工具与 oracle | E1 | P00 | VERIFIED | R1-r2 PASS a78071b；[PR7](https://github.com/kris0516/ToolAlign/pull/7)合并29a5e4c，最终双Python CI及main551CPU/18条隔离命令通过，见[主干证据](../reports/S0_P03_MAIN_VERIFICATION.md)；真实模型/正式评测NOT_RUN |
| [P03-CI-DEADLINE](tasks/P03_CI_DEADLINE.md) 截止时间测试稳定性 | E1；R1独立审查 | 最终CI实际失败；main4a1fa84 | VERIFIED | 原R1 1531892对947144f PASS；随PR8合并36b6988并完成最终CI/main验证，旧失败保留；E1/R1空闲 |
| [P04-SFT-CPU](tasks/P04_SFT_CPU_PREPARATION.md) SFT数据/collator与数值衔接 | T1；R1独立审查 | 技术基线42eaa50、ADR-0020 | VERIFIED（CPU部分） | 原R1 PASS800480b保持；[PR10](https://github.com/kris0516/ToolAlign/pull/10)合并e28f1db，最终双Python CI、main1014CPU/2跳过及三归档/57安装包文件绑定通过，见[证据](../reports/S0_P04_SFT_CPU_MAIN_VERIFICATION.md)。原CPU上游入口KeyError保留 |
| [P04-SFT-NATIVE-TOY](tasks/P04_SFT_NATIVE_TOY.md) 原生尾周期与状态绑定 | T1；独立R1；S0验收 | CPU已验证50867c0、ADR-0021 | VERIFIED（固定原创数值） | 原R1 PASS67976fd保持；[PR11](https://github.com/kris0516/ToolAlign/pull/11)合并b2247d8，最终双Python CI与main1084CPU/2跳过、三现存归档/58安装包字节绑定通过；[证据](../reports/S0_P04_SFT_NATIVE_TOY_MAIN_VERIFICATION.md)。正式模型与人工仍待完成 |
| [P04-SFT-RUNTIME-PROPOSAL](tasks/P04_SFT_RUNTIME_PROPOSAL.md) 真实模型接口只读方案 | T1 | 已验证d3；固定10份源码/元数据 | IN_PROGRESS | 实际新branch/intake经S0核验5,617路径/197链接通过；只读方案继续，无生产/框架/模型运行 |
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
