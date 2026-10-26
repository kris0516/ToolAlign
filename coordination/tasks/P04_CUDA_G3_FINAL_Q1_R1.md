# Q1｜G3 实际 SFT 数据与说明终验

状态：ACCEPTED。Q1提交 `34331c2e01bac93767c12a45d48704c2ef3d8fce`，数据与说明终验PASS；S1已回读实际证据并接纳，见[终验报告](../../reports/reviews/P04_CUDA_G3_FINAL_Q1_R1.md)。原授权为 `c658541bbf966c324353404ed3d964329e7c1670`，实际执行源码为 `2abbe7ac913661df1d5e430f285604b4ceb8ff4b`；以下保留原审查范围。

仅新增 `reports/reviews/P04_CUDA_G3_FINAL_Q1_R1.md`、`coordination/handoffs/P04-cuda-g3-final-q1-r1.md` 和必要私有核对结果。完整数组复用本人的 `98cf0e1` 审核，先核对实际消费manifest和配置身份；13例语义材料保持原版本，不重跑全数组/旧质量矩阵或重新标注。

核对smoke 1583 train/194 validation、formal 5938/213，198/743个更新及尾批7/2；原始和SFT的完整验证分母分别为21226/23841个监督token。每段cursor连续，恢复段不是独立重复实验。验证集只按已冻结规则选择SFT，原始模型点不参加该选择，测试集未消费。

独立从实际日志复核报告、数值CSV和图中全部验证点、最佳点与原始对照；训练mean-example loss和验证token-weighted CE口径区分准确。两模型使用各自冻结profile，不将它们直接当同数据规模的模型能力对照。CE结论限于完整validation的completion/EOS拟合，工具语义、无工具判断与恢复效果留G5；DPO留G4，不提前登记全项目完成。

检查实际退出、外部回收、资源预算和停止记录，以及安装SSH断线后原进程成功的事实；保留G2原失败历史。资源余额差属于观测，不写成精确账单归因；设备1秒采样峰值不等同连续测量全局峰值。真实AI reviewer身份与证据范围须明确。

只读已有JSON/CSV、图像及必要源码。每命令≤300秒、2线程、新增私有产物≤200MiB；不跑模型、GPU/SSH、训练、新编码、安装或未受影响的旧审查矩阵。R1并行负责张量和恢复技术验收；Q1交精确证据与明确PASS/FAIL，S1维护共享状态。

实际结果见 [S1 G3 报告](../../reports/S1_P04_CUDA_G3_SFT.md)。196个文件已回收，实例已停止，实际总占用9124.538896秒、余额观测差3.85 CU。私有证据索引SHA256：`be10313e0c200dde1a8c2c4660842a3d2474d9210ab7d01bda2cc506cecef544`。
