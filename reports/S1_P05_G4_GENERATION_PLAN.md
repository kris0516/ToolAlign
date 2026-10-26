# S1｜G4 首批真实候选生成计划

2026-10-26。生成与偏好CPU实现已经[R1独立接纳](reviews/P05_G4_GENERATION_R1.md)，[Q1语料r2](reviews/P05_G4_CORPUS_Q1_R2.md)通过。S1回读了R1的27份证据及Q1-r2的38份证据，当前实现与受检源码相同。Q1-G4-CORPUS-001关闭、连续未通过计数由1归零，首次REQUEST_CHANGES和旧任务包保留。本报告冻结生成计划；GPU执行配置还须绑定合并主干的精确源码、输入和分配时间。

## 固定输入与顺序

采用G3选中的Qwen3-1.7B step743，完整checkpoint SHA256 `cfb02aec2279138c01f8b336abc08a588d0ab11efa8db68fd61ba0b6150b5d14`，adapter hash `973c440e29090892ad11d6d56b94bad4c98a5398c223e2b4302d7dba7c4640ed`。沿用原CUDA锁、BF16底座、FP32 Q/V LoRA、固定non-thinking模板与完整schema。

正式任务文件SHA256 `b9c6f18995579d8af1a58d137cafe9cc1c9f2f40279d9434aa85e2c7769eb015`；20个train任务、12个family、10类别、1个共享schema连通组。任务文件顺序不变，每题candidate-0至3，共80条，seed依全局序号为42至121，每次决策重置到该候选seed。temperature=0.7、top_p=0.9；每轨迹3次决策、2轮工具、每次256新token、30秒deadline。全部实际输入及原始输出保留。

候选计划在任何真实输出前冻结，文件SHA256 `f37c200baadcc9c1234d091cc97326bb2db5d5f366269095c9c51ac47ed09603`；对应偏好提取计划SHA256 `1659635252a0acd86fe0d28b022d1895e0873ddd4787dcb6a018ed9bb14af544`。先执行前12条，即无需工具、日期参数和多步依赖各一题的4候选。pilot计入80条总分母；后续最多执行其余68条，只续跑从未启动的ID。已启动且没有终态的记录为interrupted，已有失败不覆盖、不回填。

本轮tokenizer增量检查覆盖两处修订的8条实际脚本请求，最长1,755 tokens，含256预留为2,011；未受影响语料复用原检查。真实历史仍按完整上下文上限2,048处理，超长明确计数，不截断字段。

## 资源与继续条件

首选L4。推理规划包含3.20 GiB BF16底座、约0.006 GiB FP32 adapter、2,048位置的BF16 KV cache约0.219 GiB，以及至多约0.58 GiB的一份完整BF16 logits；无梯度或Adam状态驻留GPU。加入临时激活、CUDA workspace和分配器余量，先按6–10 GiB规划。此为估算，pilot测量实际allocated/reserved与设备占用，约20%显存余量作为继续条件。

本次生成分配含安装、模型下载、空闲、失败和回收最多5,400秒；pilot进程最多480秒，后续68条最多2,400秒，每段输出最多256 MiB。它们均计入G4累计21,600秒/12 CU上限，一次仅一个重GPU作业。完成生成并回收后停止该实例，偏好审核及DPO CPU工作期间不保留空闲GPU。

pilot核对实际加载身份、完整轨迹终态、30秒边界、冷加载/总耗时、显存和有效对产率。身份正确、资源有余量、无系统性后端故障且剩余分配可覆盖固定清单时，再冻结续跑配置。产率如实报告，不据此更换任务、补造chosen或调整采样；零对不启动DPO。需要改变源码或解码的诊断另记，不能自动重跑并覆盖正式候选失败。

传到实例的私有输入限于这批任务及其执行所需oracle、已选SFT checkpoint和有限控制脚本；原始底座按冻结公开revision在Colab下载。每段使用现有Colab控制器、owned child和GPU lease；终态日志、全部候选与资源记录回收并核对后再停止实例。正式偏好仍须依冻结池执行Q1审核，不能用生成前语料PASS替代。当前真实生成、正式偏好及DPO均NOT_RUN。
