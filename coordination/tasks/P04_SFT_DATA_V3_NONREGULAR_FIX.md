# P04-SFT-DATA-V3-NONREGULAR-FIX｜拒绝阻塞的特殊文件输入

状态：IN_PROGRESS，T1；已于2026-09-07 20:09:29 UTC按完整 `90ded89286d130b2e36dd7e18d334ed603ced9f6` 原生派发，并核验新轮ACTIVE。新branch/身份/7份输入及旧证据intake待交付。code_base与父候选为 `f3b7f1a1abb23cce3bdccb74ddc6d2e0477bb2aa`，tree `1cd40f093c17da1c5a1f1399117c29eb3c1d9547`；不是已通过R1的生产基线。原生产基线48be435、原bfdf2a2源码和全部已交付证据保持。完整authorization_commit为包含本次范围的S0协调提交，由原生消息给出精确SHA。统一gpt-6-astra/max，plan-v0.1、coordination.v1、toolalign.contracts.v1、ADR-0026和REVIEW_POLICY。

沿用原T1独立App任务及自己的worktree，新建 `codex/p04-sft-data-v3-nonregular-fix-r1` 与新私有scope `p04-sft-data-v3-nonregular-fix-r1`。先保存完整授权中的AGENTS/GOAL/PROTOCOL、REVIEW_POLICY/REVIEW_FAILURES、RESOURCE_LOCK、ADR-0026、本任务、原数据CPU任务/精确配置、S0完整交接与[原发现](../../reports/S0_P04_DATA_V3_NONREGULAR_FINDING.md)。切换前核验原f3b7f1a1分支、618旧公开Git/快照、原scope终态seal、旧失败、root identity及固定609输入；新身份只写新scope，旧scope/旧分支和T1上一轮未打包文档不修改、不覆盖。

目标只关闭原发现P04-SFT-DATA-V3-F1。R1原候选完整审查继续；中间发现不是正式FAIL计数。原读取函数先阻塞open再fstat，空FIFO无writer时不能及时拒绝。修订前读取原R1实际栈/失败，不必重跑旧失败。修订需在打开前拒绝非普通文件；同时保证预检查后被换成FIFO等非普通对象时，打开不会阻塞，再由同FD检查拒绝。保留O_NOFOLLOW、同FD的fstat/hash/大小/byte budget、原DataError分类与正常文件结果；不放宽路径、摘要、数字类型、输出覆盖或其它数据绑定。

仅允许修改 `src/toolalign/training/sft/data_v3.py` 和 `tests/training/test_sft_data_v3.py` 的相关部分，新增 `reports/experiments/P04_SFT_DATA_V3_NONREGULAR_FIX.md/.json`、`coordination/handoffs/P04-sft-data-v3-nonregular-fix-r1.md`。固定配置 `e27a7d4bcdd378944af56559833c3bcd10f601b689a75f1daec96b884bd780c1` 不变。禁止修改旧handoff/报告、其它生产/测试、CLI、公共I/O工具、模型包、依赖/构建/CI、S0协调或其它worktree。若发现另一个共享组件有同类问题，向S0提交最小证据，不在本范围顺手重构。

固定最小输入manifest `cd401df1e59e791db5ef0bb9e13989ca23a664d2fa7b84ce32372d80dd2a190c` 及7份精确副本由S0私有分发；输入只读，不递归读取R1其它工作。原未修改探针SHA `f44cc02cc066ad9f2befe1b11c27c92981ff77ae87cf83672c422e3118ff1c7d`，原结果 `fa03a9689cbda1117aac63766dc55eaea49184a6473101f2322291a727bf7744`，S0接收证明 `cf6826fa347277151d01886acb97ad8b25bab5dc5bf88ddfe0ef92e5c66c1603`。

验证包括：无writer的FIFO及时拒绝；预检查后普通路径被换成FIFO仍不阻塞；目录/现有symlink拒绝；普通文件完整读取与hash-only模式、大小/hash/预算错误保持。用少量原创fixture、必要自有child和有界等待验证可观察行为，不把一个更长timeout当修复。不依赖真实语料、tokenizer或框架。原R1探针保持字节不变，修订后源码版与默认安装版各最多运行一次，使用各自新输出根；证明 `rejected_before_writer=true`、`empty_writer_needed_to_release_open=false` 和child已回收。若任一实际探针失败，保留原失败并交具体原因，不覆盖输出后无解释重试。

只运行本模块相关CPU测试及最小新反例，不机械重跑无关历史数据/HF/toy组。每次pytest用任务/本轮独占的新 `--basetemp`，公开输出测试根无 `.toolalign-local` 祖先；特殊文件用lstat类型/权限等单列封存，普通文件清单不得读取FIFO或设备。各次原argv/UTC/exit/完整stdout/stderr、源码时点与失败保留。

允许在新scope用已有离线构建支持产生一组最终sdist/direct wheel/sdist rebuilt wheel、一次新默认target安装，不创建环境/安装依赖/下载。核对真实归档成员、metadata/entry points/LICENSE/RECORD及打包源码时点；非源码cwd证明模块来自target、普通文件语义和原R1探针通过。新增制品≤1GiB；旧T1两组归档/target、13例完整数组和原counter保持。旧固定数据消费结果来自bfdf2a2时点，不伪称该新源码已消费真实数据。

实际固定609数据prepare/verify/13例转换或导出回读额度均0；全数据build、新编码、框架/模型、GPU、优化、生成、业务API、浏览器、权重/数据上传、新费用均0。原创I/O fixture调用所修的局部读取函数不计真实数据消费，但必须明示来源；不得重启旧scope已用尽的额度。

先回报真实新分支/身份、最小输入和旧证据intake。若原R1正式审查随后交付，由S0明确补充原review SHA及要求后在同一范围接入，不能自行扩大任务。完成后只提交上述五路径、普通推送并原生交完整candidate/tree/parents、测试与所有失败、原探针两次结果、实际归档/安装和最终seal后结束。不给自己签独立PASS，不合并main；S0安排R1复审和最终CI/main。普通回报S0省略model/thinking，保留max。
