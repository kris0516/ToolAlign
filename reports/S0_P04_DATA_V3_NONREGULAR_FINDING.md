# P04 v3 数据读取的非普通文件阻塞发现

R1 在冻结候选 `f3b7f1a1abb23cce3bdccb74ddc6d2e0477bb2aa` 发现一个非普通文件边界缺陷，暂标 **P04-SFT-DATA-V3-F1 / P2**。这是中间发现，原候选整包正式 verdict 尚未交付；正式失败计数增量0，PR16保持Draft。

`src/toolalign/training/sft/data_v3.py:90` 先用阻塞 `O_RDONLY | O_NOFOLLOW` 打开路径，随后才以同一个FD进行fstat/普通文件校验。原创空FIFO没有writer时卡在open；R1于19:58:31–19:58:32 UTC让自有child报告栈，确认停在第90行。父进程随后打开并关闭一个不写任何内容的writer，读取才返回 `v3_regular_file_budget`。child最终正常exit0且被回收；外层“应在writer前拒绝”断言实际exit1。

原探针 SHA `f44cc02cc066ad9f2befe1b11c27c92981ff77ae87cf83672c422e3118ff1c7d`，原结果 `fa03a9689cbda1117aac63766dc55eaea49184a6473101f2322291a727bf7744`，原child栈 `12a6857997410b11ce9c9448c36c429d7bb5df511b9a6f5dcd0b58353bec50cf`。20:03:20 UTC，S0核对630路径的原命令、helper、源码时点及这些字节，证明 `cf6826fa347277151d01886acb97ad8b25bab5dc5bf88ddfe0ef92e5c66c1603`；仅接收原反例，没有重跑FIFO或生产API。

给T1的固定最小输入包含原探针、结果、child两流和命令/两流共7份精确副本，manifest SHA `cd401df1e59e791db5ef0bb9e13989ca23a664d2fa7b84ce32372d80dd2a190c`。没有复制FIFO本身、真实语料或新编码。FIFO作为特殊文件单列类型/权限，不能交给普通文件hash读取，也不能删除后冒充原件。

[定点CPU修订](../coordination/tasks/P04_SFT_DATA_V3_NONREGULAR_FIX.md)已准备，原T1任务确认completed/idle、干净f3b7f1a1；实际派发另记。修订要求打开前拒绝非普通文件，同时用非阻塞打开与同FD校验覆盖路径被替换的窗口，保留原no-follow/hash/大小/预算/退出语义。只运行原创I/O反例、相关CPU测试、默认安装和必要三归档；不增加实际数据prepare、13例转换、编码或模型额度。

R1继续冻结原候选完成整包审查；新修订须独立复核并经最终CI/main才能验收。既有13例成功消费、原两次失败、G-DATA和两候选CI保持原时点，不关闭本次发现。
