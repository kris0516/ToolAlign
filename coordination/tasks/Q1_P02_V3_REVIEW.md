# Q1-P02-v3-r5｜实际排除与13例材料复核

状态：ACCEPTED。原review7941f1f56519ea2eac437c669ac2c6445a0329f6正式PASS、原生空闲；S0核验5,115路径/42命令后普通合并10a22a0，采纳P02-Q-081关闭/归零事件，G-DATA批准冻结v3。[正式接收](../../reports/S0_P02_Q1_V3_ADJUDICATION.md)。

原派发记录：已于2026-09-07 16:08:07 UTC按完整授权`21f92107d03f776a3b81d4d61d39072e96d236d3`原生派发并核验新轮ACTIVE；新分支/581基线、16授权、294输入和4,811实际路径已由S0核验；原intake SHA `a792297f26d9d0c8afc61804cf34e47d8ef441b6c780ab476915ecb13c55badd`，本段保留当时intake记录。D1完整候选`5825d789ee89afedbfff31e828223608c6f435e2`已正式接收；completion `1d65726003a5eed3b6b74a4ba77bc0e49cd724d0f0dab82733ac8ec9e3e7cc0f`、receipt `871c318fe264ec84c90a37aeb20b92f07ce71e6992c4ba4b71bd2fea2e04920d`。本轮固定294输入的manifest为`b2ae91538823c2e64af68deb871736134e488df00937df34e2cfd207470e4a8c`；[精确配置](Q1_P02_V3_REVIEW_CONFIG.v1.json)为`e6a1c4ac922662992f5afeba338d88e522015367f5753c8c0ebc0743994ce51e`。S0 authorization_commit以原生派发的完整SHA为准；[冻结证据](../../reports/S0_P02_Q1_V3_REVIEW_DISPATCH.md)。原`9c12c47fd815f86992078313bac88dcec253f37f`仅覆盖两新增来源语义，不替代本轮实际排除或token/mask核验。

沿用独立Q1 App任务及gpt-6-astra/max；新branch为`codex/q1-quality-v3-materials-r5`、新私有scope `q1-v3-materials-r5`。code_base固定为S0协调基线`7a731c5f08a561f5941fcba5996004706f373392`，其生产基线仍是已验证`d3e56f68ebd67cc576d912b6f06636682b4170ab`；候选5825单独冻结，不把未合并候选写成main生产能力。先保存完整授权中的本任务/配置、AGENTS/GOAL/PROTOCOL、REVIEW_POLICY/REVIEW_FAILURES、ADR-0025所在DECISIONS、D1范围/精确v3配置、S0候选接收、两来源正式接收及本次冻结报告。切换前保全原9c及旧公开Git/快照、全部旧私有seal/终端回执和根identity，新身份只写新scope。

223精确副本共29,269,007 bytes，71只读引用；包括v3和v2各30个实际输出、当前66份材料、旧66份材料、原测量13份、新旧两源码epoch的36份元数据/consumer源码、两次新编码原命令/预算/精确放行及原8a/9c判定。全部路径和字节绑定既有S0正式接收或明确固定hash。大型数据仅作identity、处置、rank及原行字节检查；来源和语义判断按本任务继承规则处理，不把出处路径当作递归读取授权。

输入由S0按精确candidate冻结，副本与只读引用逐项校验原字节/hash/类型；出处路径不自动增加读取范围。包括实际v3有效数据/选择/排除/恢复/lineage、完整13例两engine材料/HTML、旧11例的原运行/判定、新两例原编码及S0精确放行、原8a和9c裁定、当前稳定issue台账。heldout/test/ood/BFCL仅核验hash/隔离元数据，禁止语义读取、调用样本工具或追加抽样。

核验P02-Q-081问题来源全部两条原决策的实际隔离，在有效train/validation及两个profile选择中均不存在；排除记录保持原身份/字节，错误历史之前的局部PASS决策也不能遗漏。核验旧83来源处置、3项原字节恢复、同group其他来源和staging非晋升仍保持；原FAIL/UNKNOWN历史判断不重写。预期总84处置来源、81来源/100决策排除、3来源/3决策恢复，实际counts在候选接收时固定；数据过滤不补选、不重标，v1父rank/v2上一版rank/本轮连续rank明确。

固定13个唯一材料身份由11旧例（8实际train+3原创协议）和2新增实际train组成。先逐例、逐类型核对Example/Action/messages/lineage、P/C、完整ID/attention/loss/causal mask、EOS、右padding、token_texts和静态HTML表格；原Example映射到当前case/rank/quality revision。两engine26记录仍是13个唯一例，不能混计。

旧11例的来源/协议语义结论从原8a的精确PASS记录按身份继承，前提是原语义输入和完整数组未变；明确继承旧判定和原实际编码时间/命令/源码，而非重审或重新测量。新两例的完整来源语义引用原9c：2来源/3原决策/6调用已PASS，其中另一个来源覆盖目标不具备独立编码额度。本轮对两份新sequence在两engine的实际输出独立进行token/mask判定，并核对对应语义输入仍为9c审核的原字节；不因摘要的PASS跳过实际数组/前缀对应检查。

实际序列许可绑定S0放行`1eeea3bd45daa8caf5d2867efa5859a446673888993aaaf9cc3a21b80ca555fd`和原Q1提交/两级seal。核对每engine只发生2次新sequence生成及其原命令、源码epoch、开始/结束/失败事件；旧11例重编码0、第三个来源覆盖目标新编码0。不加载tokenizer，不以验证之名再次编码。浏览器实显继续NOT_RUN，静态HTML检查不写成实际屏幕观察；真实trainer消费待后续独立范围。

本轮是P02-Q-081实质整改的正式复核。若实际整来源隔离通过，提出该稳定issue的PASS/关闭与连续失败归零事件，历史失败保持；若仍未满足同一要求，提出对应下一次正式失败，不能另起名称规避计数。旧83来源和新两来源仅做处置/继承绑定检查，不重复增加其正式修订次数。其他新发现按稳定source/requirement去重，区分新问题与已存在问题；辅助脚本错误不计质量失败。S0裁定台账，同一问题第5次才暂停整个目标。

仅现有stdlib/纯CPU读取与hash；新增制品≤1GiB，生产测试、全量数据构建、分词、框架、模型/GPU、下载/API、浏览器重试均0。允许新增`reports/review/Q1-P02-v3-r5/`和`coordination/handoffs/Q1-P02-v3-r5.md`；不修改被审数据、生产实现、旧标签、台账或协调状态。不为补分母重复旧180/83来源语义审核。

输出实际处置矩阵、13例材料/判定继承映射、新两例实际token/mask结论、原始命令/数组/静态HTML绑定、稳定issue事件建议、PASS/FAIL/BLOCKED和NOT_RUN。保存所有源码时点、argv/UTC/退出码/失败及最终seal；明确Codex-AI(Q1)，不代签kris。完整提交/普通推送/原生交接后结束。R1并行技术审查，G-DATA由S0在两项独立审核与main验证之后决定；training_authorized=false。
