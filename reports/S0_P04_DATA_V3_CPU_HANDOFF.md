# P04 v3 SFT 数据 CPU 完整交接接收

S0 已接收 T1 完整候选 `f3b7f1a1abb23cce3bdccb74ddc6d2e0477bb2aa`，tree `1cd40f093c17da1c5a1f1399117c29eb3c1d9547`；状态 **READY_FOR_REVIEW_CPU**。T1 原生轮已 completed/idle，普通推送的远端分支与本机相同。独立 R1 尚未派发，本次接收不签技术 PASS。

候选直接承接生产 checkpoint `bfdf2a256065d5396e6f7a4860fd7c7506f5c278`；原 code_base `48be4352bbad53ced5af84186edac036dd0ff2ca` 的 612 份公开文件保持。新增六份为数据模块、原创测试、S0 精确配置、两份实验报告和 handoff；成文只新增三份未打包文档，实际成功消费和三归档中的生产字节未变。[T1 报告](experiments/P04_SFT_DATA_V3_CPU.md)与[正式交接](../coordination/handoffs/P04-sft-data-v3-cpu-r1.md)尚在该候选，合并前从精确 Git 提交读取。

2026-09-07 19:34:49–19:34:50 UTC，S0 直接核验 **10,935 条当前文件路径**，证明 SHA `6eec52c12fe6a97a04f167a636fee7813efa22a5d96728dc80273ffe8aabd190`。其中终态 seal 绑定 618 公开文件、3,340 私有 scope 普通文件和 168 链接，另有本轮独占外部测试根的 2 文件/5 链接。所有集合有交集，不把这些数值相加作为独立覆盖率。

| 接收项目 | 已核验的实际结果 |
|---|---|
| 原始执行 | 40 份 argv/UTC/exit/stdout/stderr 与源码时点记录；34 直接字面量调用、6 个有限字面量循环调用，均关联真实 App 工具退出结果 |
| 封存 | terminal seal `3dbad95bd7cd5309f736cc3a2dd0d0d63374f78f2f9c9aaf9eb1226c5e716017`；terminal receipt `a1f2e37762cb71eef49d4ac1af88d5cefe631df4f8486577525cbbbd43c86fb6`；最终命令实际 exit 0 |
| 输入/历史 | 固定 609 成员、612 基线、556 原 Git/快照、5,190 旧私有路径、197 原链接与根身份保持；原悬空链接不补造目标 |
| 数据/数组 | 四 view：smoke 1,583/194、formal 5,938/213；13 唯一例/26 engine 原记录逐类型完整数组已在先前 S0 实物检查核验，当前所有绑定字节保持 |
| source/installed | 两套 prepared report、容器与 manifest 相同；容器 2,030,656 bytes，SHA `9b711be1ba6b301e6efb8c9853c0c6b98fdaa2db9db2e2cd2fa348739ca6ba0b` |
| 归档 | 直接 wheel/重建 wheel 各 70 成员，sdist 143 成员；直接解析现存实物、逐源载荷和完整 RECORD 核对，65 份安装包文件保持 |
| 自测 | 最终新增模块 135 passed；较早常规轮 758 passed/3 failed，三个旧环境相关负例换独占临时根后 3 passed；不累加重复用例 |

原生命令绑定证明 `5ecf4eff1779b8d5153504eccbd92993ca7043384b7844554b511e8a4de39f13`。两种历史日志格式分别处理；某次 App 包装输出在另一长输出之后显示完整终态，S0 仅解析该完整部分。工具显示的尾部/截断内容不等于原始全日志已显示；完整 stdout/stderr 文件另经 hash 核验。S0 最初的路径投影、两种日志 schema、有限循环/PTY 对应及 envelope 相对路径检查错误均保存在本轮私有接收记录，修正接收脚本后通过，没有重跑 worker 的任何生产消费或改动候选。

源码原 `v3_root_binding` 与安装原 Q1 seal `relative_path` KeyError 都保留。S0 [精确追加批准](../coordination/approvals/P04_DATA_V3_PREPARE_RETRY_R2.json)下，源码/安装 prepare 各两次（各含一次失败），完整转换/导出/回读各一次。原源码失败没有持久化 terminal counter，仍只按 traceback/源码推定边界；安装原失败实际 counter 单独保留。成功结果的来源、完整数组和额度检查见[此前消费记录](S0_P04_DATA_V3_CPU_DISPATCH.md)。固定消费、build/install 余额均 0。

R1 [完整独立范围](../coordination/tasks/P04_SFT_DATA_V3_REVIEW.md)现可冻结并派发。已再次确认 R1 原轮 completed/notLoaded、干净原 `dbd11d03e69c650efdb330f79ec380dd9914fa89`；旧保全的 53,333 当前路径/1,234 链接均复核。原全局 pytest 临时目录的 30 文件/1 链接缺失例外及等字节封存保持，见[保全说明](S0_P04_REVIEW_EVIDENCE_PREPARATION.md)，不恢复后冒充原件。

本轮 S0 构建、安装、数据 API、编码、框架/模型/GPU均为 0。R1 独立审查、最终 CI/main、真实 trainer、容量、正式 baseline/SFT/DPO/评测与服务仍待各自验收。G-DATA 冻结 v3 批准和旧失败保持；无需 kris 操作。
