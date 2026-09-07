# 03｜SFT / DPO 训练规格

## 1. 模型与 backend

主模型：`Qwen/Qwen3-1.7B`；冒烟/容量对照：`Qwen/Qwen3-0.6B`。模型身份见 [S06/S07](09_SOURCES.md)。两者作为本项目未微调的原始 checkpoint；不要把它们写成同名 `-Base` 模型。

首选 SFT backend 为 MLX-LM 的 LoRA/量化 LoRA 路径。DPO 候选为 `mlx-tune`，备选 `mlx-lm-lora`；它们是社区项目，不是 Apple 官方 DPO 支持。由 P01 检查源码、锁定 commit/版本、完成本机功能和数值测试后只能选定一条正式链路。[S01/S02/S08/S09]

不直接照搬 CUDA 的 bitsandbytes/NF4/paged optimizer 配置。MLX 量化 LoRA 必须记录实际量化方法、group size、dtype、可训练层；与 QLoRA 论文的所有工程细节不应画等号。[S13]

## 2. 模板与训练目标

首版统一 non-thinking 配置；用实际 tokenizer 渲染并保存样本级 token/mask 检查。Qwen 的 `enable_thinking=False` 是模板/推理行为配置，不能用删除输出标签伪装实现。[S06]

SFT 默认 completion-only loss：监督 assistant 工具调用和指定最终输出，不监督 system/user prompt 或外部工具结果。多轮样本需要明确哪些 assistant turn 参与训练，不能因 chat template 改变而错位。

预测位置采用 next-token shift；padding/被 mask token 不计入分母；EOS 处理一致。手工检查至少 10 条含工具 schema、多轮 observation、无工具判断的样本。

2026-09-07本批P02的10条真实train及3条协议材料，kris已明确委托AI审阅，按ADR-0022记录审阅者和局限，不要求本人重复填写。已有问题需在修订版重新绑定、独立复核；真实trainer/collator与材料的对应仍须实证，不能用静态材料替代训练行为。浏览器实显NOT_RUN不记为通过，且不阻塞本轮CPU内容整改。

## 3. 起始配置是待校准参数，不是性能保证

| 项目 | 初始实验值 | 调整边界 |
|---|---|---|
| 最大序列长度 | 1024 smoke，1536/2048 视真实长度分布 | 不强截完整工具 schema；更长另立实验 |
| micro batch | 1 | 内存余量且速度实测有收益再增大 |
| gradient accumulation | 8 | 记录真实 effective batch、末批行为 |
| LoRA rank | 8；rank 16 作为单独对照 | 必须列出实际适配模块 |
| target modules | 先 Q/V 或 backend 支持的明确集合 | 检查参数路径，不依赖猜测 |
| SFT learning rate | 1e-4 作为 smoke 起点 | 基于验证集、梯度与失败分析调整 |
| DPO learning rate | 5e-6 作为 smoke 起点 | 不直接用 SFT LR |
| DPO beta | 0.1 起点 | 最多追加一个预注册值，避免大量扫参 |
| epoch | 先 1 | 早停按验证集，不按测试集 |
| seed | 第一轮 42 | 正式多 seed 放在算力门允许后 |

不要把 rank/alpha 的不同 backend 定义当成完全一致；记录实际 scaling。先检验少量样本可过拟合，以定位数据格式和 loss bug，而不是一开始上万条训练。

## 4. DPO 的关键数学契约

给定相同输入 x、chosen y+、rejected y−，采用标准 sigmoid DPO：

```text
margin = [log πθ(y+|x) − log πθ(y−|x)]
       − [log πref(y+|x) − log πref(y−|x)]
loss   = −log sigmoid(beta × margin)
```

序列 log probability 为 completion 有效 token 的 logprob 之和；如使用长度归一化、label smoothing 或其他变体，必须另命名并记录，不得仍声称完全相同的标准 DPO。[S10/S11]

**reference = 冻结的已验收 SFT 模型。** 策略初始化也来自同一 SFT。底座量化 + SFT adapter 的组合属于模型身份的一部分。不能为了节省内存简单 disable adapter 后拿原始模型作 reference。

可选省内存实现：为静态训练对预计算 frozen reference 的两条 logprob。cache key 必须包含 SFT checkpoint、tokenizer/template、量化/精度、input token IDs、completion masks 与代码版本。更改任一项使 cache 失效；不在验证/测试轨迹上生成训练缓存。

## 5. 正式训练前的 G-TRAIN 测试

- policy=reference、同一输入对时初始 DPO loss 应接近 ln(2)，在浮点容差内；参考输出不能随优化步骤改变。
- 使用小型人工 logprob 数据，MLX 与独立 PyTorch CPU 实现的 loss/梯度方向一致；容差由 dtype 决定并明示。
- 修改 masked prompt token 不应被误当 completion 标签；padding 不改变 loss；长短响应处理符合已选公式。
- 更新后只有声明的 adapter 参数变化；冻结权重与 reference hash 不变。
- adapter 保存、重新加载后，同输入的 logprob/生成在容差内复现。
- SFT→DPO 跨库导入不能只有“加载不报错”；必须核对 target modules、scaling、tokenizer 和前向输出。

任何一项失败，不能开始正式 DPO，也不能用结果好看来忽略实现错误。

## 6. 运行产物

每次运行保存 config、source/data/model hashes、stdout/stderr、loss/验证曲线、有效训练 token 数、微步/优化器步、时间、内存、温度/功耗可获得信息、退出码、checkpoint manifest、恢复级别。

MLX 使用惰性求值；性能计时必须等待实际计算完成，不能只测提交计算图。CLI 吞吐的 token 口径必须与样本处理实际一致。

默认只保留 best、last 和一个回滚 checkpoint；中间大制品清理要有 manifest，不清除用于证据核验的摘要。

## 7. DPO 不通时怎么办

D2 前完成 backend 兼容性判断。若主候选失败，最多选择一次备选并记录原因；不要用十天时间自造完整训练框架。可把正式主结果降为 SFT，把经严格数值校验的 0.6B DPO 作为缩小实验；必须分清两种模型，不能写成 1.7B DPO 成功。

如仍无有效 DPO，交付 `v0.1.0-core` 和完整阻塞报告，`v0.2.0-preference` 保持未完成。负结果可以发布，但伪造或错误实现不能发布成算法结论。

## 8. PyTorch 能力的保留

小规模 Dataset/collator、CE/DPO loss、mask/梯度校验用独立 PyTorch CPU 实现，作为可读 reference；正式训练在 MLX。未来 CUDA/TRL adapter 是独立里程碑。简历应如实写“MLX 训练 + PyTorch 参考实现”，不冒充已运行多卡 PyTorch 训练。
