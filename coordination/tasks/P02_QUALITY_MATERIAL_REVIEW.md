# P02-QUALITY-MATERIAL-REVIEW｜修订后16例的委托AI审阅

状态：IN_PROGRESS。S0已于02:14 UTC按完整eca077730648b91c03781306270356ddd70662ac原生追加，显式gpt-6-astra/max，并核验E1原轮仍ACTIVE；追加输入intake待确认。作为当前P02-QUALITY-AUDIT的精确追加输入，不重建任务、分支或改动已冻结180来源名单。

- owner：E1；现有独立Codex任务/隔离`work/p02-quality-audit`，gpt-6-astra / max，禁止sub-agent。
- 原code_base：`86b80bada50ac7c8f4b3910e3831a397ed65a853`；原授权`2aa0cf4a756e78d32cf10130edbe6d0e3925bf3a`保持。
- 追加authorization_commit：由S0实际原生消息给出完整SHA，先保存本任务/配置/ADR-0022的私有副本。无需merge main或切换当前已提交审计代码。
- 只读材料生成代码：`1c90ce0ba5f505e4ca4e7118012c351c5e9dff2e`；数据修订模块`53bf6bd617a454c022fdd03c09276b162df1f1fa`。这是材料输入身份，不是D1整包或R1验收。
- 契约：plan-v0.1 / coordination.v1 / toolalign.contracts.v1。S0配置绑定全部新manifest/原来源和上游数据修订身份；本机路径只在私有分发词中。

## 顺序与范围

先将原32来源的独立初判封存，再阅读本包的staging说明或修订内容，避免影响原轮初判。当前已收到E1完成原32独立初判及随后对照的交接，本包仍须核对其实际seal。新增180来源/200决策的原冻结名单、排名、模式与分母不变；本包单列为材料复核，不能把重叠来源重复计入新随机/定向分母。

精确输入为两个已有CPU tokenizer引擎对同16例的新完整记录：10个有效train原例，3个原创协议例，2个直接重标候选和1个受影响后继前缀。S0已核对两引擎记录逐值相同、来源/选择/修订绑定和全部mask/shift/EOS/padding；这是结构交接核验，没有代填语义。原CSV16行的审阅列全空，必须保留原件。

E1在自己的私有目录复制空白CSV并填写`reviewer=Codex-AI(E1)`、`semantic_verdict`、`token_mask_verdict`、真实UTC和逐例理由；允许值为pass/fail/unknown，不写kris本人或R1签字。两种判定分开：正确数组不能使错误工具调用或无依据参数获得语义通过。

对10个真实train材料核对完整原来源、原工具声明、目标及历史前缀；同来源全部有效决策一起审，来源判定单列。可复用自己已封存且身份完全相同的原来源审阅，须指出依据及复用范围，不能假定旧AI的pass就是E1的新结论。严格按已绑定assignments和实际规范化train定位，禁止读取或展示heldout语义。原协议例按原创fixture判断，独立标记非训练数据；不要求其在原语料中有来源索引。

对三个staging例核对实际新Action/ModelInput、new ID、annotation parent、未变source revision/group/split与原草稿是否一致；重标动作本身、继承观察、后续条件链分别说明。旧合成观察仍为未验证，不能因数组或参数修正宣称外部执行成功。即使直接候选获语义建议pass，`enters_effective_training=false`仍保持，本包不晋升任何候选。

token/mask审阅使用已封存P/C、完整IDs与padding数组、token文字和来源绑定；完整核对目标Action、监督位置、next-token shift、prompt/padding排除、单次追加EOS和分母。两引擎既有实际运行是输入，新增分词/模型/框架运行均0；不以静态HTML读取替代实际浏览器显示。浏览器实显继续NOT_RUN，不重试或改用其他入口绕过既有拒绝。

## 所有权、输出与结束

公共允许路径仍限`reports/data/quality-audit-r1/`及自己的`coordination/handoffs/P02-quality-audit-r1.md`；私有新增目录与输出由E1自行命名。D1目录、原review/material CSV、封存数据、生产代码、公共配置/协调看板只读。将追加结果并入本轮最终交接，清楚区分原32复核、新180来源审计、本16例材料及实际独立来源分母。

交新的填写CSV、逐例判断、来源级问题与全决策追溯、原输入/新输出seal、实际命令/退出码/hash以及FAIL/UNKNOWN/限制。新问题只作S0待裁定提案，不直接修改D1或已封存规则。材料中若发现新的有效train来源问题，先封存精确身份/证据回报S0；S0再冻结整改扩展。本包与原审计合计仍只有一个E1实现任务，保持原累计1GiB私有制品上限、无新环境/下载/费用/GPU/API。

完成精确追加审阅后继续原180批次并最终正式交付。G-DATA、真实模型容量、P04训练和完整P00–P09都不由本包放行；training_authorized=false。
