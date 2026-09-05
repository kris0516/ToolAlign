# ToolAlign 任务看板

规划基线 plan-v0.1；S0 已领取。只有 S0 可以更新此文件。P00 独立审查、合并和集成验证前不分发 P01–P03。

| 任务 | 负责人角色 | 依赖 | 当前状态 | 基线/证据 |
|---|---|---|---|---|
| [P00](tasks/P00_BOOTSTRAP_CONTRACTS.md) 仓库与契约 | S0 | 远端/本地环境可用 | READY_FOR_REVIEW | base `0f152e2`；分支 `work/p00-bootstrap-contracts`；R1-r1 FAIL 已修复；实现 6c71c9c；等待独立复核 |
| [P01](tasks/P01_HARDWARE_COMPATIBILITY.md) 本机校准与兼容 | T1 | P00 | BLOCKED | NOT_RUN |
| [P02](tasks/P02_DATA_PIPELINE.md) 数据治理 | D1 | P00 | BLOCKED | NOT_RUN |
| [P03](tasks/P03_EXECUTION_HARNESS.md) 工具与 oracle | E1 | P00 | BLOCKED | NOT_RUN |
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
