# P04-SFT-CPU-R1｜CPU 准备独立审查

**CPU 准备部分 PASS；新增 P0=0 / P1=0 / P2=0。完整原生 trainer 路径 BLOCKED_UPSTREAM_CPU_ENTRY。** 可独立集成固定输入的准备入口、只读视图、collator、累积计划及 validation 结构；`train_toy_segments`、`post_update_score` 尚无完整原生运行证据，不能作为已验收训练接口。最终接收由 S0 决定，本结论不关闭 P04、G-DATA 或人工门槛。

R1，gpt-6-astra / max；2026-09-07（Asia/Kuala_Lumpur，原始日志使用 UTC）。分支 `review/p04-sft-cpu-r1`；契约 plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / ADR-0017 至 0020。切换前已读取并保存完整授权、任务与配置、docs03/16及 S0 原证据；随后审阅候选全部20个新增文件。

| 对象 | 精确身份 |
|---|---|
| candidate / 本 review 唯一父提交 | `33d6248e2c518ea777618224382bd30a3cc3433d` |
| candidate tree | `1d2d5474ef87034e0184f8ebfa359345182e3356` |
| candidate parent | `0c7c2671a64d49fe48c722375481b4cf7a5c82c8` |
| authorization | `d65592e5529f573f061355775fec071737233d12` |
| 实现基线 / T1 原授权 | `42eaa50a9519efe96d60b49f07cfbd106b36778c` / `e42536dd7c77d90ed33ab5354f288ab0f1c3d6c6` |
| S0 原配置与候选副本 SHA-256 | `5aad6ff6db68ee4fe9bac0aa6104eaeff17bf948b509bfce3d14e3eac9d9aa29` |

本 review commit/tree 由包含审查文件的 Git 对象确定，完整值随原生交接及私有 completion 提供。仅新增本目录与[本轮交接](../../../coordination/handoffs/P04-sft-cpu-review-r1.md)；候选384文件全部保持，364份原基线不变，没有合入后来 main、修实现或改变配置、依赖、锁、CI、契约和看板。

## 可复核的 CPU 结果

实际运行四组原回归 `895 passed / 2 skipped`、`60 passed`、`2 passed`、`13 passed`，另有[44项原创 CPU 探针](probe_cpu.py)通过，合计 **1014 passed / 2 skipped**。新生产51项已包含在895内；110个 subtests、安装版44项重复及逐例材料核对不再相加。两项 skip 均为 `tests/model_io/test_snapshot.py:178` 的 HF reference 专用 snapshot cleanup。回归使用已有 Python3.14.7、纯 tokenizer CPU 环境及新的系统 basetemp，未加载模型框架。

| 授权检查 | 独立证据与结果 |
|---|---|
| 固定配置、prepare、四视图 | [检查器](check_bound.py)实际调用完整原 verifier，逐条比较原 Example 与 sidecar、profile/split、排名、身份和最小桶；调用者与返回值的嵌套修改不污染只读视图。 |
| 拒绝边界 | 原创例覆盖缺失、重复、错序、错误数量/身份/rank/profile/split、Action/audit/hash及非最小桶。另对7项固定输入篡改和缺失选择输出执行完整 prepare，8项均按预期拒绝。 |
| collator / 共用格式 | 对10条既存实际 train 例与3条协议例，逐值核对冻结 reference/native、T1 新 collator 与 R1 由既存完整 IDs 重建的 Sequence/pad 数组；13组通过。协议例不在真实视图中。 |
| 监督边界 | 原创小例验证 prompt、右 padding 不计监督，P−1 起始、N−2 预测追加 EOS，追加 EOS 恰好一次，历史 prompt 内 EOS 不误判；shift、attention、loss mask 与有效分母一致。 |
| 累积计划 | 0拒绝；1/7/8/9/13/1600/6013均检查覆盖与实际余数分母，无补齐、重复或丢尾。13为8+5，1600/6013的200/752仅为计划更新数。 |
| validation / Score | 原创不同 token 数验证总 CE / 总监督 token；完整身份/顺序及覆盖，NaN/Inf/零分母/溢出/遗漏/重复拒绝。参数 hash 绑定名称、dtype、shape和内容；选择按最小 finite CE、较早更新步、checkpoint hash确定。 |

四视图实际数量与桶如下。两种 profile 有重叠，不能把跨 profile 数量相加作为独立样本数。

| Profile / split | 数量 | 桶1024 | 桶1536 | 桶2048 |
|---|---:|---:|---:|---:|
| smoke train | 1600 | 429 | 1171 | 0 |
| smoke validation | 197 | 74 | 123 | 0 |
| formal train | 6013 | 985 | 2633 | 2395 |
| formal validation | 217 | 74 | 123 | 20 |

`training_authorized=false` 和默认无训练开关保持。准备数据路径固定绑定原 manifest/config/selection/representation/audit/protocol；没有数据驱动 import/callback 或最终测试 loader。原18份数据产物仅作 hash 保全，选择验证只使用允许的 train/validation；最终 test/ood_test/BFCL 未用于训练、统计筛选或调参。本轮真实13例新增编码0，全量8228行重编码0，原选择新增物化0。

## 一次受限数值与原生入口反例

[原创监督探针](numeric_probe.py)仅启动一次 R1 自有数值子进程。先取得共享 OS 租约，再设置 MLX CPU 默认设备/CPU stream 与 Torch CPU、两个线程，随后构造数组。只读复用锁定 replay 环境：MLX0.32.2 / MLX-LM0.31.3 / Torch2.14.0 / NumPy2.5.2。13条唯一原创输入、最大桶8、词表4、float32参数16，均低于授权上限；未使用真实 P02 数据或手动优化更新。

所有 loss/gradient 数组与设备原记录保留。MLX 与 Torch loss 最大绝对误差 `2.384185791015625e-07`，gradient最大误差 `8.940696716308594e-08`，均小于 `2e-6`；右 padding 的 loss/gradient误差及 ignored-logits的 loss误差均为0。原生 default_loss 对同一负例把监督 token 数由2变3，loss由正确的 `1.5347585678100586` 变为 `1.2920119762420654`，实际证明需要显式 completion mask。

用有效小模型、SGD、13条数据和真实 TrainingArgs 调用原 `trainer.train` **一次**；`trainer.py:229` 读取 CPU 设备信息的 `max_recommended_working_set_size` 时产生 KeyError，尚未进入迭代。CPU 元数据实际只有 arm64 / Apple M5 Pro 标识；Metal 可用不代表本次使用 GPU。trainer 源码 SHA-256 为 `ee33ebdbd20a184108541cb490d08085485e71a82ffd6d68d7d216029ecd28fe`，没有 vendor 修改、伪造设备返回、改 GPU 默认设备或独立训练循环。

本次实际 iterator 访问为空、optimizer step=0、checkpoint文件0；参数前后内容 hash 均为 `e024bbaa23be89829b80c80f2be6d780da3dbbb82e79c1e6379794229897f827`。原 P01 wired-limit 保护器未改，设置事件为空且原函数已恢复。预期 KeyError 原 traceback保存后，子进程以 **exit0 / PASS_NUMERICS_WITH_EXPECTED_ENTRY_BLOCK** 结束；这不是训练成功，也不能把预期捕获写成非零退出。

子进程墙钟 `3.547687166s`，采样峰值RSS `389185536 bytes`，低于300秒/4GiB上限；父进程实际 wait/reap，自有 PID 不存在，退出后共享 OS 锁未持有。没有第二次数值重试。

源码审查确认分段接口计划复用 model/optimizer、只seed一次，并在实际余数周期使用余数分母；`post_update_score` 设计会核验实际 step、当前参数与保存文件内容、完整 validation身份、原生evaluate结果和前后状态。但是入口阻塞使**实际8+5更新、尾周期数值、native evaluate、checkpoint保存重载、post-tail状态绑定全部 NOT_RUN**。结构断言、人工构造 Score 和前面的梯度比较不关闭这些缺项。

## 原始证据、归档与安装

[原证据审计](audit_evidence.py)核对2418个不同现有路径，包括候选384文件、T1封存248份材料及原18条命令的实际argv/UTC/源码epoch/日志。原核心108份实测源码从 `eefc142` 到最终 `33d6248` 字节一致；较早 `96fcbe1` 的真实collator、`9e71552` 的数值入口运行分别绑定各自Git源码，未把后续文档提交标成重新执行。T1 completion `7cc60a30519b6f6011b33616b40a8b24a3712d813e48051ec6b04d33c823e151`、公开索引 `ba93450f6dcd5a8aaff1f21d68499e1b3cdca45aa83fe78fc6229edfd3514a2a` 及 S0 原中间/交接/归档证明均逐字节核对。

[归档检查器](check_package.py)直接解析现有 T1 三归档，核对成员路径、普通文件、Git字节、METADATA/PKG-INFO/WHEEL/entry point/license和每项 RECORD。R1没有额外重建归档；证据已绑定实际构建时源码与最终相同生产字节。

| 已实际构建、R1本轮解析的归档 | Bytes | 成员 | SHA-256 |
|---|---:|---:|---|
| T1 sdist | 243688 | 119（118 Git + PKG-INFO） | `54ca695f640014ac03128e5dd33534d913f097c8a22019af7fae90f746183655` |
| T1默认wheel | 129868 | 62（57生产文件 + 5 metadata） | `936256e277cdf3ae7c43668dc4ad358c4249de24a17273e721936f7584cbee33` |
| T1显式sdist重建wheel | 129868 | 62 | `936256e277cdf3ae7c43668dc4ad358c4249de24a17273e721936f7584cbee33` |

R1用 `uv pip install --offline --no-python-downloads --no-deps --target` 将上述新默认wheel实际安装到本轮新私有target，基础依赖只读复用。[安装检查](exercise_installed.py)在非源码cwd用 `-B -I -S` 运行7条真实子命令：origin、44项原创重复、help、完整prepare，以及原输出存在/配置篡改/不支持训练开关三项预期拒绝（exit1/1/2）。首次额外origin检查的cwd为工作树，但随后上述非源码cwd的origin和全部接口检查独立完成，未依赖源码导入。

27个已加载 ToolAlign模块均来自新target，其中8个新模块；57份生产文件字节匹配归档，11种可选依赖不可导入。安装版与源码版完整 `preparation.json` 字节一致，SHA-256 `52cd77a04e12417b18dafae7a6447dfe1007a57780434743a4ace076d87da4c9`。没有新环境、依赖下载或旧wheel冒充；源码直接wheel和R1新构建均 NOT_RUN，安装重复不增加1014分母。

## 失败保留、人工与发布边界

原 T1 两次失败完整保留：`96fcbe1` 的 DLPack设备探针 AssertionError、`9e71552` 的原生CPU元数据KeyError，原子进程均exit1并已回收。R1本轮也保留两项辅助失败：原创数值脚本初稿ruff I001，和保全检查器错误要求 App 管理的临时 diff refs 永久存在。仅修正R1辅助检查，候选未变。初稿数值脚本由已记录修改反向重建，逐字节等于失败命令原SHA；初稿保全脚本另存原件，不覆盖失败回执。修订检查确认两个临时diff ref名称已消失、原对象仍在；全部旧审查分支及66个原ref对象保留，R1没有修改这些临时refs。探索性路径读取未命中不计测试，没有伪造单独日志hash。

末次保全核对旧50685个私有文件、283个符号链接、上轮1562个封存条目和7份旧审查文件；原未去敏审查仍只在本机且不在本轮公开祖先。原P01的183份Git输入/1310私有材料与86份选择/冻结审查材料也已核验。保全测量时新增私有材料与6个系统测试目录共 `162835816 bytes`，随后保全清单及少量发布材料另计；最终占用和文件清单随completion登记，预算2GiB。该占用不是峰值RSS或吞吐。

100行语义与13行token/mask人工表核对时仍为0 reviewer / 0 verdict；仅kris可填写四个人工字段，合法后续填写不当作证据损坏。R1实际页面观察0，未导航或绕过原浏览器拒绝。实际页面、两项人工审查均 PENDING，G-DATA与正式P04未授权。没有预训练权重、真实数据优化、真实模型容量测量、BFCL评测、费用、公网服务或模型/数据上传。

Ruff全库及本目录/五份原实验脚本显式检查、四份冻结契约已通过。[机器索引](VALIDATION.json)保存实际命令去敏映射、UTC、退出码、日志hash及证据身份；原始完整参数、源码字节与失败日志仅交S0本机核对。公开内容扫描、最终Git对象、普通推送及远端读回在索引写定后执行，并由最终私有completion绑定，避免自引用。最终CI/main验证、上游兼容修订和后续阶段由S0继续处理；R1交付后结束本轮。
