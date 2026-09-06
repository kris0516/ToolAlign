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
