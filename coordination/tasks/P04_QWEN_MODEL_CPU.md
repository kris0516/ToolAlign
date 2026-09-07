# P04-QWEN-MODEL-CPU｜固定本地 Qwen 加载与参数身份

状态：READY_FOR_REVIEW_CPU；E1完整 `01eeb74d1bce3c3a3c41d84575d4d706e246e818` 已普通推送/原生空闲，S0核验26,330路径/34原命令，见[完整接收](../../reports/S0_P04_QWEN_CPU_HANDOFF.md)。原派发状态：IN_PROGRESS，E1；已于2026-09-07 18:21:42 UTC按完整授权 `427e5e8fb49a4719afd5e09b53c2d012c52e7e80` 原生派发并核验新轮ACTIVE。实际新branch/617基线/14授权/42输入已由S0核验，4,266路径证明 `4b1ef1f20cb8b6d09f18b7c366ae84a7530bb5aff758d1f75e73a712cad27cf5`。此 CPU 实现与 T1 的 v3 数据/数组衔接并行，互不依赖变化中的代码；两个包各自通过 R1、最终 CI/main 后，才可供 T1 的真实运行接口复用。采用独立 E1 App 任务，gpt-6-astra/max，禁止 sub-agent。

code_base `a2b595c39d84f4e3ba32ee5893f3fff8c9202f4d`；authorization_commit 由 S0 实际原生消息提供完整 SHA。固定输入 manifest 为 `41aadaa79eac7467c7ef2b7c39a0524ec894d1b0e9c616d7a6ab303d05e33cc5`，旧 E1 保全证明 `61caaa835a609cc598f8480b0741eb1e115f80c54f077c2876df3970b9378144`。新分支 `codex/p04-qwen-model-cpu-r1`，新私有 scope `p04-qwen-model-cpu-r1`。遵循 plan-v0.1、coordination.v1、toolalign.contracts.v1 和 ADR-0027。切换前保存完整授权副本及旧审计/类型修订 seal、所有旧 FAIL/PASS、分支和根 identity；新身份只写新 scope。

目标是提供数据无关的固定模型文件验证、延迟加载和 LoRA 参数身份接口，供后续训练与推理共同使用。本包只运行 CPU 测试和只读文件验证；模型加载/框架导入/参数装配/adapter 重载的实际运行均为 NOT_RUN。不能执行这些真实路径来补 CPU 测试结论。

允许新增 `src/toolalign/model_io/qwen_model.py`、`tests/model_io/test_qwen_model.py`（必要时同名原创小 fixture 目录）、`reports/experiments/P04_QWEN_MODEL_CPU.md/.json` 和 `coordination/handoffs/P04-qwen-model-cpu-r1.md`。唯一配置例外：从 S0 完整授权逐字复制 `configs/qwen-models.v1.json`，SHA `b8a5e48bc2b93064c511ba796dabf55024f65df97fe0db39c43366b7bc877145`，至自己相同公开路径并提交。不得改变旧 model_io、CLI、SFT/toy/compatibility、P03、契约、依赖、锁/构建或协调文件。需要公共改动时向 S0 提交具体理由，不能自行扩展。

实现要求：

1. 固定模型只有 `Qwen/Qwen3-0.6B@c1899de289a04d12100db370d81485cdf75e47ca` 和 `Qwen/Qwen3-1.7B@70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`。S0 精确 JSON 绑定本地 9/11 文件的大小/hash、config/tokenizer/generation 元数据、622 份序列化 tensor 的形状/原 dtype/原字节 hash、LoRA 预期形状和固定库版本/源码。私有路径由 manifest 提供；新模块使用显式本地根，不下载、调用 Hub、设置全局环境或改模型文件。
2. CPU 验证先校验 S0 配置原字节，再处理模型目录和全部声明文件。拒绝重复 JSON 键、NaN/Infinity、bool/float 冒充整数、symlink/路径逃逸、缺失/额外 `model*.safetensors`、重复 tensor、错 shard/index/offset/shape/dtype/hash、config 覆盖、量化、自定义 `model_file`/`auto_map` 与替代架构。固定完整文件 hash 已覆盖 payload，不必为每次 CPU 检查重复逐 tensor 读取全部值。header 是 JSON 元数据，不能调用 safetensors/MLX/Torch 的 tensor 反序列化来做本包验证。
3. 原文件各有 311 个 BF16 tensor；固定 Qwen `sanitize` 在 `tie_word_embeddings=true` 时只移除 `lm_head.weight`。两模型该原 tensor 的字节与 `model.embed_tokens.weight` 相同，S0已只读核对。运行预期为 310 个底座参数叶、596,049,920 / 1,720,574,976 个元素；必须从实际加载对象验证，不能把序列化 311 误当运行叶数。固定 manifest 已给出装配 LoRA 后 56 个 `.weight → .linear.weight` 名称映射，其他底座名保持。
4. 延迟加载接口的签名由 E1 在此范围内决定。默认 import 和 CPU 文件验证绝不加载框架。只有调用方提供当前真实、属于同一 Git common directory 的 `gpu0` 租约，且文件/库版本/关键源码/来源验证通过后，才允许实现中的真实 loader 路径导入 MLX。使用原始 BF16、无量化、固定本地 `load_model(..., lazy=False, strict=True)`，禁止自定义模型/架构参数、远端路径回退或 shadow import。该路径本轮仅审代码与明确标记的原创模拟测试；实际调用须由后续 S0 新任务授权。
5. 模型驻留全程由调用方持有原租约，加载器不释放或替换调用方的锁；返回结构绑定准确模型/revision/文件、实际 module origin、参数键/shape/dtype/内容与状态。后续 parent/child 监督和资源预算属于 T1 运行接口，本模块不新增后台进程、独立 GPU 锁、训练循环或自动重试。
6. 固定 LoRA 为全 28 层 `self_attn.q_proj/v_proj`，rank 8、直接 scale 2、dropout 0。先 freeze 底座，再通过既有 `linear_to_lora_layers` 装配，核对全部 56 模块、112 个 A/B 与 310 个冻结叶；预期 A/B 为 FP32，元素数分别 1,146,880 / 1,605,632。底座严格保持原 BF16 内容，只声明的 A/B 可训练；不把 scale 2 擅自解释成 alpha 2。提供后续运行所需的有限检查/内容身份函数，不写 optimizer、loss、数据编码或 forward/generate 诊断。
7. 参数内容 hash 必须读取实际 dtype 的原字节，按固定名称/shape/dtype 和明确序列化方式绑定。禁止把 BF16 转 FP32 后声称原字节不变；单次宿主复制可按叶或块有界处理，不同时复制整个模型。原始 safetensors 字节与 MLX 参数名称经上述固定 sanitize/LoRA 映射对照；静态 header 推导与真实参数验证分开登记。
8. 如提供 adapter 重载，限已有同配置 LoRA 结构：先验证预期文件 SHA、准确 112 keys、FP32 shape 和完整内容，再仅更新声明 A/B，复核实际参数与文件一致、310 冻结叶完全不变。不能只凭上游 `strict=False` 返回成功验收，不能接受任意 adapter config、融合权重或改 scale/targets。checkpoint 评分/选择/写入由后续训练包负责，本包不制造真实 checkpoint。
9. 只提供模型与参数身份，不创建 tokenizer 或编码/解码接口。实际 model generation config 中 EOS 为 `[151645,151643]`、训练 EOS 为 151645、pad 为 151643；保留原 sampling 默认值作为原文件事实，后续 greedy 配置单独覆盖并审查。旧 `OfflineQwenTokenizer` 与共用格式不变。

CPU 验证以原创小 fixture 和模拟对象为主：错误目录/hash/header/index/重复/类型/offset、额外模型、任意配置与 shadow import、无效或非本机物理租约、导入顺序、sanitize/LoRA 名称、缺失/额外/错 shape/dtype 的 A/B、底座被修改、BF16 内容编码、错误 adapter 和异常状态。用少量真实自有 CPU 进程验证物理锁来源/竞争只在必要时运行；不写新全局锁实现。不通过放宽生产常量让真实模型替身被当作已验证模型。模拟调用/对象全部明确标记，不能计作 MLX/真实 Qwen 测量。

现有默认 CPU 环境；源与安装版各限一轮两模型真实文件验证（原字节/hash/header、0 tensor 解码），其余为原创小 fixture。真实 MLX/Torch/tokenizer、模型/LoRA 装配、forward/优化/生成、GPU、数据 view/build、浏览器、下载/新环境和业务 API 均 0。新增私有制品 ≤1 GiB，不复制大权重；固定输入只读，出处/proof 内其他路径不扩大读权限。保留所有原失败与封存。

完成适用 CPU/新增反例、ruff、契约/公开扫描、实际 sdist/wheel/从 sdist 重建 wheel 与新默认 target 安装；非源码 cwd 验证纯导入、拒绝路径和固定文件验证来自新 target。完整原 argv/UTC/exit/stdout/stderr、精确源码时点、三归档/安装源、全部失败和最终 seal 交付。无关历史 HF/数据/原生 toy 数值不追加重跑，不把重复用例累加为独立测试数。

完整候选普通推送、原生向 S0 交接后结束。S0 核验 candidate/原生终态，再按精确新任务派独立 R1；E1 不给自己的加载路径签运行通过，不修改 main。普通回报省略 model/thinking。CPU 技术 PASS 不授权模型运行，也不替代随后真实加载、零 LoRA 对照、容量、参数变化/保存重载和正式实验的证据。

首次 intake：保存完整授权中的 AGENTS、GOAL、PROTOCOL、REVIEW_POLICY、REVIEW_FAILURES、RESOURCE_LOCK、DECISIONS、本任务、configs/qwen-models.v1.json、S0 本次准备报告、原 runtime 方案.md/.json、S0 方案接收报告、S0 P02 审计主干报告，共14份。私有输入42成员（13精确副本/29只读引用），副本748,369 bytes；复制原 manifest 与13副本，其余按清单只读。原E1 da22baf的498公开Git/快照、1,209旧scope文件、原2,943接收路径、39链接文本和旧refs/根identity保持。冻结总证明 `9157b518ed35bd13caf693b0457d8157113c55c1e266b68eb8240148618c76ff`。[准备报告](../../reports/S0_P04_QWEN_MODEL_CPU_PREPARATION.md)。新branch/base、真实原生身份、授权/输入和保全结果由S0核验后继续原轮实现。

元数据文件的 `is_run_authorization=false` 说明该文件不是运行许可；它的预期参数和源码身份供未来已授权调用方校验，不是要求永久禁用将来真实 loader。E1本轮没有任何真实模型调用许可；后续S0任务/精确运行配置与调用方物理租约分别承担执行许可和资源控制。源码/模拟测试不得冒充真实加载，生产入口不提供跳过固定字节/来源/租约验证的参数。原创fixture只提交JSON或普通代码，临时小safetensors在测试目录生成，不提交任何权重文件。

构建支持补充：S0已核验既有离线Hatchling 1.27.0 runtime，证明 `34753a7bc583fb15635c372c02675cb0a210a18127c49a681f2f6b3f87c2bff0`，具体路径由同轮原生消息提供。可在原三归档/默认target范围只读复用，用`-B`与`PYTHONDONTWRITEBYTECODE=1`，输出仅新scope；现有uv只离线、无依赖、无cache写入安装。无需新环境或依赖下载，不扩大模型/数据运行许可。
