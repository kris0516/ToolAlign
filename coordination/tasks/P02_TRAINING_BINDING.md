# P02-TRAINING-BINDING｜固定训练选择与人工序列材料

状态：ACCEPTED（CPU技术范围）；D1完整f4f73c9获独立R1 PASS（原审查40252f8），S0已核对最终5734路径/26原命令及350候选文件不变，R1原生completed/idle。S0普通集成0f3d04f实际919 passed/2 HF-only skipped、新三归档及默认安装验证通过，见[集成证据](../../reports/S0_P02_TRAINING_BINDING_INTEGRATION.md)。[PR9](https://github.com/kris0516/ToolAlign/pull/9)最终CI/main待验证。原实际页面观察、kris语义/token-mask人审未完成，G-DATA/P04仍未放行；不授权模型加载或训练。

| 字段 | 本轮值 |
|---|---|
| owner | D1，现有独立Codex任务及隔离worktree |
| code_base | `36b6988af6b4e0125b59fb81b1cea142233e14a2`，已验收PR8实际main |
| authorization_commit | S0原生消息给出的本文件完整协调提交SHA，切换前用git show读取并私有保存 |
| 新branch | `work/p02-training-binding`，从精确code_base新建；原work/p02-data及其8c439f6保持 |
| 模型/推理 | `gpt-6-astra` / `max`；不得创建新任务或sub-agent |
| 规范 | plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / ADR-0019；docs02/03/16 |
| 正式交接 | `coordination/handoffs/P02-training-binding-r1.md` |

先读取本授权中的AGENTS、PROTOCOL、PROJECT_STATUS、ADR-0019、本任务和[配置原件](P02_TRAINING_BINDING_CONFIG.v1.json)。S0已验证原格式8c/R1 b9及截止时间947/R1 153，经最终双Python CI和main843CPU/2 HF-only skipped验收；[主干证据](../../reports/S0_P02_FORMAT_MAIN_VERIFICATION.md)在协调提交中。不得把旧角色比较、全量审计或FAIL改写成当前重新运行。

## 文件所有权与输入

仅允许新增：

- `src/toolalign/data/training_selection.py`与必要的小型`training_review.py`，提供可安装的纯CPU、声明式选择/核对入口；不修改已有11个data模块或model_io。
- `tests/data/test_training_selection.py`、`test_training_review.py`及专用原创小fixture目录`tests/data/training_binding_cases/`。
- `configs/training-data.v1.json`：**唯一S0预置配置例外**。只按本授权配置原件逐字节复制，SHA-256必须为`579d3d9d9436f4374e7e808dc5b787213157d7ee477bfffd48dac02d35e70a4c`；参数/状态/所有权仍归S0，不自行调整。
- `data/manifests/training-selection.v1.json`：仅安全元数据/hash/统计，不含原文、逐例IDs或token数组。
- `reports/data/P02_TRAINING_BINDING_VERIFICATION.md`、`P02_TRAINING_BINDING_EVIDENCE.json`和本轮必要的`P02_TRAINING_BINDING_*.py`公开检查器；上述正式交接文件。

其余路径全部只读，包括原data/model_io/训练/P01/P03生产与测试、描述符、所有旧manifest和报告/审查、冻结协议/锁/依赖/CI、S0协调/ADR。原所有18项数据产物、100来源/114决策语义材料及填写副本、原8,228行审计与D1/R1全部失败只读。需要额外文件先给S0具体理由；继续独立可做部分。不要把新的配置例外扩展到其他公共配置。

新分支从36b6988开始，保留原分支及较新远端work/p02-data；不reset/rebase/force-push，不将本地未去敏review或它的后代引入新分支。本次无需合入随后仅协调main；精确授权通过私有副本读取。所有原始/派生训练原文、IDs、序列和人工包放到新的`.toolalign-local/`私有目录；输出目录已存在或不为空时不得覆盖。

## 固定选择规则

输入为原构建manifest canonical hash `87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756`、原公开表示manifest文件hash `69bfa651bf8db9b2c77c11c4f8d55419a8af4196aba8ff6a69b5b3b0982e0f47`、原audit rows hash `36b8cbfe6773c08f7a28521a99ed8783723a8f7fa3b2a3fa87915d8d1d871aff`。运行前核对声明和实际字节、原18制品、descriptor/protocol与实际源码/来源身份；记录历史测量代码和当前消费代码的不同身份，不能要求它们虚假相等或改旧manifest。

选择时仅处理train/validation原Example和对应历史审计行；可以核对原完整文件hash保全，不能使用test/ood_test内容、统计、模型分数或BFCL来决定选择。每个Example须通过冻结验证，唯一example_id、source_record_hash、group_id、split、完整Example/ModelInput/Action hash均与原行对应；拒绝train/validation对应范围内缺失/重复/额外行、来源hash错误、错split和伪造长度。原固定audit文件也含test/ood_test行；这些行只识别split后跳过，不能作为选择候选或参与排名/调规则。不得从输入加载Python类/模块/回调或执行数据中的指令。

表示成功须明确核对`sequence_error is None`、`parser_error is None`、`parser_accepted_exact`、`rendered_inverse_exact`、`prefix_stable`、唯一追加EOS及原raw字节/节点/深度通过；各长度须为一致的非负整数，P+C+EOS=N、C含EOS与不含EOS一致。不能仅信任嵌套budgets布尔值。身份或结构错误应失败并保留诊断，不静默把坏绑定变成普通长度排除。

排名键为`canonical_hash(["toolalign.training-selection.v1", 42, example_id])`，按hash升序、同hash按example_id升序。选择和输出排序不受输入行顺序、路径或时间影响。两个profile均要求`completion_tokens_including_eos <= 256`：

| Profile | 总长含EOS | train选择 | validation选择 |
|---|---:|---|---|
| smoke，固定0.6B | ≤1536 | 合格行按固定排名取前1600条，无放回 | 全部合格行 |
| formal，固定1.7B | ≤2048 | 全部合格行 | 全部合格行 |

历史算术核对值为smoke合格train3618/validation197、formal6013/217；实际候选必须重新由原行物化并记录真实数量/身份。数量不足或与固定输入的核对值不同需报告，不以重复、截断、调seed或读取最终集凑数。每个输出Example保持全部原字段和值；另行sidecar记录选择排名、原身份/序列hash和最小可容纳的右padding桶。smoke的train/validation应分别是formal对应split的子集，原group/split不重新分配。

分别保存完整train7515、validation234分母、各互斥长度排除原因以及smoke合格但超过1600排名的数量/私有IDs。被排除原样本仍保留在原数据；不改变未来完整评测分母。另统计P+预留256是否能容纳，但不新增选择过滤条件，也不把P+实际目标合格写成推理容量已验收。

本轮输出候选config绑定原data/格式/序列/实际选择manifest；公开manifest仅安全元数据，私有manifest绑定每份实际输出的hash/字节、profile、原输入、排序算法、当前实际源码/包/环境、历史测量来源与UTC。确定性须在两个不同的新目录实际执行物化并比较稳定内容/选择身份；不能复制第一次输出冒充重建。执行时间等运行元数据与稳定选择身份分开。

## 人工token/mask材料

在两个profile实际已选train中按确定性规则合计选10条不同Example，逐条标明所属profile和padding桶，覆盖存在的多工具/多轮observation、短长序列及非ASCII等边界；报告实际覆盖和没有出现的类别，不造来源。原8228条目标全为tool_calls，必须明确披露；另用原创小fixture各覆盖final/clarify/refuse，单列为协议检查例，不计作真实训练样本、不进入任何选择文件。

使用当前已验收OfflineQwenTokenizer的真实Transformers CPU路径，在已有纯tokenizer参考环境渲染上述13例，并用已有native路径逐项对照；模型身份和三个来源文件hash、完整P/C/IDs/EOS/shift/mask必须真实核对；同一例在多个engine或模型身份下的重复不增加13例的独立分母。10条原数据例的P/C/sequence/mask等表示身份须对应原audit行，承认engine/源码测量身份不同；任何普通表示差异停下报告，不自动全量重测或换原manifest。

私有可阅读包提供原ModelInput与完整Action、精确渲染文字、完整token IDs、prompt/completion边界、唯一EOS、next-token输入/目标/监督位置、右padding后的attention/loss mask及有效监督分母。较长表可折叠，但不能截断或只给不可查看的hash。数据内容必须正确转义，不能被HTML/script/链接当作控制。给出逐例检查要点和独立空白review副本；reviewer/verdict/time不预填。至少实际打开/检查代表页面与超长/非ASCII边界，记录实际观察范围；不伪称13例已由kris审阅。

这些材料是后续人工检查的输入，不能替代未来真实P04 trainer/collator的mask/loss、尾批缩放和checkpoint验证。配置`training_authorized=false`保持，G-DATA语义审查未签。人审若要求修改原数据，须新版本/新授权后重新绑定，不回写本轮产物。

## 资源、测试与交接

只用CPU，复用现有默认/native/纯tokenizer参考环境；本轮新增私有制品累计上限2GiB。禁止新环境/联网下载、MLX/Torch模型或框架加载、权重/训练/生成/GPU、外部费用/上传。参考进程启动前禁用Torch/TF/Flax并启用离线，实际核对模型模块为空；不使用含模型库的P01环境作tokenizer-only验收。不得无差异重跑原两遍来源构建或全量8,228行编码；本轮真实分词仅限材料及必要原创小反例。

实现入口宜为`python -m toolalign.data.training_selection --help`及明确的build/verify子命令，允许可信调用者显式提供配置/manifest/私有路径；不依赖源码cwd或把configs暗中当wheel资源。默认选择/核对入口不导入可选tokenizer和模型依赖；人工材料的真实tokenizer检查另列。

新边界测试必须有独立小输入/预期：打乱输入顺序、相同seed、重复或错误Example/audit身份、train/validation误置、禁止final-test作为选择输入、单独/同时超context与response、恰好边界、错误EOS/长度/表示状态、缺失/多余/重复行、已有输出不覆盖和HTML注入转义。分开记录不同场景与安装重复。实际候选再跑适用完整CPU、原R1结构/统计与截止时间边界、lint/4契约/公开扫描；沿用同名测试分组，不修改全局收集规则或旧测试。

对最终完整候选实际构建sdist、默认wheel与显式sdist重建wheel，直接核对成员/Git/metadata/RECORD；在已有纯默认隔离环境安装本次实际wheel并运行新的选择/核对接口与原创小数据，核对导入来源。纯默认接口不加载可选tokenizer；真实13例另走允许的环境。源码直接正常wheel未执行就记NOT_RUN。保留所有失败/原命令与日志，不重写旧证据；最终文档若不改可执行/打包输入，可明确列出实际测量提交与最终提交的映射，勿捏造新运行。

交付完整candidate SHA/父关系/允许路径、实际config与选择/人工包身份、所有命令/退出码/UTC/完整日志hash、原18项及人审/旧审计保全、真实输出分母和失败/NOT_RUN；普通推送新分支并结束本轮等待独立R1。S0核验与R1 PASS后才能合并/验收该绑定，不能因CPU完成启动P04或代签人审。


2026-09-06实际派发：S0再次核验D1上一轮completed/notLoaded和干净旧8c439f6、配置原件实际hash及授权远端后，按完整5d2c6b6发送本范围，原生新轮ACTIVE已核验。原branch和制品仍保留；新branch/code_base与输入intake待D1确认，未把仅派发当作候选交付。T1/E1/R1无新派发。


11:57 UTC输入核验：D1已实际进入work/p02-training-binding，HEAD为精确36b6988，原work/p02-data仍为8c439f6。S0直接核对337份base字节、两个原构建的36项产物与2份manifest、10份授权副本、精确配置579d3d9及旧audit/人审hash，证明dbc024e5157e218d85b1befcd343e24e227c0a4ac1b75b4f403d8e0aa89b5575。D1首轮保全报告ceaabfa0与原日志15cce4f8已核对；其旧1162私有制品/76命令的本轮重核由D1执行，S0本次读取脚本并核对两个completion seal，不冒称再次全量重核。原人审100行仍0 reviewer/0 verdict；输入intake通过，候选实现/材料与独立审查尚未完成。

12:07 UTC，S0独立计算固定规则的[选择身份参考](../../reports/S0_P02_TRAINING_BINDING_REFERENCE.md)，摘要0f82eac7：smoke预期1600/197、formal6013/217，私有逐例排名/hash/桶及互斥排除分母已保存，供候选交付时核对。该检查未导入D1实现、未重新分词或生成训练Example JSONL；不替代D1两次实际物化、13例材料或R1。D1原轮仍ACTIVE，授权配置未变。

12:16 UTC，S0已将D1在526f93d的两次实际物化与该独立参考逐例核对；384文件路径、345份源码快照/Git字节、每遍13稳定文件及原记录/排名/桶/完整排除通过，证明b96605d2。两次build时间和输出目录独立，稳定manifest均为eb4bbfe6。此为选择产物预核验，候选整包/13例材料/安装/独立R1仍待交付，D1继续同一ACTIVE轮次。

12:33 UTC，S0已核对reference/native各13例的原始命令/来源、完整数组及静态HTML，94文件路径通过，证明f33c7f53；另核对28份人工副本/空白CSV，证明d36eabac。本机审阅说明已准备。原始浏览器拒绝回执b2abc9c6已核验，实际页面渲染0页/NOT_RUN，禁止替代绕过；实际页面观察与kris人工判断仍未完成。用户可填写独立人工副本的reviewer/verdict/time/notes，保留case_id/category；reference/native冻结证据只读。D1整包交接/R1继续待完成。
