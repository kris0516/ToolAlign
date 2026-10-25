# P04 CUDA 数据与 mask：Q1-r1 预审

**PASS，范围为 13 例当前真实材料与指定 CUDA 消费实现的对应。** 10 条训练材料和 3 条 protocol-only 材料的完整数组均与原 Q1 批准记录一致；未发现新增训练语义问题。下一项验证是新 CUDA 入口生成固定 20 条容量数组后的增量复核。本轮不签发 GPU 运行授权。

审核日期：2026-10-26。实际 reviewer：Codex-AI（Q1），独立 AI 对话，`gpt-6-astra / max`；不代表用户本人签字。

## 精确范围与输入

- reviewed commit：`4342af87615197c7947d001f462d3d31500cd501`，T1 CUDA 首包及报告。
- authorization commit：`10a2083fd3741bd7501449d0deb6e483ce30ee7f`。
- S1 消费报告源提交：`e5f023cd1cd50b60184d44576203070726e9dddf`。原实际命令源提交为 `04415938c749ea2e8dc1ef5e8ab7e30b777aeb47`，运行共享 v3 的 prepare/rebind/export/readback；没有运行新增 CUDA prepare/encode。
- 沿用原 Q1 `7941f1f56519ea2eac437c669ac2c6445a0329f6` 的来源语义判定；不重新抽样或重审无关来源。

| 实物 | SHA256 |
|---|---|
| S1 原命令 receipt | `7d57d5a1f14389f080cc0eb49d658550be9897b5eb82e23191d5956000d26b80` |
| S1 消费 report | `5e9e4bf3ce35b37900cee821f6e681d90924df5c61163060e5b560a1c1bef980` |
| 导出 manifest | `71204d7b17593e4796ca48c5e87b69c2b33555af1c98914ad41f742d9ac064d4` |
| 13 例 review-arrays，2,030,656 bytes | `cc82ba3cc030ac990e741bd5fa0a735009f6cb2498ec0b1b30523daa1c3649d3` |
| 冻结 CUDA 配置 | `3d4785e1e130dd04990abb3767c23d92cdb7b18dad1d30cc6991f976cd44c9c4` |
| 原 Q1 adjudications | `84613324653ca8613789c10fa0948990438873376ca55611ee0714fe3aca4f5f` |
| 本轮逐例判断及数组检查 | `4f702875bbd972faa67a62bc5bbe771658e045183b2f4f012b83c8cdc17d2812` |
| 本轮原 engine 证据绑定与静读文件身份 | `9158ccf00dccad01f7b86a8500c5a8570ecd4b59e957fae121f216ef5133e05b` |

## 13 例逐项结论

私有 `review-result.json` 保存 13 条独立结论、理由、全部边界和检查结果。`effective-01` 至 `effective-10` 均 PASS；`protocol-clarify`、`protocol-final`、`protocol-refuse` 均在原协议 fixture 范围 PASS。后者没有训练 audit、没有原训练行绑定，训练选择标记为 false，不据此主张真实业务回答的适当性。

本轮实际执行 423 项标准库比较，全部通过；另将 26 条 engine 证明的文件 hash 和证明内容 hash 与 Q1 自有、身份不变的旧裁定逐条绑定，26/26 通过。检查内容为：

1. 当前 Batch 的六组完整数组逐元素等于原 padding 数组；原七组未 padding 数组、token 文本、原 Example/Action、原训练行绑定及两 engine 记录保持原身份。导出记录中的 26 个共享消费者包文件 hash 与待审提交一致。
2. 对每例记 prompt 长度为 P、completion 长度为 C，则原序列长度 N=P+C+1。监督范围为 completion 的全部 token 和唯一 EOS；prompt、历史 assistant/tool 消息及右 padding 的 loss mask 均为 0。两条恰好占满 bucket 的材料仍保留 EOS 监督。
3. causal input 等于 padded sequence 去掉末尾，target 等于去掉首位，causal mask 等于 loss mask 去掉首位；首末监督位置为 P−1 和 N−2，监督分母为 C+1。没有再次移位。
4. 反解析 prompt 中的消息包装，原消息顺序、角色、工具调用与观察关联、工具目录均一致；completion JSON 与原 Action 按类型相等，数值和字符串类型未互换。token 文本用原 Q1 已验证 hash 继承，本轮无重新编码或解码。

## CUDA 消费与报告解释

静读 [arrays.py](../../src/toolalign/training/cuda_sft/arrays.py)、[engine.py](../../src/toolalign/training/cuda_sft/engine.py)、[runtime.py](../../src/toolalign/training/cuda_sft/runtime.py)、共享 [collator](../../src/toolalign/training/sft/collator.py) 与 [validation](../../src/toolalign/training/sft/validation.py)，并与[冻结配置](../../configs/sft-cuda.v1.json)及 [T1 报告](../experiments/P04_CUDA_SFT.md)对照：

| 项目 | 对应结果 |
|---|---|
| 一次 causal shift | `engine.py:22–38` 直接使用 Batch 的 causal input/target/mask，attention 使用 `[:-1]`；不传 HF `labels`。消费前由 Batch 及 `arrays.py:236–259` 检查原 audit、EOS 与边界。PASS。 |
| 训练样本权重 | `engine.py:53–69` 计算每例 CE sum/T，再以实际组长 g 求均值，即 `(1/g) × Σ(CE_i/T_i)`。T 为 completion+EOS token 数；常规 g=8，尾组使用实际 g。PASS。 |
| 验证权重与覆盖 | `engine.py:72–85` 经 `ValidationTotals` 累计 CE 总和/监督 token 总数，并核对指定 validation 的全部 ID、顺序与数量。PASS；不是每例 loss 的算术平均。 |
| 完整 profile 的尾组 | smoke 为 1,583=197×8+7，对应 198 updates；formal 为 5,938=742×8+2，对应 743 updates。与配置及实际组长除数一致。PASS。 |
| 固定容量选择 | `arrays.py:54–66` 按长度降序、原 rank 升序取 18 train/2 validation，再按原 rank 消费；绑定固定 cohort hash。其余选择仍使用已批准 view。PASS（选择规则及草案身份）。 |
| 容量解释 | 容量训练组为 8+8+2，最多 3 updates。`runtime.py:173–179` 明确 `diagnostic_only=true`、`validation_scope=capacity_cohort`、`epoch_complete=false`；`selected_rows_complete` 只描述该 cohort。报告相符。PASS（静态解释）。 |
| 持久副本解释 | summary 的远端副本校验与 `durability_verified=false` 同时保留；报告明确外部持久化及跨实例恢复另需实际证据。PASS（解释边界）。 |

固定容量 cohort 的 canonical SHA256 为 `48d66f48010dc0d0ce6db5bc64ac5e7223aa79fe7824f7ca623e6449f4adedeb`；与 S1 草案及 T1 常量一致。此处核对选择描述和身份，没有重做全数据最长排序，也没有生成这 20 条 portable arrays。容量验证的两个样本不能支持完整 formal validation 或模型提升结论。

## 实际命令、失败与未运行项

在本轮私有目录保存脚本、输出和进程记录，实际成功命令为：

```sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python3 -B .toolalign-local/q1-p04-cuda-mask-r1/review_arrays.py
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python3 -B .toolalign-local/q1-p04-cuda-mask-r1/review_binding.py
```

两条命令均 exit 0；完整数组比较进程耗时约 0.145 秒。均为标准库 JSON/数组比较，未导入模型或 tokenizer 框架。没有重跑 T1 的 17 项 CPU 数值测试；其工程与数学独立复核由 R1 承接。

保留 Q1 辅助脚本的首轮失败：它将 protocol-only 的 `audit=null` 当作训练 audit 对象，导致 TypeError，未生成结果文件；随后读回因此报 FileNotFoundError。字段检查还暴露协议 case 没有训练行字段及一次错误文件路径。核对原字段结构后，脚本分别验证训练对象和协议空字段；原脚本、空输出、复现 stderr 和失败说明均保留。该错误未修改候选或数据，不构成候选的正式质量失败。

20 条新入口容量数组、CUDA tensor/loss 执行、真实模型加载/训练、外部持久化和跨实例恢复、正式 SFT 及模型效果均为 **NOT_RUN**。本轮 GPU、SSH、新编码、模型下载/加载/更新为 0。E1 控制代码不在本轮批准范围。新增 issue 建议为 0，旧问题与原失败身份保持；正式计数由 S1 维护。
