# Q1-P02-v3-sources-r4｜独立审核两个固定替换来源

状态：IN_PROGRESS。已于13:55:51 UTC按完整3e18145b66baa7bce498926869b2d52bd0503453原生派发Q1并核验新轮ACTIVE，gpt-6-astra/max；实际新branch/input intake待交付。此范围与D1的v3 CPU实现并行，提前判定新来源，尚无v3数据/编码交付。

code_base：已验证main `d3e56f68ebd67cc576d912b6f06636682b4170ab`；新branch `review/q1-quality-v3-sources-r4`，新私有scope `q1-v3-sources-r4`。保持独立App任务、gpt-6-astra/max；先从完整authorization_commit保存AGENTS、GOAL、PROTOCOL、REVIEW_POLICY、REVIEW_FAILURES、本任务/配置、D1任务、ADR-0025及Q1前轮接收报告，再从code_base新建分支。原8a738ab、原分支、根identity及全部旧私有seal/失败不改，不pull/reset旧分支。

固定input manifest SHA `7d9ad0102b965a75071032d5be3e60dd1a91c09894a739ed852952c1ebbcfd2c`，8份精确副本；源码路径由S0私下提供，复制到自己的新scope。配置`Q1_P02_V3_SOURCE_REVIEW_CONFIG.v1.json` SHA `4cc29d682681ad0467833f9a7ff2ff9cc6d86a68e7aab896c43454532b96c3aa`；来源context SHA `31f7c9bf7b72721492166bba97f4da1999a153f24894ac335ccc4132aff75161`。两来源由原代表材料算法投影而来，不重抽样或按语义表现另选；共3有效决策、8原始turn，均为原train，两个Example将成为材料、另一个为完整来源覆盖目标。

先核对manifest、完整source hash、全部Example/Action/messages/lineage/group/split及源turn身份，再对两个来源的全部历史和3个有效目标分别判定：当前Action是否支持、前缀是否可用、整来源训练适用性。不以局部Action PASS替代完整历史判断；无法核实的业务约定与明确矛盾分开。记录逐决定证据、完整history覆盖、PASS/FAIL/UNKNOWN、建议保留/整来源隔离，引用实际输入hash。原材料13例及旧83来源处置、原P02-Q-081发现只作精确引用，不重复正式审核、不增加旧问题计数。

可交付来源语义结论及新增问题事件建议；**本轮不关闭P02-Q-081，也不批准v3数据处置、token/mask、浏览器或G-DATA**，这些需要实际candidate后另由S0冻结。若新来源FAIL/UNKNOWN，给出可落实到完整来源的建议；不改输入、不自行重标/补业务结果、不联系D1改变样本。S0按稳定issue规则采纳，同一问题前四次自主整改，尚无问题达到第五次。

只新增`reports/data/q1-v3-source-review-r4/`及`coordination/handoffs/Q1-P02-v3-sources-r4.md`；生产实现/测试/配置、看板/正式ADR/台账不改。私有judgments、summary、issue建议、运行manifest和最终seal保存自己的新scope；明确真实Codex-AI(Q1)，不代签kris。所跑脚本先落地并绑定源码/原生执行回执，实际退出码和全部辅助失败保留，不以空执行导出宣布PASS。

仅stdlib/现有纯CPU读取和hash，新增制品≤128MiB，无新依赖/环境、生产测试/数据构建/序列生成、模型/框架/GPU、API/网页或浏览器调用。输入所含旧seals的绝对路径只作来源映射，不跟随其可变文件替换当前冻结副本；无需复制或读取其他训练语义。所有最终集内容禁止语义读取。

先保存/核对原8a的532份公开Git/快照及旧私有封存，换branch后的公用路径按D3解释；新身份只写新scope。完整候选/独立结论、固定3目标分母、全部原命令/失败和seal交接并普通推送后结束，S0核验后决定D1编码及后续正式审核范围。
