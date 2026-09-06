# P04-SFT-CPU 最终候选交接核验

2026-09-06，S0。T1 已交付并结束本轮；候选状态为 **CPU_PARTIAL_UPSTREAM_BLOCKED，待独立 R1**。本记录验证交接身份和既有证据，不把 CPU 自测或已知上游失败改为完整 trainer PASS。

| 身份 | 实际值 |
|---|---|
| candidate | `33d6248e2c518ea777618224382bd30a3cc3433d` |
| parent | `0c7c2671a64d49fe48c722375481b4cf7a5c82c8` |
| tree | `1d2d5474ef87034e0184f8ebfa359345182e3356` |
| 已验证实现基线 / T1 授权 | `42eaa50a9519efe96d60b49f07cfbd106b36778c` / `e42536dd7c77d90ed33ab5354f288ab0f1c3d6c6` |
| T1 分支 | `work/p04-sft-cpu`；原 P01 分支及 `9fe3cbe` 保留 |
| 最终原生终态 | completed / idle，15:43:54 UTC；远端与干净本地候选一致 |
| S0 交接证明 | SHA-256 `f59023785bc7888806ea053015c30d43ecee27cc7046a211867d9daeb2e878b3` |
| T1 最终 completion | SHA-256 `7cc60a30519b6f6011b33616b40a8b24a3712d813e48051ec6b04d33c823e151` |
| 公开机器索引 | SHA-256 `ba93450f6dcd5a8aaff1f21d68499e1b3cdca45aa83fe78fc6229edfd3514a2a` |

S0 于 15:51:34–15:51:48 UTC 完成只读核对，2083 个当前文件路径通过。384 份候选文件与 Git 一致，364 份基线字节不变，只有 20 个授权新增文件；配置副本仍为 `5aad6ff6db68ee4fe9bac0aa6104eaeff17bf948b509bfce3d14e3eac9d9aa29`。真实测量提交 `eefc142` 的 108 份 src/tests/config 文件与最终候选完全一致。六个历史 Git 提交的源码集合单列检查，没有加到当前文件数或测试分母。

最终封存前 248 个私有文件、6684876 bytes 均与 completion 清单一致，封存后目录仅增加 completion 本身。18 条原命令回执包含 14 条原测量及最终候选的四条 lint/显式报告 lint/契约/公开扫描；每条开始/结束记录、源码快照、退出码和原始 stdout/stderr hash 对应真实执行提交。两个 TOY 失败完整保留。索引生成和普通推送原回执另行核对，不计为独立测试。

四组 CPU 自测原日志分别为 895 passed/2 HF-only skipped、格式 60、截止时间 2、训练绑定 13，合计 **970 passed/2 skipped = 原 919 + 新 51**。新 51 已包含于 895；单独重复运行、安装检查和 110 subtests 不再相加。这是已核实的 T1 自测记录，尚待新 R1 独立运行。

S0 直接重新解析 T1 的三份实际新归档：sdist 为 243688 bytes、119 成员（118 Git 文件加 PKG-INFO），SHA `54ca695f640014ac03128e5dd33534d913f097c8a22019af7fae90f746183655`；默认及显式 sdist 重建 wheel 均为 129868 bytes、62 成员（57 包文件加 5 metadata），SHA `936256e277cdf3ae7c43668dc4ad358c4249de24a17273e721936f7584cbee33`。逐成员 Git 字节、路径/链接、metadata 和完整 RECORD 均匹配最终候选；归档证明 SHA `c2abc373dc6b55e5fbd2bd2215361a5da8d241d52bb182929e5a3785f4a8f946`。S0 本轮新 build/install 均为 0，保留 T1 原 15:22–15:24 UTC 的真实构建/安装时间。

10 条原安装命令含 3 项预期拒绝（已有输出、改配置、训练开关，退出码 1/1/2），其余退出 0。27 个已加载 ToolAlign 模块均来自新 target，其中 8 个是新增 SFT 模块；S0 核对其当前文件与 wheel/候选源码。完整准备结果的 selection、四视图、计划、consumer 和禁止训练标识与源端一致。默认路径使用现有基础依赖，普通源码直接 wheel 及安装版 TOY replay 为 NOT_RUN。

原 13 例 collator 数组和两次 TOY 失败沿用[中间证据](S0_P04_SFT_CPU_INTERMEDIATE.md)，本次检查全部原文件仍匹配该证明。另核对原 183 份 P01 Git 身份、1310 份旧私有制品、18 份原数据及 86 份 selection/review 文件。两失败进程再次确认不存在，共享租约空闲。两份人工填写表仍为 100/13 行、各 0 reviewer/0 verdict；实际页面观察 0 页。

**未完成**：MLX-LM train 循环、optimizer 更新、8+5 尾周期、native evaluate、checkpoint 保存重载及 post-tail 参数/分数绑定。实际 MLX 更新仍为 0；Torch 参考和纯结构计划不能代替这些结果。CPU 默认设备触发的原生入口 KeyError、初次设备探针错误及早期开发 lint 提示均已明确保留。没有新模型、GPU 执行、全量重编码、人工代签、费用或上传。

精确候选的[独立审查范围](../coordination/tasks/P04_SFT_CPU_REVIEW.md)已准备。R1 需独立判断可用 CPU 功能、失败真实性和未完成训练接口的边界；本交接核验不自动批准合并、G-DATA 或正式 P04。

## 独立审查派发与候选 PR

2026-09-06 16:05 UTC，S0 核验 R1 上轮原生 completed/notLoaded、干净 `review/p02-training-binding-r1` / `40252f8517f3c7ac8ddc0340847946ac902200e1`，以及完整授权 `d65592e5529f573f061355775fec071737233d12` 和候选 `33d6248e2c518ea777618224382bd30a3cc3433d` 的远端读回。分发前证明 SHA `67f7860f837e7aae195eed494275e5a050d100884b227609c37c0979a1e800a0` 直接绑定 370 份授权、384 份候选和原 completion/索引；私有保存的完整分发词 SHA `c8f7868e08fdf83bea6c0c9fe16448a6dba622c969ad69ccc62238846ad59056`。

随后沿用原独立 R1 任务/隔离 worktree 实际发送，显式 `gpt-6-astra` / `max`，原生确认不同于旧轮的新一轮 ACTIVE/inProgress。新审查 branch/input intake 仍待确认，不能把派发成功写成已读取候选或审查通过；旧 40252f8 和所有旧审查保持。原生消息、回执、轮次与私有映射已保存，没有新建任务或 sub-agent。

16:06 UTC，[Draft PR10](https://github.com/kris0516/ToolAlign/pull/10) 已实际创建，head 精确为 33d，新增 20 文件/2720 行，base 为 main。候选 [CPU CI34044414304](https://github.com/kris0516/ToolAlign/actions/runs/34044414304) 已启动，结果另行核验。PR 描述明确区分 CPU 部分、已知上游入口阻塞和实际更新/尾周期/evaluate/checkpoint 的 NOT_RUN。最终独立验收、集成/main、实际页面和两项人工门槛未关闭。

16:12:04–16:12:14 UTC，S0 完成该候选 CI 的源码和原日志绑定，证明 SHA `779edd112eb06810c643503f1443fb76c90ff710a24be549cd9df785f5b43345`。Python3.14 job101516791320 和 Python3.11 job101516791492 各14步骤全部成功，各601 passed/48 skipped，加单独46 P00 passed；两Python结果与T1本机970/2均不互相相加。48项skip均因私有固定CPU tokenizer目录/前提未提供，原完整原因保留。四契约、390公开路径扫描和241私有canary/18公开fixture在sdist、直接wheel与重建wheel三路边界检查通过；这三条是CI的canary测试路线，不能改写T1普通源码直接wheel的NOT_RUN。

两个原日志共同绑定实际CI checkout `300bda3912a96102cc905303ea8dc686c728d112`，parents 为 d65592e 与 33d6248，tree `e212bcc6715080d30a1feb75dfa2831d0afe6faa`。该390文件恰为授权370份加候选20份新增；全部384候选内src/tests/config字节保持。两份已解码完整原日志按UTF-8原换行保存，3.14为28707 bytes、SHA `0503d917e40d4076633e015c56e7bbe5deaf20ef8986e367ac04f34c1d87a128`，3.11为28816 bytes、SHA `c35bc26560eff6a99695fa36f7e82bff133f6a57f43bac7af1b99778a7553321`。S0没有新构建、安装或模型执行。R1同一实际轮次仍ACTIVE，intake/独立结论待交付，PR保持Draft。

## R1 实际领取核验

R1 于 16:16:01 UTC 实际从精确 33d 新建 `review/p04-sft-cpu-r1`，原生回报已读取完整授权，intake 原证明 SHA `12b23bea4cb31368061d13c5c6be2ddf563efdbb848727ff3300c299d7100527`。S0 于 16:22 UTC 直接核对实际分支/HEAD/tree/parent、384 候选文件、364 不变基线、20 新增路径及 13 份授权副本，原配置 5aad 与全部 Git 字节一致；真实任务身份和 gpt-6-astra/max 对应原生派发。

S0 同时按原 completion 精确白名单重核旧 1562 封存制品、7 份公开审查及 40252f8 分支，全部匹配；未去敏 f708 仍不在被审候选祖先。共 1965 个当前文件路径和原生领取记录的证明 SHA 为 `99cfa569284dca72924acc004f9423836b1e17847592c22a933f82653da785d0`。初次附加保全检查错误假定所有旧制品均在 R1 私有根，因此遇到原系统临时文件时 exit1；原工具失败与诊断保留，随后使用原封存清单的路径核对，1347 个系统临时制品也全数匹配。没有改被审代码、测试或原证据。R1 的旧 50685 文件快照另作为其保全记录保存，S0 本次未重新 hash 全部该快照，不与本次 1562 直接核验混称。

R1 继续同一实际原生轮次的 CPU 功能、原始负结果与归档/安装独立审查；intake 通过不代替正式 PASS/FAIL/BLOCKED 结论。PR10、上游 train 阻塞及全部人工/正式训练门槛维持上述边界。

最新CPU接收补记（2026-09-07）：R1原800480b对33d6248的CPU准备正式PASS/P0/P1/P2均0，已原生completed/idle；S0核对56134路径/26原命令，普通集成487c92d实测1014CPU/2跳过、三新归档及新默认安装7条接口通过。CPU部分ACCEPTED，PR10最终CI/main待验证；原生train仍BLOCKED，实际尾周期/evaluate/checkpoint和人工/正式训练门槛保持。详见[独立验收与集成](S0_P04_SFT_CPU_INTEGRATION.md)。本报告前述旧测量保留原执行范围，不改写为新运行。

主干验收补记（2026-09-07）：P04-SFT-CPU准备部分VERIFIED；[PR10](https://github.com/kris0516/ToolAlign/pull/10)实际合并e28f1db，原R1 PASS800480b保持。最终双Python CI与main1014CPU/2 HF-only跳过、现存三归档/57安装包文件绑定通过；原生CPU train入口仍BLOCKED，实际尾周期/evaluate/checkpoint及人工/正式P04门槛保持。见[main证据](S0_P04_SFT_CPU_MAIN_VERIFICATION.md)。此前记录仍保留各自实际执行时间与待办状态，不改写旧实验。
