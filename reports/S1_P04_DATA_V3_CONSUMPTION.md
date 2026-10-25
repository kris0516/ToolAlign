# S1｜修复后真实冻结 v3 消费

2026-10-26（Asia/Shanghai）。结论：当前 CPU 接口对真实冻结 v3 的一次读取、13例数组转换/导出/回读 **PASS**。这是 CUDA 前置数据消费证据；CUDA trainer、容量和正式训练尚未运行。

源码提交 `04415938c749ea2e8dc1ef5e8ab7e30b777aeb47`，生产路径保持 PR19/PR20。使用已有默认 CPU Python 3.14.7，按顺序调用 `prepare_v3`、`rebind_review_arrays`、`export_review_arrays`、`read_review_arrays` 各一次。原输入清单 SHA256 为 `08e865ff98bd476c94153033bc192664d72cee64443184576532c0289a610dd7`；未重新构建数据或改变旧授权字段。

| View | 条数 | 已冻结身份 |
|---|---:|---|
| formal/train | 5938 | 与 sft-data-v3.v1.json 一致 |
| formal/validation | 213 | 与 sft-data-v3.v1.json 一致 |
| smoke/train | 1583 | 与 sft-data-v3.v1.json 一致 |
| smoke/validation | 194 | 与 sft-data-v3.v1.json 一致 |

13个唯一材料对应26份原始引擎记录；两个引擎的原记录一致，转换后的全部 Batch 与导出回读逐项相等。10例为真实 train 材料，3例仍仅作 protocol 诊断。新 sequence/tokenizer 调用0，模型更新0，GPU运行0。原Q1语义判断与生成来源沿原绑定保留，本次没有重做语义抽样或把协议材料加入训练。

命令 exit 0，用时76.53秒，执行期间公开源码内容未变，stderr为空。已有命令 recorder 保存实际argv、源码前后身份、时间、输出与退出码；私有原始数组和绝对来源路径不进公开仓库。

| 实物 | SHA256 |
|---|---|
| 实际命令 receipt | `7d57d5a1f14389f080cc0eb49d658550be9897b5eb82e23191d5956000d26b80` |
| 消费结果 report | `5e9e4bf3ce35b37900cee821f6e681d90924df5c61163060e5b560a1c1bef980` |
| 有限数组 manifest | `71204d7b17593e4796ca48c5e87b69c2b33555af1c98914ad41f742d9ac064d4` |
| 原始数组 export | `cc82ba3cc030ac990e741bd5fa0a735009f6cb2498ec0b1b30523daa1c3649d3` |

下一项验收是新 CUDA 数据入口、实际 tensor mask/损失和 checkpoint 路径的独立复核及 Colab 实测；此处 PASS 不代表它们已完成。
