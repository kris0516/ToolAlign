# S0｜v3 特殊文件修订完整接收

2026-09-08，T1 完整修订 `1769046468eb2ebfdd9e982ba4938833760e3fe0` 已普通推送、原生 completed/idle，S0 完整接收通过；状态 **READY_FOR_REVIEW**。[Draft PR18](https://github.com/kris0516/ToolAlign/pull/18)包含原 v3 数据接口与本次修订，等待独立复审。原 [PR16](https://github.com/kris0516/ToolAlign/pull/16)、原候选和原 FAIL 保持。

候选 tree `1373bd4c838a1af395a1ede4f7c4d7029ffad271`；唯一 parent 为源码 `53d86109f18e4131cff1ddcb905086892580d136`，其唯一 parent 为原候选 `f3b7f1a1abb23cce3bdccb74ddc6d2e0477bb2aa`。相对原候选只改两份授权源码/测试并新增三份报告/交接；621份完整候选与远端及冻结快照一致。

修订在打开前检查普通文件，并使用 `O_NONBLOCK | O_NOFOLLOW` 打开后通过同一 FD 再检查，覆盖预检查后换成 FIFO 的窗口。原 `fstat`、hash、大小、byte budget 与错误分类约束保持。原独立审查 `b99a644e3ac0386f5ebe55cfd32e51b99e89781a` 只有同一 F1/P2，见[正式 FAIL 接收](S0_P04_DATA_V3_REVIEW_HANDOFF.md)。问题 `P04-SFT-DATA-V3-F1` 当前连续未通过仍为1，未由自测关闭；本次接收计数增量0。

S0 于2026-09-07 21:21:25–21:21:27 UTC核验12,675条文件路径，证明 `6c7cbc37e690cb270d3b33d80e0934efe1b0881191cedb6ec65e2d239e3ae39b`。

| 核对项 | 结果 |
|---|---|
| 原生命令 | 26条 argv/cwd/UTC/源码前后快照/stdout/stderr/exit 与实际调用和退出逐一绑定；最终seal另有原生 exit0，证明 `acabfc886c26117a98913e1f3b909f54515de0d7b362312283462ce9db4aaf7c` |
| 输入/旧证据 | 13份精确授权副本、7份最小反例输入，10,935旧路径中的10,933份现存字节不变；2份授权修改用原f3 Git/原快照与新源码分别绑定；370旧链接、5旧refs、根identity和609旧输入保持 |
| 原反例 | 原probe字节未改，源码版和安装版各1次；均 `rejected_before_writer=true`、无需空writer释放、child exit0且已回收 |
| CPU自测 | T1 147 passed，包含135项既有用例和12项新I/O用例；安装目录外 `-I -S` 的5项原创普通文件I/O检查通过；不是独立R1结论 |
| 特殊节点 | 2个原probe FIFO和2个竞态/拒绝fixture FIFO仍在原节点，lstat类型/权限/device/inode一致；不读取FIFO内容、不放入普通文件hash清单 |
| 归档/安装 | sdist143成员，direct/rebuilt wheel各70成员且逐字一致；65生产包文件与当前源码一致，安装76文件（含另列.lock）、RECORD 70/70/75行及metadata/entry points/LICENSE通过 |
| 制品 | scope/独占pytest根/链接文本及4份终态文件共30,438,941 bytes；加5份本次公开改动共30,562,963 bytes，低于1GiB |

最终seal `9a23a53af2ebfd959c6c2d866b4fc24203439867ba7fe7148a60601396633768`，receipt `baa135ee31cf28cd43c16a00ed90516a1c5975715ca1f4a0e0ea4e54b84f6447`；原finalizer源码前后hash相同。sdist `cabbc8a37151f767925d9f83fd05b9adab93c88798db11fb298135b84b55d3de`，direct/rebuilt wheel `101eccd619e16805230cfdb8b440d4f19858020ae5d6c1d3d4068b0d31fa1ecf`。构建/安装使用原离线支持和5个现有默认依赖，没有新环境或依赖下载。

失败不删除：T1记录器因缺commands父目录产生的启动失败保留，精确开始UTC仍未记录；补目录后的新intake与后续测试/probe/构建/安装通过。S0接收脚本先后因比较项包含snapshot字段、将授权索引当Git文件而退出；两个原脚本及错误日志保留，按实际schema核验后通过，不计产品缺陷或正式修订失败。原R1/T1更早失败及缺失counter保持。

当前修订的真实609输入prepare、13例转换/导出/回读均 **NOT_RUN**；旧成功仅属于原bfdf2a2/f3时点，不能更名为修订已消费。后续[独立复审](../coordination/tasks/P04_SFT_DATA_V3_NONREGULAR_REVIEW.md)将单独绑定新consumer，排在R1当前模型CPU审查之后；此次仅READY，未提前派发或激活额度。S0本次新生产API、构建/安装、编码、框架/模型/GPU均0。冻结v3的G-DATA批准保持，真实runtime、容量、正式训练/评测/服务仍未验收。

PR18候选CI34162930570双Python各14步骤成功，各986 passed/48 skipped，另独立P00历史组各46 passed。原日志与Git绑定实际CI合并 `9167d439b1a34ee72bf2fc0b4599dcf2f10f8ffd`（父06931e2/1769046），639文件保持631份当时main和8新增文件；第9份candidate改动为main已存在且等字节的固定配置。证明 `9b3d2b8dcdf668356a0597be63dcdfd78f626e8e806134746c5195633ff552ba`；首次S0核验把9份candidate改动均当作main新增的断言失败保留，按实际共同配置映射后通过。此次不是最终集成CI或main验收，R1-r2仍READY未派发。
