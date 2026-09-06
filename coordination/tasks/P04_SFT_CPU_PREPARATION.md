# P04-SFT-CPU｜已绑定序列到实际SFT接口的CPU准备

状态：IN_PROGRESS（CPU）；S0已按完整e42536d原生派发T1、显式gpt-6-astra/max，并核验新的实际轮次ACTIVE。新分支与输入intake待T1确认。P02绑定在42eaa50完成独立R1/最终CI/main技术验证；G-DATA、13例实际页面观察及kris语义/token-mask判断仍待完成。本包不领取正式P04模型训练或代签人工门槛。

| 字段 | 本轮值 |
|---|---|
| owner | T1，既有独立Codex任务与隔离worktree |
| code_base | `42eaa50a9519efe96d60b49f07cfbd106b36778c`，PR9实际main、919CPU/2跳过已验收 |
| authorization_commit | S0原生分发给出的本文件完整协调SHA；切换前读取并保留私有副本 |
| 新branch | `work/p04-sft-cpu`，从精确code_base新建；原work/p01-compatibility及9fe3cbe保持 |
| 模型/推理 | `gpt-6-astra` / `max`；禁止新任务或sub-agent |
| 规范 | plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / ADR-0017/0018/0019/0020 |
| 交接 | `coordination/handoffs/P04-sft-cpu-r1.md` |

先读本授权的AGENTS、PROTOCOL、PROJECT_STATUS、本任务、[S0配置原件](P04_SFT_CPU_CONFIG.v1.json)、ADR-0020、docs03/16、[P04准备事实](../../reports/S0_P04_READINESS.md)和[PR9主干证据](../../reports/S0_P02_TRAINING_BINDING_MAIN_VERIFICATION.md)。本包解决纯CPU可验证的数据/collator、累积计划和参数状态到validation的对应关系；不因旧P01校准或本包通过而声明正式baseline、SFT checkpoint或G3。

## 允许范围与保全

新增 `src/toolalign/training/sft/` 的小型模块和必要 `__main__.py`，新增 `tests/training/sft/` 原创小fixture/边界测试，新增 `reports/experiments/P04_SFT_CPU_*` 的去敏报告、检查器及证据索引，新增本轮handoff。实现保持为现有MLX-LM接口的有限适配，不自建完整训练框架、任务调度平台或服务。

唯一配置例外：新增 `configs/sft-cpu.v1.json`，逐字节复制S0原件 `coordination/tasks/P04_SFT_CPU_CONFIG.v1.json`，实际SHA-256必须为 `5aad6ff6db68ee4fe9bac0aa6104eaeff17bf948b509bfce3d14e3eac9d9aa29`；参数和变更权仍归S0。该配置不是正式模型run配置，不添加从CLI开启真实训练的开关。`configs/training-data.v1.json`及原selection manifest保持原字节，公开manifest内历史candidate状态不改写；当前技术验收由S0主干报告提供。

其他全部只读：P01/其numerical与execution、全部data/model_io、P03、旧测试/报告/审查、冻结契约、configs/依赖/锁/CI、S0协调与ADR、已有worktree和私有证据。不得patch vendor、monkeypatch上游更新/loss/batching结果、改测试收集或重复实现格式。新增接口默认导入仍只需现有CPU基本依赖；MLX/Torch等采用明确的可选路径，不改pyproject/uv.lock或创建环境。

切换前核验当前9fe3cbe、原branch、原P01全部保留refs和最后交接的制品索引；留存新的保全快照。后续只写本轮新私有目录（累计上限2GiB），目录已存在不得覆盖。原18份数据、已选13稳定文件、8228审计、13例reference/native/human副本、两份人工填写CSV全部只读。合法人工字段以后改变不等于冻结证据损坏。不要reset/rebase/force-push或推送旧P01本地分支覆盖较新远端。

## 1. 读取和collator接口

消费已验收的训练绑定，使用现有 `training_selection.verify` 对固定输入/输出完整核对；不重新物化。核对配置579d3d9、公开manifest文件4b9e718d、私有manifest文件eb4bbfe6及canonical ada142fa、原输入/表示/协议身份和实际被消费源码。完整manifest/hash保全与消费train/validation分别记录；最终test/ood_test或BFCL不成为训练输入或参数依据。

提供可供后续训练使用的train/validation数据视图，保持每个Example、rank、split、sidecar和最小padding桶，禁用上游默认的按长度排序、随机重排、隐式截断和packing；不得调用通用dataset loader额外打开test文件。只接受绑定中已有profile、允许split和一致输入，不从数据加载Python对象、模块或回调。完整覆盖/顺序/桶可只读核对所有已选Example和sidecar，本轮不将全量选择重新tokenize。

精确复用 `model_io.training_sequence` / `pad_sequence` 及已验收离线tokenizer。实际collator输出应包含可完整检查的unshifted token IDs/attention/loss mask、next-token inputs/targets/mask与监督分母。唯一追加EOS保留；第一监督位置P−1、末位置N−2，prompt与padding不计loss。为MLX-LM传入专用 `iterate_batches` / `loss` 回调，使用这些显式mask；不依赖已知有padding缺陷的default_loss或重编码ChatDataset。

实际将同10条已选train及3条单列原创协议例经过**新collator**，逐数组对照原13例冻结材料，覆盖原代表/最长/1536/非ASCII边界。协议例不得进入train/validation视图。可在已有native纯tokenizer环境对这13例最多新增一遍必要编码以证明新数据路径；参考/native原测量时间与身份不改写，不新建人工判定或全量重编码。完整原记录/新collator输出私有保留，公开仅统计/hash。

## 2. 梯度累积与全覆盖计划

固定microbatch1、累积8、单遍、seed42且保持selection ranking顺序。每个微步的loss为该例有效completion token的平均CE；一次更新等权平均该周期每个微步的梯度，尾周期按**实际微步数**除。不要静默换成跨样本按token加权的训练目标；validation独立采用总CE/总监督token。这些口径进入安全元数据，不能混淆训练loss均值和validation聚合。

使用真实上游的可注入接口实现有限分段适配：完整周期段的iters应整除累积8，最后不足8的段以实际余数作累积分母；同一model/optimizer/RNG对象连续使用，数据切片不能重头读。全量计划必须得出smoke1600→200更新、formal6013→751完整更新加5微步尾周期=752更新；这些是计划算术，不能写成已实际运行1600/6013次训练。

原创边界测试覆盖0、1、7、8、9、13及实际数量；空数据失败、重复/遗漏/错序/越界范围失败，不能静默丢尾、复制样本凑整或重置optimizer。不要fork上游train循环；若其公开注入点无法实现某项，先提交精确最小反例和限制，继续其余独立工作，由S0处理范围。

## 3. validation与checkpoint状态

上游内置validation位于当前微步之前，不能按最后iteration标签把它当最终权重得分。适配使用明确的post-update validation边界，遍历选定validation完整一次，累计CE numerator和有效token denominator；拒绝空分母、NaN/Inf、不匹配profile/split以及遗漏/重复验证。

每份可供选择的score绑定实际被评估的parameter-content hash、保存checkpoint的文件hash、selection/validation身份、真实optimizer step和已处理微步数。最终尾更新后仍须保存并评估相同状态；不能用前一步分数绑定后一步权重。小型选择器按固定最小finite validation CE、相同分数优先较早optimizer step、再按checkpoint hash取结果。正式validation间隔、LoRA/学习率、真实运行预算未授权；CPU接口不得据此生成假正式run manifest或声称真实SFT best/last。必要小型保存重载仅用于原创数值模块，文件和报告明确TOY_CPU。

## 4. 实际CPU数值复核

复用现有P01已锁replay环境，不运行原整套P01/G1回归来冒充新路径。允许极小原创可训练数值模块（如有限词表表格）在**CPU**执行actual MLX-LM `train`/`evaluate` 注入接口，以13条以内、每条≤16 token、词表≤16、参数元素≤4096、每次最多2次optimizer更新证明8+5尾周期；不加载Qwen/预训练模型，不优化真实P02数据。使用独立PyTorch CPU参考比较mask/loss/梯度和尾周期最终参数，float32 atol=2e−6；记录分母与每步实际状态。不得通过放宽容差、关闭断言或伪造upstream结果取PASS。

保留上游default_loss padding与未处理尾批的既有原负结果；必要时本轮在原创小输入真实复现后给出新适配对照。验证改变被忽略预测位置的logits不会影响loss、右padding不改变loss/梯度、EOS恰好受监督、尾周期正确缩放；不宣称改变prompt输入一定不改变模型输出。实际保存/重载和post-tail validation绑定须直接读取参数与制品，纯计数mock不代替真实数值路径。

Framework replay必须在独立自有进程先实际取得已有共享租约，随后先设 `mx.set_default_device(mx.cpu)`、Torch CPU/最多2线程，再建小数组；记录并核对实际device。每个replay墙钟≤300秒、RSS≤4GiB，失败/超限停止并回收自己进程、释放租约、保留终态与原日志。复用已有资源监督方式；不要改原P01生产模块，或仅凭状态文件空闲启动。框架导入和小CPU数值优化是本包明确限域许可；原P02配置的真实数据/model training_authorized=false保持。新环境、依赖/权重下载、GPU tensor、真实baseline/生成、P04/P05正式训练、网络tracker、费用或上传均未授权。

## 5. 交付与验收

至少提供一个可安装的默认CPU准备/核验入口，可信调用者显式提供本地配置/manifest路径；默认wheel不依赖源码cwd或可选MLX/Torch/tokenizer导入。可选数值适配模块另行验证。保护已有目录不覆盖，错误输入失败并留诊断，命令行不接受任意执行型配置。

对精确候选运行新语义边界及适用原CPU回归、原格式60/截止时间2/训练绑定13探针；当前基线完整组为919 passed/2 HF-only skipped，新独立测试和重复安装须分开计数。Ruff/4契约/公开扫描通过，保留所有失败/跳过与真实source epoch。不要以改变全局收集或删旧测试获得通过。

实际构建新sdist、默认wheel及显式sdist重建wheel，逐成员对Git/metadata/RECORD和公开边界。新默认wheel在现有纯默认环境的新target中安装，运行新默认CPU入口和原创小数据，核对所有新增模块的实际origin；依赖只读复用，不下载。可选小CPU数值路径若在安装版重复，保留独立命令和实际环境，不增加独立测试分母。未执行的普通源码直接wheel路线记NOT_RUN。文档提交与真正可执行测量提交分别绑定，不伪造重跑。

交付精确candidate/parents/tree、所有权diff、S0配置原件hash、实际命令/UTC/环境/退出码/完整日志hash、源/包/13例对照/数值状态/进程清理和原证据保全。报告明确CPU实现、TOY_CPU数值、尚未发生的真实P04行为及全部人工门槛。普通推送新branch，完成handoff并结束该轮，等待独立R1与S0验收；不自行领取正式训练或扩大模型预算。
