# P04-SFT-DATA-V3-fd-close-fix-r1 交接

**READY_FOR_REVIEW_CPU。** 实现 `9e08a0961ac2fbf9e993585289b4e82b7115f016`，唯一父 `1769046468eb2ebfdd9e982ba4938833760e3fe0`；完整授权 `df37a3c64bb114b70ab8221d167ea021e22524e7`。独立 T1、gpt-6-astra/max，分支 `codex/p04-sft-data-v3-fd-close-fix-r1`。完整候选/tree/parents 由本交接所在提交、终态 seal 和原生交接共同绑定，尚未经新独立 R1 审查。

接入原正式 R1 `58212d26bdb1c6a681a1ac34ccae854daefca8d3`，tree `0e3a60db9865d82b8a15f35727769975d3b1be2b`，唯一parent完整1769046；FAIL/P0=0/P1=0/P2=1，唯一 F2 为 `data_v3_fdopen_failure_closes_successfully_opened_descriptor`。原 F1 分项 PASS、建议 S0 关闭；本轮只落实已派 F2，不另计修订轮次，不修改counter。三份只读补充 SHA 分别 README `7229be63d9a845cd6c83e4ee0627543d799f77bb611c56375259d55989ecfc3b`、verification `475774ab508dea907be81d92281355f9a582dd8a57b224e4dc6640aecae9b9e5`、handoff `2cd81b49d33355ca33347fdee04e89536befe72af4fd293dfaf5b1646a72f7ea`。补充到达时 S0 完整私有接收仍待核验，不写成已验收。

仅修改 `src/toolalign/training/sft/data_v3.py` 的裸 FD → stream 所有权交接及 `tests/training/test_sft_data_v3.py` 对应回归，新增本交接和[报告](../../reports/experiments/P04_SFT_DATA_V3_FD_CLOSE_FIX.md)/[结构化证据](../../reports/experiments/P04_SFT_DATA_V3_FD_CLOSE_FIX.json)。构造失败关闭同一自有 FD，原异常/cause保持；成功和后续错误由 stream 清理，不二次关闭。配置、旧文档及全部其它生产/测试/构建文件保持。

限定模块一次157 PASS（原147+新10）；未改六项 SHA24d475c6 在源码及新默认target各一次6 PASS，原5 PASS/1 FAIL仍保留。8个测试child全部exit0/reaped，封存前原PID已不在。原f44探针和无包装观察脚本本轮调用0。源码/测试 SHA分别 `3f7cb19fd9435076a35c20b85cf1636c68b85fda43df8e95dece7b409cbff910` / `145f9ac4f67b6c98ea9b4e1e2c108843e60b253b32d4757ddb8103753a0e30f0`；157项运行于父HEAD加这组修改，两组六项和build/install运行于9e08a096。

唯一离线三归档及默认target安装完成，143/70/70成员、65包文件与新源码一致，metadata/entry/LICENSE/完整RECORD70/70/75通过。sdist `1ea38feab6f0fb9c02527b2534ad336477c31a0e1c60d97e7d1fa323ea8629e4`；两wheel `100ec324d73c8497a3ed76580eb64dad0860f18f027e64d7428d4b2f9fdecb10`。安装仅--no-deps、无新环境/依赖/下载，额度均耗尽。

原621公开Git/既有快照、12,673旧当前路径+2项原快照映射、389链接/6旧分支/root identity/旧seal及原4 FIFO保持；新4 FIFO按lstat单列，普通hash不读取FIFO。原30文件/1链接缺失例外保持。本轮截至成文无失败；原目录失败、旧bootstrap和数据消费失败均未覆盖。真实609/13数组、新编码/框架/模型/GPU/优化/生成/业务API/浏览器/上传/费用均0；原固定消费保持1769046时点，新源码实数据NOT_RUN。

源码六项证明 `57801467dbd0e2d4345a6c7d16e5b2dc62957f4674ed279878f3f5b5ee460854`；安装六项 `28af31696bb44698c963df41ee1f888f670b046cc402e76f4e8795932b00465b`；package `c46b8e5303d19fa75ddf1489745ff79b6ce05706edc380d90d0664f43fbfb410`；交付保全 `e45cef3a6f657f491b105b3ada79807e881d1ba7fa74d94a39a4d309c01c0224`。原始命令/源码时点/输出及最终公开检查、普通push和完整seal在本机私有交接绑定。新增制品上限1 GiB；精确总量随终态回执交付。

普通推送并原生交付后本轮结束。请 S0 核验完整候选/封存，安排精确独立复审；不默认重跑真实消费，不合并main，不把本自测写成独立PASS。
