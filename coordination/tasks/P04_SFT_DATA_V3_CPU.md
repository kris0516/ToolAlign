# P04-SFT-DATA-V3-CPU｜冻结v3数据与审阅数组衔接

状态：CHANGES_REQUESTED。原R1正式 `b99a644e3ac0386f5ebe55cfd32e51b99e89781a` 对完整f3判定FAIL/P2=1，S0完整接收65,185路径/25原命令；唯一P04-SFT-DATA-V3-F1首次计1。修订1769046已交付，完整接收/独立复审待完成，见[正式接收](../../reports/S0_P04_DATA_V3_REVIEW_HANDOFF.md)。原交接记录：T1 完整 `f3b7f1a1abb23cce3bdccb74ddc6d2e0477bb2aa` 已普通推送/原生 completed/idle；S0 接收 10,935 路径/40 原命令，见[完整接收](../../reports/S0_P04_DATA_V3_CPU_HANDOFF.md)。原派发记录：T1；已于2026-09-07 17:45:52 UTC按完整授权`0fa77e228021091e357505a0e81a5d3ba0777928`原生派发并核验新轮ACTIVE。17:55:20 UTC，S0对新branch、612基线、20授权和609输入完成intake核验，7,010路径证明e6d4c83e；完整候选/独立审查待交付。code_base为已合并`48be4352bbad53ced5af84186edac036dd0ff2ca`，其生产源码与已验证PR15 main90c4da9保持；G-DATA已按[固定v3批准](../approvals/P02_DATA_V3.json)通过。authorization_commit由S0原生消息提供完整SHA。遵循plan-v0.1、coordination.v1、toolalign.contracts.v1和角色保留Action JSON v1，gpt-6-astra/max。

沿用T1独立App任务，gpt-6-astra/max；branch codex/p04-sft-data-v3-cpu-r1，私有scope p04-sft-data-v3-cpu-r1。先保存完整授权中的任务、S0精确配置、AGENTS/GOAL/PROTOCOL、REVIEW_POLICY、ADR及v3/Q1/R1/main验收；保全原4baa367方案、f7326d1固定toy及此前已封存Git/运行/根identity。只在自己的worktree切换新base，新identity只写新scope。

目标是把已验收v3的四个选择view和固定13例审阅数组接入现有SFT数据／collator。只新增 src/toolalign/training/sft/data_v3.py、tests/training/test_sft_data_v3.py（必要时同名小fixture目录）、reports/experiments/P04_SFT_DATA_V3_CPU.md/.json和本包handoff；S0提供[精确CPU配置](../../configs/sft-data-v3.v1.json)，文件SHA `e27a7d4bcdd378944af56559833c3bcd10f601b689a75f1daec96b884bd780c1`。唯一配置复制例外：从完整授权逐字节复制该文件至自己的相同公开路径并提交，禁止改值；base内尚无此新文件。保持原data.py/config.py/CLI、collator/plan/model_io、v1/v2/v3生产器、toy/runtime守卫、契约、锁文件和构建配置原字节。不要将旧v1配置hash放宽为任意文件；有必要改公共组件时先向S0提交具体要求。

1. 新入口 prepare_v3。已验收v3 API为 quality_exclusion.verify(output=..., config_path=..., input_root=...)，只读验证会通过 bound_inputs/stable_artifacts重建期望字节，无需调用build或写新全量数据。先严格读取S0精确CPU配置/输入清单，验证v3及全部祖先成员的字节/大小/hash/类型和R1/Q1/S0批准绑定，再构造四个不可变SelectionView。新selection manifest的配置在parent_training_config，各profile/split有效计数位于summary.effective_selected_count；旧v1顶层config/selected_count字段不可套用。可复用view_from_records的已审kernel，但它不验证v3质量祖先，须在外层先完成。已验收selection file SHA d765493c156d047cfaadce9c49e7edf25b973907d6a764f3272090786693efbc、training-binding SHA588c94b6bed580f6ddf0e30eef4442915c24a0dc2ad40f33b2d8772cd4a29059；本次main验收已确认两文件保持原字节。

2. 身份与rank。Example原JSONL行先按原字节校验；view内规范化JSON是新内存表示，不冒充原行。sidecar selection_rank=连续v3，parent_selection_rank=原v1，previous_selection_rank=已验证v2；按Example ID、父sidecar和原稳定ranking连接。有效7419/230、formal5938/213、smoke1583/194；必须分别与当前manifest实际值及四组身份hash匹配，不补到6000、不重排、不晋升staging、不变更split/group。只创建train/validation view；最终集/BFCL只做既有完整制品的hash和隔离元数据检查，不解析为内容view。冻结D1输入中旧P02-Q-081 CHANGES_REQUESTED台账是历史来源；新的S0关闭/批准材料另绑，不回写D1历史输入来让它显示PASS。

3. 固定13例数组衔接 rebind_review_arrays。输入使用Q1 r5已审核的完整当前native/reference材料；两engine26记录表示13个唯一例。逐类型核对Example/Action/messages/audit、case与profile/rank、quality revision、P/C文本与所有ID/attention/loss/causal mask、EOS/右padding和含padding的全部token_texts。通过既有Sequence/Batch类型和collate_sequence从已封存数组重新构造Batch，逐位置与原审阅padding一致；该操作为CPU数组转换，0新tokenizer/renderer/encoder/decoder调用，不能写成再次分词。旧11例原source/run时间、代码和Q1判定沿原继承链保存，新2例沿原4次D1编码/Q1 r5实际mask结论保存。3原创protocol例只在材料诊断集合，不能进入任一训练/验证view。

4. 只导出已冻结的固定材料数组。允许一个确定性的有限导出/回读接口（名称由T1在此窄范围内决定），写13份或一个有序容器和manifest，绑定Example/原行、profile/rank、固定原sequence与Batch、Q1判定、producer/source epoch和CPU消费者身份；明确REVIEW_ARRAY_ADAPTATION_ONLY、new_sequence_calls=0、optimization_authorized=false。原生JSON，拒绝重复键、NaN/Infinity、bool/float替代整数和symlink/越界路径、覆盖已有输出及不完整发布。回读在框架导入之前只返回已验证不可变Batch。无需通用cache或全数据导出平台，不为future capacity提前编码23例，也不暴露可任意扩展的实数据编码入口。

5. 计划输出。复用epoch_plan/validate_plan给出smoke197×8+7=198、formal742×8+2=743的完整一遍计划，实际更新0；四段完整评分计划属于后续原生runtime，本包不改旧两段validator。metadata/report如实写Codex-AI(Q1)审核身份，原native training、browser实显、0.6B1536／1.7B2048容量仍NOT_RUN。所有旧training_authorized=false原样保持；本包准许CPU消费不等于优化或正式训练许可。

最小有效验证：原创小fixture针对错误v3/selection/training-binding/审核seal或旧配置冒充、删项/重复/错误原行、v1/v2/v3 rank错位、同group误过滤/旧排除来源回流、错Example复用、bool/float数组或rank、EOS/shift/pad错位、protocol/staging/final split越界、输出覆盖/不完整发布、错误consumer与可变view；确保失败在任何生产编码或模型加载前。实际固定数据做一次prepare和一次13例转换/导出/回读，比较全部数组；这不是全量数据build或新编码。为已通过且未变更的旧model/toy/HF测试不追加大批重跑；常规CPU测试和新增有效反例、ruff、契约/公开扫描、实际sdist/wheel/rebuilt wheel及默认安装新入口按精确源码记录。R1独立新增反例并核对这些实物。

资源：现有stdlib/默认CPU依赖即可，新增制品≤1GiB，源/安装各限一次实际固定数据prepare（只读）、一次完整固定13例转换；一个新的pytest临时目录，失败修复后另存新目录，不复写旧证据。真实tokenizer/数据build/框架/模型/GPU/优化/生成/业务API/下载/新环境均0，0全选集重编码。保存实际argv/UTC/退出码/源码时点/失败、完整候选及seal、实际归档/安装回执；不得执行数据样本工具。测试中人为构造的原创小fixture与真实材料分开计数。完整提交、普通推送、原生交接后结束，S0再派独立R1，主干验证后才能规划真实runtime实现。

固定输入 manifest SHA `08e865ff98bd476c94153033bc192664d72cee64443184576532c0289a610dd7`，609成员：603只读引用与6精确副本，副本320,921 bytes。包括D1原347输入加原manifest（348项）、实际v3输出30项、原Q1的294输入中定点裁剪211项、Q1正式判定/两级seal10项及S0/R1配置/批准/接收记录10项。完整绝对路径与文件map仅在S0原生消息和私有输入中；不要公开。两原D1根仅调用已审只读verify，不添加文件，不复制后改写其旧台账。当前材料/原材料及原运行在给定map中，任何出处或proof内的历史路径都不扩大授权；不要求旧可变公共路径仍等于旧版本，而应使用精确Git/已冻结副本/既有seal。全部具体消费文件必须逐字节校验后解析。

S0批准文件SHA `1edb1e889b91dbde5dc6208b8dff2afdaa4b4a20a0ba5c166e9b55750429ec44`，当前关闭台账SHA `022356d8dc6fdf273804d0f78e58416677799e303b0dc1b6a46b1e7b1ffcb992`。R1原dbd11d03e69c650efdb330f79ec380dd9914fa89，Q1原7941f1f56519ea2eac437c669ac2c6445a0329f6；完整seal/receipt和四view身份hash均在精确CPU配置及输入manifest，不能把旧v1 pending表当作当前批准缺失，也不能把旧pending字段改为true。

本包数据/审核入口只接受该S0精确配置和固定输入manifest；可自行选择有限函数签名，但不能新增允许任意数据/任意review seal的生产旁路。原只读verify会在内存重建期望字节；这不等于重新物化数据。祖先final/ood/test payload只hash，禁止内容view、重抽样及按其答案写fixture。固定13例转换可以复用Sequence/Batch与collate_sequence；不得调用collate_selected、training_sequence或任何tokenizer回调产生新ID。metadata中的实际trainer对应状态仍NOT_RUN，CPU准备结果另报。

切换前保全原4baa367的556公开Git/快照、161当前scope文件、5,744原接收路径和197原链接文本；S0保全SHA `8644138a91d76281c4be89b87ef308c5431e4fde254bd8b509f99b025d30a259`。其中2个旧测试链接当前悬空且未列为应保留目标文件，保留其原链接文本；原seal没有记录旧目标存在性，不补造。该记录不允许新增输入symlink。准备证明 `0526b064a3a606416edd7aa84e93bbb5ad4bc202824aa4951264e95350bcc492`；[分发准备](../../reports/S0_P04_DATA_V3_CPU_DISPATCH.md)。T1旧轮原生completed/notLoaded、新分支尚未建立，不把准备写成实际派发。

保存授权中的20份文件后切换：AGENTS、GOAL、PROTOCOL、REVIEW_POLICY、REVIEW_FAILURES、RESOURCE_LOCK、DECISIONS、本任务、configs/sft-data-v3.v1.json、configs/data-quality.v3.json、configs/training-data.v1.json、P02_DATA_V3批准、S0 v3主干报告、S0 Q1 v3接收报告、本次分发报告、原runtime方案.md/.json、S0方案接收报告、原R1 v3 REVIEW.md及原Q1 v3 README.md。首次回报精确任务/branch/base、授权副本、输入hash与保全结果；新identity只写新scope，保留根identity。当前最多一个实现（T1），D1/E1/R1/Q1无新范围，GPU无新许可。交接文件为`coordination/handoffs/P04-sft-data-v3-cpu-r1.md`；完整候选、原始失败、实际source/installed验证和seal交付后结束，由S0接续独立R1。


固定复测补充：S0于2026-09-07 18:48:32 UTC核验T1已提交checkpoint `bfdf2a256065d5396e6f7a4860fd7c7506f5c278`、两处输入绑定修复和原证据，373路径/12原命令证明 `e8668110c9412d3bc5d1015a38efc2d7ea94b9ec48b1d106ed759b80642b50d0`。按[精确CPU复测批准](../approvals/P04_DATA_V3_PREPARE_RETRY_R2.json)，source/installed各追加一次prepare，总尝试上限各2（含原失败）；两边原13例转换/导出/回读额度仍各剩1。只允许一次新三归档和新default target，旧三归档/target/失败/保留号不覆盖；生产与配置严格绑定bfdf2a2，真实模型许可保持0。此批准由同轮完整S0原生提交激活，不是candidate验收。

上述一次新三归档/target已由T1完成并经S0字节核验，证明 `c2c8fcc68ede5e994d5060692c316abf997cb03faa9138b39a6f5514302287f7`；本批准剩余build/install为0，使用现存r2 target执行所准installed prepare。
