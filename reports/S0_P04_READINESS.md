# P04｜S0 输入与上游控制流准备记录

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
