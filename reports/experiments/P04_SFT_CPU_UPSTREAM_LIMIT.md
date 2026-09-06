# CPU公开train入口的最小反例

状态：**BLOCKED_UPSTREAM_CPU_ENTRY**。实际失败发生在精确`9e71552c22b4ed5daf4e4a66e24816bd61f53092`，2026-09-06 15:18:29–15:18:32 UTC。原生MLX-LM train循环执行0次、MLX optimizer更新0次；不是尾周期数值FAIL，也不是完整SFT实现PASS。

本机MLX0.32.2、MLX-LM0.31.3，实际trainer源文件SHA-256为`ee33ebdbd20a184108541cb490d08085485e71a82ffd6d68d7d216029ecd28fe`。包源码未改。进程持有共享租约，框架导入之前的已加载模型框架集合为空。随后设定并实际读回`Device(cpu, 0)`默认设备与CPU执行流，Torch设备cpu、2线程。原13条原创数值表格、专用loss和OrderedBatches均已构造；不是传入None模型产生的伪反例。

实际调用路径：`P04_SFT_CPU_TOY.py → train_toy_segments → mlx_lm.tuner.trainer.train`。已保存的错误为：

```text
trainer.py:229, in train
    mx.set_wired_limit(mx.device_info()["max_recommended_working_set_size"])
KeyError: 'max_recommended_working_set_size'
```

原train函数在所有public loss/batching注入调用之前执行上述表达式。Metal可用性检查为真，但缺省`device_info()`查询CPU默认设备，CPU信息没有该GPU专有字段。现有P01保护器只防止实际wired-limit setter调用；Python先求参数值，因此它无法避免该KeyError。

这解释了公开`loss`、`iterate_batches`、`TrainingArgs`参数为何无法解决本次入口失败。修正vendor元数据查询、重写其API返回值或先切换GPU默认设备都超出本轮边界；S0已要求保留原失败，不重复同一入口回放。没有用异常捕获后补造更新、修改梯度结果或替代循环冒充上游训练。

可复现命令的原完整路径与UTC已私有保存，公共参数形式为：

```text
PYTHONPATH=src <EXISTING_REPLAY_PYTHON> -B reports/experiments/P04_SFT_CPU_TOY.py supervise
  --mode segmented --repository . --output <NEW_PRIVATE_OUTPUT>
```

该监督入口实际创建新的自有子进程，先取得现有租约，300秒/4GiB限额，始终回收自有进程并保留退出记录。依赖必须使用既有锁定环境。命令形式供核查原始回执，不是重复当前失败或增加新框架修订的授权。

第二轮原stderr SHA为`38ee65ea5339b03e1182e8eed14220997ffeba1ee1419364224bd9cc65a8b2dd`，与[机器索引](P04_SFT_CPU_VALIDATION.json)实际记录相同。第一轮DLPack断言也保留：原探针误解已通过[版本化官方源码](https://github.com/ml-explore/mlx/blob/v0.32.2/python/src/array.cpp#L499-L510)定位，修订未改变CPU执行限制或`2e-6`数值容差。

本次可单独使用的数值证据仅为13例mask loss/梯度、padding、EOS和ignored-logits检查，以及default_loss padding负结果；native evaluate、8+5实际尾更新、最终保存重载和post-tail参数绑定均未运行。继续正式模型训练需新的独立决定与验收，不能从CPU计划或Torch参考推导已训练的MLX checkpoint。
