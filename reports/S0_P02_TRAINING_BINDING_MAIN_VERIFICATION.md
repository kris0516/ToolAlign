# S0 P02训练绑定主干验证

2026-09-06，**VERIFIED（CPU技术范围）**。[PR9](https://github.com/kris0516/ToolAlign/pull/9)已实际合并；固定训练选择及其可核对材料通过独立R1、最终双Python CI和实际main验证。代表/最长/非ASCII材料的实际页面观察、kris语义与token/mask判断仍待完成，G-DATA及P04正式训练未放行。

| 对象 | 精确身份 |
|---|---|
| 原D1候选 | `f4f73c9ac8e004b48a74a80ac00617a01c4da324` |
| 原R1独立PASS | `40252f8517f3c7ac8ddc0340847946ac902200e1`，P0/P1/P2均0 |
| S0实际集成测量 | `0f3d04f6ffee8ba77b3383ebd38459512cea718e` |
| 最终PR head | `34773a327a961a571269d1687281e628668dae20` |
| 实际CI checkout | `bc11f1c8cc66a85aa3f7ac312f84c69141d40963` |
| 实际main合并 | `42eaa50a9519efe96d60b49f07cfbd106b36778c`，14:30:48 UTC |
| 合并父提交 | `d63e5aea79e022e2dc77ae7e4b21e266224b7494`、最终PR head |
| final head / CI / main共同tree | `2071ecaa55c6d65b265444469844668cae4b7245` |

原[R1报告](review/P02-training-binding-r1/README.md)和候选SHA保持在普通合并祖先中。最终PR head相对S0实际集成只增改八份S0说明；生产代码、测试、配置、107份sdist输入及49份包文件未变。GitHub已读回closed/merged，本机main经ff-only同步，364份实际文件与最终CI对应。GitHub归一化快照的历史base字段未用作父关系证明；上表父提交来自实际Git对象和CI checkout日志。

[最终CI34038982502](https://github.com/kris0516/ToolAlign/actions/runs/34038982502)，run number 115，Python3.14 job101502153765及Python3.11 job101502153833各14步骤全部成功。每环境550 passed/48 optional-tokenizer skipped，另46项P00检查通过；lint、4契约、364路径公开扫描及241私有canary/18公共fixture的sdist/direct/rebuilt路线通过。CI未提供本地固定tokenizer来源，48跳过不冒充已运行。日志按connector返回的完整解码字符串精确保存为UTF-8，未改换行或BOM：

| 环境 | 日志bytes | 原日志SHA-256 |
|---|---:|---|
| Python3.14 | 28485 | `6f24a622fe5f5e2da354dbf0a557f4224a219a7b93745501fe0d0844c903641a` |
| Python3.11 | 28595 | `e2164cd8ce491be9771ad4e604f641c186927fb9643d6041d221cb71f952c692` |

S0于14:30:24 UTC核对最终run/jobs、两份原日志、真实CI父/tree及364个工作树Git对象，证明SHA `4a2ae488b8d29ef280cb6a4efe93994b0cbd1429928c489c7779a1f8249ff54c`。随后以expected_head精确约束普通merge，保留实际ready/merge/readback回执。

14:32:17–14:33:30 UTC，在实际main重新执行九条CPU验证命令，全部exit0。复用既有Python3.14.7 CPU环境、本地固定native tokenizer和原测试；离线、禁用bytecode及Torch/TF/Flax。每条receipt保存完整argv、cwd、环境、开始/结束UTC、main/tree和364份源码hash；全部开始/结束源码不变，工作树干净。四组互不重叠：844 passed/2 HF-only snapshot-cleanup skipped（52.98s）；原格式60 passed（0.11s）；截止时间2 passed（11.56s）；本轮R1边界13 passed/110 subtests passed（1.24s）。合计**919 passed / 2 skipped**，110 subtests、D1新增63例和安装重复13项不再相加。

| main命令标签 | UTC开始–结束 | exit | 完整日志SHA-256 |
|---|---|---:|---|
| cpu-combined | 14:32:17–14:33:10 | 0 | `c0b1c7476246b548a8d51cba71a742d372ce87812fa3ff4f8b005a408e65cf6e` |
| original-format-review | 14:33:10–14:33:10 | 0 | `b746f5b04deb9a4a5ab9ad150ef96de12b7adc51f3b8f0c709ce03184f5e8501` |
| independent-deadline-review | 14:33:10–14:33:22 | 0 | `f30f9f0420f8920b956ccd24a301d6473e8cf43b4b57cf2fc01ca1b87e2e5af2` |
| independent-training-binding-review | 14:33:22–14:33:23 | 0 | `b29a4fddb836042e4ae1383016921bfd76793df77417e86fcde2e45608c68e97` |
| ruff | 14:33:23–14:33:23 | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| ruff-new-reports | 14:33:23–14:33:23 | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| freeze | 14:33:24–14:33:24 | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| public | 14:33:24–14:33:29 | 0 | `a81bc96c013ae8607af64cc0b49b347e3d049e289659c97f62191b4e75159bfe` |
| archive-verification | 14:33:29–14:33:30 | 0 | `19b5485082b5668986f014fde0b8baebd8dc13cf3b93cccca421206e71312c8d` |

main归档操作为**读取并直接解析现存S0集成三归档**，新增build=0、install=0；它们的真实构建和默认安装仍采用[原集成记录](S0_P02_TRAINING_BINDING_INTEGRATION.md)的14:04–14:10时间。sdist 107 Git成员加PKG-INFO、两wheel各49生产成员加5 metadata，完整内容、路径/链接、依赖、entry point/license与RECORD匹配main；现存target的49份包文件也重新对应main。sdist SHA `6bf81574cace92a9e3734cc8790a47818e05534d5c033951b0477a456e84d431`；两wheel SHA均`86adee698e490871894f2670d427e83617071b2a2c08c2f7d25cb3f7405bb1ec`。本次归档证明SHA `4f0f4c6fa3dd8c0b0a66f256af16648b3be17896c8f38c488f06ead59f6542da`。

原S0默认wheel接口执行在非源码cwd、-B/-I/-S下完成，17个模块来自当时新target，11类可选依赖不可导入；selection完整verify和五种固定输入篡改拒绝通过。main重新核对该原日志、17个模块的当前文件及全部49份不变包载荷，未将它写成新安装/API执行。普通源码直接wheel仍NOT_RUN；CI canary direct路线独立计。没有新建13例人工包、全量8228编码或原数据物化。

S0主干汇总证明SHA `f0a806f157d6d34ace202bc291352f21bd0b9f9baff3715bf39b807c0220511b`，绑定上述九条receipt、CI/Git/包和原安装来源。四条实际截止时间子进程观察均确认handle关闭、reaped和目录清理，记录PID当时均不存在。共享GPU锁实际空闲。原D1四条、R1三条辅助失败，以及S0集成归档receipt同名导致的外层失败均保留原始记录；原缺失时间/子退出码未补造。本次main九条检查无失败，不更改旧负结果。

同次核对：原语义100行与token/mask13行填写副本均0 reviewer/0 verdict，SHA分别仍为`eee6b377c78eeff7ab82d65dbc0dcf6934013f546e2439a24309b8b847220efb`和`ab02b3c7d4b8cac8d12899edfc52fd9ce910ff1b90de0107c0197abc57b7dd4c`。原浏览器URL安全策略拒绝保持，实际材料页面观察0页；没有替代绕过或模型代签。训练选择保持smoke1600/197、formal6013/217及配置training_authorized=false。G-DATA、P04实际trainer/collator与容量预检、正式baseline/SFT、后续P05–P09均未因CPU合并而验收；无新模型/GPU、环境/依赖下载、费用、推理服务或模型/数据上传。
