# P02-QUALITY-EXCLUSION-v3｜排除一处新来源问题并复用已测材料

状态：CLAIMED，D1；完整输入/配置已冻结，尚未原生派发。依赖PR14的CPU主干VERIFIED与Q1原8a738ab正式交付。R1后续技术复核、Q1实际处置/材料验收与G-DATA仍待完成。

- code_base：已验证main `d3e56f68ebd67cc576d912b6f06636682b4170ab`。
- 新branch：`codex/p02-quality-exclusion-v3`；新私有scope：`quality-exclusion-v3`，只在自己的隔离worktree操作。原1c47候选、旧分支和全部封存保持；不pull/reset/rebase原分支。
- 从S0完整authorization_commit先读取本任务、配置、AGENTS、GOAL、PROTOCOL、REVIEW_POLICY、REVIEW_FAILURES、ADR-0025、Q1接收及PR14主干报告并留副本，再切换code_base。
- 契约保持plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / Action JSON v1。新实际身份写新scope，不覆盖旧根identity。

固定输入manifest SHA `ebbaf56bbb5730b5d31eca195d5ac7772d148ff876fc96be1c1c5dbbadf51e06`，347项：253精确副本、90已存在只读引用及4份S0派生元数据，副本合计23,887,060 bytes。私有路径由S0分发；整目录复制到新scope，引用逐项核对hash和类型，exact_copy的original_path只作出处。`parent-inputs/`完整保留原217项manifest/副本及60引用；`parent-revision/`固定已验收v2的30份原制品。不得把变化中的其他对话输出自行加入输入。

唯一配置例外：将S0的`P02_QUALITY_EXCLUSION_CONFIG.v3.json`逐字复制为`configs/data-quality.v3.json`，SHA `784aa699026ebb149d720745f461a9cfd493036cd0bf09a72702a81e2db45261`。允许新增`src/toolalign/data/quality_exclusion.py`、`src/toolalign/data/quality_exclusion_materials.py`、`tests/data/test_quality_exclusion*.py`、`tests/data/exclusion_cases/`原创小fixture、`reports/data/quality-exclusion-v3/`及`coordination/handoffs/P02-quality-exclusion-v3.md`。其余已有生产模块/常量/配置/测试、协调文件、依赖与打包配置不改。

P02-Q-081仅处理一个完整来源：排除其两条原决策，包括错误历史之前的目标；当前两个Action的原PASS及历史UNKNOWN子发现保持。S0冻结的delta SHA `35ae90915e26ad8c25fd1d2d70cd89bfebfaee038e2f617178a049a4675b57e4`绑定完整source/Example/Action/messages/lineage、Q1原判断/seal与当前issue事件。核对原83来源/101决策处置和3项恢复不变，合计84处置来源、81来源/100决策排除、3来源/3决策原字节恢复。未经审阅的其他来源不写成质量认证。

实现有限v3 wrapper，复用已验收v2的固定parent验证与适用纯函数（如`adjudicated_view`、`filter_selection`）、共用formatter/sequence/pad，不能改旧常量、全局monkeypatch或复制整套v2生产器。输出明确v3 manifest/quality revision、完整身份与来源追溯、有效数据/lineage、选择/训练绑定和对v2的delta。仍从原始Example及原6013/1600、217/197名单过滤；保留原逐行字节、group/split、原parent rank及相对顺序，不补选、不重标。新sidecar的selection_rank连续，parent_selection_rank仍是原v1 rank，previous_selection_rank保存v2 rank；不能混称两个父层。旧staging继续引用且不晋升。

| 集合 | v2 | v3预计 | 本轮排除 |
|---|---:|---:|---:|
| 有效train | 7421 | 7419 | 2 |
| 有效validation | 230 | 230 | 0 |
| formal train | 5940 | 5938 | 2 |
| formal validation | 213 | 213 | 0 |
| smoke train | 1583 | 1583 | 0 |
| smoke validation | 194 | 194 | 0 |

以上为固定身份投影，实际输出后再登记结果；formal较原6k计划少62条，按ADR-0025记录数量偏差。新训练绑定明确training_authorized=false、真实trainer消费NOT_RUN，原SFT consumer另由T1适配。

材料继续用原`choose_review_cases`规则：固定13例由11旧例与2新例组成。两个被选例替换不等于两个来源被排除；另一旧PASS例只是失去代表材料位置，仍保留训练资格。按Example身份映射旧记录，不能按变动后的case编号错误复用。11旧例的完整sequence、padding和token_texts逐字/类型绑定到原两engine记录；只更新本轮case、rank、quality revision及静态HTML等绑定。保留原编码命令、时间、源码与旧run身份，明确新发布不是重新测量。

两例新增身份已冻结，完整两个train来源含3个有效决策/8原始turn；Q1按独立任务先审来源。D1可先实现CPU过滤、选择冻结、静态复用和适用测试；**收到S0包含精确Q1结论的同轮放行消息后，才运行这两个新例的编码。** Q1意见不自动变成D1新输入或改样许可。本轮每engine仅2个新例，合计4次新sequence生成；来源中第三个未被选中决策仅供Q1完整语义审查，不增加编码。固定11旧例和3协议fixture不重新编码。所有新材料判定栏空白，Q1后续核对实际v3排除及完整13例绑定；页面实显仍NOT_RUN。

验收：两份新目录的完整v3数据构建确定性一致；验证整来源两目标均隔离、同组其他来源和既有恢复保持、原/上一版rank明确、无补选/annotation泄入；配置/hash/来源/Example/判断/issue/数组数值类型替换及final split越界均拒绝。材料重点测错Example复用、旧revision冒充新revision、错误parent run、完整sequence/pad/token_texts替换及越额编码，失败不得留下可误认成功的manifest。使用原创小fixture实现负例，适用默认CPU回归及新定点测试；已验收且本次无关的427项HF/历史训练大组不重复。Ruff、契约冻结、公开扫描、diff和新sdist/default wheel/从该sdist重建wheel、一次默认隔离安装验证新入口及来源绑定。每项记录实际命令、执行源码时点、退出码和失败，测试/数组/安装分母不混计。

新增私有制品≤1GiB，完整v3数据构建最多2次，实际新编码仅上述4例；预算失败或必要共享改动先报S0，不自行扩张。只用现有CPU环境，Torch/TF/Flax禁用、离线并核对未加载框架；无新持久环境/依赖/下载、全库8228重分词、模型/GPU/训练/生成、外部API、浏览器重试、费用或上传。heldout/test/ood/BFCL仅hash/隔离元数据，不作语义、筛选或训练依据。

切换前核对原1c47的492公开文件Git/已存快照、旧completion与全部私有制品/链接，后续新checkout的公共路径按D3解释；不谎称旧公共路径仍原字节。保留所有旧失败、冻结input和原encoding epoch。最终交接完整candidate SHA、运行和封存、NOT_RUN；普通推送新分支后结束。D1不修改issue台账、不自己签PASS、不合并main或放行G-DATA/P04。
