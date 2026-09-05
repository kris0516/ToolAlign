# P01 兼容性预登记

状态：实施中；本文件记录运行前预算，不代表通过。代码基线 `ebcaf586f8e65f5306259f6b134e1c5cce30cf48`，授权 `12aeb84bcbd9937440496346bcb653b8b4684952`；契约 `toolalign.contracts.v1`。正式 P04/P05、P03 完整任务推理不在本次运行范围。

## 来源与环境

本机 CPU 审计：Apple M5 Pro，16 GPU cores，15 CPU cores，物理内存 51,539,607,552 bytes（48GiB），macOS 26.5.1 / 25F80，arm64，Python 3.14.7。Metal 的可执行性待受锁运行确认。公开的去敏字段来自 `system_profiler`、`sw_vers`、`sysctl`；机器序列号与路径不公开。

- [Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B/tree/c1899de289a04d12100db370d81485cdf75e47ca)：revision `c1899de289a04d12100db370d81485cdf75e47ca`，未 gated，Apache-2.0。下载 dry-run 约1.5GB 权重；保留原始 bfloat16，无自制社区量化。
- [Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B/tree/70d244cc86ccca08cf5af4e1e306ecf908b1ad5e)：revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`，未 gated，Apache-2.0。dry-run 约4.1GB 权重。两个模型 tokenizers/config 另计。
- 私有探索环境固定：MLX/MLX-metal 0.32.2，MLX-LM 0.31.3，mlx-tune 0.6.0，唯一备选 mlx-lm-lora 3.1.2，PyTorch 2.14.0，Transformers 5.16.1，Hugging Face Hub 1.30.0，NumPy 2.5.2，psutil 7.2.2。精确传递依赖、PyPI wheel 来源与源码 hash 留在私有证据目录；公共依赖由 S0 集中管理。
- 源码核验入口：[MLX-LM](https://github.com/ml-explore/mlx-lm)、[mlx-tune](https://github.com/ARahim3/mlx-tune/tree/9690fe1fed19c72f0810902b9c188d9a2625eb5b)、[mlx-lm-lora](https://github.com/Goekdeniz-Guelmez/mlx-lm-lora)。结论绑定已安装版本的源码 hash，不能以 README 支持声明代替本机结果。

## 运行顺序与停止条件

所有模型导入、加载、驻留位于冻结 `GPULease` 内。每次单独进程运行，外层只监控自己创建的进程；锁竞争超时不得导入模型。CPU 人工数学检查也经租约，防止候选包导入期间初始化 Metal。没有提高系统或进程 wired-memory 限额；上游设置请求由作用域内包装层记录并抑制，不调用真实 setter。

| 检查 | 预登记上限 | 统计口径 |
|---|---|---|
| 人工小张量数学 | 180 秒，MLX 2GiB / RSS 8GiB | PyTorch CPU 与 MLX CPU float32；CE/DPO loss、梯度 absolute tolerance 2e-6；ln2 2e-6 |
| 0.6B smoke | 900 秒，32 SFT 微步（accumulation 8）；最多8 DPO候选微步（accumulation 1），最多131072处理 token | 32条原创 train-only 样本；1024上限、不截断；rank8，Q/V，scale2（对应alpha16），dropout0；SFT LR1e-4，DPO LR5e-6，beta0.1，seed42 |
| 1.7B 长度校准 | 每个bucket最长900秒，目标100个可测SFT微步，8暖机；DPO另计最多8微步；最多524288处理token | 1024→1536→2048；前档通过再升级。实际不足100须登记实际计数，不能替代目标 |
| 生成 | 每bucket最多4请求、每请求32新token，30秒/request | 同步计时，prefill与decode分开；不得等同于完整任务推理 |

全作业 MLX peak 24GiB、RSS 30GiB；进程监控每1秒采样，swap 比启动时增长超过1GiB或系统压力非正常（`kern.memorystatus_vm_pressure_level != 1`）即停止。系统压力不可读时视为错误。墙钟限包括导入/加载/保存。优先在安全微步边界保存现有 adapter，异常或外层终止仅保证已落盘检查点，恢复语义 `weights_only_restart`，没有 optimizer/RNG 全状态恢复。绝不杀死未知进程。MLX 内部峰值在每个同步工作单元检查，因此不能保证一次工作单元内没有瞬时超限；RSS/压力由外层监控兜底。

T1 全部私有环境、原始模型、缓存和制品规划上限20GiB；全项目50GiB不由T1擅自修订。仅本地免费计算与公开原始模型下载，无远程推理、上传或公网服务。

原始模型 identity 包含实际文件 SHA-256；每次模型 probe 使用冻结 run.v1，详细 token IDs/masks、微步、处理/监督 token、资源采样和源码 hash 在配套私有 JSON。暖机、同步训练时间、validation/forward、checkpoint I/O 分开。SFT smoke checkpoint 仅是诊断 reference，绝不标作已验收 P04 SFT；正式 DPO 仍须独立验收的 SFT 身份。

模型数值门槛补充（运行前固定）：同 checkpoint 跨库重载全部首决策 logits 与抽样 completion logps absolute tolerance `1e-5`，greedy token IDs 必须相同；人工 CPU float32 仍为 `2e-6`。原始 BF16 模型的候选原生 DPO 路径初始 ln2 容差 `0.02`；超过则不执行原生 DPO 更新，只登记失败诊断。显式 float32 completion/reference 计算的初始 ln2 容差仍为 `2e-6`。这些门槛不表示正式 DPO 已通过。

## 首选失败后的唯一备选（第二次 smoke 前登记）

首轮0.6B原生 mlx-tune 初始 DPO loss `0.9140625` 超过 ln2±0.02，未执行更新。只切换到已指定的 mlx-lm-lora 3.1.2。使用其原生 `train_dpo`、AdamW、sigmoid loss 和独立冻结 SFT smoke reference；默认 collator 的错位 mask 由明确的 completion collator 替换（通过临时替换该模块 iterator，finally 恢复）。没有改动原生 optimizer/训练循环，不使用 QAT 或 sequence chunking。

备选预算为8微步、accumulation8、预期1次optimizer更新，LR5e-6、beta0.1；总预算仍40微步/900秒/131072训练处理token。要求相同 shape 下 policy=reference 初始 ln2±2e-6；原生 float32 score 与不补齐 reference cache 的绝对误差≤0.02（不同 BF16 kernel shape 允许的另列容差），文件/参数hash必须一致、重载 logits≤1e-5。第二次运行依然独立记录，首轮负结果保留。

1.7B 每bucket采用112个SFT微步（前8暖机、104可测，满足100目标且完整累积8），备选DPO8微步；总120微步、524288训练逻辑处理token、900秒上限。容量输入由原创上下文扩展到 bucket-64 左右，保证拒绝响应有长度余量；它不是P02真实长度分布，不能用来宣称真实任务耗时。

第三次0.6B smoke前修正：第二次备选运行的非编译初始化检查通过，但进一步核对**实际训练日志**发现，第一次optimizer更新之前loss交替为0.6945998073与0.6798114181，未满足预登记严格ln2容差。第二次运行的程序性PASS不足以验收，明确降级为 `FAIL_TRAINING_PATH_LN2`；原始JSON/日志不改写。已补充训练回调门槛，使第一个累积周期任一实际loss偏差即停止。使用MLX官方诊断开关 [`mx.disable_compile()`](https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.core.disable_compile.html) 在专属备选进程阶段禁用编译优化，保留同一backend、dtype、loss、collator、LR、beta与2e-6门槛。该修正验证计算路径，没有放宽门槛或更换第二个备选。

第四次0.6B smoke前修正：第三次在reference cache形成之后才切换编译模式，触发reference score门槛，退出2且DPO更新0。由此要求**整个模型进程**从加载、SFT、reference预计算到DPO和重载保持同一编译模式，且该模式与依赖版本进入reference cache身份。microbatch1的chosen/rejected各按自身完整长度输入，避免不必要的共同补齐；没有修改completion、截断或放宽容差。第三次失败仍保留，原始错误未捕获具体score差值，不能补写成已测数字。
