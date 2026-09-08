# S0｜固定原生运行CPU配置

状态：规则已冻结，任务PLANNED，未派发。固定模型接口已由PR17/main `f27951aea573d3e220b053563078d5e428564419`验收；数据FD修订仍待独立R1完整结论、最终CI/main。本次仅使用已合并的5份配置、方案与批准元数据，不读取变化中的worker源码或新数据/模型。

[配置](../configs/sft-qwen-runtime-cpu.v1.json)为24,039B，SHA `fa9e52b4f91be9e7d3a444df95229120204fdfb408521c42ef91e916ec605875`。它绑定模型metadata b8a5e48b、v3数据配置e27a7d4b、原运行方案bc57cd61、容量计划a25ddc2e和G-DATA批准1edb1e88。准备证明 `88913a5daf02caf85827e02a46446602599af5aa17413bdec7872f51f19b1e38`及最终规则补充 `cb0a0cef3e5a2d087d303f0ada1210f8d6594ba5e16057cfbcb202e5d156fd00`保持；先前未发布草案也完整保留。

| 固定计划 | 有序训练微步 | 计划优化更新 | 状态 |
|---|---:|---:|---|
| smoke完整一遍 | 1,583 | 198 | 元数据规则，实际0 |
| formal完整一遍 | 5,938 | 743 | 元数据规则，实际0 |
| 0.6B容量及固定过拟合诊断 | 79 | 10 | 元数据规则，实际0 |

准备已核对各分段rank连续、无缺失/重复、真实尾组divisor和全局更新数；容量另固定60例次诊断前向，实际0。保留原生compile、grad_checkpoint=False和固定Adam，复用验收数据/模型接口，不增加模型loader或复制上游训练循环。

CPU任务只实现配置/数组、分段状态、checkpoint和监督接口，并用原创模拟验证；真实609输入消费、13材料、23例编码、模型/框架/GPU/优化/生成均无额度。未来CPU数组grant与数值运行grant分别由S0按已验收代码及精确输入冻结，当前两类active grant为空。旧training_authorized=false不改写；文件自报hash不能代替可信调用方提供的预期hash。child先完成无框架绑定和租约检查，经已审loader后才导入固定trainer/optimizer。资源只登记实际采样最大值，不将其解释为瞬时峰值保证。

接续条件与文件范围见[P04-SFT-QWEN-RUNTIME-CPU](../coordination/tasks/P04_SFT_QWEN_RUNTIME_CPU.md)及ADR-0029。S0本次新增实际数据消费、编码、模型读取/API、框架、GPU、构建、安装、环境、费用与上传均0；本配置尚未实现或经独立R1验收，不构成容量或正式训练放行。
