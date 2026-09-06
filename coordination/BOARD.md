# ToolAlign 任务看板

规划基线 plan-v0.1；S0 已领取。只有 S0 可以更新此文件。P00 独立审查、合并和集成验证前不分发 P01–P03。

| 任务 | 负责人角色 | 依赖 | 当前状态 | 基线/证据 |
|---|---|---|---|---|
| [P00](tasks/P00_BOOTSTRAP_CONTRACTS.md) 仓库与契约 | S0 | 远端/本地环境可用 | VERIFIED | R1-r2 PASS `5d30e1b`；审查 `441d31b`；合并 `cd091e3`；main 176 项 CPU 检查通过 |
| [S0-SHARED-01](tasks/S0_SHARED_01.md) 公共依赖/来源政策 | S0 | P01/P02 实际申请 | VERIFIED | R1 PASS `e4127d9`；审查 `8ceea3f`；合并 `18fc847`；main 233 项 CPU 检查及 wheel 通过 |
| [S0-SHARED-02](tasks/S0_SHARED_02.md) P01环境/归档边界 | S0 | P01共享申请及实际打包缺陷 | VERIFIED | R1-r3 PASS `f8ec7ff`；审查 `ad3b519`；合并 `37c00de`；main176CPU、归档与隔离安装通过 |
| [P01](tasks/P01_HARDWARE_COMPATIBILITY.md) 本机校准与兼容 | T1 | P00 | VERIFIED | R1-r3 PASS 7e20706；[PR6](https://github.com/kris0516/ToolAlign/pull/6)合并d10722e，最终双Python CI与main655CPU/21条隔离命令通过；[G1分项证据](../reports/S0_P01_MAIN_VERIFICATION.md)，首选DPO旧FAIL保留 |
| [P02](tasks/P02_DATA_PIPELINE.md) 数据治理 | D1 | P00 | MERGED | b0d8d83技术PASS、审查8e4fdbd；[PR5](https://github.com/kris0516/ToolAlign/pull/5)合并2ec1767，main338CPU/归档/隔离P02接口通过；整包/G-DATA仍待kris人审及配置绑定 |
| [P02-FORMAT-v1](tasks/P02_DATA_PIPELINE.md) 共用格式与序列 | D1；R1审查 | P02代码、ADR-0017 | VERIFIED | 原R1 b9f7567 PASS，PR8合并36b6988；最终双Python CI、main843CPU/2 HF-only skipped及归档绑定通过，见[主干证据](../reports/S0_P02_FORMAT_MAIN_VERIFICATION.md)；旧FAIL保持 |
| [P02-TRAINING-BINDING](tasks/P02_TRAINING_BINDING.md) 训练选择与人工序列材料 | D1；R1审查 | 已验证36b6988、ADR-0019 | READY_FOR_REVIEW | D1完整f4f73c9交付/原生空闲，S0核对3692路径及真实归档/安装记录，见[交接证据](../reports/S0_P02_TRAINING_BINDING_HANDOFF.md)；R1按完整5b553b4已原生派发/ACTIVE，实际页面/人审/G-DATA/P04仍待完成 |
| [P03](tasks/P03_EXECUTION_HARNESS.md) 工具与 oracle | E1 | P00 | VERIFIED | R1-r2 PASS a78071b；[PR7](https://github.com/kris0516/ToolAlign/pull/7)合并29a5e4c，最终双Python CI及main551CPU/18条隔离命令通过，见[主干证据](../reports/S0_P03_MAIN_VERIFICATION.md)；真实模型/正式评测NOT_RUN |
| [P03-CI-DEADLINE](tasks/P03_CI_DEADLINE.md) 截止时间测试稳定性 | E1；R1独立审查 | 最终CI实际失败；main4a1fa84 | VERIFIED | 原R1 1531892对947144f PASS；随PR8合并36b6988并完成最终CI/main验证，旧失败保留；E1/R1空闲 |
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

公共跟进：PR8共用格式与截止时间修订已VERIFIED。D1训练绑定完整f4f73c9已交付/空闲，S0交接核验通过；R1按完整5b553b4精确审查f4的新轮ACTIVE已原生核验，T1/E1无新任务。G-DATA语义审查、实际页面/token-mask判断、训练绑定独立审查及P04仍待完成，无新GPU作业。
