# P04-SFT-DATA-V3-R3 独立审查

**PASS**，精确候选 `d80667e4f6e3a63d5c49d4293e99271ca3c2aca1`；P0=0、P1=0、P2=0。R1 建议关闭 F2 `data_v3_fdopen_failure_closes_successfully_opened_descriptor`。原 `58212d2` 对 `1769046` 的 FAIL 保留，正式台账由 S0 更新。

候选 tree `04001535b91fca46e9612f6130da1b1745eab9e4`，parent `9e08a0961ac2fbf9e993585289b4e82b7115f016`。本轮授权 `6ff0cf72ad309cd7be86a42eb80fee0913a35991`，安装启动器限定追加 `75e03f6287da34ce5fe825078defa2fef1abd627`；独立 Codex AI R1，gpt-6-astra/max，契约为 plan-v0.1、coordination.v1、toolalign.contracts.v1。

修订把裸 FD 的所有权保留到 `fdopen` 构造成功：构造失败关闭同一 FD，原异常或 DataError cause 保持；构造成功后由 stream 在正常返回、校验拒绝及读取错误时关闭。`O_NOFOLLOW/O_NONBLOCK`、同 FD 的 fstat/hash、大小与字节预算、content/hash-only 语义保持。除 `_read` 外，61 个顶层语法节点不变；旧候选的其余 619 个文件逐字不变。

| 本轮实际检查 | 结果 | 边界 |
|---|---|---|
| 原模块测试 | 一次 157 PASS | 精确 d806 源码，原创小 fixture |
| 原未修改六项 I/O，源码 | 一次 6 PASS | 包含真实目录/FIFO/链接替换、同 FD 摘要和增长预算 |
| 新增独立 FD fixture | 一组 4 PASS | SystemExit 构造失败；stream 退出后同一 FD 编号的新 owner 在成功、摘要拒绝、部分读取失败三路保持打开 |
| 原六项 I/O，首次安装尝试 | 启动失败，保留 | pytest 导入缺少既有 py shim；pytest.main 未进入，实际用例/fixture child 均 0 |
| 原六项 I/O，S0 限定追加 | 一次 6 PASS | 同一安装 target，parent/三个 child 均 -B -I -S，独占新输出根 |
| 原现存归档与新默认 target | PASS | 143/70/70 成员，65 包文件、76 安装文件、75 RECORD、32 实际模块来源 |
| 源码 ruff、契约冻结 | PASS | 公开材料检查与提交证据另随终态封存 |

源码与安装版六项是同一组六项的两个执行路径，分别记账。八个实际 fixture child 均有界退出、回收并在后续只读核验时已不在。只安装一次既有 wheel，复用五个默认依赖，没有新构建或依赖安装。

首次安装启动器的失败和已消费 reservation 未改写。S0 按精确追加授权允许新 bootstrap/runner 副本；功能差异只放行 pytest 9.0.2 自带、已绑定 RECORD 的 `py.py`，其余差异用于新名称和 child 路由。原 helper、原失败及随后成功分别封存。另有三次有记录的只读保全/intake 辅助错误、四次只读查看错误；修正后绑定通过，不作为候选缺陷或正式失败轮次。

切换前保全了旧 626 公开 Git/快照、23 原命令和全部历史结论；94,244 路径、1,707 链接及 13 个仅 lstat 的 FIFO 已核对。20 个原模型文件仅比较既有 stat token。原 30 文件/1 链接路径缺失例外与其保留副本保持，没有重建并冒充原件。新接收独立核验 14,480 路径、27 原命令、81 源码快照、三份现存归档；T1 的 157 项测试实际发生于父 HEAD 加两份修改，原六项与构建发生于 9e08，时点未改写。

[结构化证据](evidence.json)列出真实运行时间、结果、原回执和输出摘要。原六项文件[逐字副本](test_independent_io.py) SHA256 为 `24d475c6f762b00bd218d609a81a4e019e7996a6eee946f671431c3916eb7a13`；新增四项实际运行文件的完整文本及 SHA256 保存在 evidence.json 的 `independent_FD_fixture_source` 字段，可原样取出复核。完整原 argv、进程、输入引用、源码/安装绑定与终态 seal 仅存本机。

本轮真实 609 输入 prepare/verify、13 例转换/导出/回读全部 **0**；d806 的实际真实数据消费仍 **NOT_RUN**，旧成功保持 1769046 时点。模型/框架/GPU、优化/生成、业务 API、浏览器、上传和新费用均 0。F1 既有关闭保持；本次 PASS 交 S0 保留原 SHA 集成，最终 CI/main 验证待 S0 完成，正式训练未授权。
