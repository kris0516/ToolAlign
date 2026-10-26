# P06 G5｜独立L1任务与分组 CPU 包

owner D1；复用自己的隔离worktree，从S1派发的精确集成提交建立 `codex/d1-p06-g5-corpus-r1`。先实际读取avoid-overkill和experiment-readiness。消费S1指定的E1新工具候选与[共同协议](P06_G5_PROTOCOL.md)，保留该实现的独立审核状态。本包只授权CPU任务构造、scripted轨迹、tokenizer预检和元数据审计，不授权模型推理、偏好生成、训练或GPU。

生成新的私有held-out L1包，上限48题：四个实际工作域各最多12题，单工具、多步依赖、相近工具语义、无需工具、缺信息/不可满足请求、有限恢复六类各2题。每题仅advertise所在域工具，registry使用 `LocalToolRegistry(tool_names, catalog_id="heldout-devops.v1")`。题目应有真实工作目标，四域的语义与算法可以不同；不能把实体替换数量当独立family。例数不足或分组审计不通过如实保留，不放宽规则补齐。

新包固定schema=`toolalign.evaluation-tasks.v1`、purpose=`heldout-model-evaluation`、catalog=`heldout-devops.v1`；每项为task_id/family_id/group_id/category/example/oracle_task/faults/tool_names，example及OracleTask split为test且身份相同。保持现有Action/Example/OracleTask契约；由T1的新reader消费，不能改旧G4 train-only reader、旧任务或P02分组。ModelInput投影只包含messages/tools，答案、允许策略、故障计划与分组留host。

复用现有SemanticOracle，逐题明确答案JSON结构/类型和允许执行策略。对无需工具和clarify/refuse，题目应说明所需结构值，不能在oracle里暗加只接受某句措辞的限制。允许的等价合法策略全部登记；若要求恰好两步、不得查询其他对象或禁止多余调用，必须由题意明确支持，不能把无害的额外读取自动当错误。多步依赖须由首次真实返回提供下一步信息；不能靠schema或prompt中泄漏完整答案。恢复题使用单工具的首次transient或block故障，再一次重试后final，确保正确轨迹实际能在3决策/2工具轮内完成；不要把两步依赖加重试造成不可完成题。

每题至少一个正向scripted CPU轨迹，并覆盖错误对象/版本/日期、工具语义混淆、错误参数、无工具题多余调用、缺信息猜测、伪造成功答案等反例；按实际类别安排，不为每题复制完整矩阵。多解题跑至少两条合法策略。保留真实执行输出、解析/语义分数、进程回收与失败，不能用mock工具输出充作运行证明。工具临时超时应使用真实owned block注入并回收；不改变冻结时限来迁就实现。

分组审计复用P02 `assignments.jsonl` / `tool-lineage.jsonl` 的冻结metadata、P03公开开发任务及G4 r2完整20题。S1消息提供实际私有根与hash；P02保留测试的prompt/答案不读取。按source、tool、schema、normalized-schema、family、规范化template键做传递闭包，旧组件有桥接时整个新组件隔离；新48题和可读P03/G4 prompt之间补充既有trigram近重复与可解释的语义复核。P02只做其现有metadata允许的检查，明确不声称新的全面语义近重复检索。输出实际components和跨域连接，不能强行分成四组。当前统计对不足2组已规定不估区间。

原始authoring、任务、oracle、完整轨迹和审核输入均放私有 `.toolalign-local/p06-g5-corpus-r1/`。可新增 `src/toolalign/data/evaluation/` 的小型构造/审计入口及对应原创CPU测试，复用现有投影、oracle、分组辅助函数；不改旧preferences行为、工具目录、T1后端/harness、contracts或依赖锁。源代码中不内嵌最终48题/答案。公开摘要只含覆盖、分组、隔离、执行与版本身份。

使用固定1.7B tokenizer做输入长度预检，覆盖初始及全部正向scripted历史，记录真实token数，加256后不得超2048；超出题目隔离，不截断schema/历史或按模型输出挑题。此处允许tokenizer，不允许真实模型加载或调用。另提供A2固定开发回放输入：从P03已公开开发资源构造4组、每组3个纯ModelInput，包含重复请求及共享前缀的另一合法请求，不取最终测试输出；保存独立purpose/序列ID/顺序/seed，具体run外壳由S1与T1接口绑定。

交付精确commit、`reports/P06_G5_CORPUS_CPU_R1.md`、`coordination/handoffs/P06-g5-corpus-cpu-r1.md`、实际命令/退出码、私有authoring/tasks/group-audit/长度/轨迹与evidence-index.json。Q1必须在正式模型运行前独立审核全部保留题目的语义、正确/错误策略和分组；R1审核构造消费接口。正式结果尚为NOT_RUN，不能把scripted成功率当模型效果。
