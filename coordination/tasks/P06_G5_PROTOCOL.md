# P06 G5｜独立评测执行协议 r1

2026-10-26，S1。承接PR30主干 `d0a266d9fa9abd102fc8b7ceef69e4969fb6702d`；G4经R1 `fe26311` / Q1 `d5c55fb` 终验，处置为 `DATA_INSUFFICIENT_WITH_NO_DPO`。原80条生成任务和两条诊断不进入独立测试。原DPO checkpoint条件未满足，DPO CUDA容量/恢复/训练及M2仍NOT_RUN。G5为当前唯一active App goal；本协议先授权CPU实现与独立审核，GPU仅由S1在清单、源码和运行配置冻结后执行。

## 比较与固定条件

主问题是M1相对M0的完整任务成功率差值，同时报告无需工具判断、参数语义和恢复。M0是Qwen3-1.7B原始指令checkpoint，revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`，不加载adapter，身份中的adapter_hash为null。M1为同底座加G3选中step743，完整状态 `cfb02aec2279138c01f8b336abc08a588d0ab11efa8db68fd61ba0b6150b5d14`、adapter `973c440e29090892ad11d6d56b94bad4c98a5398c223e2b4302d7dba7c4640ed`。M2单列NOT_RUN，不能估算DPO效果。

共同采用已冻结Action JSON模板、tokenizer、BF16底座、未量化、2048上下文、每次256新token、temperature=0.7、top_p=0.9、top_k=0、seed按固定任务序号42+i且每次决策重置。L1轨迹最多3次决策、2轮工具、30秒，冷加载在轨迹内；批次完整文件预检单列且进入段/分配成本。M0/M1使用相同输入、oracle、fault schedule、采样和文件验证策略。M1的FP32 Q/V rank8、alpha16、dropout0与实参hash保持。主比较cache off、recovery on，不在测试结果出现后调整任何设置。

## 三层结果与固定上界

- L0：CPU实现和小型原创数值检查，只支持实现正确性。
- L1：新只读工具集 `heldout-devops.v1` 的四个工作域，每域最多12题，六类各2题：单工具、多步依赖、相近工具语义、无需工具、缺信息/不可满足请求、有限恢复。上限48题，M0/M1各一次，共96轨迹。每题只advertise其工作域工具，完整oracle只在host侧。实际group由工具/schema/template连通审计决定；若四域有连接，就报告真实组数。既有P02所有分组、P03开发及G4 train键用于隔离审计，不通过改名或句式变化掩盖重复语义。
- L2：官方BFCL scorer与数据均固定 `f7cf7359b7ac615a0b294831c5ba2bc95ee4a000`；仅simple_python、multiple、irrelevance，每类最多20题。按官方文件顺序只检查前50个ID，依次保留契约可无损表达、固定tokenizer输入加256不超过2048、且未触发已知训练/开发分组重叠的前20题。所有检查过的ID、排除原因及未满数量均记录；规则在输出前固定，不能补选更容易的任务。两模型同清单，最多120次单决策，30秒/次。官方scorer在独立CPU环境运行；不能用自建oracle替代，不调用外部提供商API。必须补齐每个冻结ID的失败行，不能让官方partial-eval静默缩分母。AST结果不写成真实API执行成功，也不与overall排行榜混同。
- A1：M1在L1固定8个恢复题的recovery off，对照主比较中的recovery on；关闭时首次可重试工具错误即明确终止，不给模型后续重试机会。预算和失败分母保持，额外成本进入总账。
- A2：M1使用4组、每组3个已冻结开发ModelInput的相同请求序列，cache off/on各一次，共24次生成；不使用最终测试输出来制作序列。每组三请求在同一owned child中，90秒上限，单请求最多30秒，seed对应不变。prefix cache只复用完全匹配token前缀，模型/adapter/tokenizer/template/租户身份和生命周期绑定。记录实际命中token数、原始输出相同或差异、TTFT/prefill/decode及完整耗时。此项是请求回放性能测量，不冒充新的任务成功率。

## 统计、失败与证据

L1主效应为全部冻结任务上的配对成功率差（M1−M0），同时给绝对分子/分母和各类计数。按真实连通group做10,000次配对cluster bootstrap，统计seed42，报告95%分位区间与逐组效应；组数很少时明确粗粒度和适用范围，增加leave-one-group-out敏感性，不作总体显著性或多训练seed方差结论。L2依其真实工具/schema组另算配对结果，不混合L1。A1/A2为预注册次要对照，不用多个p值筛选结论。

保留raw format、tool selection、argument semantic、实际执行、task success、unnecessary call、invalid tool、recovery、budget exhaustion的原始计数，非适用为N/A。解析失败、超时、上下文溢出、被取消、基础设施中断均占正式任务分母；未启动项另列并在总体成功率中视为未成功，不补跑已started ID。恢复只接续从未启动的ID，保持原始行。实际token缺失为unknown，不按零计算。计时区分完整段、模型冷启动、预检、TTFT、prefill、decode、工具和队列；少于100次的尾延迟标探索性。显存与host RSS分开报告。

模型、prompt、工具、oracle、scorer、metrics、输入清单在正式推理前经R1/Q1冻结。evaluator bug若实证成立，版本升级、保留原结果并对全部相关模型重跑；不能只修一方分母。最终至少20例覆盖不同原因的bad cases、无改善或退化分析、质量成本图和可复算入口。没有20例失败则展示全部失败并说明真实数量，不补造失败。测试内容不反馈训练/选模。

## 资源与派发

最多224条主/恢复轨迹×30秒约6,720秒，A2最多720秒，原创开发容量探针最多两条/60秒；准备、传输、冷启动差异与回收暂按1,200秒估计，总约8,700秒。这是执行前估计，已有G4设备峰值约4GB、L4容量23,034MiB支持优先L4；不代表新矩阵已实测。G5所有GPU分配含失败/安装/空闲/回收硬上限14,400秒和余额观测8 CU，单实例初始上限7,200秒，具体segment另冻结。任何扩展必须仍在该上界内且在查看对应结果前登记。预算余量不要求强行消费。

T1实现评测后端/执行器/cache与恢复开关；E1先实现新工具集；两包文件范围分离。之后D1构造私有L1任务与隔离证据，E1再承接BFCL adapter/scorer/分析。R1独立技术审查、Q1语义/分组/结果说明审核，S1维护状态、合并、GPU与账目。使用既有独立对话和隔离worktree，禁止sub-agent，最多两个实现任务。Mac不加载固定真实模型做推理；仅小型原创CPU数值、tokenizer预检与分析。没有购买/充值或公网服务授权。
