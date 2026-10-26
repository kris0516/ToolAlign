# ToolAlign 当前看板

更新：2026-10-27。证据见 [PROJECT_STATUS](PROJECT_STATUS.md)，接续见 [toolalign.md](../toolalign.md)。原十天安排保留为历史计划。

| 工作 | 状态 | 下一动作 |
|---|---|---|
| P00 契约、P02 v3 数据、P03 CPU 工具 | VERIFIED | 复用已验收输入 |
| P01 Mac 兼容、P04 CPU 与 MLX toy | VERIFIED（原范围） | 留存证据，不再启动 Mac 训练 |
| P04 v3 数据接口 / PR19 | VERIFIED | 主干 abdc53d，定点 163 passed |
| G1 交接与执行准备 | COMPLETE | S1 接班；基线/数据/工作区/接入定位闭合，见 GOAL |
| P04 CUDA SFT 首包 / T1 | ACCEPTED（CPU） | 4342af8；PR21合并回执将固定后续执行源码 |
| P04 CUDA 依赖与 Colab / E1 | ACCEPTED（CPU） | 6183870；30项检查及独立复核通过，S1原失败上下文5项通过 |
| P04 Colab 独立复核 / R1 | r3 PASS | 7825216；两项问题均已关闭，原r1/r2 FAIL保留；跨session组合PASS |
| P04 CUDA SFT 独立复核 / R1 | PASS | 7d460f2；14项核心、3项进程及独立数值通过 |
| P04 CUDA mask 与说明 / Q1 | PASS（13例预审） | 82f1e88；423项检查及26条原证据绑定通过，20例容量数组后续增量核对 |
| P04 容量数组 / Q1增量 | PASS | ed022da；20条、531项检查通过，验证分母335 |
| P04 Linux 实装索引 / E1、R1 | ACCEPTED（CPU） | 99b8116经c4b5c1c独立PASS；48 pins/894 hashes未变，S1两项集成通过 |
| P04 L4 容量与恢复 v1 | 原FAIL保留 | PR22主干实装/3步通过；第2步恢复后更新超容差，见原实测报告 |
| P04 CUDA恢复定位 / T1、R1 | 重复backward差异已实测 | [同状态诊断](../reports/S1_P04_CUDA_RESUME_DIAGNOSTIC_R1.md)：开/关checkpointing均约0.86%梯度差；下一步核查确定性路径，原恢复FAIL保留 |
| P04 CUDA严格确定性 / T1、R1 | ACCEPTED | [v2实测](../reports/S1_P04_CUDA_V2_RECOVERY.md)：两种恢复均逐值一致，R1 be756a1独立PASS；恢复问题已关闭 |
| G2 实际结果终验 / R1、Q1 | 验收PASS | R1技术PASS、Q1 847e0be数据与说明PASS；65文件已回收、两实例已停止 |
| G3 原始验证 CE / T1、R1 | ACCEPTED（CPU） | c633bd7经fd4ad07独立PASS；8项实现检查、4项独立检查通过 |
| G3 完整数组 / Q1 | ACCEPTED | 98cf0e1；两个profile共7,928行逐行核对通过，13例身份不变 |
| P04 正式 SFT / G3 | COMPLETE | [结果与曲线](../reports/S1_P04_CUDA_G3_SFT.md)；PR27主干1267d1a、双Python CI成功；R1/Q1通过，实例已停止 |
| G4 CUDA候选生成 / T1 | r2 CPU独立审核已接纳 | [R1 r2](../reports/reviews/P05_G4_MODEL_VALIDATION_R2.md)7d36b49，47项既有检查及1项独立spawn检查通过；单条实际诊断已回收 |
| G4 train任务与偏好 / D1 | CPU与生成前语料已接纳 | [R1](../reports/reviews/P05_G4_PREFERENCE_R1.md) PASS；[Q1语料r2](../reports/reviews/P05_G4_CORPUS_Q1_R2.md) PASS，类型问题关闭、原FAIL保留 |
| G4 真实生成 / S1 | 80/80完成，0成功/0偏好；L4已停止 | [实测](../reports/S1_P05_G4_GENERATION_R1.md)：61超时、19其他失败；已回收并保持原分母，另两条诊断单列；累计分配4,477.560秒/1.75 CU |
| G4 原生TRL DPO / E1 | CPU独立审核已接纳 | [R1 r2](../reports/reviews/P05_G4_DPO_R2.md)8ce08bf复验原反例PASS，输出预算问题关闭、计数1→0；原FAIL保留 |
| G4 偏好处置 / Q1 | NO_ELIGIBLE_PAIRS已接纳 | [审核](../reports/reviews/P05_G4_PREFERENCE_Q1_R1.md)5321842：80条分母、0对及监督范围核对一致；ordinal 8诊断第三次为额外工具，DPO保持BLOCKED |
| P05 正式 DPO | NOT_RUN | [协议](tasks/P05_G4_PROTOCOL.md)；当前无有效chosen，零对不启动DPO |
| G5 评测后端 / T1 | R1 PASS已接纳 | 候选60c52f8，独立审核37eb027；复用231项通过/1项既有pip检查跳过与1项工具组合，新增6项独立检查通过，8+8个child回收；[审核](../reports/reviews/P06_G5_EVALUATION_R1.md) |
| G5 独立工具 / E1 | R1 PASS已接纳 | 候选6027096，独立审核c6c81db；109项既有/新增检查与3项独立检查通过，8+4个child回收 |
| G5 原L1语料 / D1 | 原48题永久隔离 | d4c4251原反例和REQUEST_CHANGES保留，独立L1为0；001/002后续经新题r2复验关闭，不恢复原题；[原Q1审核](../reports/reviews/P06_G5_CORPUS_Q1_R1.md) |
| G5 A2开发回放 / S1 | 24请求完成，独立终验已接纳 | 12/12原始输出配对相同，4次实际命中共5,176 tokens；完整请求总耗时91.175→91.006秒，见[实测](../reports/S1_P06_G5_EVALUATION_R1.md) |
| G5 BFCL与分析 / E1 | R1技术与Q1零题处置PASS已接纳 | 7e56244经R1 2b47acf、Q1 d31a6a6；固定150条0合格，L2分数NOT_RUN；[技术审核](../reports/reviews/P06_G5_DATA_ANALYSIS_R1.md)、[处置](../reports/reviews/P06_G5_BFCL_DISPOSITION_Q1_R1.md) |
| G5 L1观察依赖 / T1 | R1 r2 PASS已接纳 | ecbb520经eba411b复验：两原反例改判failure，合法分轮/独立batch保持；新增非相邻依赖真实轨迹及4个child回收；[审核](../reports/reviews/P06_G5_ORACLE_REFERENCE_R2.md) |
| G5完整隔离参考 / D1 | R1 r2 PASS已接纳 | f159b52经eba411b复验：0保留/48隔离，独立重建3,595节点/3,506组件；改名和schema等价变形仍传递隔离全部78旧节点；[审核](../reports/reviews/P06_G5_ORACLE_REFERENCE_R2.md) |
| G5新关系工具 / E1 | R1 r2 PASS已接纳 | 6f6a497经8e2b657独立PASS；复用60项检查及8个child，新增3项独立检查、3个child通过/回收；完整16,940份声明三类键交集0；[审核](../reports/reviews/P06_G5_CONSTRAINT_TOOLS_R2.md) |
| G5新语料 / D1 | R1与Q1正式r2 PASS已接纳 | 28题/4组/8恢复题；[R1 bb4fc27](../reports/reviews/P06_G5_CORPUS_R2.md)、[Q1 cb4c72d](../reports/reviews/P06_G5_CORPUS_Q1_R2.md)。001/002关闭、计数各1→0；原48隔离、A2不变 |
| G5 L4容量 | 冻结条件PASS，23份产物已回收 | 两模型各1,792输入tokens，实际输出27/33；31.646秒，采样峰值3,926/23,034MiB，两个child已回收；Action格式失败单列，实测最长序列1,825 tokens |
| P06 固定协议对照 | G5 COMPLETE，PR34主干核对通过 | [实测](../reports/S1_P06_G5_EVALUATION_R1.md)：M0/M1均0/28；A1均0/8，开启后8/8重试成功但未完成答案；245文件/124进程已回收，L4已停止，2,358.235秒/0.89 CU |
| G5实际终验 / R1、Q1 | PASS已接纳 | R1 b52c711五项独立核验、Q1 c4ef464逐例说明通过；S1回读540/523份私有证据，新增问题0；PR34主干98d642a、双Python CI全部成功 |
| P07–P09 服务、复现、交付 | G6 ACTIVE，两包CPU已集成 | T1 185d857 / E1 59b9c48作者证据已核对；[R1集成审核](tasks/P07_G6_INTEGRATION_REVIEW_R1.md)待独立结论，具体GPU smoke未启动 |

S1 独占当前状态维护。旧未派发 MLX runtime CPU 任务由 Colab 路线取代，不能自动恢复。G1–G3验收已经完成；G4的80条真实候选和独立加载诊断均已完成回收，L4已停止。Q1零对处置、E1 r2和T1 r2均已独立接纳；PR29已合并3250f1b；固定样本诊断20.883秒tool_round_limit，原前缀一致。R1 `fe26311` / Q1 `d5c55fb` 终验PASS已接纳，处置为DATA_INSUFFICIENT_WITH_NO_DPO；原DPO checkpoint条件未满足，M2保持NOT_RUN。PR30已合并d0a266d，双Python CI 40338862773全部成功且文件树一致，G4已按有据降级complete；G5也已随PR34主干核对后complete，G6为唯一active goal。G3正式训练和验证目标均为tool_calls，整条任务能力仍须单独测量；正式DPO未运行。[历史看板](https://github.com/kris0516/ToolAlign/blob/abdc53d468a270cc1bfecbe56980dd34918480e1/coordination/BOARD.md)。
