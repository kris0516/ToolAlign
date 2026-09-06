# P02 政策转换与真实双重建

2026-09-06；D1；分支 `work/p02-data`。生产实现精确提交 **`9be07a5b88d1dac1a6e1fea30358af1049b1119a`**。该提交生成两份独立、非空的有效数据包，18项实际产物全部同 hash。**状态为 pipeline 自测交付、kris 与独立 R1 待审；P02/G-DATA 未 VERIFIED。**

完整命令、退出码、原始日志 hash、来源/政策/产物身份与四种转换分母见 [机器证据](P02_POLICY_BUILD.json)。可公开的 build manifest 只含元数据与 hash，见 [toolace-policy-build.v1.json](../../data/manifests/toolace-policy-build.v1.json)；未公开任何原始记录或转换数据。

## 实际结果与排除会计

主源 ToolACE revision `6bda777c88d21e5a204703c1ee45597a8fa4f734`，11,300条来源、13,819个 assistant 决策。固定政策字节 hash 为 `b8c4cd238bbf27d3378dadcd4130ac44c4c991ace6315bf385f104c4f98f72f7`。原始副作用保持 unknown，所有记录为历史监督，execution_binding=none；未执行源工具。

| 项目 | 实测数量 |
|---|---:|
| 原始记录 / assistant 决策 | 11,300 / 13,819 |
| 规范化前排除决策 | 5,505 |
| 合法规范化候选 | 8,314 |
| 跨旧组的规范化 schema 隔离决策 | 53 |
| 转换后完全重复排除 | 33 |
| 最终有效决策 / 不同来源记录 | 8,228 / 7,662 |
| 不同原始工具 / 可转换工具 / 拒收工具 | 17,961 / 16,650 / 1,311 |
| 最终数据中的不同工具 | 15,105 |
| 可转换工具出现次数 | 31,822 |
| 去重可转换工具的 typed default annotations | 5,282 |
| 填参、类型强转、实际工具执行 | 0 / 0 / 0 |

会计闭合：13,819 = 5,505 + 8,314；8,314 = 53 + 33 + 8,228。没有因8192上限、无法测量或不稳定 tokenizer前缀而剔除的真实候选；对应拒收行为由原创负例测试覆盖。

规范化前互斥主原因：action_kind_unlabelled 3,727；ambiguous_tool_names 128；call_parameter_invalid 7；call_syntax_unsupported 33；call_value_not_json 115；invalid_history_prefix 14；out_of_policy_arguments 2；policy_default_conflicts_with_schema 327；policy_explicit_open_object 1；policy_history_observation_unreliable 23；policy_schema_keyword_unsupported 1,053；policy_schema_properties 10；policy_schema_type_unknown 63；policy_source_call_parse_error 1；policy_tool_contract_rejected 1。主原因按稳定排序分配；重叠理由不相加充当分母，例如 unsupported_tool_format 共518、未知 schema关键词1,308、默认值冲突434、历史前缀问题337、源调用 parse错误334个决策，完整见机器证据。

1,311个去重工具的首要拒收为：未知关键词1,059、默认值冲突203、未知类型30、properties问题17、显式开放对象1、wire契约拒收1。原始 strict schema问题仍保留诊断计数，但不再用其受政策支持的 dict/default/缺失元数据等问题冒充当前拒收。

最终全部为有明确可解析目标的 tool_calls；不把无 action-kind 真值的自然语言编造成 final/clarify/refuse。书写体系分布为 latin 8,220、han_and_latin 8，这只是字符启发式而非语言识别准确率。实际目标调用总计15,073次，1个调用的决策4,800条、2个1,382条、3个1,029条、4个772条，其余5–12个调用共245条。

## 分组、split 与完整追溯

所有旧来源分组与 assignments 字节保留：3,517组，最大组6,716个不同来源。原始近重复检索报告134条边；共享工具/schema会形成大组，隔离优先于80/10/10条数比例。

新增规范化 schema 语义审计检查9,377个键，发现11个跨旧组键，其中4个跨split，涉及64个不同来源。所有相关来源均隔离，影响其中53个合法候选；不重命名组、不重新切分，也不按样本比例挑选保留一边。最终原始source/tool/schema/template/group与新增规范化schema键交集均0；近重复算法仍不保证穷尽语义等价。

| split | 原始来源暂定条数 | 最终有效决策 |
|---|---:|---:|
| train | 10,033 | 7,515 |
| validation | 411 | 234 |
| test | 381 | 215 |
| ood_test | 475 | 264 |

每条有效 lineage 关联原始来源 hash、原工具 hash列表、政策原字节hash、规范化工具/example hash、target turn、原组/split、系统变更、历史/目标名称映射、原参数 hash、训练长度/sequence hash。全部原工具保留私有完整副本、字段变化理由和typed defaults。tool observations的原始结果仅作为历史证据，记录 executed_here=false。

[产物完整性脚本](../../tests/data/verify_policy_build.py)对最终8,228个example、16,650份工具lineage、18项artifact逐项检查，并从原始来源重新解析对应调用：15,073个目标调用、632个有效前缀内历史调用的参数 hash逐条不变。人工样本中的114个example与最终数据逐字段相同。该检查是worker完整性检查，不是独立R1或语义正确性通过。

## 实际训练长度

官方 Qwen/Qwen3-0.6B tokenizer revision `c1899de289a04d12100db370d81485cdf75e47ca`；tokenizers 0.22.2 / Jinja2 3.1.6；只读本地tokenizer文件，没有模型。口径 `qwen3_non_thinking_concat_one_eos_v1`，完整渲染、整体encode(prompt+completion)、稳定前缀、额外一个EOS、无尾换行；原始隔离表示长度仍单列。

| Token项目 | P50 | P90 | P95 | P99 |
|---|---:|---:|---:|---:|
| prompt | 849 | 1,404 | 1,600 | 2,014 |
| completion（含额外EOS） | 68 | 193 | 235 | 345 |
| total | 938 | 1,520 | 1,725 | 2,136 |

8,115例总长≤2048，113例在2049–4096，4096以上为0。聚合边际token占比：prompt不含schema 21.5101%、schema 68.8870%、completion 9.6029%，分母为8,228个可归因有效决策。P02允许窗口8192，但后续训练必须按实际模型配置绑定manifest并处理自己的窗口；本报告不声明训练已运行。

此前16个原创fixture的HF tokenizer独立API对照与两个前缀合并拒收详见 [CPU衔接报告](P02_TOKENIZER_ALIGNMENT.md)；本次355项实际CPU回归包含全部17项真实本地tokenizer检查，无skip。

## 两次真实构建与命令证据

两次都在生产提交9be07a5上，从相同官方来源、tokenizer、政策、种子17、相同参数实际运行，分别指向空的私有目录；未复制构建产物。A耗时127.811秒，B耗时128.544秒，退出码均0。

- 共同 canonical build manifest hash：`87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756`。
- 两遍构建日志 hash：`cf219eed695c71643022267271551e1a52399dbea372307784190cc31ece589b`；内容相同，实际命令、启动时间和耗时各自记录。
- examples.jsonl：`d45c815e9b775249c642cd3c9f624c28e7ab6505425cd6c009bfb06402c8f21f`。
- lineage.jsonl：`3f6a8db88a77b6df02c58c538471bbfb157a3fd9655c6a79160c0ae345a38f5c`。
- assignments.jsonl：`51ce05ecbd8a986c3ea1b585f1a1b186dd6e94d2bcc3ce5b498ccdcf40ded3db`，与旧严格检查点完全相同。

compare重新读取两边18项实际文件并校验hash，退出0，日志 `dfb71e8a3660e4b535c18ee5faa7783e6116860c461ea99014bae996b4b305d0`。旧 checkpoint-a/b 的14项产物也全部重新校验未变。

| 校验 | 结果 | 原始日志 SHA-256 |
|---|---|---|
| 真实tokenizer环境，全仓与既有独立探针 | 355 passed，退出0 | `c3e755ca9ce022f33655283bb9a32f99a5add6cc0ce597b6966c110d79a6d8ed` |
| 核心环境 pytest | 163 passed / 17明确skip，退出0 | `4edc37381843c379b997542e4ecf1bf7a48f6716ae825414f86b7b38365fbe08` |
| 产物/原始参数/人工包完整性 | PASS，退出0 | `4a55e7eaba95cfa9fd2898cef97d224a2320f6bec167ab5550090ec36774f47b` |
| ruff | PASS，退出0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| 冻结契约四文件 | PASS，退出0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| uv build --wheel | PASS，退出0 | `80e16a0917ab4f1a266a0da6b5103979a00ae1febef9f131007c81086f91a859` |

最终公开内容扫描在完整证据暂存后执行，结果写入机器证据与交接。没有修改公共依赖/契约/configs；S0合入的既有公共变更在基线链中明确记录。

## 人工材料与尚未通过的门

冻结包内 human-review/ 包含离线HTML、100个不同最终有效来源的samples.jsonl、114个有效决策、34个分层标记和全空review.csv。抽样覆盖split、语言、工具数/并行调用、多决策、历史observation、defaults、时间上下文、转换规则及长度桶。每条展示原始record、转换后完整example、工具逐字段变化、系统规则、参数/工具可逆映射与未绑定执行状态。另附排除代表；它们不计入有效审查数量。

HTML经过转义、CSP/无脚本/无外部资源与100条页面结构检查。内置浏览器URL政策拒绝本地文件地址，因此**实际页面渲染未验证**；未绕过该限制。CSV中的reviewer、时间、verdict未填；accepted_examples_reviewed=0、mislabel_rate=null、P05偏好审计NOT_RUN。

S0收到精确私有目录后安排kris审阅。请复制blank review.csv到单独私有提交目录填写，附冻结manifest和sample hash；原构建目录作为证据保留。独立R1、S0合并/集成、人工质量门及训练配置绑定仍未完成，本worker没有自签验收。未执行增强、训练、BFCL、正式评测、推理服务或模型/数据上传。

## 失败和资源记录

第一次扩展回归354PASS/1FAIL，因为worktree尚无wheel。随后默认 `uv build` 的sdist将6,651个私有成员包含进归档，因绝对venv symlink拒绝解包；生成归档107,953,843bytes、SHA `5154c83cbf57482ecab0375dbc064edaf195bb9d47f73a24d2a0d1088cca5026`，已私有隔离，未上传。S0确认属于其另行处理的公共打包问题；本worker不改公共配置、不再运行旧sdist命令。显式wheel构建后355项全部通过。

第一次compare误在B构建退出前执行，FileNotFoundError/退出2。保留该日志，等待B实际退出0后重新compare18项全部通过。上述失败的精确command/exit/log hash均列入机器证据，未把失败试验移除。

数据/环境/证据总磁盘测得1,190,912KiB，约1.136GiB，低于5GiB；其中包含已隔离的失败archive与两次真实完整构建。所有工作为CPU，未加载模型或使用GPU租约。

最终证据暂存后公开扫描：退出0、143个路径（index与worktree），日志SHA-256 `7d8ae7f38be43e923ac84e4e98386748005708e6eb4b7a88a056a27a10afbb9c`；启发式检查不替代完整隐私审查。
