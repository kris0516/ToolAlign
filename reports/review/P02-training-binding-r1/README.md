# P02-TRAINING-BINDING-R1｜独立技术审查

**PASS，P0=0 / P1=0 / P2=0。** 结论限于固定训练选择的CPU代码、真实tokenizer材料和默认安装包。原D1要求的实际页面观察仍未满足，kris语义及token/mask人审仍待完成；本审查不关闭P02/G-DATA，也不授权P04或模型训练。

R1，gpt-6-astra/max；2026-09-06。审查分支 `review/p02-training-binding-r1`；授权 `5b553b4b7140f4e62209c904bc0b79e94dff8600`，契约plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / ADR-0019，依据docs02/03/16。精确对象如下：

| 对象 | 完整身份 |
|---|---|
| candidate / 本review唯一父提交 | `f4f73c9ac8e004b48a74a80ac00617a01c4da324` |
| candidate tree | `ed7437bf371671a6a01efd324bb8bc1e2d63e294` |
| candidate parent / D1组合测量提交 | `bc9db40bc3d5a26b73b5f2e7dd308f1bb35be6f5` |
| 实现及选择物化提交 | `526f93d4e0878365a6748c593b3e685b9a395384` |
| 原集成基线 | `36b6988af6b4e0125b59fb81b1cea142233e14a2` |

本review commit/tree由包含这些审查文件的Git对象确定，完整值随原生交接及私有completion登记。R1仅新增本目录和[交接](../../../coordination/handoffs/P02-training-binding-review-r1.md)，未修改候选350文件。337份基线、346份bc9实测文件与候选逐字节一致；13条候选变更全为新增。全部30个旧branch保留，未将未去敏旧review引入祖先；审查期间main由S0推进，R1没有合入或改写main。

R1实际运行完整CPU组844 passed / 2 skipped（53.01s）、原格式结构/统计60 passed（0.11s）、原截止时间边界2 passed（11.58s），另有[13项原创边界测试](probe_training_binding.py)通过（110个subtest断言，1.24s）。合计 **919 passed / 2 skipped**；subtest、D1新增63例和后续安装重复均不再相加。两项跳过明确为参考engine专用snapshot cleanup测试；本轮完整回归环境为现有Python3.14.7/native CPU环境。不是双Python CI或真实模型评测。

原创测试使用独立构造的Example与合成长度，覆盖固定seed42/canonical排名、1603条原创输入的1600无放回选择、打乱次序不变、原记录不改、1024/1536/2048及response含EOS256边界、互斥排除、P+256不参与筛选、严格整数/显式成功、错误身份/长度/EOS/缺失/额外/重复/跨split分组、最终split内容立即跳过、小输入build/verify及输出篡改、私有路径、shift/右padding和HTML注入。合成长度没有冒充Qwen测量。

[独立来源与选择核验](review_evidence.py)首先实读并重核S0封存中的3692个路径，随后加入本工作树和必要参考，共4045个不同实际文件路径。最终保全阶段另核4195个路径，集合有重叠，不能相加为测试分母。核验D1本轮1906份私有制品/32条命令、旧620/37与542/39封存；27条公开命令摘要逐项对应原元数据与完整日志。两次build的实际argv、不同输出目录、UTC时间、345份测量源码快照及当前消费文件hash均核对，确实晚于S0在12:07 UTC完成的独立参考。较早命令缺失的结束HEAD、source_epoch或完成时间字段仍按原件缺项记录，没有补造。

原train7515/validation234与历史audit完整绑定，Example/ModelInput/Action/source/revision/source_record_hash/group/split一致；完整原18项产物和第二份原构建均保全。最终test/ood_test只识别split后跳过，没有参与选择、统计或参数决定。R1独立重算排名、选择身份、桶与排除，并逐字段核对D1两次真实物化；没有第三次物化原始全量数据。

| Profile / split | 输入 | 合格 | 选择 | 仅context | 仅response | 同时超限 | 排名排除 |
|---|---:|---:|---:|---:|---:|---:|---:|
| smoke train | 7515 | 3618 | 1600 | 3667 | 77 | 153 | 2018 |
| smoke validation | 234 | 197 | 197 | 20 | 5 | 12 | 0 |
| formal train | 7515 | 6013 | 6013 | 1272 | 158 | 72 | 0 |
| formal validation | 234 | 217 | 217 | 0 | 14 | 3 | 0 |

两次13份稳定文件完全一致，稳定manifest文件hash为 `eb4bbfe66966d95fb3a77126e4b3ee248faa66db587422846421e25b7a8242bd`。两个split中smoke均为formal子集，原Example所有字段/值、group/split均保持。每次物化8027个跨profile输出记录对应6230个不同已选原Example，不能当作8027个独立来源。已选smoke train427条及validation23条、formal train654条不能容纳完整P+256预留，这只是独立统计，未用于新增过滤，也不等于模型容量预检通过。

配置文件逐字节等于S0原件 `579d3d9d9436f4374e7e808dc5b787213157d7ee477bfffd48dac02d35e70a4c`，`CPU_PREPARATION_ONLY`和`training_authorized=false`保持。历史表示测量绑定b33a55f的12份实际Git源码，其中旧loader为 `6d1a4474cf6cdc747de53b365426367e825ea844d3ebf0b1f36e54629a8b1d30`；当前源码/安装包loader为 `f1354c349708c09e82661fbde3d7b9b96df16a5f9634b28097b66973bbe4ddf3`。两种身份分别保存，不改写旧表示manifest或声称旧代码已重新测量。

R1通过[材料检查器](review_materials.py)，用当前候选OfflineQwenTokenizer及已核验的三个本地来源文件，真实运行Transformers参考与native各13例。每例只使用主要profile，实际6例formal、7例smoke；共26次材料序列构建、**13个独立样例**。其中10条为不同的实际选定train记录，另3条原创final/clarify/refuse协议例从未进入选择文件。10条真实目标均为tool_calls，覆盖实际存在的多工具、多调用、observation历史和非ASCII情况；真实长度747–2048。没有虚构真实非tool_calls覆盖。

R1参考/native及原D1两份冻结副本的13组完整记录一致，canonical hash为 `71abf35c788c33031ca6bb0d9ecf3bb1f88cc88dae3b11eea109c587edb55650`；10条真实记录全部对应原audit。P/C、全IDs、唯一追加EOS、P−1开始监督、N−2预测EOS、右padding、attention/shifted mask及监督分母均核对；两种参考过程均未加载模型模块。新参考/native manifest分别为 `8c8cca2b4d024db01d237b436b192bd627e8412669ecf996e4540280ef80e4b9` / `cba6195dc0f2efdc248fc4cae69942b5386a357acac16127500d6a52fcfdbe18`。

四份材料副本的HTML仅做静态解析：每份13页、19968个完整token表格行、每页8个完整文本/JSON块逐值核对，原文和单token辅助文字正确转义，无数据驱动script/链接。**实际浏览器观察0页 / NOT_RUN。** 原浏览器URL安全策略拒绝回执 `b2abc9c609ccac06554e9a802a7dc3d382aec8c4f8bf7e6e8339f902a75c929e` 保持；R1没有重试、换浏览器、文件URL、localhost、代理或间接绕过。原D1要求中的代表、最长及非ASCII实际页面观察仍待用户完成，CPU PASS不关闭此缺项。

原100行语义填写副本和新13行token/mask填写副本截至最后保全仍为0 reviewer / 0 verdict。仅用户可填写reviewer/verdict/reviewed_at_utc/notes；身份列和JSON/HTML保持，冻结reference/native CSV保持。核验明确允许填写副本这些列的合法变化，不把初始空白CSV hash当成永久人审结果；R1没有代填或代签。

R1使用已存在CPU解释器及经过完整RECORD核对的118份缓存构建文件，以 `uv build --offline --no-python-downloads --no-build-isolation` 实际新构建sdist、由同一sdist产生的默认wheel及显式sdist重建wheel。没有新解释器环境、新依赖安装或联网下载。[归档检查器](review_package.py)还独立解析原D1三份归档，检查全部成员/Git字节、路径/链接、METADATA/PKG-INFO/WHEEL/entry point/license及每项RECORD；新旧归档字节相同，实际新运行的UTC和日志另存。

| 新实际归档 | Bytes | 成员 | SHA-256 |
|---|---:|---:|---|
| sdist | 231519 | 108（107 Git + PKG-INFO） | `6bf81574cace92a9e3734cc8790a47818e05534d5c033951b0477a456e84d431` |
| 默认wheel | 118408 | 54（49生产文件 + 5 metadata） | `86adee698e490871894f2670d427e83617071b2a2c08c2f7d25cb3f7405bb1ec` |
| 显式sdist重建wheel | 118408 | 54 | `86adee698e490871894f2670d427e83617071b2a2c08c2f7d25cb3f7405bb1ec` |

实际将**本轮新默认wheel**用`--offline --no-deps`安装到新的私有target，默认依赖只读复用。在非源码cwd使用`-B -I -S`，13项原创测试重复通过、对原实际选择执行完整verify，并实际拒绝config/protocol/representation/audit/data-manifest五种输入篡改。17个ToolAlign导入模块均来自新target，49份包文件全部核对；11种可选依赖不可导入，CLI help正常。安装重复不增加独立测试分母；源码直接wheel、正式trainer/collator及训练均NOT_RUN。

Ruff全库和本目录显式检查、四份冻结契约通过；最终公开内容扫描及Git对象核验随发布封存记录。CPU回归使用系统临时目录和main保护，不改变原测试前提。末次保全时37个有记录PID均已不存在，包括原D1失败的12个PID及本轮deadline探针直接核验的4个已回收子进程；两项资源跟踪进程也已退出。1540份本轮保留制品及测试临时文件共157866720 bytes，低于2GiB；这是该时刻保留量，不是峰值内存或吞吐测量，后续小型报告/封存另计。

四条D1原失败原样保留：HTML断言和ruff各exit1；缺psutil收集exit2；旧私有runner缺main保护且basetemp不当的中断exit2（15 failed / 230 passed）。本轮R1也保留三条辅助核验失败：检查器初稿括号语法错误、对早期元数据`source_epoch`及`git_head_after`列的错误必填假设各exit1；失败脚本和日志均封存，修正的是R1检查器，候选未改。字段缺失仍如实记录，不以修正后的通过覆盖失败。探索性读取中误写旧脚本位置及未命中查询未计入测试，没有伪造单独日志hash。

精确命令参数的去敏映射、UTC、退出码、日志/原元数据hash及证明索引见[机器证据](evidence.json)。原始路径、逐例身份、源码来源、进程ID和完整日志只通过本机交给S0。最终CI、main集成验证、实际页面观察、两项kris人审、P04实际trainer/collator/mask/loss及0.6B/1536容量预检均不由本次技术PASS代替。
