# P06 G5｜新关系机制私有语料 CPU r2

owner D1；仅在S1派发已集成的新工具、观察oracle、历史参考及精确源码头后启动。本文件当前是待派任务。使用既有独立worktree，分支 `codex/d1-p06-g5-corpus-r2`；先实际读取avoid-overkill、[r2构造边界](P06_G5_L1_REPLACEMENT_PLAN_R2.md)及[冻结协议](P06_G5_PROTOCOL.md)。001/002原失败与连续计数1保留，原48完整组件永久进入本次排除参考。

在已交付`heldout-constraints.v1`真实资源上原创构造至多28题：四域各单工具、多步依赖、工具语义区分、无需工具、观察后澄清各1题，以及transient/timeout恢复各1题。最多8个恢复题供A1。不得先写更多题后按模型效果挑28题；记录全部实际检查过的ID及任何排除。原48题与新批次分开披露，不复用原题/答案程序改名，也不恢复被隔离组件的其他成员。

每题都须让该域关系算法影响参数构造、推导结果或证据选择；单工具与恢复题不能退回按标识抄字段。无需工具题给出完成关系计算所需全部数据，要求计算结论。澄清题必须先观察真实关系，再揭示无法同时满足的约束及需要用户选择的取舍，接受题意允许的等价表达，不能点名缺字段后要求复制字段名。多步题须有实际观察依赖和第二操作的任务依据；恢复题一次成功读取后能完成关系推理，失败→重试→final在3决策/2工具轮内。所有答案类型、必要调用和预算约束必须由题意支持。

采用T1新版显式观察依赖payload及选择入口，保留answers/strategies供现有分析；按每个合法策略声明所需依赖，不能仅给错误策略增加约束。D1的authoring checks须实际选择该oracle，使真实scripted harness产生的观察/决策边界被检查。旧v1数据构造与既有包消费保持；允许对 `src/toolalign/data/evaluation/` 做最小的两个明确catalog/profile分支及对应原创测试，不建立通用规则引擎。不改工具、oracle实现、后端、BFCL/analysis、contracts、依赖或共享状态。

使用D1 r2冻结的完整P02 metadata/P03/G4/原48排除参考与历史边，执行实际tool/schema/normalized-schema/source/template/family连接和语义审阅。任何桥接都隔离完整组件，不为达到28题删除桥接成员或重命名字段。记录真实group数量，不预定为4。新增语义边给出原题、具体程序对应及理由，不能以一般行为类别相同直接断言重复。P02仍只读取已绑定metadata，不读取held-out prompt/答案。

每个保留题至少一条正确脚本及一条能改变结论的反例，复用最小必要的等价策略检查；多步和恢复另确认同Action预提交依赖调用失败。调用已接纳固定工具的真实owned child并保留回收记录。用固定tokenizer检查实际初始输入及最长合法scripted历史的input+256≤2048，不能按字符串长度代替；明确真实模型轨迹仍可能不同。新清单由当前G5 reader直接读入，冻结顺序/seed映射、隐藏oracle投影、recovery IDs及M0/M1/A1计划。A2沿用原Q1已接纳的4组12请求和原hash，不生成新回放材料。

公开只交必要实现/原创测试、`reports/P06_G5_CORPUS_CPU_R2.md`、`coordination/handoffs/P06-g5-corpus-cpu-r2.md`；新题、答案、recipe、完整排除图和原始轨迹留私有 `.toolalign-local/p06-g5-corpus-r2/`。交付精确commit和evidence-index，绑定全部输入/代码/命令及失败历史，列出给R1/Q1的实际审核入口。未通过独立技术及逐题语义审核不能进入模型评测；本包不运行固定模型、GPU或训练。
