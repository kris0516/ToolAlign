# P06 G5｜BFCL 固定子集、官方评分与分析 CPU 包

owner E1；仅在S1明确派发后从精确集成提交建立 `codex/e1-p06-g5-bfcl-analysis-r1`。读取avoid-overkill、experiment-readiness与research-statistical-analysis，遵守[共同协议](P06_G5_PROTOCOL.md)。本包授权CPU适配、官方源获取、独立CPU评分环境和分析实现；不授权真实模型加载/生成、GPU、训练、提供商API调用或修改最终模型/prompt。

## 官方来源与输入冻结

BFCL代码和数据均固定 `ShishirPatil/gorilla@f7cf7359b7ac615a0b294831c5ba2bc95ee4a000`。在私有目录保存原始文件、来源URL、提交及文件身份；不把原始benchmark题目/答案放进公开仓库。只检查simple_python、multiple、irrelevance各自官方文件顺序的前50个ID，依预先固定顺序保留最多20题。筛选只使用题目、函数schema、固定tokenizer长度和已知训练/开发重叠；不能依据答案、预期难度或模型输出选题。先保存全部检查ID、每项决定/原因与选中清单，再读取所需官方答案。

无损表达以冻结ModelInput/Action和官方参数含义为准；可以采用可逆、无碰撞的函数名映射，评分前恢复原名，并保留映射与逆映射证明。不得静默丢弃schema字段、补加改变语义的约束、截断历史/工具或借旧ToolACE改写授权修改新来源。无法无损转换的条目明确排除；不足20或某类为0都如实交付，不增加扫描范围。运行前固定tokenizer输入加256不得超过2048。工具为不可执行的外部声明，不加入LocalToolRegistry。

复用既有grouping及隔离辅助逻辑，核对S1指定的P02分组metadata、P03开发和G4 train材料；不读取P02 held-out prompt/答案。保留实际L2工具/schema/template连通组与重叠处置，不强制每题独立。与D1并行时只读其已交付接口；不得修改D1独占的data/evaluation包。

向T1 action-only入口输出 `toolalign.evaluation-inputs.v1`，purpose=`action-only-model-evaluation`，各项为task_id/family_id/group_id/category/model_input，顶层为schema_version/purpose/inputs。最终以S1给出的T1精确候选reader为准。答案、原始官方记录、映射和评分资料保留host侧；模型输入只含messages/tools。若没有保留题目，交付覆盖/排除结果，不伪造空计划执行或实际分数。

## 官方评分和失败分母

调用固定源码的 `_evaluate_single_ast_entry` / `_evaluate_single_relevance_entry` 或其实际官方AST核心函数；不重写答案匹配语义。已有官方profile `qwen3-1.7b` 的 `underscore_to_dot=false`，使用真实对应profile而非冒名其他模型。只提供本地严格Action解码接口，不实例化官方模型handler或联网推理。

每个冻结ID×M0/M1均须有一行，缺失结果明确标not_started/interrupted；不能用官方partial-eval缩分母。保存原raw_text、运行状态、独立raw Action有效性、官方raw valid及详细原因。严格成功要求按时completed、raw Action合法且官方评分通过；空文本、错误格式、超时、取消、基础设施错误或未启动始终失败，即使官方irrelevance将其raw score判真。合法final/clarify/refuse才可转换为明确无工具响应；错误不能改写成合法空调用。未调用官方scorer时标NOT_RUN，不填写测量值。AST通过不表示真实API执行成功，子集不称官方overall。

在单独私有CPU venv安装固定官方源码所需依赖并记录可复算lock；不改共享CUDA/SFT/DPO环境或锁。可使用现有uv/本机Python3.12与已有包缓存，只下载包和该官方仓库需要的源码/数据，不下载模型权重。官方完整依赖如需Torch仅用于CPU import和原创小例，不运行固定模型；优先最小可直接导入官方评分函数的真实依赖，不用伪造模块或修改官方源码绕过导入。新增依赖文件限 `requirements/bfcl-*.in` / `requirements/bfcl-*-py312.lock.txt`；项目默认依赖保持。

用原创CPU输入和真实官方scorer验证：正确/错误参数、错误函数、多工具选择、合法无需工具、坏Action、空输出、timeout/not_started即使官方raw为真仍严格失败；函数名可逆与不可表达schema排除。保留实际命令、退出码及官方输出。普通CI仅跑无重依赖的原创适配/分析检查；实际官方评分证据来自本专用环境，不能把跳过误报为运行。

## 预注册分析与交付

分析器消费固定输入清单和T1原始终态，不调用模型。L1/L2分别计算M0/M1全部计划分母上的配对成功率差、绝对分子/分母及分类；L2另列官方raw分与严格成功率。实际连通group做10,000次配对cluster bootstrap、seed42，并报告每组效应及leave-one-group-out；每次抽取完整group，保留其所有任务。少于2组为NOT_ESTIMABLE，不制造区间；少组数区间仅描述当前group经验分布的稳定性，不代表总体覆盖或多训练seed方差。

复用实际trace提供raw format、工具选择、参数语义、执行完成、task success、多余/无效调用、恢复和预算耗尽的可判定计数；无法从现有证据判定的项标unknown或N/A并说明分母。A1对固定恢复题做配对比较；A2对固定序列记录实际prefix命中、原始输出差异、请求位置、冷加载/prefill/TTFT/decode/全程时间，保留全部失败，不能把成功子集延迟当总体性能。token缺失不是零，host RSS与GPU显存分开，少于100请求的尾延迟为探索性。

提供JSON/CSV可复算表与质量—成本图的生成入口，图必须标实际样本量和成本范围；此时仅用原创fixture验算，不填真实模型结果。失败案例索引覆盖至少20个不同原因/类别，若不足则展示全部真实失败；完整原始题目/答案留私有，公开报告仅用允许的摘要。结果出现后不改指标、group或抽样来筛选结论。

允许新增 `src/toolalign/evaluation/bfcl/`、`src/toolalign/evaluation/analysis.py`、对应原创tests、上述新依赖文件和必要官方来源配置/notice；不改contracts、prompt、T1执行器、tools、训练实现/锁或共享状态。交付精确commit、`reports/P06_G5_BFCL_ANALYSIS_CPU_R1.md`、`coordination/handoffs/P06-g5-bfcl-analysis-cpu-r1.md`、私有evidence-index、选取/隔离/长度清单、官方评分CPU证据与分析反例。R1独立技术审查、Q1对固定子集和解释边界审核后，S1才冻结正式运行。
