# P04-SFT-DATA-V3-FD-CLOSE-FIX｜FD 构造失败清理

**READY_FOR_REVIEW_CPU；本轮独立 R1 复审 NOT_RUN。** 实现 checkpoint `9e08a0961ac2fbf9e993585289b4e82b7115f016`，唯一父 `1769046468eb2ebfdd9e982ba4938833760e3fe0`。该父提交是待修订候选；完整授权 `df37a3c64bb114b70ab8221d167ea021e22524e7`，分支 `codex/p04-sft-data-v3-fd-close-fix-r1`，Codex-AI(T1)、gpt-6-astra/max。精确最终候选/tree/parents 随终态封存和原生交接提供，不在本文件伪造自引用 SHA。

本轮接入原 [R1 正式审查](https://github.com/kris0516/ToolAlign/blob/58212d26bdb1c6a681a1ac34ccae854daefca8d3/reports/review/P04-sft-data-v3-r2/README.md) `58212d26bdb1c6a681a1ac34ccae854daefca8d3`：FAIL，P0=0/P1=0/P2=1，唯一 F2 要求 `data_v3_fdopen_failure_closes_successfully_opened_descriptor`。原 F1 分项 PASS、建议由 S0 关闭；F2 与已派范围相同。三份原报告/交接的精确 Git 副本已保存。接入时 S0 完整私有 receipt 核验仍待完成，T1 未修改 counter 或旧报告。

预检查后的路径若被换成目录，原代码能及时拒绝，却在 `fdopen` 构造失败时留下 `os.open` 已取得的 FD。现在先保存裸 FD；只有 stream 构造成功才转交清理责任。构造异常时关闭同一自有 FD，并保留原异常或 `DataError` 的原 cause；清理自身的 `OSError` 不覆盖原构造错误。成功读取、hash-only 以及后续校验/读取失败仍由 stream 关闭，读取器不再次 raw close。

`O_NOFOLLOW`、`O_NONBLOCK`、预先 `lstat`、同 FD 的类型/大小/hash 与字节预算循环及原错误分类保持。仅修改 `data_v3.py` 的这段所有权交接和对应测试；配置 SHA `e27a7d4bcdd378944af56559833c3bcd10f601b689a75f1daec96b884bd780c1` 不变。

| 实际检查 | 结果与范围 |
|---|---|
| 相关模块一次 | **157 PASS** = 原147 + 新10；不累计旧轮 |
| 原未修改六项，源码一次 | **6 PASS**；测试 SHA `24d475c6f762b00bd218d609a81a4e019e7996a6eee946f671431c3916eb7a13` |
| 同六项，新默认安装 target 一次 | **6 PASS**；重复路线不计新独立用例 |
| 新 FD 回归 | 真实目录替换；三类构造异常；清理错误不覆盖原 cause；open 失败不关闭 FD；成功/读取/同 FD stat 错误后不二次 close |
| 子进程 | 单元2个、原六项每路线3个，共8个 exit0/reaped；封存前8个原 PID 均已不存在 |
| Ruff / 冻结契约 | PASS；公开扫描和提交/推送由后续终态回执绑定 |

157 项执行时 Git HEAD 为原1769046、工作文件已是新 `3f7cb19f` / `145f9ac4`，随后提交为9e08a096；两路线六项和归档执行于精确9e08a096。两路线实际 reader SHA 均 `3f7cb19fd9435076a35c20b85cf1636c68b85fda43df8e95dece7b409cbff910`，父进程和 child 来源核验一致。六项在独占外部 cwd/输出根执行，安装路线使用 `-B -I -S` 和显式旧默认依赖解析；无源树回退。

原六项 **5 PASS/1 FAIL** 及原无 stream 包装观察保持：一次残留一个 FD 是实测，原 probe 主动关闭自己的 FD；长期重复导致耗尽是源码推论，循环试验 NOT_RUN。本轮没有重跑原观察脚本，也未重复 f44 FIFO 实物 probe。新目录单元直接使用真实 `os.fdopen`，没有 stream 包装。

| 本轮唯一归档组 | 普通成员 | bytes | SHA256 |
|---|---:|---:|---|
| sdist | 143 | 357078 | `1ea38feab6f0fb9c02527b2534ad336477c31a0e1c60d97e7d1fa323ea8629e4` |
| direct wheel | 70 | 204865 | `100ec324d73c8497a3ed76580eb64dad0860f18f027e64d7428d4b2f9fdecb10` |
| sdist rebuilt wheel | 70 | 204865 | `100ec324d73c8497a3ed76580eb64dad0860f18f027e64d7428d4b2f9fdecb10` |

65 份生产包字节与源码、sdist、两 wheel 和新默认 target 一致。METADATA、entry points、LICENSE、完整 RECORD 70/70/75 全部核验；安装器额外空 `.lock` 单列。仅离线 `--no-deps` 安装 toolalign 一次，复用五个旧默认依赖；没有新环境/依赖/下载。构建与安装额度已用尽。

621 原公开 Git/既有快照、619 个当前未变基线文件、12,673 原当前路径及两项授权源码替换映射、389 链接、6 旧分支、root identity 与全部旧 seal 保持。原四个和新四个 FIFO 只按 lstat 单列；链接按 readlink 保存，不将特殊节点纳入普通 hash。测试自身对替换 FIFO 的非阻塞打开与清单不打开两件事实分开记录。旧30文件/1链接缺失例外没有恢复或冒充现存原件。

本轮真实609输入 prepare/verify、13例转换/导出/回读、全数据构建、新编码、框架/模型/GPU/优化/生成/业务API/浏览器/上传/费用均0。原R1固定消费属于1769046、reader212c688c的既有时点；新源码真实数据消费 **NOT_RUN**，没有新运行来重写该事实。交付检查时新增制品 15,371,267 bytes；最终文档/回执增量由 terminal seal 另计，上限1 GiB。

本轮截至成文的 19 条记录器命令均 exit0，原失败保持。完整实际 argv/UTC/exit/stdout/stderr、源文件快照、安装来源和特殊节点清单保留在本机；[结构化去敏证据](P04_SFT_DATA_V3_FD_CLOSE_FIX.json) 绑定对应 hash。最终公开扫描、candidate commit/push、远端匹配与终态封存单独接续；不增加测试或实物消费。技术独立复审及主干集成由 S0 安排，T1 不自签 PASS、不合并 main。
