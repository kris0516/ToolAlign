# P04 v3 数据读取的非普通文件阻塞发现

R1 在冻结候选 `f3b7f1a1abb23cce3bdccb74ddc6d2e0477bb2aa` 发现一个非普通文件边界缺陷，暂标 **P04-SFT-DATA-V3-F1 / P2**。这是中间发现，原候选整包正式 verdict 尚未交付；正式失败计数增量0，PR16保持Draft。

`src/toolalign/training/sft/data_v3.py:90` 先用阻塞 `O_RDONLY | O_NOFOLLOW` 打开路径，随后才以同一个FD进行fstat/普通文件校验。原创空FIFO没有writer时卡在open；R1于19:58:31–19:58:32 UTC让自有child报告栈，确认停在第90行。父进程随后打开并关闭一个不写任何内容的writer，读取才返回 `v3_regular_file_budget`。child最终正常exit0且被回收；外层“应在writer前拒绝”断言实际exit1。

原探针 SHA `f44cc02cc066ad9f2befe1b11c27c92981ff77ae87cf83672c422e3118ff1c7d`，原结果 `fa03a9689cbda1117aac63766dc55eaea49184a6473101f2322291a727bf7744`，原child栈 `12a6857997410b11ce9c9448c36c429d7bb5df511b9a6f5dcd0b58353bec50cf`。20:03:20 UTC，S0核对630路径的原命令、helper、源码时点及这些字节，证明 `cf6826fa347277151d01886acb97ad8b25bab5dc5bf88ddfe0ef92e5c66c1603`；仅接收原反例，没有重跑FIFO或生产API。

给T1的固定最小输入包含原探针、结果、child两流和命令/两流共7份精确副本，manifest SHA `cd401df1e59e791db5ef0bb9e13989ca23a664d2fa7b84ce32372d80dd2a190c`。没有复制FIFO本身、真实语料或新编码。FIFO作为特殊文件单列类型/权限，不能交给普通文件hash读取，也不能删除后冒充原件。

[定点CPU修订](../coordination/tasks/P04_SFT_DATA_V3_NONREGULAR_FIX.md)已准备，原T1任务确认completed/idle、干净f3b7f1a1；实际派发另记。修订要求打开前拒绝非普通文件，同时用非阻塞打开与同FD校验覆盖路径被替换的窗口，保留原no-follow/hash/大小/预算/退出语义。只运行原创I/O反例、相关CPU测试、默认安装和必要三归档；不增加实际数据prepare、13例转换、编码或模型额度。

R1继续冻结原候选完成整包审查；新修订须独立复核并经最终CI/main才能验收。既有13例成功消费、原两次失败、G-DATA和两候选CI保持原时点，不关闭本次发现。

20:09:29 UTC，S0再次核验T1原轮completed/idle及原10,935路径/370链接后，按完整 `90ded89286d130b2e36dd7e18d334ed603ced9f6` 原生派发定点修复并核验新轮ACTIVE，gpt-6-astra/max。实际新branch/intake待确认；R1当前仍审原f3b7f1a1，正式结论待交付。

20:25:39–40 UTC，S0核验T1实际新分支 `codex/p04-sft-data-v3-nonregular-fix-r1`、新scope身份、原生gpt-6-astra/max、13份完整授权和7份最小反例副本；共11,051路径/370链接通过，证明 `a376cfb1f65bcd1c93752ad6f206222acd100b0e497fff6d09d56101cbd14e10`。618旧公开文件绑定原f3 Git与冻结快照，原10,935路径及609输入、seal/receipt、5旧分支和root identity保持。当前 `53d86109f18e4131cff1ddcb905086892580d136` 只改两授权源码/测试；这是代码checkpoint，完整候选、源码/安装原探针结果与独立复审待交付。原记录器因缺失commands父目录而启动失败的事实保持，未补造其精确开始UTC；其后不同r2 label的intake及branch/activate三原命令exit0。S0本次只读接收，新生产API、归档/安装、编码、模型/GPU均0，原R1继续冻结f3。

20:32:30 UTC，S0核验T1源码版原反例与相关147项测试记录，共96路径通过，证明 `bd9da226692658d58e1c59eef4607432fe3a33e5cbf62622a458df8dbb669de4`。实际原探针只运行一次，20:25:15 UTC在 `53d86109f18e4131cff1ddcb905086892580d136` 源码 `212c688c1a38e4c2ce7863e34efc7635d75878729e4e141333caeb08a6fd16a4` 上及时拒绝：`rejected_before_writer=true`、`empty_writer_needed_to_release_open=false`，原child exit0/reaped。7份固定输入中的probe字节不变；FIFO原节点用lstat核对设备/inode/类型/权限，未读取其内容。147项模块测试包含12项本次原创I/O反例，原执行时工作区两处修改字节与该checkpoint相同；不把合计用例重复计数。原源码probe额度1/1已用，安装版与完整候选/独立复审待交付；真实609消费/13例转换/编码/框架/模型仍0。
