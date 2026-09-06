# S0 SFT CPU准备主干验证

2026-09-07；状态：**VERIFIED（CPU准备部分）**。[PR10](https://github.com/kris0516/ToolAlign/pull/10)于2026-09-06 17:50:26 UTC实际合并，已读回closed/merged并同步本机main。原生CPU训练入口仍BLOCKED_UPSTREAM_CPU_ENTRY；实际尾周期、native evaluate、checkpoint保存重载与完整P04未验收，`training_authorized=false`。

| 对象 | 精确身份 |
|---|---|
| T1候选 | `33d6248e2c518ea777618224382bd30a3cc3433d` |
| 原独立R1 PASS | `800480b0b1e14c21937f1b5073daf543a2ba31fc`，P0/P1/P2均0 |
| S0实际隔离集成 | `487c92dfd552a2992e707301dc4a7d6edeb94f36` |
| 最终PR head | `cfe5dbeb5d6c1864938573e2c014b35c60ea13c4` |
| 实际main merge | `e28f1db81eb2b5bb819fe64e0bf0156b2d065a71` |
| 实际parents | `ad8115a33c8cccd3849d0286424d0c1b77e5d6c2` + 最终PR head |
| main/final head/CI共同tree | `749e59a964240cea130964be7d49a7a4ba4170e7` |

[R1审查](review/P04-sft-cpu-r1/README.md)和[S0隔离集成](S0_P04_SFT_CPU_INTEGRATION.md)保留原执行时间与身份。S0按原SHA普通merge，未修改候选生产代码、测试、配置或R1审查。最终main的400份Git文件与final head及CI实际checkout逐字节相同；API的历史base字段没有冒用为实际merge父提交。

最终[CI34049603450](https://github.com/kris0516/ToolAlign/actions/runs/34049603450)（CPU contracts第128次）双Python jobs各14步骤全部成功：

| Python / job | 实际测试 | 原日志Bytes / SHA-256 |
|---|---|---|
| 3.14 / 101530698116 | 601 passed / 48 skipped；另46 P00 passed | 28715 / `b738ebceef897c67df25043c3865e6f490f73d5a88f8bde967183a732b99d37a` |
| 3.11 / 101530698244 | 601 passed / 48 skipped；另46 P00 passed | 28817 / `3ff463a3b417dbd3b96850c0e80a309624314234fd3f4ca18d77d129c7958f75` |

两组48项skip均为未提供固定私有CPU tokenizer/依赖：17数据alignment、18offline、13snapshot。4契约、400路径公开扫描、241私有canary/18公开fixture在sdist、direct、rebuilt三路线通过。原日志保持UTF-8字节，绑定实际checkout`5004a3bba79ab659e23a41d29d6e52a0cf01acdc`及上述两个parents；S0于17:49:43 UTC完成核验，证明SHA为`cb46facb4685e7b4949337b9fcb122c217904f475ef443592ab690d245a7ed7d`。不同环境、重复检查与CI canary路线不混加为本机实验。

S0在实际main上新执行五个不重叠CPU组：

| 本轮main组 | 实际结果 |
|---|---|
| cpu-combined | 895 passed, 2 skipped in 51.79s |
| original-format-review | 60 passed in 0.11s |
| independent-deadline-review | 2 passed in 11.54s |
| independent-training-binding-review | 13 passed, 110 subtests passed in 1.22s |
| independent-sft-cpu-review | 44 passed in 0.07s |

合计**1014 passed / 2 skipped**。本机两项skip仅为HF reference专用snapshot cleanup。T1新增51已在895内；110 subtests、原R1的1014及此前安装重复44项均不额外计数。Ruff全库/显式新报告、4份契约冻结、400路径公开扫描及diff检查通过。每条回执保存实际argv、cwd、环境、UTC、退出码、日志与400份开始/结束源码hash；本轮main命令无失败。

main另直接解析S0集成时实际构建的三份现存归档，核对当前118份Git输入和57份包文件，以及metadata/entry point/license/完整RECORD。sdist为243688 bytes、SHA `54ca695f640014ac03128e5dd33534d913f097c8a22019af7fae90f746183655`；默认及显式sdist重建wheel各129868 bytes、SHA `936256e277cdf3ae7c43668dc4ad358c4249de24a17273e721936f7584cbee33`。main解析证明SHA为`f2e349145c55a7141b2164a18873d4f0c69eeb06903aedb1b228b915d56c37c1`。

**main本轮新build/install/API重跑均为0。** 原默认安装及7条-B/-I/-S非源码cwd接口检查实际发生在487c92d、17:38:14–17:39:07 UTC，原日志未改写；本次重新hash现存57份安装包文件和27个origin（含8新模块），与当前main和归档逐字节绑定。原7命令为origin、44项原创重复、help、完整prepare与三项预期拒绝（exit1/1/2），11种可选依赖不可导入。prepare SHA `52cd77a04e12417b18dafae7a6447dfe1007a57780434743a4ace076d87da4c9`保持。普通源码直接wheel仍NOT_RUN，CI canary direct另计。

下列12条本轮main命令均实际成功，UTC日期为2026-09-06：

| main命令 | UTC开始–结束 | exit | 原日志SHA-256 |
|---|---|---:|---|
| cpu-combined | 17:51:27–17:52:19 | 0 | `c35c3fcc64810df5d8a69edb53bf75e937fbb580c111baefe4c356fd9ac75778` |
| original-format-review | 17:52:19–17:52:19 | 0 | `b746f5b04deb9a4a5ab9ad150ef96de12b7adc51f3b8f0c709ce03184f5e8501` |
| independent-deadline-review | 17:52:19–17:52:31 | 0 | `660844050fe8f40e80f776bdb3c6e1e9f8bcb60429763e155b8783ee8864feb6` |
| independent-training-binding-review | 17:52:31–17:52:32 | 0 | `d45b2de0f480056f6b66fdd470b0673ca5f212c610b711a486cf4809e397a586` |
| independent-sft-cpu-review | 17:52:32–17:52:32 | 0 | `be32f74acee3c165b016f3ee6e603c8fee21352284684616f34d68dc4a08c86c` |
| lint-all | 17:52:33–17:52:33 | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| lint-explicit-reports | 17:52:33–17:52:33 | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| freeze | 17:52:33–17:52:33 | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| public-scan | 17:52:33–17:52:38 | 0 | `5f7a76e02d6d999a35a859266825a9f69a309619e10fe2d3e08731ba79422c75` |
| diff-check | 17:52:38–17:52:38 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| archive-verification | 17:52:38–17:52:40 | 0 | `f6c478a2788369dc7ebd497da598539a137d8c261c72890bc40650ca73381e9e` |
| main-evidence-check | 17:54:43–17:54:43 | 0 | `ebe5217c0fa97cc02ab6d856c5246e809284a6031b58534a61833694327720e5` |

17:54:43 UTC汇总核验通过，main证明SHA为`618711634565123a9fe6907fd7714078230f33ff64d109868b845146d27b4db5`。四条本轮截止时间子进程已wait/reap、handle关闭及目录清理，记录PID均不存在；共享GPU锁实际空闲。100行语义表与13行token/mask表仍0 reviewer/0 verdict，实际页面观察0；合法人工填写权限保留，原浏览器拒绝未绕过。

现在可使用固定输入的CPU prepare、只读视图、共用collator和计划/validation结构。R1原创数值对照及S0从原数组重算的结果保留，但上游CPU入口KeyError后的actual optimizer更新仍0、checkpoint0；train_toy_segments/post_update_score的实际原生路径仍不可作为已验证trainer。原T1/R1/S0辅助失败分别保留，本次不重新运行模型、框架数值探针、原13例或8228编码，也不物化新选择。

P02整包/G-DATA、实际页面、kris语义/token-mask人审、真实0.6B容量、正式baseline/SFT/DPO、评测、服务与P09最终交接仍未完成。CPU准备部分的VERIFIED不替代这些门槛，也不构成费用、公网推理或模型/数据上传授权。
