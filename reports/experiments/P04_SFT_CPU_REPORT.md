# P04 SFT CPU准备交付与原生入口限制

2026-09-06，T1；`gpt-6-astra` / `max`。状态为 **CPU_PARTIAL_UPSTREAM_BLOCKED，待独立R1/S0审查**。只读训练数据视图、新collator、累积计划、默认安装入口和CPU边界验证已交付；实际MLX-LM训练在进入循环前被原生CPU元数据查询阻塞。本报告不声明原生尾更新、checkpoint保存重载或post-tail validation通过。

| 身份 | 精确提交 |
|---|---|
| 已验证代码基线 | `42eaa50a9519efe96d60b49f07cfbd106b36778c` |
| S0授权 | `e42536dd7c77d90ed33ab5354f288ab0f1c3d6c6` |
| 数据视图、collator与适配实现；13例测量 | `96fcbe1f34fc9d2afe1d9faf3935817d37b22d76` |
| 设备证据探针修订；第二次CPU数值replay | `9e71552c22b4ed5daf4e4a66e24816bd61f53092` |
| 全部CPU回归、新归档与隔离安装测量 | `eefc142ce159c1564076dff7d3f17156412de699` |
| 原始回执/源码/证据索引核验器 | `0c7c2671a64d49fe48c722375481b4cf7a5c82c8` |

最终文档提交由原生交接给出。后续证据说明不冒充执行时的源码提交。契约保持plan-v0.1 / coordination.v1 / toolalign.contracts.v1及ADR-0017至0020。新分支为`work/p04-sft-cpu`；旧P01分支和`9fe3cbe`保留。

## 已验证的数据与默认接口

[新增包](../../src/toolalign/training/sft/__init__.py)通过`python -m toolalign.training.sft`提供默认CPU准备入口，调用者显式给出本地配置、选择manifest及固定输入路径。入口没有训练开关，拒绝篡改配置及已有输出目录，错误保留诊断。安装后可在非源码cwd、`-B -I -S`下使用；默认仅需原有基础依赖。

S0配置逐字节复制到[configs/sft-cpu.v1.json](../../configs/sft-cpu.v1.json)，SHA-256为`5aad6ff6db68ee4fe9bac0aa6104eaeff17bf948b509bfce3d14e3eac9d9aa29`。训练数据配置和公开/私有selection manifest原字节不变，`training_authorized=false`保持。

实际使用既有`training_selection.verify`完整核对两份选择及固定输入，再读取四个train/validation视图。保留原Example、rank、split、sidecar、最小padding桶；视图返回隔离JSON值，未重写、重新选择或物化数据。完整原manifest哈希核对与训练数据读取分别记录；最终split没有训练视图，不用于调参。实际数量如下，更新数仅为**未执行的单遍计划算术**：

| profile | train | validation | 计划优化器更新 |
|---|---:|---:|---:|
| smoke | 1600 | 197 | 200 |
| formal | 6013 | 217 | 751个完整周期＋5微步尾周期，共752 |

formal train最小桶分别为1024的985条、1536的2633条、2048的2395条。当前真实选择的目标仍全部为`tool_calls`，三条协议例不进入任何训练或validation视图。

15:15:53–15:17:22 UTC，新collator实际消费原10条已选train和3条单列原创协议例，只新增**一遍13例native编码**。它复用共用`training_sequence`和`pad_sequence`；每例全部未padding序列、attention/loss mask、右padding、shift inputs/targets/mask和监督分母均与原reference/native材料逐数组相同，覆盖原代表/最长/1536/非ASCII边界。第一监督位置P−1、末位置N−2和唯一追加EOS保持。没有新的reference编码或全量选择分词，没有覆盖原材料或代填人工判断。完整原值/新数组仅私有保存，公开为hash与统计。

13例摘要SHA为`e4d9a91eaa74bfeee7c0c922bf037f5543789bc7f06ad12b6c1a26f74a8c4554`；新输出canonical SHA为`ba1f7f3862ee882568ea880c9e4d30919c978a2a9d05109165d2b543a871137e`。原86个selection/review文件hash未变。

## 累积、validation与执行限制

纯CPU计划检查0、1、7、8、9、13、1600、6013边界；空数据、重复、遗漏、错序、越界和错误尾分母均失败。固定microbatch1/累积8/单遍/seed42，不排序、shuffle、packing或截断。完整段与余数段设计为使用同一model、optimizer和RNG；训练目标是等权平均每个微步的completion平均CE，尾周期除以实际微步数。

可选[mlx_adapter.py](../../src/toolalign/training/sft/mlx_adapter.py)显式注入专用有限`iterate_batches`和mask loss。当前执行入口只允许极小`TOY_CPU`，没有正式训练命令。validation组件独立按总CE/总监督token聚合，拒绝错误profile/split、重复、遗漏和非有限分母/分数；选择器固定按最低finite CE、较早优化器步、checkpoint hash排序。CPU测试验证这些结构规则。原生post-update参数内容hash、checkpoint文件hash、真实optimizer计数、保存重载与实际evaluate的组合接口**尚未被本轮数值验证**，不能作为已验收SFT状态绑定使用。

两次replay均在自有独立子进程先实际获取原共享租约，再导入MLX/Torch，固定CPU默认设备和CPU执行流、Torch CPU/2线程。模型是原创8词表、64个float32参数的表格，13条、每条右padding到16 token；未加载预训练模型或优化真实P02数据。

第一轮在设备证据断言失败，未开始梯度/optimizer更新。该探针错误地期待DLPack返回CPU标签；[MLX v0.32.2源代码](https://github.com/ml-explore/mlx/blob/v0.32.2/python/src/array.cpp#L499-L510)在Metal可用时固定返回`(8,0)`，不能据此判断操作在哪个设备执行。修订仅更正该标识解释，并记录/断言实际CPU默认设备及执行流；数值容差和数值断言没有放宽。

第二轮的13例原始数值结果已落盘：

| 检查 | 实际最大绝对误差 |
|---|---:|
| 新mask loss vs 独立Torch CPU | 0 |
| 新mask梯度 vs 独立Torch CPU | `4.470348358154297e-08` |
| 右padding loss / gradient | 0 / 0 |
| 仅改变被忽略预测位置logits | 0 |

容差为float32 `2e-6`，包括EOS监督和真实有效token分母。没有声称改变prompt输入不会影响模型输出。实际重现原生default_loss的padding负结果：正确分母2/loss`2.074565887451172`，默认分母3/loss`2.0883114337921143`。旧P01 padding与尾周期限制原记录保持，不将当前设计写成负结果已关闭。

随后原生trainer在第229行求值`mx.device_info()["max_recommended_working_set_size"]`时出现`KeyError`，尚未进入train循环。第二轮之前已经过两次Torch原创参考更新语句，但最终参考参数没有在该异常前独立落盘；不据此替代MLX实测。详细最小反例见[上游限制](P04_SFT_CPU_UPSTREAM_LIMIT.md)。S0已要求保留CPU默认设备和原vendor，沿原授权的限制分支交付，不重复同一入口回放。

| replay | 退出 | 墙钟 | 监测峰值RSS | 实际MLX更新 |
|---|---:|---:|---:|---:|
| 初次设备探针失败 | 1 | 6.272458s | 388268032 bytes | 0 |
| 修订后原生入口KeyError | 1 | 2.863546s | 389775360 bytes | 0 |

均低于300秒/4GiB，完整原stdout/stderr、租约、失败和终态记录保持。两次子进程已wait/reap，PID当时不存在，租约随进程退出释放，随后真实锁检查空闲。现有P01 wired-limit保护器未改，元数据KeyError发生在setter被调用前；无新vendor patch或操作系统内存限制调整。

## 回归、归档与安装证据

Python3.14.7，复用既有三个环境：默认基础环境；tokenizers0.22.2/Jinja2 3.1.6纯tokenizer环境；MLX0.32.2/MLX-LM0.31.3/Torch2.14.0锁定replay环境。环境身份独立回执SHA为`86d7b098f15db685816771af449a33c39cd437f1f6564e41d93832cd5eeac22b`，未创建环境或下载依赖。

15:23:26–15:24:33 UTC完成四个不重叠CPU组：895 passed/2 HF-only skipped（包含新增51）、原格式60 passed、截止时间2 passed、训练绑定13 passed/110 subtests。合计**970 passed / 2 skipped = 原919 + 新51**。新增51的独立重复运行、安装重复检查及110 subtests不再相加。Ruff、四契约及公开扫描通过；最终说明文件的补充扫描回执随交接封存。

15:22:39默认离线构建，15:23:24显式sdist重建；只读复用已缓存构建依赖和现有解释器，`--no-build-isolation --no-python-downloads`。不是复制旧归档：

| 新制品 | bytes | 成员 | SHA-256 |
|---|---:|---:|---|
| sdist | 243688 | 119（118 Git + PKG-INFO） | `54ca695f640014ac03128e5dd33534d913f097c8a22019af7fae90f746183655` |
| 默认wheel | 129868 | 62（57包文件 + 5 metadata） | `936256e277cdf3ae7c43668dc4ad358c4249de24a17273e721936f7584cbee33` |
| 显式sdist重建wheel | 129868 | 62 | 同上 |

复用未改的已验收归档检查器，逐成员对Git字节、路径/链接、公开载荷集合、PKG-INFO/METADATA/WHEEL/entry point/license和完整RECORD核对。默认wheel来自该次sdist；普通源码直接wheel未执行。

新wheel安装到新的私有target，仅只读复用原基础依赖；非源码cwd、`-B -I -S`执行。原安装验证4条命令加新增6条命令共10条，包含3项预期拒绝（已有输出exit1、改配置exit1、训练开关exit2）。8个新增模块及全部被加载ToolAlign模块来自新target，11类可选依赖不可导入。实际执行新准备入口的完整固定选择核验及原创小数据接口；未运行安装版TOY replay。全部10条原argv/UTC/输出hash留存，拒绝项不混入成功退出计数。

## 保全与未完成项

15:29 UTC核对364份base字节、183份旧P01 Git身份、1310份旧私有制品、18份原数据制品和86份selection/review文件。新私有目录当时6146610 bytes，远低于2GiB；这是记录时大小，不是最终封存总量。保全证明SHA为`372df87bd8e84ac17e614edcb17fd58a9218f4281d514d96a9d820b66a0e3af8`，最终新增证据继续独立封存。

人工语义表100行和token/mask表13行在该次读取均0 reviewer/0 verdict；合法后续填写仍允许。原浏览器URL拒绝保持，实际材料页面观察0页，没有绕过或模型代签。

**NOT_RUN / 未放行**：原生MLX训练循环/更新/8+5尾周期、原生evaluate、最终TOY checkpoint与post-tail数值绑定；预训练模型加载、真实P02优化、容量预检、正式baseline/SFT/accepted_sft、P05及后续阶段、GPU操作、权重/数据/依赖下载、收费资源、公网服务或上传。G-DATA与P04人工门未关闭。T1只交付候选，等待独立R1及S0决定，不自行合并或接受本包。

[机器索引](P04_SFT_CPU_VALIDATION.json)包含14条原命令及日志、source epoch、13例数组、数值失败/清理和归档hash；其生成时SHA为`ba93450f6dcd5a8aaff1f21d68499e1b3cdca45aa83fe78fc6229edfd3514a2a`。索引核验器实际检查原始回执和各自Git源码后产生该文件，执行回执SHA为`ff6d2faa6613550f85438811948f2970fe00783201fb7bc519c89bbfb3d8b39d`。本轮最早开发测试51通过和一次已修正的报告import排序提示不加到独立分母；两次失败replay均保留，不隐去。
