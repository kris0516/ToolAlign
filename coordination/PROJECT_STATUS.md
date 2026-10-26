# 项目真实状态

更新：2026-10-27（Asia/Shanghai）。当前入口：[toolalign.md](../toolalign.md)。G3验收已随PR27合入主干 `1267d1a33dfb08bfd9800b80ea97315730748952`，双Python CI 40295329527全部成功；实际SFT执行源码为PR26 `2abbe7ac913661df1d5e430f285604b4ceb8ff4b`。当前唯一协调者S1，G1–G5已完成，G6为唯一active goal。G4按DATA_INSUFFICIENT_WITH_NO_DPO降级处置结束，原DPO checkpoint条件未满足；已在PR28主干 `6e2f1d2` 完成80条真实候选，0成功/0偏好，产物已回收且L4已停止。

| 阶段 | 已支持的结论 | 关键证据 |
|---|---|---|
| P00 | CPU 基础包、冻结契约与互斥 VERIFIED | [main 验证](../reports/P00_MAIN_VERIFICATION.md)，PR2 |
| P01 | Mac 受限 SFT 与唯一 DPO 备选兼容通过；首选 DPO 原 FAIL 保留。这是原平台结论 | [main 验证](../reports/S0_P01_MAIN_VERIFICATION.md)，PR6 |
| P02 | 冻结 v3 数据、来源处置、13 例材料通过技术与 AI 质量审核；G-DATA PASS | [技术 main](../reports/S0_P02_QUALITY_V3_MAIN_VERIFICATION.md)、[Q1](../reports/S0_P02_Q1_V3_ADJUDICATION.md)，PR15 |
| P03 | CPU 工具、oracle、scripted 执行器 VERIFIED；模型评测未运行 | [main 验证](../reports/S0_P03_MAIN_VERIFICATION.md)，PR7 |
| P04 准备 | CPU collator、MLX 原创 toy 数值、固定 Qwen CPU 接口通过 | [CPU](../reports/S0_P04_SFT_CPU_MAIN_VERIFICATION.md)、[toy](../reports/S0_P04_SFT_NATIVE_TOY_MAIN_VERIFICATION.md)、[模型接口](../reports/S0_P04_QWEN_CPU_MAIN_VERIFICATION.md)，PR10/11/17 |
| P04 v3 接口 | R1-r3 PASS；PR19 已合并，main 定点 163 passed | [main 验证](../reports/S0_P04_DATA_V3_MAIN_VERIFICATION.md) |
| P04 真实 v3 消费 | 当前接口一次 prepare 与13例数组转换/导出/回读 PASS；0新编码/模型更新 | [S1消费记录](../reports/S1_P04_DATA_V3_CONSUMPTION.md) |
| P04 CUDA CPU 实现 | 4342af8 经独立R1审查 PASS；17项定点检查及独立数值/恢复通过，真实CUDA待运行 | R1原审查提交 `7d460f2054201c00055a1f924c5c4984be8e6988` |
| P04 CUDA mask 预审 | 13例真实材料与CUDA消费者对应PASS；423项检查、26条原证据绑定通过 | [Q1预审](../reports/reviews/P04_CUDA_MASK_Q1_R1.md)，`82f1e88` |
| P04 Colab CPU 控制 | r3独立PASS；两项控制问题均关闭，S1原失败上下文5项定点检查通过 | [R1-r3](../reports/reviews/P04_COLAB_ENVIRONMENT_R3.md)、[S1集成](../reports/S1_P04_CUDA_INTEGRATION.md) |
| P04 CUDA 容量输入 | 主干920c415的20条编码/回读PASS；独立Q1 531项检查通过，13例身份不变 | [Q1增量](../reports/reviews/P04_CUDA_CAPACITY_ARRAY_Q1_R1.md)，`ed022da` |
| P04 Colab 真实安装 | PR22锁在L4真实安装PASS；48包/pip check通过 | [实测](../reports/S1_P04_CUDA_CAPACITY_R1.md)，原安装失败保留 |
| P04 CUDA容量/恢复 v1 | 最长2048 token三步容量PASS、采样峰值5180MiB；新进程恢复后更新超容差，跨实例未运行 | [实测与数值FAIL](../reports/S1_P04_CUDA_CAPACITY_R1.md)；两份输出已回收，实例已停止 |
| P04 CUDA恢复诊断 | 新实例初始状态严格一致；同进程重复backward差异约0.86%，关闭checkpointing仍存在；零更新 | [实际诊断](../reports/S1_P04_CUDA_RESUME_DIAGNOSTIC_R1.md)，29文件已回收、实例已停止；不构成更新恢复PASS |
| P04 CUDA确定性v2 / G2 | 验收PASS；实际三步、新进程及新实例恢复1,883项通过，672个张量比较差为0；R1/Q1独立终验通过 | [实测及接纳](../reports/S1_P04_CUDA_V2_RECOVERY.md)；65文件已回收、实例已停止 |
| G3 原始验证 CE | CPU实现及独立技术审核PASS；8项实现检查、4项独立检查通过，未改变SFT选模 | [R1审核](../reports/reviews/P04_CUDA_SFT_BASELINE_R1.md)，候选c633bd7、审核fd4ad07 |
| G3 完整输入数组 / Q1 | ACCEPTED；两个profile共7,928行逐行核对通过，原13例材料身份不变 | [Q1完整数组审核](../reports/reviews/P04_CUDA_SFT_FULL_ARRAY_Q1_R1.md)，`98cf0e1` |
| P04 正式 SFT / G3 | 独立验收PASS；198/743次更新完成，验证CE为0.041494/0.024438；R1 300af3f、Q1 34331c2已接纳 | [实测与曲线](../reports/S1_P04_CUDA_G3_SFT.md)；196文件已回收，实例已停止 |
| P05 偏好与 DPO / G4 | 80条真实候选0成功/0偏好；Q1零对处置已接纳，L4已停止 | [实际生成与覆盖](../reports/S1_P05_G4_GENERATION_R1.md)、[Q1审核](../reports/reviews/P05_G4_PREFERENCE_Q1_R1.md) |
| G4 DPO CPU实现 | 独立CPU审核已接纳；输出预算问题r2 PASS关闭，原数学/恢复证据保持 | [R1 r2](../reports/reviews/P05_G4_DPO_R2.md)、[E1修订](../reports/P05_G4_DPO_FIX_R2.md) |
| G4 批次文件验证复用 | CPU审核接纳；一次诊断已回收 | [实测](../reports/S1_P05_G4_GENERATION_R1.md)：预检12.307秒/child冷加载7.219秒，第三动作返回额外工具，20.883秒tool_round_limit |
| P06 / G5实际评测 | M0/M1均0/28；恢复均0/8；A2的12对输出相同、4次实际缓存命中；独立终验已接纳 | [实测与21例失败](../reports/S1_P06_G5_EVALUATION_R1.md)，245文件及124进程已回收，L4已停止 |
| P07–P09 / G6 | ACTIVE；受限服务与客户端CPU协议已冻结，实际服务未运行 | [G6协议](tasks/P07_G6_PROTOCOL.md)、[共享HTTP](../docs/18_RESTRICTED_CUDA_SERVICE.md) |

已登记92项问题全部关闭；Q1-G5-CORPUS-001/002经Q1正式r2 `cb4c72d` 复验及S1接纳，连续计数各1→0，原首次失败及48题永久隔离保持。P05-DPO-OUTPUT-001经E1修订及R1 `8ce08bf` 独立复验原反例PASS关闭，连续计数1→0，首次REQUEST_CHANGES保留。Q1-G4-CORPUS-001经两条提示的JSON字符串约束修订及Q1独立r2 PASS关闭，连续未通过计数1→0，首次REQUEST_CHANGES保留。CUDA-RESUME-001经R1 `be756a1` 的实际完整恢复独立验收关闭，正式修订失败计数0；Q1 `847e0be` 已确认数据身份与说明范围。原FAIL和全部失败历史保留。数据质量、CPU、toy或容量PASS都不是正式模型效果。

## 原 S0 交接记录

合入已独立审查的 PR19；重写接续入口，转向 Colab；复用另一项目的 CLI/ADC/SSH/tmux 方法；整理本地技能；清理停用训练环境与可再生缓存。本机清单在 `.toolalign-local/handoff-2026-10-26/`，公开摘要见[整理记录](../reports/S0_COLAB_HANDOFF.md)。

该次交接没有新模型下载、GPU实例、训练、偏好生成或正式评测。其后S1完成的CUDA实测以上表为准。

## 当前接续

S1 已与 S0 完成协调权和证据交接，冻结数据、来源根及模型缓存已定位；G1准备完成。G2通过当前接口读取真实v3数据，完成CUDA实现、锁定环境和实际容量/恢复；独立审核均已接纳。

按 [GOAL](GOAL.md)依次推进。G2的v2三步容量、新进程和新实例恢复已通过R1/Q1终验；1,883项S1检查通过，672个adapter/Adam张量比较差为0，原v1 FAIL及诊断保留，详见[G2报告](../reports/S1_P04_CUDA_V2_RECOVERY.md)。

G3实际执行PR26主干 `2abbe7ac913661df1d5e430f285604b4ceb8ff4b`。0.6B/1.7B均完成冻结一轮SFT，完整验证CE从0.739884/1.145230降至0.041494/0.024438，选中step198/743。10段恢复链、941次更新、游标及选模已由S1核对；196文件已回收，唯一L4实例已停止，累计占用9,124.538896秒、余额观测差3.85 CU。[R1技术终验](../reports/reviews/P04_CUDA_G3_FINAL_R1.md) `300af3f` 与[Q1数据及说明终验](../reports/reviews/P04_CUDA_G3_FINAL_Q1_R1.md) `34331c2` 均PASS，S1已回读接纳；PR27合并后G3 App goal实际complete。

以下为G4实际执行与接纳记录；App goal已于PR30主干核对后按有据降级complete。T1交付d1aa1c8，170项受影响检查通过、2项既有pip parser检查跳过，最终回收修补另有18项通过；D1交付147d045及938c471，42项测试、32正向/20反例CPU轨迹通过。实际新语料为20个train任务、12个family、10类别、1个共享工具/schema连通组；完整recipe和原始材料留私有。S1回读源码与证据身份，并通过1项生成恢复到偏好提取的组合检查。固定tokenizer预检中，初始输入最长1,351、scripted轨迹输入最长1,742 tokens，预留256均在2,048上限内；不代表真实生成不会遇到更长历史。

R1提交 `fac9ec5` 对生成与偏好CPU实现均PASS，新增实质问题0；4项独立CPU检查覆盖实际输出到提取、上下文边界、传递分组隔离及外层控制器对真实owned child的回收。S1已回读27份审核证据，当前生产/测试/配置/依赖与受检源码逐字节相同，接纳两包CPU实现。Q1对固定20题的生成前语义/分组审阅r1为REQUEST_CHANGES：18题通过，第10、13项未明确版本答案须为JSON字符串，独立反例确认同值数字被判失败；分组和v3根绑定通过。S1已核对Q1提交 `fd0e8f3` 及30份私有证据，接纳问题Q1-G4-CORPUS-001；D1候选 `76e114f` 已补充两题类型要求及约束依据，4条定点轨迹通过；S1核对34份文件和实际差异，其余18项内容/全部答案策略保持，group身份传导已记录。新tasks SHA `b9c6f18995579d8af1a58d137cafe9cc1c9f2f40279d9434aa85e2c7769eb015` 经Q1 `5044029` 定点复审PASS，S1回读38份证据后接纳，旧包和原FAIL保留。两题的8条脚本请求tokenizer检查最长1,755，含256预留在2,048内。正式偏好池审核另行执行。PR28已合并为6e2f1d2，最终头双Python CI 40311970393全部成功且文件树一致。完整20题×4候选80条均已结束：61超时、12参数错误、5未提供工具、2无记录，0成功/0有效偏好。前12条终态逐字节继承；80条实际输入、seed、模型与终态身份已回读，202个模型/工具进程已回收，23/80条token计数完整。首段43份、续段175份、独立加载诊断17份产物已回收；本次L4分配3,758.929秒、余额观测1.58 CU，实例已停止。

79条完整首动作全为tool_calls；原G3的5,938 train/213 validation监督目标也全为tool_calls，原CE结论限于这组目标拟合。独立profiler中固定模型文件验证累计12.230秒，其中SHA-256 update自身11.015秒；这支持先做[批次验证复用CPU修订](tasks/P05_G4_MODEL_VALIDATION_CPU_R2.md)，不能声称修复模型语义。Q1 `5321842` 独立核对158次实际输入、101个完整动作及原12条继承，S1回读55份证据后接纳NO_ELIGIBLE_PAIRS处置：审核样本0、误标率不定义、DPO质量门BLOCKED。首个合法返回动作后超时的样本为ordinal 8、seed50，两次合法调用后第三次请求已提交；未返回答案保持unknown，供一次独立运行时诊断。E1原生DPO候选982cc191经R1 32a031b核对：SUM/mask/reference与CPU恢复获得支持；最终summary漏计输出预算为一项P2。E1 r2 `61f84f5` 经R1 `8ce08bf` 独立原反例复验PASS，S1核对10份审核证据后关闭输出预算问题、计数1→0，原失败保留。T1 `db5cbac` 经R1 `7d36b49` 独立PASS：复用47项检查并新增1项owned spawn文件变化检查；单条诊断脚本只读审核通过。S1回读7份审核证据后接纳，PR29已合并为3250f1b，最终头双Python CI 40331335284成功且文件树一致。原ordinal 8/seed50的单列诊断完成：原三次输入、前两动作和观察相同，第三次返回额外日志工具，20.883秒因tool_round_limit失败；预检12.307秒、child冷加载7.219秒、完整段33.939秒，不声称单请求整体加速。23份产物已回收，第二实例718.631秒/0.17 CU后停止；G4合计4,477.560秒/1.75 CU。R1 `fe26311` 与Q1 `d5c55fb` 独立终验均PASS；S1回读接纳 **DATA_INSUFFICIENT_WITH_NO_DPO**。原DPO checkpoint交付条件未满足，DPO CUDA容量/恢复/训练及M2保持NOT_RUN；原80条、两条单列诊断和失败历史不变。后续G5比较M0/M1，M2明确缺失。PR30已合并d0a266d，最终头双Python CI 40338862773成功且文件树一致；G4 App goal已按该处置complete。

G5 App goal现为active。按[评测协议](tasks/P06_G5_PROTOCOL.md)实现M0/M1后端、真实prefix cache与恢复开关，并构造、独立审核L1隐藏oracle任务及官方BFCL固定子集。E1新工具候选6027096已通过独立R1 c6c81db：复用109项通过记录和四域8个已回收child，新增3项独立检查与4个child全部通过/回收；S1回读69份审核证据后接纳，旧工具身份保持。T1执行器60c52f8经[R1 37eb027](../reports/reviews/P06_G5_EVALUATION_R1.md)独立PASS：复用231项通过、1项既有pip缺失跳过，以及1项真实工具组合和8个回收进程；新增6项独立检查通过、8个child回收。S1回读96份审核证据并核对17份候选文件后接纳CPU实现。原创小模型的真实扩展前缀命中将20-token输入的首轮计算降至4 tokens，输出一致；CUDA延迟及模型效果仍待实测。D1语料已交付待独立审核，E1官方BFCL/分析CPU实现继续；四域不预先视为四个独立group。G5上限14,400秒/8 CU，当前GPU及正式评测仍NOT_RUN，G6随后继续。

PR31已合并为 `25eb63be4710d015d235af08e31088751c46f525`，最终头双Python CI 40356242133全部成功，main文件树与受检头一致。D1候选d4c4251已交付48题、23 family、1个连通组；51正向/48反例符合预期，199 child全部回收。S1回读177份证据，并用已接纳的当前reader实际读取L1/A2输入，得到104个L1/A1单元与8个A2序列单元。Q1 `08d4c5a` 对全部48题审阅为REQUEST_CHANGES，S1回读203份证据后接纳：001为16题未编码观察/决策轮次要求，两条真实预提交反例误判；002为遗漏具体missing-field语义连接，加入后原48题均连接到旧P03/G4组件，按冻结规则应保留0、隔离48。原包与99条作者CPU记录保持；当前题集不进入正式模型评测。两项各计首次未通过，不重复计算R1复读或多条反例。A2的4组12个开发请求独立审核PASS，仅接纳输入，性能未测。D1正在只读准备有据整改方案，E1 BFCL/分析候选尚未交付；G5保持active，GPU及模型评测NOT_RUN。

G5修订现按[模型输出前r2边界](tasks/P06_G5_L1_REPLACEMENT_PLAN_R2.md)继续：Q1只读预审允许进入CPU构造，前提是完整冻结P02/P03/G4及原48题参考，关系计算实质影响作答，澄清冲突由观察揭示，四类算法含义在写题前明确。这不是正式语料PASS，不关闭001/002。T1实现版本化观察依赖oracle；D1导出原48整组隔离和完整排除参考，未构造新题。后续新关系工具候选目标28题，48题与GPU预算上限不变。

E1 BFCL/分析候选 `7e56244` 已经R1 `2b47acf` 技术PASS及Q1 `d31a6a6` 零题处置PASS，S1分别回读534份、37份审核证据后接纳。固定150条、227个函数根对象均未显式关闭schema，实际0合格，未读取官方答案或产生空模型计划。R1新增四项检查通过，实际调用官方checker的8个原创案例通过，并独立复算不等规模group的整组bootstrap、缺失分母及中断回放；此前D1部分三项独立检查保持。联合REQUEST_CHANGES只引用原L1的001/002，不新增问题或失败轮次。Q1复算111组件中7组件、28题触及P02，零题处置与说明PASS。L2模型分数未定义，正式官方评分NOT_RUN。

E1原32项新增CPU检查、19个官方scorer原创案例及6行CLI证据保持；其中19例是较早源码快照，最终官方路径另由R1的8例与最终CLI支持。全库原记录为1,396通过/4失败/78跳过，4项临时根错误在默认临时根下原测试通过，失败保留。T1 `ecbb520` 已交付新版观察oracle，S1核对127产物及7源码；两条原反例改判failure、合法策略继续通过，141项受影响检查通过、12个owned child回收。D1 `f159b52`（实现2153c68）落实48题整组隔离，S1核对59产物、4交付文件及22项参考绑定；完整参考含全部旧节点与851历史边，13项定点检查通过。R1 `eba411b` 对两修订均PASS，S1回读227份证据、18份当前源码与2份报告后接纳；复用154项通过记录，新增2项独立检查及1条真实CPU轨迹，4个child全部回收。8份Q1原结果重评分一致，非相邻依赖与事后补观察边界通过；完整参考独立重建3,595节点/3,506组件，改名及schema等价变形仍传递隔离全部78旧节点。001/002正式关闭待新题Q1复验，连续计数仍各1。L1模型评测、A1/A2性能和GPU分配仍为NOT_RUN/0。

PR32已合并为 `9963a0a0501c668ac1604ed21a140b6be85531be`，最终头 `9f5aada` 的双Python CI 40373485110成功，main完整文件树相同。E1新关系工具 `6f6a497` 已交付；S1回读93份产物、7份交付文件和四对8个真实child记录后接入候选分支。53项工具/5项新reader及2项旧reader检查通过，最终reader fixture补齐后5项定点复验通过；生产源码身份相同。三类排除键的实现前/交付前交集均0，旧两个catalog及18种registry变体保持。R1独立技术审核与D1新语料构造并行；D1从同一集成头采用已接纳观察oracle和完整排除参考，至多28题，正式资格仍待逐题Q1。

R1 `8e2b657` 对新关系工具独立技术PASS，S1回读158份证据、18份当前源码与2份报告后接纳。复用60项定点检查及8个已回收child；新增3项独立检查、9个算法案例及1条新reader完整链路通过，新增3个child全部回收。对完整3,595节点及16,940份工具声明复算，三类键交集均0；新题语义资格仍待Q1，001/002状态和计数不变。PR33当前候选e66e45b的双Python CI 40375735604成功，新增交付集成后另核对最终头；D1新语料继续构造，GPU仍0。

D1新语料r2实现 `3206fbc`、最终交付 `32bc19c` 已接入PR33；S1回读总索引208份私有文件、6份公共文件，并核对120份当前源码/配置身份。实际28题形成4个连通组，36条正向成功、56条反例失败，216个child全部回收；最长合法历史1,334 tokens，加256预留为1,590。当前reader实读生成56个M0/M1主单元、8个A1单元，原A2身份不变。R1代码预审3项独立检查及6个child通过/回收，S1已接纳；最终语料消费审查与Q1逐题正式r2审查正在并行，001/002各计数1保持。PR33实现头60ba22d的双Python CI 40380159936成功，最终合入前另核对最后提交；当前GPU仍0，模型效果及A1/A2性能NOT_RUN。详见[候选报告](../reports/P06_G5_CORPUS_CPU_R2.md)。

R1最终语料技术审核 `bb4fc27` 与Q1正式逐题r2 `cb4c72d` 均PASS，S1分别回读298份、167份私有产物、120份当前源码/配置及各两份公开报告后接纳。R1复用代码预审3项/6个child，新增4项最终消费、轨迹、图与tokenizer核对；Q1逐题推导全部28题并比较78个可读旧程序，新增3条合法等价/预提交真实CPU轨迹、9个child全部回收。新28题保留、分组及长度隔离0，实际4组各7题；001/002正式关闭、各计数1→0，原FAIL和原48永久隔离不变。冻结tasks SHA `a645b445d37a66522c39d83d110b6384abe8e0e93b15ad4ff8b208eb7eb2b54f`，56条M0/M1主轨迹、8条A1及原A2的24次请求；当前等待PR33最终CI与主干合并后冻结执行配置，G5 GPU分配仍0。见[技术终验](../reports/reviews/P06_G5_CORPUS_R2.md)、[正式Q1复验](../reports/reviews/P06_G5_CORPUS_Q1_R2.md)。

PR33已合并为 `19f6f9bbc3710487634765854f74f9af3fc80eef`，最终头5698f18的双Python CI 40388206384全部成功，主干完整文件树与受检头一致。三段输入和配置于实际推理前冻结。S1已申请唯一L4并核验23,034MiB实际显存；安装SSH断开后回读确认原安装正常完成，原失败保留。容量探针两模型均完成实际CUDA生成：各1,792输入tokens，输出27/33，完整段31.646秒含文件预检12.088秒，采样峰值3,926MiB；两个owned child均回收，23份产物已验证回收。两条Action格式失败按预先规则单列，未作为容量条件；实测最长序列1,825 tokens，不扩写为完整2,048-token解码。S1接纳冻结容量条件PASS。随后56条M0/M1主比较、8条A1恢复关闭对照与A2的24次请求全部完成，未启动项0。M0/M1均0/28、四组配对差值及bootstrap区间均0；M1首动作Action格式28/28合法（M0为1/28），全部66个合法动作均为tool_calls。恢复开启8/8重试成功但无完整答案，on/off均0/8；A2的12对原始输出相同，4次实际命中5,176 tokens，全部请求wall总和减少0.169秒。S1已回读104个L1实际输入和24个回放请求；245文件及124个owned进程已回收，唯一L4已停止且确认0活动分配。累计2,358.235秒、余额167.21→166.32 CU（观测差0.89），全部安装、空闲、失败连接与传输计入，低于14,400秒/8CU上限。[实际结果与21例失败](../reports/S1_P06_G5_EVALUATION_R1.md)候选等待独立R1/Q1终验，G5保持active。

R1技术终验 `b52c7115dba09c5f83faab24f0a95baf04694280` 与Q1结果说明终验 `c4ef4645eb032d4884dc2f6ec8a414cb6f2383a6` 均PASS，S1分别回读540份、523份私有证据、各两份公开文档及完整审核脚本后接纳。R1五项独立检查通过，130次实际输入计数、完整分母、统计、成本及回收账目一致；Q1重建104次L1请求并独立审阅21例失败。新增问题0，原FAIL、48题永久隔离、M2 NOT_RUN及L2零合格处置保持。结果与审核已纳入PR34，当前等待最后提交CI及主干核对；G5仍为唯一active goal，随后进入G6。见[技术终验](../reports/reviews/P06_G5_FINAL_R1.md)与[Q1终验](../reports/reviews/P06_G5_FINAL_Q1_R1.md)。

PR34已合并为`98d642a116da94f2ab2b2aaeb6e931f79fd5cabc`，最后提交`3730b048119d448da013aca6e9079661a587c936`的双Python CI 40400234474全部成功；S1核对主干完整文件树一致、工作树干净，G5 App goal实际complete。G6 App goal已创建并成为唯一active：共享HTTP与两包CPU任务已冻结，待派发T1服务/控制器与E1客户端/示例/说明。当前G6新模型推理及GPU分配为0；CPU/R1/主干通过后才冻结具体有界smoke。

完整历史见[迁移前状态](https://github.com/kris0516/ToolAlign/blob/abdc53d468a270cc1bfecbe56980dd34918480e1/coordination/PROJECT_STATUS.md)和各阶段报告。旧 Mac 包的“待派发”状态不覆盖新路线。
