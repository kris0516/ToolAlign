# S0｜v3 输入 FD 清理修订完整接收

2026-09-07 23:39:56 UTC，S0 完整接收 T1 候选 `d80667e4f6e3a63d5c49d4293e99271ca3c2aca1`，tree `04001535b91fca46e9612f6130da1b1745eab9e4`；唯一 parent `9e08a0961ac2fbf9e993585289b4e82b7115f016`，后者唯一 parent 为原候选 `1769046468eb2ebfdd9e982ba4938833760e3fe0`。状态 **READY_FOR_REVIEW_CPU**；新独立复审尚未运行。

独立 T1 原生任务于23:29:51 UTC completed/idle，模型与推理保持 gpt-6-astra/max。授权为完整 `df37a3c64bb114b70ab8221d167ea021e22524e7`；本次 S0 证明 SHA256 `2bd9eac089ac0e1136ad7ea2a6c063a1bfce3decec4cdd62f9bc7a1ec71d213d`。私有原始路径和原生命令仅保存在本机。

## 范围与实际证据

原正式 R1 `58212d26bdb1c6a681a1ac34ccae854daefca8d3` 的唯一 P2/F2 是 `data_v3_fdopen_failure_closes_successfully_opened_descriptor`。S0 已完整接收原审查，F1分项关闭、F2首次计1；[原审查接收](S0_P04_DATA_V3_REVIEW_R2_HANDOFF.md)保持。T1补充副本中的S0接收pending是23:18:36 UTC的历史观察，不回写为后来的状态。

修订仅改变 `src/toolalign/training/sft/data_v3.py` 的裸FD到stream所有权交接、对应测试，新增三份报告/交接；共624候选文件、五份差异。构造失败关闭自有FD并保留原异常，成功后的关闭由stream完成。源码 SHA `3f7cb19fd9435076a35c20b85cf1636c68b85fda43df8e95dece7b409cbff910`、测试 SHA `145f9ac4f67b6c98ea9b4e1e2c108843e60b253b32d4757ddb8103753a0e30f0` 与Git、原运行快照和安装包一致。

S0核验13,825路径、421链接和八个lstat-only FIFO，包含原12,673当前路径及两份原公开快照映射、389旧链接、六旧分支和root identity。十二授权、七原反例输入、三份原R1补充副本保持；旧30文件/1链接缺失例外未改变。27条原始命令逐条绑定实际argv、UTC、exit和stdout/stderr，81份原源码快照及终态退出均已核对。

| 项目 | 原实际结果与限制 |
|---|---|
| 模块测试 | 一次157 PASS，包含原147和新增10；实际HEAD为1769046加两份授权修改，不能写成运行于后来的9e08a096提交 |
| 原六项I/O检查 | 原文件SHA `24d475c6f762b00bd218d609a81a4e019e7996a6eee946f671431c3916eb7a13`未改；源码/新安装target各一次6 PASS，运行于9e08a096；相同六项的两种路径分列 |
| 子进程 | 八个自有child全部exit0/reaped，原封存前PID均不在；目录替换检查确认打开的FD已关闭 |
| 三份离线归档 | 143/70/70成员；sdist SHA `1ea38feab6f0fb9c02527b2534ad336477c31a0e1c60d97e7d1fa323ea8629e4`；两个wheel同为 `100ec324d73c8497a3ed76580eb64dad0860f18f027e64d7428d4b2f9fdecb10` |
| 默认安装 | 一次--no-deps新target；65生产包文件、76安装文件、完整RECORD 70/70/75及metadata/entry points/LICENSE通过；复用五个旧依赖，无新环境/下载 |
| 封存 | seal `81b38f140e30ab4fc41165d238ecf26ddca0c1b5fd156bf03732b8f1da88e8f8`；receipt `cff3dc6f2157a6c5acd3e5b6e0e9c16545b8b0f6ec0144bff27d4046b84b87c2`；含五份公开差异的制品上界16,972,749 bytes，小于1GiB |

源码六项证明 `57801467dbd0e2d4345a6c7d16e5b2dc62957f4674ed279878f3f5b5ee460854`、安装六项 `28af31696bb44698c963df41ee1f888f670b046cc402e76f4e8795932b00465b`、package `c46b8e5303d19fa75ddf1489745ff79b6ce05706edc380d90d0664f43fbfb410` 和交付保全 `e45cef3a6f657f491b105b3ada79807e881d1ba7fa74d94a39a4d309c01c0224`均与实物相符。S0原生命令绑定脚本的两次读取/解析错误单独保留，修正后27/27与终态通过；没有重跑T1测试或改候选。

本修订真实609输入消费、13例转换/导出/回读均为0；实际固定消费仍对应原1769046时点。新源码真实数据消费为NOT_RUN，不把旧导出重新命名为新消费。原5 PASS/1 FAIL、所有历史失败和封存保持；S0本次新增build/install/数据API/编码/框架/模型/GPU均0。

后续由[R1精确复审](../coordination/tasks/P04_SFT_DATA_V3_FD_CLOSE_REVIEW.md)决定F2关闭。独立PASS、最终组合CI、main验证完成前不验收此修订；固定Qwen模型CPU PR17/main与冻结v3 G-DATA已验收结论保持，正式模型训练/容量/评测/服务仍NOT_RUN。
