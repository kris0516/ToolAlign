# G4｜偏好与 DPO 执行协议

2026-10-26；S1 协调。基线为 PR27 主干 `1267d1a33dfb08bfd9800b80ea97315730748952`。当前仅放行两项 CPU 实现；真实候选生成、容量与 DPO 均须在代码独立验收后绑定具体 run 配置。

## 输入、边界与预算

- 主实验使用 G3 选中的 Qwen3-1.7B step743，完整状态 SHA256 `cfb02aec2279138c01f8b336abc08a588d0ab11efa8db68fd61ba0b6150b5d14`，adapter 参数 hash `973c440e29090892ad11d6d56b94bad4c98a5398c223e2b4302d7dba7c4640ed`。原始 revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`，其余模型/模板身份沿用 G3。
- 新建原创、仅 train 的可执行任务。最多128个任务、每任务4条真实SFT候选，最多512条轨迹。先冻结任务与分组，再生成候选；每任务最多保留1对，不把模板替换实体算作独立问题。
- 复用现有固定工具实现。P03的10个公开开发例仍为原 validation 身份，属于已公开开发诊断，不进入G4训练，也不作为正式held-out证据。新任务须记录与这些开发例的共享工具/schema和不同任务来源；不能宣称对开发集的schema隔离。新正式语料与P02的train/validation/test/ood_test及未来G5测试按来源、schema、任务模板组检查，覆盖prompt暴露的全部工具而非仅实际调用。使用冻结分组索引；新连通分量若触及P02 validation/test/ood_test则整体隔离新增分量。其余同一工具/schema连通组整体留train，G5不得把同组任务报成独立held-out测试。
- 新训练语料原始文件、oracle、轨迹与偏好存私有目录；公开代码、合成小型测试、统计和hash。不得读取BFCL或最终测试来构造候选。
- G4累计GPU分配上限21,600秒、余额观测消耗上限12 CU，包含安装、空闲、失败、回收和恢复。优先L4，任何时刻一个重GPU作业；不购买、不开放公网。Mac只做开发、小型CPU检查、预处理、控制与分析。
- 真实生成前冻结一个小pilot和完整候选顺序；pilot轨迹计入总预算。先测加载/吞吐/成功与有效对产率，再决定是否在原上限内执行余下清单；不按结果更换任务或补造chosen。超限、数据不足或失败均留记录。
- 候选启动前保存固定ID和started记录，完成后保存终态。恢复只执行从未启动的候选；已有终态不重跑，已启动而没有可确认终态的候选记interrupted并留在原分母。诊断重试另列，不能用其成功覆盖正式候选失败。

## 生成与偏好定义

沿用固定 Action JSON / non-thinking 模板与完整schema，最长上下文2048（包含所需生成空间）；超长明确计数排除，不截关键字段。沿用每轨迹3次模型决策、2轮工具、每决策256新token、30秒deadline。当前生成默认温度0.7、top_p0.9、主seed42，4个候选的实际派生seed与顺序须在运行前固定并逐条保存。正式G5另冻同口径解码。

只把 `ModelInput` 与 `GenerationConfig` 给模型；oracle和脚本答案留在父进程。每个candidate从同一初始faults独立构建executor，防止已消费的故障队列影响下一候选。首先复用LocalHarness拥有的子进程，CUDA backend在该子进程按需加载已选SFT，同轨迹复用。先用pilot测量，不提前引入常驻服务或RPC。CPU测试用小型fake/scripted backend，不能将其输出登记为真实SFT候选。

偏好completion是一条真实assistant Action JSON决策，避免把外部tool observation当作DPO标签。从同一任务的真实成功/失败轨迹中找共享完整ModelInput下的首次分歧：

1. chosen整条轨迹经独立确定性oracle判success，且当前决策属于至少一个剩余合法策略或合法终止答案。
2. rejected整条轨迹判failure，当前分歧决策本身须有明确语义错误；不能因后续回答失败把正确当前调用降为负例。
3. 两个合法动作/等价策略为tie；成功/成功、失败/失败、unknown、长度/超时/基础设施失败、不可恢复前缀、仅格式坏例不进入正式偏好。
4. 原始JSON的空白、key顺序或call_id差异不能独自成为偏好。完整前缀hash、决策位置、两条原始轨迹hash、实际采样参数、语义错误类别与选择顺序进入lineage。
5. 每任务多对候选时按预先固定candidate ID顺序取第一有效对；其余保留处置，禁止按DPO收益选样。

P05须单独证明当前语义错误，不能把既有oracle的“未匹配枚举”直接当证明。例如开发例未限制时间单位时，ms/s以外的合法min转换仍可能正确，未枚举且不能证明错误的动作记unknown。动作等价比较不能重写实际ModelInput来制造共同前缀。多步依赖的chosen还须由decision_inputs证明调用前已有所需observation；同一decision内按顺序列出两个调用不构成此证据。

正式记录使用冻结 `toolalign.preference.v1`，共享prompt hash可复算。其单个generation_parameters对象明确绑定chosen候选；sidecar保存chosen和rejected各自参数，禁止丢掉不同seed的事实。新增批次/lineage格式属于P05内部输入，不修改冻结公共契约。

Q1判定前冻结有效对池、分层配额和抽样seed42；按已登记的语义错误主类别分层，每个非空类别至少1对，其余名额按类别剩余数量比例分配，余数以固定类别顺序裁定，层内按seed42与preference_id的规范hash排序取样。总数为 `min(total,max(100,ceil(total*0.10)))`，unknown计误标，严格大于5%阻断正式DPO。1–100对全审，101–128对审100对；零对不启动DPO。所有已确认误标或unknown对均排除训练，即使批次不超过5%；保留原审核分母，不以删除后重算或换对回填绕过门槛。对数不足和纯格式负例均如实处置。Q1还检查同组隔离、合法多解及首分歧归因；interrupted留候选分母并按不可判排除。

上述补充来自独立Q1的只读协议预审；尚无真实候选质量或正式偏好PASS。

## 两包共享输入/输出

D1输出私有 `tasks.json`：顶层schema_version=`toolalign.preference-tasks.v1`、purpose=`train-candidate-generation`、registry_hash、tasks；每个task含task_id、family_id、group_id、category、example（冻结Example）、oracle_task（OracleTask字段）、faults。全部split=train，task_id与Example/OracleTask一致。任务清单hash、来源/分组/排除记录另存manifest。

T1读取该清单，用registry/executor/oracle运行真实轨迹。输出 `candidates.jsonl` 每行含task_id、candidate_id、generation_parameters、model_identity、harness_result（asdict）、decision_inputs（各次完整ModelInput，按顺序）、status；原始轨迹和错误均保存。decision_inputs必须来自真实请求并与decisions.model_input_hash吻合，不能重写观测或加入oracle。批次summary记录全部固定分母、各类失败、实际时长/资源/源码/输入身份。D1抽取器消费该结构，产出preferences.jsonl、lineage.jsonl、dispositions.jsonl与summary.json。

## DPO 后续门

TRL版本与CUDA依赖锁由S1另行分包核验；本首包不添加训练框架或修改依赖。正式DPO采用标准sigmoid、completion token logprob之和、beta0.1、lr5e-6、seed42、一轮；policy与冻结reference均由同一已选SFT初始化，不能停用adapter代替reference。有效batch8、末批按实际对数；具体步数由Q1已接纳的实际对数确定。

R1只读核对了[TRL 0.26.2](https://github.com/huggingface/trl/blob/v0.26.2/trl/trainer/dpo_trainer.py)与[Transformers 4.57.6](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/trainer.py)接口，后续CPU包沿用原生DPOTrainer循环。传两个已加载SFT的PEFT模型且peft_config=None；reference全冻结/eval，不混入ref logprob缓存。显式关闭label smoothing、RPO、IPO、length desensitization、weighting、reference同步和Liger等变体。普通字符串prompt不会再次套模板，但上游会分别编码并给两条completion追加EOS；因此输入completion不预加EOS，关闭三个长度截断参数，实际prepared token IDs须与冻结输入逐项对应。

优化器显式AdamW，betas=(0.9,0.999)、eps=1e-8、weight_decay=0、foreach=False、fused=False、常数lr5e-6、零warmup、max_grad_norm=0。使用SequentialSampler保持冻结顺序，microbatch1/累积8，尾组按实际微步数。保存完整optimizer/scheduler/RNG/Trainer state；分段通过on_step_end在完整optimizer步后保存并停止，保留原一轮总步数，ignore_data_skip=False。reference每次从原选中SFT重建。必要CPU验收包含不等长响应的mask/EOS/SUM数值与梯度、ln2和reference不变，以及10对样本完整两步对比第一步保存后新进程恢复第二步（尾组2）。上述均为接口方案，实际兼容和恢复仍NOT_RUN。

R1先验收ln2、梯度、prompt/pad/EOS mask、长度求和、SFT加载前向一致、reference不变与仅adapter更新；随后在Colab覆盖最长对、首次optimizer state、保存及新进程/新实例完整恢复。参考方案优先两份同SFT BF16底座与FP32 adapter，容量不足再评估有身份绑定的reference logprob cache，不静默切换。

G4完成条件是偏好处置、实际DPO checkpoint/曲线、资源和失败证据、R1/Q1独立终验与主干合并。效果方向由G5同协议结果决定。
