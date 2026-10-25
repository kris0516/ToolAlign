# P04 冻结 v3 数据与审阅数组 CPU 衔接

**READY_FOR_REVIEW_CPU。** 新入口已把冻结 v3 数据绑定为四个不可变 `SelectionView`，并将原 Q1 审核的 13 例完整数组转换、导出和回读为现有 `Batch`。源码与默认安装包的固定消费均通过，全部位置和绑定字节一致；新编码与实际优化均为 **0**。这是 T1 自测交付，尚无本候选的独立 R1 结论。机器可读结果见 [对应 JSON](P04_SFT_DATA_V3_CPU.json)，SHA `0650cefdf8230c35e6ca8dc4f9aaeb82a89a07f4990314ff819b28ed6d4372ef`。

任务 `P04-SFT-DATA-V3-CPU`；分支 `codex/p04-sft-data-v3-cpu-r1`；code_base `48be4352bbad53ced5af84186edac036dd0ff2ca`，原授权 `0fa77e228021091e357505a0e81a5d3ba0777928`。生产实现固定在 `bfdf2a256065d5396e6f7a4860fd7c7506f5c278`；后续仅补本报告和交接单。契约为 `plan-v0.1 / coordination.v1 / toolalign.contracts.v1`，格式为 `toolalign.action-json.qwen3-message-roles.v1`。

**数据与审核绑定。** `prepare_v3(*, sft_config_path, input_manifest_path)` 只接受精确配置 `e27a7d4bcdd378944af56559833c3bcd10f601b689a75f1daec96b884bd780c1` 和输入 manifest `08e865ff98bd476c94153033bc192664d72cee64443184576532c0289a610dd7`。609 成员含 603 只读引用、6 精确副本（320,921 bytes）；先核大小、类型和原字节 hash，再读允许解析的内容。三份 final/test/ood payload 只 hash，不生成内容 view。已审 `quality_exclusion.verify` 只读重建期望字节，实际数据物化为 0。

原 R1 `dbd11d03e69c650efdb330f79ec380dd9914fa89`、Q1 `7941f1f56519ea2eac437c669ac2c6445a0329f6`、两级 Q1 seal、S0 当前数据批准及 82 项关闭台账另行绑定。审核身份为 **Codex-AI(Q1)**，沿用 `PASS_WITHIN_FIXED_Q1_SCOPE`；原 D1 pending、CHANGES_REQUESTED 与 `training_authorized=false` 字段保持原字节。当前 G-DATA 的冻结批准不赋予优化权限。

| view | 实际条数 | 有序身份 SHA-256 |
|---|---:|---|
| `formal/train` | 5938 | `93c41855d3b9fd14a33ec83b9515e6cf96d3791c674ad39bc7bfa55c2bc366bb` |
| `formal/validation` | 213 | `187b2e23a92d7638049ba1b7ef3572232563e8af52e6e5b6a75997ebe6f0a431` |
| `smoke/train` | 1583 | `bb9e01d8da0e8a61bded075d2ddf530eb1c0a2a6baf0fd0560d0fa8092ca6f5d` |
| `smoke/validation` | 194 | `870108febc3d3e8465d6a3a84086bfb2f3659c3b728196101669e620c67918ab` |

有效全集为 train 7,419 / validation 230。原 JSONL 行先逐字节校验，随后 view 的规范化 buffer 作为新的内存表示。三代身份分别连接连续 v3 `selection_rank`、原 v1 `parent_selection_rank` 与 v2 `previous_selection_rank`；按完整来源过滤并保留原稳定次序，同 group 的其他来源不被误删。不补选到 6,000，不改变 split/group 或晋升 staging。

**完整材料数组。** `rebind_review_arrays(prepared)` 将 native/reference 两 engine 的 26 原记录按 13 唯一例连接。Example、Action、messages、audit、case/profile/rank、quality revision、完整文本、7 组未 padding 数组、6 组 padded 数组、EOS、next-token shift、mask 和所有含 padding 的 token_texts 均逐类型与逐位置核对。经已有 `Sequence`、`collate_sequence` 生成的 `Batch` 与原数组相同；未调用 `training_sequence`、`collate_selected` 或 tokenizer/renderer/encoder/decoder。10 例绑定有效训练 view，3 个原创 protocol 例只在材料诊断集合。

旧 11 例保留原 source/run 时间、consumer 与 Q1 继承链；另 2 例绑定 D1 原 v3 编码及 Q1 r5 结论。本次没有重新编码，也不把两 engine 当成 26 个新样本。确定性 `export_review_arrays(review, output=...)` 输出一个有序容器（2,030,656 bytes）和 manifest（3,013 bytes）；`read_review_arrays(output=..., expected=review)` 在框架导入前校验原始预期对象、consumer 及整个容器，返回不可变 `tuple[Batch, ...]`。只重算输出 manifest 无法替换原始预期绑定。

导出拒绝重复 JSON key、NaN/Infinity、bool/float 冒充整数、symlink/越界路径、覆盖已有目录和不完整发布；manifest 最后发布，容器上限 16MiB。接口范围为 `REVIEW_ARRAY_ADAPTATION_ONLY`，没有全选集导出或容量样本编码入口。

**CPU 计划与实测。** 沿用原两段 `epoch_plan / validate_plan`：smoke `197×8+7 → 198`，formal `742×8+2 → 743`；microbatch 1、单遍、不 shuffle/packing/truncation。两计划实际更新均为 0，后续四段原生 runtime 未在本包实现。

| 实际验证 | 结果与限制 |
|---|---|
| 新增原创小 fixture 最终 `unit-r5` | **135 passed**；本次固定生产/测试/config 字节 |
| 常规 CPU `cpu-r3` | **758 passed / 3 failed**；包含较早版本的 121 个新增测试，不能与 135 相加作为独立覆盖 |
| 原三个失败测试定点 `cpu-environment-fix-r4` | **3 passed**；只改新 pytest 临时根，旧代码/测试未变 |
| Ruff、契约冻结、成文前公开扫描 | PASS；最终文档扫描另封存 |
| 固定源码 `fixed-source-r2` | PASS；prepare 160.082049s；13 例转换/导出/回读 8.413885s |
| 默认安装 `fixed-installed-r2` | PASS；prepare 153.530760s；13 例转换/导出/回读 8.097879s |
| 既有输出比较 `delivery-compare-r1` | 两套 prepared report、整个容器、manifest、13 完整 Batch 和 consumer 字节一致；额外消费 API 0 |

实测 CPU 时间包含严格校验与计数开销，不是训练吞吐或模型性能。常规检查排除了未改动的 model_io、tokenizer alignment、compatibility、native toy、HF-only 套件；没有为本包重跑旧模型或大批历史报告。

源码与安装最终分别调用 `prepare_v3`、只读 verify、rebind、export、readback 各 **1** 次。计入保留的原失败后，源码 prepare **2** 次、安装 prepare **2** 次；两方完整转换/导出/回读仍各 **1** 组。S0 追加许可 `8c8aff8300bfa564db7d47be79e6c3f764360a8b` / grant SHA `0dcef6488eeec3f246560dabd7590a2239fd1238b97073cf5758fb7b8e549bbe` 绑定冻结 checkpoint、原失败与新路径。当前实际固定消费及 build/install 余额均 **0**。

**保留的失败。** 新测试首轮 `unit-r1` 为 96 passed / 1 failed，其负例误把私有 pytest 根内的路径当成公开路径；修正新 fixture 后 121 passed，最终扩充到 135 passed。常规 CPU 的三个旧负例同样依赖公开临时根，原 758/3 日志保留，改用新的公开临时根定点 3/3 通过，未修改旧测试或降低生产边界。

首次源码消费因 `v3_root_binding` 失败：初版把原 D1 的 90 个合法 immutable external references 错套为 root 相对路径。首次安装消费因 Q1 final seal 的 `relative_path` KeyError 失败：实际 seal 同时含 1,104 个私有条目与 3 个 public Git 条目。修复后分别按已钉住的 descriptor/manifest 和两类 seal 验证，不追读历史可变公共路径；在 S0 精确追加许可下，两次重试均通过。原源码失败没有 terminal profile 计数文件，只能由 traceback/原源码定位到 verifier 前，不能补称有实测计数；原安装失败的计数实际为 prepare 1、verify/rebind/export/readback/new encoding/build 0。两份原 reservation、旧 helper、原归档/安装、失败日志均保留。探索性路径查找、发送包装语法与只读摘要投影错误也另记，未伪造原命令或计数回执。

**实际归档与默认安装。** 使用现有 Python 3.14.7、既有 CPU 默认依赖和本机已有构建支持，以 offline/no-download/no-build-isolation 生成下列实物；没有新环境。新的默认 target 使用隔离 `-I -S` bootstrap，只加入新安装目录，固定消费来源实际在该 target。源码、sdist、直接 wheel、由 sdist 重建 wheel 和安装的 65 份 ToolAlign 包文件逐字节一致。

| 当前归档 | bytes | 普通成员 | SHA-256 |
|---|---:|---:|---|
| direct | 204,581 | 70 | `8070c4954dfb9a60a689b76ccfe46694b35d9dc056a262381de0e26a72aef3dc` |
| rebuilt | 204,581 | 70 | `8070c4954dfb9a60a689b76ccfe46694b35d9dc056a262381de0e26a72aef3dc` |
| sdist | 354,205 | 143 | `be725d44fa290eb13072e6f360999c7b9a13edbd5e2b67aa222a0115f1a80ffe` |

默认 distributions 为 toolalign 0.0.1、jsonschema 4.26.0、attrs 26.1.0、jsonschema-specifications 2025.9.1、referencing 0.37.0、rpds-py 2026.6.3。两组三归档及默认 target 均保留；当前 r2 归档绑定最终生产源码，成文只新增未打包的三份文档，不再 build/install。

**证据与交接。** 公共报告仅列 hash、公开源码与规范化命令；实际 argv/UTC/退出码、前后源码快照、完整私有文件 map、原始数据/材料及 App 路径留在本机。源码结果 SHA `fa9ec294f5eeef84a15f0a435180c4b528f098d181ba3e93c84fbf6c63b8e0fe`；安装结果 `4237a21dba30e9d3c4cd643d41beffb1ca0259ded1e4918e2ce52ab6da826593`；完整比较 `ca8c3008959d6a9b4478775280d677023c80885ad080de723ae3ca93ccc168d1`；当前包验证 `89cff9aa8459be610025f76706ed38e7a4da4132bb275314695fcd39a800a5e7`。

原证据保全 `e6ef5436c6aef3262298aca8d4c07506e79a15b43d0ed5fbe8d17c717a8a4eb6` 核对当前 612 基线文件、原 556 公开 Git/冻结副本、5,190 旧私有路径、197 原链接（含原本两条悬空链接）、4 旧 refs、根 identity 与 609 输入。旧公开字节按原 Git/冻结副本绑定，不要求授权换基线后的可变工作区仍等于旧版本；不补造悬空目标。最终 scope/制品预算、文档扫描、commit/普通 push、远端一致性及终态 seal 随 [正式交接单](../../coordination/handoffs/P04-sft-data-v3-cpu-r1.md) 的原生完整候选发送；本报告不把成文后的检查预写为已运行。

新私有制品上限 1GiB；本包实际全量数据 build、新分词、框架/模型加载、GPU、优化、生成、业务 API、下载、新环境、费用、模型/数据上传均为 **0**。浏览器实显、真实 trainer 消费、0.6B/1536 与 1.7B/2048 容量、正式 SFT/DPO/评测与服务部署均 **NOT_RUN**。原 Q1 审核身份和历史失败保持；完整候选交回后由 S0 接续独立 R1 与主干流程。
