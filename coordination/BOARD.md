# ToolAlign 任务看板

规划基线 plan-v0.1；S0 已领取。只有 S0 可以更新此文件。P00 独立审查、合并和集成验证前不分发 P01–P03。

| 任务 | 负责人角色 | 依赖 | 当前状态 | 基线/证据 |
|---|---|---|---|---|
| [P00](tasks/P00_BOOTSTRAP_CONTRACTS.md) 仓库与契约 | S0 | 远端/本地环境可用 | VERIFIED | R1-r2 PASS `5d30e1b`；审查 `441d31b`；合并 `cd091e3`；main 176 项 CPU 检查通过 |
| [S0-SHARED-01](tasks/S0_SHARED_01.md) 公共依赖/来源政策 | S0 | P01/P02 实际申请 | VERIFIED | R1 PASS `e4127d9`；审查 `8ceea3f`；合并 `18fc847`；main 233 项 CPU 检查及 wheel 通过 |
| [S0-SHARED-02](tasks/S0_SHARED_02.md) P01环境/归档边界 | S0 | P01共享申请及实际打包缺陷 | VERIFIED | R1-r3 PASS `f8ec7ff`；审查 `ad3b519`；合并 `37c00de`；main176CPU、归档与隔离安装通过 |
| [P01](tasks/P01_HARDWARE_COMPATIBILITY.md) 本机校准与兼容 | T1 | P00 | READY_FOR_REVIEW | 新9fe3cbe已交付/空闲，85项hash和174份原文件核验；280CPU自测通过，R1-r3范围已准备；[Draft PR6](https://github.com/kris0516/ToolAlign/pull/6)保持，旧FAIL保留 |
| [P02](tasks/P02_DATA_PIPELINE.md) 数据治理 | D1 | P00 | MERGED | b0d8d83技术PASS、审查8e4fdbd；[PR5](https://github.com/kris0516/ToolAlign/pull/5)合并2ec1767，main338CPU/归档/隔离P02接口通过；整包/G-DATA仍待kris人审及配置绑定 |
| [P02-FORMAT-v1](tasks/P02_DATA_PIPELINE.md) 共用格式与序列 | D1 | P02代码、ADR-0017 | IN_PROGRESS | 按完整0c94ad5原生派发/确认ACTIVE；新共用模块和8,228例序列CPU审计，原数据/人审材料保持；尚未实现验收 |
| [P03](tasks/P03_EXECUTION_HARNESS.md) 工具与 oracle | E1 | P00 | ACCEPTED | R1-r2对3598cef正式PASS（review a78071b），139项hash和158份候选字节核验；待最终CI/合并/main验证；[Draft PR7](https://github.com/kris0516/ToolAlign/pull/7)保持，旧FAIL保留 |
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

公共跟进：P03精确候选的独立CPU复审与S0交接核验已通过，进入集成准备；T1启动修复9fe3cbe交付/空闲，R1上一轮completed/idle已核验，新P01-r3范围已准备待实际派发。D1按0c94ad5已原生启动新格式CPU实现和派生审计，仍在最多两个实现限额内。kris人审原请求、材料及填写副本保留，不代签判断。
