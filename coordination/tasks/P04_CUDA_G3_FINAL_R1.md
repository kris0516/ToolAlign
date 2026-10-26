# R1｜G3 实际 SFT 与选模独立终验

状态：ACCEPTED。R1提交 `300af3f4137ecea481fe188c5994822d84221d74`，独立PASS，P0/P1/P2均为0；S1已回读实际证据并接纳，见[终验报告](../../reports/reviews/P04_CUDA_G3_FINAL_R1.md)。原授权为 `c658541bbf966c324353404ed3d964329e7c1670`，实际执行源码固定为 `2abbe7ac913661df1d5e430f285604b4ceb8ff4b`；以下保留原审查范围。

仅新增 `reports/reviews/P04_CUDA_G3_FINAL_R1.md`、`coordination/handoffs/P04-cuda-g3-final-r1.md` 及必要私有核对结果。独立读取实际10段运行和最后/最佳完整checkpoint，复算198+743个更新的连续step、cursor、有效batch及7/2条尾批；核对固定配置、模型、数组、依赖、strict数值策略及各段身份。

原始validation实现的CPU独立证据复用 `fd4ad07`，完整数组数据证据复用Q1 `98cf0e1`。从实际原始验证文件、events和summary独立复算CE分子/分母、每100步及final的验证点、历史best选择、最终CSV与图表。原始模型点不参与SFT选模，训练mean-example loss和验证token-weighted CE须分别标明。没有测试集选择或重复epoch。

核对每次恢复所指定的完整state摘要、adapter接续、optimizer/scheduler、步数、游标和RNG结构，最后/最佳state与索引和实际选择相符；检查历史best被保留到后续段，外部回收的manifest与文件实际字节一致。G2已有新进程/新实例更新复现证据，本轮不重复容量探针或训练矩阵。

检查退出、有限值、GPU资源、全部分配时间及余额观测差、输出预算、回收后停止与实例不存在证据。保存本轮安装SSH Broken pipe及原进程成功结束记录，不能把全部命令描述为一次性全绿。Torch峰值和1秒设备采样峰值分列；运行summary内部remote-copy状态不代替S1实际Mac回收。完整SFT没有另做底座内容全量hash，相关字段的NOT_RUN不得改称PASS。

使用既有CPU Torch环境读取保存张量与日志，不加载真实模型、不新增训练/编码/SSH/GPU/安装。每命令≤300秒、2线程、新增私有产物≤512MiB；大型状态文件只读核对，避免整套复制。交精确源码/材料/报告摘要、独立PASS/FAIL和可复核原始命令。S1负责状态维护及正式失败计数。

实际结果见 [S1 G3 报告](../../reports/S1_P04_CUDA_G3_SFT.md)。196个文件已回收，实例已停止，实际总占用9124.538896秒、余额观测差3.85 CU。私有证据索引SHA256：`be10313e0c200dde1a8c2c4660842a3d2474d9210ab7d01bda2cc506cecef544`。
