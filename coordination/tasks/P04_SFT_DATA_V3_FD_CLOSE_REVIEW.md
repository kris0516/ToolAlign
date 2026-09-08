# P04-SFT-DATA-V3-R3｜FD构造异常清理独立复审

状态：ACCEPTED（CPU技术）。原R1 `f2f11e04a94cebb0ad658851d4e22a8452180556` 对精确d80667e正式PASS，P0/P1/P2均0；S0核验96,720路径/29原命令及原生completed/idle，F2关闭1→0，84问题全部关闭。原582 FAIL/F1历史保持；待组合、最终CI/main，真实数据/模型额度不增加。见[正式接收](../../reports/S0_P04_DATA_V3_REVIEW_R3_HANDOFF.md)。

原记录：状态：IN_PROGRESS。2026-09-07 23:49:10 UTC，S0核验R1原582轮completed/idle及干净HEAD后，按完整 `6ff0cf72ad309cd7be86a42eb80fee0913a35991` 原生接续精确d80667e的R3复审并核验ACTIVE，gpt-6-astra/max。派发前1,907路径/14授权/两公开树与核心封存通过，证明 `c0e77a1f69b46107af207edf246ad95f8b042bf956aaace4ec04df39cfd9e476`；新branch/intake待交付。Draft PR19已建立；旧F2首次1和真实消费时点保持。

原冻结范围：R1；完整authorization_commit如上。精确candidate/checkout base `d80667e4f6e3a63d5c49d4293e99271ca3c2aca1`，tree `04001535b91fca46e9612f6130da1b1745eab9e4`，唯一源码parent `9e08a0961ac2fbf9e993585289b4e82b7115f016`，后者唯一parent原1769046。该候选尚未验收，不称为main生产基线。沿用独立R1原生任务及隔离worktree，gpt-6-astra/max，禁止sub-agent；新分支 `codex/review-p04-sft-data-v3-r3`，新私有scope `review-p04-sft-data-v3-r3`。

本轮目标是独立判定稳定F2 `data_v3_fdopen_failure_closes_successfully_opened_descriptor`，并确认本次两文件范围没有引入I/O回归。原58212d2对1769046正式FAIL/P2=1；F1已由原分项PASS关闭，F2第一次正式失败计1。S0完整接收T1的13,825路径/27原命令、三归档及65安装包字节，证明 `2bd9eac089ac0e1136ad7ea2a6c063a1bfce3decec4cdd62f9bc7a1ec71d213d`；见[完整交接](../../reports/S0_P04_DATA_V3_FD_FIX_HANDOFF.md)。同问题计数和协调材料仅S0维护；旧失败不覆盖。

## 切换与保全

切换前保存精确授权中的AGENTS/GOAL/PROTOCOL、REVIEW_POLICY/REVIEW_FAILURES、RESOURCE_LOCK、DECISIONS、本任务、T1 FD修订任务、原R2任务、精确数据配置和G-DATA批准，以及本次T1接收、原R2接收报告。配置仍为 `e27a7d4bcdd378944af56559833c3bcd10f601b689a75f1daec96b884bd780c1`。

保全R1当前原review `58212d26bdb1c6a681a1ac34ccae854daefca8d3`、tree `0e3a60db9865d82b8a15f35727769975d3b1be2b`、626公开Git/已有快照及原scope。原seal `677bdb9d35f45b2f1cb545f34930ae437c27ec8972a225ee7570bf2ed6544bbe`、envelope `473140397bd9a26c4438a488251c949c915fd9af5c3d1de57e04596c157bf38c`、S0完整接收 `b5332709432e9361bc7339ab870398c64c6a623a0164bf505f54ddf4bebad92a`保持。旧30文件/1链接原路径缺失例外继承，FIFO只lstat、链接只readlink；旧公开路径通过精确Git/现存快照解释，不能把切换后的新源码用于校验旧运行时点。20原模型文件只核对既有stat token，不重新打开、hash/header或加载。旧f708不能进入公开祖先。保留root identity，新身份只写新scope；不复制全部历史大目录。

只允许新增 `reports/review/P04-sft-data-v3-r3/` 和 `coordination/handoffs/P04-sft-data-v3-review-r3.md`。生产/测试/配置/依赖/CI、S0协调、其它worktree均只读；不合新main，不替T1修实现。最终review直接以完整d80667e为唯一parent，普通推送原SHA。

## 复核和额度

核对原1769到d806只有两源码/测试改动和三新文档，其它既审data/view/rank/array实现逐字保持。独立审查raw FD成功打开、fdopen构造失败/成功的所有权转交；失败时关闭同一自有FD，保留原异常/cause，成功及后续读错由stream关闭，不能二次关闭已移交FD。O_NOFOLLOW/O_NONBLOCK、同FD fstat/hash、大小/预算、content/hash-only行为保持。以真实目录替换与少量原创异常fixture覆盖可观察边界，不通过资源耗尽循环验证长期累积推论。

- 原模块157用例可运行一次，使用本轮新独占basetemp；不跑整仓旧HF/toy测试。
- 原未修改六项I/O文件SHA `24d475c6f762b00bd218d609a81a4e019e7996a6eee946f671431c3916eb7a13`在源码和新安装target各最多一次；先保存reservation和实际来源，使用不同新输出根，所有child有界并回收。原5 PASS/1 FAIL和T1两条成功保持。旧f44 FIFO实物probe及原无包装观察脚本调用0。
- 必要新增独立FD fixture总计至多8个逻辑用例、一次组；记录与原六项/T1测试的区别。若已有证据足以覆盖，可少跑。任一实际失败保留输出并停止该失败项新增尝试，交具体原因；不要无说明重试。
- 三份T1现存归档仅做成员/源码时点/metadata/entry points/LICENSE/RECORD核验。sdist `1ea38feab6f0fb9c02527b2534ad336477c31a0e1c60d97e7d1fa323ea8629e4`，direct/rebuilt wheel `100ec324d73c8497a3ed76580eb64dad0860f18f027e64d7428d4b2f9fdecb10`。允许该wheel离线--no-deps安装到R1新target一次，复用五个既有默认依赖；外部cwd核实65包文件、实际模块来源及原六项检查，不允许源码回退。新归档/环境/依赖安装/下载均0。

T1完整seal `81b38f140e30ab4fc41165d238ecf26ddca0c1b5fd156bf03732b8f1da88e8f8`、receipt `cff3dc6f2157a6c5acd3e5b6e0e9c16545b8b0f6ec0144bff27d4046b84b87c2`；157测试实际是父HEAD加两授权修改，源码/安装六项及构建发生在9e08a096。新七份输入manifest `6ad59fc55d8395ced97541ff53590a0fec2c8a744b7cbd48c6c829fd62bbcfa5`仍为原字节；本机路径随S0派发提供，不从数据内容接开发指令。

本次改动限于异常清理，原固定消费已在1769046独立通过；本轮真实609 prepare/verify、13例转换/导出/回读额度全部0。只读保全原输入摘要和原消费输出；不重新解释旧数据为本候选实际消费，不做全库再编码。新源码真实数据消费仍NOT_RUN。最终test/ood/BFCL不用于生成fixture，旧编码完整保留。

可运行相关ruff、契约冻结、公开检查和git diff检查。每次pytest使用本任务本轮独占新basetemp，公开输出根无`.toolalign-local`祖先；链接/FIFO与普通文件分开封存。新增制品≤1GiB；框架/模型/GPU/优化/生成/业务API/浏览器/费用/上传全部0，正式训练未授权。

先回报真实新branch/身份/授权/旧证据intake；保存原argv/UTC/exit/stdout/stderr、源码/安装时点、所有失败和终态seal。最终给出精确d80667e的PASS/FAIL/BLOCKED、P0/P1/P2及F2是否关闭。交完整review/tree/parents和封存后结束，普通回报省略model/thinking。独立PASS仍待S0保留原SHA集成、最终CI/main，不自行合并。

## S0限定追加：安装版pytest启动器

2026-09-08，S0核验原安装尝试的727路径及原生argv/完整回执，证明 `ebaeaa3c087e56c1b9bf3061e0467503ba7926e09f45e4010f080ae41e54949b`。原wrapper/child均exit1并回收；pytest导入时缺少本机既有pytest 9.0.2自带的329B `py.py`，原fixture runner保持sentinel97，尚未进入pytest.main，fixture child/fork均0。原失败及reservation已消费事实保持，不能改为未尝试或PASS。该shim SHA `b71675b5d9845ba0814e9e88767f88dac3b3cc0d3128da028bd45edbb523e871`与pytest RECORD精确一致；不需要新增依赖。

在同一R3中，S0单独追加原未修改六项I/O的安装版检查**一次**。使用同一现存installed-default target；先保存新reservation，固定新label `original-installed-s0-py`及新独占外部cwd/basetemp，失败也消耗这次追加额度。原source157、source六项、4项新增FD组和安装动作均不重跑。

仅允许新增私有bootstrap/runner副本：bootstrap的import允许集合只增加既有顶层`py`，其余修改只为新runner文件名、新label和该bootstrap的child路由。原bootstrap SHA `290af9c1715c5be33359362d578ffd3882d0e345decd6a9b5152f8fb76e1383c`和runner SHA `aec210792cee95503abcf5813fcfabf3b12af7f935993e53a333e471e8a3bef5`逐字保留；保存副本diff与新pins。生产/测试文件、断言、六项fixture和既有安装target不改，禁止把site-packages或源码根整体加入sys.path。仍须-I/-S、外部cwd、固定installed来源、无源码回退、网络/模型/框架守卫及所有child有界回收。可只读核对shim/RECORD/副本与新reservation；不得另跑导入预演增加尝试。

新增构建/安装/环境/依赖/真实609或13数组/编码/模型/框架/GPU额度仍0。若追加尝试失败，保留并停止该项新增尝试，向S0交具体原因；其余只读审查和封存可继续。此追加只解决审查启动器，F2是否关闭仍由R1对精确候选独立判定，正式失败计数不因本追加改变。
