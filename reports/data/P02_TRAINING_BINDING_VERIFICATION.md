# P02 训练数据绑定候选｜CPU 实测记录

2026-09-06，D1，P02-TRAINING-BINDING。固定选择、两次实际物化、13例真实 tokenizer 对照、906项CPU回归及归档/隔离安装已通过自测。**浏览器实际渲染观察 NOT_RUN；独立R1、G-DATA语义人审和token/mask人审均未完成，训练未授权。** 本记录不是整包验收。

任务基线为 plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / ADR-0019，依据docs02/03/16。精确code_base `36b6988af6b4e0125b59fb81b1cea142233e14a2`；完整授权 `5d2c6b66421a47ee71d3b5d0d3c3892354b10512` 通过私有原件读取。仅使用现有独立D1任务和隔离分支 `work/p02-training-binding`，保持 gpt-6-astra/max，无新任务或sub-agent。

实现与选择测量提交 `526f93d4e0878365a6748c593b3e685b9a395384`；包检查器提交 `bc9db40bc3d5a26b73b5f2e7dd308f1bb35be6f5` 是其直接子提交，只新增公开检查器，不改变包或选择输入。最终文档提交增加本报告、证据、选择公开manifest和交接；完整最终SHA由原生交付和私有completion登记。旧本地分支8c439f6保留，未引入未去敏review f708及其后代，未合随后协调main。

## 固定输入与实现边界

[配置](../../configs/training-data.v1.json)逐字节复制S0原件，文件SHA-256 `579d3d9d9436f4374e7e808dc5b787213157d7ee477bfffd48dac02d35e70a4c`，`training_authorized=false`。配置不回写；新的manifest同时绑定配置和实际选择产物。

| 固定输入 | SHA-256 |
|---|---|
| 原data manifest canonical | `87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756` |
| 原公开表示manifest文件 | `69bfa651bf8db9b2c77c11c4f8d55419a8af4196aba8ff6a69b5b3b0982e0f47` |
| 原audit rows文件 | `36b8cbfe6773c08f7a28521a99ed8783723a8f7fa3b2a3fa87915d8d1d871aff` |
| 表示common binding canonical | `82a341f37de3c05ac83f4eda5131b74703aaa1de6b241ff27164cadde9c5be86` |

新模块仅消费train/validation原Example和对应历史行。最终split行只识别split后跳过；整文件及18项产物hash用于保全。每个Example通过冻结验证；完整Example、ModelInput、Action、来源/修订、source_record_hash、group与split逐一对应。缺失、重复、额外、错split或坏身份直接失败。表示成功必须显式为真，错误字段必须显式为None；长度拒绝bool/负值并核对P+C+1=N、含EOS长度、唯一追加EOS、监督起止和完整mask hash。Action原值与当前parser、原raw字节/节点/深度也核对，嵌套budgets布尔值不作为选择依据。

纯函数 `select_examples` 可用于原创小输入的结构测试，不单独认证测量真实性；生产 `build` / `verify` 额外固定实际原始文件hash和数量，因此不能用重算一致的伪造长度替换历史行。`verify`从固定原件重算选择，再检查每份输出，而不是只信任输出manifest。默认入口不导入tokenizer或模型依赖；配置/数据/协议路径由可信调用者显式提供，不依赖源码cwd或隐式wheel配置资源。

历史全量测量代码为b33a55f及原native loader hash `6d1a4474cf6cdc747de53b365426367e825ea844d3ebf0b1f36e54629a8b1d30`。当前消费的是已验收loader hash `f1354c349708c09e82661fbde3d7b9b96df16a5f9634b28097b66973bbe4ddf3`。两者分别登记；没有伪称历史代码与当前源码相同，也没有改旧manifest或重测8228行。

## 两次实际选择

12:11:00–12:12:30 UTC，在两个不同的新私有目录分别运行build，耗时36.53s及35.87s。13份稳定文件全部逐字节相同；时间、路径和当前消费环境独立放在run元数据中。

| Profile / split | 原分母 | 长度合格 | 实际选择 | 仅context排除 | 仅response排除 | 两者排除 | 排名排除 |
|---|---:|---:|---:|---:|---:|---:|---:|
| smoke train | 7515 | 3618 | 1600 | 3667 | 77 | 153 | 2018 |
| smoke validation | 234 | 197 | 197 | 20 | 5 | 12 | 0 |
| formal train | 7515 | 6013 | 6013 | 1272 | 158 | 72 | 0 |
| formal validation | 234 | 217 | 217 | 0 | 14 | 3 | 0 |

使用固定seed42和 `canonical_hash(["toolalign.training-selection.v1",42,example_id])` 排序，同hash按ID升序；smoke取首1600且无放回。每份输出保留原Example字段和值，sidecar另记排名、原表示身份和最小右padding桶。两个split的smoke均是formal对应子集；不改group/split，不截断、不packing、不增标签。互斥排除的逐例IDs只保存在私有产物中。

P+预留256是独立描述统计，不参与筛选：smoke原train/validation可容纳2765/180，已选部分1173/174；formal原train/validation5526/232，已选5359/217。因此已选smoke有427/23条、formal有654/0条不能容纳完整预留256；实际目标合格不等于推理容量预检通过。

私有稳定manifest文件SHA `eb4bbfe66966d95fb3a77126e4b3ee248faa66db587422846421e25b7a8242bd`，canonical SHA `ada142fa7ca31b2fa24a22e8d228d847ed645cea6fd028c5d1fd54ffa0567696`。确定性证明SHA `1f2874e279e4816a075ac835cff042cbb3dd7574262fa09932925fcb314c5990`。[公开manifest](../../data/manifests/training-selection.v1.json)只含安全元数据、hash及统计。

## 13例token/mask材料与明确缺项

12:13及12:17 UTC，已有纯Transformers参考环境与已有native环境各实际构建13条序列：10条来自实际选定train并去重，另3条原创final/clarify/refuse协议例不进入训练文件。两个profile的固定模型修订、三个本地来源文件、模板/EOS和参数均按当前OfflineQwenTokenizer核对；每个样例使用其主要profile，重复engine不增加独立分母。结果为**13个独立样例、26次材料序列构建**，完整P/C/IDs/EOS/causal shift/mask/padding及单token辅助文字完全一致；10条原数据例全部匹配历史表示hash。

真实选定train并集6013条的目标全为tool_calls。10条人工材料覆盖7条多工具、4条多目标调用、1条observation历史、1条非ASCII；全部有多条消息，长度747–2048 tokens，右padding桶1024/1536/2048分别3/1/6条。规则先取短长边界及现有特征，再按固定排名补足；不存在的非tool_calls真实目标明确由原创协议例补充，不混入实际数据分母。对照证明SHA `71abf35c788c33031ca6bb0d9ecf3bb1f88cc88dae3b11eea109c587edb55650` 是完整材料记录canonical hash。

私有HTML含完整ModelInput、Action、精确P/C、所有IDs、未padding/右padding attention和loss mask、next-token输入/目标及有效监督分母。13页静态解析核对19968个完整token表格行及每页8个完整文本/JSON块，数据经过HTML转义，无数据驱动script/链接。单token解码只辅助阅读；完整序列文字与IDs是精确依据。独立human-review目录提供索引、13页及JSON、空白review.csv；13行reviewer/verdict/time/notes均为空，manifest SHA `a4681bb8370d5225839913ea6b9f7726c1145af7bdbe6d63edb950b9379187b0`。

**浏览器实际观察NOT_RUN。** 12:20:01.467Z通过CUA请求打开代表性本地HTML；12:20:01.593Z被浏览器URL安全策略拒绝，并明确禁止绕过。停止该路径，没有换浏览器、代理或本地服务器尝试相同导航。完整原始回执JSON SHA `b2abc9c609ccac06554e9a802a7dc3d382aec8c4f8bf7e6e8339f902a75c929e`；拒绝文字原件SHA `57a5937c612587bc11865727fe56934cefedbfe41d2286047c9e0fafb2606b93`。原工具/参数/路径及时间只存私有证据。静态解析不是渲染或人审；代表、最长和非ASCII页面仍需用户实际打开检查。S0已指示保留原拒绝并以实际缺项交接。

## CPU、归档与安装

| 实际验证 | 结果 | 原日志SHA-256 |
|---|---|---|
| 完整tests及既有P00/P02/P03/P01独立组合 | 844 passed / 2 HF-only skipped，52.95s | `cb6c15607788b3c1b04d51ef614960fd50a5db3277f9bfc351cef6002bdd0800` |
| 原R1格式结构与统计（独立调用） | 60 passed，0.10s | `6279136f10e7afff61d1aaf2285e31851be7611224c92cc18592304e0e8aa9c3` |
| 原R1截止时间边界（独立调用） | 2 passed，11.54s | `660844050fe8f40e80f776bdb3c6e1e9f8bcb60429763e155b8783ee8864feb6` |

合计906 passed / 2 skipped，新增63个原创边界测试已包含其中，不与迭代或安装重复相加。沿用原同名文件分组和系统临时测试目录，不修改旧测试或全局收集。已有native环境缺psutil时，只读复用已缓存的锁定7.2.2并核对15个RECORD条目；不安装依赖、不新建环境，测试后模型模块为空。全库ruff、4份冻结契约及350路径公开扫描通过；扫描日志SHA `356d4ebda23e6ecde0eae018e962ccec03d68d5805781ec26bd33ec856107c6f`。文档定稿后的扫描及源码不变映射随最终completion封存。

| 实际归档（bc9db40） | Bytes / 成员 | SHA-256 |
|---|---|---|
| sdist | 231519 / 108 | `6bf81574cace92a9e3734cc8790a47818e05534d5c033951b0477a456e84d431` |
| 默认wheel（同次sdist生成） | 118408 / 54 | `86adee698e490871894f2670d427e83617071b2a2c08c2f7d25cb3f7405bb1ec` |
| 显式sdist重建wheel | 118408 / 54 | `86adee698e490871894f2670d427e83617071b2a2c08c2f7d25cb3f7405bb1ec` |

直接解析全部成员：sdist为107份Git文件加PKG-INFO；wheel为49份生产源码/资源加5份metadata，两个wheel全字节一致。Git字节、METADATA/PKG-INFO、WHEEL、entry point、license及每项RECORD均核对。实际安装本次默认wheel到新隔离target，复用原只读纯默认依赖，使用`-B -I -S`在非源码cwd执行3个原创小输入、声明式选择/HTML接口、CLI help及对原始实际选择的完整verify。4条安装/接口命令均exit0，49份包文件与导入来源核对通过；无可选模型/tokenizer包可导入。安装摘要SHA `fb5c70a3b18b9f600d144d3b7d66fc866007dc22bdd5ae10cb6a8b4a503aac3c`。源码直接wheel未运行，记NOT_RUN。

## 原失败、保全与后续门槛

带完整命令日志的27条验证调用在[机器证据](P02_TRAINING_BINDING_EVIDENCE.json)冻结，准确argv/退出码/UTC和完整日志另存私有；后续公开扫描和最终封存另入completion。保留四条失败：早期HTML测试误将JSON转义文字按原字符串比较、同轮ruff要求普通def；首次全组合缺psutil收集exit2；第二次私有启动器缺main保护导致spawn重复启动pytest，同时私有basetemp使公开目录反例失去前提。第二次主动中断，父测试15 failed/230 passed、exit2，不作为通过计数；旧启动器和全部日志保留，只修私有启动器并恢复系统临时目录后组合通过。已观察到的该轮自有进程均不再存活，未改生产进程代码。

末次保全证明SHA `ba92f162eac7f981b8309c1460cd9ba9c5c19da233f2a9639a41f15dec220acd`：337份基线文件、两份原构建各18产物、旧format-v1-r2的620私有制品/37命令、format-fix-r3的542制品/39命令与原人审填写副本hash全保持。原人审副本仍为 `eee6b377c78eeff7ab82d65dbc0dcf6934013f546e2439a24309b8b847220efb`。保全时本轮私有目录加日志144697818 bytes，低于2GiB；最终封存再次登记实际值。

后续仍须独立R1审查/S0集成、实际页面观察、kris语义与token/mask审查、明确P04配置/GPU预算和真实0.6B/1536容量预检。未加载模型、训练、生成或评测最终集/BFCL；未修改原标签、未执行模型产生的代码、无新GPU/公网/费用/模型数据上传。本材料不能代替未来trainer/collator的真实mask/loss、尾批缩放、梯度或checkpoint验证。
