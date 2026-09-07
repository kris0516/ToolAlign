# P04 真实 Qwen 运行接口方案

**PROPOSED_NOT_AUTHORIZED。** 本方案将已验收的 CPU 序列组件和原生 toy 接口衔接到未来的 v3 数据与真实 Qwen。仅交付接口、运行边界、计数、候选预算和验证要求；本轮生产实现、数据构建、分词、框架导入、模型加载、GPU、优化和生成均为 **0**。结构化对应件为 [P04_SFT_RUNTIME_PROPOSAL.json](P04_SFT_RUNTIME_PROPOSAL.json)，它不是可执行训练配置。

代码基线 `d3e56f68ebd67cc576d912b6f06636682b4170ab`；授权 `8929cbbef0b24f9a4053adfe778bb4ef76147293`；任务 `P04-SFT-RUNTIME-PROPOSAL`，T1，分支 `codex/p04-sft-runtime-proposal-r1`。契约保持 `plan-v0.1 / coordination.v1 / toolalign.contracts.v1`，模型格式保持 `toolalign.action-json.qwen3-message-roles.v1`。PR14 的 CPU 验收与 PR11 的固定原创 toy 验收分别保留原范围；本方案不产生新的阶段验收。

固定输入 manifest 为 `eb5f25bd164c1394c0d82350a1f1d0ccc09ddb1306dac3977403b695d7f1ac02`，10 个文件、166,598 bytes；v3 政策为 `784aa699026ebb149d720745f461a9cfd493036cd0bf09a72702a81e2db45261`，长度投影为 `9052c0b40e83a494b8c259df782df1d6b934a193ec22bcf5cc77594a829dd4fa`。另只读现有 MLX 的 optimizer、Module、数组及 RNG 定义，共四份源码。出处路径只表示来源；没有读取 D1/Q1 变化中的输出、真实样本语义或权重。本轮新 v3 candidate、实际 manifest/选择/材料/运行配置/权重文件复核与 checkpoint hash 均为 **PENDING**。

**消费入口与数据边界。** 建议新增 `training.sft.data_v3.prepare_v3()`，用 S0 后续固定的 CPU 配置调用已验收 v3 的只读 verifier，再构造四个 train/validation view。D1 的实际 v3 verifier 名称和参数尚待候选交付；此处 `quality_exclusion.verify` 是接口预期，不能当成当前已有实现。旧 `data.prepare()` 仍调用 v1 verifier，且 `config.load_config()` 校验精确旧配置 hash，不能只替换一个路径绕过它。[sft_data 76–114；sft_config 10–25]

| 复用对象 | 复用前必须新增的检查 |
|---|---|
| `SelectedRow / SelectionView / view_from_records` | 当前 v3 quality/selection/training-binding 与 v1、v2 祖先链完整一致；旧 kernel 不验证质量祖先 |
| `training_selection.validate_pair` | 原 Example、ModelInput、Action、来源、split/group 与旧长度审计一致；新质量过滤不改变原序列 |
| `training_sequence / collate_sequence / collate_selected` | 新配置允许的准确编码次数、完整审阅数组、真实 trainer 输入与审计逐例绑定 |
| `epoch_plan / validate_plan` | 先验证完整单遍和 1..N rank；检查点细分另验证覆盖原 plan，不能把四段直接传给只接受原两段结构的 validator |
| `completion_loss / OrderedBatches` | 固定 microbatch 1、有限 rank、真实完成计数、作用域与资源检查；不绕开原 toy 公共入口 |
| `ValidationTotals` | 可用于 smoke/formal 的 validation 累积；真实 score 另建，旧 toy `Score / validate_score` 保持不变 |

验证顺序是先校验声明成员的原字节、大小、类型和 hash，再解析。只接收原生 JSON，拒绝重复键、非有限数、bool 冒充整数、浮点 rank/mask/IDs、符号链接和路径逃逸。逐个绑定 quality revision、政策、selection manifest、training-binding、四组 Example/sidecar/排除文件及 Q1/R1/S0 seal。训练产物中的 `training_authorized=false` 原样保留，未来模型使用权限由单独的 S0 精确运行授权绑定，不能回写旧数据文件为 true。[quality_v2 447–476、500–536]

新 `selection_rank` 必须为连续 1..N；`parent_selection_rank` 指向原 v1，`previous_selection_rank` 指向 v2。三者通过 Example ID、父 sidecar hash 和单调原顺序连接，不能都解释成上一个版本。验证原 Example JSONL 行的精确字节后，才允许 kernel 为不可变内存 view 重新编码；重新编码的 buffer 不冒充原 JSONL 字节。staging 不晋升，不改 split/group，不补选到 6,000。heldout/test/ood/BFCL 不进入内容 view、取样、调参或回答生成。[quality_filter 281–324；sft_data 47–73]

13 例材料按 Example 身份和实际编码 run/sequence 身份连接：11 例保留旧 sequence、padding、token_texts 与原时间/源码，2 例接收 D1 的新封存；3 个原创 final/clarify/refuse fixture 仍在训练集合之外。静态复用重新绑定 case、rank 和质量版本，不能宣称再次测量。CPU 适配先由已封存的 `Sequence` 数组生成 `Batch`，逐位置、逐类型核对完整 sequence/prompt/concatenated IDs、attention/loss masks、shifted inputs/targets/masks、EOS 和 token_texts。随后真实 trainer 的编码范围由 S0 单独冻结，并与旧长度审计和完整审阅数组相符；本方案没有为 T1 分配任何新编码次数。

`OfflineQwenTokenizer` 构造时拒绝已加载 MLX/Torch。因此训练用的编码/数组导出应在独立的无框架 CPU 阶段完成；GPU 子进程消费只读、已绑定的数值 Batch，不在导入模型之后调用该 CPU tokenizer 构造器。实际推理可使用固定本地 loader 返回的 tokenizer，仍须按共用投影、模板和编码参数核对同一 prompt IDs；不能因使用另一个 wrapper 而换模板。[offline_tokenizer 103–163；collator 65–83]

**模型与训练接口。** 以下默认值均为后续 S0 配置提议，尚未生效。

| 项目 | 提议值及依据 |
|---|---|
| smoke | 原始 `Qwen/Qwen3-0.6B`，revision `c1899de289a04d12100db370d81485cdf75e47ca`，总长上限 1536 |
| formal | 原始 `Qwen/Qwen3-1.7B`，revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`，总长上限 2048 |
| 底座 | 现有本地原始 BF16、无量化；实际文件 manifest 与加载后的参数身份另核，不下载或重命名为 `-Base` |
| LoRA | rank 8、直接 scale 2、dropout 0；全部 28 层的 `self_attn.q_proj/v_proj`，56 模块、预期 112 个 A/B tensor |
| dtype | 底座 BF16，原生 LoRA A/B 的默认 FP32；加载后必须核对所有实际 shape/dtype/路径 |
| optimizer | `mlx.optimizers.Adam(lr=1e-4, betas=[0.9,0.999], eps=1e-8, bias_correction=False)`；无 weight decay/scheduler |
| 数据次序 | microbatch 1、accumulation 8、seed 42、单遍；不 shuffle、packing 或截断，使用 sidecar 指定的最小完整 padding bucket |
| 编译/重算 | 保留原生 `mx.compile`，`grad_checkpoint=False`；不自动关闭编译或切换重算方案 |

P01 的同配置采用 `model.freeze()` 后 `linear_to_lora_layers()`；只有声明的 A/B 可以训练。验证零 B 时与原底座前向一致、至少一个 adapter 参数随训练变化、所有变化都在声明集合内、冻结底座字节不变。`scale=2` 是 LoRA 实际直接乘子；只有采用 alpha/r 约定时才可写 alpha 16。源代码的 Adam 默认 `bias_correction=False`，不能套用另一库的默认值。[p01_model 221–256；upstream_lora 67–98；upstream_lora_loader 38–110；mlx_optimizer 493–545；mlx_random 42；mlx_array 1967]

loader 使用现有已解析本地目录、固定 config/权重/tokenizer/generation_config 文件、`trust_remote_code=False`、严格权重匹配和 eager materialization。上游目录缺失会尝试下载，config 的 `model_file` 还会执行自定义代码；新入口必须在导入/加载前拒绝这些路径和量化/架构覆盖。传入原 revision 只是来源记录，不能替代本地字节核验。上游 `load_adapters()` 使用 `strict=False`，成功返回不足以验收重载。[upstream_loader 234–256、282–336、414–420；upstream_lora_loader 113–138]

训练仍调用公开 `trainer.train(model, optimizer, train_dataset, val_dataset=None, args, loss=completion_loss, iterate_batches=...)`。不复制上游循环，不用默认 Chat/CompletionsDataset 重新模板化。loss 只覆盖 next-token shift 后的当前完整 Action 与一个 EOS；每例先按有效 completion token 求 mean CE，再按当前累积组的真实例数平均梯度。validation 则使用总 CE / 总监督 token，不能把两种 reduction 混为同一目标。[upstream_train 86–99、176–215、248–260；toy_adapter 41–70]

Qwen 的无 cache 前向使用因果 attention。microbatch 1 的右 padding 位于所有有效监督目标之后，因此源码支持这些 pad 不应改变先前 token 的因果依赖；这仍只是推导。真实容量试跑需比较同一例的 padded/unpadded 监督 CE，并检查 prompt/padding 的 mask 为零；不能把记录了 attention_mask 误写成 Qwen 接口实际消费了该参数。[upstream_qwen 142–178；upstream_attention 45–55]

**分段、真实更新与检查点。** 下列数目来自冻结投影，实际执行全部 **NOT_RUN / 0 updates**。正式 5,938 条较原 6k 规划少 62 条，按 ADR-0025 保留这一偏差。

| profile | train / validation | 总 sequence token | train 逻辑 padding token | train 监督 token | 单遍真实更新计划 |
|---|---:|---:|---:|---:|---|
| smoke | 1583 / 194 | 1,888,995 | 2,214,400 | 141,211 | 197×8 + 尾 7 → 198 |
| formal | 5938 / 213 | 8,441,316 | 9,830,400 | 536,238 | 742×8 + 尾 2 → 743 |

smoke validation 监督分母投影为 21,226，formal 为 23,841；未来必须以实际数组重新核对。单遍逻辑 causal position 分别为 2,212,817 / 9,824,462，即每例 padding bucket 减一；这些不是 GPU kernel FLOPs 或实测吞吐。

建议三次有实用间隔的完整 post-update validation，另保留上游尾段前强制保存的临时状态。表中 rank 为当前 profile 的 v3 连续 rank；slice 为零起点半开区间。

| profile / call | rank | slice | 局部 it | 梯度分母 | 本段更新 | 实际 optimizer.step 应从→至 | 返回后保存 / 完整验证 |
|---|---|---|---|---:|---:|---|---|
| smoke / 1 | 1–528 | [0,528) | 1–528 | 8 | 66 | 0→66 | 保存，验证 |
| smoke / 2 | 529–1056 | [528,1056) | 1–528 | 8 | 66 | 66→132 | 保存，验证 |
| smoke / 3 | 1057–1576 | [1056,1576) | 1–520 | 8 | 65 | 132→197 | 保存，暂不评分 |
| smoke / 4 | 1577–1583 | [1576,1583) | 1–7 | 7 | 1 | 197→198 | 保存，验证 |
| formal / 1 | 1–2000 | [0,2000) | 1–2000 | 8 | 250 | 0→250 | 保存，验证 |
| formal / 2 | 2001–4000 | [2000,4000) | 1–2000 | 8 | 250 | 250→500 | 保存，验证 |
| formal / 3 | 4001–5936 | [4000,5936) | 1–1936 | 8 | 242 | 500→742 | 保存，暂不评分 |
| formal / 4 | 5937–5938 | [5936,5938) | 1–2 | 2 | 1 | 742→743 | 保存，验证 |

每次调用重新建立 `TrainingArgs`、有限训练 iterator、`nn.value_and_grad`/compiled `step` closure 和引用当前 state 的列表；局部 `it`、`grad_accum=None`、loss/token/report 计数及 `train_time` 从头开始。上游局部函数重建不能写成编译免费或缓存必定复用；记录各次调用及新 bucket 首次使用的实际耗时。每段长度恰为该段 divisor 的整数倍，进入下一段时无未应用梯度。seed 只在该 run 的 LoRA 初始化前设置一次，不随分段、验证或 checkpoint 重设。[upstream_train 237–281、325–368]

model、optimizer 和全局 RNG 的对象及连续状态留在同一个持租约进程。optimizer 更新可以替换 tensor 对象，不要求每个数组 Python ID 不变；需核对实际名字、shape、dtype、参数/optimizer/RNG 内容 hash，以及 `optimizer.step` 的连续值。首个更新懒初始化 Adam m/v 是正常过程。每个完成更新的对应关系为 `step_before + floor(local_it/divisor)`，再与同步读取的实际 step 对比，不能将局部 it 或 checkpoint 文件名当全局更新数。[mlx_optimizer 15–29、85–133]

每次 validation 都新建自己的有限 iterator 与 `ValidationTotals`，不复用已经耗尽的训练 iterator。`evaluate()` 会调用 `model.eval()` 并保留 eval 状态；外层记录原模式，在 finally 恢复，下一次 train 及首个实际 batch 再确认 train 模式。验证前后模型参数、optimizer 状态/step、RNG 内容和 checkpoint 文件必须不变。对象身份检查本身不能证明这些内容没有被替换。[upstream_train 176–215、264、299；mlx_module 585–611]

数据 iterator 在 yield 前登记的 rank 只证明尝试供给。新 wrapper 应在上游同步完成后、iterator 恢复或 report callback 中登记完成，再在正常返回时补核最后一个 batch：`zip(range(...), iterator)` 结束时不保证恢复末次 yield。覆盖证据应同时含 planned、yielded、synchronized-completed、更新应用到的 rank；失败时不能由 visited 列表推定最后一步完成，不可观察的计数写 unknown。资源检查异常若发生在更新之后，必须保留已经执行的 step，不能回填 0。

每段传 `val_dataset=None`；`steps_per_eval/save=本段微步+1` 避免周期保存，`steps_per_report=divisor`。原生 train 返回仍保存一次 adapter，所以总计四份原生保存、三次完整评分。上游末次内置 validation 发生在当前训练微步之前，即使 iteration 被标为末尾，也不是最终状态的分数；这里一律在返回、同步和保存核验之后评分。[upstream_train 286–323、370–387]

新 `qwen_checkpoint.RealScore` 独立于 toy Score。每份评分绑定 run/scope/profile、原模型文件与参数、adapter metadata/参数/文件、S0 config、quality/selection/validation、tokenizer/format、实际 optimizer 状态/step、累计完成微步和有序 rank、实际 CE numerator/token denominator。基线 step 0 用单独的 BaselineEvidence，不能混入正 step 的 SFT 候选。真实 scope 为 `REAL_CAPACITY_0_6B / REAL_SFT_SMOKE / REAL_SFT_FORMAL`，它们也不能混选。[toy_score 52–94]

保存后从实际 safetensors 读取 A/B，要求 keys、shape、dtype、原字节与当前 trainable 参数一致；逐叶用原 dtype 的 uint8 view 计算内容 hash，避免将 BF16 转 FP32 后冒充原参数字节，也避免一次把全部大权重复制到宿主内存。validation 覆盖完整固定集合且顺序不漏不重，独立累计总 CE/总监督 token，与原生返回作预先固定的数值容差对照；建议绝对误差 ≤ `1e-5 × max(1, abs(CE))`，待 S0 冻结。任何不完整、非有限或旧状态评分均拒绝。

相同实验身份下，按 `(validation_ce, optimizer_step, checkpoint_file_sha256)` 选择：loss 最小，同值取更早更新，再按文件 hash 排序。仅保留 best、last 和最近的不同 scored rollback，最多三份；尾段前未评分文件和未保留候选在保存 hash/处置凭证后清理自有副本，实际保存峰值四份另加写入中的临时文件。score 与摘要证据保留，不删除旧历史证据。

选中后释放原 model/optimizer，再从同一原始底座加载并严格装配相同 LoRA，核对 bitwise adapter/冻结底座身份；重跑完整 validation 和预冻结 greedy prompt。建议同精度重载 CE 绝对差 ≤ 1e-5、固定 greedy token IDs 完全一致。重载进程不伪造 optimizer；原 checkpoint 的 step 是来源字段，不是新 optimizer 已执行的更新。当前只提议 `weights_only_restart`，不声称具备 optimizer/RNG 全状态恢复。每 profile 的预算需包含 raw baseline validation 1 次、训练评分 3 次、重载 1 次，共 5 次完整 validation，另计诊断前向/生成；没有将 toy 容差或分数作为真实 Qwen 结果。

**先做一个有限的 0.6B 容量候选。** 该候选当前 **NOT_RUN**，需新实施验收和 S0 单独授权。仅使用已验收 v3 smoke 中 15 个唯一 train 和 8 个唯一 validation：train 强制包含 1536 bucket 中总长最大、C 最长、C 最短的例，按 selection_rank 打破并列，去重后按原 rank 补至 15，再排序；validation 取总长最大、C 最长并按 rank 补至 8。具体 ID/数组/config hash 均 PENDING，由 S0 在看任何新模型输出前冻结。若无法取得要求的 1536 bucket，不用合成填充冒充实际容量。

| 候选项目 | 明确上限/计量 |
|---|---|
| 首轮容量 | 15 例一次，8+7 微步，divisor 8/7，2 次更新 |
| 微型过拟合 | 固定容量子集的前 8 例重复 8 遍，64 微步、8 更新；分别记唯一例与重复次数 |
| 累计 | 79 微步、10 更新；此诊断为独立 scope，不计入后续正式 smoke 的唯一例或单遍更新 |
| 前向诊断 | teacher-forced 例次最多 64，包含 step2/10 的 8 例过拟合 CE、8 例 validation、重载、零 adapter 与 padding 对照 |
| 逻辑 token | 训练上界 121,344；训练加上述前向上界 219,648，预设总上限 262,144；生成 0 请求 |
| 编码 | 23 个唯一例、一个现有 CPU engine，各至多一次；须另获 S0 精确 CPU 编码授权 |
| 启动/加载 | 最多 1 个自有 GPU child、0 自动重试；同进程顺序加载底座和重载共至多 2 次，同一时刻只驻留一个模型 |
| 时间 | 900 秒，包含导入、加载、编译、前后参数 hash、validation、I/O、重载及收尾 |
| 内存 | MLX peak ≤24GiB、RSS ≤30GiB；swap 增长 ≤1GiB，系统 pressure=1；指标分开，不相加 |
| 制品 | 新增 ≤512MiB、完整 adapter 文件最多 4 份；不复制大底座 |

capacity_rank 1..15 是局部索引，必须同时保存原 smoke rank 与 Example ID。重复的 8 例写明 pass 号；不能将这段过拟合调用塞进 formal 的一次性 rank 验证。过拟合比较 step2 与 step10 的同 8 例 CE，建议预先固定 `CE10 ≤ 0.90×CE2` 或 `CE10 ≤ 0.1`；否则保留失败，不追加步数或改变阈值。零 B 前向、只有声明 adapter 改变、冻结底座、8+7 更新、真实 1536 padding/未截断、保存重载都须有各自证据。padding/unpadding 的真实 BF16 CE 建议绝对容差 0.02，重载参数要求原字节一致；这些是待 S0 冻结的诊断阈值，不是已观测误差。

P01 的 0.6B 原测试上限 1024、1.7B 原长度校准和 compile_disabled 结果保持其历史身份，均不证明新格式/原生编译的 0.6B 1536 容量。formal 的新墙钟/启动/制品预算仍 PENDING，需另有 1.7B 2048 原生路径证据后由 S0 冻结；不能将旧线性估计或 0.6B 新测量当作它的上限。若 S0 要安排该有限 1.7B 前置测量，需独立范围、准确样本和更新数；不能在正式一遍前隐含加入额外训练暖机。

所有模型导入/驻留必须由真实 child 持有同一 Git common directory 的 `gpu0` 租约。复用已审 `preserve_wired_limit`，只在独占进程作用域记录并抑制 train/generate 的上游 setter 请求，finally 恢复 API；不调用实际 setter 或提高系统/进程 wired-memory 限额。train/evaluate/compile 代码保持原样，iterator/loss/callback 通过公开参数注入。[gpu_lease 25–41；wired_guard 253–269；upstream_train 228–229]

原生 `train` 在 Metal 可用时，**每次调用都会执行** `mx.set_wired_limit(mx.device_info()["max_recommended_working_set_size"])`；原样调用会触及进程 wired 设置，与“本运行不提高限制”不能直接画等号。固定 MLX 文本接口说明默认进程 wired limit 为 0，`device_info` 可报告系统推荐/限制及物理内存；推荐值不等于观测到的当前进程设置。本方案只提议沿用已审抑制层。它返回的 0 是供上游控制流使用的合成返回值，绝不能记为实测旧上限。生成的 `wired_limit` 正常结束还会用这个返回值请求恢复 0，该请求也必须被同一 guard 抑制。[upstream_train 228–229；upstream_generate 229–266；mlx_array 877–904；wired_guard 253–269]

后续进入原生调用前，需要确认固定源码/版本、Metal GPU、可读且类型正确的 `0 < max_recommended_working_set_size < memory_size`、独占 child 和抑制函数的 API 身份；逐次保留请求事件。正常 train 每段应有一次推荐值请求，完整结束的 stream_generate 应有推荐值及合成恢复值 0 两次请求。guard 缺失/被替换、元数据缺键/不可读、意外 setter 请求或任何实际 setter 调用都应拒绝/终止并记录，不能为读取“旧值”调用真实 setter。本轮没有执行 device_info，也没有观测当前进程 wired 状态；这些文本接口未提供本方案已确认的只读进程 getter，旧 toy 事件与文档默认值不能代替新运行证据。运行时抑制、异常恢复和内存影响仍 **NOT_RUN**。

新 supervisor 不能直接放宽 `native_toy` 的 300 秒/4GiB 守卫，也不能跳过 P01 Budget 的 120 微步上限来运行 formal。建议新 `qwen_run.py` 对 S0 固定 scope/参数/预算做有限验证，沿用已有自有进程监督模式：预登记和启动额度先落盘，parent 无框架，child 在租约内加载；每次同步微步/更新及验证/保存前后检查 MLX，parent 至少每秒检查 wall/RSS/swap/pressure/制品。采样不保证一个算子内无瞬时超限，实际峰值必须保留。不可读指标视为失败，不写成零。异常或预算耗尽只记录已验证完成的状态，终止并回收确切自有进程，复核锁释放；不杀未知 PID。监控、保存、收尾诊断失败也必须有终态，不能覆盖原异常或写 PASS。[toy_supervisor 519–638；p01_budget 133–180]

**原始模型/SFT 与 P03。** 每种模型容量内部比较 raw 与其 SFT：相同原始 revision、dtype、tokenizer/模板、消息投影、prompt IDs 和生成限制；差别仅为已验收 adapter。raw baseline 在任何本 run 更新前记录；fresh SFT run 从原始底座/新 optimizer 开始，不能继承容量/过拟合 adapter。

生成使用固定 non-thinking、greedy argmax、seed42、temperature0/top_p1、最多 256 个新 token（含终止 EOS）、30 秒请求截止；禁用跨请求 cache、draft model、KV 量化和额外 stop 字符串。将整数 prompt IDs 直接传入 `stream_generate`，避免字符串路径自动加入 BOS。实际完整 EOS 列表须从 S0 固定的 tokenizer/model generation config 字节解析、冻结并在 raw/SFT 两侧核对；训练 EOS 151645 必须包含其中，完整生成 stop 列表当前 **PENDING**，不猜测另一个结束 token。[upstream_generate 657–753]

收集真实生成 ID 与 `generation_tokens`，EOS 也计预算；仅移除真正的终止 EOS ID，再用固定 `skip_special_tokens=False`、禁空白清理的 decoder 解码其余完整 IDs。保留普通 special-token 文字、空白和失败；不补 kind/字段、不删 think 标签、不 unwrap 或修复 JSON。native stream 的 terminal response 也含最后 token；长度上限时最后普通 token 必须计入原文，不能多计或漏计。EOS、length、deadline、error/cancel 分别落入契约 finish_reason，长度耗尽不把碰巧可解析的前缀写成 stop。[upstream_generate 714–753；p03_harness 363–376]

建议单独新增 `inference.qwen_backend.QwenBackend.generate(ModelInput, GenerationConfig) -> ModelOutput`。传入现有 P03 spawn 的对象只携带不可变配置，不能把已加载的 MLX 模型 pickle 给 child；在 `generate` 首次调用的 child 内核对来源、持租约并加载，模型驻留期间始终持锁。P03 当前将加载计入任务截止时间；真实 cold-load 如果超出 30 秒，保留失败，再由 S0 明确新增生命周期/协议范围，不暗中增加免计时暖机或截止时间。[p03_interface 157–158；p03_process 56–107；p03_harness 91–115、299–315]

模型只收到 ModelInput，expected_action/oracle 留在 evaluator。P03 继续解析原始文本，再执行 registry 验证的本地工具、最多 3 次模型决策/2 工具轮。ToolACE 的目标名称不自动具有本地注册实现：v3 的单决策语法诊断与可实际执行的 harness 任务分别冻结，不能重命名工具或伪造远端结果来凑执行成功。

一个有限诊断提议是每种模型容量各固定 8 train+8 validation 的单决策输入，raw/selected-SFT 两状态共 32 次；另固定 2 train+2 validation、工具和 oracle 已登记的完整本地任务，两状态最多 24 次模型决策，总上限 56 决策/14,336 新 token。具体 ID/工具/oracle 绑定与总墙钟/启动额度仍 PENDING。不存在合格的可执行任务时如实交付单决策范围，不能把它写成 harness 完成。所有候选在看输出前冻结；只按上述完整 validation CE 选 checkpoint，不用这些诊断输出挑参数/例子。最终 test、ood_test、BFCL evaluation 不用于本方案的取样、调参、checkpoint 选择或回答生成。

P05 交接至少需要 S0 已验收 SFT 的实际 run/checkpoint/配置/数据选择/validation/Q1/R1 身份、原始底座和 adapter 原字节与缩放/模块/dtype、tokenizer/template/format/量化身份、仅 train 的 preference 与 Q1 判断、reference cache 的输入 IDs/masks/代码/精度身份。reference 和初始 policy 都是同一已验收 SFT 组合；disable 全部 adapter 一般返回原底座。跨库加载成功不能代替 target/scaling/前向和 reference 冻结数值验证。原首选 DPO FAIL 保留，本轮 DPO=0。

**后续可拆分的最小工作包。** 全部为 PROPOSED_NOT_AUTHORIZED；文件名、配置 hash、实际新增编码和模型额度由 S0 下一包最终冻结。

| 顺序 | 新增文件/API | 依赖与最低必要反例 |
|---|---|---|
| 1. v3 CPU 接收 | `training/sft/data_v3.py`：`prepare_v3 / rebind_review_arrays / export_selected_batches`；对应 `tests/training/test_sft_data_v3.py` | 已验收 v3 和 Q1/R1/S0 seal、精确 CPU 配置。错误 revision/原字节/父 rank、bool/float 替换、staging/final split、错 Example 复用、13 完整数组、越额编码/框架导入拒绝 |
| 2. 有限真实接口 | `training/sft/qwen_training.py / qwen_checkpoint.py / qwen_run.py` 与 `tests/training/test_sft_qwen_runtime.py` | CPU 接收已验收。细分覆盖/局部全局步数、状态重置、丢尾、旧 checkpoint/错 dtype/参数/分母/重复 validation、toy/real 混分、CPU 自有子进程异常终态 |
| 3. 0.6B 容量 | 精确候选配置与本机运行证据；公开报告路径由 S0 冻结 | 前两包独立验收、S0 固定 23 例/编码、1 启动/900 秒等明确额度；真实 1536/compile/8+7/过拟合/重载全部另测 |
| 4. smoke 后 formal | 另增 `inference/qwen_backend.py` 与 `tests/evaluation/test_qwen_backend_boundary.py`，E1/P03 按 S0 范围协作 | G-DATA/容量/配置/预算门槛分别满足；P03 spawn/锁/冷启动/取消、EOS 与第256 token 边界；原始 baseline、三次真实状态 validation 与重载 |

新 CPU/capacity/smoke/formal 配置各自独立，由 S0 所有。metadata prepare 不授权编码，CPU/编码不授权模型容量，容量不授权完整 smoke，smoke 不授权 formal 或 P05/P06/P07。旧代码、默认 CLI/import、契约、依赖/构建配置、toy 守卫和历史报告均保持；如下一实现需要公共改动，先交 S0 固定范围。本轮无需 pytest/build/install 或新训练测试，只检查方案一致性、来源/行号/hash、算术、所有权、公开内容和 diff。

源码索引见下表；完整 SHA-256、准确行区间及各区间 UTF-8 hash 均在结构化对应件的 `source_evidence`。repo 项均逐字绑定上述 d3 基线；upstream 项来自冻结副本，MLX 项为本轮追加只读源码。行号表示所引用的源码事实，不是本轮框架执行证明。

| 来源键 | 路径 | 行区间 | SHA-256 |
|---|---|---|---|
| `collator` | `src/toolalign/training/sft/collator.py` | 28–62, 65–83 | `2bee5bcba478134265f19e3c297d4f59b7e6a0edf6545af70c203a57a8ca72f7` |
| `epoch_plan` | `src/toolalign/training/sft/plan.py` | 10–57 | `d10602b687eef366ef246fd697b4164f5b5af76d9c5dbd3a85d5f34c2326bbd6` |
| `format` | `src/toolalign/model_io/format.py` | 55–85, 112–165 | `84b522170d5c5e11b444842f7123d8656778c9d6aa5a274290089aee11a11d31` |
| `gpu_lease` | `src/toolalign/runtime/gpu_lock.py` | 25–41, 61–127 | `22569ddd0b2bce636f778ca103a3cc71197f6b2a9b3bcf517eec44565f9a4b79` |
| `mlx_array` | `mlx/core/__init__.pyi` | 75–89, 813–905, 1967–1978 | `9ab12f532bfbcb37f5530c1957e0f748180f8d905678984c35d9b1dac1c0c115` |
| `mlx_module` | `mlx/nn/layers/base.py` | 62–69, 585–611 | `ec749e1d50fd1a5e57e0aedc8e6eb13fc697e630f59333a0e24aee62a8dc7f0f` |
| `mlx_optimizer` | `mlx/optimizers/optimizers.py` | 10–29, 85–133, 493–545 | `57501691b4cf5e16cc4edd738f2dd358305e6c54bcd4bb93c7d10144d09e2c3a` |
| `mlx_random` | `mlx/core/random.pyi` | 11–17, 42–54 | `cc48e32ebb1a266e7af981c83e400cf880c3f7d0ed4a3296ab7d08c722d724b0` |
| `offline_tokenizer` | `src/toolalign/model_io/offline.py` | 21–39, 103–163, 177–221 | `f1354c349708c09e82661fbde3d7b9b96df16a5f9634b28097b66973bbe4ddf3` |
| `p01_budget` | `src/toolalign/training/compatibility/core.py` | 133–180 | `5a019dc973e9ff64801acfb060079d0e0a464ce182ce3c31f711d1fcc54e0671` |
| `p01_history` | `reports/hardware/P01_RESULTS.json` | 1–5 | `d0fb9deb067b1e3f6f8b85855a0d1509b3bc15569065bbfed22a5c95928f42bd` |
| `p01_model` | `src/toolalign/training/compatibility/model_probe.py` | 109–115, 160–165, 221–256, 299–330 | `abbb7b40e6f82837f548570906ba509774de20498d50570ffd613cb58b7ddbca` |
| `p01_preregistration` | `reports/hardware/P01_PREREGISTRATION.md` | 9–25 | `a6638a2b04ffc5d20a0ffa06e04bc7850e1b597b5e0ca34db158b9cc0bc36977` |
| `p03_harness` | `src/toolalign/evaluation/harness.py` | 91–115, 299–315, 363–397 | `b4aff77d4adffea786d742d5c5aeeee72f99feaf3783ee0f01ad504aa84bb987` |
| `p03_interface` | `src/toolalign/contracts/interfaces.py` | 39–68, 157–174 | `f57963758c61aab8dee29a3d9517160ed726ed5b985391b7424467003393cd55` |
| `p03_process` | `src/toolalign/tools/isolation.py` | 56–138 | `84a96791205488bad6bd3fe43a42f33f7abcbfb5fc8bb0b64f27aa13e5667f6f` |
| `protocol` | `configs/protocol.v1.json` | 1–19 | `e1c38ac24c1faff3f631ca27b7dc9e8ab80ea951cd07f00c8d91b9fc61ebaa15` |
| `quality_filter` | `src/toolalign/data/quality_revision.py` | 281–324 | `cb6dce2a974de6ea1a64fc5ad4970488536fe124302a43ea673cc8b59dd5458c` |
| `quality_v2` | `src/toolalign/data/quality_adjudication.py` | 27–37, 356–477, 500–536 | `3c7edbc6994b544c2c91cb3652e98f3a9dd6e3393fd2b13176cb629409697405` |
| `selection_v1` | `src/toolalign/data/training_selection.py` | 53–124, 305–320 | `ad3f9c86f125dd8f7c87345fd4f38a1847db986e9157873beea2adafd219b3cd` |
| `sequence` | `src/toolalign/model_io/sequence.py` | 13–71, 74–122, 126–158 | `b2e5e1f26e7236cfc80f131ac2d2ef48bd59cbe06b30e30872bb4021e0670e63` |
| `sft_config` | `src/toolalign/training/sft/config.py` | 10–25 | `aede5020b8dce0a71b5d242251878c928c558a796775cfa4e37076a7ecd5fe98` |
| `sft_data` | `src/toolalign/training/sft/data.py` | 16–73, 76–114 | `4d5e475f27f9699349a4e6fdf46f3187c05001fc0a97c47b4457e809844e45e9` |
| `toy_adapter` | `src/toolalign/training/sft/mlx_adapter.py` | 23–38, 41–80, 84–152, 163–208 | `72010be489316cceaa20e1e35bc223f8f135d3de16d6ab53ddb08fe0e18682ed` |
| `toy_score` | `src/toolalign/training/sft/validation.py` | 14–49, 52–94 | `b80af4ed4bd39a21a34cf0e114ce506a70c9ae7b7fb62e9175d83871f97167f5` |
| `toy_supervisor` | `src/toolalign/training/sft/native_toy.py` | 124–142, 184–218, 340–419, 519–638 | `f4ce51fecad6bc914f806a9cd53c631166651212503ae5e376a32eb01a0aaedd` |
| `upstream_attention` | `upstream/mlx_lm/models/base.py` | 45–55 | `61330e1c065739cd712bfeb09d673f33797cde7e613e95bf6d9ebbee9006f373` |
| `upstream_datasets` | `upstream/mlx_lm/tuner/datasets.py` | 11–132, 309–325 | `fa112840e6ea98a4ff18428792fe2ab023999c2da51ea64b3ebdf8657a152f17` |
| `upstream_generate` | `upstream/mlx_lm/generate.py` | 229–266, 307–329, 386–421, 657–753 | `270778ad53eaca55a8533d82e6752660fe5d2605c4aa0879b48a50a91f69345f` |
| `upstream_loader` | `upstream/mlx_lm/utils.py` | 234–256, 282–336, 414–420, 453–502 | `ba0371e9c88d52b34d71271945c2394005fbcb2bfb2ee9f6f82d627a33b72422` |
| `upstream_lora` | `upstream/mlx_lm/tuner/lora.py` | 11–32, 67–98 | `4d3a8edab111d4ddba33398ba8700203db7b61621c39e9c348fdd50e57278b45` |
| `upstream_lora_loader` | `upstream/mlx_lm/tuner/utils.py` | 38–138 | `166eaf5e5f923113bed43614a5fb7319795fa0cac5a7fa319ea54e5f0045b553` |
| `upstream_qwen` | `upstream/mlx_lm/models/qwen3.py` | 32–89, 129–188, 221–223 | `2284df96ecb669109b281df4534470b18f285aa9a5e41735ad682f601f93c639` |
| `upstream_train` | `upstream/mlx_lm/tuner/trainer.py` | 86–99, 102–173, 176–215, 218–281, 286–330, 332–387 | `ee33ebdbd20a184108541cb490d08085485e71a82ffd6d68d7d216029ecd28fe` |
| `wired_guard` | `src/toolalign/training/compatibility/execution.py` | 253–269 | `22635be51783928ed732760168351a57e51846ed5f97cade687efb8b97c8bae1` |
