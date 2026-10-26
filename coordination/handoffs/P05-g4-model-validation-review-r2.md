# P05 G4｜模型文件验证复用 R1 r2 交接

独立技术审核者 R1 AI。**PASS，新增阻断项 0。** 精确审核提交见最终交付；该提交只增加本交接及[审核报告](../../reports/reviews/P05_G4_MODEL_VALIDATION_R2.md)。

| 绑定 | 值 |
|---|---|
| T1 原提交 | `db5cbacf25499f5d1fa5ae66853eb5f3d66ef35f` |
| R1 受检 S1 集成提交 | `500d9dce4b66762efb72e3ed93a07ac3baa9454b` |
| 实现授权 | `3890349baeb7f262230873bd0f52b4d05deeca4e` |
| T1 索引 SHA256 | `5ff2beeadebb8123681beebfa8aabcb0ca87f646cc645cafdc6888c63fc89564` |
| R1 索引 SHA256 | `b3909f3bbb17fc4e2ee2e115dc3f3bce52bdc50eae46e2e8903de7d72877451f` |

R1 核对 8 个候选文件、13 份 T1 证据及 7 份最终回执，复用其中 47 passed。新增 1 项独立 CPU spawn 检查：初次完整验证 4 个文件；child 未重新哈希模型文件；原位改写后即使恢复字节及 mtime，旧验证对象仍因 ctime 变化被拒绝；进程已回收。独立 CPU 检查和证据回读命令均 exit 0，失败历史保留。

每次 execute 的完整预检、child 加载前后身份复查、默认 SFT/DPO 完整验证、共享 lease/checkpoint/adapter 实参检查及原 decode/seed/deadline 均符合本轮要求。预检成本计入 segment，动态耗时/stat 不进入恢复 hash，已有终态不重跑；冷加载口径标签明确。

S1 单条诊断脚本 SHA256 `c951acfe94069f0ffd40f4cb405d2b04bf31dd1ecd4588030b33f76412f5cc40` 只读审核 PASS。原始材料确认 Q1 选择为 ordinal 8（第 9 条）、seed 50；脚本只运行 1 条，segment 90 秒、轨迹 30 秒，显式传入本次完整验证对象，并隔离为非训练诊断。S1 下一步冻结 CI 已通过的 main、实际 run/control/authorization、脚本/config hash 和分配预算后再执行。真实性能、诊断结果和正式 DPO仍未运行，原 80 条与 0 偏好保持。

私有入口：`.toolalign-local/review-p05-g4-model-validation-r2/evidence-index.json`，绝对位置随最终交付提供；其中 `intake-readback.json` 绑定源码、回执及原样本，`cpu-probe-observation.json` 保留独立进程观察。未修改生产文件、共享状态、既有审核、S1 脚本或环境。
