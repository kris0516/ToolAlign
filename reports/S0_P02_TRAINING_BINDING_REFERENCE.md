# S0训练绑定：独立选择身份参考

状态：REFERENCE_CALCULATED；已与D1随后两次实际物化逐项核对通过，并核对13例既有数组/静态HTML及人工副本，范围见下文，实现整包尚未验收。D1的[P02-TRAINING-BINDING](../coordination/tasks/P02_TRAINING_BINDING.md)仍在实施，R1未派发。固定配置、原数据、G-DATA人审和P04授权状态保持。

2026-09-06 12:06:45–12:07:01 UTC，S0在`f02de2461e721a9794dc5d4fa7705f17220d7ca9`实际执行私有参考检查器，Python 3.14.7，exit 0，用时16.44秒。检查器没有读取或导入D1正在开发的选择模块。契约验证来自已验收的S0源码，排名与身份编码按固定规范用标准库独立计算。

## 输入与实际检查

先核对配置`579d3d9d9436f4374e7e808dc5b787213157d7ee477bfffd48dac02d35e70a4c`、原manifest文件`c728dfe385e340fadf1e5949976c012709fc10a1dbca9010548edf74785259e5`及其canonical身份`87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756`，以及原train、validation和audit完整字节hash。audit身份仍为`36b8cbfe6773c08f7a28521a99ed8783723a8f7fa3b2a3fa87915d8d1d871aff`。

实际检查7,515条train与234条validation的冻结Example契约、唯一身份、split/group隔离，以及每条对应audit的来源、Example/ModelInput/Action hash、共同绑定和格式身份。核对原表示成功标记、parser Action hash、整数长度、P+C含EOS=N、唯一追加EOS、监督边界与按长度重算的mask hash；缺失、重复或错误身份会失败。其他audit split仅在识别split后跳过，不参与候选、排名或统计。此次没有重新分词，不证明当前tokenizer实际输出。

排名严格为`canonical_hash(["toolalign.training-selection.v1", 42, example_id])`，按hash、example_id升序；smoke合格train取前1600，其余按已授权规则全取。逐例ID、Example hash、排名和最小padding桶参考只保存在私有文件，未生成训练消费的Example JSONL。

## 固定规则的预期结果

以下是S0由原输入算出的参考，不是尚未交付的D1物化结果。四种长度分区互斥，合计各自完整分母；context包含EOS，response上限256也包含EOS。

| Profile / split | 完整分母 | 合格 | 仅超context | 仅超response | 两者均超 | 预期选中 | 合格但排名未选 |
|---|---:|---:|---:|---:|---:|---:|---:|
| smoke / train | 7515 | 3618 | 3667 | 77 | 153 | 1600 | 2018 |
| smoke / validation | 234 | 197 | 20 | 5 | 12 | 197 | 0 |
| formal / train | 7515 | 6013 | 1272 | 158 | 72 | 6013 | 0 |
| formal / validation | 234 | 217 | 0 | 14 | 3 | 217 | 0 |

| Profile / split | 1024桶 | 1536桶 | 2048桶 | 选中后P+预留256可容纳 | 选中ID顺序canonical hash |
|---|---:|---:|---:|---:|---|
| smoke / train | 429 | 1171 | — | 1173 / 1600 | `db96988c1968e1232e93adcbe974c30a5a1b76681ff68c66edca8af039af533c` |
| smoke / validation | 74 | 123 | — | 174 / 197 | `cd82b5142a6575e51d1654dc179ea9fe85d6c18f6fb10eb4d9553c0b464c899b` |
| formal / train | 985 | 2633 | 2395 | 5359 / 6013 | `43bbe027d65b37845c3a551460eb632b87be1bf461a3cebe783247a50936a8a9` |
| formal / validation | 74 | 123 | 20 | 217 / 217 | `f8ca56d242761da1ed5a23bbc2c5dba443c1a81f657c0c2165538ac140ad6ca5` |

两个smoke集合分别是formal对应split的子集；四个集合的Action均为tool_calls。完整候选分母中P+预留256可容纳的数量分别为smoke train2765/validation180、formal train5526/validation232。预留统计不新增选择条件，也不是未来模型推理容量验收。smoke选中train有427条不能在1536内预留完整256 token，仍按原固定规则保留；后续模型容量与生成预算须另行验证。

## 原始证据与限制

实际命令的角色路径表示为：`PYTHONPATH=<S0_WORKTREE>/src PYTHONDONTWRITEBYTECODE=1 <S0_WORKTREE>/.venv/bin/python -B <S0_PRIVATE>/evidence/p02-training-binding/compute_selection_reference.py`。原始命令、cwd、时间、解释器、完整日志及逐例参考均在S0本机保留。

| 制品 | SHA-256 |
|---|---|
| 实际检查器 | `043e9f93f0873d7e1731716a6c323d5734ee5725a03ef572d0dcaeaf1ce2c96e` |
| 命令metadata | `e1dc0253615c312195a3950db189a746424e883afcf4ba1ec78f15445bcd1e2d` |
| 完整stdout/stderr日志 | `b76b0bc8787995d005f15128c9aa365a4ff3a9d9bff7c5e48afd15dea3807881` |
| 参考摘要 | `0f82eac7f0b20a9a7d64168a2368952a349a944a1a741807b0c4c94148633f69` |
| 私有逐例身份参考 | `e7e95f70d029a19867f44342d51cc6de80b36f46cdf684c92da19c23a6737bc2` |

此次未导入可选tokenizer或模型模块，新分词次数0、训练Example物化文件0。没有执行D1候选、13例真实tokenizer材料、安装接口、独立R1或模型训练；这些仍须在实际交付和后续授权中分别验证。本参考不重复记作原8,228行测量，不改变旧报告或人工填写副本。

## 12:16 UTC：与两次实际物化交叉核对

D1随后在实现提交`526f93d4e0878365a6748c593b3e685b9a395384`执行两个真实build，使用不同的新私有输出目录：A为12:11:00–12:11:36 UTC、36.53秒；B为12:11:54–12:12:30 UTC、35.87秒，均exit0。S0读取实际build入口与命令记录器，核对两份原metadata和完整日志、各自run时间/目录；同一摘要输出导致两份stdout具有相同hash，并未用它单独推定两次运行。两次实际来源快照的345份文件均与精确526f93d的Git字节一致。

S0于12:16:13–12:16:17 UTC实际运行另一个只读交叉检查器，exit0、4.49秒，核对384个文件路径。每次物化的四组Example逐例与原train/validation全部字段及先前参考hash一致，ID顺序、排名、最小桶、sidecar完整历史audit、完整排除IDs与统计均匹配独立参考。每遍8027条输出记录包含smoke与formal的重叠，不能相加成8027条独立来源样本。两遍各13份稳定文件（12份输出加manifest）字节相同；各自run元数据保持不同的实际时间和目录。

共同稳定manifest文件hash为`eb4bbfe66966d95fb3a77126e4b3ee248faa66db587422846421e25b7a8242bd`。S0核对器SHA为`47874c365b3d9146f81c9eabc7c018889523b4a56fd4e2e4a8c29df19f452db4`，命令metadata为`994eb5e214bdf55ce0a49d2522fd266afb3a63b2d4bc873fb4cbac19293a417b`，完整日志为`ac46a6b87bff813f4bb4aeae67ce985390f8986b986cbb1109cb1aff941d1a47`，证明为`b96605d2cb167db8ae8b4e045182b6bb2b22365fbfcf616f9514299ca6ed74f2`。原检查器和先前身份参考保持原hash；此次S0没有重新物化或分词。

该结果仅为已出现的选择产物交叉核对，不能代替D1完整候选、13例真实token/mask材料、默认安装、完整CPU或独立R1。D1原轮仍ACTIVE；其checkpoint不是最终验收提交，后续可执行变化必须在最终交接中重新绑定。

## 13例材料静态核对与浏览器限制

12:33:03–12:33:04 UTC，S0实际执行静态材料检查器，exit0、1.11秒，核对94个文件路径。读取D1两次真实measure的完整命令/日志、所用11份相关源码/fixture快照与Git身份、来源文件，以及reference/native各13份完整JSON/HTML。逐例检查原已选train身份或原创协议fixture、历史audit、P/C/完整IDs hash、EOS、shift、loss/attention、右padding与有效监督分母；静态HTML中的完整文字块和每行token表格均与JSON相同，数据保持转义。两种engine的完整记录一致，独立样例分母13，重复测量26。实际10条训练样本长度747–2048，另3条协议例不进入训练。

D1的reference测量日志`87a6034dd12b320e525937e10aa314f4c44da945db846b421a4a3c24eed0c59c`含真实Transformers tokenizer-only提示与成功结果；native日志`8abfb5dcb2791ba3e4e7158f660f6d2d50979a824d26077a56efc289cb297a67`单列。S0最初将带提示的整份reference日志直接解析JSON而报读取错误，原日志保持；后续读取完整原文并只解析最后的结果行，未改D1命令或测量。reference记录绑定526f93d，native所用来源快照对应bc9db40；两者实际消费代码相同。S0本次只核对已有测量，新增分词0。

静态检查器SHA为`5f1643fd3c14f6cc17d720a2aaffa4d1e0e89272a0306d2a09266a2d3c83e9e1`，命令metadata为`5d9fc2fad9a042cc0cb911397275984584ae23087524db872fa395a5dcbd03af`，完整日志为`59e1d299079c1a2fbe99e5ecbb5ce4168b489ca71a9969bdcfd2201054f2513c`，证明为`f33c7f536aa1b0c8acdb1a243d09604f91f96e18e3c05826c07875d4c2e93b4d`。reference/native manifest分别为`9f239739d64bb0cbaf83248d7624489af8e70f34cd1519e71f5055f425b302cb`与`420c0171d4cf8ab3f773a27267bebde4bf1751e2722a02d53d5edcb4f529a56a`。

S0另直接核对人工副本的28份文件：26份JSON/HTML及初始空白CSV与reference逐字节相同，索引身份已记录；13行reviewer/verdict均为空。证明`d36eabac859ccc96f412bada5335f3949c3d63ec0161ac8b2e4f2cee21393318`。本机审阅说明已准备材料入口和代表、最长、smoke边界、非ASCII样例；用户填写副本中的reviewer/verdict/time/notes是预期可变的人工输出，case_id/category保持，冻结reference/native证据不改。

实际浏览器渲染仍为0页、NOT_RUN。D1在12:20:01 UTC调用浏览器打开本地file URL，被浏览器URL安全策略拒绝；原回执明确禁止通过替代浏览器、间接执行或其他绕过方式达到同一结果。S0已核对完整原始回执JSON `b2abc9c609ccac06554e9a802a7dc3d382aec8c4f8bf7e6e8339f902a75c929e`和原文`57a5937c612587bc11865727fe56934cefedbfe41d2286047c9e0fafb2606b93`。此次安全的静态检查未执行浏览器动作，不证明实际显示；实际页面观察及13例人工判断仍需kris完成。代码独立R1与完整候选交接继续待完成，不能以这项静态通过放行P04。
