# S1｜G3 完整 SFT 与原始模型初步对照

状态：ACCEPTED_R1_Q1。0.6B完成198次更新、1.7B完成743次更新，全部941个训练事件连续；196个产物文件已回收，唯一L4实例已停止并确认不存在。R1 `300af3f`、Q1 `34331c2` 独立终验通过，S1已回读接纳。实际结果、曲线和证据见 [S1 G3报告](../../reports/S1_P04_CUDA_G3_SFT.md)。

实际执行源码为PR26主干 `2abbe7ac913661df1d5e430f285604b4ceb8ff4b`，双Python CI 40271208505成功。原始验证CE候选 `c633bd7` 经R1 `fd4ad07` 独立CPU审查通过；完整数组经Q1 `98cf0e1` 逐行审核后才分配GPU。两profile的13例语义材料身份未变。

固定方案见 [G3 v1计划](../../configs/sft-cuda-g3.v1.json)及CUDA v2配置：seed42、BF16底座、FP32 Q/V rank8、有效batch8、strict数值策略。smoke为1583 train/194 validation、198 updates、尾批7；formal为5938/213、743 updates、尾批2。实际完整验证分母分别为21226/23841个监督token。

两个原始模型点在首次更新前计算，不参与SFT选模。SFT每100步及final验证，按冻结规则保留最低CE的完整状态。smoke按100/198分段，formal按100/200/300/400/500/600/700/743分段；每段外部回收后从完整checkpoint继续，保持历史best。最终选中step198/743，CE分别为0.0414936900/0.0244376391；原始CE为0.7398840323/1.1452295558。

累计GPU占用9124.538896/14400秒，包含安装、空闲、失败和回收；账户余额观测差3.85/8 CU。原安装SSH Broken pipe及同一进程随后exit0的证据保留，未重复提交训练。没有改变原4小时、8 CU、一个重GPU作业和4GiB新增私有产物上限。

[R1技术终验](P04_CUDA_G3_FINAL_R1.md)已核对数值、完整状态、恢复和选模；[Q1数据与说明终验](P04_CUDA_G3_FINAL_Q1_R1.md)已核对实际消费和解释。主干发布后完成G3 App goal，再进入G4；不重复完整SFT。validation CE不替代G5工具语义测试，DPO和正式模型评测保持NOT_RUN。
