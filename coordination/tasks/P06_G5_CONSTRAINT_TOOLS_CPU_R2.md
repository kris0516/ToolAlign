# P06 G5｜关系约束工具 CPU r2

owner E1；仅在S1另行派发精确集成头和D1完整排除参考后启动，当前文档不是活动任务。使用既有独立worktree，分支 `codex/e1-p06-g5-constraint-tools-r2`；先实际读取avoid-overkill及[已接纳的构造边界](P06_G5_L1_REPLACEMENT_PLAN_R2.md)。原heldout-devops及48题继续整体隔离，不能靠函数/字段/catalog改名恢复。

新增固定 `tools/constraints_catalog.py` 和catalog `heldout-constraints.v1`，四域各两个只读工具，共8个。每域提供完整有限关系数据的读取与对应关系检验，两种操作的语义明确；单次读取足以完成单工具、观察后澄清和故障重试题的关系推理，两步任务可依据实际观察构造第二工具参数。域键沿用releases/incidents/packages/storage，公开DOMAIN_TOOLS、固定资源和算法语义，D1另行撰写私有题目。

算法按已冻结计划实现：发布按阶段累计摘除实例并逐区检查quorum；事件计算整数左闭右开窗口内事件区间的并集与补集；软件包根据prerequisite→dependent DAG、目标的传递前置闭包检查恰好覆盖且无重复的安装序列；存储按故障域失效后仍存活的唯一shard数与k判断恢复，同一shard多副本不能重复计数。声明必须说明端点、累计性、节点范围及副本语义，不靠隐藏约定。固定数据规模保持小，给出能区分相邻边界、错误顺序或关联故障的原创实例。无需工具题由D1提供全部关系数据，本包不创建最终28题。

工具操作仅使用代码内原创虚构数据和有界输入，不访问路径、网络、环境或训练原文。参数名称和结构必须来自实际机制，不增添无意义字段或随机前缀改变hash。用D1冻结的完整参考实算tool/schema/normalized-schema交集，保留任何命中和处置；若某个设计命中原组件则停止该设计并交回具体证据，不能放宽隔离规则。语义独立性仍须后续Q1逐题审核，四域不预先宣称四个独立group。

允许新增constraints_catalog.py、registry.py中的第三个固定catalog映射及必要导出、`evaluation/cuda_eval/protocol.py`中明确允许新catalog并按输入catalog建立registry/subset、对应原创tools和reader测试。保留旧两个catalog模块字节及其spec/manifest/registry hash；默认值和旧输入消费保持。runner.py由T1占有，本包不改；不改D1 data/evaluation、旧oracle、模型、contracts、依赖或共享状态。现有executor已传递固定catalog，复用即可，不建立通用插件机制。

验证8工具真实执行与对应关系边界、实际owned child选择新catalog并回收、reader消费新catalog的原创小fixture、旧两catalog身份和旧输入保持，以及实际排除参考交集。复用未变的取消/ValidatedCall/模型数值证据，只测本次影响的边界。交付精确commit、`reports/P06_G5_CONSTRAINT_TOOLS_CPU_R2.md`、`coordination/handoffs/P06-g5-constraint-tools-cpu-r2.md`与私有 `p06-g5-constraint-tools-r2/evidence-index.json`；明确D1可用的schema、资源、两步关系及单次关系读取。仅CPU，无新依赖安装、模型推理或GPU。R1技术及后续Q1语义独立通过后由S1接纳。
