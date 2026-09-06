# S0 P02训练绑定独立验收与隔离集成

2026-09-06，状态：**ACCEPTED（CPU技术范围），最终CI/main待验证**。[PR9](https://github.com/kris0516/ToolAlign/pull/9)保持Draft，配置仍为CPU_PREPARATION_ONLY / training_authorized=false。原实际页面观察、语义及token/mask人审尚未完成；本记录不关闭G-DATA或授权P04。

| 对象 | 精确身份 |
|---|---|
| D1完整候选 | `f4f73c9ac8e004b48a74a80ac00617a01c4da324` |
| R1独立PASS | `40252f8517f3c7ac8ddc0340847946ac902200e1`，唯一父为上述候选 |
| R1 tree | `a5ad2ac705e382b21633ab216d48f08c9c02de68` |
| 集成时main | `d63e5aea79e022e2dc77ae7e4b21e266224b7494` |
| S0实际普通合并 | `0f3d04f6ffee8ba77b3383ebd38459512cea718e`，父为d63e5ae与40252f8 |
| S0实测tree | `dae84fddc3b095e5e14dfe30cf02229457d4ccd8` |

R1按完整5b553b4、gpt-6-astra/max独立审查，正式PASS/P0/P1/P2均0，并已原生completed/idle。仅新增七份审查文件，原350份候选保持；[审查报告](review/P02-training-binding-r1/README.md)、[机器证据](review/P02-training-binding-r1/evidence.json)和[交接](../coordination/handoffs/P02-training-binding-review-r1.md)保留原SHA。

13:58:35–13:58:41 UTC，S0核对5734个实际文件路径、26条已结束原命令、1562个最终封存制品及完整Git对应关系；原26条中三条R1辅助失败保持。最终completion为464716 bytes/SHA `b83d409a266dc14e9cb612b5e9a9912625432ac82024f7ef73e4c246faf1dee5`，含封存总159979680 bytes。另核对44个记录PID已不存在，30个旧branch保持，未引入未去敏旧审查祖先。S0交接证明SHA `4b9552b1032c478b91609707ff36411b47920ff3ff8d3296175866e46a38fb1b`，实际命令exit0、5.92秒、日志SHA `ffb15a22d6c2fd3d66ca1a4b1a81aec5e0f2493d2a2a06600724f493e8f814a2`。集合存在重叠，不相加为测试或独立来源分母。

R1独立重算原7749条允许输入及两次真实物化，smoke1600/197、formal6013/217保持，6230个不同已选原Example、8027个跨profile输出记录。配置579d3d9、稳定manifest eb4bbfe6及先行S0参考一致。原目标全为tool_calls；10条实际选中train与三条单列原创协议材料分别记录，协议例未进入训练选择。R1参考/native各对同13例真实构建一次，共26次、13独立样例；全部数组与D1原件一致，records hash71abf35c。实际页面观察仍0页，完整静态HTML核对不能代替用户判断。

S0在新隔离worktree普通合并后，实际运行四个不重叠CPU组：

| 组 | 实际结果 | pytest报告耗时 |
|---|---|---:|
| tests及既有P00/P01/P02/P03独立回归 | 844 passed / 2 skipped | 54.79s |
| 原格式结构与统计边界 | 60 passed | 0.15s |
| 原截止时间独立边界 | 2 passed | 11.62s |
| 本轮R1原创训练绑定边界 | 13 passed / 110 subtests passed | 1.41s |

合计**919 passed / 2 skipped**。两项跳过为native环境中的HF-only snapshot cleanup；110 subtests、D1新增63例和安装重复13项均不再相加。这是Python3.14.7的本机CPU验证，不是模型性能测量或最终双Python CI。原R1的919/2保持其独立执行时间；S0没有用同一日志改写执行者。

Ruff全库及新增报告显式检查、四份冻结契约、363路径公开扫描通过。全部363份实际Git文件和每条检查开始/结束的源码hash一致，main的343份内容保持并加入候选13文件和R1七文件；所有src/tests/configs及107份sdist输入/49份生产包文件与被审候选对应。没有更改生产代码、测试、参数或旧审查来取得通过。

S0只读复用已核验的缓存构建依赖，用现有CPU解释器实际执行离线默认构建和显式sdist重建，产生三份新归档。逐成员/Git字节、路径/链接、PKG-INFO/METADATA/WHEEL/entry point/license及完整RECORD核对通过：

| 本轮S0实际制品 | Bytes | 成员 | SHA-256 |
|---|---:|---:|---|
| sdist | 231519 | 108（107 Git + PKG-INFO） | `6bf81574cace92a9e3734cc8790a47818e05534d5c033951b0477a456e84d431` |
| 默认wheel | 118408 | 54（49生产 + 5 metadata） | `86adee698e490871894f2670d427e83617071b2a2c08c2f7d25cb3f7405bb1ec` |
| 显式sdist重建wheel | 118408 | 54 | `86adee698e490871894f2670d427e83617071b2a2c08c2f7d25cb3f7405bb1ec` |

归档全字节与R1/D1既有归档相同，S0有独立的新构建日志和UTC，并未复制旧归档冒充构建。源码直接普通wheel仍NOT_RUN；CI canary的direct路线另计。归档证明SHA `c2761eeb4384e013f3739b0cc6b428e8b34d548c96d9f5bb49cdd859c2c0eb7c`。

本轮新默认wheel已实际离线安装到S0新target，依赖只读复用。在非源码cwd使用-B/-I/-S复用原R1安装探针：49份包文件与当前Git匹配，17个ToolAlign模块全部来自新target，11种可选依赖不可导入；13项原探针重复、原实际selection完整verify及五类固定输入篡改拒绝均通过。S0新增原始数据物化与tokenizer构建均0，不刷新R1的真实13例或CLI help时间。

本轮S0原始归档检查输出了PASS证明，但记录器的receipt路径与该证明同名，随后FileExistsError、外层exit1。原脚本、证明、stdout和失败回执保留；原开始/结束UTC及子进程退出码未成功持久化，保持缺项。S0只复制检查器并改用新证明文件名和独立receipt标签，重新解析同三归档实际exit0；没有重新构建或修改归档。该S0辅助失败与D1四条、R1三条原失败分别保留。

以下为本轮14条实际成功命令的UTC及完整日志hash，命令argv、cwd、环境、363源码hash和退出状态另存本机原始receipt。归档外层失败作为独立保留记录，不混入成功表；汇总核验前有13条成功receipt。

| 命令记录标签 | UTC开始–结束 | exit | 原日志SHA-256 |
|---|---|---:|---|
| cpu-combined | 14:03:48–14:04:43 | 0 | `1f8de2b07af0cf06df5fad24a604747d133dafa5b443b0825d0a915e5f21d399` |
| independent-deadline-review | 14:04:15–14:04:27 | 0 | `d2cb4efd13f239e23ff58de3cbb490b6cca671b73df5cf4dc0b05ad455903274` |
| original-format-review | 14:04:15–14:04:15 | 0 | `4ec47ac4ace25090235b15d09739fbbf184204c0c09ecb2075d36b83a2bf5441` |
| independent-training-binding-review | 14:04:15–14:04:16 | 0 | `9b0da86f0ddf95c58d46e8cd10f19524bd6e18a2861f678bbd9a18ff412a5897` |
| ruff | 14:04:15–14:04:15 | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| ruff-new-reports | 14:04:15–14:04:15 | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| freeze | 14:04:15–14:04:15 | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| public | 14:04:15–14:04:21 | 0 | `b154dda493cb22d3e3301b85f8cc36168134d9109c006a7ecbf548e77151f7e7` |
| build-default | 14:04:44–14:04:45 | 0 | `966788833cc9907e7e090c4f97396c2e26dabc14e972aacdf951482d51365ce4` |
| build-rebuilt | 14:06:18–14:06:18 | 0 | `13703a4f53fc419ddb23729bb9e29d529dae36b8aee372af03acaebd778de61c` |
| install-default-wheel | 14:07:17–14:07:17 | 0 | `8832d478c2b47afd5cbe4d422b7d634f3ebc797f038a69681e2019d504fb8851` |
| archive-verification-r2 | 14:08:24–14:08:26 | 0 | `f25f4c89806508baecf599fd3f2a914e7773198dc2b3b3871b5613222acbd20d` |
| installed-api-r1 | 14:09:31–14:10:08 | 0 | `16acb29394e577107efa13a4825158cfa14dcb1a16a70890cc303f980c458e14` |
| integration-evidence-check | 14:13:04–14:13:17 | 0 | `e16c5e4559a9014696bfc4754437541c1afc3349c7aa1eb2a53b206e564587c6` |

14:13 UTC汇总核验exit0，证明SHA `961e7d7865fd3a0c0fc2a0fafaa7147bf81ff15d9df17c2a64d3fe5dd4e44865`。S0本轮保留文件瞬时大小144720851 bytes，低于2GiB；该预算观察时当前日志/证明仍在收尾，不是不可变制品seal或峰值内存。四条本轮截止时间子进程记录确认回收及目录清理，记录PID当时均不存在。共享GPU锁实际未持有，没有新模型加载/GPU作业、环境或依赖下载、费用、推理服务或模型/数据上传。

同次核对原语义100行、新token/mask13行填写副本仍0 reviewer/0 verdict。kris已收到请求；合法人工字段可填写，身份和冻结HTML/JSON保持。原URL安全策略拒绝回执和代表/最长/非ASCII实际页面缺项保持，无绕过。**最终CI/main验证、实际页面观察、两项人审、G-DATA及P04真实trainer/collator/容量等仍未关闭。**
