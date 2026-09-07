# S0｜v3 数据 CPU 原候选技术审查接收

2026-09-08，原候选 **CHANGES_REQUESTED**。独立 R1 对 `f3b7f1a1abb23cce3bdccb74ddc6d2e0477bb2aa` 正式判定 **FAIL，P0=0、P1=0、P2=1**；原审查提交 `b99a644e3ac0386f5ebe55cfd32e51b99e89781a` 已普通推送，唯一 parent 为该候选，tree `8ff42e0e9c74adeb78cfd0df40a9b8068521a5ae`。R1 原生 completed/idle 已核验。见[原审查报告](https://github.com/kris0516/ToolAlign/blob/b99a644e3ac0386f5ebe55cfd32e51b99e89781a/reports/review/P04-sft-data-v3-r1/REVIEW.md)；没有将失败候选提前合并 main。

唯一问题 `P04-SFT-DATA-V3-F1`：`data_v3._read` 先阻塞打开路径，随后才检查普通文件类型；无 writer 的 FIFO 因而不能及时拒绝。原探针、信号栈、空 writer 释放及 child 回收均已绑定。修订要求打开前拒绝非普通类型，并覆盖预检查后路径被替换的窗口；保留同 FD 的 fstat、no-follow、hash/大小与预算边界。首次正式未通过计 **1**；同轮复现、自测和接收检查不增加轮次，尚未达到整体暂停阈值。

S0 于 2026-09-07 20:55:57–20:56:06 UTC 完成只读接收，证明 `f240ef4ec109550b7cba4c2cea3f0a6422a1aebc6dacad41027e46e719c8beea`：

| 核对范围 | 实际结果 |
|---|---|
| 提交与源码 | 623 个审查文件、618 个候选和612个原基线字节绑定；仅新增5份审查/交接文件；原 SHA 与公开快照保持 |
| 原始命令 | 25 条 R1 命令逐 argv、UTC、前后源码、stdout/stderr、退出码与原生工具结果绑定；23条字面调用、2条有限数组调用，所有child均回收 |
| 现存证据 | 共65,185路径、1,628链接；1个原FIFO仅核对lstat类型/权限/device/inode，未读取其内容 |
| 历史来源 | 1,189项公开Git绑定、989个旧scope文件、根身份与旧审查保持；私有f708不在公开祖先 |
| 历史缺失 | 原30临时文件路径/1链接仍缺失，原封存与S0等字节副本保持，未恢复或冒称原件存在 |
| 原数据归档 | sdist 143成员，direct/rebuilt wheel各70成员；65生产包文件、metadata与RECORD保持原候选时点 |
| 制品总量 | 本轮私有文件、四个独占外部目录、公开审查和两层seal共132,945,444 bytes，低于1GiB |

原证据 seal `cdd2a826a40066d2c570d83dfb862dc0e21b09392ef09fccb5e13bfc1ec006be`，最终 seal `a6fb47b9616c36d99cd6dcdacd272bc7baaea02ffe2ae657c2ff05d5d6885058`，最终 envelope `6781ee178413c284de972c4a03bb484e21b3da65bc6a2c36ed6b5a11a9eeea8e`。全部 T1/R1 原失败与源码快照保持；R1 的6次辅助脚本失败与候选F1分开登记。原 source 首次消费缺失的终态 counter 仍为 `ABSENT_NOT_RECONSTRUCTED`。

正常路径的独立结果成立：135项相关既有CPU测试、27项原创反例/对照通过；一次新安装和一次固定 prepare/verify/13例转换/导出/回读通过。四视图7,928成员及13例双引擎26份完整记录与原字节、rank、EOS、mask、padding、token_texts和来源链一致，见[固定消费接收](S0_P04_DATA_V3_CPU_HANDOFF.md)。这些结果不关闭F1；原实际消费/安装额度已用尽。

T1 在原中间发现基础上交付完整修订 `1769046468eb2ebfdd9e982ba4938833760e3fe0`，代码 `53d86109f18e4131cff1ddcb905086892580d136`；两次原反例与147项CPU为其自测，S0完整接收进行中。原成文时尚未收到正式review SHA的记录保持实际时间；S0将本次唯一正式F1及精确原审查直接绑定到后续复审，不因重复同一要求而新增实现轮次。修订仍需独立R1、最终CI/main。

R1 下一[固定Qwen模型CPU审查](../coordination/tasks/P04_QWEN_MODEL_REVIEW.md)已准备接续；真实模型/框架、容量、编码和正式训练授权不变。S0本次新增生产API、build/install、编码、模型/GPU均0；冻结v3的G-DATA批准保持，正式trainer、baseline/SFT、评测与服务仍未验收。

21:06:16 UTC，S0完成原b99轮终态与91,517路径的派发前保全核验后，按完整 `9a29a72f9c418ff5c18c12f0065eae4f311aa3ec` 原生接续R1的精确01ee模型CPU审查并确认ACTIVE。新数据修订复审仍待T1完整接收；本次没有把原数据FAIL改写为PASS。
