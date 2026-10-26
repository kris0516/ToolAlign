# P05 G4｜R1 最终技术复核交接 r1

独立技术审核者 R1 AI。**PASS；支持 `DATA_INSUFFICIENT_WITH_NO_DPO` 有据降级，新增 P0/P1/P2 均为 0，正式未通过计数增量 0。** 精确审核提交见最终交付，仅新增本交接及[报告](../../reports/reviews/P05_G4_FINAL_R1.md)。

授权提交 `31dc871d0a4c8c2a04545dcfca684f483f1e0b4a`；实际执行源码 `3250f1b83ecbaccea535d74232d6c3f28ffe4df7`。独立核对 111 份输入、93 份执行包文件、23 份回收产物及 tar/ACK，保存的双 Python CI 成功且合并树与受检头一致。新增 CPU 核对命令 `audit-02` exit 0；既有文件验证与 DPO 数学/恢复/输出预算证据复用，未重新运行矩阵。

ordinal 8、seed50 单列诊断的三次输入、前两次完整动作和两次观察与原记录一致；第三次返回 `filter_build_logs`，实际未执行，20.883 秒以 `tool_round_limit` 失败。预检 12.307 秒、child 冷加载 7.219 秒、完整段 33.939 秒，不能据此声称整体加速或已测批量吞吐。三个进程已回收，新实例已停止；G4 分配累计 4,477.560427 秒、余额观测 1.75 CU。

原 80 条正式候选及 0 偏好池保持，DPO 质量门 BLOCKED；DPO CUDA 容量、恢复、正式训练及 M2 checkpoint 均 NOT_RUN。建议 S1 结合 Q1 终验记录该明确降级，再冻结 G5 的 M0/M1 同协议比较与独立测试边界，M2 显式缺失。原计划的 DPO checkpoint 交付未满足，不将 CPU PASS 写作真实训练通过，不推断 DPO 负效果或 SFT 导致退化。G4/App goal 状态由 S1 裁定，本交付未修改。

| 私有证据 | SHA256 |
|---|---|
| S1 固定输入索引 | `e7e278dbe0a12f6dd51357612c0582c5253b9ae80a560cade1721d8bb61dede1` |
| R1 `evidence-index.json` | `acd061720acb9bf45ba8c345212d50f55c81c745322511d59bce90ea0a94a1b0` |

私有目录 `.toolalign-local/review-p05-g4-final-r1/` 的绝对位置随最终交付提供。索引绑定原始输入索引副本、审核脚本、命令回执与 `audit-result.json`。保留首次审核脚本的序列化断言失败及其修正依据、原安装 SSH 失败、原 80 条失败与既有问题历史。未改生产文件、共享状态、旧审核或环境；没有新模型、GPU、远端操作。
