# S0训练绑定：独立选择身份参考

状态：REFERENCE_CALCULATED；供D1候选交付后核对，尚未接受实现或物化产物。D1的[P02-TRAINING-BINDING](../coordination/tasks/P02_TRAINING_BINDING.md)仍在实施，R1未派发。固定配置、原数据、G-DATA人审和P04授权状态保持。

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
