# P04｜S0 输入与上游控制流准备记录

最新补记（2026-09-07，ADR-0022）：原共用格式、训练绑定、CPU及原生toy技术范围均已VERIFIED；本批P02材料已由kris委托AI审阅，32个问题来源进入新质量版本处理。下一步执行D1质量修订与E1扩展审计，不再等待本人抄填；新绑定、独立复核和真实模型容量完成前不放行正式P04。浏览器实显仍NOT_RUN，页面体验待办独立保留，旧来源/长度/预算计算继续只代表各自历史范围。

2026-09-06；S0。**准备与格式决策记录，P04尚未派发或授权训练。** P03已在29a5e4c完成[CPU主干验收](S0_P03_MAIN_VERIFICATION.md)，P01已在d10722e完成[主干与G1分项验收](S0_P01_MAIN_VERIFICATION.md)。P02人工语义抽查、新格式独立验收及训练配置绑定仍待完成。本记录没有改变原数据、训练选择、依赖、运行预算或冻结协议；以下旧长度与旧格式证据保留其历史范围。

## 已知输入与边界

- P02代码在`2ec17673c18ffbc817b1ff8512e53e44a11766a5`合并，main技术验证通过；数据构建manifest为`87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756`。这不代表G-DATA已通过。
- 当前train有7,515条决策，7,404条长度不超过2,048，另111条较长；validation为234条，其中232条不超过2,048，另2条较长。所有113条长样本仍保留，未截断或删除。正式训练配置必须记录窗口/选择规则及其manifest，不能只写一个max_length值。
- 主模型仍为固定revision的Qwen3-1.7B，0.6B用于前置smoke；遵循原计划的1k–2k SFT smoke，再经门槛进入6k–10k规模。P01短容量实测仅用于预算计算输入，不是正式长训练或256-token完整harness验收。
- 10条含工具schema、多轮observation和无工具判断的token/mask人工核对属于P04训练验收。当前P02语义抽查请求不自动完成该项，也不套用P05偏好审计的数值阈值。

## 固定上游的两个实际控制流事实

只读检查T1已锁环境中的`mlx-lm==0.31.3`、`mlx_lm/tuner/trainer.py`，源码SHA-256为`ee33ebdbd20a184108541cb490d08085485e71a82ffd6d68d7d216029ecd28fe`，与[已登记来源](https://github.com/kris0516/ToolAlign/blob/59b3802c81aa6eceaf3609af88f288756bcb1581/reports/hardware/P01_SOURCE_IDENTITIES.json)一致。S0通过AST和源码定位检查，没有导入MLX或运行模型。

| 事实 | 精确范围 | 对P04的要求 |
|---|---|---|
| 仅在完整累积边界更新，结束后不补尾批 | 319–323行的更新条件为迭代数整除配置累积数；257–259行用固定累积数除梯度；循环结束只保存权重 | 7,404条、microbatch1、累积8的朴素单次调用只有925次更新，余下4微步梯度未应用。必须明确定义并核验尾批，不静默丢弃或重复样本，也不把尾批记作已更新 |
| 内置验证先于当前训练微步 | 286–315行先验证并把iteration记为it−1，319行才训练；最终it也按这个顺序 | 1,600微步/累积8时，最后一次内置验证对应199次更新的权重，最终保存权重为200次更新。不能把前者的分数直接绑定到后者；最终checkpoint必须实际验证 |

这些是固定源码的控制流事实与整数计数推导，**不是GPU复现实验**，也不构成对P01已记录的训练前/后独立验证结果的否定。

一个待P04实现与测试的方案是保持同一model、optimizer和RNG状态：先运行7,400微步/累积8，再对剩余4微步使用累积4，分别记录925+1次真实更新并在最终状态上验证。该方案尚未选定或授权；不得为绕过尾批问题偷偷缩减数据。实施时需要证明不重复数据、不重置optimizer/RNG、计数和梯度缩放正确，且不是自建完整训练框架。

checkpoint选择须用明确的validation集合和固定规则，每条分数绑定当时参数/制品hash、实际optimizer step与处理计数；最终测试集不能参与选择。后续真实ModelBackend还须在P03的spawn/取消生命周期内验证模型加载、共享GPU租约与回收，不能由scripted demo推定可行。

## 证据与下一步

### 训练输出与评测raw语法尚未绑定

S0在main `b71993a36999a14c0ae0eb34a431136e9d91c6c3`以`tests/fixtures/contracts/example.json`和已验证本地Qwen tokenizer运行当前`LocalTokenizer.training_sequence()`。completion为Qwen原生`<tool_call>`包裹的name/arguments对象；将这些精确字节送入P03候选`79a15d990fc27a9a33d033983c94eb92cccfb268`的原始`parse_action()`，得到`ContractError: Invalid JSON`。另用同一原创content构造合法final/clarify/refuse，当前训练序列三者相同，未编码kind。

该CPU证明仅涉及表示层，不是模型生成或P03整包评测失败。私有证据JSON SHA-256为`f880bd901b58814ecc5ff834b355f75d25e2c4d50a2e278dcf2225c65d13c46f`，记录fixture、源码hash、精确结果与UTC。原18数据产物、训练配置和人审材料均未修改。

正式训练前必须版本化共同输出语法、prompt/history投影、token/EOS边界及配置/manifest绑定。S0优先评估保留完整Action的JSON格式，并让D1准备仅CPU提案；目前尚未切换生产默认值。固定Qwen模板在传tools时会声明原生tool_call格式，assistant历史也有think标记处理；提案必须实际解决这些输入冲突和可逆性，不能只替换completion或在生成后悄悄包装raw。新格式如改变序列，需另建长度/序列manifest并保留原版本，人审语义材料的复用必须由其内容hash与语义投影证明。

本次只读检查的私有JSON SHA-256为`53fad6074957f841df8ef6bb5eaf21a867ff220966a57f6cb1ff63786e1c28e8`，记录实际UTC、源码hash、AST位置、原生循环计数、限制及未授权方案。未修改T1工作区、未构造权重tensor、未运行GPU。

S0在P01/P02/P03前提满足后再发布精确P04 code_base、配置授权、允许文件和模型预算。以上要求进入届时任务包与独立审查范围；当前没有正式训练、checkpoint选择或模型结果。

## ADR-0017 与新的实现前提

D1同12例的角色比较已正式交付6c3d330e4b28be0fbc93c273bb2576f7317c69a8；S0完整读取并核对68项hash，原A结果与167份原文件不变，私有复核证据hash为1793b65bbdb6e990387319ffb84e050ece7225e188612633783fed4977620d6f。S0选择保留Message模板输入角色的B方案，见[正式规范](../docs/16_MODEL_IO_FORMAT.md)及ADR-0017。这是实现规范选择，尚未实现验收、切换原P02默认格式或授权P04训练。

该方案保持完整Action，固定官方模板及non-thinking；tool仍由模板形成user/tool_response。P01固定0.6B/1.7B与D1 tokenizer三个来源小文件字节实际一致，来源复核证据hash为83bafd8cfeedf25ef82f558ddb23eb5a1a333a2617cbaf2a461b9aadb24b7d3f；未读取权重。最终v1的标记/指令已区别于proposal，需新跨实现对照和全量8,228例序列审计。上表旧113条长度统计仅对应原格式，不能沿用于新格式选集。一个边界例276内容token加EOS超过当前256响应上限但总长低于2048，说明两种预算必须分别记录；没有模型生成或质量结论。

D1 P02-format-r2的新授权仅覆盖共用纯模块及CPU派生审计，不改变原数据代码、18项产物、split/标签、人审材料和填写副本。新代码须精确候选独立R1/主干验证，新的训练选择与人工token/mask核对随后另行办理；既有G-DATA人审请求无需重复。


## 新格式候选后的 train/validation 预算算术

D1最终候选`7bada2e451d43dae4b3ed532d5efa310fc8e6a57`已交付，[Draft PR8](https://github.com/kris0516/ToolAlign/pull/8)双Python CI34017408825全部步骤通过，独立R1正在按完整授权1de9078审查。S0核对713项交接checksum及217份原公共文件不变。这是候选完整性和CI证据，新格式仍未达到独立验收或主干VERIFIED。

S0只读原8,228行派生指标文件（SHA-256 `36b8cbfe6773c08f7a28521a99ed8783723a8f7fa3b2a3fa87915d8d1d871aff`），核对format/descriptor身份，再对固定 **train及validation** 重算以下交集。没有重新tokenize、选择/输出训练样本、修改标签/切分或使用最终测试模型分数。每格均要求表示/parser恢复正确、总长不超过cap且C含唯一EOS不超过256；原分母仍为train7515、validation234。

| 总长 cap | train 统计交集 | validation 统计交集 | train 按累积8的整组 + 尾微步 |
|---:|---:|---:|---:|
| 1024 | 985 | 74 | 123组 + 1 |
| 1536 | 3618 | 197 | 452组 + 2 |
| 2048 | 6013 | 217 | 751组 + 5 |

2048档未进入交集的1,502条train按互斥原因分为：仅context超限1,272、仅response超限158、两者都超限72；原样本全部保留。validation对应17条为仅response14、两者均超限3。尚未把这些统计作为训练选集或修改全量评测分母。若未来采用该规则，训练配置必须显式绑定选择算法/输出身份及排除清单；751组加5尾微步须形成真实的752次更新，或另有预先说明并验证的尾批策略，不能静默舍弃。

1024档只有985条train，不能声称已满足1k–2k不重复样本的单遍smoke目标。未来0.6B smoke若使用更长窗口，需在该阶段先完成新长度的小型受限运行与预算验证，不能把1.7B容量结果当作0.6B该格式实测，也不靠重复样本凑独立数量。目前未选择窗口、样本或运行方案。

作为预算输入，6013条的最小对应长度桶为1024档985、1536档2633、2048档2395；有效序列共8,552,832 token，C含EOS的监督token共543,286。若按上述桶右补齐，每单遍为9,957,888个逻辑处理token。将这些计数乘[P01原1.7B各档已同步测量的平均SFT微步时间](hardware/P01_REPORT.md)，仅局部训练计算的线性估计为107.15分钟。该数值没有测量新格式或长训练，不包含导入/暖机、validation、checkpoint、生成、压力停止/重试；实测样本min/max不能作为运行上限或置信区间，正式墙钟预算尚未授权。实际trainer分桶/padding/完整数据覆盖也尚未实现验收。

私有算术记录SHA-256为`cabf99647841b80d9a32db449fec1a8128a05e4bfd381b9ef08a5df3aaf96398`，绑定原指标文件、P01精确结果/各档来源及实际UTC；未加载任何模型。旧格式7404/232条及其控制流举例仍保留为历史，不能用于新格式run计数。下一步在R1/main格式验收、kris实际语义审查及训练选择/配置绑定完成后，由S0发布精确P04范围和资源预算。


## 新格式主干前提已满足

2026-09-06，PR8已合并36b6988并通过最终双Python CI及main843CPU/2 HF-only skipped与实际归档绑定，新格式技术范围VERIFIED，见[S0主干记录](S0_P02_FORMAT_MAIN_VERIFICATION.md)。以上原候选/旧长度/预算推导保持其原时间和范围。下一步仍需训练选择/配置/manifest绑定及kris真实语义、token/mask检查；本报告不构成训练授权，也不将原统计交集改写成已选训练集。


2026-09-06主干补记：训练绑定已随[PR9](https://github.com/kris0516/ToolAlign/pull/9)合并42eaa50并完成最终双Python CI与main919CPU/2 HF-only skipped、现存三归档及49份安装包载荷绑定，CPU技术范围VERIFIED；原R1 PASS40252f8保持。见[本次主干证据](S0_P02_TRAINING_BINDING_MAIN_VERIFICATION.md)。smoke1600/197及formal6013/217现在为已物化并核验的训练绑定；本文件中的旧候选/算术/待验记录保留原时间。实际材料页面观察、kris语义/token-mask判断及P04实际trainer/collator、尾批/checkpoint/容量与正式训练仍待完成。

最新CPU接收补记（2026-09-07）：R1原800480b对33d6248的CPU准备正式PASS/P0/P1/P2均0，已原生completed/idle；S0核对56134路径/26原命令，普通集成487c92d实测1014CPU/2跳过、三新归档及新默认安装7条接口通过。CPU部分ACCEPTED，PR10最终CI/main待验证；原生train仍BLOCKED，实际尾周期/evaluate/checkpoint和人工/正式训练门槛保持。详见[独立验收与集成](S0_P04_SFT_CPU_INTEGRATION.md)。本报告前述旧测量保留原执行范围，不改写为新运行。

主干验收补记（2026-09-07）：P04-SFT-CPU准备部分VERIFIED；[PR10](https://github.com/kris0516/ToolAlign/pull/10)实际合并e28f1db，原R1 PASS800480b保持。最终双Python CI与main1014CPU/2 HF-only跳过、现存三归档/57安装包文件绑定通过；原生CPU train入口仍BLOCKED，实际尾周期/evaluate/checkpoint及人工/正式P04门槛保持。见[main证据](S0_P04_SFT_CPU_MAIN_VERIFICATION.md)。此前记录仍保留各自实际执行时间与待办状态，不改写旧实验。

2026-09-07新版只读准备：按已冻结v3排除身份，formal投影5,938条、742组8+尾2共743更新；smoke1,583条、197组8+尾7共198更新。证明`9052c0b40e83a494b8c259df782df1d6b934a193ec22bcf5cc77594a829dd4fa`仅使用既有长度元数据及源码，没有新数据构建/分词/框架/模型运行。当前prepare仍固定旧v1，native训练/score仍仅toy范围，真实0.6B1536容量NOT_RUN。[T1只读方案](../coordination/tasks/P04_SFT_RUNTIME_PROPOSAL.md)已于14:15:28 UTC按完整8929cbb原生派发/ACTIVE，新branch/intake待交付；实际v3/hash/独立验收后S0再确定CPU消费与真实模型运行范围。
