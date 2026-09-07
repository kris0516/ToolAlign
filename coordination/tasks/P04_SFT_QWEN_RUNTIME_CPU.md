# P04-SFT-QWEN-RUNTIME-CPU｜有限原生训练接口

状态：PLANNED，未派发、未实现。等待 T1 的 v3 数据 CPU 包与 E1 的固定模型 CPU 包分别通过 R1、最终 CI 和 main 验证；code_base、精确 CPU 配置、模型接口版本和输入 manifest 届时由 S0 填入。本文件不允许读取变化中的两个实现工作区或提前执行编码/模型调用。

拟由原 T1 独立 App 任务承接，gpt-6-astra/max、隔离 branch `codex/p04-sft-qwen-runtime-cpu-r1` 和新私有 scope；禁止 sub-agent。遵循 plan-v0.1、coordination.v1、toolalign.contracts.v1、ADR-0026/0027、REVIEW_POLICY 与已接收的 [真实运行接口方案](../../reports/experiments/P04_SFT_RUNTIME_PROPOSAL.md)。最多两个实现，S0 在实际分发时重新检查名额和旧任务终态。

目标是把已验收数据与模型接口接入固定原生 MLX-LM trainer，完成真实运行前可独立验证的 CPU 控制与状态记录。实际 MLX/Torch 导入、模型/LoRA 装配、tokenizer 构造/编码、forward、优化、checkpoint 数值、生成、GPU 和容量均为 NOT_RUN。CPU 模拟用例必须标为原创模拟，不作为真实 Qwen 数值证据。

允许新增 `training/sft/qwen_batches.py`、`qwen_training.py`、`qwen_checkpoint.py`、`qwen_run.py`（均位于 `src/toolalign/` 下），对应 `tests/training/test_sft_qwen_*.py`、必要原创小 fixture、`reports/experiments/P04_SFT_QWEN_RUNTIME_CPU.md/.json` 和 `coordination/handoffs/P04-sft-qwen-runtime-cpu-r1.md`。S0 精确配置的复制例外在实际派发时固定。不得改原 data/config/CLI、collator/plan、data_v3、model_io/qwen_model、原生 toy、P01 budget、锁、P03、依赖/构建或 S0 协调文件；确有共享缺陷先向 S0 交证据，不复制修订另一个版本绕过。

接口要求：

1. 数据与编码分开。复用验收后的 `prepare_v3` 获得仅 train/validation 的不可变 view。新有限 Batch 文件接口先验证 S0 精确 cohort/配置/输入，在无框架 CPU 阶段用固定现有 engine 生成完整 Sequence/Batch，逐 ID/mask/EOS/长度/审计 hash 核对后原子发布。这个生产路径本轮只用原创 fixture 测试，真实23例编码尚未授权。新接口不得成为可任意取样、解码或导出最终集的通用 cache。GPU child 只读已经绑定的数组；不在导入 MLX 后构造 `OfflineQwenTokenizer`。
2. 运行授权独立于旧数据的 pending 字段。metadata、CPU 配置、容量和完整训练的 S0 运行配置分别绑定；保留所有旧 `training_authorized=false`，不得写 true。生产入口只接受 S0 后续明确固定的 scope/配置 hash/输入与预算，无任意模型、参数覆盖或 skip-validation 参数。本轮 CPU 配置允许实现与模拟测试，不允许真实 loader；后续运行配置的生效方式需明确且不能靠修改已审生产常量暗中放行。
3. 固定模型和参数完全复用 E1 验收后的 `model_io.qwen_model`。不再新增第二套 Qwen loader、LoRA 装配或 adapter key/shape/dtype 校验。rank8、直接 scale2、dropout0、全28层 q/v 和 BF16/FP32 身份沿固定 metadata；运行时全部底座叶与112个 A/B 实测验证。加载后到模型释放始终由真实 child 持同一物理 gpu0 租约。
4. 只调用固定上游 `trainer.train` 的公开参数，注入已审 completion loss 与有限 iterator；不复制循环、改 vendor、关闭 compile 或 grad-checkpoint。固定 Adam(lr=1e-4, betas=[0.9,0.999], eps=1e-8, bias_correction=False)，无 weight decay/scheduler；microbatch1、seed42、原顺序、无 packing/shuffle/截断。每例完成 token mean 后按本累积组真实例数平均梯度，validation 用总 CE/总监督 token。
5. 一遍 smoke/formal 分段采用已接收方案的准确 rank/slice/divisor：smoke 528/528/520/7，对应8/8/8/7、66/66/65/1更新；formal 2000/2000/1936/2，对应8/8/8/2、250/250/242/1更新。原 epoch plan 和旧两段 validator 不放宽；新验证器证明细分完整覆盖原 plan。model/optimizer/RNG 状态跨段连续，seed只初始化一次。capacity 的15例8+7和固定8例重复8遍是独立 scope，不能计入完整训练的一遍。
6. 记录 planned、yielded、同步完成及实际更新应用的 rank。yield 前登记不等于完成；正常返回补核末次 yield，异常时只有确已同步的更新可登记，未知保留 unknown。每段上游局部 it/closure/计数重建与全局 optimizer.step 区分；验证 step 连续值及实际参数/optimizer/RNG 内容，不只核对象 id。首更新的 Adam 状态懒初始化单列。
7. 每段 `val_dataset=None`，局部 save/eval 周期设为本段微步+1，report周期为divisor；上游返回保存仍逐一核对。三次完整 post-update validation：smoke steps66/132/198，formal250/500/743，尾段前文件未评分。每次 validation 使用新有限 iterator，finally 恢复原 training 模式，核对前后模型/optimizer/RNG/step/文件不变。中途异常或元数据缺失不产生可选 score。
8. 新真实 score 与 toy/容量/基线分离。绑定实际 run/scope、原模型/adapter参数与文件、配置/数据/validation/format/tokenizer、optimizer状态与step、完整有序rank、CE numerator/token denominator；只接受有限正值分母和有限 CE。按 `(validation_ce, optimizer_step, checkpoint_file_sha256)` 选择，基线step0不混入SFT候选。保留best、last与最近不同的已评分rollback，最多三份；新运行临时峰值四份加写入文件，删除只限明确属于本轮且已留hash/处置记录的未保留副本，所有历史证据保持。
9. 保存与重载按 E1 完整 A/B/底座身份验证，不因上游 strict=False 返回而验收。选择后先释放模型与optimizer再顺序加载同底座/固定LoRA并重载；同一时刻只驻留一个模型。这里只提供 `weights_only_restart`，旧checkpoint.step是来源元数据，不伪造新optimizer或声称支持完整训练恢复。真实重载CE/greedy比较在后续已授权运行中登记，本包不生成真实checkpoint。
10. parent 无框架，预登记启动额度，child持共享租约后才导入/加载。沿已审自有进程监督模式，至少每秒检查 wall/RSS/swap/pressure/制品，每次同步微步/更新及验证/保存边界检查MLX；不可读指标拒绝，采样不证明瞬时峰值未越限。预算由后续精确scope配置给出，不能放宽原toy/P01 budget。异常、超限、监控或收尾失败均保留原原因及已确认实际进度，终止/回收确切自有PID并核锁；不杀未知进程，不自动重试。
11. 复用已审 wired-limit 抑制层，实际 setter 调用为0。运行前验证固定源码、Metal和真实 device_info 类型/范围，记录每个上游请求；返回0仅为抑制层合成值，不写成实测旧limit。验证抑制层 API 身份、预期请求和finally恢复；不得用 setter 读取旧值或改系统设置。
12. 本包不新增生成/P03 backend。原始baseline、正式SFT的真实validation与后续greedy配置/完整EOS身份分别在对应运行范围登记；不得以诊断结果重新选样或调参。DPO、最终test/ood/BFCL和服务部署均不在本包范围。

CPU 验证用原创小数组/模拟模型及必要少量自有CPU进程，覆盖配置/输入/预算错误在框架前拒绝、数组/审计错配与bool/float、部分导出/回读覆盖、分段丢尾/重复/越界、末次yield未完成、局部/全局step混淆、异常后的实际更新、状态被修改、未评分/旧/跨scope checkpoint、错误分母/非有限score、重载不等、wired guard异常以及监督/收尾失败。测试验证可观察结果，避免为凑数重复上游或机械镜像实现。

资源计划：现有默认CPU与既有离线构建工具，无新环境/下载；新增制品≤1GiB，真实编码/数据build/框架/模型/GPU全部0。实际固定数据prepare与13材料是否需要调用，待S0基于已验收的导出接口决定最小额度，不默认重跑。完成本次相关CPU/独立负例、ruff、契约/公开扫描、实际三归档与默认target，外部cwd验证纯导入/拒绝及CPU状态接口来源。原始argv/UTC/exit/输出/源码时点、全部失败与最终seal交付。

完整候选普通推送、原生交接并结束后，S0才按精确SHA接续独立R1。CPU PASS需最终CI/main才可作为后续0.6B容量前提；真实23例数组另经固定CPU编码范围，容量1次启动及数值预算也另行明确。本任务不提前关闭任何运行门槛。
