# P04-SFT-DATA-V3-R2｜特殊文件修订独立复审

状态：CLAIMED，尚未原生派发或激活消费额度。原P04-QWEN-MODEL-R1的bdebe4c正式交接已由S0接收，原生completed/idle已核验；等待S0发送本次完整authorization_commit。沿用独立R1任务及自己的隔离worktree，gpt-6-astra/max，禁止sub-agent。新分支 `codex/review-p04-sft-data-v3-r2`、新私有scope `review-p04-sft-data-v3-r2`；由S0派发完整authorization_commit。

精确candidate/checkout base `1769046468eb2ebfdd9e982ba4938833760e3fe0`，tree `1373bd4c838a1af395a1ede4f7c4d7029ffad271`，源码parent `53d86109f18e4131cff1ddcb905086892580d136`。原f3候选直接承接关系及原b99正式FAIL不可改写。S0完整接收证明 `6c7cbc37e690cb270d3b33d80e0934efe1b0881191cedb6ec65e2d239e3ae39b`，见[修订接收](../../reports/S0_P04_DATA_V3_NONREGULAR_FIX_HANDOFF.md)。[原审查范围](P04_SFT_DATA_V3_REVIEW.md)和[原正式接收](../../reports/S0_P04_DATA_V3_REVIEW_HANDOFF.md)作只读历史；原轮所有消费额度均0，不在旧scope重跑。

切换前保存完整授权中的AGENTS/GOAL/PROTOCOL、REVIEW_POLICY/REVIEW_FAILURES、RESOURCE_LOCK、DECISIONS、本任务、原R1任务、[T1定点范围](P04_SFT_DATA_V3_NONREGULAR_FIX.md)、[精确配置](../../configs/sft-data-v3.v1.json)、[G-DATA批准](../approvals/P02_DATA_V3.json)与两份S0交接报告。保全届时当前模型review和seal、原b99全部证据、旧FAIL/PASS、根identity与新scope身份。旧30文件/1链接原路径缺失继承精确清单及等字节封存，不能冒称原件已恢复；旧公共路径以其Git/冻结快照绑定。原FIFO节点一律lstat分类封存，不打开或hash。私有f708不得进入公开祖先。

只新增 `reports/review/P04-sft-data-v3-r2/` 和 `coordination/handoffs/P04-sft-data-v3-review-r2.md`。生产/测试/配置/依赖/CI、S0协调及其它worktree只读；不合新main、不替T1修复。review提交直接以完整1769046为parent，普通推送，保留原SHA。

本轮只关闭稳定问题 `P04-SFT-DATA-V3-F1`，并核验所改I/O基础函数的正常消费回归：

1. 原f3到1769仅两源码/测试修改和三新文档；固定配置仍为 `e27a7d4bcdd378944af56559833c3bcd10f601b689a75f1daec96b884bd780c1`。其它已审data/view/rank/array实现逐字保持，不重复扩展未变更模块。
2. 无writer FIFO及时拒绝，预检查后换成FIFO仍不阻塞；目录、symlink、正常文件content/hash-only模式、大小/hash/预算错误保持。独立原创小fixture和自有有界child覆盖可观察边界，不能以加长timeout代替修复。保留 `O_NOFOLLOW`、同FD fstat/hash/大小检查。
3. 原未修改probe `f44cc02cc066ad9f2befe1b11c27c92981ff77ae87cf83672c422e3118ff1c7d`在新源码和新安装目录各最多1次，先落reservation，使用独占新根。证明及时拒绝、无需writer释放、child回收及实际consumer路径/hash。T1两次成功和R1原失败都保留；任一实际失败停止该项新增调用并交具体原因。
4. 核对T1实际三归档、完整成员/源载荷、metadata/entry points/LICENSE/RECORD及构建源码时点。直接wheel与rebuilt `101eccd619e16805230cfdb8b440d4f19858020ae5d6c1d3d4068b0d31fa1ecf`，sdist `cabbc8a37151f767925d9f83fd05b9adab93c88798db11fb298135b84b55d3de`；seal `9a23a53af2ebfd959c6c2d866b4fc24203439867ba7fe7148a60601396633768`、receipt `baa135ee31cf28cd43c16a00ed90516a1c5975715ca1f4a0e0ea4e54b84f6447`。允许一份已绑定wheel离线 `--no-deps` 安装到R1新target，复用现有5个默认依赖。新归档/环境/依赖安装/下载0。
5. 当前修订须有新consumer证据：原固定manifest `08e865ff98bd476c94153033bc192664d72cee64443184576532c0289a610dd7` 的609成员不变，只在新安装target允许1次 `prepare_v3` 和1次13例转换/导出/回读完整组。先冻结reservation及consumer源码、配置、固定输入；外部cwd无源码回退。对四view的7,928原行/rank和13例两engine完整26记录逐字段/类型比对既有原材料与原独立结果；完整ID/mask/causal/padding/EOS/token_texts逐项不变。新consumer hash和本次运行时点单独登记，不能把旧bfdf/f3导出改名为新消费。若失败保留原输出并停止追加实物调用，请求S0明确范围。

intake只读核验T1完整seal/26原命令与最终exit、两原probe和所有失败、7反例副本及原固定609描述；原13序列保持既有编码，最终test/ood/BFCL只hash、不用于造fixture。实际数据build/tokenizer/renderer/encoder/decoder/框架/模型/GPU/优化/生成/业务API/浏览器/费用/上传全为0；已有G-DATA批准不构成训练授权。原当前修订真实消费NOT_RUN事实保留，新独立消费须另列。

仅相关CPU测试、必要独立反例、ruff/契约/公开检查；原147用例可一次运行，不重复整仓历史HF/toy或原27全部用例来凑计数。pytest使用本任务本轮独占的新basetemp，含public-output假设的根无`.toolalign-local`祖先；普通/链接/FIFO分开封存。新增制品≤1GiB；无S0运行任务或物理GPU租约授权。

保留实际argv/UTC/exit/stdout/stderr、源码/consumer时点、所有失败和终态seal。正式给出精确1769的PASS/FAIL/BLOCKED、P0/P1/P2及原F1关闭与否；同问题第5次规则由S0维护，当前为1，重复检查/辅助错误不增加轮次。原生回报完整candidate/review/tree/parents和私有证据后结束；普通消息省略model/thinking。PASS仍需S0原SHA整合、最终CI/main，不自行合并。

本次切换前精确保全：当前模型review `bdebe4c2bddf927995a6c15124fab75ad04ba5de`、tree `9cfaad151f216fb3298a899d7a0fb2399e393a38`、628公开Git/冻结字节及完整scope；seal `17fe9b621357eeaea31b31483be55164fd26d1b8a017760a433fd4a301cf9671`、envelope `a8e4f84de6ff628d28b5aca9865da7f17b1f4e33d74a0ed44dfbc9aa2db35196` 和S0接收 `28593f448e1197711a6a9f9d8604c58d7c30ced54f7d0890812e7eb0771da890`。原23命令/89,807封存文件、1,664链接与4个lstat-only FIFO保持；20原模型文件仅核对旧记录和stat token，不重新打开或调用模型API。旧公开当前路径切换后依原Git/已存快照绑定；保留原30文件/1链接缺失例外，不将原模型proof中的路径转为本数据轮新增读取或调用许可。保存本次S0正式模型接收报告；完整私有实物位置随原生派发给出。
